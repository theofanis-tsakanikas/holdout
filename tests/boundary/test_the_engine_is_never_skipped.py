"""A test that cannot import its engine must fail. It may never skip.

`T010` puts Spark in an optional dependency group, so silver's tests run in one CI job and on a
laptop that asked for the group — and nowhere else. **That is the arrangement this file exists
to make safe.** A test whose engine is missing has two ways to behave and only one of them is
honest:

    import pyspark                        collection ERROR, pytest exit 2 — loud
    pytest.importorskip("pyspark")        "1 skipped", and inside the suite that is a green run

Both were measured in this repository on 2026-09-03, on a machine with no Spark. **The first is
what an absent engine does by default; the second is what one line turns it into**, and the
second is `CLAUDE.md`'s own defect — *a declared thing that never runs* — arriving through a
missing package rather than a missing target. A skipped test looks exactly like a passing one in
`1251 passed`, and nobody reads the skip count.

**The property is red-rather-than-green, not import-at-module-scope**, and CI taught the
difference the hard way. `tests/pipelines/test_silver.py` first imported the engine at the top,
and `gate` went red with `ModuleNotFoundError` at **collection** — because pytest collects every
module before it applies a mark expression, so `make test` could not run at all on a machine
without the extra. The engine's imports moved inside the functions that need them, which keeps
an absent engine an **error at the first test that asks for it** and lets the suite collect. That
is the property intact; a `skipif` there would not be. Verified on this machine with the extra
removed: `make check` green, `make silver` red with `ModuleNotFoundError: No module named
'delta'`.

**So this is the guard, and it is written before the tests it guards exist.** A guard added after
them is a guard whose absence was never demonstrated: with silver already written and passing on
a machine that has Spark, nothing distinguishes *the guard works* from *nobody has skipped yet*.

**The population, stated as a rule.** Every `*.py` under `tests/`, walked from disk rather than
asked of git, so a test written five minutes ago and not yet added is inside it.

**What it does not cover.** A test that catches `ImportError` itself and returns early, or one
that asserts nothing when the engine is absent — both are skips written longhand, and neither is
visible to this walk. The rule is enforceable on the two spellings pytest offers and stated as
narrower than the property it protects, which is the honest half: **the property is that an
absent engine is loud, and this checks the two ways of making it quiet that a person actually
reaches for.**
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Where the rule applies. `tests/` and nothing else: a skip in `evals/` would be a different
#: defect, and `evals/` does not import an engine.
POLICED = "tests"

#: The engines an optional group may withhold. `delta` is `delta-spark`'s import name, which is
#: not its package name — a rule written from `pyproject.toml` would have missed it, and `dbt`
#: makes the point twice: `dbt-core` and `dbt-spark` both import as `dbt`.
#:
#: **`dbt` arrived here after `gate` went red for the module it names.** `T011` put dbt in an
#: optional extra and this list did not learn about it, so the two spellings below were policed
#: for three engines and not for the fourth. Nothing had used either spelling, so nothing was
#: broken — the guard was simply blind, which is the state that looks most like coverage.
#:
#: **`deltalake` is in no extra, is installed nowhere, and is policed anyway — deliberately.**
#: Those three facts are checkable; why it was first written here is not recorded, so this is
#: `T011`'s argument for keeping it rather than a claim about what `T010` meant. `deltalake` is
#: delta-rs, the **JVM-free** way to read a Delta table, and that is exactly what somebody
#: reaching past the `spark` extra's 713 MB and its Java runtime would reach for. An
#: `importorskip("deltalake")` would arrive *because* it looks cheap, and it is the same defect
#: as the other three: a test that goes green when its engine is absent. **A name nothing
#: imports reads as dead**, so it is written down here that it is not — the entry is guarding a
#: door nobody has opened yet, which is the only useful moment to guard one.
ENGINES: tuple[str, ...] = ("pyspark", "delta", "deltalake", "dbt")

#: The two spellings pytest offers for turning an absent import into a green run.
SKIP_CALLS: tuple[str, ...] = ("importorskip", "skipif", "skip")

#: The guard `if TYPE_CHECKING:` puts around an import that never executes. An engine imported
#: there costs nothing at collection and is the one module-level spelling that is safe.
TYPE_ONLY = "TYPE_CHECKING"


def _mentions_engine(text: str) -> bool:
    return any(engine in text for engine in ENGINES)


def _called_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    if isinstance(node.func, ast.Name):
        return node.func.id
    return None


def offences(source: str, filename: str) -> list[str]:
    """Every skip-shaped call in `source` that names an engine, by line.

    Read from the source segment rather than from the call's arguments, because the engine can
    arrive as `importlib.util.find_spec("pyspark")` inside a `skipif` condition and an argument
    walk that looked only for string literals would miss it — which is the same defect as a
    guard tested on the shape its author pictured.
    """
    tree = ast.parse(source, filename=filename)
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _called_name(node)
        if name not in SKIP_CALLS:
            continue
        segment = ast.get_source_segment(source, node) or ""
        if _mentions_engine(segment):
            found.append(f"line {node.lineno}: {name}(...) naming an engine")
    return found


def _module_level(tree: ast.Module) -> list[ast.stmt]:
    """Every statement that runs when the module is imported, function bodies excluded.

    Class bodies **are** included: they execute at import time like any other top-level code.
    A `if TYPE_CHECKING:` block is excluded, because it never executes at all — which is the
    one module-level spelling of an engine import that costs nothing at collection, and the
    one this repository's own silver tests use for their type annotations.
    """
    found: list[ast.stmt] = []

    def walk(body: list[ast.stmt]) -> None:
        for node in body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if isinstance(node, ast.If) and TYPE_ONLY in ast.dump(node.test):
                continue
            found.append(node)
            for field in ("body", "orelse", "finalbody"):
                nested = getattr(node, field, None)
                if isinstance(nested, list):
                    walk([item for item in nested if isinstance(item, ast.stmt)])

    walk(tree.body)
    return found


def imported_at_module_scope(source: str, filename: str) -> list[str]:
    """Every engine imported where **collection** will run it, which is the other direction.

    **The guard above refuses a silent green; this refuses a loud red in the wrong place.**
    pytest imports every test module before it applies a mark expression, so a mark cannot
    isolate an environment — only an import site can. A module-level `import pyspark` here makes
    `make test` fail on every machine without the `spark` extra, which is every machine except
    the one CI job that installs it: measured, on run `33737357923`, as
    `ModuleNotFoundError: No module named 'pyspark'` at collection with `gate` red.

    **Same boundary, two directions, and only one of them was guarded first.** The skip
    direction had a story behind it — an engine in an optional group is exactly where somebody
    reaches for `importorskip` — so it was written before silver existed. This direction had no
    story, and the failure lay along it.
    """
    tree = ast.parse(source, filename=filename)
    found: list[str] = []
    for node in _module_level(tree):
        if isinstance(node, ast.Import):
            found += [
                f"line {node.lineno}: import {alias.name} at module scope"
                for alias in node.names
                if _is_engine(alias.name)
            ]
        elif isinstance(node, ast.ImportFrom) and node.module and _is_engine(node.module):
            found.append(f"line {node.lineno}: from {node.module} import ... at module scope")
    return found


def _is_engine(module: str) -> bool:
    return any(module == engine or module.startswith(f"{engine}.") for engine in ENGINES)


def _modules() -> list[Path]:
    return sorted(
        path for path in (REPO_ROOT / POLICED).rglob("*.py") if "__pycache__" not in path.parts
    )


def test_there_are_tests_to_police() -> None:
    """A walk that found nothing passes vacuously, which is the shape this file is about."""
    modules = _modules()
    assert len(modules) > 30, f"the walk found {len(modules)} test modules, which is not this tree"


@pytest.mark.parametrize(
    "source",
    [
        pytest.param('import pytest\npytest.importorskip("pyspark")\n', id="importorskip"),
        pytest.param('from pytest import importorskip\nimportorskip("delta")\n', id="imported"),
        pytest.param(
            'import pytest\n\n\n@pytest.mark.skipif(not have("pyspark"), reason="no engine")\n'
            "def test_x() -> None:\n    pass\n",
            id="skipif on a helper",
        ),
        pytest.param(
            "import importlib.util\nimport pytest\n\n\n"
            '@pytest.mark.skipif(\n    importlib.util.find_spec("pyspark") is None, reason="x"\n)\n'
            "def test_x() -> None:\n    pass\n",
            id="skipif on find_spec",
        ),
        pytest.param(
            'import pytest\n\n\ndef test_x() -> None:\n    pytest.skip("no pyspark here")\n',
            id="an outright skip",
        ),
        # The fourth engine, planted the day it entered `ENGINES`. A list that grew without a
        # case proving the new entry is policed is a list somebody widened on paper.
        pytest.param('import pytest\npytest.importorskip("dbt")\n', id="dbt importorskip"),
    ],
)
def test_the_detector_fires_on_the_thing_it_is_looking_for(source: str) -> None:
    """The instrument answers for itself before its result is trusted."""
    assert offences(source, "<planted>"), source


def test_the_detector_leaves_an_ordinary_skip_alone() -> None:
    """A skip that names no engine is somebody's business and not this rule's."""
    assert not offences(
        'import pytest\n\n\n@pytest.mark.skipif(WINDOWS, reason="posix only")\n'
        "def test_x() -> None:\n    pass\n",
        "<clean>",
    )
    assert not offences("import pyspark\n\n\ndef test_x() -> None:\n    pass\n", "<import>")


@pytest.mark.parametrize(
    "source",
    [
        pytest.param("import pyspark\n", id="plain"),
        pytest.param("from pyspark.sql import functions as sf\n", id="from"),
        pytest.param("import delta\n\n\ndef test_x() -> None:\n    pass\n", id="beside a test"),
        pytest.param(
            "try:\n    import pyspark\nexcept ImportError:\n    pyspark = None\n", id="in a try"
        ),
        pytest.param("class Fixtures:\n    import pyspark\n", id="in a class body"),
        pytest.param("from dbt.cli.main import dbtRunner\n", id="dbt at module scope"),
    ],
)
def test_the_module_scope_detector_fires(source: str) -> None:
    assert imported_at_module_scope(source, "<planted>"), source


def test_an_import_that_never_executes_is_left_alone() -> None:
    """`if TYPE_CHECKING:` costs nothing at collection, and silver's own tests rely on it."""
    assert not imported_at_module_scope(
        "from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n"
        "    from pyspark.sql import DataFrame\n",
        "<clean>",
    )
    assert not imported_at_module_scope(
        "def test_x() -> None:\n    import pyspark\n\n    assert pyspark\n", "<inside>"
    )


