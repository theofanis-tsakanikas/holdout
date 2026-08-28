"""Both potential outcomes for every unit, from two counterfactual worlds — and why that is
allowed at all.

The naive reading of *"every draw runs the whole system"* is two hundred world generations per
world: the data depend on the assignment. **It does not, in five of the six**, and that is a
fact about the generator which is checked rather than assumed.

`corpus/world/generate.py` is store-major, and the only place another store's arm enters a
store's emission is `_spillover`, whose first line is::

    if world.spillover_pct == 0:
        return 1.0

`spillover_pct` is non-zero in **W2 alone**. So in W1, W3, W4, W5 and W6 a store's whole event
stream is a function of its own arm and nothing else, and two generations — every store
control, every store treated — give each unit **both** potential outcomes exactly. Any lottery
is then a lookup::

    Y_observed[i] = Y_treatment[i] if arms[i] is TREATMENT else Y_control[i]

Two generations buy forty lotteries. That is the whole reason K = 200 is affordable.

**W1 needs one generation, not two.** `treats=False`, so both arms run the same policy and
`Y(1) ≡ Y(0)`; `tests/corpus/test_world_determinism.py` already asserts the two streams are
byte-identical except for the arm label on the decision record, and the metric does not read
that label. Empty is empty.

**The two generations are cached**, keyed on the world, the seed, the scale and a digest of
every source file they were produced by — see `cache.py`. A world is a pure function of those
three things, so generating it again inside the same command would be waste rather than
evidence; and a mutation that changes the corpus or the code that groups it moves the digest
and regenerates, which is checked rather than remembered.

**W2 generates per assignment**, and the eval says so rather than hiding it. A world built to
break the stable unit treatment value assumption, whose outcomes could nonetheless be composed
unit by unit, would not be breaking it — so `tests/evals/test_uplift_composition.py` asserts
the composition is exact on the five and **wrong on W2**, which is the only way that sentence
can be worth anything.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from corpus.world import Arm, Run, prepare
from corpus.world.scale import Scale
from corpus.world.worlds import World, world_by_id

from evals.uplift import cache, outcomes
from evals.uplift.outcomes import Week

if TYPE_CHECKING:
    from holdout.contracts.model import Rounding


class PotentialError(ValueError):
    """The composition was asked for something the generator does not support."""


@dataclass(frozen=True, slots=True)
class Potential:
    """`Y(1)` and `Y(0)` for every unit-week, and the run each was taken from.

    `run` is the all-control run, kept because the roster, the chain, the neighbour pairs and
    the two policy refs are read off it — every one of which is a fact about the estate rather
    than about an arm, so which of the two runs supplies them cannot matter.
    """

    world: World
    world_seed: str
    scale: Scale
    run: Run
    control: Mapping[tuple[str, Week], int]
    treatment: Mapping[tuple[str, Week], int]
    control_ledger: outcomes.Ledger
    treatment_ledger: outcomes.Ledger

    @property
    def weeks(self) -> tuple[Week, ...]:
        return tuple(sorted({week for _unit, week in self.control}))

    @property
    def units(self) -> tuple[str, ...]:
        return tuple(sorted({unit for unit, _week in self.control}))

    @property
    def generations(self) -> int:
        """One for the A/A world, two otherwise. Printed, because it is the budget."""
        return 1 if self.world.is_aa else 2


def _arms(run: Run, arm: Arm) -> dict[str, Arm]:
    return {store.store_id: arm for store in run.chain.stores}


def build(world_id: str, *, world_seed: str, scale: Scale, rounding: Rounding) -> Potential:
    """The two counterfactual worlds, aggregated to unit-weeks.

    Under common random numbers: `corpus/world/rng.py` keys every draw on what it is a draw
    *about* and never on the arm, so the two runs draw the same numbers for every store whose
    policy did not change. The difference between them is the treatment effect and not Monte
    Carlo noise, which is what makes a per-unit truth computable at all.
    """
    world = world_by_id(world_id)
    if world.spillover_pct:
        raise PotentialError(
            f"{world.id} declares spillover_pct={world.spillover_pct}, so a store's outcome "
            "depends on its neighbour's arm and there is no such thing as its potential "
            "outcome under a lottery it has not seen. Generate it per assignment."
        )
    control_run = prepare(world, seed=world_seed, scale=scale)
    control_run = prepare(
        world, seed=world_seed, scale=scale, assignment=_arms(control_run, Arm.CONTROL)
    )
    (control_ledger,) = cache.ledgers(
        cache.key("potential/control", world.id, world_seed, scale.name),
        lambda: (outcomes.collect(control_run),),
    )
    control = outcomes.unit_weeks(control_ledger, rounding)
    if world.is_aa:
        return Potential(
            world=world,
            world_seed=world_seed,
            scale=scale,
            run=control_run,
            control=control,
            treatment=control,
            control_ledger=control_ledger,
            treatment_ledger=control_ledger,
        )
    treated_run = prepare(
        world, seed=world_seed, scale=scale, assignment=_arms(control_run, Arm.TREATMENT)
    )
    (treatment_ledger,) = cache.ledgers(
        cache.key("potential/treatment", world.id, world_seed, scale.name),
        lambda: (outcomes.collect(treated_run),),
    )
    return Potential(
        world=world,
        world_seed=world_seed,
        scale=scale,
        run=control_run,
        control=control,
        treatment=outcomes.unit_weeks(treatment_ledger, rounding),
        control_ledger=control_ledger,
        treatment_ledger=treatment_ledger,
    )


def counterfactual_unit_weeks(
    world_id: str, *, world_seed: str, scale: Scale, rounding: Rounding
) -> tuple[dict[tuple[str, Week], int], dict[tuple[str, Week], int]]:
    """`Y(0)` and `Y(1)` for every unit-week, for **any** world including W2.

    `build` refuses a world that declares spillover, because there is no such thing as a
    unit's potential outcome under a lottery it has not seen when a neighbour's arm is in the
    answer. That guard stays exactly where it is: nothing here composes a draw.

    What this is for is the **estimand**. Under all-control no store has a treated neighbour
    and under all-treatment none has a control one, so `_spillover` returns 1.0 in both — the
    two counterfactual worlds carry no interference at all, and their difference is the
    average effect a difference of means would target if the stable unit treatment value
    assumption held. That is precisely the number W2's bias is a deviation from, so it is the
    number `U6` compares against.
    """
    world = world_by_id(world_id)
    base = prepare(world, seed=world_seed, scale=scale)
    pair: list[dict[tuple[str, Week], int]] = []
    for arm in (Arm.CONTROL, Arm.TREATMENT):
        run = prepare(world, seed=world_seed, scale=scale, assignment=_arms(base, arm))
        (ledger,) = cache.ledgers(
            cache.key(f"counterfactual/{arm.value}", world.id, world_seed, scale.name),
            lambda run=run: (outcomes.collect(run),),  # type: ignore[misc]
        )
        pair.append(outcomes.unit_weeks(ledger, rounding))
    return pair[0], pair[1]


def compose_exposure(
    potential: Potential, arms: Mapping[str, Arm]
) -> tuple[dict[str, int], dict[str, int], dict[str, frozenset[str]]]:
    """The acknowledgement counts and delivered policies a lottery would have produced.

    They compose exactly as the outcomes do and for the same reason: a store's
    acknowledgements are drawn on keys that carry the store, the SKU and the day and never
    the arm, so a store's stream is a function of its own arm alone outside W2.

    **Read from the corpus, never inferred from the assignment.** An acknowledgement is the
    only evidence a price reached a shelf; a delivered-policy map derived from the arms would
    make the contamination check a statement about itself.
    """
    dispatched: dict[str, int] = {}
    acknowledged: dict[str, int] = {}
    delivered: dict[str, frozenset[str]] = {}
    for unit in potential.units:
        ledger = (
            potential.treatment_ledger if arms[unit] is Arm.TREATMENT else potential.control_ledger
        )
        dispatched[unit] = ledger.dispatched.get(unit, 0)
        acknowledged[unit] = ledger.acknowledged.get(unit, 0)
        delivered[unit] = ledger.delivered.get(unit, frozenset())
    return dispatched, acknowledged, delivered


def compose(potential: Potential, arms: Mapping[str, Arm]) -> dict[tuple[str, Week], int]:
    """The unit-weeks a lottery would have produced, without generating the world again.

    Every unit on the roster must carry an arm. A unit left out would silently take its
    control outcome, which is the same defect `generate` refuses one layer down: a store with
    no arm quietly shrinks the experiment.
    """
    missing = sorted({unit for unit, _week in potential.control} - set(arms))
    if missing:
        raise PotentialError(
            f"{len(missing)} unit(s) have no arm to compose from: {missing[:5]}. A unit "
            "without one would take the control outcome and nobody would have drawn it."
        )
    return {
        key: (potential.treatment if arms[key[0]] is Arm.TREATMENT else potential.control)[key]
        for key in potential.control
    }
