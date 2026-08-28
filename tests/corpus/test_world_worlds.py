"""Each of the six worlds does the thing it is named after — measured, not asserted in prose.

`CLAUDE.md` lists six adversarial worlds and the correct behaviour in each. That list is a
claim about the **corpus**, and a world that quietly stopped exhibiting its pathology would
leave every downstream eval green while proving nothing: an interference check that never sees
interference passes, and so does one that was deleted.

So each test below constructs the situation deliberately — this pair of neighbours, this arm —
rather than hoping a default assignment produces it. `test_world_chain.py` already refuses a
scale with no neighbour pair in it, for the same reason.
"""

from __future__ import annotations

import statistics
from collections import Counter
from collections.abc import Sequence
from dataclasses import replace
from datetime import date

import pytest
from corpus.world import SEAL_FILENAME, Arm, Run, all_control, events, prepare
from corpus.world.events import EslAck, PosLine, ShelfDay
from corpus.world.policy import LadderStep, MarkdownPolicy
from corpus.world.seal import open_after_readout
from corpus.world.worlds import (
    BASELINE_ACK_FAILURE_PCT,
    INTERFERING_CLUSTERED_PCT,
    REALISTIC_CLUSTERED_PCT,
    W1,
    W2,
    W3,
    W4,
    W5,
    W6,
    WORLDS,
)

SEED = "worlds"


def _sold(run: Run, only_stores: Sequence[str] | None = None) -> dict[str, int]:
    out: Counter[str] = Counter()
    for event in events(run, only_stores=only_stores):
        if isinstance(event, ShelfDay):
            out[event.store_id] += event.sold_qty
    return dict(out)


def _one_pair(run: Run) -> tuple[str, str]:
    pairs = run.chain.neighbour_pairs
    assert pairs, "no neighbour pair at this scale — the interference world cannot interfere"
    return pairs[0]


def test_the_six_worlds_are_the_six() -> None:
    assert sorted(WORLDS) == ["W1", "W2", "W3", "W4", "W5", "W6"]
    assert [w.is_aa for w in (W1, W2, W3, W4, W5, W6)] == [True, False, False, False, False, False]


def test_every_world_produces_all_four_streams() -> None:
    """A world that emitted no acknowledgement would make exposure unmeasurable in silence."""
    for world_id in sorted(WORLDS):
        seen = Counter(
            type(e).__name__ for e in events(prepare(world_id, seed=SEED, scale="smoke"))
        )
        assert seen["PosLine"] > 0, world_id
        assert seen["EslAck"] > 0, world_id
        assert seen["ShelfDay"] > 0, world_id
        assert seen["PriceDecision"] > 0, world_id


def test_w1_injects_nothing_at_all() -> None:
    """The A/A world's treatment policy is its control policy, by construction."""
    run = prepare("W1", seed=SEED, scale="smoke")
    assert run.control.policy_id == run.treatment.policy_id
    assert run.control.steps == run.treatment.steps


@pytest.mark.parametrize("world_id", ["W2", "W3", "W4", "W5", "W6"])
def test_every_other_world_actually_intervenes(world_id: str) -> None:
    run = prepare(world_id, seed=SEED, scale="smoke")
    assert run.control.policy_id != run.treatment.policy_id
    assert run.control.steps != run.treatment.steps


def test_only_w2_declares_a_more_clustered_estate() -> None:
    """`clustered_pct` is a declaration about a world, and only one world needs it high.

    It is here rather than only in `test_world_chain.py` because the number is a claim about
    *which world*, not about the chain: a corpus where every world clustered like W2 would
    have thrown away most of its roster in five worlds that never needed interference at all,
    and one where W2 clustered like the rest would have no interference to detect.
    """
    assert W2.clustered_pct == INTERFERING_CLUSTERED_PCT
    assert {w.clustered_pct for w in (W1, W3, W4, W5, W6)} == {REALISTIC_CLUSTERED_PCT}
    assert INTERFERING_CLUSTERED_PCT > REALISTIC_CLUSTERED_PCT


