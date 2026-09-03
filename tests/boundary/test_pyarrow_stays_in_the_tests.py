"""`pyarrow` is read with, never written with: no module of ours may import it.

`corpus/world/parquet.py` writes Parquet with the standard library, and the reason it is
allowed to be ours is that something nobody here wrote checks it — pyarrow, in the dev group,
in `tests/`. **That argument survives only while our own code never calls it.**

**Restated when the `spark` extra landed, because half of what this file used to say stopped
being true.** It read *"the day a module imports pyarrow … 122 MB has entered the estate through
a test fixture"*, which argued from the **install**: pyarrow was here only because the tests
asked for it. `pyspark[pipelines]` depends on pyarrow, so in the one environment that has the
`spark` extra, pyarrow is installed whatever this test says. **The install argument is gone and
the real one is untouched**: our Parquet writer must not be checked by a library our own code
also calls, because then the writer and its check share a dependency and the independence that
justified writing the format by hand is spent. That property is about **our modules**, not about
what is on disk, and it is what this file has always actually measured.

A guard whose stated reason has quietly become false is worse than no guard, because it reads as
checked. The prior wording is above rather than deleted, per doctrine rule 4.

**The population, stated as a rule.** Every `*.py` under the directories the Makefile lints —
`PYTHON_DIRS` — minus `tests/`, walked from disk rather than asked of git, so a module written
five minutes ago and not yet added is inside the population rather than outside it. That
includes `pipelines/silver/`, which will import `pyspark`: **importing an engine that depends on
pyarrow is not importing pyarrow**, and the distinction is the whole of what is left to police.

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
        "reader corpus/world/parquet.py is checked by; a module of ours importing it makes "
        "the writer and its check one dependency again — which stays true however pyarrow "
        "came to be installed."
    )