@pytest.mark.parametrize("module", _modules(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_test_imports_an_engine_where_collection_will_run_it(module: Path) -> None:
    broken = imported_at_module_scope(module.read_text(encoding="utf-8"), str(module))
    assert not broken, (
        f"{module.relative_to(REPO_ROOT)}: {broken}. pytest imports every module before it "
        "applies a mark expression, so this breaks `make test` on every machine without the "
        "`spark` extra — which is every machine except the one CI job that installs it."
    )


@pytest.mark.parametrize("module", _modules(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_test_turns_an_absent_engine_into_a_skip(module: Path) -> None:
    broken = offences(module.read_text(encoding="utf-8"), str(module))
    assert not broken, (
        f"{module.relative_to(REPO_ROOT)}: {broken}. An engine this repository declares in an "
        "optional group must be absent loudly — a plain import errors the collection, and that "
        "is the behaviour these two spellings would turn into a green run."
    )


def _mypy_ignored_modules() -> set[str]:
    """Every module `pyproject.toml` tells mypy it may not find, as bare import names.

    Read out of the file rather than restated here, for the reason `ops/figures.py` gives about
    `ci.yml`'s discovery pattern: a second copy would agree with itself on the day it was
    written.
    """
    import tomllib

    settings = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    ignored: set[str] = set()
    for override in settings["tool"]["mypy"]["overrides"]:
        if not override.get("ignore_missing_imports"):
            continue
        modules = override["module"]
        ignored.update(
            m.removesuffix(".*") for m in ([modules] if isinstance(modules, str) else modules)
        )
    return ignored


def test_every_engine_is_ignorable_by_mypy() -> None:
    """**The third list, and it is the one that went red on a runner.**

    Three hand-kept lists name the packages this tree may not have: the extras in
    `pyproject.toml`, `ENGINES` above, and mypy's `ignore_missing_imports` overrides. `T011`
    added a fourth engine and had to edit all three; **only the third said anything, and it said
    it on CI after a green local `make check`** — because both extras were installed on the
    laptop, which is the one environment where a missing override cannot fail.

    mypy resolves imports **statically**, so it needs the package or an override. Without one,
    `make typecheck` fails on every machine that has not installed the extra, which is every
    machine except the single CI job that does.

    **This compares the second list against the third, which is the direction that needs no
    package-to-module mapping.** Deriving either from the extras is what `ENGINES`' own comment
    refuses: `delta-spark` imports as `delta` and both dbt distributions import as `dbt`, so a
    rule written from the packaging would be wrong about three of four names.
    """
    ignored = _mypy_ignored_modules()
    assert ignored, "pyproject.toml declares no ignorable modules, so this compares against nothing"
    missing = sorted(engine for engine in ENGINES if engine not in ignored)
    assert not missing, (
        f"{missing} may be withheld by an optional extra and mypy is not told to ignore it, so "
        "`make typecheck` fails on every machine without that extra — which is every machine "
        "except the one CI job that installs it. Add it to [[tool.mypy.overrides]]."
    )
