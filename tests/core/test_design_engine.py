"""Moment 1 — each of the eight refusals fired alone, and the sizing arithmetic by hand.

Every test overrides exactly one argument of an otherwise admissible design, so a refusal
here is traceable to the one thing the test changed. A test that changed three things and
asserted one code would be a test that passes for two other reasons.

The interference table is attacked from **outside the contract**: `interference_of` is handed
a `Carryover` built here from literal flags, with `contracts/` never opened, and the refusal
has to appear and disappear as those flags move. That is the difference between checking a
derivation and checking a table somebody typed twice.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from fractions import Fraction

import pytest

from holdout.contracts.model import BalanceCovariates, Carryover, ContractSet, InferenceSettings
from holdout.core.design import (
    DESIGN_PRECEDENCE,
    JUDGMENT_REFUSALS,
    SCOPE_REFUSALS,
    DesignForm,
    DesignRefusal,
    DesignRefusalCode,
    Exclusion,
    FeasibilityError,
    Feasible,
    FilledBy,
    FilledByKind,
    Intervention,
    MaxDuration,
    Mde,
    MdeDirection,
    MdeKind,
    StoppingKind,
    StoppingRule,
    Unit,
    interference_of,
)
from holdout.core.experiment import CovariateKind, CovariateMatrix

AssessFactory = Callable[..., "Feasible | DesignRefusal"]
DesignFormFactory = Callable[..., DesignForm]


def codes_of(outcome: Feasible | DesignRefusal) -> set[DesignRefusalCode]:
    assert isinstance(outcome, DesignRefusal), f"expected a refusal, got {outcome}"
    return set(outcome.codes)


# ------------------------------------------------------------------ the admissible design


def test_an_admissible_design_is_feasible_and_carries_its_sealed_lottery(
    assess_design: AssessFactory,
) -> None:
    """Moment 1's whole output: the assignment is written *before* the period opens."""
    outcome = assess_design()
    assert isinstance(outcome, Feasible), outcome
    assert outcome.assignment.experiment_id == "exp-t001"
    assert set(outcome.assignment.roster) == set(outcome.roster)
    assert outcome.control_size + outcome.treatment_size == len(outcome.roster)
    assert outcome.balance, "the accepted draw's own balance figures are recorded"


def test_the_engine_does_not_know_who_filled_the_form(
    assess_design: AssessFactory, design_form: DesignFormFactory
) -> None:
    """CLAUDE.md's sentence, made checkable.

    A human, a declared policy and the agent fill an otherwise identical form, and the
    engine must produce the identical experiment — same roster, same seed, same accepted
    draw, same arms. It may not produce the same *digest*, because the digest is the
    identity of a document and the same design signed by two people is two documents; that
    is asserted the other way round below.
    """
    attributions = (
        FilledBy(kind=FilledByKind.AGENT),
        FilledBy(kind=FilledByKind.HUMAN, name="A. Reviewer"),
        FilledBy(kind=FilledByKind.POLICY, name="quarterly_fresh_review"),
    )
    results = [assess_design(form=design_form(filled_by=who)) for who in attributions]
    for outcome in results:
        assert isinstance(outcome, Feasible), outcome
    first = results[0]
    assert isinstance(first, Feasible)
    for other in results[1:]:
        assert isinstance(other, Feasible)
        assert other.roster == first.roster
        assert other.required_per_arm == first.required_per_arm
        assert other.weeks == first.weeks
        assert dict(other.assignment.arms) == dict(first.assignment.arms)
        assert other.assignment.draw_index == first.assignment.draw_index


def test_the_form_digest_does_distinguish_who_filled_it(
    design_form: DesignFormFactory,
) -> None:
    """The other half of the sentence above, and it is not a contradiction.

    Attribution is ignored when *deciding* and carried when *identifying*. A readout that
    accepted a form signed by somebody else as the same document would have lost the one
    thing a signature is for.
    """
    from holdout.core.design import form_digest_of

    agent = design_form(filled_by=FilledBy(kind=FilledByKind.AGENT))
    human = design_form(filled_by=FilledBy(kind=FilledByKind.HUMAN, name="A. Reviewer"))
    assert form_digest_of(agent) != form_digest_of(human)


