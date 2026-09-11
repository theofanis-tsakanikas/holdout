"""A refused design, run under the violation it was refused for, on the world where the
truth is known.

`grade.anyway` runs a power-refused design with the guards off and gets, on the null world, a
false positive at the declared rate — which is the estimator behaving and not the refusal
saving anything. This module runs the refusals whose reason predicts a wrong number at a rate
**above** chance, because that is where a refusal is a save with a count on it:

* **peeking** — the same design under a group-sequential rule with no spending function. The
  engine refuses it `STOPPING_RULE_PERMITS_PEEKING`. Run anyway, the number is read at every
  look and reported at the first one that is significant, which is what a peeker does. On a
  world whose true effect is zero, every such number is a false positive, and four unadjusted
  looks produce them at well over the declared α.
* **post-hoc exclusions** — a design the engine accepted and locked, re-submitted with the
  control units that happened to do best excluded, each with a reason that reads well. The
  engine refuses it `EXCLUSIONS_DEFINED_POST_HOC`. Run anyway, the estimate moves in the
  direction the exclusion was chosen to move it, on a world where the true effect is zero.

What is not here, and why
-------------------------
**Interference.** `UNIT_GUARANTEES_INTERFERENCE` refuses a unit whose arms share customers by
construction, and the harness can generate the world where that happens — W2. What it cannot
do is say what the *truth* is there: under interference a unit's outcome depends on its
neighbours' arms, so there is no potential outcome to subtract and no estimand for a number to
be wrong against. That is not a gap in the harness. It is the reason the engine refuses the
unit, and a K computed against a truth that does not exist would be this eval inventing the
thing the refusal exists to say is uninventable. The refusal is counted as refused-not-runnable
and the reason is printed.

Every number here is computed the way `close()` computes it after the four checks it would
never have got past — the studentized difference, the permutation p-value under the same
strata, the interval by inversion — and nothing is read from disk.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from corpus.world import Arm as WorldArm

from evals.design import build, grade, pool
from evals.uplift import grouped_metric
from holdout.contracts.model import DesignHarness
from holdout.core.design import DesignRefusal, Feasible, assess
from holdout.core.design.feasibility import form_digest_of, neighbour_exclusions
from holdout.core.design.form import (
    DesignForm,
    Exclusion,
    MdeDirection,
    StoppingKind,
    StoppingRule,
)
from holdout.core.experiment import Arm
from holdout.core.experiment.assignment import SealedAssignment, draw, reference_set
from holdout.core.experiment.estimator import (
    Design,
    ReferencePlan,
    design_of,
    difference_in_means,
    permutation_p,
    plan_for,
    studentized,
)


def peeking_rule(harness: DesignHarness) -> StoppingRule:
    """Group-sequential with no spending function, at the contract's number of looks -- the
    rule the estate's own second experiment declared and was refused for on 2026-09-10."""
    return StoppingRule(
        kind=StoppingKind.GROUP_SEQUENTIAL, spending_function=None, looks=harness.peeking_looks
    )


def lottery_seeds(count: int) -> tuple[str, ...]:
    """Spelled out the way `evals.uplift.parallel.world_seeds` spells its own.

    Combined with the design's index inside `_draw`, so that two designs drawn under the same
    seed do not share a lottery. **They did, on the first published run**: seven designs that
    differ only in their MDE and metric drew the identical assignment from the identical seed,
    and one unlucky lottery was counted seven times -- 5 of 28 false positives that were one
    of four. A rate over draws that are copies of each other is not a rate.
    """
    return tuple(f"violate-{index:02d}" for index in range(count))


@dataclass(frozen=True, slots=True)
class Look:
    weeks: int
    uplift_cents: Fraction  # the adjusted estimate, as the readout reports it
    raw_difference_cents: Fraction  # treatment mean minus control mean, unadjusted
    p_value: Fraction
    significant: bool


@dataclass(frozen=True, slots=True)
class Violated:
    """One design, one lottery, one violation, and the number it would have reported."""

    scenario: str  # peeking | post_hoc
    index: int
    lottery_seed: str
    refused_codes: tuple[str, ...]
    honest: Look
    reported: Look
    #: `True` when the reported number is a confident one the truth contradicts. On the null
    #: world: significant, full stop.
    wrong: bool


