"""One draw, one whole system run — and the record that comes back from it.

`CLAUDE.md` enumerates claim 2's system as *assignment, exposure collection, the four validity
checks, the readout*, and every one of them runs here, per draw:

1. the pre-period, measured off the **all-control** world: five covariates in the contract's
   own order, the mean per unit-week, and the variance the power calculation sizes on;
2. `assess(...)` — the nine-field form, the eight design refusals, the automatic neighbour
   exclusions, the committed seed, the stratified draw, the sealed assignment;
3. the comparison window's outcomes, **composed** from two counterfactual generations where
   the world permits it and generated per assignment where it does not;
4. exposure, **read from the corpus's acknowledgements** — the only evidence a price reached a
   shelf — and the delivered policy refs, read off the same stream;
5. `reference_set(...)`, then `close(...)`: balance, exposure, contamination, power, and only
   then a number.

**A refusal is a result.** A `DesignRefusal` at moment 1 and a `ReadoutRefusal` at moment 3 are
both recorded as what they are. Nothing is retried and **no draw is ever discarded** — a
harness that drops the draws it does not like is the fishing this repository exists to make
impossible, and it would do it while every individual number stayed true.

**Nothing here opens a seal.** The record carries no truth and no reference to one; the
comparison against the injected truth happens after every readout is on disk, in `worlds.py`,
through `corpus.world.seal.open_after_readout`, which refuses without a readout to be graded
against.

What crosses a process boundary
-------------------------------
Three strings go in and a small frozen record comes back. `SealedAssignment.__reduce__` raises
by design — a seal that survived a round trip could be restored in a process where no lottery
ever ran — so a worker re-derives its own lottery from the committed seed rather than being
handed one. That is a better shape anyway: it means the parallel harness and a single-process
run of the same draw are the same computation, not two arrangements of it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import timedelta
from fractions import Fraction

from corpus.world import Arm as WorldArm
from corpus.world import Run, prepare
from corpus.world.scale import CATEGORIES, Scale
from corpus.world.worlds import World, world_by_id

from evals.uplift import cache, outcomes, potential
from evals.uplift import design as design_module
from holdout.contracts.model import AaHarness, ContractSet
from holdout.core.design import DesignRefusal, Feasible, assess
from holdout.core.experiment import (
    CHECK_ORDER,
    Arm,
    Period,
    Readout,
    ReadoutRefusal,
    close,
    reference_set,
)

#: The metric every world is read out on.
METRIC_ID = "category_margin_per_store_week"


class HarnessError(RuntimeError):
    """A draw could not be run at all — never a refusal, which is a result."""


@dataclass(frozen=True, slots=True)
class DrawRecord:
    """What one draw produced. Plain data, so it crosses a process boundary intact.

    Carried whether the draw produced a number or refused, and carrying the same four check
    figures either way — a refusal that reported only the check that fired would hide how
    close the others came, which is most of what a reader of a refused readout wants to know.
    """

    world: str
    world_seed: str
    lottery_seed: str
    scale: str

    roster: int
    excluded: int
    control_size: int
    weeks: int

    design_refusals: tuple[str, ...] = ()
    readout_refusals: tuple[str, ...] = ()
    check_figures: tuple[tuple[str, bool, str], ...] = ()

    uplift_cents: Fraction | None = None
    interval_cents: tuple[int, int] | None = None
    p_value: Fraction | None = None
    permutation_draws: int = 0
    standard_error: str = ""
    significant: bool | None = None

    #: Every unit's outcome, so a world's check can compute what it needs without re-running
    #: the draw. Small — a few hundred integers — and it is what estimator bias and the
    #: interference pair are computed from once the seal has been opened.
    unit_outcomes: Mapping[str, int] = field(default_factory=dict)
    arms: Mapping[str, str] = field(default_factory=dict)
    digest: str = ""

    @property
    def produced_a_number(self) -> bool:
        return self.uplift_cents is not None

    @property
    def refused(self) -> tuple[str, ...]:
        return self.design_refusals + self.readout_refusals


def _period(scale: Scale, weeks: int) -> Period:
    """The comparison window, as dates, from the world's own calendar.

    The window is the last `weeks` ISO weeks the world spans, and the scale starts on a Monday
    so an ISO week and a calendar week are the same thing here. `ends_on` is the first day the
    period is **not** running, matching the half-open convention every effective window in
    `contracts/` uses.
    """
    ends_on = scale.start_date + timedelta(days=scale.days)
    return Period(opens_on=ends_on - timedelta(weeks=weeks), ends_on=ends_on)


def _by_unit(cells: Mapping[outcomes.Cell, int], weeks: Sequence[outcomes.Week]) -> dict[str, int]:
    wanted = set(weeks)
    out: dict[str, int] = {}
    for (store, year, week, _category), value in cells.items():
        if (year, week) in wanted:
            out[store] = out.get(store, 0) + value
    return out


def _sole(refs: frozenset[str]) -> str:
    """The one policy a unit was delivered, or a name no arm declares.

    A unit that ran two policy versions inside one experiment is contamination, and it is
    reported as such by giving the check something that matches neither arm rather than by
    picking one of the two and calling it the answer.
    """
    return next(iter(refs)) if len(refs) == 1 else "<more than one policy delivered>"


def _exposed(
    dispatched: Mapping[str, int],
    acknowledged: Mapping[str, int],
    treated: Sequence[str],
    *,
    minimum_pct: Fraction,
) -> frozenset[str]:
    """Which treated units count as exposed — the eval's own line, declared in its contract.

    `holdout.core` measures exposure per **unit** and a world fails acknowledgements per
    **price change**, so something has to say where the line between the two grains is. It is
    `aa_harness.yaml`'s `unit_exposed_min_ack_pct`, and it is deliberately not the core's
    `exposure_min_pct`: that number is the floor on the share of exposed units, this one is
    the definition of an exposed unit.

    A treated unit with no price change at all is **not** exposed. There is no acknowledgement
    to have arrived, so there is no evidence the treatment reached it, and reading an empty
    ledger as full compliance is the direction that always flatters.
    """
    out: set[str] = set()
    for unit in treated:
        sent = dispatched.get(unit, 0)
        if sent and Fraction(acknowledged.get(unit, 0), sent) >= minimum_pct:
            out.add(unit)
    return frozenset(out)


@dataclass(frozen=True, slots=True)
class WorldFixture:
    """One world seed's pre-period, its form, and the potential outcomes if it has any.

    Built once per `(world, world_seed)` and reused by every lottery drawn against it. That
    reuse is the whole budget: two generations buy forty lotteries outside W2, and W2 pays
    per lottery because a store's outcome there depends on its neighbour's arm.
    """

    world: World
    world_seed: str
    scale: Scale
    run: Run
    pre: design_module.PrePeriod
    form_: object
    potential_: potential.Potential | None
    control_policy: str
    treatment_policy: str


def build_fixture(
    world_id: str, *, world_seed: str, scale: Scale, contracts: ContractSet
) -> WorldFixture:
    """Generate what every lottery against this world seed will share."""
    world = world_by_id(world_id)
    metric = contracts.metric_versions(METRIC_ID)[-1]
    base = prepare(world, seed=world_seed, scale=scale)
    control_arms = {store.store_id: WorldArm.CONTROL for store in base.chain.stores}
    control_run = prepare(world, seed=world_seed, scale=scale, assignment=control_arms)
    # The all-control world is generated **once**. Both the pre-period and the potential
    # outcomes need it, and generating it twice would spend a third of this harness's whole
    # clock bill on a world it already had. Where a world declares spillover there are no
    # potential outcomes to build and this is the only generation the fixture pays for.
    built = (
        None
        if world.spillover_pct
        else potential.build(world_id, world_seed=world_seed, scale=scale, rounding=metric.rounding)
    )
    control_ledger = (
        built.control_ledger
        if built is not None
        else cache.ledgers(
            cache.key("potential/control", world.id, world_seed, scale.name),
            lambda: (outcomes.collect(control_run),),
        )[0]
    )
    weeks = control_ledger.weeks
    pre_weeks, _period_weeks = design_module.split_weeks(weeks)
    pre = design_module.pre_period(
        control_run,
        by_unit_week=outcomes.unit_weeks(control_ledger, metric.rounding),
        revenue_by_unit=_by_unit(control_ledger.revenue_cents, pre_weeks),
        cogs_by_unit=_by_unit(control_ledger.cogs_cents, pre_weeks),
        waste_by_unit=_by_unit(control_ledger.waste_cents, pre_weeks),
        weeks=weeks,
        covariates=contracts.balance_covariates,
    )
    return WorldFixture(
        world=world,
        world_seed=world_seed,
        scale=scale,
        run=control_run,
        pre=pre,
        form_=design_module.form(
            harness=contracts.aa_harness,
            categories=CATEGORIES,
            treatment_policy=base.treatment.policy_id,
            control_policy=base.control.policy_id,
        ),
        potential_=built,
        control_policy=base.control.policy_id,
        treatment_policy=base.treatment.policy_id,
    )


def run_one(
    fixture: WorldFixture,
    *,
    lottery_seed: str,
    contracts: ContractSet,
    harness: AaHarness,
    withhold_neighbour_pairs: bool = False,
    permutation_draws: int | None = None,
) -> DrawRecord:
    """One lottery, end to end, and a record either way.

    `withhold_neighbour_pairs` is W2's second arm and nothing else's: the same world and the
    same seed with the interfering pairs **not** declared to the engine, so the eval can
    publish what the exclusion is worth rather than assert that it is worth something.
    """
    metric = contracts.metric_versions(METRIC_ID)[-1]
    inference = contracts.inference
    scale = fixture.scale
    pairs = () if withhold_neighbour_pairs else fixture.run.chain.neighbour_pairs

    assessed = assess(
        fixture.form_,  # type: ignore[arg-type]
        experiment_id=f"aa/{fixture.world.id}/{fixture.world_seed}/{lottery_seed}",
        seed=lottery_seed,
        metric=metric,
        metric_ids=contracts.metric_ids,
        covariates=contracts.balance_covariates,
        inference=inference,
        roster=fixture.pre.matrix.units,
        matrix=fixture.pre.matrix,
        variance_per_unit_week=fixture.pre.variance_per_unit_week,
        mean_per_unit_week=fixture.pre.mean_per_unit_week,
        committed_elsewhere=frozenset(),
        neighbour_pairs=pairs,
        stopping=design_module.STOPPING,
        previously_locked=None,
    )
    roster_size = len(fixture.pre.matrix.units)
    if isinstance(assessed, DesignRefusal):
        return DrawRecord(
            world=fixture.world.id,
            world_seed=fixture.world_seed,
            lottery_seed=lottery_seed,
            scale=scale.name,
            roster=roster_size,
            excluded=0,
            control_size=0,
            weeks=design_module.PERIOD_WEEKS,
            design_refusals=tuple(code.value for code in assessed.codes),
        )
    return _close_one(
        assessed,
        fixture=fixture,
        lottery_seed=lottery_seed,
        contracts=contracts,
        harness=harness,
        roster_size=roster_size,
        permutation_draws=permutation_draws,
    )


def _close_one(
    feasible: Feasible,
    *,
    fixture: WorldFixture,
    lottery_seed: str,
    contracts: ContractSet,
    harness: AaHarness,
    roster_size: int,
    permutation_draws: int | None,
) -> DrawRecord:
    metric = contracts.metric_versions(METRIC_ID)[-1]
    inference = contracts.inference
    seal = feasible.assignment
    arms = dict(seal.arms)

    world_arms = {
        store.store_id: (
            WorldArm.TREATMENT if arms.get(store.store_id) is Arm.TREATMENT else WorldArm.CONTROL
        )
        for store in fixture.run.chain.stores
    }
    if fixture.potential_ is not None:
        by_unit_week = potential.compose(fixture.potential_, world_arms)
        dispatched, acknowledged, delivered_refs = potential.compose_exposure(
            fixture.potential_, world_arms
        )
    else:
        drawn_run = prepare(
            fixture.world, seed=fixture.world_seed, scale=fixture.scale, assignment=world_arms
        )
        # W2 alone: a store's outcome depends on its neighbour's arm, so there are no potential
        # outcomes to compose and the world is generated for this lottery. Cached on the arms
        # as well as on the world, because here the arms are part of what was generated.
        (ledger,) = cache.ledgers(
            cache.key(
                "drawn",
                fixture.world.id,
                fixture.world_seed,
                fixture.scale.name,
                "".join(world_arms[store].value[0] for store in sorted(world_arms)),
            ),
            lambda: (outcomes.collect(drawn_run),),
        )
        by_unit_week = outcomes.unit_weeks(ledger, metric.rounding)
        dispatched, acknowledged, delivered_refs = (
            dict(ledger.dispatched),
            dict(ledger.acknowledged),
            dict(ledger.delivered),
        )

    period_weeks = fixture.pre.period_weeks
    unit_outcomes = outcomes.window_mean(
        by_unit_week,
        units=seal.roster,
        weeks=period_weeks,
        rounding=metric.rounding,
    )
    exposed = _exposed(
        dispatched,
        acknowledged,
        seal.treatment,
        minimum_pct=Fraction(harness.unit_exposed_min_ack_pct) / 100,
    )
    delivered = {
        unit: _sole(delivered_refs[unit]) for unit in seal.roster if delivered_refs.get(unit)
    }
    draws = reference_set(
        seal,
        draws=permutation_draws or inference.permutation_draws,
        max_attempts=inference.max_assignment_attempts,
    )
    period = _period(fixture.scale, len(period_weeks))
    result = close(
        seal,
        outcomes=unit_outcomes,
        exposed=exposed,
        delivered=delivered,
        treatment_policy=fixture.treatment_policy,
        control_policy=fixture.control_policy,
        covariates_at_close=fixture.pre.matrix,
        draws=draws,
        inference=inference,
        metric=metric,
        mde_absolute=feasible.mde_absolute,
        direction=fixture.form_.mde.direction,  # type: ignore[attr-defined]
        form_digest=feasible.form_digest,
        data_version=(f"corpus/world/{fixture.world.id}@{fixture.world_seed}/{fixture.scale.name}"),
        period=period,
        asked_on=period.ends_on,
    )
    figures = tuple((c.check.value, c.passed, c.figure) for c in result.checks)
    common = {
        "world": fixture.world.id,
        "world_seed": fixture.world_seed,
        "lottery_seed": lottery_seed,
        "scale": fixture.scale.name,
        "roster": roster_size,
        "excluded": len(feasible.automatic_exclusions),
        "control_size": feasible.control_size,
        "weeks": len(period_weeks),
        "check_figures": figures,
        "unit_outcomes": unit_outcomes,
        "arms": {unit: arm.value for unit, arm in arms.items()},
        "digest": seal.digest,
    }
    if isinstance(result, ReadoutRefusal):
        return DrawRecord(readout_refusals=tuple(c.value for c in result.codes), **common)  # type: ignore[arg-type]
    assert isinstance(result, Readout)
    return DrawRecord(
        uplift_cents=result.uplift,
        interval_cents=result.confidence_interval,
        p_value=result.p_value,
        permutation_draws=result.draws,
        standard_error=f"{result.statistic.standard_error:.4f}",
        significant=result.is_significant,
        **common,  # type: ignore[arg-type]
    )


#: The declared order the four checks are reported in, re-exported so a reader of a record
#: does not have to import the core to know what the third figure is about.
CHECKS = tuple(check.value for check in CHECK_ORDER)
