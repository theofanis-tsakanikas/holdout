"""The standardised difference, worked by hand — and the check that re-measures.

Two halves.

The first is the arithmetic, on tables small enough to check by eye, on both covariate
types, plus the two degenerate cases that a "just divide" implementation gets wrong: zero
spread with equal arms, and zero spread with unequal ones.

The second is the half that matters. **The readout's balance check is not the design's
figures read back.** An assignment re-checked against the matrix its strata were built from
passes almost by construction, which is a gate that can barely bite — the family of defect
this project has now found four times, and the reason CLAUDE.md carries a section about it.
So each of the three ways the data actually moves between design and readout is planted here
and the check has to go red: restated pre-period covariates, an attrited store, and a roster
that gained one.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from fractions import Fraction
from hashlib import blake2b

import pytest
from corpus.world.chain import build as build_chain
from corpus.world.scale import Scale
from corpus.world.worlds import REALISTIC_CLUSTERED_PCT

from holdout.core.experiment import (
    Arm,
    BalanceError,
    CovariateKind,
    CovariateMatrix,
    attainable,
    candidate,
    standardised,
    strata_of,
    worst_of,
)

TOLERANCE = Decimal("0.10")


def within_tolerance(matrix: CovariateMatrix, arms: dict[str, Arm], tolerance: Decimal) -> bool:
    """What the readout's balance check decides: no covariate exceeds the tolerance."""
    return not any(s.exceeds(tolerance) for s in standardised(matrix, arms))


NUMERIC_ONLY = (("revenue",), (CovariateKind.NUMERIC,))
CATEGORICAL_ONLY = (("format",), (CovariateKind.CATEGORICAL,))


def numeric_matrix(values: dict[str, int]) -> CovariateMatrix:
    return CovariateMatrix.of(
        *NUMERIC_ONLY, {unit: (Fraction(value),) for unit, value in values.items()}
    )


def categorical_matrix(levels: dict[str, str]) -> CovariateMatrix:
    return CovariateMatrix.of(*CATEGORICAL_ONLY, {unit: (level,) for unit, level in levels.items()})


def arms_of(treated: tuple[str, ...], control: tuple[str, ...]) -> dict[str, Arm]:
    return {**dict.fromkeys(treated, Arm.TREATMENT), **dict.fromkeys(control, Arm.CONTROL)}


# ------------------------------------------------------------------ the arithmetic


def test_a_numeric_difference_matches_the_formula_worked_by_hand() -> None:
    """Treated 10 and 20, control 30 and 40.

    Means 15 and 35, so the difference is 20. Each arm's population variance is 25, so the
    pooled variance is 25 and the pooled spread is 5. The standardised difference is
    20 / 5 = 4, and its square — which is what the comparison actually uses — is 16.
    """
    matrix = numeric_matrix({"a": 10, "b": 20, "c": 30, "d": 40})
    result = standardised(matrix, arms_of(("a", "b"), ("c", "d")))[0]
    assert result.squared == Fraction(16)
    assert result.value == Decimal(4)
    assert result.exceeds(TOLERANCE)


def test_perfectly_balanced_arms_score_zero() -> None:
    matrix = numeric_matrix({"a": 10, "b": 20, "c": 10, "d": 20})
    result = standardised(matrix, arms_of(("a", "b"), ("c", "d")))[0]
    assert result.squared == 0
    assert not result.exceeds(TOLERANCE)


