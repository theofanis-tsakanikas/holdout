"""The A/A split: both arms get the same policy, and the system must not find an effect.

This is claim 2's sentence and the only check in the harness that **needs no ground truth at
all**. W1's treatment policy *is* its control policy, so there is nothing to be right or wrong
about: `tests/corpus/test_world_determinism.py` asserts the two arms produce byte-identical
streams except for the arm label on the decision record, and the metric does not read that
label. Empty is empty, so nobody has to take the simulator's word for anything.

What is measured is the rate at which the whole system — assignment, exposure, the four checks,
the readout — reports a **significant** uplift over K draws, against the alpha the system
declared about itself in `contracts/design/inference.yaml`.

**It is tested, not eyeballed.** A rate of 4% on 200 draws is not evidence that the true rate
is at or below 5%; it is a sample. The one-sided binomial answers the question actually being
asked — *is a rate this high still consistent with a true rate at or below alpha?* — at a level
declared separately in `aa_harness.yaml`, because alpha is what the system claims and the level
is what we test the claim at. Collapsing the two would be the estimator grading its own
homework.

**A refused draw is not a significant one**, and that matters more than it looks. A system that
refused every draw would report a false-positive rate of zero and pass this check while being
worthless — which is exactly why `U3` is published in the same block, and why the share of
draws that produced no number at all is printed here rather than left to be inferred.
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction
from math import comb

from evals.report import Check
from evals.uplift.harness import DrawRecord


def at_least(successes: int, trials: int, probability: Fraction) -> Fraction:
    """`P(X >= successes)` for `X ~ Binomial(trials, probability)`, exactly.

    `math.comb` is exact and `Fraction` is exact, so the answer is a rational and no
    approximation enters. At the sizes this harness runs — a few hundred draws — the sum is
    milliseconds, and an exact tail is one nobody has to argue about at the margin.
    """
    if successes <= 0:
        return Fraction(1)
    if successes > trials:
        return Fraction(0)
    q = 1 - probability
    return sum(
        (
            Fraction(comb(trials, i)) * probability**i * q ** (trials - i)
            for i in range(successes, trials + 1)
        ),
        Fraction(0),
    )


def at_most(successes: int, trials: int, probability: Fraction) -> Fraction:
    return Fraction(1) - at_least(successes + 1, trials, probability)


def two_sided(successes: int, trials: int, probability: Fraction) -> Fraction:
    """Twice the smaller tail, capped at one — the convention, declared rather than assumed.

    There are three conventions for a two-sided binomial p-value and they disagree on skewed
    binomials. This one is the simplest to state and the most conservative of the three in the
    direction that matters here: it is harder to reject with, so a check built on it does not
    fire on a coverage rate that is merely lucky.
    """
    smaller = min(at_least(successes, trials, probability), at_most(successes, trials, probability))
    return min(Fraction(1), 2 * smaller)


def _fraction(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0/0"
    return f"{numerator}/{denominator} = {100 * numerator / denominator:.1f}%"


def false_positive_rate(
    records: Sequence[DrawRecord], *, alpha: Fraction, level: Fraction
) -> Check:
    """`U1` — claim 2's sentence, as a number and a test of that number."""
    total = len(records)
    significant = sum(1 for record in records if record.significant)
    p_value = at_least(significant, total, alpha) if total else Fraction(1)
    passed = bool(total) and p_value > level
    return Check(
        id="U1.aa-false-positive-rate",
        unarmed_because=(
            "it is rate-shaped and is deliberately absent from `evals.uplift.machinery`, the only "
            " entry point a mutation names — computing a rate on three draws would make it a diff "
            "erent check wearing the same id. See that module's docstring."
        ),
        question=(
            "On an A/A split, where both arms run the same policy and there is nothing to "
            "find, does the whole system report a significant effect no more often than the "
            "alpha it declared about itself?"
        ),
        passed=passed,
        figure=(
            f"{_fraction(significant, total)} significant against alpha={float(alpha):.0%}"
            f" · one-sided binomial p={float(p_value):.4f} at level {float(level)}"
        ),
        detail=(
            ""
            if passed
            else (
                f"a rate of {_fraction(significant, total)} is not consistent with a true "
                f"rate at or below {float(alpha):.0%}: the one-sided binomial rejects that at "
                f"level {float(level)}. Nothing downstream of this is worth reading — the "
                "SPEC's stop condition says the branch stops here rather than loosening a "
                "threshold or re-drawing a seed."
            )
        ),
        counterexamples=tuple(
            f"{r.world_seed}/{r.lottery_seed}: p={float(r.p_value or 0):.4f} "
            f"uplift={float(r.uplift_cents or 0) / 100:+,.2f} EUR"
            for r in records
            if r.significant
        )
        if not passed
        else (),
    )


