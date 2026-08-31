"""The envelope: five guardrails, resolved as of a decision time, evaluated as arithmetic.

What this module is for
-----------------------
`certify` in `holdout.core.guardrails.certificate` is the only way to obtain a
`CertifiedPrice`. This module is what it consults: a proposal in, an `Assessment` out —
the admissible price range with each bound attributed to the rule that produced it, what
may be announced on the label, whether the cost was fresh, and every guardrail that
refused.

The seam that keeps claim 1 honest
----------------------------------
Claim 1's declared trap is that *a planter reading the same contract as the detector is one
function agreeing with itself*. The defence is the shape of this module's public surface:

* `Envelope` and its five rule blocks are plain frozen dataclasses over `Money`, `Decimal`,
  `int`, `bool` and `frozenset`. Nothing in them refers to a contract, a file, a window or
  a date range. An attacker who has read a supermarket's actual published price list can
  build an `Envelope` out of the numbers *it* implies and drive `certify` with it, without
  importing anything private and without ever touching `contracts/`.
* `envelope_as_of` is the one function that projects *this repository's* contracts into
  that shape. It is a convenience for the production path, not the way in. Nothing in
  `evaluate` or `certify` can tell whether the envelope in front of it came from there.

If the only way to build an envelope were a helper that also built the proposal, the eval
would end up agreeing with itself, and claim 1 would be a tautology dressed as a test.

Nothing is defaulted
--------------------
Doctrine rule 3. `envelope_as_of` raises when a rule the envelope needs is absent from the
window in force; it never substitutes a plausible number. `evaluate` refuses with
`INPUT_NOT_AVAILABLE` when the *proposal* lacks an input a rule needs, rather than assuming
one. A certified price whose certificate asserts a check that never ran is worse than no
price at all, because it is indistinguishable from one that was actually checked.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, DecimalException
from enum import StrEnum
from typing import Protocol

from holdout.contracts.model import Guardrail, GuardrailRule, GuardrailWindow
from holdout.contracts.windows import resolve_as_of
from holdout.core.decision import DecisionKey, DecisionPath, PriceSource, SafeState, safe_state_for
from holdout.core.guardrails.benchmark import MarkupOnCost
from holdout.core.guardrails.codes import (
    GUARDRAIL_ORDER,
    PRECEDENCE,
    GuardrailId,
    RefusalCode,
)
from holdout.core.money import Money

#: The bases the 2026 and 2022 regimes state, and which this core knows how to compute.
#: A window whose instrument states none — `unspecified_in_the_instrument` in
#: `contracts/guardrails/regulated_basket.yaml` for 2021 — is refused rather than evaluated
#: with a neighbouring regime's arithmetic.
EVALUABLE_CAP_BASES = frozenset({"per_unit", "per_product_code"})


class EnvelopeError(ValueError):
    """The envelope could not be built, or was applied to a decision it does not govern.

    Distinct from a refusal on purpose. A refusal is a correct output about a price; this
    is a statement that the machinery itself is wrong — a missing rule, a decision routed
    to the wrong path — and it must stop the build or the run rather than become a number.
    """


class ProposalError(ValueError):
    """A proposal that is malformed rather than inadmissible.

    Also not a refusal. A price with no timezone on its decision time, or a ladder price
    with its fallback marker missing, is not a decision the envelope may judge and refuse —
    it is a caller that has not finished writing the proposal.
    """


class Freshness(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"


class AnnouncementBasis(StrEnum):
    """On what footing a reduction may be printed on the label."""

    NOT_ANNOUNCED = "not_announced"
    PERISHABLE_EXEMPTION = "perishable_exemption"
    PRIOR_PRICE = "prior_price"


# ------------------------------------------------------------------ the five rule blocks


@dataclass(frozen=True, slots=True)
class FloorRule:
    """`contracts/guardrails/floor.yaml`, resolved."""

    minimum_gross_margin_pct: Decimal
    minimum_absolute_price: Money
    cost_staleness_hours: int
    refuse_when_no_price_satisfies_every_guardrail: bool
    safe_state: SafeState

    def __post_init__(self) -> None:
        if not self.refuse_when_no_price_satisfies_every_guardrail:
            raise EnvelopeError(
                "floor.refuse_when_no_price_satisfies_every_guardrail is false, and this "
                "core has no other behaviour to offer. Forcing a price below the floor to "
                "avoid an empty answer is the failure the rule exists to prevent, and "
                "inventing a third option here would be doctrine rule 3 in reverse."
            )


@dataclass(frozen=True, slots=True)
class MaxDeltaRule:
    """`contracts/guardrails/max_delta.yaml`, resolved."""

    markdown_max_depth_pct: Decimal
    markdown_max_changes_per_sku_per_day: int
    base_price_max_weekly_increase_pct: Decimal
    base_price_max_weekly_decrease_pct: Decimal
    safe_state: SafeState


@dataclass(frozen=True, slots=True)
class FrozenCategoriesRule:
    """`contracts/guardrails/frozen_categories.yaml`, resolved.

    Not a tighter bound — a category the decision path does not enter at all.
    """

    category_ids: frozenset[str]
    safe_state: SafeState


@dataclass(frozen=True, slots=True)
class MarginCapRule:
    """`contracts/guardrails/regulated_basket.yaml`, resolved.

    A cap on margin is neither a floor nor a ceiling on price: it binds the difference
    between the cost and the price, so the same shelf price is legal or illegal depending
    on what the goods cost the retailer. It therefore has to be evaluated against the cost
    as it was known at decision time, like everything else here.

    What the basis does, and a declared limit
    -----------------------------------------
    `unspecified_in_the_instrument` is refused outright (`MARGIN_CAP_BASIS_UNEVALUABLE`).
    That is the load-bearing branch: `docs/REGULATORY.md` shows that ν. 4818/2021 never
    says what the margin is measured on, and code that borrowed the 2022 regime's per-unit
    arithmetic would keep returning a plausible number computed the wrong way, with nothing
    red anywhere.

    `per_unit` and `per_product_code` are both evaluated here as a bound on **this
    decision's own margin** against the supplied benchmark. For `per_unit` that is exactly
    what the instrument says. For `per_product_code` it is **stricter than the instrument
    requires**: the 2026 measure compares an aggregate over a product code against the 2025
    full-year average, and a single price above the benchmark could still be lawful once
    averaged down. Evaluating it per decision errs toward refusal.

    That is a deliberate choice and not an oversight, and it is recorded in three places —
    here, in `contracts/guardrails/regulated_basket.yaml` beside the value, and in
    `docs/REGULATORY.md` — because a reader of any one of them would otherwise take it for
    compliance. The aggregate the instrument actually names is not available at decision
    time: it needs the code's realised margin for the period, which is a gold table and not
    an argument to a pure function. When that arrives, this becomes a different bound, and
    the `basis` field is where the branch will go.

    Which denominator the benchmark is in
    -------------------------------------
    `benchmark` names the quantity; it does not say what that quantity is a fraction of, and
    the two candidates differ by a fifth. The bound below is computed from
    `ProposedPrice.benchmark_markup_on_cost`, a `MarkupOnCost` — see
    `holdout.core.guardrails.benchmark` for why that is a type and not a comment, and
    `docs/DECISIONS.md` for the half of the ambiguity that lives in the contract and is
    deferred to the next window it opens.

    What is reachable today
    -----------------------
    `floor`, `max_delta` and `frozen_categories` all open on 2025-01-01, so `envelope_as_of`
    cannot build an envelope for any earlier date. The 2021 and 2022 windows of this
    guardrail are therefore **not reachable through the contract path**: the
    `unspecified_in_the_instrument` refusal and the `per_unit` basis are live code guarding
    a *future* instrument that again states no basis, not a demonstrated property of the
    2021 window. They are exercised against hand-built envelopes in the tests, which is the
    honest way to say it — a branch tested only by the corpus that cannot reach it would be
    a branch nobody has run.
    """

    in_force: bool
    basis: str | None
    benchmark: str | None
    regulated_category_ids: frozenset[str]
    safe_state: SafeState

    def binds(self, category_id: str) -> bool:
        return self.in_force and category_id in self.regulated_category_ids

    @property
    def is_evaluable(self) -> bool:
        return self.basis in EVALUABLE_CAP_BASES


@dataclass(frozen=True, slots=True)
class PriorPriceRule:
    """`contracts/guardrails/prior_price.yaml`, resolved.

    `perishable_exemption` is the single provision the fresh-markdown path depends on.
    Without it every automatic markdown is an announcement that must carry a thirty-day
    lowest price, and the primary decision path cannot actuate itself at all.
    """

    perishable_exemption: bool
    lookback_days: int
    progressive_reduction_window_days: int | None
    safe_state: SafeState


@dataclass(frozen=True, slots=True)
class Envelope:
    """The five guardrails as they stood on `decided_on`, for one decision path.

    One path, not both. `envelope_as_of` reads only the safe state declared for the path it
    was asked for, so a markdown envelope does not contain the base-price answer anywhere.

    Doctrine rule 1 is checked **here**, in `__post_init__`, and not only on the way in from
    the contracts. This constructor is the door the independent-corpus seam requires an
    external eval to use, so a rule enforced only in `envelope_as_of` would be a rule that
    holds on the production path and nowhere else — and it is precisely the hand-built
    envelope, written by someone who has not read this file, that would get it wrong.
    """

    decided_on: date
    path: DecisionPath
    floor: FloorRule
    max_delta: MaxDeltaRule
    frozen_categories: FrozenCategoriesRule
    margin_cap: MarginCapRule
    prior_price: PriorPriceRule

    def __post_init__(self) -> None:
        for name in ("floor", "max_delta", "frozen_categories", "margin_cap", "prior_price"):
            block = getattr(self, name)
            # Raises `SafeStateError` where a path would inherit the other's answer. The
            # return value is discarded: what is wanted is the refusal, not the value.
            safe_state_for(self.path, block.safe_state.value)


# ------------------------------------------------------------------ the proposal


@dataclass(frozen=True, slots=True)
class ProposedPrice:
    """A price somebody wants to put on a shelf, and everything the envelope needs to judge it.

    **No field on this class carries a default that stands in for a fact.** Every field that
    describes the world is either required or `X | None = None`, where `None` means *not
    supplied* and every rule that needs it refuses with `INPUT_NOT_AVAILABLE` rather than
    assuming. Doctrine rule 3, and the reason it is written this way is that a default
    always falls in the permissive direction: a `changes_dispatched_today` that defaulted to
    zero would mean the daily budget guardrail could never fire, and nothing would be red.

    The one field with a default is `marker`, which is not a fact about the world but an
    invariant of `source`: a ladder price carries the policy's marker and nothing else may.
    """

    key: DecisionKey
    decided_at: datetime
    price: Money
    base_price: Money
    category_id: str
    source: PriceSource
    is_perishable: bool
    announced_as_reduction: bool
    unit_cost: Money | None = None
    cost_known_at: datetime | None = None
    marker: str | None = None
    changes_dispatched_today: int | None = None
    prior_price: Money | None = None
    benchmark_markup_on_cost: MarkupOnCost | None = None
    week_opening_price: Money | None = None

    def __post_init__(self) -> None:
        if self.decided_at.tzinfo is None:
            raise ProposalError(
                "decided_at must carry a timezone. A naive timestamp compared against a "
                "cost's arrival time is an arithmetic that changes answer twice a year."
            )
        if self.cost_known_at is not None and self.cost_known_at.tzinfo is None:
            raise ProposalError("cost_known_at must carry a timezone, for the same reason")
        if self.changes_dispatched_today is not None and self.changes_dispatched_today < 0:
            raise ProposalError("changes_dispatched_today counts dispatches; it is never negative")
        if not self.category_id:
            raise ProposalError("a proposal names the category it is in; nothing is inferred")
        # The denominator, refused at runtime and not only by the annotation. A gross margin
        # published over the *selling price* and a mark-up over the *cost* are the same
        # constraint and different numbers, and the mistake this refuses is the shape the
        # ambiguity actually arrives in: a bare percentage, taken off an instrument that
        # defines it over the price, handed to a field that will multiply the cost by it.
        # mypy sees it where mypy runs; this sees it everywhere else.
        if self.benchmark_markup_on_cost is not None and not isinstance(
            self.benchmark_markup_on_cost, MarkupOnCost
        ):
            raise ProposalError(
                "benchmark_markup_on_cost is a MarkupOnCost — a percentage of the cost, "
                f"not {type(self.benchmark_markup_on_cost).__name__}. A figure published "
                "as a margin over the selling price is a MarginOnPrice, and "
                "MarginOnPrice.as_markup_on_cost() is the only route between them: "
                "16.81% of the price is 20.21% of the cost, and applying the first where "
                "the second was meant is a silently stricter cap."
            )
        # Doctrine rule 2, made structural at the point the marker enters the system. A
        # ladder price without its marker would be indistinguishable from a model decision
        # downstream, and a model decision wearing a fallback marker would make the
        # decision monitor's amber band a lie in the other direction.
        if self.source is PriceSource.LADDER and not self.marker:
            raise ProposalError(
                "a price produced by the ladder carries the policy's marker. A fallback "
                "that looks like a model decision is worse than an outage, because it is "
                "silent and it teaches someone to trust it."
            )
        if self.source is not PriceSource.LADDER and self.marker:
            raise ProposalError(
                f"only a fallback carries a marker; {self.source.value} must not. A marker "
                "on a model decision inflates the fallback rate and hides a real outage."
            )


# ------------------------------------------------------------------ the assessment


@dataclass(frozen=True, slots=True)
class Bound:
    """One end of the admissible range, attributed to the rule that produced it."""

    amount: Money
    guardrail: GuardrailId
    rule_id: str
    code: RefusalCode
    """What the refusal is called when the price falls outside this bound."""
    why: str

    @property
    def tie_break(self) -> tuple[int, str]:
        """Everything but the amount, so two bounds at the same amount still order."""
        return (GUARDRAIL_ORDER.index(self.guardrail), self.rule_id)


@dataclass(frozen=True, slots=True)
class PriceBounds:
    """Every bound that applies, and the two that actually bind.

    Both ends are kept as lists rather than collapsed on the way in, because claim 1's
    evidence is *which guardrails fired* and a collapsed bound has already thrown that away.
    """

    lower: tuple[Bound, ...] = ()
    upper: tuple[Bound, ...] = ()

    @property
    def minimum(self) -> Bound | None:
        """The highest lower bound. Ties break on a declared guardrail order and then on
        the rule id, never on whichever happened to be appended first."""
        if not self.lower:
            return None
        return min(self.lower, key=lambda b: (-b.amount.cents, b.tie_break))

    @property
    def maximum(self) -> Bound | None:
        """The lowest upper bound, broken by the same declared order."""
        if not self.upper:
            return None
        return min(self.upper, key=lambda b: (b.amount.cents, b.tie_break))

    @property
    def is_empty(self) -> bool:
        """No price satisfies every guardrail at once."""
        low, high = self.minimum, self.maximum
        return low is not None and high is not None and low.amount > high.amount

    def contains(self, price: Money) -> bool:
        low, high = self.minimum, self.maximum
        return (low is None or price >= low.amount) and (high is None or price <= high.amount)


@dataclass(frozen=True, slots=True)
class Announcement:
    """What may be printed on the label about a reduction, and on what footing."""

    basis: AnnouncementBasis
    prior_price: Money | None = None
    lookback_days: int | None = None

    @property
    def is_reduction(self) -> bool:
        return self.basis is not AnnouncementBasis.NOT_ANNOUNCED


@dataclass(frozen=True, slots=True)
class GuardrailRefusal:
    """One guardrail's answer of no, named precisely enough to count and to fix."""

    code: RefusalCode
    guardrail: GuardrailId
    rule_id: str
    detail: str
    safe_state: SafeState


