"""The matching — a pure function of the matrix, checked from outside the finished strata.

Three kinds of assertion. The **arithmetic** of the composite distance, worked by hand on
tables small enough to check by eye. The **shape** of the stratification — a partition,
canonical, the declared count, both arms possible everywhere. And the **behaviour** that
makes it a matcher rather than a partitioner: similar units end up together, categorical
levels hold their share of the control arm by allocation, and the answer never depends on
the order anything arrived in.
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from holdout.core.experiment import (
    CovariateKind,
    CovariateMatrix,
    StrataError,
    composite_distance,
    strata_of,
)

NUMERIC_ONLY = (("revenue",), (CovariateKind.NUMERIC,))
MIXED = (("revenue", "format"), (CovariateKind.NUMERIC, CovariateKind.CATEGORICAL))


def numeric_matrix(values: dict[str, int]) -> CovariateMatrix:
    return CovariateMatrix.of(
        *NUMERIC_ONLY, {unit: (Fraction(value),) for unit, value in values.items()}
    )


# ------------------------------------------------------------------ the distance


def test_the_numeric_distance_is_the_squared_gap_over_the_population_variance() -> None:
    """Values 0, 0, 10, 10: mean 5, population variance 25. The distance between an 0 and
    a 10 is `10² / 25 = 4`, and between equals it is zero."""
    matrix = numeric_matrix({"a": 0, "b": 0, "c": 10, "d": 10})
    assert composite_distance(matrix, "a", "c") == Fraction(4)
    assert composite_distance(matrix, "a", "b") == Fraction(0)


def test_a_categorical_mismatch_costs_one_and_agreement_costs_nothing() -> None:
    matrix = CovariateMatrix.of(
        *MIXED,
        {
            "a": (Fraction(10), "hypermarket"),
            "b": (Fraction(10), "hypermarket"),
            "c": (Fraction(10), "convenience"),
            "d": (Fraction(10), "convenience"),
        },
    )
    assert composite_distance(matrix, "a", "b") == Fraction(0)
    assert composite_distance(matrix, "a", "c") == Fraction(1)


def test_a_covariate_with_no_spread_contributes_nothing() -> None:
    """Every unit agrees, so there is nothing to separate on — and no division by zero."""
    matrix = CovariateMatrix.of(
        (("flat", "moving")),
        (CovariateKind.NUMERIC, CovariateKind.NUMERIC),
        {
            "a": (Fraction(7), Fraction(0)),
            "b": (Fraction(7), Fraction(0)),
            "c": (Fraction(7), Fraction(10)),
            "d": (Fraction(7), Fraction(10)),
        },
    )
    assert composite_distance(matrix, "a", "b") == Fraction(0)
    assert composite_distance(matrix, "a", "c") == Fraction(4)


def test_a_distance_to_a_unit_nobody_measured_is_an_error() -> None:
    matrix = numeric_matrix({"a": 1, "b": 2})
    with pytest.raises(StrataError, match="no covariates"):
        composite_distance(matrix, "a", "zzz")


# ------------------------------------------------------------------ the shape


def test_the_strata_partition_the_roster_into_the_declared_count() -> None:
    matrix = numeric_matrix({f"s{i:02d}": 100 + i for i in range(20)})
    strata = strata_of(matrix, 4)
    assert strata is not None
    assert len(strata) == 4
    assert sorted(u for stratum in strata for u in stratum) == sorted(matrix.units)
    assert all(len(stratum) == 5 for stratum in strata)


def test_stratum_sizes_differ_by_at_most_one() -> None:
    matrix = numeric_matrix({f"s{i:02d}": 100 + i for i in range(23)})
    strata = strata_of(matrix, 4)
    assert strata is not None
    assert sorted(len(stratum) for stratum in strata) == [5, 6, 6, 6]


def test_a_share_that_leaves_a_stratum_of_one_is_none_not_an_error() -> None:
    """The genuine refusal: six controls out of ten units cannot all hold both arms."""
    matrix = numeric_matrix({f"s{i:02d}": 100 + i for i in range(10)})
    assert strata_of(matrix, 6) is None
    pairs = strata_of(matrix, 5)
    assert pairs is not None
    assert all(len(stratum) == 2 for stratum in pairs)


def test_a_count_the_caller_got_wrong_is_an_error_not_a_refusal() -> None:
    matrix = numeric_matrix({"a": 1, "b": 2})
    with pytest.raises(StrataError, match="at least one stratum"):
        strata_of(matrix, 0)
    with pytest.raises(StrataError, match="nobody in them"):
        strata_of(matrix, 2)


# ------------------------------------------------------------------ the matching


def test_similar_units_end_up_in_the_same_stratum() -> None:
    """Two obvious clusters, far apart. Any matcher worth the name pairs within them."""
    matrix = numeric_matrix({"a": 100, "b": 101, "c": 102, "d": 900, "e": 901, "f": 902})
    strata = strata_of(matrix, 2)
    assert strata is not None
    assert set(strata) == {("a", "b", "c"), ("d", "e", "f")}


def test_categorical_levels_hold_their_share_of_the_control_arm_by_allocation() -> None:
    """The property the distance alone cannot buy, stated as counts.

    Twenty hypermarkets and ten convenience stores at six strata: the allocation gives the
    formats four and two strata — their proportional share — so every stratum is pure and
    every draw's control arm carries exactly four hypermarkets and two convenience stores.
    A fixed-size matcher would have had to mix the leftovers, and the mixed strata are
    exactly where a level's control count starts moving between draws.
    """
    rows: dict[str, tuple[Fraction | str, ...]] = {}
    for i in range(20):
        rows[f"h{i:02d}"] = (Fraction(6000 + 10 * i), "hypermarket")
    for i in range(10):
        rows[f"c{i:02d}"] = (Fraction(500 + 10 * i), "convenience")
    matrix = CovariateMatrix.of(*MIXED, rows)
    strata = strata_of(matrix, 6)
    assert strata is not None
    pure_hyper = [s for s in strata if all(u.startswith("h") for u in s)]
    pure_conv = [s for s in strata if all(u.startswith("c") for u in s)]
    assert len(pure_hyper) == 4
    assert len(pure_conv) == 2
    assert len(pure_hyper) + len(pure_conv) == len(strata)


def test_a_cell_too_small_for_a_stratum_joins_its_neighbours() -> None:
    """One store of a level nobody else has cannot hold a stratum of its own; it attaches
    to the nearest formed stratum instead of forcing a stratum of one."""
    rows: dict[str, tuple[Fraction | str, ...]] = {
        f"s{i:02d}": (Fraction(100 + i), "supermarket") for i in range(9)
    }
    rows["odd"] = (Fraction(104), "hypermarket")
    matrix = CovariateMatrix.of(*MIXED, rows)
    strata = strata_of(matrix, 2)
    assert strata is not None
    assert len(strata) == 2
    assert sorted(u for stratum in strata for u in stratum) == sorted(matrix.units)


def test_a_roster_of_singleton_cells_falls_back_to_one_pool() -> None:
    """Every unit its own level: no cell can hold a stratum, so the allocation degenerates
    and the whole roster is matched as one pool on the full composite distance."""
    rows: dict[str, tuple[Fraction | str, ...]] = {
        f"s{i:02d}": (Fraction(100 + i), f"level-{i:02d}") for i in range(12)
    }
    matrix = CovariateMatrix.of(*MIXED, rows)
    strata = strata_of(matrix, 3)
    assert strata is not None
    assert len(strata) == 3
    assert sorted(u for stratum in strata for u in stratum) == sorted(matrix.units)


def test_the_strata_are_canonical_and_ignore_arrival_order() -> None:
    """A stratification that moved between runs would be an assignment that cannot be
    reproduced, so the answer is a value: sorted inside, sorted outside, and indifferent
    to the order the rows were written in."""
    forwards = {f"s{i:02d}": 100 + i for i in range(12)}
    backwards = dict(reversed(list(forwards.items())))
    first = strata_of(numeric_matrix(forwards), 3)
    second = strata_of(numeric_matrix(backwards), 3)
    assert first == second
    assert first is not None
    assert list(first) == sorted(first)
    assert all(list(stratum) == sorted(stratum) for stratum in first)
