"""Moments 2 and 3 — may this be read, and may the result be stated?

**Moment 2 is the lock.** `may_read` refuses to compute anything before the declared end,
whatever the `decision_rule` said and whoever is asking. The design-time check on the
stopping rule is the announcement; this is the thing that actually stops peeking, because it
does not consult the announcement at all.

**Moment 3 runs four checks in the declared order — balance, exposure, contamination,
power — and it runs all four, always.** The report carries four figures whether or not one of
them failed. A refusal that reported only the check that fired would hide how close the
others came, which is most of what a reader of a refused readout wants to know; and it would
make the refusal look like a verdict on one thing rather than the state of the experiment.

All four pass, and the readout carries the uplift, its interval, the p-value, B, the four
figures, the pinned data version, the seed, the accepted draw index and the digest. Any fail,
and it carries a reason code, the same four figures, **and no number**. The refusal is
rendered at the same size as an uplift would have been, and the refused version of that
screen is the single most important image in this project.

`POWER_NOT_REACHED` is decided on the **realised** variance
-----------------------------------------------------------
Not on the pre-experiment approximation. The design sized itself on a variance somebody
supplied from history; this asks whether the standard error the world actually delivered is
small enough to detect the MDE that was declared in advance. That is the honest half of W5 —
heavy-tailed baskets, variance far above what the power calculation assumed — where the
correct behaviour is that *the power check fails, or the interval is honestly wide*.

The estimate is computed last, and only if the checks pass
-----------------------------------------------------------
Deliberate, and not only for the cost. A number computed and then withheld is a number
somebody can be asked for. The permutation test runs after the four checks have all passed,
so on a refusal there is no uplift anywhere in the process to be talked out of a drawer.

What this engine does not do
----------------------------
It never chooses what to test and never decides what to do about the answer. The
`decision_rule` declared at the start is applied by whoever declared it, to whichever of the
three outcomes arrived. **It decides only what may be claimed.**
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from fractions import Fraction

from holdout.contracts.model import InferenceSettings, Metric
from holdout.core.design.form import MdeDirection
from holdout.core.experiment import contamination as contamination_module
from holdout.core.experiment import exposure as exposure_module
from holdout.core.experiment.assignment import SealedAssignment
from holdout.core.experiment.balance import (
    CovariateMatrix,
    Standardised,
    standardised,
    worst_of,
)
from holdout.core.experiment.codes import (
    CHECK_ORDER,
    CODE_OF,
    Arm,
    ReadoutRefusalCode,
    ValidityCheck,
)
from holdout.core.experiment.estimator import (
    Statistic,
    design_of,
    interval,
    permutation_p,
    plan_for,
    studentized,
)
from holdout.core.money import decimal_of


class PeekError(Exception):
    """A result was asked for before the declared end of the period.

    Not a refusal and not a `ValueError`. A refusal is a correct output about an experiment
    that has closed; this is an experiment that has not, and there is no reason code for it
    because there is nothing to report — the period is still running. It is the one door
    moment 2 exists to hold shut.
    """


class ReadoutError(ValueError):
    """The readout was handed something it cannot close over."""


@dataclass(frozen=True, slots=True)
class Period:
    """When the comparison window opened and when it ends.

    `ends_on` is the first day the period is **not** running, matching the half-open
    convention every effective window in `contracts/` uses. One convention, so nobody has to
    remember which kind of boundary they are looking at.
    """

    opens_on: date
    ends_on: date

    def __post_init__(self) -> None:
        if self.ends_on <= self.opens_on:
            raise ReadoutError(
                f"a period running from {self.opens_on} to {self.ends_on} is in force for no "
                "days, and an experiment that ran for no days has nothing to read out."
            )


def may_read(*, asked_on: date, period_ends_on: date) -> bool:
    """Whether results may be computed at all. The lock, and it consults nothing else.

    Not the `decision_rule`, not the stopping rule, not who is asking. A design that
    declared a single readout at the end and a design that declared nothing at all are held
    to the same line here, because the check that stops peeking must not be one a design can
    talk its way past.
    """
    return asked_on >= period_ends_on


@dataclass(frozen=True, slots=True)
class CheckResult:
    """One of the four, with the figure it produced. Present on a refusal as well as a pass."""

    check: ValidityCheck
    passed: bool
    figure: str

    @property
    def code(self) -> ReadoutRefusalCode | None:
        return None if self.passed else CODE_OF[self.check]

    def __str__(self) -> str:
        return f"{'OK  ' if self.passed else 'RED '} {self.check.value:<14} {self.figure}"


@dataclass(frozen=True, slots=True)
class Readout:
    """The number, and everything needed to check it a year from now."""

    experiment_id: str
    metric_ref: str
    data_version: str
    period: Period
    seed: str
    draw_index: int
    digest: str
    uplift: Fraction
    confidence_interval: tuple[int, int]
    p_value: Fraction
    draws: int
    alpha: Decimal
    statistic: Statistic
    checks: tuple[CheckResult, ...]
    balance: tuple[Standardised, ...]

    @property
    def is_significant(self) -> bool:
        """The declared test against the declared level, never one chosen after the fact.

        The **p-value** governs, because that is the test the design declared — one-sided
        where it declared a direction. The interval is always two-sided, so for a one-sided
        design the two can disagree at the margin: a one-sided rejection whose two-sided
        interval still contains zero is a real and correct combination, and the honest way
        to report it is both numbers rather than whichever one agrees with the other.
        """
        return self.p_value <= Fraction(self.alpha)

    def __str__(self) -> str:
        low, high = self.confidence_interval
        return (
            f"{self.experiment_id}: uplift {decimal_of(self.uplift):+.2f} canonical unit(s) "
            f"[{low:+d}, {high:+d}] p={decimal_of(self.p_value):.4f} at B={self.draws} "
            f"on {self.data_version}"
        )


@dataclass(frozen=True, slots=True)
class ReadoutRefusal:
    """The experiment ran and no uplift may be stated from it. A correct output.

    It carries the same four figures a `Readout` does, so a reader can see how close the
    checks that passed came, and it carries no number at all — see the module docstring for
    why the estimate is never computed on this path.
    """

    experiment_id: str
    metric_ref: str
    data_version: str
    period: Period
    seed: str
    draw_index: int
    digest: str
    checks: tuple[CheckResult, ...]
    balance: tuple[Standardised, ...]

    def __post_init__(self) -> None:
        if all(check.passed for check in self.checks):
            raise ReadoutError(
                "a refusal with every check green. Something computed a refusal without a "
                "reason, and a refusal that cannot name its code cannot be counted."
            )

    @property
    def codes(self) -> tuple[ReadoutRefusalCode, ...]:
        """Every check that failed, in the declared order. All of them, not just the first."""
        return tuple(c.code for c in self.checks if c.code is not None)

    @property
    def code(self) -> ReadoutRefusalCode:
        """The leading code — the first failing check in `CHECK_ORDER`."""
        return self.codes[0]

    def __str__(self) -> str:
        return f"REFUSED {self.code.value} ({self.experiment_id}) — no uplift may be stated"


def close(
    seal: SealedAssignment,
    *,
    outcomes: Mapping[str, int],
    exposed: AbstractSet[str],
    delivered: Mapping[str, str],
    treatment_policy: str,
    control_policy: str,
    covariates_at_close: CovariateMatrix,
    draws: Sequence[Mapping[str, Arm]],
    inference: InferenceSettings,
    metric: Metric,
    mde_absolute: Fraction,
    direction: MdeDirection,
    form_digest: str,
    data_version: str,
    period: Period,
    asked_on: date,
) -> Readout | ReadoutRefusal:
    """Moment 3. Four checks, then — only if all four pass — the number.

    The arguments the SPEC's sketch folded into "the form" are passed as the three facts the
    readout actually needs: `mde_absolute` and `direction`, which the design declared in
    advance and against which realised power is judged, and `form_digest`, which is what lets
    the contamination check notice a readout being run against a *different* design than the
    one that was sealed.

    Nothing here reads a clock. `asked_on` is an argument, like every date in this package,
    so that a readout can be replayed a year later and give the same answer.
    """
    if not may_read(asked_on=asked_on, period_ends_on=period.ends_on):
        raise PeekError(
            f"{seal.experiment_id} was asked for a result on {asked_on} and its period ends "
            f"on {period.ends_on}. Results are not computed before the declared end, "
            "whatever the decision rule says and whoever is asking: an interim look spends "
            "the declared level, and a level spent without a pre-declared spending function "
            "is a false-positive rate nobody wrote down."
        )
    reported = frozenset(seal.roster) & frozenset(outcomes)
    attrited = tuple(sorted(frozenset(seal.roster) - reported))
    stray = sorted(frozenset(outcomes) - frozenset(seal.roster))
    if stray:
        raise ReadoutError(
            f"{len(stray)} unit(s) report an outcome and were never assigned: {stray[:8]}. "
            "An outcome from outside the experiment is not a small addition to the mean; it "
            "is a unit whose price nobody randomised."
        )
    arms = {unit: seal.arms[unit] for unit in sorted(reported)}
    if not any(a is Arm.TREATMENT for a in arms.values()) or not any(
        a is Arm.CONTROL for a in arms.values()
    ):
        raise ReadoutError(
            f"attrition emptied an arm: {len(reported)} of {len(seal.roster)} unit(s) "
            "reported. There is nothing left to take a difference of, and an experiment with "
            "one arm is not one that refuses — it is one that never ran."
        )

    matrix = covariates_at_close.restricted_to(reported)
    differences = standardised(matrix, arms)
    worst = worst_of(differences)
    balance_ok = not worst.exceeds(inference.balance_tolerance_smd)
    balance_figure = f"worst SMD {worst}"
    if attrited:
        balance_figure += f"; {len(attrited)} of {len(seal.roster)} unit(s) did not report"
    if matrix.ids != covariates_at_close.ids:  # pragma: no cover - restricted_to preserves ids
        raise ReadoutError("the covariate columns moved between design and readout")

    realised_exposure = exposure_module.measure(seal, exposed)
    exposure_ok = realised_exposure.meets(inference.exposure_min_pct)

    contaminated = contamination_module.check(
        seal,
        delivered=delivered,
        treatment_policy=treatment_policy,
        control_policy=control_policy,
        form_digest=form_digest,
    )

    design = design_of(matrix)
    observed = studentized(outcomes, arms, design)
    two_sided = direction is MdeDirection.EITHER
    z_sum = Fraction(inference.z_alpha(two_sided=two_sided)) + Fraction(inference.z_power)
    power_ok = observed.detects(mde_absolute, z_sum)

    checks = (
        CheckResult(check=ValidityCheck.BALANCE, passed=balance_ok, figure=balance_figure),
        CheckResult(
            check=ValidityCheck.EXPOSURE,
            passed=exposure_ok,
            figure=f"{realised_exposure} against a floor of {inference.exposure_min_pct}%",
        ),
        CheckResult(
            check=ValidityCheck.CONTAMINATION,
            passed=contaminated.is_clean,
            figure=str(contaminated),
        ),
        CheckResult(
            check=ValidityCheck.POWER,
            passed=power_ok,
            figure=(
                f"standard error {observed.standard_error:.4f} against a declared MDE of "
                f"{decimal_of(mde_absolute):.4f} canonical unit(s) at "
                f"{inference.target_power} power"
            ),
        ),
    )
    _check_order_is_the_declared_one(checks)

    if not all(check.passed for check in checks):
        return ReadoutRefusal(
            experiment_id=seal.experiment_id,
            metric_ref=metric.ref,
            data_version=data_version,
            period=period,
            seed=seal.seed,
            draw_index=seal.draw_index,
            digest=seal.digest,
            checks=checks,
            balance=differences,
        )

    restricted = [
        {unit: arm for unit, arm in candidate.items() if unit in reported} for candidate in draws
    ]
    plan = plan_for(design, restricted)
    p_value = permutation_p(observed, plan, outcomes, direction=direction)
    bounds = interval(outcomes, arms, plan, alpha=inference.alpha)
    return Readout(
        experiment_id=seal.experiment_id,
        metric_ref=metric.ref,
        data_version=data_version,
        period=period,
        seed=seal.seed,
        draw_index=seal.draw_index,
        digest=seal.digest,
        uplift=observed.difference,
        confidence_interval=bounds,
        p_value=p_value,
        draws=plan.size,
        alpha=inference.alpha,
        statistic=observed,
        checks=checks,
        balance=differences,
    )


def _check_order_is_the_declared_one(checks: tuple[CheckResult, ...]) -> None:
    """The four run and are reported in `CHECK_ORDER`, not in whatever order they were written.

    `ReadoutRefusal.code` takes the first failing check as the leading one, so the order is a
    decision about what a refusal is *called* — and a decision like that must not fall to the
    order somebody happened to build a tuple in.
    """
    if tuple(c.check for c in checks) != CHECK_ORDER:
        raise ReadoutError(  # pragma: no cover - a guard against a future edit, not an input
            f"the checks were assembled as {[c.check.value for c in checks]} and the declared "
            f"order is {[c.value for c in CHECK_ORDER]}. Which code leads a refusal must not "
            "depend on the order this function was written in."
        )