@dataclass(frozen=True, slots=True)
class Assessment:
    """Everything the envelope has to say about one proposal.

    Public and returned whole, refusals included, so that an eval driving the gates from an
    independent corpus can count which guardrails fired without reaching into anything
    private.
    """

    key: DecisionKey
    bounds: PriceBounds
    cost_freshness: Freshness
    announcement: Announcement | None
    refusals: tuple[GuardrailRefusal, ...]

    @property
    def passed(self) -> bool:
        return not self.refusals

    @property
    def leading(self) -> GuardrailRefusal | None:
        """The refusal that leads, by declared precedence rather than by evaluation order."""
        if not self.refusals:
            return None
        return min(self.refusals, key=lambda r: PRECEDENCE.index(r.code))

    @property
    def fired(self) -> tuple[GuardrailId, ...]:
        """Which guardrails refused, in the declared order. Claim 1's countable evidence."""
        seen = {r.guardrail for r in self.refusals}
        return tuple(g for g in GUARDRAIL_ORDER if g in seen)


# ------------------------------------------------------------------ the evaluation


def evaluate(proposal: ProposedPrice, envelope: Envelope) -> Assessment:
    """Judge a proposal against an envelope. Pure arithmetic; no clock, no contract, no I/O.

    Every guardrail is evaluated even after one has already refused, because a readout that
    counts guardrail firings needs all of them and because stopping at the first refusal
    would make the count depend on the order they happen to be written in.
    """
    if proposal.key.path is not envelope.path:
        raise EnvelopeError(
            f"a {proposal.key.path.value} decision was handed a {envelope.path.value} "
            "envelope. The two paths bound differently and neither may inherit the "
            "other's answer, so this is a wiring error rather than a refusal."
        )

    refusals: list[GuardrailRefusal] = []
    lower: list[Bound] = []
    upper: list[Bound] = []

    def refuse(
        code: RefusalCode, guardrail: GuardrailId, rule_id: str, detail: str, safe: SafeState
    ) -> None:
        refusals.append(
            GuardrailRefusal(
                code=code, guardrail=guardrail, rule_id=rule_id, detail=detail, safe_state=safe
            )
        )

    # --- frozen categories: the path does not enter at all -------------------------
    if proposal.category_id in envelope.frozen_categories.category_ids:
        refuse(
            RefusalCode.CATEGORY_FROZEN,
            GuardrailId.FROZEN_CATEGORIES,
            "frozen_category_ids",
            f"category {proposal.category_id!r} is frozen in the window in force on "
            f"{envelope.decided_on}. No automated price decision is taken in it.",
            envelope.frozen_categories.safe_state,
        )

    # --- the cost, and what depends on it ------------------------------------------
    freshness = _freshness(proposal, envelope.floor)
    if freshness is Freshness.UNKNOWN:
        refuse(
            RefusalCode.INPUT_NOT_AVAILABLE,
            GuardrailId.FLOOR,
            "cost_staleness_hours",
            "no unit cost with a known arrival time. Every bound in the envelope is "
            "computed from the cost as it was known at decision time, and a default cost "
            "is a lie with a plausible shape.",
            envelope.floor.safe_state,
        )
    elif freshness is Freshness.STALE and proposal.source is not PriceSource.LADDER:
        refuse(
            RefusalCode.COST_STALE,
            GuardrailId.FLOOR,
            "cost_staleness_hours",
            f"the unit cost was known at {proposal.cost_known_at} and the decision is "
            f"taken at {proposal.decided_at}, more than "
            f"{envelope.floor.cost_staleness_hours}h later. A floor computed from a stale "
            "cost is a floor in the wrong place, and every price above it still passes "
            "every other check. Only the ladder — the declared safe state of a path where "
            "silence throws the product away — may proceed on a stale cost, marked.",
            envelope.floor.safe_state,
        )

    lower.append(
        Bound(
            amount=envelope.floor.minimum_absolute_price,
            guardrail=GuardrailId.FLOOR,
            rule_id="minimum_absolute_price_eur",
            code=RefusalCode.BELOW_ABSOLUTE_FLOOR,
            why="the absolute minimum a certified decision may carry, whatever the cost says",
        )
    )

    cost = proposal.unit_cost
    if cost is not None:
        lower.append(
            Bound(
                amount=Money.as_lower_bound(
                    Decimal(cost.cents) + cost.pct(envelope.floor.minimum_gross_margin_pct)
                ),
                guardrail=GuardrailId.FLOOR,
                rule_id="minimum_gross_margin_pct",
                code=RefusalCode.BELOW_MARGIN_FLOOR,
                why=(
                    f"cost {cost} plus the declared minimum gross margin of "
                    f"{envelope.floor.minimum_gross_margin_pct}% of cost"
                ),
            )
        )

    # --- how far the price may move ------------------------------------------------
    if envelope.path is DecisionPath.MARKDOWN:
        depth = envelope.max_delta.markdown_max_depth_pct
        lower.append(
            Bound(
                amount=Money.as_lower_bound(
                    Decimal(proposal.base_price.cents) - proposal.base_price.pct(depth)
                ),
                guardrail=GuardrailId.MAX_DELTA,
                rule_id="markdown_max_depth_pct",
                code=RefusalCode.MARKDOWN_EXCEEDS_MAX_DEPTH,
                why=f"at most {depth}% below the shelf base price of {proposal.base_price}",
            )
        )
        budget = envelope.max_delta.markdown_max_changes_per_sku_per_day
        if proposal.changes_dispatched_today is None:
            refuse(
                RefusalCode.INPUT_NOT_AVAILABLE,
                GuardrailId.MAX_DELTA,
                "markdown_max_changes_per_sku_per_day",
                "how many price changes have already been dispatched for this SKU in this "
                "store today is a fact held in the operational store, and it was not "
                "supplied. Reading it as zero would mean this guardrail could never refuse "
                "anything, which is worse than not having it.",
                envelope.max_delta.safe_state,
            )
        elif proposal.changes_dispatched_today >= budget:
            refuse(
                RefusalCode.DAILY_CHANGE_BUDGET_EXHAUSTED,
                GuardrailId.MAX_DELTA,
                "markdown_max_changes_per_sku_per_day",
                f"{proposal.changes_dispatched_today} price changes have already been "
                f"dispatched for this SKU in this store today, and the bound is {budget}. "
                "A decision is idempotent per (sku_id, store_id, ladder_step), so a re-run "
                "never contributes to this count.",
                envelope.max_delta.safe_state,
            )
    else:
        opening = proposal.week_opening_price
        if opening is None:
            refuse(
                RefusalCode.INPUT_NOT_AVAILABLE,
                GuardrailId.MAX_DELTA,
                "base_price_max_weekly_increase_pct",
                "a base-price move is measured against the price in force at the start of "
                "the pricing week, and no such price was supplied.",
                envelope.max_delta.safe_state,
            )
        else:
            rise = envelope.max_delta.base_price_max_weekly_increase_pct
            fall = envelope.max_delta.base_price_max_weekly_decrease_pct
            upper.append(
                Bound(
                    amount=Money.as_upper_bound(Decimal(opening.cents) + opening.pct(rise)),
                    guardrail=GuardrailId.MAX_DELTA,
                    rule_id="base_price_max_weekly_increase_pct",
                    code=RefusalCode.BASE_PRICE_MOVE_EXCEEDS_WEEKLY_LIMIT,
                    why=f"at most {rise}% above the week's opening price of {opening}",
                )
            )
            lower.append(
                Bound(
                    amount=Money.as_lower_bound(Decimal(opening.cents) - opening.pct(fall)),
                    guardrail=GuardrailId.MAX_DELTA,
                    rule_id="base_price_max_weekly_decrease_pct",
                    code=RefusalCode.BASE_PRICE_MOVE_EXCEEDS_WEEKLY_LIMIT,
                    why=f"at most {fall}% below the week's opening price of {opening}",
                )
            )

    # --- the regulated basket ------------------------------------------------------
    cap = envelope.margin_cap
    if cap.binds(proposal.category_id):
        if not cap.is_evaluable:
            refuse(
                RefusalCode.MARGIN_CAP_BASIS_UNEVALUABLE,
                GuardrailId.REGULATED_BASKET,
                "cap_basis",
                f"a cap is in force in the window governing {envelope.decided_on} and its "
                f"basis is {cap.basis!r}, which states nothing this core can compute. "
                "Borrowing the arithmetic of the regime before or after would produce a "
                "number that looks right and answers a different question.",
                cap.safe_state,
            )
        elif cost is None or proposal.benchmark_markup_on_cost is None:
            refuse(
                RefusalCode.INPUT_NOT_AVAILABLE,
                GuardrailId.REGULATED_BASKET,
                "cap_benchmark",
                f"the cap is benchmarked on {cap.benchmark!r} and needs both the unit cost "
                "as known at decision time and the benchmark margin for this product. One "
                "of them was not supplied and neither is invented.",
                cap.safe_state,
            )
        else:
            upper.append(
                Bound(
                    amount=Money.as_upper_bound(
                        Decimal(cost.cents) + cost.pct(proposal.benchmark_markup_on_cost.pct)
                    ),
                    guardrail=GuardrailId.REGULATED_BASKET,
                    rule_id="cap_benchmark",
                    code=RefusalCode.MARGIN_CAP_EXCEEDED,
                    why=(
                        f"cost {cost} plus a benchmark mark-up of "
                        f"{proposal.benchmark_markup_on_cost} ({cap.benchmark}, "
                        f"basis {cap.basis})"
                    ),
                )
            )

    # --- the bounds, and whether the price is inside them --------------------------
    bounds = PriceBounds(lower=tuple(lower), upper=tuple(upper))
    low, high = bounds.minimum, bounds.maximum
    if low is not None and high is not None and low.amount > high.amount:
        refuse(
            RefusalCode.NO_PRICE_SATISFIES_EVERY_GUARDRAIL,
            low.guardrail,
            low.rule_id,
            f"the floor of {low.amount} ({low.guardrail.value}/{low.rule_id}) is above the "
            f"ceiling of {high.amount} ({high.guardrail.value}/{high.rule_id}), so no price "
            "satisfies every guardrail at once. Donation or disposal is the correct output.",
            envelope.floor.safe_state,
        )
    else:
        for bound in bounds.lower:
            if proposal.price < bound.amount:
                refuse(
                    bound.code,
                    bound.guardrail,
                    bound.rule_id,
                    f"{proposal.price} is below {bound.amount} — {bound.why}.",
                    _safe_state_of(envelope, bound.guardrail),
                )
        for bound in bounds.upper:
            if proposal.price > bound.amount:
                refuse(
                    bound.code,
                    bound.guardrail,
                    bound.rule_id,
                    f"{proposal.price} is above {bound.amount} — {bound.why}.",
                    _safe_state_of(envelope, bound.guardrail),
                )

    # --- what may be said on the label ---------------------------------------------
    announcement = _announcement(proposal, envelope, refuse)

    return Assessment(
        key=proposal.key,
        bounds=bounds,
        cost_freshness=freshness,
        announcement=announcement,
        refusals=tuple(refusals),
    )


