"""Markdown policies, as plain data.

**This is the one thing the world shares with the system, and it is shared as data.**
`CLAUDE.md`: *"The only thing they share is the schema from `contracts/`, never logic."* The
control arm of a fresh-markdown experiment is `ladder_policy@v1` — *"the holdout does not mean
nothing, it means the existing policy"* — so a generator whose control arm were some other
schedule would be simulating a chain this system does not run, and every uplift measured
against it would be an uplift against a fiction.

What is **not** shared is any code. `from_contract_document` takes an already-parsed mapping
and returns frozen dataclasses; `src/holdout/core/ladder/` is never imported, never consulted
and never compared against. The two read the same table and each does its own arithmetic with
it — and that is exactly the arrangement the barrier exists to protect, because a shared
`depth_for()` would let a bug in it cancel out of every comparison.

`contract_ladder()` is the only function in this package that touches the filesystem, and the
only one that touches PyYAML. Everything downstream of it takes a `MarkdownPolicy` as an
argument.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
LADDER_CONTRACT = REPO_ROOT / "contracts" / "policies" / "ladder_policy@v1.yaml"
CANDIDATE_CONTRACT = REPO_ROOT / "contracts" / "policies" / "shallow_ladder_policy@v1.yaml"

#: What a price produced by the ladder carries, all the way to the label, the P&L and the
#: experiment — doctrine rule 2. Read from the contract, not written here.
_MARKER_FIELD = "marker"


@dataclass(frozen=True, slots=True)
class LadderStep:
    """One rung: from this many hours before expiry, take this much off the base price."""

    step: int
    hours_to_expiry_at_most: int
    depth_pct: int


@dataclass(frozen=True, slots=True)
class MarkdownPolicy:
    """A schedule of reductions keyed on hours remaining before expiry.

    It consults no model and no forecast, so it has exactly one correct answer for a given
    input — which is what makes it usable as a control arm at all, and what makes the
    *difference* between two of them the entire intervention.
    """

    policy_id: str
    marker: str
    steps: tuple[LadderStep, ...]

    def __post_init__(self) -> None:
        if not self.steps:
            raise ValueError("a markdown policy with no steps is not a policy")
        hours = [step.hours_to_expiry_at_most for step in self.steps]
        depths = [step.depth_pct for step in self.steps]
        if hours != sorted(hours, reverse=True):
            raise ValueError(f"{self.policy_id}: rungs must deepen as expiry approaches: {hours}")
        if depths != sorted(depths):
            raise ValueError(f"{self.policy_id}: a later rung may not be shallower: {depths}")

    def step_at(self, hours_to_expiry: float) -> LadderStep | None:
        """The deepest rung whose window this moment is inside, or `None` above them all."""
        chosen: LadderStep | None = None
        for step in self.steps:
            if hours_to_expiry <= step.hours_to_expiry_at_most:
                chosen = step
        return chosen

    @property
    def first_rung_hours(self) -> int:
        """When this policy starts marking down. W2's spillover is keyed on it."""
        return max(step.hours_to_expiry_at_most for step in self.steps)

    def price_cents(self, base_price_cents: int, hours_to_expiry: float) -> tuple[int, int]:
        """The shelf price this policy asks for, and the rung it came from (0 for none).

        Rounded half-up to the cent, which is the world's arithmetic and deliberately not the
        core's. `holdout.core.money` rounds a *price* half-even and a *bound* away from what
        it forbids, for reasons that belong to the guardrail set; a shop's own till does not
        know about any of that. If the two ever have to agree on a number, they must agree by
        computing it separately and matching — not by sharing the function that computes it.
        """
        step = self.step_at(hours_to_expiry)
        if step is None:
            return base_price_cents, 0
        kept = base_price_cents * (100 - step.depth_pct)
        return max(1, (kept + 50) // 100), step.step


def from_contract_document(document: Any) -> MarkdownPolicy:
    """A `MarkdownPolicy` from a parsed `contracts/policies/*.yaml`, and nothing else.

    Pure: it takes the mapping, not the path. The world is testable against a policy nobody
    committed, which is how `tests/corpus/test_world_policy.py` checks that a policy with a
    shallower late rung is refused rather than silently applied.
    """
    steps = tuple(
        LadderStep(
            step=int(raw["step"]),
            hours_to_expiry_at_most=int(raw["hours_to_expiry_at_most"]),
            depth_pct=int(raw["depth_pct"]),
        )
        for raw in document["steps"]
    )
    ordered = tuple(sorted(steps, key=lambda s: s.hours_to_expiry_at_most, reverse=True))
    return MarkdownPolicy(
        policy_id=f"{document['id']}@v{document['version']}",
        marker=str(document[_MARKER_FIELD]),
        steps=ordered,
    )


def contract_ladder(path: Path = LADDER_CONTRACT) -> MarkdownPolicy:
    """`ladder_policy@v1`, read as data.

    The only filesystem access and the only PyYAML import in `corpus/world/`. It is
    `yaml.safe_load` and a dictionary lookup — not `holdout.contracts.loader`, which validates
    against the schema, resolves effective windows and checks provenance. The world does not
    need any of that and must not have it: a corpus that ran the system's contract loader
    would inherit the system's opinion about which window is in force, and the world's job is
    to be a chain, not to agree.
    """
    import yaml

    return from_contract_document(yaml.safe_load(path.read_text(encoding="utf-8")))


def candidate(control: MarkdownPolicy, path: Path = CANDIDATE_CONTRACT) -> MarkdownPolicy:
    """The treatment arm: `shallow_ladder_policy@v1`, read as data.

    **Read from a contract since 2026-09-11, computed from the ladder before it.** This function
    used to take a quarter off every depth of `control` and name the result
    `ladder_policy@candidate` -- a policy ref that existed in this package and nowhere else, so
    the compiled design form's closed list did not contain it and the agent, asked twelve
    questions about interventions, declined all twelve for want of a treatment it could name.
    The A/A harness never noticed because it builds its form in Python and skips the schema. A
    treatment the estate's own experiment delivers, that no design may name, is two definitions
    of one thing, and the contract is the one that stays.

    `control` is still taken, for the one thing this function still checks: the candidate must
    be the ladder's rungs at the ladder's hours, or it is not the candidate. The depths' relation
    to the ladder's -- a quarter shallower -- is asserted by `tests/corpus/test_world_policy.py`
    against both contracts, so the two cannot drift apart without a red run.

    **Why shallower rather than deeper** is now the contract's own comment, kept in full there.
    The short form: a deeper ladder teaches shoppers a lower normal price, and what it loses at
    full price the rest of the week costs more than the waste it saves. The *magnitude* of the
    candidate's effect is written nowhere, including here, because it moved by a factor of four
    between seeds: there is only the effect in a given world, computed after the readout.
    """
    treatment = contract_ladder(path)
    if tuple(s.hours_to_expiry_at_most for s in treatment.steps) != tuple(
        s.hours_to_expiry_at_most for s in control.steps
    ):
        raise ValueError(
            f"{treatment.policy_id} does not share {control.policy_id}'s rungs; a candidate "
            "that moves the hours as well as the depths is two changes, and the experiment "
            "could not say which one it measured."
        )
    return treatment
