"""The property K = 200 rests on: a unit's outcome is a function of its own arm — except in W2.

`evals/uplift/potential.py` composes each draw's outcomes from two counterfactual generations
instead of generating a world per lottery, which is the whole reason two hundred draws are
affordable. That is a **claim about the generator**, so it is checked against the generator
rather than argued from its docstring: a mixed assignment is generated for real, and the
per-unit metric it produces has to equal the composed value **as integers**. Not close: equal.

And the same test on W2 must **fail**, which is asserted here rather than skipped. A world
built to break the stable unit treatment value assumption whose outcomes could nonetheless be
composed unit by unit would not be breaking it, and the eval that estimates on what W2 leaves
behind would be estimating on a world with no interference in it.

The mixed assignment is `corpus.world.alternating` — deterministic, and not a lottery, which
its own docstring is careful about. Nothing here produces a number: the property under test is
a fact about how the generator emits a store, and drawing the arms with the real engine would
add a dependency on the covariate matrix for no gain. It is also the harder case by accident:
stores are laid out in contiguous town blocks, so a clustered pair sits on consecutive
ordinals and `alternating` puts the two members of it in **opposite arms** — which is exactly
the arrangement W2's spillover acts on.
"""

from __future__ import annotations

import pytest
from corpus.world import Arm, alternating, prepare
from corpus.world.assignment import Assignment
from corpus.world.scale import SMOKE
from evals.uplift import grouped_metric, outcomes, potential

from holdout.contracts.model import ContractSet, Rounding

SEED = "composition"

#: Every world whose stores emit independently — the five `spillover_pct == 0` leaves.
INDEPENDENT = ("W1", "W3", "W4", "W5", "W6")


@pytest.fixture(scope="module")
def rounding(contracts: ContractSet) -> Rounding:
    versions = contracts.metric_versions("category_margin_per_store_week")
    return versions[-1].rounding


def _observed(world_id: str, rounding: Rounding) -> dict[tuple[str, tuple[int, int]], int]:
    run = prepare(world_id, seed=SEED, scale=SMOKE)
    mixed = alternating(run.chain)
    generated = prepare(world_id, seed=SEED, scale=SMOKE, assignment=mixed)
    return grouped_metric.unit_weeks(outcomes.collect(generated), rounding)


@pytest.mark.parametrize("world_id", INDEPENDENT)
def test_composition_is_exact_where_there_is_no_interference(
    world_id: str, rounding: Rounding
) -> None:
    """Integer equality, per unit and per week, between generating and composing."""
    built = potential.build(world_id, world_seed=SEED, scale=SMOKE, rounding=rounding)
    run = prepare(world_id, seed=SEED, scale=SMOKE)
    composed = potential.compose(built, alternating(run.chain))
    generated = _observed(world_id, rounding)
    assert composed.keys() == generated.keys()
    disagreeing = {key for key, value in composed.items() if generated[key] != value}
    assert not disagreeing, (
        f"{world_id}: {len(disagreeing)} of {len(composed)} unit-weeks differ between a world "
        f"generated under the assignment and one composed from two counterfactuals — "
        f"{sorted(disagreeing)[:3]}. The composition is not exact, so every draw would have "
        "to generate its own world and K = 200 is not affordable"
    )


def test_the_a_a_world_needs_only_one_generation(rounding: Rounding) -> None:
    """W1's two potential outcomes are the same object, and that is the point of an A/A world.

    Both arms run the same policy, so there is nothing to generate twice. It is asserted
    because the budget assumes it: `Potential.generations` is 1 here and 2 everywhere else,
    and a W1 that quietly cost two generations would be paying for a counterfactual that
    cannot differ.
    """
    built = potential.build("W1", world_seed=SEED, scale=SMOKE, rounding=rounding)
    assert built.generations == 1
    assert built.control == built.treatment


def test_composition_is_wrong_under_interference(rounding: Rounding) -> None:
    """W2 must break it, and the eval refuses to compose a world that declares spillover.

    Two assertions, because they fail for different reasons. `potential.build` refuses W2
    outright — a potential outcome under a lottery the unit has not seen is not a thing that
    exists when a neighbour's arm is in the answer. And the composition, done by hand from the
    two counterfactuals anyway, has to **disagree** with the world generated under the same
    assignment: if it agreed, W2 would have no interference in it and every eval downstream of
    it would be measuring nothing.
    """
    with pytest.raises(potential.PotentialError, match="spillover_pct"):
        potential.build("W2", world_seed=SEED, scale=SMOKE, rounding=rounding)

    run = prepare("W2", seed=SEED, scale=SMOKE)
    mixed = alternating(run.chain)
    control = grouped_metric.unit_weeks(
        outcomes.collect(
            prepare("W2", seed=SEED, scale=SMOKE, assignment=_all(mixed, treated=False))
        ),
        rounding,
    )
    treated = grouped_metric.unit_weeks(
        outcomes.collect(
            prepare("W2", seed=SEED, scale=SMOKE, assignment=_all(mixed, treated=True))
        ),
        rounding,
    )
    composed = {
        key: (treated if mixed[key[0]] is Arm.TREATMENT else control)[key] for key in control
    }
    generated = _observed("W2", rounding)
    disagreeing = {key for key, value in composed.items() if generated[key] != value}
    assert disagreeing, (
        "W2 composed exactly, unit by unit, from two counterfactuals — so a store's outcome "
        "does not depend on its neighbour's arm and the interference world has stopped "
        "interfering. Everything downstream of it would be green and worthless"
    )


def _all(mixed: Assignment, *, treated: bool) -> dict[str, Arm]:
    """Every store on one arm — the two counterfactuals, built here rather than imported.

    `potential.build` refuses W2, which is the point of the test above, so W2's counterfactuals
    have to be constructed by hand to show what the composition would have claimed.
    """
    return dict.fromkeys(mixed, Arm.TREATMENT if treated else Arm.CONTROL)
