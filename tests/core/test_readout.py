"""Moments 2 and 3 — may this be read, and may the result be stated?

Each of the four refusals is fired **alone**, so a code here is traceable to the one thing
the test changed. Beside each one: the assertion that the other three figures are still on
the report. A refusal that carried only the check that fired would hide how close the others
came, which is most of what a reader of a refused readout wants to know — and the refused
version of that screen is the single most important image in this project.

Moment 2 is a separate section because it is a different kind of guarantee. The design-time
check on the stopping rule is an announcement; `may_read` is the lock, and it consults
nothing — not the decision rule, not the stopping rule, not who is asking.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from fractions import Fraction

import pytest

from holdout.contracts.model import InferenceSettings, Metric
from holdout.core.design import MdeDirection
from holdout.core.experiment import (
    Arm,
    CovariateMatrix,
    PeekError,
    Period,
    Readout,
    ReadoutError,
    ReadoutRefusal,
    ReadoutRefusalCode,
    SealedAssignment,
    ValidityCheck,
    close,
    control_size_for,
    draw,
    may_read,
    reference_set,
)

SEED = "holdout-t001-committed-seed"
FORM_DIGEST = "c" * 64
POLICY = "ladder_policy@v1"
OPENS_ON = date(2026, 4, 1)
ENDS_ON = date(2026, 6, 1)
PERIOD = Period(opens_on=OPENS_ON, ends_on=ENDS_ON)
DATA_VERSION = "delta@42"

#: Big enough to clear the `2 / (1 + B)` floor the mirror assignment imposes at alpha = 0.05,
#: and small enough that a whole suite of readouts runs in a second. See `estimator.py`.
DRAWS = 80

#: An effect large enough that the power check passes on a realised standard error of a few
#: units, and small enough to state in one number a reader can hold.
EFFECT = 5000


@pytest.fixture
def seal(matrix: CovariateMatrix, inference: InferenceSettings) -> SealedAssignment:
    drawn = draw(
        experiment_id="exp-readout",
        roster=matrix.units,
        seed=SEED,
        form_digest=FORM_DIGEST,
        matrix=matrix,
        control_size=control_size_for(len(matrix.units), inference.holdout_share_pct),
    )
    assert drawn is not None
    return drawn[0]


@pytest.fixture
def outcomes(seal: SealedAssignment) -> dict[str, int]:
    """Integers at the metric's declared scale, with a real effect on the treated arm."""
    return {
        unit: 40_000 + 37 * index + (EFFECT if seal.arms[unit] is Arm.TREATMENT else 0)
        for index, unit in enumerate(seal.roster)
    }


@pytest.fixture
def draws(
    seal: SealedAssignment, matrix: CovariateMatrix, inference: InferenceSettings
) -> tuple[Mapping[str, Arm], ...]:
    return reference_set(seal, draws=DRAWS, max_attempts=inference.max_assignment_attempts)


def close_it(
    seal: SealedAssignment,
    matrix: CovariateMatrix,
    inference: InferenceSettings,
    metric: Metric,
    outcomes: Mapping[str, int],
    draws: tuple[Mapping[str, Arm], ...],
    **overrides: object,
) -> Readout | ReadoutRefusal:
    arguments: dict[str, object] = {
        "outcomes": outcomes,
        "exposed": frozenset(seal.treatment),
        "delivered": dict.fromkeys(seal.roster, POLICY),
        "treatment_policy": POLICY,
        "control_policy": POLICY,
        "covariates_at_close": matrix,
        "draws": draws,
        "inference": inference,
        "metric": metric,
        "mde_absolute": Fraction(2000),
        "direction": MdeDirection.EITHER,
        "form_digest": FORM_DIGEST,
        "data_version": DATA_VERSION,
        "period": PERIOD,
        "asked_on": ENDS_ON,
    }
    arguments.update(overrides)
    return close(seal, **arguments)  # type: ignore[arg-type]


# ------------------------------------------------------------------ moment 2, the lock


