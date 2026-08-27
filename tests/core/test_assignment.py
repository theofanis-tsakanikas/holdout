"""The lottery — reproducible from the committed seed alone, and from nothing else.

Claim 3's sentence is *assignment from a committed seed, exactly reproducible*, and this
file is the four things that phrase has to mean:

* the same seed twice is byte-identical;
* changing one character of one unit id moves **that** unit and no other;
* the order the roster arrived in does not reach the answer;
* the accepted candidate index is recorded, and re-running lands on it again.

The last section is the measurement nobody wanted: how often the re-randomisation screen
actually accepts, at the tolerance the contract declares, on a roster shaped like the one
the scenario describes. It is a test rather than a paragraph because the number decides
whether claim 2 can be computed at all, and a number in a paragraph is a number nobody
re-measures.
"""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction

import pytest

from holdout.contracts.model import ContractSet, InferenceSettings
from holdout.core.experiment import (
    Arm,
    AssignmentError,
    CovariateKind,
    CovariateMatrix,
    SealedAssignment,
    candidate,
    control_size_for,
    draw,
    ordering,
    rank_of,
    redraw,
    reference_set,
    sealed,
)
from holdout.core.experiment.assignment import key_for

SEED = "holdout-t001-committed-seed"
FORM_DIGEST = "0" * 64


def a_roster(size: int = 12) -> tuple[str, ...]:
    return tuple(f"store-{i:03d}" for i in range(size))


# ------------------------------------------------------------------ reproducibility


def test_the_same_seed_and_roster_give_the_same_arms_every_time() -> None:
    roster = a_roster()
    first = candidate(roster, seed=SEED, draw_index=0, control_size=3)
    second = candidate(roster, seed=SEED, draw_index=0, control_size=3)
    assert dict(first) == dict(second)


def test_a_different_seed_gives_a_different_lottery() -> None:
    """Otherwise the seed would be decoration and every experiment would run the same draw."""
    roster = a_roster(40)
    first = candidate(roster, seed=SEED, draw_index=0, control_size=8)
    second = candidate(roster, seed=SEED + "x", draw_index=0, control_size=8)
    assert dict(first) != dict(second)


def test_a_different_candidate_index_gives_a_different_lottery() -> None:
    roster = a_roster(40)
    first = candidate(roster, seed=SEED, draw_index=0, control_size=8)
    second = candidate(roster, seed=SEED, draw_index=1, control_size=8)
    assert dict(first) != dict(second)


def test_the_order_the_roster_arrived_in_does_not_reach_the_answer() -> None:
    """The property a seeded generator does not give you.

    A PRNG walked over a list produces a different assignment for a different list order,
    so an experiment would depend on how somebody happened to sort the store table. Here
    each unit's rank is computed from its own id, and the id breaks a tie, so the order is
    total and the arrival order is invisible.
    """
    roster = a_roster(20)
    forwards = candidate(roster, seed=SEED, draw_index=0, control_size=4)
    backwards = candidate(tuple(reversed(roster)), seed=SEED, draw_index=0, control_size=4)
    shuffled = candidate(tuple(sorted(roster, key=len)), seed=SEED, draw_index=0, control_size=4)
    assert dict(forwards) == dict(backwards) == dict(shuffled)


def test_one_changed_character_moves_that_unit_and_leaves_the_rest_alone() -> None:
    """A unit's rank is a function of its own id, so a typo in one store's code is a
    correction to one store's arm and not a re-draw of the whole experiment.

    Only the *ranks* are asserted, not the arms: the arms depend on where every unit falls
    in the sorted order, so moving one necessarily shifts the cut for the neighbours it
    passed. What must not move is any other unit's own number.
    """
    key = key_for(SEED, 0)
    roster = a_roster(20)
    before = {unit: rank_of(unit, key) for unit in roster}
    renamed = ("store-00X", *roster[1:])
    after = {unit: rank_of(unit, key) for unit in renamed}
    assert after["store-00X"] != before["store-000"]
    for unit in roster[1:]:
        assert after[unit] == before[unit]


