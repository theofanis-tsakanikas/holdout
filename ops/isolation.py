"""The corpus barrier: no module under `corpus/` may import `holdout`.

CLAUDE.md states it for `corpus/world/` and gives the reason — a generator sharing a
"compute margin" function with the estimator would cancel a bug in it and both would agree on
a wrong number. `tests/boundary/test_corpus_imports_nothing.py` has enforced it since the
corpus arrived, and it polices the whole of `corpus/` rather than `corpus/world/` alone,
because `corpus/real/` is the independent evidence claim 1 attacks the gates *from*.

This module exists so the barrier has **one** implementation. It is called from two places
that run at two different moments:

- the boundary test, after the fact, on every push;
- `.claude/hooks/corpus_isolation.py`, before the write lands.

Two hand-written copies of the same rule drift, and the copy that drifts is the one nobody
reads. Stdlib only, so the hook can run under a bare `python3` with no virtualenv.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

#: The system the corpus must not be able to see. Not `src.holdout` — the corpus would import
#: it by its installed name.
FORBIDDEN = "holdout"

#: Where the barrier applies, relative to the repository root.
POLICED = "corpus"

# The text fallback below is *only* for source that does not parse. That is the ordinary case
# for an editing hook, which is handed a fragment — an indented block out of the middle of a
# function — rather than a module. A fragment that happens to parse is checked by the AST like
# anything else; the fallback never gets the chance to be laxer than the real check.
_TEXT_IMPORT = re.compile(
    rf"^[ \t]*(?:"
    rf"from[ \t]+(?P<from>{FORBIDDEN}(?:\.[A-Za-z_]\w*)*)[ \t]+import\b"
    rf"|import[ \t]+(?P<plain>{FORBIDDEN}(?:\.[A-Za-z_]\w*)*)(?![\w.])"
    rf")",
    re.MULTILINE,
)


def _is_forbidden(module: str) -> bool:
    return module == FORBIDDEN or module.startswith(f"{FORBIDDEN}.")


def _by_ast(tree: ast.AST) -> list[str]:
    offences: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            offences += [alias.name for alias in node.names if _is_forbidden(alias.name)]
        elif isinstance(node, ast.ImportFrom) and node.module and _is_forbidden(node.module):
            offences.append(node.module)
    return offences


def _by_text(source: str) -> list[str]:
    return [m.group("from") or m.group("plain") for m in _TEXT_IMPORT.finditer(source)]


def offences(source: str, *, filename: str = "<source>") -> list[str]:
    """Every import of `holdout` in `source`, named as it is written.

    Checked by reading rather than by importing, for two reasons that have not changed since
    the boundary test was written. An import test only catches a *module-level* import, and
    the dangerous one is the local import inside a function that somebody added in a hurry.
    And a `corpus` module that imported `holdout` successfully would leave the test passing
    while the barrier was gone.
    """
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        return _by_text(source)
    return _by_ast(tree)


def is_policed(path: Path, *, root: Path) -> bool:
    """Does the barrier apply to `path`? Only Python, only under `corpus/`.

    `path` need not exist: the hook asks about a file the write has not created yet.
    """
    if path.suffix != ".py":
        return False
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return relative.parts[:1] == (POLICED,)


def scan(root: Path) -> dict[Path, list[str]]:
    """Every policed file on disk that breaks the barrier, mapped to what it imports.

    This is the exact check, over complete files. The hook runs it after a `Bash` call, which
    can write a file by a route no editing tool ever reports.
    """
    found: dict[Path, list[str]] = {}
    for module in sorted((root / POLICED).rglob("*.py")):
        broken = offences(module.read_text(encoding="utf-8"), filename=str(module))
        if broken:
            found[module] = broken
    return found


REFUSAL = (
    "{where} imports {what}. The corpus is the independent evidence the claims are attacked "
    "with; the moment it can see the system it is attacking, it starts agreeing with it. A "
    "generator that shared a 'compute margin' function with the estimator would cancel a bug "
    "in it and both would agree on a wrong number. The join belongs in evals/, not here."
)
