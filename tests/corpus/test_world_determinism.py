"""Reproducible, order-independent, and drawing common random numbers across arms.

These are the three properties `rng.py` claims, and they are the three the whole of claim 2
leans on:

- **Reproducible**, or a sealed truth means nothing and nobody can re-run the harness.
- **Order-independent**, or a window onto the scenario-scale world is a different world.
- **Common random numbers**, or T003's counterfactual differs from the observed world by the
  treatment effect *plus* Monte-Carlo noise, and the reference implementation of truth is
  measuring the noise as well as the effect.

The A/A test at the bottom is the strongest statement in this file: under W1 the assignment
makes **no difference at all**, byte for byte. `CLAUDE.md`: *"It needs no ground truth at all:
empty is empty, so no one can argue the simulation was rigged."*
"""

from __future__ import annotations

from collections.abc import Container, Sequence
from dataclasses import asdict

import pytest
from corpus.world import Arm, Event, Run, all_control, alternating, events, prepare

SEED = "determinism"


#: Every field of every event, as a comparable tuple. Read off the dataclass rather than
#: listed, so a field added to a stream is compared from the day it exists.
Fingerprint = list[tuple[str, str, tuple[object, ...]]]


def _tuple(event: Event, *, without: str = "") -> tuple[object, ...]:
    return tuple(value for name, value in asdict(event).items() if name != without)


def _fingerprint(
    run: Run, *, only_stores: Sequence[str] | None = None, without: str = ""
) -> Fingerprint:
    return [
        (type(event).__name__, event.store_id, _tuple(event, without=without))
        for event in events(run, only_stores=only_stores)
    ]


def _only(mark: Fingerprint, stores: Container[str]) -> Fingerprint:
    return [row for row in mark if row[1] in stores]


def test_the_same_world_twice_is_the_same_world() -> None:
    one = _fingerprint(prepare("W6", seed=SEED, scale="smoke"))
    other = _fingerprint(prepare("W6", seed=SEED, scale="smoke"))
    assert one == other
    assert one, "a world with no events would make every test in this file vacuous"


def test_a_different_seed_is_a_different_world() -> None:
    assert _fingerprint(prepare("W6", seed="one", scale="smoke")) != _fingerprint(
        prepare("W6", seed="two", scale="smoke")
    )


def test_a_window_onto_the_world_is_the_same_world() -> None:
    """`only_stores` must be a window and not a smaller world.

    This is what makes the scenario-scale corpus inspectable without materialising it, and it
    only holds because no draw is keyed on anything outside the store it belongs to.
    """
    run = prepare("W6", seed=SEED, scale="smoke")
    wanted = [run.chain.stores[2].store_id, run.chain.stores[5].store_id]
    windowed = _fingerprint(run, only_stores=wanted)
    assert windowed == _only(_fingerprint(run), set(wanted))
    assert windowed


def test_common_random_numbers_hold_for_every_untreated_store() -> None:
    """Re-run under all-control: a store whose policy did not change did not change.

    T003 computes the true effect on the metric by running exactly this counterfactual and
    subtracting. If the untreated stores moved between the two runs, that subtraction would be
    measuring simulation noise as well as the treatment, and the "independent measurement of
    truth" would be independent of nothing.
    """
    run = prepare("W6", seed=SEED, scale="smoke")
    counterfactual = prepare("W6", seed=SEED, scale="smoke", assignment=all_control(run.chain))
    controls = {s for s, arm in run.assignment.items() if arm is Arm.CONTROL}
    observed = _only(_fingerprint(run), controls)
    counter = _only(_fingerprint(counterfactual), controls)
    assert observed == counter
    assert observed


def test_the_treated_stores_are_the_ones_that_moved() -> None:
    """The other half of the same statement: something has to change, or W6 has no effect."""
    run = prepare("W6", seed=SEED, scale="smoke")
    counterfactual = prepare("W6", seed=SEED, scale="smoke", assignment=all_control(run.chain))
    treated = set(run.treated)
    assert treated
    assert _only(_fingerprint(run), treated) != _only(_fingerprint(counterfactual), treated)


def test_under_the_aa_world_the_assignment_changes_nothing_at_all() -> None:
    """W1, byte for byte. Both arms get the same policy and nothing is applied.

    No ground truth is needed to grade this and none is consulted: two runs of the same world
    under two different assignments produce the identical stream. Empty is empty.
    """
    chain = prepare("W1", seed=SEED, scale="smoke").chain
    a = prepare("W1", seed=SEED, scale="smoke", assignment=all_control(chain))
    b = prepare("W1", seed=SEED, scale="smoke", assignment=alternating(chain, treated_share=75))
    assert a.treated == ()
    assert len(b.treated) > 0

    # Every field except one. `PriceDecision.arm` is the *label* the decision was routed by —
    # `gold.decisions` carries it in the real system and the corpus would be lying if it did
    # not — and under W1 it is the only thing in the whole stream that the assignment touches.
    assert _fingerprint(a, without="arm") == _fingerprint(b, without="arm")

    # And that exclusion is not a loophole: with the label back in, the two streams differ, so
    # the test above is comparing something that had every chance to disagree.
    assert _fingerprint(a) != _fingerprint(b)


def test_a_partial_assignment_is_refused() -> None:
    """A store with no arm would quietly take the control path and shrink the experiment."""
    run = prepare("W6", seed=SEED, scale="smoke")
    partial = dict(run.assignment)
    partial.pop(run.chain.stores[0].store_id)
    broken = prepare("W6", seed=SEED, scale="smoke", assignment=partial)
    with pytest.raises(ValueError, match="no arm"):
        list(events(broken))


def test_the_aa_world_refuses_a_treatment_policy() -> None:
    """W1 with two different policies is not W1, and is refused rather than quietly run."""
    from corpus.world.policy import candidate, contract_ladder

    run = prepare("W1", seed=SEED, scale="smoke")
    ladder = contract_ladder()
    broken = type(run)(
        world=run.world,
        seed=run.seed,
        scale=run.scale,
        chain=run.chain,
        control=ladder,
        treatment=candidate(ladder),
        assignment=run.assignment,
    )
    with pytest.raises(ValueError, match="A/A world"):
        list(events(broken))
