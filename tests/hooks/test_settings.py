"""`.claude/settings.json` is the wiring. Nothing read it until this test.

The rest of `tests/hooks/` fires each hook as a subprocess, which proves the hook works. It
does not prove the harness will ever *reach* it: the command in `settings.json` could name a
file that does not exist, the exec bit could be cleared by a `git checkout` on a filesystem
that does not carry it, the shebang could be wrong. Every one of those leaves the suite green
and both guarantees dead — and a guarantee that is silently not running is worse than one that
was never claimed, because the rule it carried is now believed to be enforced.

`tests/hooks/conftest.py` invokes the hooks as `[sys.executable, path]`, which deliberately
bypasses the shebang and the exec bit so that the *logic* is tested in isolation. This file is
the other half: the wiring, checked on its own terms.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SETTINGS = REPO_ROOT / ".claude" / "settings.json"

#: The events this repository wires hooks to. Listed so that adding a third is a deliberate
#: edit here rather than something that arrives unnoticed.
EXPECTED_EVENTS = {"PreToolUse", "PostToolUse"}


def _hooks() -> dict[str, Any]:
    settings: dict[str, Any] = json.loads(SETTINGS.read_text(encoding="utf-8"))
    hooks: dict[str, Any] = settings["hooks"]
    return hooks


def _commands() -> list[str]:
    found: list[str] = []
    for matchers in _hooks().values():
        for matcher in matchers:
            for hook in matcher["hooks"]:
                if hook.get("type") == "command":
                    found.append(str(hook["command"]))
    return found


def _resolve(command: str) -> Path:
    """The command as the harness expands it, with `$CLAUDE_PROJECT_DIR` at the repository."""
    expanded = os.path.expandvars(command.replace("${CLAUDE_PROJECT_DIR}", "$CLAUDE_PROJECT_DIR"))
    return Path(expanded.replace("$CLAUDE_PROJECT_DIR", str(REPO_ROOT)))


def test_settings_is_committed_and_parses() -> None:
    """A guarantee that lives on one laptop is not one — hence a committed settings file."""
    assert SETTINGS.is_file()
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(SETTINGS.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    assert tracked.returncode == 0, "settings.json is not tracked by git"
    assert set(_hooks()) == EXPECTED_EVENTS


def test_it_wires_every_hook_that_exists_and_no_others() -> None:
    """A hook file nobody wired is dead code; a wired file that is missing is a dead rule."""
    on_disk = {p.name for p in (REPO_ROOT / ".claude" / "hooks").glob("*.py")}
    wired = {_resolve(c).name for c in _commands()}
    assert on_disk == wired, f"on disk {sorted(on_disk)}, wired {sorted(wired)}"


@pytest.mark.parametrize("command", _commands(), ids=lambda c: Path(c).name)
def test_every_wired_command_can_actually_run(command: str) -> None:
    script = _resolve(command)
    assert script.is_file(), f"{command} resolves to {script}, which does not exist"
    assert os.access(script, os.X_OK), (
        f"{script.name} is not executable. The harness runs the command as written, so a "
        "cleared exec bit silently disables the rule this hook carries."
    )
    shebang = script.read_text(encoding="utf-8").splitlines()[0]
    assert re.fullmatch(r"#!/usr/bin/env python3", shebang), (
        f"{script.name} starts with {shebang!r}. `/usr/bin/env python3` rather than an "
        "absolute interpreter path, because the hooks run on whatever machine cloned this."
    )


@pytest.mark.parametrize("command", _commands(), ids=lambda c: Path(c).name)
def test_every_wired_command_runs_through_its_shebang(command: str) -> None:
    """Executed as the harness executes it — by path, not by handing it to an interpreter.

    This is the one place the exec bit and the shebang are load-bearing. Everywhere else in
    `tests/hooks/` the hook is invoked as `[sys.executable, path]`, which would keep passing
    with both of them broken.
    """
    script = _resolve(command)
    result = subprocess.run(
        [str(script)],
        input="not json",
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_the_hooks_run_without_the_projects_virtualenv() -> None:
    """The harness does not run them under `uv`, so they must be stdlib-only.

    `ops/isolation.py` is imported by `corpus_isolation.py` through a `sys.path` insert, and
    the whole reason it is stdlib-only is this: a hook that needed `PyYAML` would work on the
    machine that wrote it and fail silently everywhere else.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            f"import sys; sys.path.insert(0, {str(REPO_ROOT)!r}); import ops.isolation",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
