"""The engine's verdict on every recorded proposal, and the number a refused one would have made.

Two things happen here and they are kept apart on purpose.

**The verdict** is `holdout.core.design.feasibility.assess`, called on this run with the
proposal completed by the human's two fields and the world's own pre-period. Nothing is read
from disk except the proposal. A proposal the harness cannot grade — a unit it has no roster
for, a metric it has no history for — is `ungraded` with the reason, never assessed against a
roster or a variance that belongs to a different design: a region design assessed over three
hundred and twenty stores would produce a verdict about a design nobody proposed, and it would
look exactly like a verdict.

**The number anyway** is what a system without this one's guards would have reported. A
refused design is drawn from its committed seed over the same roster the engine would have
used, its outcomes composed from the world's potential outcomes for that assignment, and the
estimator run on them with the four validity checks **skipped** — the difference, the
permutation p-value and the interval, as `close()` computes them after the checks it would
never have got past. On the null world the true effect is zero, so a number significant at the
declared α is a false positive the refusal prevented, and an interval that excludes zero is
one that excludes the truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from corpus.world import Arm as WorldArm

from evals.design import build
from evals.uplift import design as design_module
from evals.uplift import grouped_metric, potential
from holdout.core.design import DesignRefusal, DesignRefusalReason, Feasible, assess
from holdout.core.design.feasibility import form_digest_of, interference_of, neighbour_exclusions
from holdout.core.design.form import MdeDirection, MdeKind, Unit
from holdout.core.design.refusal import DesignRefusalCode
from holdout.core.experiment import Arm
from holdout.core.experiment.assignment import draw, reference_set
from holdout.core.experiment.estimator import (
    design_of,
    interval,
    permutation_p,
    plan_for,
    studentized,
)

#: The unit the harness has a roster for. Its matrix is one row per store; a design at any
#: other unit has no roster here and is `ungraded`, with the reason.
GRADABLE_UNIT = Unit.STORE


@dataclass(frozen=True, slots=True)
class Verdict:
    """What the engine said about one recorded proposal. Exactly one of the three is set."""

    index: int
    feasible: Feasible | None = None
    refused: DesignRefusal | None = None
    ungraded: str | None = None

    @property
    def codes(self) -> tuple[str, ...]:
        return () if self.refused is None else tuple(r.code.value for r in self.refused.reasons)


@dataclass(frozen=True, slots=True)
class Anyway:
    """The number a refused design would have produced with the guards off."""

    index: int
    codes: tuple[str, ...]
    uplift_cents: Fraction
    p_value: Fraction
    interval_cents: tuple[Fraction, Fraction]
    significant: bool
    #: `True` when the interval excludes the world's true effect -- on W1, zero.
    excludes_truth: bool
    units: int


def verdict(
    recorded: build.Recorded, *, contracts: build.ContractSet, built: build.World
) -> Verdict:
    """Moment 1 for one recorded proposal, or the reason it cannot be asked."""
    if recorded.proposal is None:
        return Verdict(index=recorded.index, ungraded=f"no proposal: {recorded.failed}")
    proposal = recorded.proposal
    if proposal.unit is not GRADABLE_UNIT:
        # Interference is a property of the unit and of the contract's carryover block, not
        # of any roster, so the engine's own predicate answers it for a unit the harness has
        # no roster for. What it cannot answer without a roster -- capacity, duration -- is
        # not answered: a region design sized over three hundred and twenty stores would be
        # a verdict about a design nobody proposed.
        why = interference_of(proposal.unit, contracts.inference.carryover)
        if why is not None:
            return Verdict(
                index=recorded.index,
                refused=DesignRefusal(
                    experiment_id=f"design/{recorded.index:03d}",
                    reasons=(
                        DesignRefusalReason(
                            code=DesignRefusalCode.UNIT_GUARANTEES_INTERFERENCE,
                            detail=why,
                            what_would_fix_it=(
                                "A unit the declared carryover does not cross: store or region."
                            ),
                        ),
                    ),
                ),
            )
        return Verdict(
            index=recorded.index,
            ungraded=(
                f"unit {proposal.unit.value}: the harness has a roster of stores and no "
                f"roster of {proposal.unit.value}s. The unit crosses no declared carryover, so "
                "what remains to decide is capacity and duration, and those need a roster."
            ),
        )
    pre = built.pre_by_metric.get(proposal.primary_metric)
    if pre is None:
        return Verdict(
            index=recorded.index,
            ungraded=(
                f"metric {proposal.primary_metric}: the harness ledger carries no history for "
                "it, so there is no variance to size the design against."
            ),
        )
    form = build.complete(proposal)
    metric = contracts.metric_versions(proposal.primary_metric)[-1]
    assessed = assess(
        form,
        experiment_id=f"design/{recorded.index:03d}",
        seed=build.LOTTERY_SEED,
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
        stopping=design_module.STOPPING,
        previously_locked=None,
    )
    if isinstance(assessed, DesignRefusal):
        return Verdict(index=recorded.index, refused=assessed)
    return Verdict(index=recorded.index, feasible=assessed)


def anyway(
    recorded: build.Recorded,
    verdict_: Verdict,
    *,
    contracts: build.ContractSet,
    built: build.World,
) -> Anyway | None:
    """The guards-off number for a refused design, or `None` where it cannot be drawn.

    The roster is the engine's: the declared exclusions removed, then the later-sorted member
    of every neighbouring pair, exactly as `assess` does before it sizes the design. The
    control size is the contract's holdout share of what is left. Then the same lottery from
    the same seed, and the estimator on the composed outcomes.
    """
    if verdict_.refused is None or recorded.proposal is None:
        return None
    proposal = recorded.proposal
    if proposal.unit is not GRADABLE_UNIT:
        # Refused for its unit, and the harness has no roster at that unit to draw over. It
        # is counted as refused-but-not-runnable, which D6 prints; running it over the store
        # roster would be a number about a design nobody proposed.
        return None
    pre = built.pre_by_metric[proposal.primary_metric]
    form = build.complete(proposal)

    declared = frozenset(e.store_id for e in proposal.exclusions)
    after_declared = tuple(u for u in pre.matrix.units if u not in declared)
    automatic = neighbour_exclusions(
        after_declared, built.fixture.run.chain.neighbour_pairs, declared
    )
    excluded = declared | frozenset(e.store_id for e in automatic)
    available = tuple(u for u in pre.matrix.units if u not in excluded)
    control_size = int(len(available) * Decimal(contracts.inference.holdout_share_pct) / 100)
    if control_size < 1 or len(available) - control_size < 1:
        return None

    drawn = draw(
        experiment_id=f"design/{recorded.index:03d}/anyway",
        roster=available,
        seed=build.LOTTERY_SEED,
        form_digest=form_digest_of(form),
        matrix=pre.matrix.restricted_to(frozenset(available)),
        control_size=control_size,
    )
    if drawn is None:
        return None
    seal, _balance = drawn
    arms = dict(seal.arms)

    fixture = built.fixture
    assert fixture.potential_ is not None, "W1 has potential outcomes; the fixture lost them"
    world_arms = {
        store.store_id: (
            WorldArm.TREATMENT if arms.get(store.store_id) is Arm.TREATMENT else WorldArm.CONTROL
        )
        for store in fixture.run.chain.stores
    }
    metric = contracts.metric_versions(proposal.primary_metric)[-1]
    by_unit_week = _unit_weeks_for(proposal.primary_metric, fixture, world_arms)
    unit_outcomes = grouped_metric.window_mean(
        by_unit_week, units=seal.roster, weeks=pre.period_weeks, rounding=metric.rounding
    )

    reported = frozenset(seal.roster) & frozenset(unit_outcomes)
    arms_reported = {unit: seal.arms[unit] for unit in sorted(reported)}
    matrix = pre.matrix.restricted_to(reported)
    design = design_of(matrix)
    observed = studentized(unit_outcomes, arms_reported, design)
    draws = reference_set(
        seal,
        draws=contracts.inference.permutation_draws,
        max_attempts=contracts.inference.max_assignment_attempts,
    )
    restricted = [
        {unit: arm for unit, arm in candidate.items() if unit in reported} for candidate in draws
    ]
    plan = plan_for(design, restricted)
    direction = proposal.mde.direction
    p_value = permutation_p(observed, plan, unit_outcomes, direction=direction)
    bounds = interval(unit_outcomes, arms_reported, plan, alpha=contracts.inference.alpha)
    alpha = Fraction(contracts.inference.alpha)
    low, high = Fraction(bounds[0]), Fraction(bounds[1])
    return Anyway(
        index=recorded.index,
        codes=verdict_.codes,
        uplift_cents=observed.difference,
        p_value=p_value,
        interval_cents=(low, high),
        significant=p_value <= alpha,
        excludes_truth=not (low <= 0 <= high),
        units=len(reported),
    )


def _unit_weeks_for(
    metric_id: str,
    fixture: build.harness.WorldFixture,
    world_arms: dict[str, WorldArm],
) -> dict[tuple[str, tuple[int, int]], int]:
    """The composed outcome per store-week for the metric the design named."""
    assert fixture.potential_ is not None
    if metric_id == build.MARGIN:
        return potential.compose(fixture.potential_, world_arms)
    if metric_id == build.WASTE:
        # The margin is composed by `potential.compose`; the waste column is composed here
        # from the same two ledgers by the same rule -- a treated store's week from the
        # treatment ledger, a control store's from the control one -- because the harness
        # only ever needed the one metric and this eval needs two.
        control = build._waste_unit_weeks(fixture.potential_.control_ledger)
        treatment = build._waste_unit_weeks(fixture.potential_.treatment_ledger)
        return {
            key: (treatment if world_arms[key[0]] is WorldArm.TREATMENT else control)[key]
            for key in control
        }
    raise ValueError(f"no potential outcomes for {metric_id}")


def mde_cents(proposal_mde_kind: MdeKind, value: Decimal, mean_cents: Decimal) -> Fraction:
    """The declared MDE as cents, the way `feasibility._absolute_mde` reads it."""
    if proposal_mde_kind is MdeKind.ABSOLUTE:
        return Fraction(value)
    return Fraction(mean_cents) * Fraction(value) / 100


def is_two_sided(direction: MdeDirection) -> bool:
    return direction is MdeDirection.EITHER