def test_a_categorical_difference_is_the_indicator_s_own_standardised_difference() -> None:
    """Four treated, two of them hypermarkets; four control, all four hypermarkets.

    `p_T = 0.5`, `p_C = 1`, so the difference is 0.5. The indicator's variance is `p(1 - p)`:
    0.25 in the treated arm and 0 in the control arm, so the pooled variance is 0.125 and the
    standardised difference squared is `0.25 / 0.125 = 2`.

    **This is the number that distinguishes the two conventions**, which is why it is the
    worked example. Pooling the proportions first — `p̄ = 0.75`, spread `sqrt(3)/4` — would
    give 4/3 instead. `balance.py` says which one it computes and why; this asserts it.
    """
    matrix = categorical_matrix(
        {
            "t1": "hypermarket",
            "t2": "hypermarket",
            "t3": "convenience",
            "t4": "convenience",
            "c1": "hypermarket",
            "c2": "hypermarket",
            "c3": "hypermarket",
            "c4": "hypermarket",
        }
    )
    result = standardised(matrix, arms_of(("t1", "t2", "t3", "t4"), ("c1", "c2", "c3", "c4")))[0]
    assert result.squared == Fraction(2)


def test_a_categorical_reports_the_level_that_maximised_it() -> None:
    """So a refusal can name the level. Three levels, and the worst one is the answer."""
    matrix = categorical_matrix(
        {
            "t1": "a",
            "t2": "a",
            "t3": "b",
            "t4": "c",
            "c1": "b",
            "c2": "b",
            "c3": "b",
            "c4": "c",
        }
    )
    result = standardised(matrix, arms_of(("t1", "t2", "t3", "t4"), ("c1", "c2", "c3", "c4")))[0]
    assert result.level in {"a", "b"}
    assert result.exceeds(TOLERANCE)


def test_the_level_reported_does_not_depend_on_iteration_order() -> None:
    """Levels are sorted rather than first-seen, so the reported level — and the reference
    level the estimator drops — is the same on every machine and in every process."""
    forwards = categorical_matrix({"t1": "a", "t2": "b", "c1": "b", "c2": "a"})
    assert forwards.levels("format") == ("a", "b")


# ------------------------------------------------------------------ the degenerate cases


def test_no_spread_and_no_difference_is_perfect_balance() -> None:
    """Every unit identical. `0/0` has an obvious answer here and it is zero."""
    matrix = numeric_matrix({"a": 7, "b": 7, "c": 7, "d": 7})
    result = standardised(matrix, arms_of(("a", "b"), ("c", "d")))[0]
    assert result.squared == 0
    assert not result.exceeds(TOLERANCE)


def test_no_spread_and_a_difference_is_undefined_and_never_admissible() -> None:
    """The most extreme imbalance the statistic can describe, and the one an implementation
    that "just divides" would report as zero or crash on.

    Each arm is constant and the two constants differ, so the pooled spread is zero and the
    difference is not. That is not a small standardised difference; it is an infinite one,
    and reading it as zero would wave through exactly the assignment the screen exists to
    reject.
    """
    matrix = numeric_matrix({"a": 10, "b": 10, "c": 20, "d": 20})
    result = standardised(matrix, arms_of(("a", "b"), ("c", "d")))[0]
    assert result.squared is None
    assert result.value is None
    assert result.exceeds(TOLERANCE)
    assert result.exceeds(Decimal(1000)), "no tolerance admits an undefined difference"


def test_the_worst_covariate_is_the_undefined_one_where_there_is_one() -> None:
    finite = numeric_matrix({"a": 10, "b": 20, "c": 11, "d": 21})
    degenerate = numeric_matrix({"a": 10, "b": 10, "c": 20, "d": 20})
    arms = arms_of(("a", "b"), ("c", "d"))
    both = (*standardised(finite, arms), *standardised(degenerate, arms))
    assert worst_of(both).squared is None


# ------------------------------------------------------------------ the inputs it refuses


def test_an_empty_arm_is_an_error_and_not_a_small_number() -> None:
    matrix = numeric_matrix({"a": 10, "b": 20})
    with pytest.raises(BalanceError, match="an arm is empty"):
        standardised(matrix, arms_of(("a", "b"), ()))


def test_a_unit_with_covariates_and_no_arm_is_an_error() -> None:
    """It would be balanced into neither arm — a unit silently dropped from the check,
    which is the shape of defect this whole file exists to catch."""
    matrix = numeric_matrix({"a": 10, "b": 20, "c": 30})
    with pytest.raises(BalanceError, match="covariates and no arm"):
        standardised(matrix, arms_of(("a",), ("b",)))