# ------------------------------------------------------------------ the interference table


@pytest.mark.parametrize("unit", [Unit.STORE, Unit.REGION])
def test_a_unit_no_declared_carryover_crosses_is_admissible(unit: Unit) -> None:
    """A store is what a shopper visits, and a region is strictly coarser."""
    carryover = Carryover(
        reference_price_memory=True, cross_price_substitution=True, washout_weeks=None
    )
    assert interference_of(unit, carryover) is None


def test_store_week_is_refused_by_the_declared_reference_price_memory() -> None:
    carryover = Carryover(
        reference_price_memory=True, cross_price_substitution=False, washout_weeks=None
    )
    reason = interference_of(Unit.STORE_WEEK, carryover)
    assert reason is not None
    assert "washout" in reason


def test_a_declared_washout_admits_store_week_with_no_code_change() -> None:
    """The assertion that makes the table a derivation rather than a second definition.

    The `carryover` here is built from literal flags with `contracts/` never opened. If the
    table were hard-coded, this test would fail — which is exactly what it is for. A
    hard-coded table passes every test that only ever hands it the contract's own values.
    """
    declared = Carryover(
        reference_price_memory=True, cross_price_substitution=True, washout_weeks=6
    )
    assert interference_of(Unit.STORE_WEEK, declared) is None


def test_clearing_the_memory_flag_also_admits_store_week() -> None:
    """The same derivation from the other side: no memory, nothing to wash out."""
    forgetful = Carryover(
        reference_price_memory=False, cross_price_substitution=True, washout_weeks=None
    )
    assert interference_of(Unit.STORE_WEEK, forgetful) is None


def test_store_category_is_refused_by_declared_cross_price_substitution() -> None:
    carryover = Carryover(
        reference_price_memory=False, cross_price_substitution=True, washout_weeks=None
    )
    reason = interference_of(Unit.STORE_CATEGORY, carryover)
    assert reason is not None
    assert "substitut" in reason


def test_declaring_no_substitution_admits_store_category() -> None:
    separated = Carryover(
        reference_price_memory=True, cross_price_substitution=False, washout_weeks=None
    )
    assert interference_of(Unit.STORE_CATEGORY, separated) is None


def test_a_washout_of_zero_is_not_a_washout() -> None:
    """`None` and `0` are different claims, and the difference is load-bearing.

    Zero asserts that no washout is *needed*, which is a much stronger statement than "none
    is declared". Reading zero as a mitigation would admit `store_week` on the strength of a
    number nobody argued for.
    """
    zero = Carryover(reference_price_memory=True, cross_price_substitution=True, washout_weeks=0)
    assert interference_of(Unit.STORE_WEEK, zero) is not None


def test_the_engine_refuses_store_week_under_this_repository_s_contract(
    assess_design: AssessFactory, design_form: DesignFormFactory
) -> None:
    """And the whole way through, not only in the helper."""
    outcome = assess_design(form=design_form(unit=Unit.STORE_WEEK))
    assert codes_of(outcome) == {DesignRefusalCode.UNIT_GUARANTEES_INTERFERENCE}


# ------------------------------------------------------------------ the eight, fired alone


def test_a_metric_outside_the_contract_is_refused(
    assess_design: AssessFactory, design_form: DesignFormFactory
) -> None:
    outcome = assess_design(
        form=design_form(primary_metric="margin_we_made_up_this_morning"), metric=None
    )
    assert codes_of(outcome) == {DesignRefusalCode.METRIC_NOT_IN_CONTRACT}


def test_resolving_the_wrong_metric_is_an_error_and_not_a_refusal(
    assess_design: AssessFactory, contracts: ContractSet
) -> None:
    """A caller that resolved a different metric than the form names has not finished
    building the call. Sizing against it would size for a metric nobody will read."""
    other = next(m for m in contracts.metrics if m.id == "waste_value_per_store_week")
    with pytest.raises(FeasibilityError, match=r"[Tt]he caller resolved the wrong one"):
        assess_design(metric=other)


