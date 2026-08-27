"""Markdown policies, and the one place the world reads the system's contract.

`policy.py` is the seam `CLAUDE.md` allows: *"The only thing they share is the schema from
`contracts/`, never logic."* These tests hold both halves of that sentence — that the control
arm really is `ladder_policy@v1` as the contract declares it, and that nothing about how the
world uses it came from `holdout.core.ladder`.
"""

from __future__ import annotations

import pytest
import yaml
from corpus.world.policy import (
    LADDER_CONTRACT,
    LadderStep,
    MarkdownPolicy,
    candidate,
    contract_ladder,
    from_contract_document,
)


@pytest.fixture(scope="module")
def ladder() -> MarkdownPolicy:
    return contract_ladder()


def test_the_control_arm_is_the_contract(ladder: MarkdownPolicy) -> None:
    """Read against the YAML directly, so a compiler change cannot quietly alter the control.

    `CLAUDE.md`: *"the holdout does not mean nothing — it means the existing policy."* If this
    drifted, every uplift the project ever reported would be measured against a schedule the
    chain does not run, and nothing else in the repository would notice.
    """
    document = yaml.safe_load(LADDER_CONTRACT.read_text(encoding="utf-8"))
    assert ladder.policy_id == f"{document['id']}@v{document['version']}"
    assert ladder.marker == document["marker"]
    assert [(s.step, s.hours_to_expiry_at_most, s.depth_pct) for s in ladder.steps] == sorted(
        [(s["step"], s["hours_to_expiry_at_most"], s["depth_pct"]) for s in document["steps"]],
        key=lambda row: row[1],
        reverse=True,
    )


def test_the_marker_travels(ladder: MarkdownPolicy) -> None:
    """Doctrine rule 2 — a fallback is visible all the way to the end.

    The world does not enforce that; the system does. What the world must not do is drop the
    marker on the floor, which would make the rule untestable one layer down.
    """
    assert ladder.marker == "FALLBACK_LADDER"


def test_the_deepest_rung_is_the_one_closest_to_expiry(ladder: MarkdownPolicy) -> None:
    assert ladder.step_at(100.0) is None
    assert ladder.step_at(float(ladder.first_rung_hours)) is not None
    deepest = ladder.step_at(0.0)
    assert deepest is not None
    assert deepest.depth_pct == max(s.depth_pct for s in ladder.steps)


def test_a_price_above_every_rung_is_the_base_price(ladder: MarkdownPolicy) -> None:
    price, step = ladder.price_cents(299, 96.0)
    assert (price, step) == (299, 0)


def test_a_price_on_a_rung_is_the_base_price_less_that_rung(ladder: MarkdownPolicy) -> None:
    for rung in ladder.steps:
        price, step = ladder.price_cents(1000, float(rung.hours_to_expiry_at_most))
        assert step == rung.step
        assert price == 1000 - rung.depth_pct * 10


def test_the_world_rounds_a_price_its_own_way_and_says_so(ladder: MarkdownPolicy) -> None:
    """Half-up on the cent, which is deliberately not `holdout.core.money`'s rounding.

    The core rounds a *price* half-even and a *bound* away from what it forbids, for reasons
    that belong to the guardrail set. A till does not know about any of that. If the two ever
    have to agree on a number they must agree by computing it separately and matching — which
    is the whole architecture of claim 5 — and they cannot do that if one of them imported the
    other's arithmetic.
    """
    # 101 cents at 20% off is 80.8; a shop's till says 81.
    assert ladder.price_cents(101, 24.0)[0] == 81
    # 105 at 50% off is exactly 52.5. Half-up gives 53; half-even would give 52.
    assert ladder.price_cents(105, 6.0)[0] == 53


def test_a_price_never_falls_below_a_cent(ladder: MarkdownPolicy) -> None:
    assert ladder.price_cents(1, 0.0)[0] == 1


def test_the_candidate_is_the_same_rungs_a_quarter_shallower(ladder: MarkdownPolicy) -> None:
    treatment = candidate(ladder)
    assert treatment.policy_id != ladder.policy_id
    for control_step, treated_step in zip(ladder.steps, treatment.steps, strict=True):
        assert treated_step.hours_to_expiry_at_most == control_step.hours_to_expiry_at_most
        assert treated_step.depth_pct == round(control_step.depth_pct * 3 / 4)
        assert treated_step.depth_pct < control_step.depth_pct


def test_a_policy_whose_late_rung_is_shallower_is_refused() -> None:
    """A ladder that un-marks-down as expiry approaches is not a ladder.

    Refused at construction rather than applied and then wondered about: a policy is an input
    from outside this package — `from_contract_document` takes whatever a caller parsed — and
    the world has no way to tell a typo from an intention.
    """
    with pytest.raises(ValueError, match="may not be shallower"):
        MarkdownPolicy(
            policy_id="broken@v1",
            marker="X",
            steps=(LadderStep(1, 24, 40), LadderStep(2, 12, 20)),
        )


def test_a_policy_whose_rungs_do_not_approach_expiry_is_refused() -> None:
    with pytest.raises(ValueError, match="must deepen as expiry approaches"):
        MarkdownPolicy(
            policy_id="broken@v2",
            marker="X",
            steps=(LadderStep(1, 12, 20), LadderStep(2, 24, 40)),
        )


def test_a_policy_with_no_steps_is_refused() -> None:
    with pytest.raises(ValueError, match="no steps"):
        MarkdownPolicy(policy_id="empty@v1", marker="X", steps=())


def test_a_document_the_repository_never_committed_still_parses() -> None:
    """`from_contract_document` is pure, which is what makes the world testable off-contract.

    A world that could only be built from a file on disk would make every one of the tests
    above a test of that file, and there would be nowhere to exercise a schedule nobody
    committed.
    """
    policy = from_contract_document(
        {
            "id": "invented",
            "version": 9,
            "marker": "MARK",
            "steps": [
                {"step": 2, "hours_to_expiry_at_most": 4, "depth_pct": 60},
                {"step": 1, "hours_to_expiry_at_most": 20, "depth_pct": 10},
            ],
        }
    )
    assert policy.policy_id == "invented@v9"
    assert [s.hours_to_expiry_at_most for s in policy.steps] == [20, 4]
