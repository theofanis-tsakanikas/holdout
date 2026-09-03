"""`pyarrow` is read with, never written with: no runtime module may import it.

`corpus/world/parquet.py` writes Parquet with the standard library, and the reason it is
allowed to be ours is that something nobody here wrote checks it — pyarrow, in the dev group,
in `tests/`. **That argument survives only while the dependency stays on the test side.** The
day a module under `src/`, `corpus/`, `evals/`, `ops/` or `pipelines/` imports pyarrow, the
writer is checked by a library the code also depends on, `dependencies = []` stops being the
runtime's true answer, and 122 MB has entered the estate through a test fixture.

**The population, stated as a rule.** Every `*.py` under the directories the Makefile lints —
`PYTHON_DIRS` — minus `tests/`, walked from disk rather than asked of git, so a module written
five minutes ago and not yet added is inside the population rather than outside it.

This is the same shape as `tests/boundary/test_corpus_imports_nothing.py` and deliberately not
the same implementation: `ops/isolation.py` is the corpus barrier's one copy, it is imported by
a hook that must run under a bare `python3`, and widening it to take a forbidden root as an
argument would put a second caller's needs inside a guarantee. Two rules, two files, and the
duplication is eleven lines of AST walk.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

FORBIDDEN = "pyarrow"

REPO_ROOT = Path(__file__).resolve().parents[2]

#: The linted directories, minus the one place the import belongs. `.claude/hooks` is in the
#: population because a hook is a guarantee and runs with no virtualenv at all.
POLICED = ("src", "evals", "corpus", "ops", "pipelines", ".claude/hooks")


def _imports(source: str, filename: str) -> list[str]:
    found: list[str] = []
    for node in ast.walk(ast.parse(source, filename=filename)):
        if isinstance(node, ast.Import):
            found += [alias.name for alias in node.names if _is_forbidden(alias.name)]
        elif isinstance(node, ast.ImportFrom) and node.module and _is_forbidden(node.module):
            found.append(node.module)
    return found


def _is_forbidden(module: str) -> bool:
    return module == FORBIDDEN or module.startswith(f"{FORBIDDEN}.")


def _modules() -> list[Path]:
    return sorted(
        path
        for directory in POLICED
        for path in (REPO_ROOT / directory).rglob("*.py")
        if ".venv" not in path.parts
    )


def test_there_are_modules_to_police() -> None:
    """A barrier over an empty walk passes vacuously and says nothing at all."""
    modules = _modules()
    assert len(modules) > 100, f"the walk found {len(modules)} modules, which is not this tree"


def test_the_detector_fires_on_the_thing_it_is_looking_for() -> None:
    """The instrument, before its result. `make language` learned this the expensive way."""
    for source in (
        f"import {FORBIDDEN}",
        f"import {FORBIDDEN}.parquet as pq",
        f"from {FORBIDDEN} import parquet",
        f"from {FORBIDDEN}.parquet import read_table",
        f"def f():\n    import {FORBIDDEN}\n",
    ):
        assert _imports(source, "<planted>"), source
    assert not _imports("import pyarrowish\nfrom corpus.world import parquet\n", "<clean>")


@pytest.mark.parametrize("module", _modules(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_runtime_module_imports_pyarrow(module: Path) -> None:
    offences = _imports(module.read_text(encoding="utf-8"), str(module))
    assert not offences, (
        f"{module.relative_to(REPO_ROOT)} imports {offences}. pyarrow is the independent "
        "reader corpus/world/parquet.py is checked by; a runtime module importing it makes "
        "the writer and its check one dependency again."
    )