def test_a_stopping_rule_that_permits_peeking_is_refused(
    assess_design: AssessFactory,
) -> None:
    outcome = assess_design(stopping=StoppingRule(kind=StoppingKind.GROUP_SEQUENTIAL, looks=3))
    assert codes_of(outcome) == {DesignRefusalCode.STOPPING_RULE_PERMITS_PEEKING}


def test_a_group_sequential_design_with_its_spending_function_declared_is_admissible(
    assess_design: AssessFactory,
) -> None:
    """The refusal is about the *absence* of the function, not about looking twice.

    A design that declared how it would spend the level in advance did the thing the code
    exists to require, and refusing it anyway would be refusing the remedy.
    """
    outcome = assess_design(
        stopping=StoppingRule(
            kind=StoppingKind.GROUP_SEQUENTIAL, spending_function="obrien_fleming", looks=3
        )
    )
    assert isinstance(outcome, Feasible), outcome


def test_an_exclusion_set_that_moved_after_the_lock_is_refused(
    assess_design: AssessFactory, design_form: DesignFormFactory, roster: tuple[str, ...]
) -> None:
    locked = design_form(
        exclusions=(
            Exclusion(store_id=roster[0], reason="refit closes the fresh counters for a month"),
        )
    )
    outcome = assess_design(form=design_form(exclusions=()), previously_locked=locked)
    assert codes_of(outcome) == {DesignRefusalCode.EXCLUSIONS_DEFINED_POST_HOC}


def test_the_same_exclusions_in_a_different_order_are_not_post_hoc(
    assess_design: AssessFactory, design_form: DesignFormFactory, roster: tuple[str, ...]
) -> None:
    """The refusal is about the set having moved, not about the order somebody typed it in."""
    first = Exclusion(store_id=roster[0], reason="refit closes the fresh counters")
    second = Exclusion(store_id=roster[1], reason="franchise store on different terms")
    locked = design_form(exclusions=(first, second))
    outcome = assess_design(form=design_form(exclusions=(second, first)), previously_locked=locked)
    assert isinstance(outcome, Feasible), outcome


def test_a_rewritten_exclusion_reason_is_post_hoc_too(
    assess_design: AssessFactory, design_form: DesignFormFactory, roster: tuple[str, ...]
) -> None:
    """The reason is the justification, so changing it after the fact is the same edit."""
    locked = design_form(
        exclusions=(Exclusion(store_id=roster[0], reason="refit closes the fresh counters"),)
    )
    outcome = assess_design(
        form=design_form(
            exclusions=(Exclusion(store_id=roster[0], reason="it was dragging the mean down"),)
        ),
        previously_locked=locked,
    )
    assert codes_of(outcome) == {DesignRefusalCode.EXCLUSIONS_DEFINED_POST_HOC}


def test_units_committed_elsewhere_are_refused_and_not_quietly_dropped(
    assess_design: AssessFactory, roster: tuple[str, ...]
) -> None:
    """Which units an experiment runs on is the design's decision, not the engine's.

    The contract's own remedy says *exclude the committed units*, in the imperative — so
    dropping them here would be the engine answering a question it was asked to refuse.
    """
    outcome = assess_design(committed_elsewhere=frozenset(roster[:3]))
    assert codes_of(outcome) == {DesignRefusalCode.UNITS_ALREADY_COMMITTED}
    assert isinstance(outcome, DesignRefusal)
    assert "Exclude the committed units" in outcome.reasons[0].what_would_fix_it


def test_an_mde_too_small_for_the_capacity_is_refused_for_capacity(
    assess_design: AssessFactory, design_form: DesignFormFactory
) -> None:
    """No window up to a year reaches power, so the capacity code leads — and the duration
    code is carried beside it rather than lost to the ordering."""
    outcome = assess_design(
        form=design_form(
            mde=Mde(kind=MdeKind.ABSOLUTE, value=Decimal(1), direction=MdeDirection.EITHER)
        )
    )
    assert codes_of(outcome) == {
        DesignRefusalCode.UNDERPOWERED_FOR_CAPACITY,
        DesignRefusalCode.UNDERPOWERED_FOR_DURATION,
    }
    assert isinstance(outcome, DesignRefusal)
    assert outcome.code is DesignRefusalCode.UNDERPOWERED_FOR_CAPACITY


