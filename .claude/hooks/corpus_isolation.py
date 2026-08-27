#!/usr/bin/env python3
"""The corpus barrier, enforced by the harness instead of by a test that runs afterwards.

`tests/boundary/test_corpus_imports_nothing.py` is the gate: it goes red on every push and
`main` cannot take a violation. But it runs *after* the write, which means a session can build
on top of a broken barrier for an hour and find out at the end. CLAUDE.md's rule for where the
AI layer lives says a thing that must never happen is a hook, and this is that thing.

Two events, because a file can be written by two very different routes:

**PreToolUse** on the editing tools sees the content before it lands and refuses it. What an
`Edit` hands over is a *fragment*, not a module, and a fragment read on its own is read badly:
an indented block does not parse, an import after a semicolon is invisible to the textual
fallback, and a line inside a docstring looks exactly like code. So the fragment is not read
on its own — the file is read from disk and the edit applied to a copy of it, and what gets
checked is the module the write would actually produce. Only when there is no file to read
from does the fragment get judged alone.

**PostToolUse** on `Bash` re-reads `corpus/` from disk. A heredoc, a `sed -i`, a `git
checkout` of somebody else's branch and a code generator all write files without any editing
tool reporting a `file_path`, and a Pre-only hook would be blind to every one of them. It
cannot un-write the file — nothing at PostToolUse can — so it is not the guarantee; it is what
makes the violation impossible to miss in the same turn that created it.

The two together are still not the gate. The gate is the test, and it stays.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ops.isolation import REFUSAL, is_policed, offences, scan

#: The tool that hands over a whole file. `Edit` and `MultiEdit` hand over fragments and are
#: reconstructed instead; see `_proposed_content`.
#:
#: `NotebookEdit` is deliberately absent. `is_policed` covers `*.py` only — which is what the
#: gate behind this hook covers — so a notebook was never policed, and listing the tool here
#: was wiring that could not fire. Advertising a guarantee that cannot run is worse than not
#: having it.
_WHOLE_FILE = {"Write": "content"}


def _project_root(event: dict[str, object]) -> Path:
    declared = os.environ.get("CLAUDE_PROJECT_DIR")
    if declared:
        return Path(declared)
    cwd = event.get("cwd")
    return Path(cwd) if isinstance(cwd, str) else Path.cwd()


def _edits(tool_input: dict[str, object]) -> list[tuple[str, str, bool]]:
    """Every (old, new, replace_all) this call would apply, `Edit` and `MultiEdit` alike."""
    listed = tool_input.get("edits")
    raw = listed if isinstance(listed, list) else [tool_input]
    out: list[tuple[str, str, bool]] = []
    for edit in raw:
        if not isinstance(edit, dict):
            continue
        old, new = edit.get("old_string"), edit.get("new_string")
        if isinstance(old, str) and isinstance(new, str):
            out.append((old, new, bool(edit.get("replace_all"))))
    return out


def _proposed_content(tool_name: str, tool_input: dict[str, object], target: Path) -> list[str]:
    """The module this call would produce, or — failing that — the fragments it would insert.

    Reconstructing the file is what makes an `Edit` exact: the AST then sees the edit in its
    real context, so an import after a semicolon is caught and a line inside a docstring is
    not mistaken for one. It falls back to the fragments only when there is no file on disk to
    apply them to, which is the case that does not arise for an `Edit`.
    """
    field = _WHOLE_FILE.get(tool_name)
    if field is not None:
        value = tool_input.get(field)
        return [value] if isinstance(value, str) else []

    edits = _edits(tool_input)
    if not edits:
        return []
    try:
        content = target.read_text(encoding="utf-8")
    except OSError:
        return [new for _, new, _ in edits]
    for old, new, everywhere in edits:
        if old not in content:
            return [new for _, new, _ in edits]
        content = content.replace(old, new) if everywhere else content.replace(old, new, 1)
    return [content]


def _refuse(message: str) -> None:
    """Exit 2: at PreToolUse this blocks the call, at PostToolUse it goes back to Claude."""
    sys.stderr.write(f"corpus_isolation: {message}\n")
    raise SystemExit(2)


def _pre(event: dict[str, object], root: Path) -> None:
    tool_name = event.get("tool_name")
    tool_input = event.get("tool_input")
    if not isinstance(tool_name, str) or not isinstance(tool_input, dict):
        return
    file_path = tool_input.get("file_path")
    if not isinstance(file_path, str):
        return
    target = Path(file_path)
    if not target.is_absolute():
        target = root / target
    if not is_policed(target, root=root):
        return
    for text in _proposed_content(tool_name, tool_input, target):
        broken = offences(text, filename=file_path)
        if broken:
            _refuse(REFUSAL.format(where=file_path, what=broken))


def _post(root: Path) -> None:
    found = scan(root)
    if not found:
        return
    lines = [
        REFUSAL.format(where=path.relative_to(root), what=broken) for path, broken in found.items()
    ]
    lines.append(
        "This was written by a route no editing tool reported, so it was caught after the "
        "fact rather than blocked. Revert it before building anything on top of it."
    )
    _refuse("\n".join(lines))


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        # A hook that dies on malformed input takes the session's editing with it. The test
        # and CI are still the gate; failing open here costs a turn, failing closed costs
        # the whole session.
        return 0
    if not isinstance(event, dict):
        return 0
    root = _project_root(event)
    if not (root / "corpus").is_dir():
        return 0
    if event.get("hook_event_name") == "PostToolUse":
        _post(root)
    else:
        _pre(event, root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