def test_the_clustering_is_sealed_with_the_rest_of_the_injection(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """It is part of what was injected, so it goes in the seal like everything else.

    Not because it is secret — `worlds.py` states every rate in the open — but because a seal
    that recorded the spillover and not the estate the spillover happened on would describe
    half a world, and the harness opens it to explain a number rather than to discover one.
    """
    run = prepare("W2", seed=SEED, scale="smoke")
    for _ in events(run, seal_into=tmp_path):
        pass
    readout = tmp_path / "readout.json"
    readout.write_text("{}", encoding="utf-8")
    truth = open_after_readout(tmp_path / SEAL_FILENAME, readout)
    assert truth.injection["clustered_pct"] == INTERFERING_CLUSTERED_PCT


def test_w2_a_neighbours_arm_changes_a_stores_outcome() -> None:
    """Interference, at the unit it happens between. The whole of W2 is this one sentence.

    The comparison is the same store under two assignments that differ **only in its
    neighbour's arm**. Common random numbers make that a clean contrast: nothing else about
    the store changed, so whatever moved, moved because of another unit's assignment. That is
    the definition of the SUTVA violation and not an approximation of it — and it is what makes
    every arm mean in this world mean something other than what it says.
    """
    run = prepare("W2", seed=SEED, scale="smoke")
    neighbour, watched = _one_pair(run)
    isolated = all_control(run.chain)
    exposed = dict(isolated, **{neighbour: Arm.TREATMENT})

    alone = _sold(replace(run, assignment=isolated), only_stores=[watched])[watched]
    beside = _sold(replace(run, assignment=exposed), only_stores=[watched])[watched]
    assert beside != alone, (
        "the store's outcome did not move when its neighbour's arm did — W2 has stopped "
        "interfering, and a contamination check would have nothing to catch"
    )


def test_w2_the_trade_moves_toward_the_deeper_ladder_whichever_arm_that_is() -> None:
    """Driven from both directions, with a policy this test writes rather than one it is given.

    The first version of the generator hard-coded the direction — control loses to treatment —
    from the assumption that a candidate markdown policy cuts deeper. `policy.candidate` cuts
    *shallower*, for reasons its own docstring gives, so the assumption had been false since
    the day the candidate was chosen. A world whose interference pointed the wrong way still
    broke SUTVA and would still have been detected by everything downstream, which is exactly
    why nothing would have caught it.

    So the direction is not asserted against the rule the generator uses — that would be the
    implementation agreeing with itself. It is **driven**: the same neighbour is given a
    shallower ladder and then a deeper one, and the watched store has to move both ways. A
    hard-coded direction passes one half of this test and fails the other, whichever way it
    was wired.
    """
    run = prepare("W2", seed=SEED, scale="smoke")
    neighbour, watched = _one_pair(run)
    isolated = all_control(run.chain)
    exposed = dict(isolated, **{neighbour: Arm.TREATMENT})

    deeper = MarkdownPolicy(
        policy_id="ladder_policy@deeper-for-this-test",
        marker=run.control.marker,
        steps=tuple(
            LadderStep(step.step, step.hours_to_expiry_at_most, min(90, step.depth_pct + 15))
            for step in run.control.steps
        ),
    )
    shallower_total = sum(s.depth_pct for s in run.treatment.steps)
    control_total = sum(s.depth_pct for s in run.control.steps)
    assert shallower_total < control_total < sum(s.depth_pct for s in deeper.steps), (
        "the two candidates must straddle the control, or this test only pushes one way"
    )

    alone = _sold(replace(run, assignment=isolated), only_stores=[watched])[watched]
    beside_shallower = _sold(replace(run, assignment=exposed), only_stores=[watched])[watched]
    beside_deeper = _sold(
        replace(run, assignment=exposed, treatment=deeper), only_stores=[watched]
    )[watched]

    assert beside_shallower > alone, (
        f"the neighbour cut less deeply than this store did and its markdown trade did not "
        f"cross the road: {alone} units alone against {beside_shallower} beside"
    )
    assert beside_deeper < alone, (
        f"the neighbour cut more deeply than this store did and this store lost nothing to "
        f"it: {alone} units alone against {beside_deeper} beside"
    )


def test_w6_leaves_the_neighbour_alone() -> None:
    """The control: in the clean world the same manipulation changes nothing next door.

    Without this, the two tests above would pass on any world in which a treated neighbour's
    existence perturbed anything at all, including a bug that had nothing to do with W2.

    **W6 is given W2's clustering for this one comparison**, since T00E made the clustering a
    per-world declaration: at W6's own 15% a smoke-scale estate has no neighbour pair to
    manipulate, so there would be nothing to leave alone. Handing it W2's estate is the
    stronger control anyway — the geography is now held fixed and `spillover_pct` is the only
    thing that differs, where before the two worlds differed in nothing at all and the test
    could not have told which half it was measuring.
    """
    run = prepare(replace(W6, clustered_pct=INTERFERING_CLUSTERED_PCT), seed=SEED, scale="smoke")
    neighbour, watched = _one_pair(run)
    isolated = all_control(run.chain)
    exposed = dict(isolated, **{neighbour: Arm.TREATMENT})
    assert _sold(replace(run, assignment=exposed), only_stores=[watched]) == _sold(
        replace(run, assignment=isolated), only_stores=[watched]
    )


def _ack_failure_pct(world_id: str, arm_of_interest: Arm) -> float:
    run = prepare(world_id, seed=SEED, scale="smoke")
    wanted = [s for s, arm in run.assignment.items() if arm is arm_of_interest]
    failed = total = 0
    for event in events(run, only_stores=wanted):
        if isinstance(event, EslAck):
            total += 1
            failed += not event.accepted
    assert total > 200, "too few acknowledgements to say anything about a rate"
    return 100.0 * failed / total


def test_w3_exposure_fails_on_roughly_a_third_of_treated_units() -> None:
    """Assignment and exposure come apart, on the arm where coming apart dilutes the estimate."""
    assert W3.ack_failure_pct_treated == 30
    treated = _ack_failure_pct("W3", Arm.TREATMENT)
    assert 25.0 <= treated <= 35.0, treated


def test_w3_leaves_the_control_arm_at_the_ordinary_rate() -> None:
    """Labels fail everywhere; what W3 raises is the treated rate and nothing else.

    If the control arm failed at the same raised rate, the two arms would be equally
    unexposed, the dilution would cancel, and the world would be testing nothing.
    """
    control = _ack_failure_pct("W3", Arm.CONTROL)
    assert abs(control - BASELINE_ACK_FAILURE_PCT) < 2.5, control


def test_every_world_has_labels_that_sometimes_fail() -> None:
    """`CLAUDE.md`: "ESL acknowledgements that sometimes fail" — in every world, not just W3."""
    for world_id in sorted(WORLDS):
        run = prepare(world_id, seed=SEED, scale="rehearsal")
        failures = sum(1 for e in events(run) if isinstance(e, EslAck) and not e.accepted)
        assert failures > 0, f"{world_id} never lost an acknowledgement"


def _lift_by_half(world_id: str, seed: str) -> tuple[float, float]:
    """The treated stores' margin against **their own counterfactual**, first half and second.

    Paired against all-control rather than against the control arm, which is what makes this
    readable at all: common random numbers mean the only difference between the two runs is
    the policy, so the between-store variance that swamps a cross-arm comparison at this scale
    is not in the number.
    """
    run = prepare(world_id, seed=seed, scale="rehearsal")
    counterfactual = replace(run, assignment=all_control(run.chain))
    treated = list(run.treated)
    cut = run.scale.start_date.toordinal() + run.scale.days // 2

    def margin(which: Run) -> dict[str, float]:
        agg: Counter[str] = Counter()
        for event in events(which, only_stores=treated):
            if isinstance(event, PosLine):
                half = "early" if event.event_ts.date().toordinal() < cut else "late"
                agg[half] += event.line_total_cents
            elif isinstance(event, ShelfDay):
                half = (
                    "early" if date.fromisoformat(event.business_date).toordinal() < cut else "late"
                )
                agg[half] -= (event.sold_qty + event.wasted_qty) * event.unit_cost_cents
        return dict(agg)

    observed, base = margin(run), margin(counterfactual)
    return (
        100.0 * (observed["early"] / base["early"] - 1.0),
        100.0 * (observed["late"] / base["late"] - 1.0),
    )


@pytest.mark.parametrize("seed", ["worlds", "another-seed"])
def test_w4_the_effect_decays_and_w6_does_not(seed: str) -> None:
    """Novelty, measured as W4's advantage **over W6** in each half of the window.

    W4 is W6 plus a decaying boost, so the two worlds are the right pair to difference: what
    is left is the novelty and nothing else — not the underlying effect, not the season, not
    the store mix.

    What has to be true of the corpus is the sentence `CLAUDE.md` writes about the *system*:
    the first week must genuinely overstate the window. So the boost is present early, it is
    smaller late, and by the second half most of it is gone. If it were flat, a readout that
    extrapolated the first week would be right by accident and the world would be testing
    nothing.
    """
    w4_early, w4_late = _lift_by_half("W4", seed)
    w6_early, w6_late = _lift_by_half("W6", seed)
    early, late = w4_early - w6_early, w4_late - w6_late

    assert early > 0.0, (w4_early, w6_early)
    assert late < early, (early, late)
    assert late < 0.6 * early, (
        f"the novelty was still {late:.2f} points of the {early:.2f} it started at; "
        f"a half-life of {W4.novelty_half_life_days} days over "
        "half of an eight-week window should have taken most of it"
    )


def test_w5_baskets_are_heavy_tailed() -> None:
    """Variance far above what a power calculation would have assumed — and a fatter maximum.

    Both halves matter. A distribution with the same mean and a longer tail is what defeats a
    power calculation; a distribution that merely shifted up would be a different world.
    """
    assert W5.quantity_tail_alpha is not None and W5.quantity_tail_alpha < 2.0

    def quantities(world_id: str) -> list[int]:
        return [
            e.qty
            for e in events(prepare(world_id, seed=SEED, scale="smoke"))
            if isinstance(e, PosLine)
        ]

    heavy, ordinary = quantities("W5"), quantities("W6")
    assert statistics.variance(heavy) > 8 * statistics.variance(ordinary)
    assert max(heavy) > 4 * max(ordinary)


def test_w6_produces_a_real_difference_between_the_arms() -> None:
    """W6 matters as much as W1: a corpus in which the clean world has no effect would make
    the false-refusal rate meaningless, because there would be nothing to refuse."""
    run = prepare("W6", seed=SEED, scale="rehearsal")
    treated = set(run.treated)
    sold = _sold(run)
    per_store = {s: sold[s] for s in sold}
    t = statistics.mean(v for s, v in per_store.items() if s in treated)
    c = statistics.mean(v for s, v in per_store.items() if s not in treated)
    assert t != c
