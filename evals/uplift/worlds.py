"""What each world has to do, checked against the function that would make it true.

`CLAUDE.md` carries a table of six worlds and the correct behaviour in each. Three of its rows
were restated on 2026-08-28 because they named behaviour no function in this repository
performs, and the rule that came out of it is written into the checklist: **a sentence about
what the system does when something goes wrong is written against the function that would do
it, named.** So each check below names its function, and where there is none the check says so
rather than inventing one.

===  ============================================  =========================================
W1   no significant uplift, at a rate <= alpha     `Readout.is_significant` — `aa.py`
W2   exclude the interfering units at design,      `feasibility.neighbour_exclusions`, at
     then estimate on what is left                 moment 1. **Nothing at readout** — U6 is
                                                   the pair, not a detector
W3   report ITT with the realised rate printed,    `exposure.measure` -> `Exposure.meets` ->
     or refuse below the declared threshold        `EXPOSURE_BELOW_THRESHOLD`
W4   no result before the declared end, then       `may_read`, and then the caller's own
     report what the window aggregated             aggregation — which U8 checks rather
                                                   than assumes
W5   the power check fails, or the interval is     `Statistic.detects` on the **realised**
     honestly wide                                 variance -> `POWER_NOT_REACHED`
W6   produce the number. No refusal                `close` returning a `Readout`
===  ============================================  =========================================

**W2 has no detector and that is the finding, not a gap in this file.** The closed vocabulary's
only interference code is `at_design`; `contamination.check` compares the digest, the redraw
and the delivered policy, and none of the three can see a neighbour's trade crossing the road.
So `U6` publishes the **pair** — the estimate with the neighbour pairs declared to the engine,
and the bias that arrives when they are withheld — which measures the cost of the gap rather
than closing it.

The seals are opened here, and only here
-----------------------------------------
`corpus.world.seal.open_after_readout` refuses without a readout already on disk and appends
the opening to the seal's own ledger. What comes out is the injected **behaviour** — the
acknowledgement counts, the spillover, the policies — never a number about money, which
`seal.py` is explicit was never in there. `U7` compares what the readout measured against what
the seal says was injected, which is a comparison that needs both and can only be made in this
order.
"""

from __future__ import annotations

import json
import statistics
from collections.abc import Mapping, Sequence
from fractions import Fraction
from pathlib import Path

from corpus.world.seal import SEAL_FILENAME, WorldTruth, open_after_readout

from evals.report import Check
from evals.uplift import aa
from evals.uplift.harness import DrawRecord


