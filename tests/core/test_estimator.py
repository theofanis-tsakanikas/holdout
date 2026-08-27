"""The number: the difference of means, Lin's adjustment, the p-value and the interval.

Everything here is checked against arithmetic a reader can finish by hand, on tables small
enough to hold in the head. The design matrices are built **here**, not taken from the
shared fixture: the fixture's covariates are all functions of one block, so its adjustment
has rank two and three of its columns are dropped as dependent. That exercises the dropping
path on every composition run and proves nothing about the adjustment, so the adjustment is
attacked separately, with covariates that carry real information.

What these tests do **not** do is validate the estimator. A difference of means over
randomly assigned units is unbiased under any data-generating process — that is a theorem,
not something a suite establishes. What is checked is that the machinery around it computes
what it says it computes: exactly, deterministically, and with no tolerance anywhere.
"""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction

import pytest

from holdout.core.design import MdeDirection
from holdout.core.experiment import (
    Arm,
    CovariateKind,
    CovariateMatrix,
    Design,
    EstimatorError,
    adjusted_difference,
    design_of,
    difference_in_means,
    interval,
    permutation_p,
    plan_for,
    studentized,
)

ALPHA = Decimal("0.05")


def arms_of(treated: tuple[str, ...], control: tuple[str, ...]) -> dict[str, Arm]:
    return {**dict.fromkeys(treated, Arm.TREATMENT), **dict.fromkeys(control, Arm.CONTROL)}


def one_numeric(values: dict[str, int]) -> Design:
    matrix = CovariateMatrix.of(
        ("revenue",),
        (CovariateKind.NUMERIC,),
        {unit: (Fraction(value),) for unit, value in values.items()},
    )
    return design_of(matrix)


def no_information(units: tuple[str, ...]) -> Design:
    """A design whose one covariate is constant, so the adjustment has nothing to adjust on.

    Its column is dependent on the intercept and gets dropped, which makes the adjusted
    estimate exactly the difference of means — the property asserted below.
    """
    matrix = CovariateMatrix.of(
        ("revenue",), (CovariateKind.NUMERIC,), dict.fromkeys(units, (Fraction(1),))
    )
    return design_of(matrix)


# ------------------------------------------------------------------ the difference itself


def test_the_difference_of_means_on_a_table_small_enough_to_check_by_eye() -> None:
    """Treated 10 and 20, control 1 and 3. Means 15 and 2, so the difference is 13."""
    outcomes = {"a": 10, "b": 20, "c": 1, "d": 3}
    assert difference_in_means(outcomes, arms_of(("a", "b"), ("c", "d"))) == Fraction(13)


def test_the_difference_is_exact_where_the_means_are_not_whole() -> None:
    """One third and two thirds are not representable in binary, which is the whole reason
    the arithmetic is `Fraction` and never `float`."""
    outcomes = {"a": 1, "b": 1, "c": 1, "d": 0, "e": 0, "f": 1}
    result = difference_in_means(outcomes, arms_of(("a", "b", "c"), ("d", "e", "f")))
    assert result == Fraction(2, 3)


def test_an_empty_arm_has_nothing_to_take_a_difference_of() -> None:
    with pytest.raises(EstimatorError, match="an arm is empty"):
        difference_in_means({"a": 1, "b": 2}, arms_of(("a", "b"), ()))


# ------------------------------------------------------------------ Lin's adjustment


def test_the_adjusted_estimate_solves_a_two_covariate_system_by_hand() -> None:
    """Six units, one covariate, an outcome that is exactly `2 x + 10 x 1{treated}`.

    The covariate is deliberately imbalanced — the treated arm carries 1, 2, 3 and the
    control arm 4, 5, 6 — so the unadjusted difference is wrong by `2 x (2 - 5) = -6`: it
    reports 4 where the effect is 10. The adjustment fits `y = a + b x` inside each arm,
    finds `b = 2` in both, and compares the two fits at the grand mean of 3.5. That gives
    exactly 10, because the model is exactly right.

    A worked case with an exact answer is the point: an adjustment that returned 9.97 would
    be an adjustment computing something else.
    """
    covariates = {"t1": 1, "t2": 2, "t3": 3, "c1": 4, "c2": 5, "c3": 6}
    arms = arms_of(("t1", "t2", "t3"), ("c1", "c2", "c3"))
    outcomes = {
        unit: 2 * value + (10 if arms[unit] is Arm.TREATMENT else 0)
        for unit, value in covariates.items()
    }
    design = one_numeric(covariates)
    assert difference_in_means(outcomes, arms) == Fraction(4)
    assert adjusted_difference(outcomes, arms, design) == Fraction(10)


