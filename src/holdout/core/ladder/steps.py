"""The deterministic markdown ladder — the declared safe state of the fresh path.

Doctrine rule 1 — the safe state is asymmetric
----------------------------------------------
For an expiring product silence is not safe: the product is thrown away. So when the
freshness gate fails, when the model is unavailable, or when any input is stale, the
markdown path falls **here** rather than to no action. For a price increase silence *is*
safe, so the base-price path falls to no action and may never fall here. `quote()` refuses
a policy whose `decision_path` is anything but `markdown`, and `holdout.core.decision`
refuses to resolve `SafeState.LADDER` on the other path, so the crossing is closed at both
ends rather than in a comment.

Doctrine rule 2 — a fallback is visible all the way to the end
---------------------------------------------------------------
A `LadderQuote` carries the policy's `marker` and there is no way to make one without it:
the field is required, the object is frozen, and `ProposedPrice` refuses to accept a
ladder-sourced price with an empty marker. The marker travels onto the certificate, which
has no setter and no `replace`, so by the time a price reaches a label, a P&L row or an
experiment arm, dropping the marker means forging a certificate rather than forgetting a
field.

The ladder never refuses
------------------------
`contracts/policies/ladder_policy@v1.yaml` declares
`floor_behaviour.when_step_breaches_floor: clamp_to_floor`, and this module honours it: a
step whose price falls below the floor is quoted **at the floor**. Deciding that no legal
price sells the item is the guardrail set's job, and it is a refusal there — donation or
disposal, a correct output. A safe state that could itself refuse would fail exactly when
it is the only thing left standing.

The ladder is also the control arm
-----------------------------------
"Holdout does not mean nothing" — it means the *existing* policy. This is that policy, so
the same function computes the control arm of every fresh-markdown experiment. Comparing a
treatment against abandonment instead would inflate every uplift.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from holdout.contracts.model import Policy, PolicyStep
from holdout.core.decision import DecisionPath
from holdout.core.money import Money

MINUTES_PER_HOUR = 60


class LadderError(ValueError):
    """The ladder was asked something it is not the policy for."""


@dataclass(frozen=True, slots=True)
class LadderQuote:
    """A price from the schedule, and the marker that must follow it everywhere."""

    step: int
    depth_pct: Decimal
    price: Money
    marker: str
    clamped_to_floor: bool
    """True when the step's own price fell below the floor and the floor was quoted
    instead. Visible on purpose: a clamped ladder price is shallower than the schedule
    says, and an experiment that treated it as the schedule's price would be measuring
    something else."""

    def __post_init__(self) -> None:
        if not self.marker:
            raise LadderError(
                "a ladder quote carries the policy's marker. A fallback that looks like a "
                "model decision is worse than an outage, because it is silent and it "
                "teaches someone to trust it."
            )


def step_thresholds_minutes(policy: Policy) -> tuple[tuple[PolicyStep, int], ...]:
    """Each step with its trigger expressed in whole minutes, deepest last.

    Hours arrive from the contract as a number PyYAML has already made binary. It is turned
    into an exact `Decimal` from its text and then into whole minutes, and a threshold that
    is not a whole number of minutes is a build failure rather than something rounded
    quietly: a ladder that fires half a minute early on one machine and half a minute late
    on another is not deterministic, and the ladder's entire value is that it is.
    """
    out: list[tuple[PolicyStep, int]] = []
    for step in sorted(policy.steps, key=lambda s: s.step):
        hours = Decimal(str(step.hours_to_expiry_at_most))
        minutes = hours * MINUTES_PER_HOUR
        if minutes != minutes.to_integral_value():
            raise LadderError(
                f"step {step.step} triggers at {hours} hours, which is not a whole number "
                "of minutes. The ladder is the safe state and its answer must not depend "
                "on how a machine rounds."
            )
        out.append((step, int(minutes)))
    return tuple(out)


def applicable_step(minutes_to_expiry: int, policy: Policy) -> PolicyStep | None:
    """The deepest step whose trigger the product has already passed, or None.

    The rule, worked through on `ladder_policy@v1` — steps at 24h/20%, 12h/35%, 6h/50% and
    3h/70%:

    * 30 hours out, no step has triggered and the answer is None. The product is not on
      markdown yet, and that is not the same as a markdown of zero.
    * 20 hours out, only the 24-hour step has triggered: 20%.
    * 10 hours out, the 24-hour and 12-hour steps have both triggered and the deepest one
      wins: 35%. Taking the *first* match instead would leave a product two hours from
      expiry sitting at the shallowest step.
    * exactly 12 hours out, the 12-hour step triggers, because the contract's field is
      `hours_to_expiry_at_most` and 12 is at most 12.
    * past expiry, the deepest step still applies. An expired product is withdrawn rather
      than repriced, and withdrawal is a stock decision this function does not make — but
      it does not raise either, because a safe state that can fail is not one.
    """
    if policy.decision_path != DecisionPath.MARKDOWN.value:
        raise LadderError(
            f"the ladder is the markdown path's safe state; {policy.ref} declares "
            f"decision_path={policy.decision_path!r}. Falling back to a markdown schedule "
            "on another path would mark down a product nobody asked to mark down."
        )
    triggered = [
        step
        for step, threshold in step_thresholds_minutes(policy)
        if minutes_to_expiry <= threshold
    ]
    if not triggered:
        return None
    return max(triggered, key=lambda s: (Decimal(str(s.depth_pct)), s.step))


def quote(
    minutes_to_expiry: int,
    *,
    base_price: Money,
    policy: Policy,
    floor: Money | None = None,
) -> LadderQuote | None:
    """The ladder's price, or None when no step has triggered yet.

    `floor` is the envelope's lower bound where the caller has one. Passing it applies the
    contract's `clamp_to_floor` behaviour; leaving it out quotes the schedule's own price
    and lets the guardrail set have the argument. Either way the ladder itself never
    refuses.
    """
    step = applicable_step(minutes_to_expiry, policy)
    if step is None:
        return None
    if not policy.marker:
        raise LadderError(
            f"{policy.ref} is a fallback policy and declares no marker. Doctrine rule 2: a "
            "price produced by a fallback carries that marker to the label, the P&L and "
            "the experiment."
        )
    depth = Decimal(str(step.depth_pct))
    # `as_lower_bound` — rounded UP — and not `as_price`. Two reasons, and the second is
    # the one that was actually costing money.
    #
    # The argument money.py makes: a markdown price rounded *down* is a markdown *deeper*
    # than the schedule declares, and a schedule of maximum depths is itself a limit. So a
    # half-cent goes to the shallower side, exactly as a floor does.
    #
    # The bug it fixes: the envelope's `markdown_max_depth_pct` bound is a lower bound and
    # rounds up. Rounding the quote half-to-even put the ladder a cent *below* that bound
    # whenever the depth landed on a half-cent — at rung 4 of `ladder_policy@v1`, that is
    # every base price ending in five cents, one in five of them, at the rung that matters
    # most. The declared safe state of the primary decision path was producing a price the
    # guardrail set refused, which is the one thing doctrine rule 1 exists to prevent.
    # `tests/core/test_composition.py` runs every rung against every cent ending.
    scheduled = Money.as_lower_bound(Decimal(base_price.cents) - base_price.pct(depth))
    clamped = floor is not None and scheduled < floor
    return LadderQuote(
        step=step.step,
        depth_pct=depth,
        price=floor if (clamped and floor is not None) else scheduled,
        marker=policy.marker,
        clamped_to_floor=clamped,
    )