def test_a_unit_s_arm_can_be_re_derived_without_replaying_a_sequence() -> None:
    """What keeps the contamination check cheap enough to run on every unit.

    A seeded generator would need the whole draw replayed in order to say what one store
    got. Here the ordering is a sort on per-unit ranks, so one unit's place is computable
    from its id and the seed.
    """
    roster = a_roster(20)
    key = key_for(SEED, 3)
    arms = candidate(roster, seed=SEED, draw_index=3, control_size=5)
    ranked = sorted(roster, key=lambda u: (rank_of(u, key), u))
    for index, unit in enumerate(ranked):
        assert arms[unit] is (Arm.CONTROL if index < 5 else Arm.TREATMENT)


def test_the_ordering_is_a_permutation_of_the_roster() -> None:
    roster = a_roster(30)
    assert sorted(ordering(roster, seed=SEED, draw_index=7)) == sorted(roster)


# ------------------------------------------------------------------ the arms themselves


def test_the_control_arm_is_exactly_the_declared_size() -> None:
    arms = candidate(a_roster(40), seed=SEED, draw_index=0, control_size=8)
    assert sum(1 for a in arms.values() if a is Arm.CONTROL) == 8
    assert sum(1 for a in arms.values() if a is Arm.TREATMENT) == 32


@pytest.mark.parametrize("control_size", [0, 12, 13])
def test_a_split_that_leaves_an_arm_empty_is_refused(control_size: int) -> None:
    with pytest.raises(AssignmentError, match="holdout of"):
        candidate(a_roster(12), seed=SEED, draw_index=0, control_size=control_size)


def test_a_duplicated_unit_is_refused() -> None:
    with pytest.raises(AssignmentError, match="twice"):
        candidate(("a", "b", "a"), seed=SEED, draw_index=0, control_size=1)


def test_the_holdout_share_rounds_down() -> None:
    """Down, not to nearest. Every unit not held back is treated, so rounding up would
    treat fewer units than the design declared — a bound rounding toward what it excludes."""
    assert control_size_for(100, Decimal(20)) == 20
    assert control_size_for(99, Decimal(20)) == 19
    assert control_size_for(11, Decimal(20)) == 2


def test_a_share_that_rounds_to_nothing_is_refused() -> None:
    with pytest.raises(AssignmentError, match=r"rounds to\s+nothing"):
        control_size_for(4, Decimal(20))


def test_a_roster_of_one_is_not_an_experiment() -> None:
    with pytest.raises(AssignmentError, match="anecdote with a seed"):
        control_size_for(1, Decimal(20))


# ------------------------------------------------------------------ the screened draw


def test_the_accepted_draw_index_is_recorded_and_reproducible(
    matrix: CovariateMatrix, inference: InferenceSettings
) -> None:
    """The reference set at readout is the set of candidates the same screen accepts, so
    the realised one has to be identifiable inside it — which means the index it came from
    is part of the seal, not a detail of how it was found."""
    roster = matrix.units
    first = draw(
        experiment_id="exp-1",
        roster=roster,
        seed=SEED,
        form_digest=FORM_DIGEST,
        matrix=matrix,
        control_size=control_size_for(len(roster), inference.holdout_share_pct),
        tolerance=inference.balance_tolerance_smd,
        max_attempts=inference.max_assignment_attempts,
    )
    assert first is not None
    seal, balance = first
    assert sealed(seal)
    assert balance, "the accepted candidate's own figures come back with it"
    replayed = candidate(
        roster,
        seed=SEED,
        draw_index=seal.draw_index,
        control_size=len(seal.control),
    )
    assert dict(replayed) == dict(seal.arms)
    assert dict(redraw(seal)) == dict(seal.arms)