def _safe_state_of(envelope: Envelope, guardrail: GuardrailId) -> SafeState:
    return {
        GuardrailId.FLOOR: envelope.floor.safe_state,
        GuardrailId.MAX_DELTA: envelope.max_delta.safe_state,
        GuardrailId.FROZEN_CATEGORIES: envelope.frozen_categories.safe_state,
        GuardrailId.REGULATED_BASKET: envelope.margin_cap.safe_state,
        GuardrailId.PRIOR_PRICE: envelope.prior_price.safe_state,
    }[guardrail]


def _freshness(proposal: ProposedPrice, floor: FloorRule) -> Freshness:
    if proposal.unit_cost is None or proposal.cost_known_at is None:
        return Freshness.UNKNOWN
    age_seconds = (proposal.decided_at - proposal.cost_known_at).total_seconds()
    return Freshness.STALE if age_seconds > floor.cost_staleness_hours * 3600 else Freshness.FRESH


class _Refuse(Protocol):
    """The shape of the closure `evaluate` hands to `_announcement`."""

    def __call__(
        self,
        code: RefusalCode,
        guardrail: GuardrailId,
        rule_id: str,
        detail: str,
        safe: SafeState,
    ) -> None: ...  # pragma: no cover


def _announcement(
    proposal: ProposedPrice, envelope: Envelope, refuse: _Refuse
) -> Announcement | None:
    """Whether a reduction may be announced, and against which prior price.

    The perishable exemption is the branch the whole fresh path stands on, and it is a
    genuinely different rule rather than a looser version of the same one: inside it there
    is no prior price to state, so nothing is compared and nothing can be wrong about the
    comparison.
    """
    if not proposal.announced_as_reduction:
        return Announcement(basis=AnnouncementBasis.NOT_ANNOUNCED)

    if proposal.is_perishable and envelope.prior_price.perishable_exemption:
        return Announcement(basis=AnnouncementBasis.PERISHABLE_EXEMPTION)

    prior = proposal.prior_price
    if prior is None:
        refuse(
            RefusalCode.PRIOR_PRICE_NOT_ESTABLISHED,
            GuardrailId.PRIOR_PRICE,
            "prior_price_lookback_days",
            "the decision announces a reduction and carries no prior price. The prior "
            f"price is the lowest actually applied over {envelope.prior_price.lookback_days} "
            "days, and it is evidence rather than an inference.",
            envelope.prior_price.safe_state,
        )
        return None
    if proposal.price >= prior:
        refuse(
            RefusalCode.PRIOR_PRICE_NOT_ESTABLISHED,
            GuardrailId.PRIOR_PRICE,
            "prior_price_lookback_days",
            f"{proposal.price} is not below the prior price of {prior}, so there is no "
            "reduction to announce. A reduction announced against a price that was never "
            "higher is the practice the rule exists to stop.",
            envelope.prior_price.safe_state,
        )
        return None
    return Announcement(
        basis=AnnouncementBasis.PRIOR_PRICE,
        prior_price=prior,
        lookback_days=envelope.prior_price.lookback_days,
    )


