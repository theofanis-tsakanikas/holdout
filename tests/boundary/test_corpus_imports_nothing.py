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

from pathlib import Path

import pytest
from ops.isolation import FORBIDDEN, POLICED, REFUSAL, offences

CORPUS = Path(__file__).resolve().parents[2] / POLICED


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
    ],
)
def test_the_barrier_does_not_catch_what_it_should_not(source: str) -> None:
    """A barrier that fires on `# import holdout` gets widened until it stops firing at all."""
    assert not offences(source), source