def test_a_unit_missing_a_covariate_is_refused_at_construction() -> None:
    with pytest.raises(BalanceError, match="value\\(s\\) for"):
        CovariateMatrix.of(
            ("x", "y"),
            (CovariateKind.NUMERIC, CovariateKind.NUMERIC),
            {"a": (Fraction(1), Fraction(2)), "b": (Fraction(1),)},
        )


def test_a_float_never_reaches_the_statistic() -> None:
    """Numeric covariates arrive as `Fraction` so the comparison of squares stays exact.
    The first binary approximation would put a tolerance back into a comparison built to
    avoid one."""
    with pytest.raises(BalanceError, match="arrive as Fraction"):
        CovariateMatrix.of(
            ("x",),
            (CovariateKind.NUMERIC,),
            {"a": (1.5,), "b": (Fraction(2),)},  # type: ignore[dict-item]
        )


def test_a_categorical_level_is_named_and_never_numbered() -> None:
    with pytest.raises(BalanceError, match="named, never numbered"):
        CovariateMatrix.of(("x",), (CovariateKind.CATEGORICAL,), {"a": (Fraction(1),), "b": ("b",)})


def test_an_empty_covariate_list_would_make_every_check_pass() -> None:
    with pytest.raises(BalanceError, match="at least one covariate"):
        CovariateMatrix.of((), (), {})


# ------------------------------------------------------------------ the check


def test_the_check_judges_every_covariate_and_not_an_average() -> None:
    """Per covariate, not on average. An assignment balanced on four and badly wrong on the
    fifth is badly wrong."""
    matrix = CovariateMatrix.of(
        ("balanced", "skewed"),
        (CovariateKind.NUMERIC, CovariateKind.NUMERIC),
        {
            "a": (Fraction(10), Fraction(1)),
            "b": (Fraction(20), Fraction(2)),
            "c": (Fraction(10), Fraction(100)),
            "d": (Fraction(20), Fraction(200)),
        },
    )
    arms = arms_of(("a", "b"), ("c", "d"))
    differences = standardised(matrix, arms)
    assert not differences[0].exceeds(TOLERANCE), "the balanced covariate is balanced"
    assert differences[1].exceeds(TOLERANCE), "the skewed one is what fails the check"
    assert not within_tolerance(matrix, arms, TOLERANCE)


# ---------------------------------------- the check re-measures, and that is what bites


@pytest.fixture
def balanced() -> tuple[CovariateMatrix, dict[str, Arm]]:
    """A matrix and an assignment inside the tolerance at design time."""
    matrix = numeric_matrix({f"s{i}": 100 + (i % 2) for i in range(12)})
    arms = arms_of(
        tuple(f"s{i}" for i in range(12) if i % 4 in (0, 1)),
        tuple(f"s{i}" for i in range(12) if i % 4 in (2, 3)),
    )
    assert within_tolerance(matrix, arms, TOLERANCE)
    return matrix, arms


def test_re_checking_against_the_design_s_own_matrix_proves_nothing(
    balanced: tuple[CovariateMatrix, dict[str, Arm]],
) -> None:
    """Stated as a test so the point of the three below is unmistakable.

    This is the gate that cannot bite. If `close` re-checked the matrix the strata were
    built from, the balance check would be green on every experiment whose design was, and
    would have proved nothing about what actually arrived.
    """
    matrix, arms = balanced
    assert within_tolerance(matrix, arms, TOLERANCE)


def test_restated_covariates_turn_the_check_red(
    balanced: tuple[CovariateMatrix, dict[str, Arm]],
) -> None:
    """Doctrine rule 4 in action: late data restates, and the pre-period revenue the strata
    were built from is not the pre-period revenue the readout reads. A restatement large
    enough to unbalance the arms has to be visible, because the estimate is now carrying
    it."""
    _, arms = balanced
    restated = numeric_matrix(
        {f"s{i}": (900 if arms[f"s{i}"] is Arm.TREATMENT else 100) for i in range(12)}
    )
    assert not within_tolerance(restated, arms, TOLERANCE)


