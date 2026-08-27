"""The lottery — reproducible from the committed seed alone, and from nothing else.

Claim 3's sentence is *assignment from a committed seed, exactly reproducible*, and this
file is the four things that phrase has to mean:

* the same seed twice is byte-identical;
* changing one character of one unit id moves **that** unit and no other;
* the order the roster arrived in does not reach the answer;
* the seal records what it drew, and re-running lands on it again.

The last section is the measurement the deferral in `docs/DECISIONS.md` demanded: under the
old re-randomisation screen the reference set starved at the scenario's shape and the
smallest attainable p-value sat above the declared α. The stratified lottery is the remedy,
so the measurement is re-run here in its new shape — the reference set must fill to the
contract's B with the p-value floor under α, and the realised draws must pass the readout's
balance tolerance most of the time on a roster shaped like the scenario's. Numbers in a
test, because a number in a paragraph is a number nobody re-measures.
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
    rank_of,
    redraw,
    reference_set,
    sealed,
    standardised,
    strata_of,
    worst_of,
)
from holdout.core.experiment.assignment import key_for

SEED = "holdout-t001-committed-seed"
FORM_DIGEST = "0" * 64

#: Two hand-built strata, small enough that every draw can be checked by eye.
STRATA = (("store-00", "store-01", "store-02"), ("store-03", "store-04", "store-05"))


def a_roster(size: int = 12) -> tuple[str, ...]:
    return tuple(f"store-{i:03d}" for i in range(size))


def strata_over(roster: tuple[str, ...], size: int) -> tuple[tuple[str, ...], ...]:
    """Consecutive strata of `size` over the roster — a fixture, not the matcher."""
    assert len(roster) % size == 0
    return tuple(roster[i : i + size] for i in range(0, len(roster), size))


# ------------------------------------------------------------------ reproducibility


def test_the_same_seed_and_strata_give_the_same_arms_every_time() -> None:
    first = candidate(STRATA, seed=SEED, draw_index=0)
    second = candidate(STRATA, seed=SEED, draw_index=0)
    assert dict(first) == dict(second)


def test_a_different_seed_gives_a_different_lottery() -> None:
    """Otherwise the seed would be decoration and every experiment would run the same draw."""
    strata = strata_over(a_roster(40), 5)
    first = candidate(strata, seed=SEED, draw_index=0)
    second = candidate(strata, seed=SEED + "x", draw_index=0)
    assert dict(first) != dict(second)


def test_a_different_candidate_index_gives_a_different_lottery() -> None:
    strata = strata_over(a_roster(40), 5)
    first = candidate(strata, seed=SEED, draw_index=0)
    second = candidate(strata, seed=SEED, draw_index=1)
    assert dict(first) != dict(second)


def test_the_order_a_stratum_arrived_in_does_not_reach_the_answer() -> None:
    """The property a seeded generator does not give you.

    A PRNG walked over a list produces a different assignment for a different list order,
    so an experiment would depend on how somebody happened to sort the store table. Here
    each unit's rank is computed from its own id, the minimum of a set does not care how
    the set is written down, and the id breaks a tie — so the arrival order is invisible.
    """
    forwards = candidate(STRATA, seed=SEED, draw_index=0)
    backwards = candidate(
        tuple(tuple(reversed(stratum)) for stratum in reversed(STRATA)),
        seed=SEED,
        draw_index=0,
    )
    assert dict(forwards) == dict(backwards)


def test_one_changed_character_moves_that_unit_and_leaves_the_rest_alone() -> None:
    """A unit's rank is a function of its own id, so a typo in one store's code is a
    correction to one store's rank and not a re-draw of the whole experiment.

    Only the *ranks* are asserted, not the arms: the arm depends on which unit in the
    stratum holds the minimum, so moving one can flip its own stratum's control. What must
    not move is any other unit's own number.
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
    got. Here the control is the stratum's minimum `(rank, id)`, so one unit's arm is
    computable from its own stratum and the seed — never from the other strata.
    """
    key = key_for(SEED, 3)
    arms = candidate(STRATA, seed=SEED, draw_index=3)
    for stratum in STRATA:
        chosen = min(stratum, key=lambda u: (rank_of(u, key), u))
        for unit in stratum:
            assert arms[unit] is (Arm.CONTROL if unit == chosen else Arm.TREATMENT)


# ------------------------------------------------------------------ the arms themselves


def test_each_stratum_contributes_exactly_one_control() -> None:
    strata = strata_over(a_roster(40), 5)
    arms = candidate(strata, seed=SEED, draw_index=0)
    for stratum in strata:
        assert sum(1 for u in stratum if arms[u] is Arm.CONTROL) == 1
    assert sum(1 for a in arms.values() if a is Arm.CONTROL) == len(strata)


def test_a_stratum_of_one_is_refused() -> None:
    """A stratum of one is a unit whose arm nobody drew."""
    with pytest.raises(AssignmentError, match="cannot hold both arms"):
        candidate((("a", "b"), ("c",)), seed=SEED, draw_index=0)


def test_a_unit_in_two_strata_is_refused() -> None:
    with pytest.raises(AssignmentError, match="two strata"):
        candidate((("a", "b"), ("b", "c")), seed=SEED, draw_index=0)


def test_an_empty_stratification_is_refused() -> None:
    with pytest.raises(AssignmentError, match="at least one stratum"):
        candidate((), seed=SEED, draw_index=0)


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


# ------------------------------------------------------------------ the stratified draw


def test_the_drawn_seal_records_its_strata_and_reproduces_its_arms(
    matrix: CovariateMatrix, inference: InferenceSettings
) -> None:
    """The reference set is the candidates after the realised one under the same strata,
    so the strata and the index have to be on the seal — a readout re-derives both the
    draw and its reference set from nothing else."""
    roster = matrix.units
    first = draw(
        experiment_id="exp-1",
        roster=roster,
        seed=SEED,
        form_digest=FORM_DIGEST,
        matrix=matrix,
        control_size=control_size_for(len(roster), inference.holdout_share_pct),
    )
    assert first is not None
    seal, balance = first
    assert sealed(seal)
    assert balance, "the realised draw's own figures come back with it"
    assert seal.draw_index == 0, "the realised assignment is the first candidate"
    assert sorted(u for stratum in seal.strata for u in stratum) == sorted(roster)
    replayed = candidate(seal.strata, seed=SEED, draw_index=seal.draw_index)
    assert dict(replayed) == dict(seal.arms)
    assert dict(redraw(seal)) == dict(seal.arms)


def test_the_strata_are_the_matcher_s_own(
    matrix: CovariateMatrix, inference: InferenceSettings
) -> None:
    """`draw` does not invent a partition; it commits the one `strata_of` builds, so the
    restriction on the seal is exactly the restriction anybody can recompute from the
    matrix."""
    control = control_size_for(len(matrix.units), inference.holdout_share_pct)
    drawn = draw(
        experiment_id="exp-1",
        roster=matrix.units,
        seed=SEED,
        form_digest=FORM_DIGEST,
        matrix=matrix,
        control_size=control,
    )
    assert drawn is not None
    assert drawn[0].strata == strata_of(matrix, control)


def test_a_share_no_stratification_can_hold_returns_none_rather_than_raising(
    contracts: ContractSet, covariate_kinds: tuple[CovariateKind, ...]
) -> None:
    """A roster whose share leaves strata of one is a refusal, and a refusal is returned.

    Six controls out of ten units cannot give every stratum both arms. The design engine
    turns the `None` into `NO_ADMISSIBLE_ASSIGNMENT`, which names what would fix it; an
    exception would have made an infeasible design an error.
    """
    rows: dict[str, tuple[Fraction | str, ...]] = {
        f"store-{index:02d}": (
            Fraction(1_000 + index),
            "convenience",
            Fraction(400),
            Fraction(2, 100),
            "zone_south",
        )
        for index in range(10)
    }
    matrix = CovariateMatrix.of(contracts.balance_covariates.ids, covariate_kinds, rows)
    assert (
        draw(
            experiment_id="exp-1",
            roster=matrix.units,
            seed=SEED,
            form_digest=FORM_DIGEST,
            matrix=matrix,
            control_size=6,
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
        )


def test_an_empty_seed_is_refused(matrix: CovariateMatrix) -> None:
    """An empty seed is not a seed nobody chose; it is a seed everybody can reproduce."""
    with pytest.raises(AssignmentError, match="never empty"):
        draw(
            experiment_id="exp-1",
            roster=matrix.units,
            seed="",
            form_digest=FORM_DIGEST,
            matrix=matrix,
            control_size=8,
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
    )
    assert drawn is not None
    return drawn[0]


def test_the_reference_set_excludes_the_realised_draw(seal: SealedAssignment) -> None:
    """It is counted once, by the `(1 + hits) / (1 + B)` rule. Counting it here as well
    would make every p-value at least `2 / (1 + B)` — a floor nobody declared."""
    draws = reference_set(seal, draws=20, max_attempts=2000)
    assert len(draws) == 20
    assert all(dict(d) != dict(seal.arms) for d in draws)


def test_every_candidate_in_the_reference_set_is_drawn_within_the_same_strata(
    seal: SealedAssignment,
) -> None:
    """This is the whole point of the restriction: the reference set has to be drawn under
    the rule the realised assignment was, or the inference answers a different question.
    Under stratification the rule is the strata themselves — one control per stratum, the
    same strata — and nothing is screened, so every candidate is admissible."""
    draws = reference_set(seal, draws=15, max_attempts=2000)
    for arms in draws:
        for stratum in seal.strata:
            assert sum(1 for u in stratum if arms[u] is Arm.CONTROL) == 1


def test_the_reference_set_comes_back_short_only_where_the_budget_is_below_it(
    seal: SealedAssignment,
) -> None:
    """A budget that runs out is a smaller B, and the p-value divides by what was actually
    drawn. The alternative — padding, or reusing a candidate — would put a number on the
    readout that no draw supports. With no screen the budget is the only thing that can
    cut the set short, and it says so on the report."""
    short = reference_set(seal, draws=500, max_attempts=20)
    assert len(short) == 19, "twenty indices scanned, one of them the realised draw"
    full = reference_set(seal, draws=500, max_attempts=501)
    assert len(full) == 500


def test_the_reference_set_is_reproducible(seal: SealedAssignment) -> None:
    first = reference_set(seal, draws=10, max_attempts=500)
    second = reference_set(seal, draws=10, max_attempts=500)
    assert [dict(d) for d in first] == [dict(d) for d in second]


# ------------------------------- what the stratified lottery buys, at the scenario's shape

#: The declared scenario shape: a hundred stores, the contract's 20% holdout.
SCENARIO_STORES = 100


def scenario_matrix(contracts: ContractSet, kinds: tuple[CovariateKind, ...]) -> CovariateMatrix:
    """A hundred stores whose covariates hang together the way a chain's actually do.

    Format drives selling area, area drives revenue, waste runs against size — plus
    deterministic per-store variation from a hash, so nothing here is tuned by hand. The
    correlations matter: matching can only make strata homogeneous in five dimensions at
    once because real covariates carry information about each other. The fully orthogonal
    roster the old screen was measured on is kept below, as the honest worst case.
    """
    from hashlib import blake2b

    def vary(tag: str, index: int, span: int) -> int:
        material = f"{tag}-{index}".encode()
        return int.from_bytes(blake2b(material, digest_size=4).digest(), "big") % span

    base_of = {"hypermarket": 6000, "supermarket": 1500, "convenience": 500}
    rows: dict[str, tuple[Fraction | str, ...]] = {}
    for index in range(SCENARIO_STORES):
        store_format = ("hypermarket", "supermarket", "convenience")[index % 3]
        base = base_of[store_format]
        size = base + vary("size", index, base // 3)
        revenue = size * 12 + vary("revenue", index, size * 3)
        waste = (
            Fraction(2, 100)
            + Fraction(vary("waste", index, 500), 10_000)
            - Fraction(size, 2_000_000)
        )
        zone = ("zone_north", "zone_south")[vary("zone", index, 2)]
        rows[f"store-{index:03d}"] = (Fraction(revenue), store_format, Fraction(size), waste, zone)
    return CovariateMatrix.of(contracts.balance_covariates.ids, kinds, rows)


def test_the_reference_set_fills_and_the_p_value_floor_sits_under_alpha(
    contracts: ContractSet, covariate_kinds: tuple[CovariateKind, ...]
) -> None:
    """The number the deferral in `docs/DECISIONS.md` said T003 could not start without.

    Under the re-randomisation screen the reference set at this exact shape held single
    figures inside the contract's whole attempt budget, and the smallest attainable
    p-value inside an inverted interval — `2 / (1 + B)`, because the mirror of the
    realised assignment ties under a large shift — sat **above** the declared α: W6's
    false-refusal rate would have been 100% by construction. Under the stratified lottery
    nothing is screened, so the reference set fills to the contract's B and the floor
    lands two orders of magnitude under α.
    """
    matrix = scenario_matrix(contracts, covariate_kinds)
    inference = contracts.inference
    drawn = draw(
        experiment_id="exp-scenario",
        roster=matrix.units,
        seed=SEED,
        form_digest=FORM_DIGEST,
        matrix=matrix,
        control_size=control_size_for(SCENARIO_STORES, inference.holdout_share_pct),
    )
    assert drawn is not None
    draws = reference_set(
        drawn[0],
        draws=inference.permutation_draws,
        max_attempts=inference.max_assignment_attempts,
    )
    assert len(draws) == inference.permutation_draws
    floor = Fraction(2, 1 + len(draws))
    assert floor <= Fraction(inference.alpha), (
        f"the p-value floor {floor} is above alpha — the deferral is back"
    )


def test_most_stratified_draws_pass_the_readout_tolerance_at_the_scenario_s_shape(
    contracts: ContractSet, covariate_kinds: tuple[CovariateKind, ...]
) -> None:
    """The balance the strata buy, measured where the readout will judge it.

    The tolerance moved to the readout, so the question that decides W6's false-refusal
    rate is now: how often does a stratified draw land inside 0.10 on its worst covariate?
    Measured here over 200 candidates on the correlated scenario roster: **a clear
    majority** — against roughly one in a thousand for the unstratified lottery the screen
    used to reject draws from (the arithmetic is in `docs/DECISIONS.md`).

    What is deliberately *not* asserted is anything near 100%. With 20 controls a
    covariate the others carry no information about keeps a sampling spread near the
    tolerance, so some healthy stratified draws fail the check — a refusal, never a wrong
    number, and `strata.py`'s docstring owns the limit. The published rate on the corpus
    is T003's to measure.
    """
    matrix = scenario_matrix(contracts, covariate_kinds)
    inference = contracts.inference
    strata = strata_of(matrix, control_size_for(SCENARIO_STORES, inference.holdout_share_pct))
    assert strata is not None
    tried, passed = 200, 0
    for index in range(tried):
        arms = candidate(strata, seed=SEED, draw_index=index)
        worst = worst_of(standardised(matrix, arms))
        if not worst.exceeds(inference.balance_tolerance_smd):
            passed += 1
    assert passed * 2 > tried, (
        f"only {passed} of {tried} stratified draws pass the readout tolerance — the "
        "strata are no longer buying the balance the restatement in inference.yaml claims"
    )


def test_the_orthogonal_roster_is_still_hard_and_the_check_still_bites(
    contracts: ContractSet, covariate_kinds: tuple[CovariateKind, ...]
) -> None:
    """The honest worst case, kept on purpose — the old screen's measurement roster.

    Five covariates that carry no information about each other cannot be matched into
    homogeneous strata of five, so the readout's balance check refuses most draws here.
    That is the check biting where it should: a roster like this genuinely cannot support
    a balanced 20% holdout at this tolerance, and under the old screen it could not
    support a *p-value* either. The difference is where the truth lands — a reason code on
    a readout instead of an experiment that could never report anything.
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
        for i in range(SCENARIO_STORES)
    }
    matrix = CovariateMatrix.of(contracts.balance_covariates.ids, covariate_kinds, rows)
    inference = contracts.inference
    strata = strata_of(matrix, control_size_for(SCENARIO_STORES, inference.holdout_share_pct))
    assert strata is not None
    tried, passed = 100, 0
    for index in range(tried):
        arms = candidate(strata, seed=SEED, draw_index=index)
        if not worst_of(standardised(matrix, arms)).exceeds(inference.balance_tolerance_smd):
            passed += 1
    assert passed * 2 < tried, (
        "the orthogonal roster now passes the tolerance more often than not — either the "
        "matcher learned something impossible or the check stopped biting; both need "
        "reading, not celebrating"
    )