# ------------------------------------------------- projecting this repository's contracts


def envelope_as_of(guardrails: Sequence[Guardrail], *, on: date, path: DecisionPath) -> Envelope:
    """The five contracts, resolved to the window in force on `on`, for one path.

    A convenience for the production path and not the way in — see the module docstring.
    Everything it can fail on, it fails on loudly: a guardrail missing from the set, a
    guardrail that does not govern this path, a date before a timeline opens, a rule absent
    from the window in force. None of those has a default.
    """
    by_id = {g.id: g for g in guardrails}
    missing = {g.value for g in GuardrailId} - set(by_id)
    if missing:
        raise EnvelopeError(
            f"the envelope is the five guardrails and {sorted(missing)} are absent. A "
            "partial envelope certifies prices against checks that were never made."
        )

    def block(guardrail_id: GuardrailId) -> tuple[GuardrailWindow, SafeState]:
        guardrail = by_id[guardrail_id.value]
        if path.value not in guardrail.applies_to:
            raise EnvelopeError(
                f"guardrail {guardrail_id.value!r} declares applies_to="
                f"{list(guardrail.applies_to)} and does not govern the {path.value} path."
            )
        window = resolve_as_of(guardrail.windows, on)
        if window is None:
            raise EnvelopeError(
                f"guardrail {guardrail_id.value!r} has no window in force on {on}; its "
                "timeline opens later. A decision cannot be judged by a rule that did not "
                "exist yet, and assuming the earliest window would be inventing one."
            )
        declared = guardrail.safe_state.get(path.value)
        if not declared:
            raise EnvelopeError(
                f"guardrail {guardrail_id.value!r} declares no safe state for the "
                f"{path.value} path. Doctrine rule 1: the safe state is asymmetric and "
                "declared per path, so there is nothing to fall back to here."
            )
        return window, safe_state_for(path, declared)

    floor_window, floor_safe = block(GuardrailId.FLOOR)
    delta_window, delta_safe = block(GuardrailId.MAX_DELTA)
    frozen_window, frozen_safe = block(GuardrailId.FROZEN_CATEGORIES)
    basket_window, basket_safe = block(GuardrailId.REGULATED_BASKET)
    prior_window, prior_safe = block(GuardrailId.PRIOR_PRICE)

    cap_in_force = _bool(basket_window, GuardrailId.REGULATED_BASKET, "cap_in_force")

    return Envelope(
        decided_on=on,
        path=path,
        floor=FloorRule(
            minimum_gross_margin_pct=_decimal(
                floor_window, GuardrailId.FLOOR, "minimum_gross_margin_pct"
            ),
            minimum_absolute_price=_money(
                floor_window, GuardrailId.FLOOR, "minimum_absolute_price_eur"
            ),
            cost_staleness_hours=_int(floor_window, GuardrailId.FLOOR, "cost_staleness_hours"),
            refuse_when_no_price_satisfies_every_guardrail=_bool(
                floor_window,
                GuardrailId.FLOOR,
                "refuse_when_no_price_satisfies_every_guardrail",
            ),
            safe_state=floor_safe,
        ),
        max_delta=MaxDeltaRule(
            markdown_max_depth_pct=_decimal(
                delta_window, GuardrailId.MAX_DELTA, "markdown_max_depth_pct"
            ),
            markdown_max_changes_per_sku_per_day=_int(
                delta_window, GuardrailId.MAX_DELTA, "markdown_max_changes_per_sku_per_day"
            ),
            base_price_max_weekly_increase_pct=_decimal(
                delta_window, GuardrailId.MAX_DELTA, "base_price_max_weekly_increase_pct"
            ),
            base_price_max_weekly_decrease_pct=_decimal(
                delta_window, GuardrailId.MAX_DELTA, "base_price_max_weekly_decrease_pct"
            ),
            safe_state=delta_safe,
        ),
        frozen_categories=FrozenCategoriesRule(
            category_ids=_id_set(
                frozen_window, GuardrailId.FROZEN_CATEGORIES, "frozen_category_ids"
            ),
            safe_state=frozen_safe,
        ),
        margin_cap=MarginCapRule(
            in_force=cap_in_force,
            basis=(
                _text(basket_window, GuardrailId.REGULATED_BASKET, "cap_basis")
                if cap_in_force
                else None
            ),
            benchmark=(
                _text(basket_window, GuardrailId.REGULATED_BASKET, "cap_benchmark")
                if cap_in_force
                else None
            ),
            regulated_category_ids=(
                _id_set(basket_window, GuardrailId.REGULATED_BASKET, "regulated_category_ids")
                if cap_in_force
                else frozenset()
            ),
            safe_state=basket_safe,
        ),
        prior_price=PriorPriceRule(
            perishable_exemption=_bool(
                prior_window, GuardrailId.PRIOR_PRICE, "perishable_exemption"
            ),
            lookback_days=_int(prior_window, GuardrailId.PRIOR_PRICE, "prior_price_lookback_days"),
            progressive_reduction_window_days=_optional_int(
                prior_window, "progressive_reduction_window_days"
            ),
            safe_state=prior_safe,
        ),
    )


