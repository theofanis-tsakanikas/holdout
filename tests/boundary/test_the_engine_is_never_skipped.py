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
#: not its package name — a rule written from `pyproject.toml` would have missed it.
ENGINES: tuple[str, ...] = ("pyspark", "delta", "deltalake")

#: The two spellings pytest offers for turning an absent import into a green run.
SKIP_CALLS: tuple[str, ...] = ("importorskip", "skipif", "skip")


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


@pytest.mark.parametrize("module", _modules(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_test_turns_an_absent_engine_into_a_skip(module: Path) -> None:
    broken = offences(module.read_text(encoding="utf-8"), str(module))
    assert not broken, (
        f"{module.relative_to(REPO_ROOT)}: {broken}. An engine this repository declares in an "
        "optional group must be absent loudly — a plain import errors the collection, and that "
        "is the behaviour these two spellings would turn into a green run."
    )