def test_an_attrited_store_turns_the_check_red(
    balanced: tuple[CovariateMatrix, dict[str, Arm]],
) -> None:
    """The units that reported are not the units that were assigned. Balance held over the
    assigned set says nothing about the set that actually produced the numbers."""
    matrix = numeric_matrix({f"s{i}": (1000 if i in (0, 1) else 100 + (i % 2)) for i in range(12)})
    _, arms = balanced
    reported = frozenset(matrix.units) - {"s2", "s3", "s6"}
    remaining = {unit: arm for unit, arm in arms.items() if unit in reported}
    assert not within_tolerance(matrix.restricted_to(reported), remaining, TOLERANCE)


def test_a_roster_that_moved_turns_the_check_red(
    balanced: tuple[CovariateMatrix, dict[str, Arm]],
) -> None:
    """A store opened, or a store id changed, and the arms no longer describe the roster.
    A check that quietly balanced whatever it found would be balancing a different
    experiment."""
    matrix, arms = balanced
    moved = dict(matrix.rows)
    moved["s99"] = (Fraction(50_000),)
    grown = CovariateMatrix.of(matrix.ids, matrix.kinds, moved)
    with pytest.raises(BalanceError, match="covariates and no arm"):
        standardised(grown, arms)


def test_restricting_to_units_that_do_not_exist_is_an_error() -> None:
    matrix = numeric_matrix({"a": 1, "b": 2})
    with pytest.raises(BalanceError, match="no covariates for"):
        matrix.restricted_to(frozenset({"a", "zzz"}))


# ------------------------------- what no draw could have reached (T00D)
#
# The guard's case is not this file's idea of a bad roster. The categorical composition
# comes from `corpus.world.chain`, drawn by the corpus's own keyed hashing with nobody
# choosing it, and the control count that breaks is found by **search** rather than named:
# the defect it was written for was found on a roster nobody designed either, at 25 controls
# on the corpus, where `store_format=hypermarket` sat at a constant 0.1734 across two
# hundred draws. CLAUDE.md's checklist asks who wrote the case a guard is tested on; the
# answer here is the chain's rng and a loop.
#
# Only the two categorical covariates decide the bound. The two numeric columns are filled
# from a hash so the matcher has something to separate on — they change which unit lands in
# which stratum and they can change nothing about `attainable`, which never reads them.

CORPUS_IDS = ("category_revenue_8w", "store_format", "store_size_sqm", "waste_rate", "pricing_zone")
#: The contract's declared order — numeric, categorical, numeric, numeric, categorical.
CORPUS_KINDS = (
    CovariateKind.NUMERIC,
    CovariateKind.CATEGORICAL,
    CovariateKind.NUMERIC,
    CovariateKind.NUMERIC,
    CovariateKind.CATEGORICAL,
)


#: One SKU over one week: `chain.build` never emits an event, so this costs milliseconds and
#: the stores it lays out are exactly the ones the scenario scale would.
def corpus_roster(stores: int) -> CovariateMatrix:
    chain = build_chain(
        "holdout-w-0001",
        Scale("t00d", stores, 1, 7, date(2025, 9, 1)),
        clustered_pct=REALISTIC_CLUSTERED_PCT,
    )

    def vary(tag: str, store_id: str, span: int) -> int:
        return (
            int.from_bytes(blake2b(f"{tag}-{store_id}".encode(), digest_size=4).digest(), "big")
            % span
        )

    rows: dict[str, tuple[Fraction | str, ...]] = {}
    for store in chain.stores:
        size = round(store.size_index * 1000)
        rows[store.store_id] = (
            Fraction(size * 12 + vary("revenue", store.store_id, size * 3)),
            store.store_format,
            Fraction(size),
            Fraction(200 + vary("waste", store.store_id, 400), 10_000),
            store.pricing_zone,
        )
    return CovariateMatrix.of(CORPUS_IDS, CORPUS_KINDS, rows)


