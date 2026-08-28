"""What the interval and the estimate are worth, measured against a truth computed separately.

Two quantities on W6 — the world where everything works and a real effect is present:

**Coverage.** Over K draws a 95% interval must contain the true average effect about 95% of the
time. It is the property inversion buys and asymptotics do not, and it is the one number that
would notice an inference that ignored the restriction the strata impose — a confidence
interval that assumed simple randomisation comes out falsely wide, and a wide interval covers
too often rather than too rarely, which is the direction nobody questions.

**Bias.** The mean of `estimate - truth` over the same draws. A difference of means over
randomly assigned units is unbiased under any data-generating process — that is a theorem, not
an opinion held here — so what this measures is whether the machinery around the subtraction
lost it on the way.

Where the truth comes from, and what the seal does about it
-----------------------------------------------------------
`truth = mean over the roster of Y(1) minus mean over the roster of Y(0)`, at the metric's grain,
from the two counterfactual generations. It is the estimand a difference of means targets, so
coverage is a question about the same number the interval is an interval for.

**And it is in the worker's memory by construction, which is said here rather than dressed up.**
Composing a draw's outcomes needs both potential outcomes; a harness that has them has the
average of their difference. No file can prevent that. What `corpus/world/seal.py` holds is the
injected **behaviour** — the exposure rates, the spillover, the ack failures — and its own
docstring is explicit that the effect on the metric is not in it and never was, because the
generator injects three more units per store and not four thousand euros a week.

So the ordering guarantee is real and it is about the behaviour: `worlds.py` opens each seal
with `open_after_readout`, which refuses without a readout already on disk and records the
opening in the seal's own ledger. What keeps the *metric* truth out of the estimate is
structural instead: `DrawRecord` has no field for it, `close()` never sees a potential outcome,
and the number is formed by the core from the observed arm alone.
"""

from __future__ import annotations

import statistics
from collections.abc import Mapping, Sequence
from fractions import Fraction

from evals.report import Check
from evals.uplift import aa
from evals.uplift.harness import DrawRecord
from evals.uplift.outcomes import Week


#: A 95% interval, from the declared alpha. Written as the complement rather than as 0.95, so
#: a moved alpha moves this with it instead of leaving two numbers to disagree.
def nominal_coverage(alpha: Fraction) -> Fraction:
    return 1 - alpha


def average_treatment_effect(
    control: Mapping[tuple[str, Week], int],
    treatment: Mapping[tuple[str, Week], int],
    *,
    units: Sequence[str],
    weeks: Sequence[Week],
) -> Fraction:
    """The true effect on the metric, in canonical units per unit-week.

    The mean over the roster of each unit's window mean under treatment, minus the same under
    control. Taken over the **same window** the readout was taken over and over the **same
    roster** the lottery drew on, because an estimand measured on a different set of units is a
    different estimand and comparing an estimate to it would be comparing two things.
    """
    if not units or not weeks:
        raise ValueError("an average treatment effect over no units or no weeks")
    span = Fraction(len(weeks))
    total = Fraction(0)
    for unit in units:
        under_treatment = sum((Fraction(treatment[(unit, w)]) for w in weeks), Fraction(0))
        under_control = sum((Fraction(control[(unit, w)]) for w in weeks), Fraction(0))
        total += (under_treatment - under_control) / span
    return total / len(units)