def test_a_design_that_needs_more_weeks_than_it_declared_is_refused_for_duration(
    assess_design: AssessFactory, design_form: DesignFormFactory
) -> None:
    """A window exists; it is longer than `max_duration`. The design is not shortened."""
    outcome = assess_design(
        form=design_form(
            mde=Mde(kind=MdeKind.ABSOLUTE, value=Decimal(700), direction=MdeDirection.EITHER),
            max_duration=MaxDuration(weeks=1),
        )
    )
    assert codes_of(outcome) == {DesignRefusalCode.UNDERPOWERED_FOR_DURATION}


def test_a_roster_that_cannot_be_stratified_is_refused_by_name(
    assess_design: AssessFactory,
    contracts: ContractSet,
    covariate_kinds: tuple[CovariateKind, ...],
) -> None:
    """`NO_ADMISSIBLE_ASSIGNMENT` — restated with inference.yaml v2, still a first-class code.

    Under v1 it meant the re-randomisation screen rejected every candidate in its budget;
    the stratified draw screens nothing, so the code now fires where no stratification
    gives every stratum both arms — the holdout share asks for more controls than the
    roster can stratify at two-plus units each. A 60% share over ten units wants six
    strata, and six strata over ten units leave some stratum with a single unit, whose
    arm nobody would have drawn. The design is feasible on paper — the sample is there and
    the duration fits at the large MDE declared here — and there is still no lottery.

    The share is built here rather than read from the contract, because the contract's own
    20% never produces the case: a fifth of any roster of two or more stratifies. That is
    the honest status of this code — live at the engine's boundary, unreachable at the
    contract's current values — the same standing `MARGIN_CAP_BASIS_UNEVALUABLE` already
    has on the contract path.
    """
    rows: dict[str, tuple[Fraction | str, ...]] = {}
    for index in range(10):
        rows[f"store-{index:02d}"] = (
            Fraction(10_000 + 137 * index),
            "convenience",
            Fraction(400 + 10 * index),
            Fraction(2 + index, 100),
            "zone_south",
        )
    matrix = CovariateMatrix.of(contracts.balance_covariates.ids, covariate_kinds, rows)
    outcome = assess_design(
        form=None,
        roster=tuple(sorted(rows)),
        matrix=matrix,
        inference=_with_share(contracts.inference, Decimal(60)),
    )
    assert codes_of(outcome) == {DesignRefusalCode.NO_ADMISSIBLE_ASSIGNMENT}
    assert isinstance(outcome, DesignRefusal)
    assert "larger roster" in outcome.what_would_fix_it()[0]


def _with_share(inference: InferenceSettings, share: Decimal) -> InferenceSettings:
    """The contract's settings with a different holdout share, built rather than replaced.

    Written out field by field on purpose: `dataclasses.replace` would silently carry a
    tenth setting the day one is added, and a test that quietly stopped exercising a new
    contract value would be a test passing for the wrong reason.
    """
    return InferenceSettings(
        version=inference.version,
        effective_from=inference.effective_from,
        alpha=inference.alpha,
        target_power=inference.target_power,
        z_two_sided_alpha=inference.z_two_sided_alpha,
        z_one_sided_alpha=inference.z_one_sided_alpha,
        z_power=inference.z_power,
        balance_tolerance_smd=inference.balance_tolerance_smd,
        exposure_min_pct=inference.exposure_min_pct,
        holdout_share_pct=share,
        neighbour_radius_m=inference.neighbour_radius_m,
        permutation_draws=inference.permutation_draws,
        max_assignment_attempts=inference.max_assignment_attempts,
        carryover=inference.carryover,
    )


# ------------------------------------------------------------------ the automatic exclusions