# ------------------------------------------------------------------ reading a rule value


@dataclass(frozen=True, slots=True)
class Renaming:
    """What a rule was called before `since`, and the date the canonical name took over.

    `previously` is **every** spelling this rule has ever had, oldest included — not the one
    the canonical name directly replaced. A second rename that lists only its predecessor
    leaves the oldest window unresolvable, and that failure arrives on a historical decision
    rather than at the moment of the edit, which is the worst place for it to appear.
    """

    since: date
    previously: tuple[str, ...]


#: Rules whose **id** changed when a window closed, canonical spelling to what it was called
#: before, **and from when**.
#:
#: A window is read in its own vocabulary. Contract rule 1 says no version is ever deleted, so
#: `floor.yaml`'s closed window keeps `refuse_when_no_legal_price_sells` forever — and a decision
#: dated inside it must still resolve, because that is the whole point of judging April by April's
#: rule. The alternative was renaming the id inside the live window, which is the contract edit
#: `docs/DECISIONS.md` refused on 2026-08-27 for exactly this reason.
#:
#: **`since` is what makes this a rename rather than a second permanent name.** An old spelling is
#: accepted only in a window that opened *before* the canonical name took over. Without it the map
#: states a fact about all time: write a window dated 2027 — by copying an older one, which is how
#: contract windows actually get written — put the retired id in it, and the envelope resolves it
#: without complaint. The retired name would be alive and in force in a window opened months after
#: the branch that retired it, undoing the rename it exists to serve, and nothing else would catch
#: it: `ops/personhood.py` reads dataclass fields rather than the YAML, and the both-spellings
#: guard below does not fire when only one spelling is present.
#:
#: **This is not a default and not a fallback.** A window declares *one* spelling. Declaring both
#: is refused, because then two rules with the same meaning disagree about which is in force and
#: nothing says which was read; declaring neither is refused as it always was. What the mechanism
#: buys is that a rename costs a window rather than a rewrite of history.
#:
#: The map is a symptom and `docs/FINDINGS.md` says so: an id names a rule inside a window *and*
#: identifies it across windows, and one string cannot do both through a rename. Fifteen other
#: rules are each one rename from an entry here.
RENAMED_RULES: dict[tuple[GuardrailId, str], Renaming] = {
    (GuardrailId.FLOOR, "refuse_when_no_price_satisfies_every_guardrail"): Renaming(
        since=date(2026, 9, 1),
        previously=("refuse_when_no_legal_price_sells",),
    ),
}