def test_an_exhausted_attempt_budget_returns_none_rather_than_raising(
    contracts: ContractSet, covariate_kinds: tuple[CovariateKind, ...]
) -> None:
    """A roster on which no lottery balances is a refusal, and a refusal is returned.

    One unit dominates every covariate, so wherever it lands that arm is different from the
    other. The design engine turns the `None` into `NO_ADMISSIBLE_ASSIGNMENT`, which names
    what would fix it; an exception would have made an infeasible design an error.
    """
    rows: dict[str, tuple[Fraction | str, ...]] = {}
    for index in range(10):
        dominant = index == 0
        rows[f"store-{index:02d}"] = (
            Fraction(9_000_000) if dominant else Fraction(1_000),
            "hypermarket" if dominant else "convenience",
            Fraction(40_000) if dominant else Fraction(400),
            Fraction(80, 100) if dominant else Fraction(2, 100),
            "zone_north" if dominant else "zone_south",
        )
    matrix = CovariateMatrix.of(contracts.balance_covariates.ids, covariate_kinds, rows)
    assert (
        draw(
            experiment_id="exp-1",
            roster=matrix.units,
            seed=SEED,
            form_digest=FORM_DIGEST,
            matrix=matrix,
            control_size=2,
            tolerance=Decimal("0.10"),
            max_attempts=200,
        )
        is None
    )


def test_a_roster_and_a_matrix_describing_different_units_is_an_error(
    matrix: CovariateMatrix, inference: InferenceSettings
) -> None:
    with pytest.raises(AssignmentError, match="different units"):
        draw(
            experiment_id="exp-1",
            roster=(*matrix.units, "store-999"),
            seed=SEED,
            form_digest=FORM_DIGEST,
            matrix=matrix,
            control_size=8,
            tolerance=inference.balance_tolerance_smd,
            max_attempts=10,
        )


def test_an_empty_seed_is_refused(matrix: CovariateMatrix, inference: InferenceSettings) -> None:
    """An empty seed is not a seed nobody chose; it is a seed everybody can reproduce."""
    with pytest.raises(AssignmentError, match="never empty"):
        draw(
            experiment_id="exp-1",
            roster=matrix.units,
            seed="",
            form_digest=FORM_DIGEST,
            matrix=matrix,
            control_size=8,
            tolerance=inference.balance_tolerance_smd,
            max_attempts=10,
        )


# ------------------------------------------------------------------ the reference set


@pytest.fixture
def seal(matrix: CovariateMatrix, inference: InferenceSettings) -> SealedAssignment:
    drawn = draw(
        experiment_id="exp-1",
        roster=matrix.units,
        seed=SEED,
        form_digest=FORM_DIGEST,
        matrix=matrix,
        control_size=control_size_for(len(matrix.units), inference.holdout_share_pct),
        tolerance=inference.balance_tolerance_smd,
        max_attempts=inference.max_assignment_attempts,
    )
    assert drawn is not None
    return drawn[0]


def test_the_reference_set_excludes_the_realised_draw(
    seal: SealedAssignment, matrix: CovariateMatrix, inference: InferenceSettings
) -> None:
    """It is counted once, by the `(1 + hits) / (1 + B)` rule. Counting it here as well
    would make every p-value at least `2 / (1 + B)` — a floor nobody declared."""
    draws = reference_set(
        seal, matrix, tolerance=inference.balance_tolerance_smd, draws=20, max_attempts=2000
    )
    assert len(draws) == 20
    assert all(dict(d) != dict(seal.arms) for d in draws)


def test_every_candidate_in_the_reference_set_passes_the_same_screen(
    seal: SealedAssignment, matrix: CovariateMatrix, inference: InferenceSettings
) -> None:
    """This is the whole point of the restriction: the reference set has to be drawn under
    the rule the realised assignment was, or the inference answers a different question."""
    from holdout.core.experiment import screen

    draws = reference_set(
        seal, matrix, tolerance=inference.balance_tolerance_smd, draws=15, max_attempts=2000
    )
    for arms in draws:
        assert screen(matrix, arms, tolerance=inference.balance_tolerance_smd) is not None


