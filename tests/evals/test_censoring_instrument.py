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
from fractions import Fraction
from pathlib import Path

from evals.censoring import build, checks

from holdout.core.demand.censoring import fit

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


def test_the_fitted_curve_recovers_the_arrival_draw_and_not_the_generator_s_profile() -> None:
    """The independence claim, turned into a number that can go red.

    `evals/censoring/README.md` §2 argues that the curve is learned from emitted units rather than
    being a transformation of a constant the generator holds. Oversight level 2 attacked exactly
    that and the attack failed — but it failed on a *measurement*, so the measurement is pinned
    here rather than left in a paragraph.

    What the curve actually recovers is `generate.py`'s uniform-within-segment arrival draw, not
    `demand.HOURLY_PROFILE`. The profile's numbers are **written out below rather than imported**,
    because importing them is the one thing `test_the_eval_never_reads_the_simulator_s_own_intraday_shape`
    forbids — and a test that broke its own rule to check the rule would be the defect it is about.

    What this does not cover
    ------------------------
    It shows the curve is not the profile *in this corpus*. Had the generator drawn arrival hours
    from the profile instead of uniformly inside a price segment, the two would coincide and a
    hand-copied constant would be the right answer. The backstop is therefore contingent on a
    generator implementation detail, which is stated here rather than discovered later.
    """
    profile = (
        0.030,
        0.052,
        0.078,
        0.092,
        0.086,
        0.070,
        0.055,
        0.048,
        0.052,
        0.066,
        0.088,
        0.104,
        0.096,
        0.058,
        0.015,
        0.010,
    )
    window = build.WINDOW
    assert len(profile) == window.hours
    total = sum(profile)
    cumulative: list[float] = []
    running = 0.0
    for share in profile:
        cumulative.append(running / total)
        running += share

    for days in build.worlds():
        curve = fit(days.fit_days, window)
        hours = range(window.open_hour, window.close_hour)
        from_profile = max(
            abs(float(curve.share_before(h)) - cumulative[h - window.open_hour]) for h in hours
        )
        from_uniform = max(
            abs(float(curve.share_before(h)) - (h - window.open_hour) / window.hours) for h in hours
        )
        assert from_uniform < 0.02 <= from_profile, (
            f"{days.world}: the fitted curve sits {from_uniform:.4f} from uniform and "
            f"{from_profile:.4f} from the generator's hourly profile. If those ever swap, the "
            "curve has started recovering a constant the generator holds rather than a shape "
            "learned from emitted units, and README section 2's independence argument needs "
            "rewriting rather than repeating."
        )


def test_the_recorded_stock_out_hour_is_later_than_trade_stopped_on_two_days_in_five() -> None:
    """Pinned because a docstring in `core/` asserted the opposite and was believed.

    `ShelfState` said `stocked_out_from_hour` *"is derivable from inventory movements"*. In this
    corpus it is the hour the first shopper was turned away, which is a fact about the arrival
    process and not about the movements — and the difference decides which way the correction errs.
    Found by oversight level 2, by measuring rather than by reading. The two numbers below are the
    ones `C12`, the module docstring and `docs/DECISIONS.md` all quote.
    """
    window = build.WINDOW
    with_sales = later = after = 0
    for days in build.worlds():
        for day in days.ran_out:
            if not day.state.units_sold:
                continue
            with_sales += 1
            recorded = day.state.stocked_out_from_hour
            assert recorded is not None
            last = max(i for i, u in enumerate(day.units_by_hour) if u) + window.open_hour
            if last > recorded:
                after += 1
            elif last < recorded:
                later += 1
    assert after == 0, (
        f"{after} censored store-days sold after the hour their shelf is recorded empty from. "
        "Those units sit in the reconstruction's numerator while the share's window excludes "
        "them, and the expansion inflates without bound — C12 is the check, this is the pin."
    )
    assert (with_sales, later) == (16_942, 7_290), (
        "the gap between the recorded stock-out hour and the last hour that sold anything moved: "
        f"got {later} of {with_sales}. It is quoted as 43.0% in censoring.py's module docstring, "
        "in C12's detail, in evals/censoring/README.md section 4 and in docs/DECISIONS.md, so it "
        "goes red here rather than becoming four paragraphs that disagree."
    )


def test_the_overshoot_at_a_thin_window_is_selection_and_not_a_broken_correction() -> None:
    """The eval publishes both estimands; this pins the relationship between them.

    The conditional figure at 08:00 is +36% to +40% and the unconditional one is -1.5% to -0.6%.
    That gap **is** the finding — it is what makes "selection" the right word rather than a
    plausible story told by the author of the correction. If a change ever moved the pooled figure
    out to where the conditional one is, the explanation printed in `Report.notes` would have
    quietly become false.
    """
    worlds = tuple(checks._measure(days) for days in build.worlds())
    thin = [p for m in worlds for p in m.grid if p.hour == build.WINDOW.open_hour + 1]
    assert len(thin) == 3
    for point in thin:
        conditional = point.reconstructed_recovery
        pooled = point.pooled_recovery
        assert conditional is not None and pooled is not None
        assert conditional - 1 > Fraction(30, 100), (
            f"{point.world}: the conditional estimand at a thin window is no longer high "
            f"({float(conditional) - 1:+.3f}); the notes explain a number that is not there."
        )
        assert abs(pooled - 1) < Fraction(5, 100), (
            f"{point.world}: the unconditional estimand at a thin window is "
            f"{float(pooled) - 1:+.3f}. The correction is not merely selecting — it is wrong at "
            "small shares, and Report.notes says the opposite."
        )