def _required(window: GuardrailWindow, guardrail: GuardrailId, rule_id: str) -> GuardrailRule:
    renaming = RENAMED_RULES.get((guardrail, rule_id))
    retired: tuple[str, ...] = renaming.previously if renaming else ()
    accepted = (
        (rule_id, *retired)
        if renaming is None or window.effective_from < renaming.since
        else (rule_id,)
    )

    found = [(name, window.rule(name)) for name in accepted]
    present = [(name, rule) for name, rule in found if rule is not None]

    if len(present) > 1:
        carried = ", ".join(repr(name) for name, _ in present)
        raise EnvelopeError(
            f"the window of {guardrail.value} in force from {window.effective_from} declares "
            f"{carried} — the same rule under a name and its replacement. A window is read in "
            "one vocabulary, and nothing here can say which of the two was meant."
        )
    if not present:
        stale = [name for name in retired if window.rule(name) is not None]
        if stale and renaming is not None:
            raise EnvelopeError(
                f"the window of {guardrail.value} opening {window.effective_from} declares "
                f"{stale[0]!r}, which was retired on {renaming.since}. A window opened after a "
                f"rename is written in the vocabulary of its own time: it declares {rule_id!r}. "
                "The old spelling is readable only in the windows that were open when it was "
                "the name."
            )
        wanted = " or ".join(repr(name) for name in accepted)
        raise EnvelopeError(
            f"the window of {guardrail.value} in force from {window.effective_from} declares "
            f"no rule {wanted}. The envelope needs it and will not substitute a value: a "
            "default is a lie with a plausible shape."
        )
    return present[0][1]