def coverage(
    records: Sequence[DrawRecord],
    truth: Mapping[str, Fraction],
    *,
    alpha: Fraction,
    level: Fraction,
) -> Check:
    """`U4` — a 95% interval contains the truth about 95% of the time.

    **A binomial test rather than a fixed band**, and the reason is that a band means different
    things at different draw counts: five percentage points is more than three standard errors
    at K = 200 and less than one at a dozen, so the same check would have been two checks at
    the two configurations this harness runs in. The binomial is one instrument at any K.
    """
    with_truth = [r for r in records if r.interval_cents is not None and r.world_seed in truth]
    total = len(with_truth)
    covered = sum(
        1
        for r in with_truth
        if r.interval_cents is not None
        and Fraction(r.interval_cents[0]) <= truth[r.world_seed] <= Fraction(r.interval_cents[1])
    )
    nominal = nominal_coverage(alpha)
    p_value = aa.two_sided(covered, total, nominal) if total else Fraction(0)
    passed = bool(total) and p_value > level
    return Check(
        id="U4.w6-coverage",
        question=(
            "Over K runs of the world where everything works, does the confidence interval "
            "contain the true average effect about as often as its declared level says?"
        ),
        passed=passed,
        figure=(
            f"{covered}/{total} = {100 * covered / total:.1f}% covered against a nominal "
            f"{float(nominal):.0%} · two-sided binomial p={float(p_value):.4f} at level "
            f"{float(level)}"
            if total
            else "no draw produced an interval"
        ),
        detail=(
            ""
            if passed
            else (
                "coverage this far from nominal is not sampling. Too high means the interval "
                "is wider than the test it claims to invert — which is what ignoring the "
                "restriction the strata impose looks like, and it errs in the direction "
                "nobody questions. Too low means it is narrower than the data supports."
            )
        ),
        counterexamples=tuple(
            f"{r.world_seed}/{r.lottery_seed}: interval {r.interval_cents} misses "
            f"truth {float(truth[r.world_seed]):,.0f}"
            for r in with_truth
            if r.interval_cents is not None
            and not (
                Fraction(r.interval_cents[0])
                <= truth[r.world_seed]
                <= Fraction(r.interval_cents[1])
            )
        )
        if not passed
        else (),
    )


def bias(
    records: Sequence[DrawRecord], truth: Mapping[str, Fraction]
) -> tuple[Check, list[tuple[str, str]]]:
    """`U5` — the estimate is unbiased for the truth, with its spread beside it.

    The threshold is the estimator's own standard error rather than a number chosen here: over
    `n` draws the mean of `estimate - truth` has a standard error of `sd / sqrt(n)`, so a mean
    bias inside two of those is what an unbiased estimator produces and anything outside it is
    a finding. It is the same discipline as `U1` and `U4` — test the number, do not eyeball it
    — expressed with the only scale the data itself supplies.
    """
    errors = [
        float(r.uplift_cents) - float(truth[r.world_seed])
        for r in records
        if r.uplift_cents is not None and r.world_seed in truth
    ]
    total = len(errors)
    if total < 2:
        return (
            Check(
                id="U5.w6-estimator-bias",
                question="Is the estimate unbiased for the true average effect?",
                passed=False,
                figure=f"{total} draw(s) produced a number — too few to take a mean of",
            ),
            [],
        )
    mean = statistics.fmean(errors)
    spread = statistics.stdev(errors)
    standard_error = spread / (total**0.5)
    passed = abs(mean) <= 2 * standard_error
    numbers = [
        ("W6 estimator bias, mean", f"{mean / 100:+,.2f} EUR per store-week over {total} draws"),
        ("  its standard error", f"{standard_error / 100:,.2f} EUR"),
        ("  spread of the errors", f"{spread / 100:,.2f} EUR"),
    ]
    return (
        Check(
            id="U5.w6-estimator-bias",
            question=(
                "Is the estimate unbiased for the true average effect — is the mean of "
                "estimate minus truth inside what an unbiased estimator's own noise allows?"
            ),
            passed=passed,
            figure=(
                f"mean error {mean / 100:+,.2f} EUR against a standard error of "
                f"{standard_error / 100:,.2f} EUR over {total} draws"
            ),
            detail=(
                ""
                if passed
                else (
                    "a difference of means over randomly assigned units is unbiased under any "
                    "data-generating process. That is a theorem, so a bias this size is not a "
                    "fact about the world — it is the machinery around the subtraction having "
                    "lost what the subtraction already had."
                )
            ),
        ),
        numbers,
    )