def test_with_no_usable_covariate_the_adjustment_is_the_difference_of_means() -> None:
    """A constant column is dependent on the intercept, so it is dropped and its coefficient
    is zero. Lin's estimator then reduces to the thing it is an adjustment of."""
    outcomes = {"a": 10, "b": 20, "c": 1, "d": 3}
    arms = arms_of(("a", "b"), ("c", "d"))
    design = no_information(tuple(outcomes))
    assert adjusted_difference(outcomes, arms, design) == difference_in_means(outcomes, arms)


def test_a_dependent_column_is_dropped_and_changes_no_fitted_value() -> None:
    """A column that is twice another adds nothing to the column space, so the estimate must
    not move. This is the ordinary case in real data — a categorical level no unit in one arm
    happens to take — and an implementation that raised on it would refuse most experiments.
    """
    base = {"t1": 1, "t2": 2, "t3": 3, "c1": 2, "c2": 3, "c3": 4}
    arms = arms_of(("t1", "t2", "t3"), ("c1", "c2", "c3"))
    outcomes = {unit: 5 * value + 7 for unit, value in base.items()}
    lean = one_numeric(base)
    duplicated = design_of(
        CovariateMatrix.of(
            ("revenue", "revenue_twice"),
            (CovariateKind.NUMERIC, CovariateKind.NUMERIC),
            {unit: (Fraction(v), Fraction(2 * v)) for unit, v in base.items()},
        )
    )
    assert adjusted_difference(outcomes, arms, duplicated) == adjusted_difference(
        outcomes, arms, lean
    )


def test_a_categorical_covariate_becomes_indicators_with_the_first_level_as_reference() -> None:
    """Sorted, so the reference level is the same on every machine — and dropped, because
    keeping every level makes the intercept a combination of them by construction."""
    matrix = CovariateMatrix.of(
        ("format",),
        (CovariateKind.CATEGORICAL,),
        {"a": ("convenience",), "b": ("hypermarket",), "c": ("supermarket",)},
    )
    design = design_of(matrix)
    assert design.columns == ("format=hypermarket", "format=supermarket")


def test_adjusting_on_more_columns_than_an_arm_has_units_is_an_error() -> None:
    """It does not produce a wide interval; it produces no interval at all, because there
    is nothing left to estimate a variance from. Saying so is better than dividing by zero.
    """
    base = {"t1": 1, "t2": 2, "c1": 3, "c2": 4}
    design = design_of(
        CovariateMatrix.of(
            ("a", "b", "c"),
            (CovariateKind.NUMERIC,) * 3,
            {
                "t1": (Fraction(1), Fraction(5), Fraction(9)),
                "t2": (Fraction(2), Fraction(3), Fraction(1)),
                "c1": (Fraction(4), Fraction(1), Fraction(7)),
                "c2": (Fraction(8), Fraction(2), Fraction(2)),
            },
        )
    )
    outcomes = {unit: 10 * value for unit, value in base.items()}
    with pytest.raises(EstimatorError, match="nothing left to estimate a variance from"):
        studentized(outcomes, arms_of(("t1", "t2"), ("c1", "c2")), design)


def test_a_unit_in_the_design_with_no_outcome_is_an_error() -> None:
    """Attrition treated as if it never happened would be a unit silently dropped from the
    mean, which is the most flattering possible way to lose data."""
    design = one_numeric({"a": 1, "b": 2, "c": 3, "d": 4})
    with pytest.raises(EstimatorError, match="report no outcome"):
        studentized({"a": 1, "b": 2, "c": 3}, arms_of(("a", "b"), ("c", "d")), design)


# ------------------------------------------------------------------ the studentization


def test_the_statistic_is_the_difference_over_the_standard_error() -> None:
    """No covariate, so the fit is the arm mean and the residuals are the deviations.

    Treated 10, 12, 14: mean 12, residual sum of squares 8, one degree of freedom used, so
    `s²_T = 8 / 2 = 4` and `s²_T / n_T = 4/3`. Control 4, 6, 8: identical spread, so the
    variance of the difference is `8/3` and the difference is 6. `T² = 36 / (8/3) = 13.5`.
    """
    outcomes = {"t1": 10, "t2": 12, "t3": 14, "c1": 4, "c2": 6, "c3": 8}
    arms = arms_of(("t1", "t2", "t3"), ("c1", "c2", "c3"))
    result = studentized(outcomes, arms, no_information(tuple(outcomes)))
    assert result.difference == Fraction(6)
    assert result.variance == Fraction(8, 3)
    assert result.squared == Fraction(27, 2)
    assert result.sign == 1


def test_a_negative_difference_carries_its_sign() -> None:
    outcomes = {"t1": 4, "t2": 6, "c1": 10, "c2": 12}
    result = studentized(
        outcomes, arms_of(("t1", "t2"), ("c1", "c2")), no_information(tuple(outcomes))
    )
    assert result.sign == -1
    assert result.difference == Fraction(-6)
    assert result.value is not None and result.value < 0