def p_values_are_not_piled_at_one_end(records: Sequence[DrawRecord]) -> Check:
    """`U2` — under the null the p-values are uniform, so their spread is a second look.

    The false-positive rate reads one point of the p-value distribution. If the machinery were
    subtly wrong the whole distribution would lean, and a rate at the tail could still come out
    at alpha by luck. So the largest gap between the empirical distribution of the p-values and
    the uniform one is published too — a Kolmogorov-Smirnov statistic, computed exactly on
    rationals and compared against the level a table gives for the number of draws.

    **Only the draws that produced a number are in it.** A refused draw has no p-value, and
    counting it as one would be inventing an observation — doctrine rule 3, applied to a plot.
    """
    values = sorted(record.p_value for record in records if record.p_value is not None)
    total = len(values)
    if not total:
        return Check(
            id="U2.aa-p-values-are-uniform",
            unarmed_because=(
                "it is rate-shaped and is deliberately absent from `evals.uplift.machinery`, the only "
                " entry point a mutation names — computing a rate on three draws would make it a diff "
                "erent check wearing the same id. See that module's docstring."
            ),
            question=(
                "Under the null, are the p-values the system produces spread like a uniform "
                "distribution rather than piled at one end?"
            ),
            passed=False,
            figure="no draw produced a p-value at all",
            detail=(
                "every A/A draw refused, so there is no distribution to look at. That is not "
                "a uniform distribution; it is an absent one, and U3 is where it is counted."
            ),
        )
    gap = max(
        max(
            abs(Fraction(index + 1, total) - value),
            abs(value - Fraction(index, total)),
        )
        for index, value in enumerate(values)
    )
    # The asymptotic two-sided Kolmogorov critical value at 1%, 1.63 / sqrt(n). Written out
    # because `holdout.core`'s no-statistics-library rule is about the core and this is an
    # eval, but computing it from a table nobody can check would be no better than a literal.
    critical = Fraction(163, 100) / Fraction(int(total**0.5 * 1000), 1000)
    passed = gap <= critical
    return Check(
        id="U2.aa-p-values-are-uniform",
        question=(
            "Under the null, are the p-values the system produces spread like a uniform "
            "distribution rather than piled at one end?"
        ),
        passed=passed,
        figure=(
            f"largest gap from uniform {float(gap):.4f} over {total} p-value(s), "
            f"against a 1% critical value of {float(critical):.4f}"
        ),
        detail=(
            ""
            if passed
            else (
                "the p-values lean. A rate at alpha can still come out of a distribution that "
                "is wrong everywhere else, so this is the second look that would notice."
            )
        ),
    )


def refusal_share(records: Sequence[DrawRecord]) -> tuple[str, str]:
    """A published number rather than a check: how much of the A/A world produced nothing.

    Printed beside `U1` because a system that refuses everything passes `U1` trivially. It is
    a *figure* and not a gate here — the gate on refusing too much is `U3`, on the world where
    something was actually there to find.
    """
    total = len(records)
    refused = sum(1 for record in records if not record.produced_a_number)
    return "A/A draws that produced no number", _fraction(refused, total)