def peeking(
    recorded: build.Recorded,
    *,
    contracts: build.ContractSet,
    built: build.World,
    lottery_seed: str,
) -> Violated | None:
    """The design under four unadjusted looks, on the null world."""
    if recorded.proposal is None or recorded.proposal.unit is not grade.GRADABLE_UNIT:
        return None
    if recorded.proposal.primary_metric not in built.pre_by_metric:
        return None
    form = build.complete(recorded.proposal)
    rule = peeking_rule(contracts.design_harness)
    refused = _refusal(form, contracts=contracts, built=built, stopping=rule, locked=None)
    if refused is None or "STOPPING_RULE_PERMITS_PEEKING" not in refused:
        # The engine did not refuse this for peeking. Recorded as a violation with no refusal
        # behind it, so a check can see the engine admitting what it should not, rather than
        # dropped -- a dropped case is how a gate stops biting without a red run.
        return _unrefused("peeking", recorded.index, lottery_seed, refused)

    drawn = _draw(form, recorded.index, contracts=contracts, built=built, seed=lottery_seed)
    if drawn is None:
        return None
    seal, outcomes_by_unit_week = drawn
    pre = built.pre_by_metric[recorded.proposal.primary_metric]
    period = pre.period_weeks
    looks: list[Look] = []
    assert rule.looks is not None
    plan = _plan(seal, contracts=contracts, built=built, metric_id=recorded.proposal.primary_metric)
    for k in range(1, rule.looks + 1):
        upto = period[: max(1, round(len(period) * k / rule.looks))]
        looks.append(
            _estimate(
                seal,
                outcomes_by_unit_week,
                weeks=upto,
                contracts=contracts,
                built=built,
                metric_id=recorded.proposal.primary_metric,
                direction=recorded.proposal.mde.direction,
                plan=plan,
            )
        )
    honest = looks[-1]
    first_significant = next((look for look in looks if look.significant), None)
    reported = first_significant if first_significant is not None else honest
    return Violated(
        scenario="peeking",
        index=recorded.index,
        lottery_seed=lottery_seed,
        refused_codes=refused,
        honest=honest,
        reported=reported,
        wrong=reported.significant,
    )


def post_hoc(
    recorded: build.Recorded,
    *,
    contracts: build.ContractSet,
    built: build.World,
    lottery_seed: str,
) -> Violated | None:
    """A locked design re-submitted with its best controls excluded, on the null world.

    Only a design the engine accepts can be locked, so this scenario runs over the feasible
    designs; the refused ones have nothing to re-submit. The honest number is the locked
    design's; the reported one drops the `POST_HOC_EXCLUDED` control units whose outcome was
    highest -- the ones a treatment-favouring analyst would find a reason to remove.
    """
    if recorded.proposal is None or recorded.proposal.unit is not grade.GRADABLE_UNIT:
        return None
    if recorded.proposal.primary_metric not in built.pre_by_metric:
        return None
    locked = build.complete(recorded.proposal)
    if _refusal(locked, contracts=contracts, built=built, stopping=None, locked=None):
        return None  # refused at moment 1; never locked, so nothing to move

    drawn = _draw(locked, recorded.index, contracts=contracts, built=built, seed=lottery_seed)
    if drawn is None:
        return None
    seal, outcomes_by_unit_week = drawn
    pre = built.pre_by_metric[recorded.proposal.primary_metric]
    metric = recorded.proposal.primary_metric
    honest = _estimate(
        seal,
        outcomes_by_unit_week,
        weeks=pre.period_weeks,
        contracts=contracts,
        built=built,
        metric_id=metric,
        direction=recorded.proposal.mde.direction,
    )

    # The exclusions an analyst finds after the fact: the controls that did best.
    rounding = contracts.metric_versions(metric)[-1].rounding
    window = grouped_metric.window_mean(
        outcomes_by_unit_week, units=seal.roster, weeks=pre.period_weeks, rounding=rounding
    )
    controls = sorted(
        (unit for unit in seal.roster if seal.arms[unit] is Arm.CONTROL),
        key=lambda unit: window[unit],
        reverse=True,
    )
    to_drop = tuple(controls[: contracts.design_harness.post_hoc_controls_excluded])
    moved = DesignForm(
        hypothesis=locked.hypothesis,
        intervention=locked.intervention,
        scope=locked.scope,
        primary_metric=locked.primary_metric,
        unit=locked.unit,
        mde=locked.mde,
        max_duration=locked.max_duration,
        exclusions=(
            *locked.exclusions,
            *(
                Exclusion(store_id=unit, reason="atypical trading in the period, on review")
                for unit in to_drop
            ),
        ),
        decision_rule=locked.decision_rule,
        filled_by=locked.filled_by,
    )
    refused = _refusal(moved, contracts=contracts, built=built, stopping=None, locked=locked)
    if refused is None or "EXCLUSIONS_DEFINED_POST_HOC" not in refused:
        return _unrefused("post_hoc", recorded.index, lottery_seed, refused)

    kept = tuple(unit for unit in seal.roster if unit not in set(to_drop))
    reported = _estimate(
        seal,
        outcomes_by_unit_week,
        weeks=pre.period_weeks,
        contracts=contracts,
        built=built,
        metric_id=metric,
        direction=recorded.proposal.mde.direction,
        units=kept,
    )
    return Violated(
        scenario="post_hoc",
        index=recorded.index,
        lottery_seed=lottery_seed,
        refused_codes=refused,
        honest=honest,
        reported=reported,
        wrong=reported.significant,
    )