def test_a_perfect_fit_with_a_difference_is_unbounded_rather_than_large() -> None:
    """Zero residual spread in both arms and the arms differ. `T` is not a big number, it is
    undefined — and `None` is read as more extreme than any finite value everywhere it is
    compared, so a permuted draw like this counts as a hit rather than as a miss.
    """
    outcomes = {"t1": 10, "t2": 10, "c1": 4, "c2": 4}
    result = studentized(
        outcomes, arms_of(("t1", "t2"), ("c1", "c2")), no_information(tuple(outcomes))
    )
    assert result.squared is None
    assert result.value is None


def test_the_standard_error_is_what_realised_power_is_judged_against() -> None:
    """`d >= (z_a + z_b) x se`, compared as squares so nothing takes a square root and
    nothing needs a tolerance."""
    outcomes = {"t1": 10, "t2": 12, "t3": 14, "c1": 4, "c2": 6, "c3": 8}
    result = studentized(
        outcomes,
        arms_of(("t1", "t2", "t3"), ("c1", "c2", "c3")),
        no_information(tuple(outcomes)),
    )
    z_sum = Fraction(28) / 10
    assert result.detects(Fraction(100), z_sum)
    assert not result.detects(Fraction(1), z_sum)


# ------------------------------------------------------------------ the permutation test


@pytest.fixture
def small() -> tuple[Design, dict[str, Arm], dict[str, int]]:
    units = tuple(f"u{i}" for i in range(8))
    design = no_information(units)
    arms = arms_of(units[:4], units[4:])
    outcomes = {unit: 100 + 10 * index for index, unit in enumerate(units)}
    return design, arms, outcomes


def test_the_p_value_is_one_plus_hits_over_one_plus_b_exactly(
    small: tuple[Design, dict[str, Arm], dict[str, int]],
) -> None:
    """Not approximately. The rule is what makes the level exact at any B, so it is asserted
    as an equality of rationals rather than as a number close to one."""
    design, arms, outcomes = small
    draws = _all_splits(design, count=9)
    plan = plan_for(design, draws)
    observed = studentized(outcomes, arms, design)
    p = permutation_p(observed, plan, outcomes, direction=MdeDirection.EITHER)
    # `Fraction` reduces, so 2/10 arrives as 1/5 — the assertion is over the unreduced
    # rational the rule produces, not over the shape it happens to be stored in.
    scaled = p * (1 + plan.size)
    assert scaled.denominator == 1
    assert 1 <= scaled.numerator <= 1 + plan.size


def test_b_buys_resolution_and_not_validity(
    small: tuple[Design, dict[str, Arm], dict[str, int]],
) -> None:
    """The smallest attainable p-value is `1 / (1 + B)`, so B decides how small a p-value can
    get and nothing else. It is the reason the readout prints B beside the p-value."""
    design, arms, outcomes = small
    observed = studentized(outcomes, arms, design)
    for count in (4, 9, 19):
        plan = plan_for(design, _all_splits(design, count=count))
        p = permutation_p(observed, plan, outcomes, direction=MdeDirection.EITHER)
        assert p >= Fraction(1, 1 + count)


def test_a_one_sided_test_counts_only_draws_in_the_declared_direction(
    small: tuple[Design, dict[str, Arm], dict[str, int]],
) -> None:
    """A design that declared a direction gets the p-value its own hypothesis asked for, not
    half of a two-sided one and not the mirror of it."""
    design, arms, outcomes = small
    plan = plan_for(design, _all_splits(design, count=15))
    observed = studentized(outcomes, arms, design)
    up = permutation_p(observed, plan, outcomes, direction=MdeDirection.INCREASE)
    down = permutation_p(observed, plan, outcomes, direction=MdeDirection.DECREASE)
    both = permutation_p(observed, plan, outcomes, direction=MdeDirection.EITHER)
    assert up != down
    assert min(up, down) <= both


def test_an_empty_reference_set_is_an_error(
    small: tuple[Design, dict[str, Arm], dict[str, int]],
) -> None:
    """`(1 + hits) / (1 + 0)` is not a p-value, it is the number 1."""
    design, _, _ = small
    with pytest.raises(EstimatorError, match="empty reference set"):
        plan_for(design, [])


def test_the_plan_is_computed_once_and_reused(
    small: tuple[Design, dict[str, Arm], dict[str, int]],
) -> None:
    """The structural half of "the same draws are reused at every step of the bisection".

    A plan holds one entry per draw, and each entry is the arm split and its factorisation —
    the half that does not depend on the outcomes. Asserting the shape here is what stops a
    later edit quietly rebuilding it inside the loop.
    """
    design, _, _ = small
    draws = _all_splits(design, count=6)
    plan = plan_for(design, draws)
    assert plan.size == len(draws)
    assert len(plan.plans) == len(draws)
    assert plan.design is design