def test_may_read_refuses_before_the_declared_end() -> None:
    assert not may_read(asked_on=date(2026, 5, 31), period_ends_on=ENDS_ON)
    assert may_read(asked_on=ENDS_ON, period_ends_on=ENDS_ON)
    assert may_read(asked_on=date(2026, 6, 2), period_ends_on=ENDS_ON)


def test_closing_before_the_end_raises_rather_than_refusing(
    seal: SealedAssignment,
    matrix: CovariateMatrix,
    inference: InferenceSettings,
    metric: Metric,
    outcomes: dict[str, int],
    draws: tuple[Mapping[str, Arm], ...],
) -> None:
    """Not a refusal and not a reason code. There is nothing to report — the period is still
    running — and an interim look spends the declared level whether or not anybody acts on
    it. This is the thing that actually stops peeking; the design-time check is only the
    announcement.
    """
    with pytest.raises(PeekError, match="before the declared end"):
        close_it(seal, matrix, inference, metric, outcomes, draws, asked_on=date(2026, 5, 30))


def test_the_lock_does_not_consult_the_stopping_rule(
    seal: SealedAssignment,
    matrix: CovariateMatrix,
    inference: InferenceSettings,
    metric: Metric,
    outcomes: dict[str, int],
    draws: tuple[Mapping[str, Arm], ...],
) -> None:
    """`close` takes no stopping rule at all, which is the point: a design that declared a
    single readout and one that declared nothing are held to the same line, because a check
    a design can talk its way past is not a check."""
    import inspect

    assert "stopping" not in inspect.signature(close).parameters
    with pytest.raises(PeekError):
        close_it(seal, matrix, inference, metric, outcomes, draws, asked_on=OPENS_ON)


# ------------------------------------------------------------------ moment 3, all four


def test_all_four_checks_pass_and_a_number_is_stated(
    seal: SealedAssignment,
    matrix: CovariateMatrix,
    inference: InferenceSettings,
    metric: Metric,
    outcomes: dict[str, int],
    draws: tuple[Mapping[str, Arm], ...],
) -> None:
    result = close_it(seal, matrix, inference, metric, outcomes, draws)
    assert isinstance(result, Readout), result
    assert [c.check for c in result.checks] == list(ValidityCheck)
    assert all(c.passed for c in result.checks)
    assert result.data_version == DATA_VERSION
    assert result.seed == SEED
    assert result.draw_index == seal.draw_index
    assert result.digest == seal.digest
    assert result.draws == len(draws)
    low, high = result.confidence_interval
    assert low <= result.uplift <= high


def test_the_interval_contains_the_effect_that_was_actually_injected(
    seal: SealedAssignment,
    matrix: CovariateMatrix,
    inference: InferenceSettings,
    metric: Metric,
    outcomes: dict[str, int],
    draws: tuple[Mapping[str, Arm], ...],
) -> None:
    """One run is not coverage — coverage is claim 2 at K = 200 and it is measured, not
    asserted. What this checks is that the interval is in the right place at all, which is
    the failure a sign error or a scale error produces and a single run does catch.
    """
    result = close_it(seal, matrix, inference, metric, outcomes, draws)
    assert isinstance(result, Readout), result
    low, high = result.confidence_interval
    assert low <= EFFECT <= high


# ------------------------------------------------------------------ each refusal, alone


def test_an_imbalanced_pre_period_refuses_and_still_reports_four_figures(
    seal: SealedAssignment,
    matrix: CovariateMatrix,
    inference: InferenceSettings,
    metric: Metric,
    outcomes: dict[str, int],
    draws: tuple[Mapping[str, Arm], ...],
) -> None:
    """The covariates as they stood at close, not as the screen saw them.

    A restatement moved the pre-period revenue after the assignment was drawn, and the arms
    are now separated on it. The screen could not have known; the check is what notices, and
    it can only notice because it re-measures.
    """
    restated = CovariateMatrix.of(
        matrix.ids,
        matrix.kinds,
        {
            unit: (
                Fraction(90_000 if seal.arms[unit] is Arm.TREATMENT else 10_000),
                *row[1:],
            )
            for unit, row in matrix.rows.items()
        },
    )
    result = close_it(
        seal, matrix, inference, metric, outcomes, draws, covariates_at_close=restated
    )
    assert isinstance(result, ReadoutRefusal), result
    assert result.codes == (ReadoutRefusalCode.IMBALANCED_PRE_PERIOD,)
    assert len(result.checks) == 4
    assert all(c.figure for c in result.checks)