def _exact_decimal(value: object, where: str) -> Decimal:
    """A contract number as an exact `Decimal`.

    PyYAML has already turned `0.05` into a binary float by the time anything here sees it.
    Text is the shortest decimal string that round-trips to that float, which for any
    literal a person actually typed is the literal itself — so the number that reaches the
    arithmetic is the number on disk, and it is a `Decimal` from this line onward. This is
    the one place in `holdout.core` where a binary approximation exists at all, and it does
    not outlive the expression.
    """
    if isinstance(value, bool) or value is None:
        raise EnvelopeError(f"{where} is {value!r}, which is not a number")
    if isinstance(value, Decimal | int | str):
        candidate: Decimal | int | str = value
    else:
        candidate = str(value)
    try:
        return Decimal(candidate)
    except (DecimalException, ValueError) as error:
        raise EnvelopeError(f"{where} is {value!r}, which is not a number") from error


def _decimal(window: GuardrailWindow, guardrail: GuardrailId, rule_id: str) -> Decimal:
    rule = _required(window, guardrail, rule_id)
    return _exact_decimal(rule.value, f"{guardrail.value}/{rule_id}")


def _money(window: GuardrailWindow, guardrail: GuardrailId, rule_id: str) -> Money:
    return Money.of(_decimal(window, guardrail, rule_id))