def _all_splits(design: Design, *, count: int) -> list[dict[str, Arm]]:
    """`count` distinct even splits of the roster, **spread across the whole enumeration**.

    Enumerated rather than drawn, because this file is about the arithmetic: the screened
    reference set is `assignment.reference_set`'s job and is tested there.

    The stride is the part that matters and it cost an afternoon. Taking the *first* `count`
    combinations gives a reference set in which every draw shares most of its treated units
    with every other, because `itertools.combinations` varies the last position first. The
    permutation distribution is then nearly a point mass, no shift is ever rejected, and the
    interval comes back unbounded — which is the correct answer to the question that
    degenerate reference set asks, and not the question the test meant to ask.
    """
    from itertools import combinations
    from math import comb

    units = design.units
    half = len(units) // 2
    stride = max(1, comb(len(units), half) // count)
    out: list[dict[str, Arm]] = []
    for index, treated in enumerate(combinations(units, half)):
        if index % stride:
            continue
        out.append(arms_of(treated, tuple(u for u in units if u not in treated)))
        if len(out) == count:
            break
    return out


# ------------------------------------------------------------------ the interval


def test_the_interval_endpoints_are_integers_that_bracket_the_point_estimate() -> None:
    """Termination at one canonical metric unit, so there is nothing to round.

    Both endpoints are integers in the metric's own unit and the point estimate lies between
    them. An interval that did not contain its own point estimate would be an interval
    inverted around a different statistic.
    """
    units = tuple(f"u{i}" for i in range(10))
    design = no_information(units)
    arms = arms_of(units[:5], units[5:])
    outcomes = {unit: 100 + 7 * index for index, unit in enumerate(units)}
    plan = plan_for(design, _all_splits(design, count=40))
    low, high = interval(outcomes, arms, plan, alpha=ALPHA)
    assert isinstance(low, int) and isinstance(high, int)
    point = difference_in_means(outcomes, arms)
    assert low <= point <= high


def test_a_larger_effect_moves_the_interval_and_does_not_widen_it_without_reason() -> None:
    """Shifting every treated outcome by a constant shifts the whole interval by the same
    constant: the statistic is a difference, and adding a constant to one arm adds it to the
    difference. An interval that did not move with it would be an interval computed on
    something other than the shift it is inverting.
    """
    units = tuple(f"u{i}" for i in range(10))
    design = no_information(units)
    arms = arms_of(units[:5], units[5:])
    base = {unit: 100 + 7 * index for index, unit in enumerate(units)}
    lifted = {
        unit: value + (500 if arms[unit] is Arm.TREATMENT else 0) for unit, value in base.items()
    }
    plan = plan_for(design, _all_splits(design, count=40))
    low, high = interval(base, arms, plan, alpha=ALPHA)
    lifted_low, lifted_high = interval(lifted, arms, plan, alpha=ALPHA)
    assert lifted_low == low + 500
    assert lifted_high == high + 500


def test_the_interval_is_deterministic() -> None:
    """The same draws at every step, so the endpoints are the same integers every run —
    which is what lets a readout be re-read a year later and argued with.

    Eighty draws rather than thirty, because the mirror assignment ties with the realised
    one under a large shift and the attainable p-value floor is therefore `2 / (1 + B)`.
    At B = 30 that floor is 0.065, no shift is ever rejected at alpha = 0.05, and the
    interval is correctly unbounded. See `estimator.py`.
    """
    units = tuple(f"u{i}" for i in range(10))
    design = no_information(units)
    arms = arms_of(units[:5], units[5:])
    outcomes = {unit: 100 + 7 * index for index, unit in enumerate(units)}
    plan = plan_for(design, _all_splits(design, count=80))
    assert interval(outcomes, arms, plan, alpha=ALPHA) == interval(
        outcomes, arms, plan, alpha=ALPHA
    )


def test_a_wider_alpha_gives_a_narrower_interval() -> None:
    """Inversion, so the two move together by construction: a test that rejects more shifts
    leaves fewer of them inside the interval.

    Both levels have to sit above `2 / (1 + B)` or neither interval is bounded — the floor
    the mirror assignment imposes, argued in `estimator.py`.
    """
    units = tuple(f"u{i}" for i in range(10))
    design = no_information(units)
    arms = arms_of(units[:5], units[5:])
    outcomes = {unit: 100 + 7 * index for index, unit in enumerate(units)}
    plan = plan_for(design, _all_splits(design, count=100))
    tight = interval(outcomes, arms, plan, alpha=Decimal("0.30"))
    loose = interval(outcomes, arms, plan, alpha=Decimal("0.05"))
    assert loose[0] <= tight[0] <= tight[1] <= loose[1]