def test_the_later_sorted_neighbour_is_excluded_and_says_why(
    assess_design: AssessFactory, roster: tuple[str, ...]
) -> None:
    """Deterministic on purpose: the surviving roster must not depend on the order the
    pairs arrived in, or the experiment cannot be reproduced."""
    pair = (roster[5], roster[2])
    outcome = assess_design(neighbour_pairs=(pair,))
    assert isinstance(outcome, Feasible), outcome
    excluded = {e.store_id for e in outcome.automatic_exclusions}
    assert excluded == {max(pair)}
    assert min(pair) in outcome.roster
    assert "neighbour radius" in outcome.automatic_exclusions[0].reason


def test_the_neighbour_exclusion_does_not_depend_on_the_order_of_the_pair(
    assess_design: AssessFactory, roster: tuple[str, ...]
) -> None:
    forwards = assess_design(neighbour_pairs=((roster[2], roster[5]),))
    backwards = assess_design(neighbour_pairs=((roster[5], roster[2]),))
    assert isinstance(forwards, Feasible) and isinstance(backwards, Feasible)
    assert forwards.roster == backwards.roster


def test_a_declared_exclusion_leaves_the_roster_and_is_reported(
    assess_design: AssessFactory, design_form: DesignFormFactory, roster: tuple[str, ...]
) -> None:
    excluded = roster[3]
    outcome = assess_design(
        form=design_form(
            exclusions=(Exclusion(store_id=excluded, reason="refit closes the fresh counters"),)
        )
    )
    assert isinstance(outcome, Feasible), outcome
    assert excluded not in outcome.roster
    assert excluded in outcome.excluded_store_ids


def test_a_store_listed_as_its_own_neighbour_is_an_error(
    assess_design: AssessFactory, roster: tuple[str, ...]
) -> None:
    with pytest.raises(FeasibilityError, match="its own neighbour"):
        assess_design(neighbour_pairs=((roster[0], roster[0]),))


# ------------------------------------------------------------------ the sizing arithmetic


