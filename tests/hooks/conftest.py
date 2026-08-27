"""The hooks are exercised as the harness runs them: a subprocess, JSON on stdin, an exit code.

Importing them and calling `main()` would test the same lines while proving nothing about the
contract that actually matters — that the harness can find the file, that it is executable,
that it reads the event shape the harness sends, and that a refusal comes back as exit 2. A
hook that passes its unit tests and never fires is the failure mode being guarded against.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

HOOKS = Path(__file__).resolve().parents[2] / ".claude" / "hooks"


class Fired:
    """What a hook did: its exit code and what it said."""

    def __init__(self, code: int, stdout: str, stderr: str) -> None:
        self.code = code
        self.stdout = stdout
        self.stderr = stderr

    @property
    def refused(self) -> bool:
        """Exit 2 is the harness's refusal. Every other code lets the tool call through."""
        return self.code == 2


@pytest.fixture
def fire() -> Callable[..., Fired]:
    def run(
        hook: str,
        event: dict[str, Any] | str,
        *,
        project_dir: Path | None = None,
        cwd: Path | None = None,
    ) -> Fired:
        payload = event if isinstance(event, str) else json.dumps(event)
        environment = {"PATH": "/usr/bin:/bin:/usr/local/bin"}
        if project_dir is not None:
            environment["CLAUDE_PROJECT_DIR"] = str(project_dir)
        result = subprocess.run(
            [sys.executable, str(HOOKS / hook)],
            input=payload,
            capture_output=True,
            text=True,
            cwd=cwd,
            env=environment,
            timeout=60,
            check=False,
        )
        return Fired(result.returncode, result.stdout, result.stderr)

    return run