def test_the_reference_set_comes_back_short_rather_than_pretending(
    seal: SealedAssignment, matrix: CovariateMatrix, inference: InferenceSettings
) -> None:
    """A budget that runs out is a smaller B, and the p-value divides by what was actually
    accepted. The alternative — padding, or reusing a candidate — would put a number on the
    readout that no draw supports."""
    draws = reference_set(
        seal, matrix, tolerance=inference.balance_tolerance_smd, draws=500, max_attempts=20
    )
    assert 0 < len(draws) < 500


def test_the_reference_set_is_reproducible(
    seal: SealedAssignment, matrix: CovariateMatrix, inference: InferenceSettings
) -> None:
    first = reference_set(
        seal, matrix, tolerance=inference.balance_tolerance_smd, draws=10, max_attempts=500
    )
    second = reference_set(
        seal, matrix, tolerance=inference.balance_tolerance_smd, draws=10, max_attempts=500
    )
    assert [dict(d) for d in first] == [dict(d) for d in second]


# --------------------------------------------- what the declared tolerance actually costs


def test_the_screen_accepts_about_one_draw_in_a_thousand_at_the_scenario_s_shape(
    contracts: ContractSet, covariate_kinds: tuple[CovariateKind, ...]
) -> None:
    """The measurement that decides whether claim 2 can be computed, made in the suite.

    A hundred stores with heterogeneous covariates, the contract's 20% holdout share and
    its tolerance of 0.10 standardised differences. The arithmetic is not mysterious: the
    standardised difference has a spread of roughly `sqrt(1/n_T + 1/n_C)`, which is 0.25 at
    eighty against twenty, so each of the seven comparisons passes about 31% of the time
    and all seven pass about three times in ten thousand.

    **The consequence is the one that matters.** `max_assignment_attempts` is 10,000, so a
    reference set drawn inside that budget holds a handful of draws, and the smallest
    attainable p-value is `1 / (1 + B)`. At B in single figures that is larger than the
    declared alpha of 0.05, which means **no experiment at the scenario's own shape could
    ever report a significant effect** — W6's false-refusal rate would be 100% by
    construction. That is a sizing problem for T003 and a deferral in `docs/DECISIONS.md`,
    not a defect in this module; what this test does is make sure nobody can start T003
    without meeting the number first.

    The bound asserted is deliberately loose. The exact rate depends on the corpus, and the
    finding is the order of magnitude, not the third digit.
    """
    formats = ("hypermarket", "supermarket", "convenience")
    zones = ("zone_north", "zone_south")
    rows: dict[str, tuple[Fraction | str, ...]] = {
        f"store-{i:03d}": (
            Fraction(10_000 + 137 * i),
            formats[i % 3],
            Fraction(800 + 40 * (i % 7)),
            Fraction(3 + (i % 5), 100),
            zones[i % 2],
        )
        for i in range(100)
    }
    matrix = CovariateMatrix.of(contracts.balance_covariates.ids, covariate_kinds, rows)
    roster = matrix.units
    control = control_size_for(len(roster), contracts.inference.holdout_share_pct)
    tried = 1000
    accepted = 0
    for index in range(tried):
        arms = candidate(roster, seed=SEED, draw_index=index, control_size=control)
        from holdout.core.experiment import screen

        if screen(matrix, arms, tolerance=contracts.inference.balance_tolerance_smd) is not None:
            accepted += 1
    assert accepted * 100 < tried, (
        f"the screen accepted {accepted} of {tried} draws — more than one in a hundred. "
        "That is better news than the deferral in docs/DECISIONS.md records, so the "
        "deferral needs re-reading rather than this assertion needs relaxing."
    )
