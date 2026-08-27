#!/usr/bin/env python3
"""The corpus barrier, enforced by the harness instead of by a test that runs afterwards.

`tests/boundary/test_corpus_imports_nothing.py` is the gate: it goes red on every push and
`main` cannot take a violation. But it runs *after* the write, which means a session can build
on top of a broken barrier for an hour and find out at the end. CLAUDE.md's rule for where the
AI layer lives says a thing that must never happen is a hook, and this is that thing.

Two events, because a file can be written by two very different routes:

**PreToolUse** on the editing tools sees the content before it lands and refuses it. What it
is handed is sometimes a fragment rather than a module — an indented block out of the middle
of a function — so `ops.isolation` falls back to a textual read when the fragment does not
parse.

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

#: Every tool that hands over the content it is about to write, and the field it arrives in.
#: `Edit` and `MultiEdit` hand over a fragment; see the module docstring.
_CONTENT_FIELDS = {
    "Write": ("content",),
    "Edit": ("new_string",),
    "NotebookEdit": ("new_source",),
}


def _project_root(event: dict[str, object]) -> Path:
    declared = os.environ.get("CLAUDE_PROJECT_DIR")
    if declared:
        return Path(declared)
    cwd = event.get("cwd")
    return Path(cwd) if isinstance(cwd, str) else Path.cwd()


def _proposed_content(tool_name: str, tool_input: dict[str, object]) -> list[str]:
    """The text this call would put into the file, from whichever field carries it."""
    texts: list[str] = []
    for field in _CONTENT_FIELDS.get(tool_name, ()):
        value = tool_input.get(field)
        if isinstance(value, str):
            texts.append(value)
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        texts += [e["new_string"] for e in edits if isinstance(e, dict) and "new_string" in e]
    return texts


def _refuse(message: str) -> None:
    """Exit 2: at PreToolUse this blocks the call, at PostToolUse it goes back to Claude."""
    sys.stderr.write(f"corpus_isolation: {message}\n")
    raise SystemExit(2)


def _pre(event: dict[str, object], root: Path) -> None:
    tool_name = event.get("tool_name")
    tool_input = event.get("tool_input")
    if not isinstance(tool_name, str) or not isinstance(tool_input, dict):
        return
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not isinstance(file_path, str):
        return
    target = Path(file_path)
    if not target.is_absolute():
        target = root / target
    if not is_policed(target, root=root):
        return
    for text in _proposed_content(tool_name, tool_input):
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