def _reaches(
    matrix: CovariateMatrix, strata: tuple[tuple[str, ...], ...], tolerance: Decimal
) -> bool:
    reachable = attainable(matrix, strata)
    return not any(s.exceeds(tolerance) for s in reachable)


def _scan(matrix: CovariateMatrix, tolerance: Decimal) -> dict[int, bool]:
    """Every control count from a fifth of the roster down and up, and whether it is reachable."""
    out: dict[int, bool] = {}
    for controls in range(len(matrix.units) // 6, len(matrix.units) // 3):
        strata = strata_of(matrix, controls)
        if strata is None:
            continue
        out[controls] = _reaches(matrix, strata, tolerance)
    return out


def test_some_control_count_is_out_of_reach_and_it_was_not_chosen() -> None:
    """The non-vacuity half: searching finds at least one, and at least one the other way.

    A guard that refused every control count would be indistinguishable from a broken one,
    and a guard that refused none would never have caught the defect it was written for. So
    the scan has to come back mixed, and neither side is named in advance.
    """
    matrix = corpus_roster(100)
    scanned = _scan(matrix, TOLERANCE)
    assert scanned, "no control count produced a stratification at all"
    unreachable = sorted(c for c, ok in scanned.items() if not ok)
    reachable = sorted(c for c, ok in scanned.items() if ok)
    assert unreachable, (
        f"every control count in {sorted(scanned)} is reachable, so this roster cannot arm "
        "the guard and the two tests below would pass vacuously"
    )
    assert reachable, (
        f"no control count in {sorted(scanned)} is reachable — the bound is refusing "
        "everything, which is a broken guard rather than a strict one"
    )


def test_nothing_the_bound_refuses_could_have_been_drawn() -> None:
    """Soundness, corroborated by the lottery rather than by the arithmetic that claims it.

    For every control count the bound calls unreachable, two hundred real draws are taken
    and every one of them must fail the readout's balance check. If a single draw passed,
    the bound would have refused a design that could have run — which is the one direction
    a refusal must never err in.
    """
    matrix = corpus_roster(100)
    for controls, reachable in _scan(matrix, TOLERANCE).items():
        if reachable:
            continue
        strata = strata_of(matrix, controls)
        assert strata is not None
        passed = [
            index
            for index in range(200)
            if within_tolerance(
                matrix, dict(candidate(strata, seed="t00d-lottery", draw_index=index)), TOLERANCE
            )
        ]
        assert not passed, (
            f"at {controls} controls the bound says no draw can pass and draws {passed[:5]} "
            "do. The refusal is unsound, which is worse than no refusal at all"
        )


def test_the_bound_is_never_beaten_by_a_real_draw() -> None:
    """The same soundness, per covariate, against every draw rather than against a verdict.

    `attainable` claims a floor for each categorical covariate. A realised draw is a member
    of the set that floor is over, so no draw may come in under it — and this is checked on
    the control counts the bound *accepts*, where a wrong floor would otherwise never show.
    """
    matrix = corpus_roster(100)
    categorical = [
        index for index, kind in enumerate(CORPUS_KINDS) if kind is CovariateKind.CATEGORICAL
    ]
    checked = 0
    for controls, reachable in _scan(matrix, TOLERANCE).items():
        if not reachable:
            continue
        strata = strata_of(matrix, controls)
        assert strata is not None
        floors = attainable(matrix, strata)
        for index in range(50):
            realised = standardised(
                matrix, dict(candidate(strata, seed="t00d-floor", draw_index=index))
            )
            for position, column in enumerate(categorical):
                floor, here = floors[position], realised[column]
                assert floor.covariate_id == here.covariate_id
                if floor.squared is None:
                    continue  # undefined is the worst there is; nothing can be under it
                assert here.squared is None or here.squared >= floor.squared, (
                    f"{here} beat the floor {floor} at {controls} controls, draw {index}"
                )
                checked += 1
    assert checked, "no floor was compared against a draw — the test proved nothing"
