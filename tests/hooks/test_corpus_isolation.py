"""The corpus barrier fires *before* the write, and again after a route that has no `file_path`.

`tests/boundary/test_corpus_imports_nothing.py` is still the gate — it goes red on every push
and `main` cannot take a violation. These tests are about the other property: that the same
rule refuses the write at the moment it is attempted, so a session does not build for an hour
on top of a barrier that is already gone.

Every case here starts from a real repository shape in `tmp_path` — a `corpus/` directory with
a module in it — because the hook's first act is to decide whether the path it was handed is
policed, and a fixture with no `corpus/` would make every test pass for the wrong reason.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

HOOK = "corpus_isolation.py"

VIOLATION = "from holdout.core.guardrails import Envelope\n"
CLEAN = "from __future__ import annotations\n\nimport random\n"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "corpus" / "world").mkdir(parents=True)
    (tmp_path / "corpus" / "world" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "src" / "holdout").mkdir(parents=True)
    return tmp_path


def _write(project: Path, relative: str, content: str) -> dict[str, Any]:
    return {
        "hook_event_name": "PreToolUse",
        "cwd": str(project),
        "tool_name": "Write",
        "tool_input": {"file_path": str(project / relative), "content": content},
    }


def test_it_refuses_a_write_that_imports_the_system(
    fire: Callable[..., Any], project: Path
) -> None:
    fired = fire(HOOK, _write(project, "corpus/world/generator.py", VIOLATION), project_dir=project)
    assert fired.refused, fired.stdout
    assert "holdout.core.guardrails" in fired.stderr
    assert "belongs in evals/" in fired.stderr


def test_it_allows_a_write_that_does_not(fire: Callable[..., Any], project: Path) -> None:
    fired = fire(HOOK, _write(project, "corpus/world/generator.py", CLEAN), project_dir=project)
    assert fired.code == 0, fired.stderr


def test_it_catches_the_import_hidden_inside_a_function(
    fire: Callable[..., Any], project: Path
) -> None:
    """The dangerous one is never at module level — it is the local import added in a hurry."""
    source = "def demand(price: int) -> int:\n    import holdout\n    return price\n"
    fired = fire(HOOK, _write(project, "corpus/world/generator.py", source), project_dir=project)
    assert fired.refused, fired.stdout


def test_it_catches_an_edit_fragment_that_does_not_parse_on_its_own(
    fire: Callable[..., Any], project: Path
) -> None:
    """An `Edit` hands over an indented block, not a module. The AST refuses to parse it.

    This is the case the textual fallback exists for, and it is the ordinary case rather than
    the exotic one: almost every edit to an existing file arrives indented.
    """
    fragment = "        from holdout.core.ladder import quote\n\n        return quote(x)\n"
    event = {
        "hook_event_name": "PreToolUse",
        "cwd": str(project),
        "tool_name": "Edit",
        "tool_input": {
            "file_path": str(project / "corpus" / "world" / "generator.py"),
            "old_string": "        return x",
            "new_string": fragment,
        },
    }
    fired = fire(HOOK, event, project_dir=project)
    assert fired.refused, fired.stdout
    assert "holdout.core.ladder" in fired.stderr


def test_it_catches_a_multiedit(fire: Callable[..., Any], project: Path) -> None:
    event = {
        "hook_event_name": "PreToolUse",
        "cwd": str(project),
        "tool_name": "MultiEdit",
        "tool_input": {
            "file_path": str(project / "corpus" / "world" / "generator.py"),
            "edits": [
                {"old_string": "a", "new_string": "b"},
                {"old_string": "c", "new_string": "import holdout.core"},
            ],
        },
    }
    fired = fire(HOOK, event, project_dir=project)
    assert fired.refused, fired.stdout


def test_it_resolves_a_relative_path_against_the_project_root(
    fire: Callable[..., Any], project: Path
) -> None:
    event = _write(project, "corpus/world/generator.py", VIOLATION)
    event["tool_input"]["file_path"] = "corpus/world/generator.py"
    fired = fire(HOOK, event, project_dir=project)
    assert fired.refused, fired.stdout


def test_it_leaves_the_rest_of_the_repository_alone(
    fire: Callable[..., Any], project: Path
) -> None:
    """`src/` and `evals/` import `holdout` constantly. The barrier is `corpus/` and only it."""
    fired = fire(HOOK, _write(project, "src/holdout/thing.py", VIOLATION), project_dir=project)
    assert fired.code == 0, fired.stderr


def test_it_leaves_prose_alone(fire: Callable[..., Any], project: Path) -> None:
    """`corpus/real/README.md` explains what the corpus must not import. It may say the words."""
    fired = fire(HOOK, _write(project, "corpus/world/README.md", VIOLATION), project_dir=project)
    assert fired.code == 0, fired.stderr


def test_it_catches_a_file_written_by_a_route_no_editing_tool_reports(
    fire: Callable[..., Any], project: Path
) -> None:
    """A heredoc, a `sed -i`, a generator script. No `file_path` reaches any Pre hook.

    This is why the hook is also registered on PostToolUse. It cannot un-write the file —
    nothing at PostToolUse can — but the violation surfaces in the same turn that created it
    instead of at the end of the session.
    """
    (project / "corpus" / "world" / "smuggled.py").write_text(VIOLATION, encoding="utf-8")
    event = {
        "hook_event_name": "PostToolUse",
        "cwd": str(project),
        "tool_name": "Bash",
        "tool_input": {"command": "cat > corpus/world/smuggled.py <<'PY'\n...\nPY"},
        "tool_response": {"stdout": "", "stderr": ""},
    }
    fired = fire(HOOK, event, project_dir=project)
    assert fired.refused, fired.stdout
    assert "smuggled.py" in fired.stderr
    assert "caught after the fact rather than blocked" in fired.stderr


def test_a_clean_corpus_survives_the_after_the_fact_scan(
    fire: Callable[..., Any], project: Path
) -> None:
    (project / "corpus" / "world" / "generator.py").write_text(CLEAN, encoding="utf-8")
    event = {
        "hook_event_name": "PostToolUse",
        "cwd": str(project),
        "tool_name": "Bash",
        "tool_input": {"command": "ls"},
    }
    fired = fire(HOOK, event, project_dir=project)
    assert fired.code == 0, fired.stderr


def test_it_fails_open_on_input_it_cannot_read(fire: Callable[..., Any], project: Path) -> None:
    """A hook that dies on malformed input takes the session's editing with it.

    The test and CI are still the gate. Failing open here costs a turn; failing closed costs
    the session, and a hook that has to be disabled to get work done is a hook that gets
    disabled.
    """
    fired = fire(HOOK, "not json at all", project_dir=project)
    assert fired.code == 0, fired.stderr