def _share(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0/0"
    return f"{numerator}/{denominator} = {100 * numerator / denominator:.1f}%"


def _passes(numerator: int, denominator: int, minimum_pct: Fraction) -> bool:
    return bool(denominator) and Fraction(numerator, denominator) * 100 >= minimum_pct


# ------------------------------------------------------------------ W6


#: The readout refusal that is arithmetic about the roster rather than the machinery reporting
#: on the experiment. It is published as its own number, with no threshold on it in this phase
#: — `docs/DECISIONS.md` carries why, and what would give grounds to put one there.
IMBALANCE = "IMBALANCED_PRE_PERIOD"


def false_refusal_rate(records: Sequence[DrawRecord], *, maximum_pct: Fraction) -> Check:
    """`U3` — the world where everything works produces the number.

    CLAUDE.md: *a system that refuses everything passes every other world and is worthless*,
    which is why this is published beside the false-positive rate rather than under it.

    **It binds the refusals the machinery produces** — every code except
    `IMBALANCED_PRE_PERIOD`, whose share is a separate published number. The two are different
    quantities wearing one name: a refusal for exposure, contamination or power is the
    machinery reporting on the experiment, and a refusal for imbalance is arithmetic about the
    roster, whose categorical half is already refused at design and whose residue `strata.py`
    owns as its own limit.
    """
    total = len(records)
    machine = [r for r in records if [c for c in r.refused if c != IMBALANCE]]
    passed = bool(total) and Fraction(len(machine), total) * 100 <= maximum_pct
    return Check(
        id="U3.w6-false-refusal-rate",
        unarmed_because=(
            "it is rate-shaped and is deliberately absent from `evals.uplift.machinery`, the "
            "only entry point a mutation names — computing a rate on three draws would make "
            "it a different check wearing the same id. See that module's docstring."
        ),
        question=(
            "In the world where everything works and a real effect is present, does the "
            "system produce the number — refusing no more often than declared, for any "
            "reason the machinery itself is responsible for?"
        ),
        passed=passed,
        figure=(
            f"{_share(len(machine), total)} refused by the machinery against a ceiling of "
            f"{float(maximum_pct):.0f}%"
        ),
        detail=""
        if passed
        else (
            "a world with nothing wrong in it is being refused. Every check that fires here "
            "fires on an experiment the system itself broke, and a system that refuses what "
            "works is worth no more than one that reports what did not happen."
        ),
        counterexamples=tuple(
            f"{r.world_seed}/{r.lottery_seed}: {', '.join(r.refused)}" for r in machine[:8]
        ),
    )


def imbalance_share(records: Sequence[DrawRecord]) -> list[tuple[str, str]]:
    """The other half of W6's refusals: published, with no threshold on it in this phase."""
    total = len(records)
    imbalanced = sum(1 for r in records if IMBALANCE in r.refused)
    return [
        ("W6 refused IMBALANCED_PRE_PERIOD", f"{_share(imbalanced, total)} — no threshold"),
        (
            "  what that rate is a function of",
            "the control arm, the five declared covariates and a 0.10 tolerance; "
            "see docs/DECISIONS.md",
        ),
    ]


# ------------------------------------------------------------------ W2


def interference_pair(
    declared: Sequence[DrawRecord],
    withheld: Sequence[DrawRecord],
    *,
    minimum_pct: Fraction,
) -> tuple[Check, list[tuple[str, str]]]:
    """`U6` — what W2 actually does, published as the pair of refusal rates it is.

    **This was a pair of biases and it could not be computed.** Measured over sixteen draws at
    the harness scale, W2 produced no number at all — every draw refused `POWER_NOT_REACHED`,
    with the neighbour pairs declared to the engine and with them withheld alike. There is
    nothing to take a bias of.

    And the reason is worth more than the number would have been. **The system does not detect
    interference**: `contamination.check` asks whether the digest describes the arms it carries
    and whether each unit received its own arm's policy, and neither question can see a
    neighbour's trade crossing the road. What refuses is the power check, because 18% spillover
    inflates the residual variance past what it will admit — **a refusal by luck, not by
    design**. `docs/DECISIONS.md` carries the limit that follows: at a lower spillover the
    variance would stay under the threshold and the system would state a contaminated number in
    silence.

    So both arms are run and both rates are published. The check is that W2 states no number,
    which is what its `correct_behaviour` now says; the pair is what a reader needs to see that
    declaring the pairs is not what produced that outcome.
    """

    def rate(records: Sequence[DrawRecord]) -> tuple[int, int, dict[str, int]]:
        codes: dict[str, int] = {}
        for record in records:
            for code in record.refused:
                codes[code] = codes.get(code, 0) + 1
        return sum(1 for r in records if not r.produced_a_number), len(records), codes

    refused_declared, total_declared, codes_declared = rate(declared)
    refused_withheld, total_withheld, codes_withheld = rate(withheld)
    correct = refused_declared + refused_withheld
    total = total_declared + total_withheld
    passed = _passes(correct, total, minimum_pct)
    numbers = [
        (
            "W2 with the neighbour pairs declared",
            f"{_share(refused_declared, total_declared)} stated no number · "
            f"{codes_declared or 'no refusal code'}",
        ),
        (
            "W2 with the neighbour pairs withheld",
            f"{_share(refused_withheld, total_withheld)} stated no number · "
            f"{codes_withheld or 'no refusal code'}",
        ),
        (
            "  what refused it",
            "the power check, on variance the spillover created — not a detector. "
            "See docs/DECISIONS.md for what that means at a lower spillover",
        ),
    ]
    return (
        Check(
            id="U6.w2-states-no-number",
            question=(
                "On a world that breaks the stable unit treatment value assumption, does the "
                "system state no number — whether or not the interfering pairs were declared "
                "to the design engine?"
            ),
            passed=passed,
            figure=(
                f"{_share(correct, total)} stated no number, against a floor of "
                f"{float(minimum_pct):.0f}% · declared "
                f"{_share(refused_declared, total_declared)}, withheld "
                f"{_share(refused_withheld, total_withheld)}"
            ),
            detail=""
            if passed
            else (
                "a draw on the interference world produced an uplift. Nothing in the four "
                "validity checks looks for interference, so a number stated here is a number "
                "stated about arms that were measuring each other — which is the silent "
                "contaminated result docs/DECISIONS.md carries as this system's declared "
                "limit, arriving earlier than the deferral expected it to."
            ),
            counterexamples=tuple(
                f"{r.world_seed}/{r.lottery_seed}: uplift "
                f"{float(r.uplift_cents or 0) / 100:+,.2f} EUR"
                for r in [*declared, *withheld]
                if r.produced_a_number
            )[:8],
        ),
        numbers,
    )


# ------------------------------------------------------------------ W3, W4, W5


def exposure_refuses(records: Sequence[DrawRecord], *, minimum_pct: Fraction) -> Check:
    """`U5`'s sibling on W3 — `U7`: below the threshold it refuses, and never dilutes silently.

    The function is `exposure.measure` into `Exposure.meets` into
    `EXPOSURE_BELOW_THRESHOLD`. There is no exposure-adjusted alternative in this repository
    and `exposure.py` says so in as many words: no CACE, no instrumental variable, and the
    absence is deliberate rather than pending, because such a number carries an exclusion
    restriction this readout exists to avoid.

    So the correct behaviour is binary and this is the check of it: on a world where a third
    of the treated units never take the price, the readout refuses.
    """
    total = len(records)
    correct = sum(1 for r in records if "EXPOSURE_BELOW_THRESHOLD" in r.readout_refusals)
    passed = _passes(correct, total, minimum_pct)
    return Check(
        id="U7.w3-exposure-refuses",
        question=(
            "When a third of the treated units never take the price, does the readout refuse "
            "with EXPOSURE_BELOW_THRESHOLD rather than report a diluted number?"
        ),
        passed=passed,
        figure=f"{_share(correct, total)} refused, against a floor of {float(minimum_pct):.0f}%",
        detail=""
        if passed
        else (
            "a draw that neither refused nor was exposed above the threshold has reported an "
            "intention-to-treat estimate diluted by an amount nobody declared — and dilution "
            "runs toward zero, which makes a real effect look absent and never gets queried."
        ),
        counterexamples=tuple(
            f"{r.world_seed}/{r.lottery_seed}: {', '.join(r.refused) or 'produced a number'}"
            for r in records
            if "EXPOSURE_BELOW_THRESHOLD" not in r.readout_refusals
        )[:8],
    )


def window_not_first_week(
    records: Sequence[DrawRecord],
    *,
    window_truth: Mapping[str, Fraction],
    first_week_truth: Mapping[str, Fraction],
) -> tuple[Check, list[tuple[str, str]]]:
    """`U8` — a decaying effect is reported as the window's average, not its first week.

    **This is checked rather than assumed, and the reason is a restatement.** `close` takes
    `outcomes` as given and *cannot verify that what it was handed spans the declared period*;
    what `may_read` guarantees is that a result cannot be **asked for** early. The aggregation
    is the caller's obligation — and in this harness the caller is `harness.py`, so a check
    that trusted it would be the harness grading itself.

    **It is a comparison of means and not of individual draws**, which is a correction made on
    measurement. The two truths differ by about a fifth of what a single draw's standard error
    is, so which of them a *given* estimate is nearer is very nearly a coin toss and a check
    over draws would have reported the seed it drew. The mean of the estimates has a standard
    error smaller by the square root of the number of draws, and the check publishes both
    distances so a reader can see how much room there was between them.
    """
    scored = [
        r
        for r in records
        if r.uplift_cents is not None
        and r.world_seed in window_truth
        and r.world_seed in first_week_truth
    ]
    if not scored:
        return (
            Check(
                id="U8.w4-window-average",
                question=(
                    "When the effect decays, is what the readout reports the declared "
                    "window's average rather than its first week extrapolated?"
                ),
                passed=False,
                figure="no draw produced a number to compare against either truth",
            ),
            [],
        )
    to_window = statistics.fmean(
        abs(float(r.uplift_cents or 0) - float(window_truth[r.world_seed])) for r in scored
    )
    to_first = statistics.fmean(
        abs(float(r.uplift_cents or 0) - float(first_week_truth[r.world_seed])) for r in scored
    )
    gap = statistics.fmean(
        abs(float(window_truth[r.world_seed] - first_week_truth[r.world_seed])) for r in scored
    )
    passed = to_window < to_first
    numbers = [
        ("W4 mean |estimate - window truth|", f"{to_window / 100:,.2f} EUR"),
        ("W4 mean |estimate - first-week truth|", f"{to_first / 100:,.2f} EUR"),
        ("  how far apart the two truths are", f"{gap / 100:,.2f} EUR"),
    ]
    return (
        Check(
            id="U8.w4-window-average",
            question=(
                "When the effect decays, is what the readout reports the declared window's "
                "average rather than its first week extrapolated?"
            ),
            passed=passed,
            figure=(
                f"mean distance {to_window / 100:,.2f} EUR to the window truth against "
                f"{to_first / 100:,.2f} EUR to the first week, over {len(scored)} draw(s); "
                f"the two truths are {gap / 100:,.2f} EUR apart"
            ),
            detail=""
            if passed
            else (
                "the estimate is nearer what the first week alone would have said. Nothing in "
                "`close` could have caught that — it cannot see whether the outcomes it was "
                "handed span the declared period — so this is the check that stands in for a "
                "guarantee the core does not make."
            ),
        ),
        numbers,
    )


def power_or_width(
    records: Sequence[DrawRecord],
    *,
    truth: Mapping[str, Fraction],
    alpha: Fraction,
    level: Fraction,
) -> Check:
    """`U9` — heavy tails fail the power check, or the interval is honestly wide.

    The function is `Statistic.detects`, judged on the **realised** variance rather than on
    the one the design believed, into `POWER_NOT_REACHED`; and `interval`, which widens by
    inversion rather than by an asymptotic formula, so a variance the design did not expect
    comes out as width instead of as a confident wrong number.

    **"Honestly wide" means it still contains the truth**, and that reading is a correction
    made on measurement. It was written as *contains zero*, which is a different sentence: the
    effect in this world is real, so an interval that excludes zero can be perfectly honest and
    a draw whose realised variance happened to be mild was being counted as a failure for
    getting a precise answer. What W5 must never do is produce a **confidently wrong** number,
    and that is what covering the truth says.

    Either outcome is correct and both are counted. What is not is a narrow interval that
    misses — a confident number from data that could not support one.

    **It is judged as a binomial and not against `per_world_min_correct_pct`**, which governs
    W2 and W3. Those two are deterministic: every draw refuses or the world has stopped being
    what it says. This one is not — a draw that survives the power check then covers the truth
    with the interval's own declared probability, so the rate a correct system produces here is
    `1 - alpha` and not 1. A fixed percentage would have been a threshold with a different
    meaning at every draw count, which is the same mistake the coverage check was restated to
    stop making.
    """
    scored = [r for r in records if r.world_seed in truth]
    total = len(scored)
    refused = [r for r in scored if "POWER_NOT_REACHED" in r.readout_refusals]
    honest = [
        r
        for r in scored
        if r.interval_cents is not None
        and Fraction(r.interval_cents[0]) <= truth[r.world_seed] <= Fraction(r.interval_cents[1])
    ]
    correct = len(refused) + len(honest)
    nominal = 1 - alpha
    p_value = aa.at_most(correct, total, nominal) if total else Fraction(0)
    passed = bool(total) and p_value > level
    return Check(
        id="U9.w5-power-or-width",
        question=(
            "On a world whose variance arrives far above what the power calculation was sized "
            "on, does the system either fail the power check or return an interval that still "
            "contains the truth — never a confident number the data cannot support?"
        ),
        passed=passed,
        figure=(
            f"{_share(correct, total)} did one or the other "
            f"({len(refused)} refused POWER_NOT_REACHED, {len(honest)} honestly wide) · "
            f"one-sided binomial p={float(p_value):.4f} against a nominal "
            f"{float(nominal):.0%} at level {float(level)}"
        ),
        detail=""
        if passed
        else (
            "a draw produced an interval that misses the truth on a world whose variance the "
            "design never anticipated. That is a confident number from data that cannot "
            "support one, which is the failure this whole repository is about."
        ),
        counterexamples=tuple(
            f"{r.world_seed}/{r.lottery_seed}: interval {r.interval_cents} misses truth "
            f"{float(truth[r.world_seed]) / 100:,.2f} EUR"
            for r in scored
            if r not in refused and r not in honest
        )[:8],
    )


def neighbour_pairs_are_excluded(records: Sequence[DrawRecord]) -> Check:
    """`U13` — no pair inside the declared radius has both members in the experiment.

    This is the design engine's central promise about interference and the only defence
    against it anywhere in the system: `feasibility.neighbour_exclusions` drops the
    later-sorted member of every pair inside `neighbour_radius_m` at moment 1, and the closed
    vocabulary's only interference code is filed under `at_design`. `contamination.check` does
    not look for interference and nothing at readout does.

    So the promise is worth checking per draw rather than trusting, and it is checkable
    exactly: the pairs come from the chain, the roster comes from the seal, and the answer is
    an integer. **W2's withheld arm is excluded from it on purpose** — withholding the pairs is
    the counterfactual the eval publishes, and counting it here would be marking the control
    condition wrong.
    """
    declared = [r for r in records if r.control_size]
    surviving = [r for r in declared if r.surviving_neighbour_pairs]
    return Check(
        id="U13.neighbour-pairs-are-excluded",
        question=(
            "After moment 1, does any pair of stores inside the declared neighbour radius "
            "still have both of its members in the experiment?"
        ),
        passed=not surviving and bool(declared),
        figure=(
            f"{len(declared) - len(surviving)}/{len(declared)} draw(s) left no pair intact"
            if declared
            else "no draw reached a lottery"
        ),
        detail=""
        if not surviving
        else (
            "two stores inside the radius are in the same experiment, so one of them is "
            "measuring the other. Nothing downstream would notice: there is no interference "
            "detector at readout, and the four validity checks would all pass."
        ),
        counterexamples=tuple(
            f"{r.world}/{r.world_seed}/{r.lottery_seed}: {r.surviving_neighbour_pairs} pair(s) "
            "intact"
            for r in surviving[:8]
        ),
    )


# ------------------------------------------------------------------ the seals


def open_seals(seal_dir: Path, readout: Path) -> dict[str, WorldTruth]:
    """Open every seal beside the readout that has already been written.

    `open_after_readout` refuses without a readout on disk, verifies the seal against its own
    commitment, and appends the opening to a ledger inside it. This is the only place in the
    harness that opens one.
    """
    opened: dict[str, WorldTruth] = {}
    for path in sorted(seal_dir.glob(f"*/{SEAL_FILENAME}")):
        truth = open_after_readout(path, readout)
        opened[f"{truth.world}@{truth.seed}"] = truth
    return opened


def write_readout(records: Sequence[DrawRecord], path: Path) -> Path:
    """Every draw, on disk, before any seal is opened. The ordering is the guarantee.

    Written as JSON rather than pickled, because the thing a seal's ledger records is a digest
    of *this file*, and a reader a year from now has to be able to open it without importing
    the version of this package that wrote it.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            [
                {
                    "world": r.world,
                    "world_seed": r.world_seed,
                    "lottery_seed": r.lottery_seed,
                    "scale": r.scale,
                    "roster": r.roster,
                    "excluded": r.excluded,
                    "control_size": r.control_size,
                    "weeks": r.weeks,
                    "design_refusals": list(r.design_refusals),
                    "readout_refusals": list(r.readout_refusals),
                    "checks": [
                        {"check": name, "passed": ok, "figure": figure}
                        for name, ok, figure in r.check_figures
                    ],
                    "uplift_cents": str(r.uplift_cents) if r.uplift_cents is not None else None,
                    "interval_cents": list(r.interval_cents) if r.interval_cents else None,
                    "p_value": str(r.p_value) if r.p_value is not None else None,
                    "permutation_draws": r.permutation_draws,
                    "significant": r.significant,
                    "digest": r.digest,
                }
                for r in records
            ],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path