def test_exposure_below_the_threshold_refuses_and_states_no_number(
    seal: SealedAssignment,
    matrix: CovariateMatrix,
    inference: InferenceSettings,
    metric: Metric,
    outcomes: dict[str, int],
    draws: tuple[Mapping[str, Arm], ...],
) -> None:
    """Below the floor there is no estimate at all — not a diluted one, not an adjusted one.

    An exposure-adjusted number would carry an exclusion restriction, and this readout is
    built to avoid assumptions rather than to accumulate them.
    """
    treated = seal.treatment
    thin = frozenset(treated[: len(treated) // 2])
    result = close_it(seal, matrix, inference, metric, outcomes, draws, exposed=thin)
    assert isinstance(result, ReadoutRefusal), result
    assert result.codes == (ReadoutRefusalCode.EXPOSURE_BELOW_THRESHOLD,)
    assert not hasattr(result, "uplift")


def test_exposure_exactly_at_the_threshold_passes(
    seal: SealedAssignment,
    matrix: CovariateMatrix,
    inference: InferenceSettings,
    metric: Metric,
    outcomes: dict[str, int],
    draws: tuple[Mapping[str, Arm], ...],
) -> None:
    """The comparison is `>=`, exactly, in `Fraction`. A threshold that refused the value it
    declares as its floor would be a threshold nobody could hit."""
    treated = seal.treatment
    needed = -(-len(treated) * 95 // 100)
    result = close_it(
        seal, matrix, inference, metric, outcomes, draws, exposed=frozenset(treated[:needed])
    )
    exposure = next(c for c in result.checks if c.check is ValidityCheck.EXPOSURE)
    assert exposure.passed, exposure.figure


def test_a_unit_running_the_other_arm_s_policy_is_contamination(
    seal: SealedAssignment,
    matrix: CovariateMatrix,
    inference: InferenceSettings,
    metric: Metric,
    outcomes: dict[str, int],
    draws: tuple[Mapping[str, Arm], ...],
) -> None:
    """Not a dilution to correct for. A treated store running the control policy measures
    the other arm and is attributed to this one.

    The two arms carry different policies here on purpose: in an A/A design the comparison
    is vacuous by construction, which `contamination.py` says out loud and which this test
    would otherwise be quietly asserting nothing about.
    """
    delivered = dict.fromkeys(seal.roster, "ladder_policy@v1")
    for unit in seal.control:
        delivered[unit] = "ladder_policy@v0"
    delivered[seal.control[0]] = "ladder_policy@v1"
    result = close_it(
        seal,
        matrix,
        inference,
        metric,
        outcomes,
        draws,
        delivered=delivered,
        treatment_policy="ladder_policy@v1",
        control_policy="ladder_policy@v0",
    )
    assert isinstance(result, ReadoutRefusal), result
    assert result.codes == (ReadoutRefusalCode.CONTAMINATED_ASSIGNMENT,)


def test_a_unit_with_no_delivery_on_record_is_contamination_too(
    seal: SealedAssignment,
    matrix: CovariateMatrix,
    inference: InferenceSettings,
    metric: Metric,
    outcomes: dict[str, int],
    draws: tuple[Mapping[str, Arm], ...],
) -> None:
    """A unit that was assigned an arm and has no decision record is not a unit that ran the
    right policy; it is a unit nobody can say anything about."""
    delivered = dict.fromkeys(seal.roster, POLICY)
    del delivered[seal.roster[0]]
    result = close_it(seal, matrix, inference, metric, outcomes, draws, delivered=delivered)
    assert isinstance(result, ReadoutRefusal), result
    assert result.codes == (ReadoutRefusalCode.CONTAMINATED_ASSIGNMENT,)


def test_power_is_judged_on_the_realised_variance_and_not_the_assumed_one(
    seal: SealedAssignment,
    matrix: CovariateMatrix,
    inference: InferenceSettings,
    metric: Metric,
    outcomes: dict[str, int],
    draws: tuple[Mapping[str, Arm], ...],
) -> None:
    """The honest half of W5. The design believed a variance somebody supplied from history;
    this asks whether the standard error the world actually delivered is small enough to
    detect the MDE that was declared. An MDE of one canonical unit is not detectable at any
    realised spread this data has."""
    result = close_it(seal, matrix, inference, metric, outcomes, draws, mde_absolute=Fraction(1))
    assert isinstance(result, ReadoutRefusal), result
    assert result.codes == (ReadoutRefusalCode.POWER_NOT_REACHED,)
    power = next(c for c in result.checks if c.check is ValidityCheck.POWER)
    assert "standard error" in power.figure


def test_two_failing_checks_are_both_reported_and_the_declared_order_leads(
    seal: SealedAssignment,
    matrix: CovariateMatrix,
    inference: InferenceSettings,
    metric: Metric,
    outcomes: dict[str, int],
    draws: tuple[Mapping[str, Arm], ...],
) -> None:
    """Every code that fired is carried; `CHECK_ORDER` decides only which one leads. Nothing
    is lost to the ordering, so a count over refusals is a count over all of them."""
    treated = seal.treatment
    result = close_it(
        seal,
        matrix,
        inference,
        metric,
        outcomes,
        draws,
        exposed=frozenset(treated[: len(treated) // 2]),
        mde_absolute=Fraction(1),
    )
    assert isinstance(result, ReadoutRefusal), result
    assert set(result.codes) == {
        ReadoutRefusalCode.EXPOSURE_BELOW_THRESHOLD,
        ReadoutRefusalCode.POWER_NOT_REACHED,
    }
    assert result.code is ReadoutRefusalCode.EXPOSURE_BELOW_THRESHOLD


def test_a_refusal_with_every_check_green_is_impossible() -> None:
    """A refusal that cannot name its code cannot be counted, and claim 2 is a count."""
    from holdout.core.experiment.readout import CheckResult

    with pytest.raises(ReadoutError, match="every check green"):
        ReadoutRefusal(
            experiment_id="exp-1",
            metric_ref="m@v1",
            data_version=DATA_VERSION,
            period=PERIOD,
            seed=SEED,
            draw_index=0,
            digest="d",
            checks=tuple(
                CheckResult(check=check, passed=True, figure="fine") for check in ValidityCheck
            ),
            balance=(),
        )


# ------------------------------------------------------------------ what it refuses to read


def test_an_outcome_from_a_unit_that_was_never_assigned_is_an_error(
    seal: SealedAssignment,
    matrix: CovariateMatrix,
    inference: InferenceSettings,
    metric: Metric,
    outcomes: dict[str, int],
    draws: tuple[Mapping[str, Arm], ...],
) -> None:
    """Not a small addition to the mean — a unit whose price nobody randomised."""
    with pytest.raises(ReadoutError, match="never assigned"):
        close_it(
            seal,
            matrix,
            inference,
            metric,
            {**outcomes, "store-999": 40_000},
            draws,
        )


def test_attrition_that_empties_an_arm_is_an_error(
    seal: SealedAssignment,
    matrix: CovariateMatrix,
    inference: InferenceSettings,
    metric: Metric,
    outcomes: dict[str, int],
    draws: tuple[Mapping[str, Arm], ...],
) -> None:
    """An experiment with one arm is not one that refuses; it is one that never ran."""
    survivors = {u: v for u, v in outcomes.items() if seal.arms[u] is Arm.TREATMENT}
    with pytest.raises(ReadoutError, match="emptied an arm"):
        close_it(seal, matrix, inference, metric, survivors, draws)


def test_attrition_short_of_that_is_reported_on_the_balance_figure(
    seal: SealedAssignment,
    matrix: CovariateMatrix,
    inference: InferenceSettings,
    metric: Metric,
    outcomes: dict[str, int],
    draws: tuple[Mapping[str, Arm], ...],
) -> None:
    """Stores that did not report are a fact about the experiment, so they go on the report
    rather than being quietly excluded from it."""
    thinned = {u: v for u, v in outcomes.items() if u not in seal.roster[:2]}
    result = close_it(seal, matrix, inference, metric, thinned, draws)
    balance = next(c for c in result.checks if c.check is ValidityCheck.BALANCE)
    assert "did not report" in balance.figure


def test_an_acknowledgement_from_outside_the_roster_is_an_error(
    seal: SealedAssignment,
    matrix: CovariateMatrix,
    inference: InferenceSettings,
    metric: Metric,
    outcomes: dict[str, int],
    draws: tuple[Mapping[str, Arm], ...],
) -> None:
    """Either it belongs to another experiment or the assignment table is not the one the
    decisions were routed by. Neither is something to filter out quietly."""
    from holdout.core.experiment import ExposureError

    with pytest.raises(ExposureError, match="outside the roster"):
        close_it(
            seal,
            matrix,
            inference,
            metric,
            outcomes,
            draws,
            exposed=frozenset({*seal.treatment, "store-999"}),
        )


def test_a_control_unit_with_a_treatment_acknowledgement_is_an_error(
    seal: SealedAssignment,
    matrix: CovariateMatrix,
    inference: InferenceSettings,
    metric: Metric,
    outcomes: dict[str, int],
    draws: tuple[Mapping[str, Arm], ...],
) -> None:
    """That is contamination, and it is the contamination check's finding rather than a
    number to average away in the exposure rate."""
    from holdout.core.experiment import ExposureError

    with pytest.raises(ExposureError, match="carry a treatment acknowledgement"):
        close_it(
            seal,
            matrix,
            inference,
            metric,
            outcomes,
            draws,
            exposed=frozenset({*seal.treatment, seal.control[0]}),
        )


def test_a_period_that_ran_for_no_days_is_an_error() -> None:
    with pytest.raises(ReadoutError, match="in force for no"):
        Period(opens_on=ENDS_ON, ends_on=ENDS_ON)


# ------------------------------------------------------------------ significance


def test_significance_is_the_declared_test_against_the_declared_level(
    seal: SealedAssignment,
    matrix: CovariateMatrix,
    inference: InferenceSettings,
    metric: Metric,
    outcomes: dict[str, int],
    draws: tuple[Mapping[str, Arm], ...],
) -> None:
    """Alpha comes from the contract and travels on the readout, so nobody can compare a
    p-value against a level chosen after seeing it."""
    result = close_it(seal, matrix, inference, metric, outcomes, draws)
    assert isinstance(result, Readout), result
    assert result.alpha == inference.alpha
    assert result.is_significant == (result.p_value <= Fraction(inference.alpha))
    assert result.is_significant, "a five-thousand-unit effect on a clean split is detected"


def test_an_a_a_split_reports_no_effect(
    seal: SealedAssignment,
    matrix: CovariateMatrix,
    inference: InferenceSettings,
    metric: Metric,
    draws: tuple[Mapping[str, Arm], ...],
) -> None:
    """Both arms get the same numbers — the smoke-test shape of claim 2.

    A single seed is not a false-positive rate and this test does not pretend otherwise. It
    catches the failure that would make claim 2 unmeasurable: a system that reports an
    effect where the two arms received literally identical data.
    """
    flat = {unit: 40_000 + 37 * index for index, unit in enumerate(seal.roster)}
    result = close_it(seal, matrix, inference, metric, flat, draws)
    assert isinstance(result, Readout), result
    low, high = result.confidence_interval
    assert low <= 0 <= high, f"an A/A split excluded zero: [{low}, {high}]"
    assert not result.is_significant, f"p={result.p_value}"


def test_the_declared_alpha_is_never_defaulted(inference: InferenceSettings) -> None:
    """A level a caller supplied would be a level a caller could choose. It comes from
    `contracts/design/inference.yaml` and from nowhere else."""
    assert inference.alpha == Decimal("0.05")
