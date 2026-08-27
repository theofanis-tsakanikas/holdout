"""No module under `corpus/` may import `holdout`. The whole of claim 1's independence.

`tests/boundary/test_core_imports_nothing.py` keeps the cloud out of the core. This is the
mirror of it, pointing the other way: it keeps the *system* out of the data that is supposed
to be independent of the system.

CLAUDE.md states the barrier for `corpus/world/` and gives the reason — a generator sharing a
"compute margin" function with the estimator would cancel a bug in it and both would agree on
a wrong number. The same argument applies a sentence earlier to `corpus/real/`: a corpus that
can reach the gates it exists to attack has stopped being an independent corpus, and it would
stop being one gradually, by the ordinary drift of whoever is editing both.

**The rule itself lives in `ops.isolation`, and this test is one of its two callers.** The
other is `.claude/hooks/corpus_isolation.py`, which refuses the write before it lands. Two
hand-written copies of one rule drift, and the copy that drifts is the one nobody reads — so
there is one copy, called at two moments. This test is the gate: it runs on every push and
`main` cannot take a violation. The hook is the convenience that stops a session building for
an hour on top of a barrier that is already gone.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from pathlib import Path

import pytest
from ops.isolation import FORBIDDEN, POLICED, REFUSAL, offences
from ops.isolation import _by_text as by_text_only

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS = REPO_ROOT / POLICED


def _modules() -> list[Path]:
    return sorted(CORPUS.rglob("*.py"))


def test_the_corpus_directory_has_modules_to_police() -> None:
    """A barrier over an empty directory is a barrier that has never been tested."""
    assert _modules(), f"{POLICED}/ contains no Python at all — this test would pass vacuously"


@pytest.mark.parametrize("module", _modules(), ids=lambda p: str(p.relative_to(CORPUS)))
def test_no_corpus_module_imports_the_system(module: Path) -> None:
    broken = offences(module.read_text(encoding="utf-8"), filename=str(module))
    assert not broken, REFUSAL.format(where=module.relative_to(CORPUS), what=broken)


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(f"import {FORBIDDEN}", id="plain"),
        pytest.param(f"import {FORBIDDEN}.core.ladder as ladder", id="submodule, aliased"),
        pytest.param(f"from {FORBIDDEN} import core", id="from the package"),
        pytest.param(f"from {FORBIDDEN}.core.guardrails import Envelope", id="from deep inside"),
        pytest.param(f"def f():\n    import {FORBIDDEN}\n", id="inside a function"),
        pytest.param(f"if True:\n    from {FORBIDDEN} import core\n", id="inside a branch"),
        pytest.param(
            f"try:\n    import {FORBIDDEN}\nexcept ImportError:\n    pass\n", id="in a try"
        ),
    ],
)
def test_the_barrier_catches_every_shape_of_the_import(source: str) -> None:
    """The barrier is the evidence; evidence that has never been shown to bite is a claim.

    The local import inside a function is the one that matters. An import test would miss it
    entirely — it only ever sees module level — which is why this reads the source instead.

    **`src.holdout` is here because it works.** `src/` is an implicit namespace package and the
    repository root is on `sys.path` under `uv run` and under pytest, so
    `from src.holdout.core.guardrails import Envelope` imports and runs — and it is the
    spelling that matches the path on disk, which makes it the one somebody reaches for. The
    first version of this barrier looked for the installed name only, and carried a comment
    explaining that the other spelling would not be used.
    """
    assert offences(source), source


@pytest.mark.parametrize(
    "source",
    [
        pytest.param("import holdouts", id="a package whose name merely starts the same"),
        pytest.param("from holdout_extras import x", id="and another"),
        pytest.param("import random\nfrom pathlib import Path\n", id="the ordinary imports"),
        pytest.param('"""A docstring that says import holdout."""', id="the words, in prose"),
        pytest.param("# import holdout\n", id="the words, commented out"),
        pytest.param("import srcs.holdout", id="a `src`-ish prefix that is not `src`"),
        pytest.param("from source import holdout", id="and another"),
        pytest.param(
            'def f():\n    """The rule:\n\n    import holdout.core\n    """\n    return 1\n',
            id="the words inside an indented docstring",
        ),
    ],
)
def test_the_barrier_does_not_catch_what_it_should_not(source: str) -> None:
    """A barrier that fires on `# import holdout` gets widened until it stops firing at all."""
    assert not offences(source), source


@pytest.mark.parametrize(
    ("source", "caught"),
    [
        pytest.param(f"import {FORBIDDEN}", True, id="at the start of a line"),
        pytest.param(f"import src.{FORBIDDEN}", True, id="the path spelling too"),
        pytest.param(f"    from {FORBIDDEN} import core", True, id="indented"),
        pytest.param(f"x = 1; import {FORBIDDEN}", False, id="after a semicolon — it cannot see"),
        pytest.param(f"    import {FORBIDDEN}.core", True, id="indented, submodule"),
    ],
)
def test_the_text_scan_is_exercised_in_both_directions(source: str, caught: bool) -> None:
    """The last resort has its own tests, because every source above parses.

    Twelve parsing sources all take the AST path, so `_by_text` could be deleted outright and
    the parametrisations above would stay green. It is reached only when a fragment survives
    both `ast.parse` and `ast.parse(dedent(...))`, and what it cannot do — see an import after
    a semicolon — is asserted here rather than discovered by whoever hits it.
    """
    assert bool(by_text_only(source)) is caught, source


def test_every_corpus_module_imports_with_the_system_absent(
    block_imports: Callable[..., None],
) -> None:
    """The dynamic half, which reading the source cannot see.

    Everything above this line reads text, and `.claude/README.md` states the hole that leaves:
    *"`corpus_isolation` reads imports, not behaviour. `importlib.import_module("holdout")` is
    invisible to it."* It is invisible to `offences` for the same reason — there is no `Import`
    node to find.

    So this closes the module-level half of it from the other side: every module under
    `corpus/` is imported with `holdout` unreachable through `sys.meta_path`, which is the
    level every import mechanism goes through. A dynamic import taken at import time raises
    here, whatever it was spelled as. The first version of this test blocked
    `builtins.__import__` instead and **did not catch the case it was written for** — see
    `tests/boundary/conftest.py` and `test_blocking.py`.

    **What it still does not catch, and the reason the source scan stays.** A dynamic import
    *inside a function* never runs during import, so nothing here executes it — which is
    exactly the case the text scan was written for, pointing the other way. Neither check
    subsumes the other, and this file needs both.
    """
    block_imports(FORBIDDEN, evict=(POLICED,))
    names = [
        f"{POLICED}." + str(path.relative_to(CORPUS).with_suffix("")).replace("/", ".")
        for path in _modules()
    ]
    names = [name.removesuffix(".__init__") for name in names]
    assert len(names) >= 10, "too few corpus modules for this to be worth asserting"
    for name in sorted(set(names)):
        importlib.import_module(name)