def test_the_required_sample_matches_the_formula_worked_by_hand(
    assess_design: AssessFactory, design_form: DesignFormFactory, inference: InferenceSettings
) -> None:
    """`n = ceil( 2 (z_a + z_b)^2 s^2 / (W d^2) )`, checked against the contract's own
    quantiles rather than against a number this file made up.

    With s^2 = 1,000,000 and d = 3,000 the answer at one week is
    2 x (1.959964 + 0.841621)^2 x 1e6 / 9e6 = 1.744..., so 2 units per arm. It is a small
    number on purpose: the point is that a reader can finish the arithmetic.
    """
    outcome = assess_design(
        form=design_form(
            mde=Mde(kind=MdeKind.ABSOLUTE, value=Decimal(3000), direction=MdeDirection.EITHER)
        ),
        variance_per_unit_week=Decimal(1_000_000),
    )
    assert isinstance(outcome, Feasible), outcome
    z_sum = Fraction(inference.z_two_sided_alpha) + Fraction(inference.z_power)
    exact = 2 * z_sum * z_sum * Fraction(1_000_000) / (outcome.weeks * Fraction(3000) ** 2)
    assert outcome.required_per_arm == -((-exact.numerator) // exact.denominator)
    assert outcome.weeks == 1


def test_a_one_sided_mde_sizes_on_the_smaller_quantile(
    assess_design: AssessFactory, design_form: DesignFormFactory
) -> None:
    """A design that declared a direction sizes on a smaller quantile than one that did not,
    and the difference comes from the contract rather than from a number in a module."""
    two_sided = assess_design(
        form=design_form(
            mde=Mde(kind=MdeKind.ABSOLUTE, value=Decimal(400), direction=MdeDirection.EITHER),
            max_duration=MaxDuration(weeks=52),
        )
    )
    one_sided = assess_design(
        form=design_form(
            mde=Mde(kind=MdeKind.ABSOLUTE, value=Decimal(400), direction=MdeDirection.INCREASE),
            max_duration=MaxDuration(weeks=52),
        )
    )
    assert isinstance(two_sided, Feasible) and isinstance(one_sided, Feasible)
    # Both arms are pinned at the same capacity, so the sample sizes come out equal and the
    # difference shows up where it actually is: the one-sided design reaches power sooner.
    assert one_sided.weeks < two_sided.weeks
    assert two_sided.two_sided and not one_sided.two_sided


def test_a_relative_mde_is_a_percentage_of_the_historical_mean(
    assess_design: AssessFactory, design_form: DesignFormFactory
) -> None:
    relative = assess_design(
        form=design_form(
            mde=Mde(kind=MdeKind.RELATIVE_PCT, value=Decimal("7.5"), direction=MdeDirection.EITHER)
        ),
        mean_per_unit_week=Decimal(40_000),
    )
    assert isinstance(relative, Feasible), relative
    assert relative.mde_absolute == Fraction(3000)


def test_a_relative_mde_against_a_non_positive_mean_is_an_error(
    assess_design: AssessFactory, design_form: DesignFormFactory
) -> None:
    """A percentage of zero is zero, and an MDE of zero asks for an infinite sample without
    saying so. Reading it as an absolute difference would be inventing one."""
    with pytest.raises(FeasibilityError, match="non-positive mean"):
        assess_design(
            form=design_form(
                mde=Mde(kind=MdeKind.RELATIVE_PCT, value=Decimal(5), direction=MdeDirection.EITHER)
            ),
            mean_per_unit_week=Decimal(0),
        )


def test_a_non_positive_variance_is_an_error(assess_design: AssessFactory) -> None:
    with pytest.raises(FeasibilityError, match="non-positive variance"):
        assess_design(variance_per_unit_week=Decimal(0))


def test_the_chosen_window_is_the_shortest_that_reaches_power(
    assess_design: AssessFactory, design_form: DesignFormFactory
) -> None:
    """Not `max_duration`. A design that reached power in three weeks and ran for eight
    would be spending five weeks of holdout on nothing."""
    outcome = assess_design(
        form=design_form(
            mde=Mde(kind=MdeKind.ABSOLUTE, value=Decimal(600), direction=MdeDirection.EITHER),
            max_duration=MaxDuration(weeks=52),
        )
    )
    assert isinstance(outcome, Feasible), outcome
    assert 1 < outcome.weeks <= 52


# ------------------------------------------------------------------ the inputs it refuses


def test_a_covariate_matrix_that_is_not_the_contract_s_is_an_error(
    assess_design: AssessFactory,
    contracts: ContractSet,
    matrix: CovariateMatrix,
) -> None:
    """The fixed list is what stops an experiment fishing for a flattering draw. A matrix
    that chose its own columns would be the same degree of freedom entering by the back
    door, so it is refused rather than screened on."""
    trimmed = CovariateMatrix.of(
        matrix.ids[:-1],
        matrix.kinds[:-1],
        {unit: row[:-1] for unit, row in matrix.rows.items()},
    )
    assert trimmed.ids != contracts.balance_covariates.ids
    with pytest.raises(FeasibilityError, match="the contract fixes"):
        assess_design(matrix=trimmed)


def test_a_roster_unit_with_no_covariates_is_an_error(
    assess_design: AssessFactory, roster: tuple[str, ...]
) -> None:
    with pytest.raises(FeasibilityError, match="carry no covariates"):
        assess_design(roster=(*roster, "store-999"))


def test_an_empty_roster_is_an_error(assess_design: AssessFactory) -> None:
    with pytest.raises(FeasibilityError, match="needs a roster"):
        assess_design(roster=())


# ------------------------------------------------------------------ the vocabulary's shape


def test_the_precedence_covers_the_vocabulary_exactly() -> None:
    """A code missing from the order would raise a KeyError the first time it fired, which
    is a bad way to find out."""
    assert set(DESIGN_PRECEDENCE) == set(DesignRefusalCode)
    assert len(DESIGN_PRECEDENCE) == len(DesignRefusalCode)


def test_every_code_is_either_scope_or_judgment_and_never_both() -> None:
    """Claim 6 reports M per code and splits it two ways. A code in neither set would be
    silently uncounted; a code in both would be counted twice."""
    assert not SCOPE_REFUSALS & JUDGMENT_REFUSALS
    assert set(DesignRefusalCode) == SCOPE_REFUSALS | JUDGMENT_REFUSALS


def test_a_scope_refusal_is_not_counted_as_a_judgment_one(
    assess_design: AssessFactory, design_form: DesignFormFactory
) -> None:
    """The distinction claim 6's K depends on, asserted on a real refusal.

    `UNIT_GUARANTEES_INTERFERENCE` is a design falling outside a declared envelope, exactly
    as `CATEGORY_FROZEN` is not a pricing model failing. Counting it as a caught judgment
    would flatter the engine and defame the proposer at the same time.
    """
    outcome = assess_design(form=design_form(unit=Unit.STORE_CATEGORY))
    assert isinstance(outcome, DesignRefusal)
    assert outcome.is_scope_only
    assert not outcome.judgment_codes


def test_an_underpowered_design_is_a_judgment_refusal(
    assess_design: AssessFactory, design_form: DesignFormFactory
) -> None:
    outcome = assess_design(
        form=design_form(
            mde=Mde(kind=MdeKind.ABSOLUTE, value=Decimal(700), direction=MdeDirection.EITHER),
            max_duration=MaxDuration(weeks=1),
        )
    )
    assert isinstance(outcome, DesignRefusal)
    assert not outcome.is_scope_only


def test_a_refusal_reports_every_code_and_leads_with_the_declared_one(
    assess_design: AssessFactory, design_form: DesignFormFactory
) -> None:
    """Two things wrong at once: the unit and the stopping rule. Both are carried, and the
    leading code comes from the declared precedence rather than from the order the checks
    happen to be written in."""
    outcome = assess_design(
        form=design_form(unit=Unit.STORE_CATEGORY),
        stopping=StoppingRule(kind=StoppingKind.GROUP_SEQUENTIAL, looks=4),
    )
    assert codes_of(outcome) == {
        DesignRefusalCode.UNIT_GUARANTEES_INTERFERENCE,
        DesignRefusalCode.STOPPING_RULE_PERMITS_PEEKING,
    }
    assert isinstance(outcome, DesignRefusal)
    assert outcome.code is DesignRefusalCode.UNIT_GUARANTEES_INTERFERENCE
    assert len(outcome.what_would_fix_it()) == 2


def test_a_refusal_with_no_reason_is_impossible() -> None:
    with pytest.raises(ValueError, match="at least one reason"):
        DesignRefusal(experiment_id="exp-1", reasons=())


# ------------------------------------------------------------------ the form itself


def test_an_a_a_design_is_admissible(design_form: DesignFormFactory) -> None:
    """The same policy in both arms is not a mistake — it is how claim 2 is proved.

    A validator that refused it would have made the hardest claim in the project
    unbuildable, which is why the property is asserted here rather than left to be
    discovered in T003.
    """
    form = design_form(
        intervention=Intervention(treatment="ladder_policy@v1", control="ladder_policy@v1")
    )
    assert form.intervention.is_a_a


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("hypothesis", "too short", "one precise sentence"),
        ("primary_metric", "", "names its primary metric"),
    ],
)
def test_a_malformed_form_raises_rather_than_refusing(
    design_form: DesignFormFactory, field: str, value: str, match: str
) -> None:
    """Malformed is not refused. A refusal is a correct output about a design; an error says
    the caller has not finished writing one, and counting the second as the first would
    inflate claim 6's M with things that were never designs."""
    from holdout.core.design import DesignFormError

    with pytest.raises(DesignFormError, match=match):
        design_form(**{field: value})


def test_the_agent_never_fills_max_duration_or_the_decision_rule(
    contracts: ContractSet,
) -> None:
    """ "The agent proposes how we will find out. Never what we will do once we know."

    Enforced by the form schema's `x-never-filled-by`, and asserted here because the
    sentence is in CLAUDE.md and nothing else in the core reads that key.
    """
    properties = contracts.design_form["properties"]
    never = {
        field for field, spec in properties.items() if "agent" in spec.get("x-never-filled-by", [])
    }
    assert never == {"max_duration", "decision_rule"}


def test_the_balance_covariates_the_engine_screens_on_are_the_contract_s(
    contracts: ContractSet, matrix: CovariateMatrix
) -> None:
    covariates: BalanceCovariates = contracts.balance_covariates
    assert matrix.ids == covariates.ids