def _int(window: GuardrailWindow, guardrail: GuardrailId, rule_id: str) -> int:
    value = _decimal(window, guardrail, rule_id)
    if value != value.to_integral_value():
        raise EnvelopeError(f"{guardrail.value}/{rule_id} is {value}, which is not a whole number")
    return int(value)


def _optional_int(window: GuardrailWindow, rule_id: str) -> int | None:
    """A rule that genuinely may be absent from a window, because it was absent from the law.

    `progressive_reduction_window_days` enters Greek law with ν. 5111/2024 and does not
    exist in the windows before it. Absent is the honest answer there, and it is different
    from zero.
    """
    rule = window.rule(rule_id)
    if rule is None:
        return None
    value = _exact_decimal(rule.value, rule_id)
    return int(value)


def _bool(window: GuardrailWindow, guardrail: GuardrailId, rule_id: str) -> bool:
    rule = _required(window, guardrail, rule_id)
    if not isinstance(rule.value, bool):
        raise EnvelopeError(
            f"{guardrail.value}/{rule_id} is {rule.value!r}; the envelope reads it as a "
            "boolean and will not coerce one out of something else."
        )
    return rule.value


def _text(window: GuardrailWindow, guardrail: GuardrailId, rule_id: str) -> str:
    rule = _required(window, guardrail, rule_id)
    if not isinstance(rule.value, str):
        raise EnvelopeError(f"{guardrail.value}/{rule_id} is {rule.value!r}; expected text")
    return rule.value


def _id_set(window: GuardrailWindow, guardrail: GuardrailId, rule_id: str) -> frozenset[str]:
    rule = _required(window, guardrail, rule_id)
    if not isinstance(rule.value, tuple) or not all(isinstance(v, str) for v in rule.value):
        raise EnvelopeError(
            f"{guardrail.value}/{rule_id} is {rule.value!r}; expected a list of identifiers"
        )
    return frozenset(rule.value)
