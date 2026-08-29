"""The measuring instrument for claim 4, measured.

Claim 4's eval is evidence, and evidence held to a lower standard than the code it judges
stops being evidence. Three things are asserted here, and each is written against a defect
that was found rather than one imagined:

* **the eval may not read the simulator's shape.** The whole claim rests on the corrector
  learning an intraday shape from data rather than being handed the one that produced it, and
  a single import would end that quietly. The rule is an **exclusion list**, because the
  version of this idea in `tests/evals/test_guardrail_instrument.py` began as an inclusion
  list and the branch that wrote it added a module the rule could not see;
* **the published figures are pinned**, so a change that merges two counts or moves a
  boundary is red in the suite rather than wrong in a paragraph;
* **the shape the corpus actually reaches is pinned**, because a first draft of `checks.py`
  asserted the opposite from reasoning and was corrected by a mutation crashing on it.
"""

from __future__ import annotations

import ast
from pathlib import Path

from evals.censoring import build, checks

#: The simulator's own model of a shopper: `HOURLY_PROFILE`, the category elasticities, the
#: seasonal swing, the reference-price decay, the basket-size distributions. It is the process
#: that produced the shape claim 4's correction has to learn back out, so an eval that read it
#: — or a core module that did — would be the trap this claim names, arriving one import at a
#: time rather than all at once.
THE_SIMULATOR_S_SHAPE = "corpus.world.demand"

#: Nothing under `src/holdout/` may import the corpus at all. The corpus barrier
#: (`ops/isolation.py`) runs in the other direction; this is the near side of the same wall,
#: and it is asserted here rather than assumed from the packaging.
THE_CORPUS = "corpus"


def _imports(source: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


def _reaches(module: str, root: str) -> bool:
    return module == root or module.startswith(f"{root}.")


def test_the_eval_never_reads_the_simulator_s_own_intraday_shape() -> None:
    """Claim 4's independence, enforced rather than promised.

    The eval legitimately imports `corpus.world` — it has to, that is where the store-days
    come from — and it imports `corpus.world.scale` for the trading hours, which is schema
    rather than behaviour: an hour index means nothing without the window it indexes into.
    What it may never import is `corpus.world.demand`, which is the *generating process*.

    Every module in the package is scanned, found by a glob rather than named, with **no
    exclusions at all**. The moment one is needed it will be a decision somebody has to argue
    for in a diff.

    What it does not cover
    ----------------------
    * `importlib.import_module("corpus.world.demand")`, or any name computed at run time. The
      scan is syntactic, like every scan in this repository;
    * a constant **re-typed** into this package by hand — somebody reading `HOURLY_PROFILE`
      and copying the sixteen numbers in. No import graph can see that, and nothing here can;
    * a shape reached through a module that is allowed. `corpus.world.generate` imports
      `demand`, so `generate.demand.HOURLY_PROFILE` is one attribute away and this rule sees
      only the import line.

    The second is the one to watch, because it is what a *convenience* looks like rather than
    what an evasion looks like. What catches it afterwards is `C5`: a curve that agreed with
    the generator's profile rather than with the held-out days would not beat the naive
    reading by more on a world it was not fitted on.
    """
    package = Path(checks.__file__).parent
    scanned = sorted(package.glob("*.py"))
    assert {path.name for path in scanned} >= {"build.py", "checks.py", "reference.py"}, (
        f"the modules that produce the eval's inputs must be scanned; the glob found "
        f"{[p.name for p in scanned]}"
    )
    offending = [
        f"{path.name} imports {module}"
        for path in scanned
        for module in _imports(path)
        if _reaches(module, THE_SIMULATOR_S_SHAPE)
    ]
    assert not offending, (
        "claim 4's eval reached for the generating process it is supposed to reconstruct "
        "without. A corrector graded against the shape that produced the data is one "
        "function agreeing with itself:\n  " + "\n  ".join(offending)
    )


def test_the_correction_never_imports_the_corpus() -> None:
    """The near side of the corpus barrier, for the module claim 4 is about.

    `ops/isolation.py` refuses `corpus/` importing `holdout`. Nothing refuses `holdout`
    importing `corpus`, because until now nothing in `src/` had any reason to want to. The
    censoring correction is the first module whose independence *from the generator* is the
    claim, so it is asserted here.
    """
    package = Path(__file__).resolve().parents[2] / "src" / "holdout" / "core" / "demand"
    scanned = sorted(package.glob("*.py"))
    assert {path.name for path in scanned} >= {"censoring.py"}, (
        f"the correction must be among the scanned modules; the glob found "
        f"{[p.name for p in scanned]}"
    )
    offending = [
        f"{path.name} imports {module}"
        for path in scanned
        for module in _imports(path)
        if _reaches(module, THE_CORPUS)
    ]
    assert not offending, (
        "the censoring correction imported the corpus that generates the censoring:\n  "
        + "\n  ".join(offending)
    )


def test_the_two_no_evidence_answers_are_counted_apart() -> None:
    """A censored day with no point estimate has two different reasons, and they stay two.

    *No open window at all* is a shelf that was bare before the first sale — there is nothing
    to expand. *Nothing sold before it emptied* is a window that was open and saw no trade —
    there is something to expand and it is zero, which is the one line where the claim's own
    sentence gets violated. Merging the counts would hide which of the two the corpus produces,
    and the corpus produces both in comparable numbers.
    """
    worlds = tuple(checks._measure(days) for days in build.worlds())
    no_window = sum(m.no_window_at_all for m in worlds)
    nothing_sold = sum(m.nothing_sold_in_the_window for m in worlds)
    assert no_window > 0 and nothing_sold > 0, (
        f"both no-evidence branches must be reached: {no_window} with no window, "
        f"{nothing_sold} that sold nothing"
    )
    assert (no_window, nothing_sold) == (26_557, 25_326), (
        "the published no-evidence counts moved. They are pinned so that a change which "
        "merges the two reasons, or moves a boundary, is red here rather than quietly "
        f"different in a paragraph: got {no_window} / {nothing_sold}"
    )


def test_the_corpus_reaches_a_stock_out_before_the_shelf_opened() -> None:
    """Pinned because prose asserted the opposite and the prose was wrong.

    An earlier `checks.py` declared both no-evidence shapes constructible only by the sweep,
    reasoning that a shelf empties by being sold out. W5's heavy-tailed store-day demand
    empties one inside the first trading hour three times in 26,880, having sold up to three
    units — a shape nobody built for this claim, produced by a pathology that exists for
    claim 2. Found by a `gate-proof` mutation reporting `CRASHED`, not by reading anything.
    """
    at_open = {
        world.world: [
            day
            for day in world.ran_out
            if day.state.stocked_out_from_hour == build.WINDOW.open_hour
        ]
        for world in build.worlds()
    }
    assert {name: len(days) for name, days in at_open.items()} == {"W1": 0, "W5": 3, "W6": 0}, (
        f"the corpus's stock-outs at the first trading hour moved: "
        f"{ {name: len(days) for name, days in at_open.items()} }"
    )
    assert all(day.state.units_sold > 0 for days in at_open.values() for day in days), (
        "a store-day that emptied at the first trading hour having sold nothing would make "
        "the two no-evidence branches indistinguishable in the corpus"
    )
