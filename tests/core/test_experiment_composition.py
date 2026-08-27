"""The whole path, run end to end. **This file is T001's closing condition.**

`docs/DECISIONS.md` records why it exists. A branch delivered `ladder/` and `guardrails/`
and never ran one into the other; both modules were right on their own terms and they
disagreed by a cent, so the declared safe state of the primary decision path produced a price
the envelope refused for one base price in five. Every unit test passed. The rule that came
out of it: **no module in `core/` is tested only alone.**

This branch delivers two packages, so the test that matters runs the whole path:

    a form -> feasibility -> the committed seed -> the screened draw -> a sealed assignment
    -> delivered outcomes and exposure -> the four checks -> a number with an interval

and beside it the shape T003 will scale up: **the same policy in both arms**, over a handful
of seeds, asserting that the p-values are not concentrated where an A/A split says they
cannot be. That is a smoke test here and a claim at K = 200 in T003 — but a branch that
delivers an estimator and never runs an A/A through it is the same mistake, one module along.

**What this is not.** It is not claim 2. Every number here comes from a table this file's
author chose, which is exactly the difference between a suite and an eval. The inputs its
author did not choose arrive with T002 and T003.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import date
from decimal import Decimal
from fractions import Fraction

import pytest

from holdout.contracts.model import ContractSet, InferenceSettings, Metric
from holdout.core.design import (
    DesignForm,
    DesignRefusal,
    Feasible,
    MaxDuration,
    Mde,
    MdeDirection,
    MdeKind,
    StoppingKind,
    StoppingRule,
    Unit,
    assess,
)
from holdout.core.experiment import (
    Arm,
    CovariateMatrix,
    Period,
    Readout,
    ReadoutRefusal,
    ReadoutRefusalCode,
    close,
    reference_set,
    sealed,
)

POLICY = "ladder_policy@v1"
PERIOD = Period(opens_on=date(2026, 4, 1), ends_on=date(2026, 6, 1))
DATA_VERSION = "delta@1731"

#: Above the `2 / (1 + B)` floor the mirror assignment imposes at alpha = 0.05, and small
#: enough that the whole path runs in about a second. B buys resolution, not validity — the
#: contract says so in its own note, and T003 runs it at the declared 1000.
DRAWS = 80

BASELINE = 40_000
EFFECT = 5_000


def outcomes_for(arms: Mapping[str, Arm], *, effect: int, spread: int = 37) -> dict[str, int]:
    """Integers at the metric's declared scale, with a stated effect on the treated arm.

    `spread` gives each store its own level so the arms are not two constants — a difference
    of two constants has no within-arm variance, and a statistic with no denominator would
    make every assertion here vacuous in the most flattering possible direction.
    """
    return {
        unit: BASELINE + spread * index + (effect if arm is Arm.TREATMENT else 0)
        for index, (unit, arm) in enumerate(sorted(arms.items()))
    }


def run_the_whole_path(
    contracts: ContractSet,
    inference: InferenceSettings,
    metric: Metric,
    matrix: CovariateMatrix,
    form: DesignForm,
    *,
    seed: str,
    effect: int,
    experiment_id: str = "exp-composition",
) -> tuple[Feasible, Readout | ReadoutRefusal]:
    """Form to number, with nothing skipped and nothing stubbed."""
    feasible = assess(
        form,
        experiment_id=experiment_id,
        seed=seed,
        metric=metric,
        metric_ids=contracts.metric_ids,
        covariates=contracts.balance_covariates,
        inference=inference,
        roster=matrix.units,
        matrix=matrix,
        variance_per_unit_week=Decimal(1_000_000),
        mean_per_unit_week=Decimal(BASELINE),
        committed_elsewhere=frozenset(),
        neighbour_pairs=(),
        stopping=form_stopping(),
        previously_locked=None,
    )
    assert isinstance(feasible, Feasible), feasible

    seal = feasible.assignment
    outcomes = outcomes_for(seal.arms, effect=effect)
    draws = reference_set(
        seal,
        matrix,
        tolerance=inference.balance_tolerance_smd,
        draws=DRAWS,
        max_attempts=inference.max_assignment_attempts,
    )
    result = close(
        seal,
        outcomes=outcomes,
        exposed=frozenset(seal.treatment),
        delivered=dict.fromkeys(seal.roster, POLICY),
        treatment_policy=form.intervention.treatment,
        control_policy=form.intervention.control,
        covariates_at_close=matrix,
        draws=draws,
        inference=inference,
        metric=metric,
        mde_absolute=feasible.mde_absolute,
        direction=form.mde.direction,
        form_digest=feasible.form_digest,
        data_version=DATA_VERSION,
        period=PERIOD,
        asked_on=PERIOD.ends_on,
    )
    return feasible, result


def form_stopping() -> StoppingRule:
    """A single readout at the declared end — the only stopping rule this file uses.

    Written once so no test can accidentally exercise the path through a different one:
    what `close` refuses to do before the period ends is `may_read`'s business, and it is
    tested where it lives.
    """
    return StoppingRule(kind=StoppingKind.SINGLE_READOUT_AT_END)


DesignFormFactory = Callable[..., DesignForm]


# ------------------------------------------------------- the whole path, once, in order


def test_a_form_becomes_a_number_with_an_interval(
    contracts: ContractSet,
    inference: InferenceSettings,
    metric: Metric,
    matrix: CovariateMatrix,
    design_form: DesignFormFactory,
) -> None:
    """Every seam in one run, in the order CLAUDE.md declares them.

    The assertions walk the path rather than only its end, because the failure this file
    exists to catch is two modules that are each right and disagree at the join.
    """
    form = design_form()
    feasible, result = run_the_whole_path(
        contracts, inference, metric, matrix, form, seed="composition-seed-1", effect=EFFECT
    )

    # moment 1 — the assignment is written before the period opens, and then read-only
    seal = feasible.assignment
    assert sealed(seal)
    assert seal.form_digest == feasible.form_digest
    assert set(seal.roster) == set(feasible.roster)
    assert len(seal.control) == feasible.control_size

    # moment 3 — four checks, then the number
    assert isinstance(result, Readout), result
    assert all(check.passed for check in result.checks)
    assert result.metric_ref == metric.ref
    assert result.data_version == DATA_VERSION
    assert result.seed == "composition-seed-1"
    assert result.draw_index == seal.draw_index
    assert result.digest == seal.digest

    low, high = result.confidence_interval
    assert low <= EFFECT <= high, f"the injected effect fell outside [{low}, {high}]"
    assert result.is_significant


def test_the_form_that_produced_the_seal_is_the_form_the_readout_is_read_against(
    contracts: ContractSet,
    inference: InferenceSettings,
    metric: Metric,
    matrix: CovariateMatrix,
    design_form: DesignFormFactory,
) -> None:
    """A readout run against a different design is the same failure as an edited assignment,
    arriving by a different door — and the contamination check is the door.

    This is a seam that only a composition test can reach: `feasibility` computes the digest
    and `readout` compares it, and neither module can check the other on its own.
    """
    form = design_form()
    feasible, _ = run_the_whole_path(
        contracts, inference, metric, matrix, form, seed="composition-seed-1", effect=EFFECT
    )
    seal = feasible.assignment
    outcomes = outcomes_for(seal.arms, effect=EFFECT)
    draws = reference_set(
        seal,
        matrix,
        tolerance=inference.balance_tolerance_smd,
        draws=DRAWS,
        max_attempts=inference.max_assignment_attempts,
    )
    result = close(
        seal,
        outcomes=outcomes,
        exposed=frozenset(seal.treatment),
        delivered=dict.fromkeys(seal.roster, POLICY),
        treatment_policy=POLICY,
        control_policy=POLICY,
        covariates_at_close=matrix,
        draws=draws,
        inference=inference,
        metric=metric,
        mde_absolute=feasible.mde_absolute,
        direction=MdeDirection.EITHER,
        form_digest="d" * 64,
        data_version=DATA_VERSION,
        period=PERIOD,
        asked_on=PERIOD.ends_on,
    )
    assert isinstance(result, ReadoutRefusal), result
    assert ReadoutRefusalCode.CONTAMINATED_ASSIGNMENT in result.codes


def test_a_refused_design_never_reaches_a_readout(
    contracts: ContractSet,
    inference: InferenceSettings,
    metric: Metric,
    matrix: CovariateMatrix,
    design_form: DesignFormFactory,
) -> None:
    """The other half of the composition, and the one the project is named for.

    An infeasible design produces a `DesignRefusal` and no seal, so there is no assignment
    for a readout to be computed against. The refusal is where the path stops — which is
    what "an uplift number produced without a valid holdout is a build failure" means when
    it is a type rather than a slogan.
    """
    refused = assess(
        design_form(unit=Unit.STORE_WEEK),
        experiment_id="exp-refused",
        seed="composition-seed-1",
        metric=metric,
        metric_ids=contracts.metric_ids,
        covariates=contracts.balance_covariates,
        inference=inference,
        roster=matrix.units,
        matrix=matrix,
        variance_per_unit_week=Decimal(1_000_000),
        mean_per_unit_week=Decimal(BASELINE),
        committed_elsewhere=frozenset(),
        neighbour_pairs=(),
        stopping=form_stopping(),
        previously_locked=None,
    )
    assert isinstance(refused, DesignRefusal)
    assert not hasattr(refused, "assignment")


def test_a_design_the_engine_admits_produces_a_lottery_the_readout_accepts(
    contracts: ContractSet,
    inference: InferenceSettings,
    metric: Metric,
    matrix: CovariateMatrix,
    design_form: DesignFormFactory,
) -> None:
    """The composition property doctrine rule 1 is really about, one moment along.

    Moment 1 screens the assignment at the declared tolerance; moment 3 re-checks balance at
    the same tolerance over the units that reported. Where nothing moved in between, a
    design the engine admitted must not be refused by its own readout — a screen and a check
    that could disagree on unchanged data would be the ladder-and-envelope defect again.
    """
    for seed in ("composition-seed-a", "composition-seed-b", "composition-seed-c"):
        _, result = run_the_whole_path(
            contracts, inference, metric, matrix, design_form(), seed=seed, effect=EFFECT
        )
        balance = next(c for c in result.checks if c.check.value == "balance")
        assert balance.passed, f"{seed}: {balance.figure}"


# ------------------------------------------------------- the A/A shape T003 scales up


@pytest.mark.parametrize(
    "seed",
    ["aa-seed-1", "aa-seed-2", "aa-seed-3", "aa-seed-4", "aa-seed-5"],
)
def test_an_a_a_split_does_not_report_an_effect(
    contracts: ContractSet,
    inference: InferenceSettings,
    metric: Metric,
    matrix: CovariateMatrix,
    design_form: DesignFormFactory,
    seed: str,
) -> None:
    """The same policy in both arms and no effect injected. Nothing is applied.

    **This is a smoke test and not a false-positive rate.** Five seeds cannot measure a rate
    against alpha = 0.05; two hundred can, and that is claim 2. What five seeds do catch is
    the failure that would make claim 2 unmeasurable — a system that reports an effect where
    the two arms received data drawn from one process with no difference between them.

    It needs no ground truth at all: empty is empty, so nobody can argue the table was
    rigged.
    """
    _, result = run_the_whole_path(
        contracts,
        inference,
        metric,
        matrix,
        design_form(),
        seed=seed,
        effect=0,
        experiment_id=f"exp-aa-{seed}",
    )
    assert isinstance(result, Readout), result
    low, high = result.confidence_interval
    assert low <= 0 <= high, f"{seed}: an A/A split excluded zero — [{low}, {high}]"
    assert not result.is_significant, f"{seed}: p={result.p_value} at B={result.draws}"


def test_the_a_a_p_values_are_not_concentrated_where_they_cannot_be(
    contracts: ContractSet,
    inference: InferenceSettings,
    metric: Metric,
    matrix: CovariateMatrix,
    design_form: DesignFormFactory,
) -> None:
    """Under the null a permutation p-value is roughly uniform, so a handful of seeds should
    not all pile up at one end.

    Deliberately a weak assertion — five draws from a uniform can look like almost anything,
    and asserting more would be a test that fails for the wrong reason a few times a year.
    What it does catch is the degenerate shape: every seed returning the same p-value, which
    is what a reference set that is not actually varying produces.
    """
    seeds = ("aa-seed-1", "aa-seed-2", "aa-seed-3", "aa-seed-4", "aa-seed-5")
    p_values: list[Fraction] = []
    for seed in seeds:
        _, result = run_the_whole_path(
            contracts,
            inference,
            metric,
            matrix,
            design_form(),
            seed=seed,
            effect=0,
            experiment_id=f"exp-aa-{seed}",
        )
        assert isinstance(result, Readout), result
        p_values.append(result.p_value)
    assert len(set(p_values)) > 1, f"every seed returned the same p-value: {p_values}"
    assert max(p_values) > Fraction(1, 4), f"all five p-values are small: {p_values}"


# ------------------------------------------------------- a design that must be refused


def test_an_experiment_can_be_designed_and_then_refused_at_readout(
    contracts: ContractSet,
    inference: InferenceSettings,
    metric: Metric,
    matrix: CovariateMatrix,
    design_form: DesignFormFactory,
) -> None:
    """A valid design, run, and then refused — the screenshot the project is built around.

    Nothing is wrong with the design: it was feasible, the lottery was drawn and sealed, the
    period ran. What went wrong is the world — the price reached only half the treated
    shelves — and the correct output is a reason code at the same size an uplift would have
    been, with all four figures beside it and no number anywhere.
    """
    form = design_form()
    feasible = assess(
        form,
        experiment_id="exp-refused-at-readout",
        seed="composition-seed-1",
        metric=metric,
        metric_ids=contracts.metric_ids,
        covariates=contracts.balance_covariates,
        inference=inference,
        roster=matrix.units,
        matrix=matrix,
        variance_per_unit_week=Decimal(1_000_000),
        mean_per_unit_week=Decimal(BASELINE),
        committed_elsewhere=frozenset(),
        neighbour_pairs=(),
        stopping=form_stopping(),
        previously_locked=None,
    )
    assert isinstance(feasible, Feasible), feasible
    seal = feasible.assignment
    half = seal.treatment[: len(seal.treatment) // 2]
    result = close(
        seal,
        outcomes=outcomes_for(seal.arms, effect=EFFECT),
        exposed=frozenset(half),
        delivered=dict.fromkeys(seal.roster, POLICY),
        treatment_policy=POLICY,
        control_policy=POLICY,
        covariates_at_close=matrix,
        draws=reference_set(
            seal,
            matrix,
            tolerance=inference.balance_tolerance_smd,
            draws=DRAWS,
            max_attempts=inference.max_assignment_attempts,
        ),
        inference=inference,
        metric=metric,
        mde_absolute=feasible.mde_absolute,
        direction=MdeDirection.EITHER,
        form_digest=feasible.form_digest,
        data_version=DATA_VERSION,
        period=PERIOD,
        asked_on=PERIOD.ends_on,
    )
    assert isinstance(result, ReadoutRefusal), result
    assert result.code is ReadoutRefusalCode.EXPOSURE_BELOW_THRESHOLD
    assert len(result.checks) == 4
    assert result.digest == seal.digest
    assert result.data_version == DATA_VERSION


def test_an_underpowered_design_is_refused_before_any_unit_is_assigned(
    contracts: ContractSet,
    inference: InferenceSettings,
    metric: Metric,
    matrix: CovariateMatrix,
    design_form: DesignFormFactory,
) -> None:
    """The refusal happens at moment 1, so no holdout is spent on an experiment that could
    never have answered its own question."""
    refused = assess(
        design_form(
            mde=Mde(kind=MdeKind.ABSOLUTE, value=Decimal(50), direction=MdeDirection.EITHER),
            max_duration=MaxDuration(weeks=2),
        ),
        experiment_id="exp-underpowered",
        seed="composition-seed-1",
        metric=metric,
        metric_ids=contracts.metric_ids,
        covariates=contracts.balance_covariates,
        inference=inference,
        roster=matrix.units,
        matrix=matrix,
        variance_per_unit_week=Decimal(1_000_000),
        mean_per_unit_week=Decimal(BASELINE),
        committed_elsewhere=frozenset(),
        neighbour_pairs=(),
        stopping=form_stopping(),
        previously_locked=None,
    )
    assert isinstance(refused, DesignRefusal)
    assert refused.what_would_fix_it()