# --------------------------------------------------------------------------- the machinery


def _refusal(
    form: DesignForm,
    *,
    contracts: build.ContractSet,
    built: build.World,
    stopping: StoppingRule | None,
    locked: DesignForm | None,
) -> tuple[str, ...] | None:
    """The engine's codes for this form, or `None` when it accepts."""
    from evals.uplift import design as design_module

    pre = built.pre_by_metric[form.primary_metric]
    metric = contracts.metric_versions(form.primary_metric)[-1]
    result = assess(
        form,
        experiment_id="design/violate",
        seed="violate",
        metric=metric,
        metric_ids=contracts.metric_ids,
        covariates=contracts.balance_covariates,
        inference=contracts.inference,
        roster=pre.matrix.units,
        matrix=pre.matrix,
        variance_per_unit_week=pre.variance_per_unit_week,
        mean_per_unit_week=pre.mean_per_unit_week,
        committed_elsewhere=frozenset(),
        neighbour_pairs=built.fixture.run.chain.neighbour_pairs,
        stopping=stopping if stopping is not None else design_module.STOPPING,
        previously_locked=locked,
    )
    if isinstance(result, DesignRefusal):
        return tuple(r.code.value for r in result.reasons)
    assert isinstance(result, Feasible)
    return None


def _draw(
    form: DesignForm,
    index: int,
    *,
    contracts: build.ContractSet,
    built: build.World,
    seed: str,
) -> tuple[SealedAssignment, dict[tuple[str, tuple[int, int]], int]] | None:
    """The lottery the engine would have drawn, and the world's outcomes for it."""
    pre = built.pre_by_metric[form.primary_metric]
    declared = frozenset(e.store_id for e in form.exclusions)
    after = tuple(u for u in pre.matrix.units if u not in declared)
    automatic = neighbour_exclusions(after, built.fixture.run.chain.neighbour_pairs, declared)
    excluded = declared | frozenset(e.store_id for e in automatic)
    available = tuple(u for u in pre.matrix.units if u not in excluded)
    control_size = int(len(available) * contracts.inference.holdout_share_pct / 100)
    if control_size < 1 or len(available) - control_size < 1:
        return None
    drawn = draw(
        experiment_id=f"design/{index:03d}/violate",
        roster=available,
        seed=f"{seed}/{index:03d}",
        form_digest=form_digest_of(form),
        matrix=pre.matrix.restricted_to(frozenset(available)),
        control_size=control_size,
    )
    if drawn is None:
        return None
    seal, _ = drawn
    arms = dict(seal.arms)
    world_arms = {
        store.store_id: (
            WorldArm.TREATMENT if arms.get(store.store_id) is Arm.TREATMENT else WorldArm.CONTROL
        )
        for store in built.fixture.run.chain.stores
    }
    return seal, grade._unit_weeks_for(form.primary_metric, built.fixture, world_arms)


def _plan(
    seal: SealedAssignment,
    *,
    contracts: build.ContractSet,
    built: build.World,
    metric_id: str,
    units: tuple[str, ...] | None = None,
) -> tuple[Design, ReferencePlan]:
    """The design and the permutation reference plan for a lottery over these units.

    Built once per lottery and reused across the looks: the plan depends on the covariates
    and the candidate assignments and not on any outcome, and building it is what one
    violated run mostly costs -- measured, 26 of 36 seconds under the profiler for four looks
    that each rebuilt it.
    """
    pre = built.pre_by_metric[metric_id]
    roster = seal.roster if units is None else units
    reported = frozenset(roster)
    design = design_of(pre.matrix.restricted_to(reported))
    draws = reference_set(
        seal,
        draws=contracts.inference.permutation_draws,
        max_attempts=contracts.inference.max_assignment_attempts,
    )
    restricted = [
        {unit: arm for unit, arm in candidate.items() if unit in reported} for candidate in draws
    ]
    return design, plan_for(design, restricted)


def _unrefused(
    scenario: str, index: int, lottery_seed: str, codes: tuple[str, ...] | None
) -> Violated:
    """The engine admitted the violation. Recorded so a check can refuse the admission."""
    nothing = Look(
        weeks=0,
        uplift_cents=Fraction(0),
        raw_difference_cents=Fraction(0),
        p_value=Fraction(1),
        significant=False,
    )
    return Violated(
        scenario=scenario,
        index=index,
        lottery_seed=lottery_seed,
        refused_codes=codes or (),
        honest=nothing,
        reported=nothing,
        wrong=False,
    )


def _estimate(
    seal: SealedAssignment,
    by_unit_week: dict[tuple[str, tuple[int, int]], int],
    *,
    weeks: tuple[tuple[int, int], ...],
    contracts: build.ContractSet,
    built: build.World,
    metric_id: str,
    direction: MdeDirection,
    units: tuple[str, ...] | None = None,
    plan: tuple[Design, ReferencePlan] | None = None,
) -> Look:
    """What `close()` computes after its four checks, over the given weeks and units."""
    rounding = contracts.metric_versions(metric_id)[-1].rounding
    roster = seal.roster if units is None else units
    outcomes = grouped_metric.window_mean(
        by_unit_week, units=roster, weeks=weeks, rounding=rounding
    )
    reported = frozenset(roster) & frozenset(outcomes)
    arms = {unit: seal.arms[unit] for unit in sorted(reported)}
    design, reference = (
        plan
        if plan is not None
        else _plan(seal, contracts=contracts, built=built, metric_id=metric_id, units=roster)
    )
    observed = studentized(outcomes, arms, design)
    p_value = permutation_p(observed, reference, outcomes, direction=direction)
    return Look(
        weeks=len(weeks),
        uplift_cents=observed.difference,
        raw_difference_cents=difference_in_means(outcomes, arms),
        p_value=p_value,
        significant=p_value <= Fraction(contracts.inference.alpha),
    )


# --------------------------------------------------------------------------- the pool


@dataclass(frozen=True, slots=True)
class Task:
    """One design, one lottery seed, one scenario: three small values in, a record out.

    The same contract `evals/uplift/parallel.py` describes and for the same reason -- a seal
    does not survive a round trip and must not, so a worker re-derives its own lottery from
    the seed. The world is built once per worker from the cache and the contracts and the
    recording are read there rather than pickled across.
    """

    index: int
    lottery_seed: str
    scenario: str


def run_task(task: Task) -> Violated | None:
    contracts, world, recording = pool.worker_state()
    recorded = recording.outcomes[task.index]
    scenario = peeking if task.scenario == "peeking" else post_hoc
    return scenario(recorded, contracts=contracts, built=world, lottery_seed=task.lottery_seed)


def run_all(
    recording: build.Recording, *, lotteries: int, workers: int | None = None
) -> tuple[Violated, ...]:
    """Every (design, seed, scenario), across `evals.design.pool`, in a deterministic order."""
    tasks = [
        Task(index=o.index, lottery_seed=seed, scenario=scenario)
        for seed in lottery_seeds(lotteries)
        for o in recording.outcomes
        for scenario in ("peeking", "post_hoc")
    ]
    results = pool.run(run_task, tasks, workers=workers)
    return tuple(r for r in results if r is not None)


__all__ = ["Task", "Violated", "lottery_seeds", "peeking", "peeking_rule", "post_hoc", "run_all"]
