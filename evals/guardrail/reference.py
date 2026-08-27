"""A second implementation of the envelope's arithmetic, written to disagree.

Why a second implementation at all
----------------------------------
Driving the gates with an independent corpus answers "does the system refuse?". It does not
answer "does it refuse *for the right reason, at the right place*?" — for that, something
has to know where the boundary is, and if the only thing that knows is `evaluate`, the eval
is asking a function to mark its own paper.

So the boundary is computed twice. This module is the second time, and it is deliberately
built to a different shape from the first:

============================  ==============================  =============================
                              `holdout.core.guardrails`        here
============================  ==============================  =============================
unit                          integer euro cents               exact `Decimal` euros
bounds                        rounded — floors up, ceilings     not rounded at all
                              down, so a bound never rounds
                              toward what it forbids
structure                     one pass appending `Bound`        one predicate per rule,
                              objects, with tie-breaks and      evaluated independently,
                              precedence                        with no notion of which
                                                                one leads
============================  ==============================  =============================

Sharing nothing but the rule *values* is the most independence available, and the limit is
worth naming: this cannot show that the numbers in `contracts/guardrails/` are the right
numbers. Nothing can. It shows that the machinery honours whatever envelope it is handed,
on real prices, at the cent.

The rounding contract, and why it makes the comparison one-sided
----------------------------------------------------------------
`Money.as_lower_bound` rounds **up** and `Money.as_upper_bound` rounds **down**, so every
bound the core computes is **at least as strict** as the exact one here. Two consequences,
and both are asserted rather than assumed:

* if the core **certified** a price, every exact constraint here must hold — with no
  tolerance whatsoever. A certified price outside an exact bound is a hole in the envelope;
* if the core **refused**, the exact constraint must be violated **or** the price must lie
  within one cent of the exact boundary. A refusal further away than that is a bound in the
  wrong place, which is the shape of the bug that once put the ladder's deepest rung below
  the guardrail that was supposed to admit it.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from evals.guardrail.build import Case
from holdout.core.decision import DecisionPath, PriceSource
from holdout.core.guardrails import RefusalCode

#: The width of the rounding contract above. One cent, because that is the scale `Money`
#: rounds at; anything wider would be a tolerance, and claim 5's whole argument is that
#: this repository does not need tolerances.
ONE_CENT = Decimal("0.01")

HUNDRED = Decimal(100)


#: Which way a rule bounds the price. `predicate` is a rule with no edge at all — a frozen
#: category, a stale cost — and a `bound` of `None` says so in the type rather than by an
#: absent field, so nothing downstream has to infer it from the constraint's name. An
#: earlier version of this module did infer it from the name, and got the empty-range check
#: wrong: `weekly_fall` is a floor whose name contains no "floor".
Side = Literal["lower", "upper", "predicate"]


@dataclass(frozen=True, slots=True)
class Constraint:
    """One rule of the envelope, recomputed here, and where its edge is."""

    code: RefusalCode
    name: str
    side: Side
    satisfied: bool
    bound: Decimal | None
    """The exact edge, in euros — a floor when `side` is lower, a ceiling when upper.
    `None` for a predicate."""

    detail: str

    @property
    def slack(self) -> Decimal | None:
        """How far inside the bound the price sits. Negative when outside it."""
        if self.bound is None or self._price is None:
            return None
        return (self._price - self.bound) if self.side == "lower" else (self.bound - self._price)

    _price: Decimal | None = None


def _price(case: Case) -> Decimal:
    return case.proposal.price.euros


def lower_bounds(case: Case) -> tuple[Decimal, ...]:
    return tuple(c.bound for c in constraints(case) if c.side == "lower" and c.bound is not None)


def upper_bounds(case: Case) -> tuple[Decimal, ...]:
    return tuple(c.bound for c in constraints(case) if c.side == "upper" and c.bound is not None)


def _lower(code: RefusalCode, name: str, price: Decimal, bound: Decimal, why: str) -> Constraint:
    return Constraint(
        code=code,
        name=name,
        side="lower",
        satisfied=price >= bound,
        bound=bound,
        detail=f"{why}: price {price} against a floor of {bound}",
        _price=price,
    )


def _upper(code: RefusalCode, name: str, price: Decimal, bound: Decimal, why: str) -> Constraint:
    return Constraint(
        code=code,
        name=name,
        side="upper",
        satisfied=price <= bound,
        bound=bound,
        detail=f"{why}: price {price} against a ceiling of {bound}",
        _price=price,
    )


def _predicate(code: RefusalCode, name: str, satisfied: bool, detail: str) -> Constraint:
    return Constraint(
        code=code, name=name, side="predicate", satisfied=satisfied, bound=None, detail=detail
    )


def constraints(case: Case) -> tuple[Constraint, ...]:
    """Every rule of `case.envelope`, recomputed from the case's own numbers.

    Exact arithmetic throughout. Nothing here reads a `Bound`, an `Assessment` or a
    `PriceBounds` — the inputs are the proposal's numbers and the envelope's rule values,
    and the output is this module's own opinion about each rule.
    """
    envelope = case.envelope
    proposal = case.proposal
    price = _price(case)
    cost = case.unit_cost.euros if proposal.unit_cost is not None else None
    found: list[Constraint] = []

    found.append(
        _predicate(
            RefusalCode.CATEGORY_FROZEN,
            "frozen_category",
            proposal.category_id not in envelope.frozen_categories.category_ids,
            f"category {proposal.category_id!r} against the frozen list",
        )
    )

    if proposal.unit_cost is None or proposal.cost_known_at is None:
        # Not a bound and not a predicate about the price: the caller did not supply
        # something a rule needs. `INPUT_NOT_AVAILABLE` is the core's answer and this module
        # records it as a predicate so the two can be compared, but every arithmetic rule
        # below that needs the cost is skipped rather than computed on a substitute.
        found.append(
            _predicate(
                RefusalCode.INPUT_NOT_AVAILABLE,
                "unit_cost_supplied",
                False,
                "no unit cost with a known arrival time was supplied",
            )
        )
    else:
        age_hours = (proposal.decided_at - proposal.cost_known_at).total_seconds() / 3600
        stale = age_hours > envelope.floor.cost_staleness_hours
        found.append(
            _predicate(
                RefusalCode.COST_STALE,
                "cost_freshness",
                # Only the ladder may proceed on a stale cost — the declared safe state of a
                # path where silence throws the product away.
                (not stale) or proposal.source is PriceSource.LADDER,
                f"cost {age_hours:g}h old against a limit of "
                f"{envelope.floor.cost_staleness_hours}h",
            )
        )

    found.append(
        _lower(
            RefusalCode.BELOW_ABSOLUTE_FLOOR,
            "absolute_floor",
            price,
            envelope.floor.minimum_absolute_price.euros,
            "the absolute floor",
        )
    )
    if cost is not None:
        found.append(
            _lower(
                RefusalCode.BELOW_MARGIN_FLOOR,
                "margin_floor",
                price,
                cost * (Decimal(1) + envelope.floor.minimum_gross_margin_pct / HUNDRED),
                f"cost plus {envelope.floor.minimum_gross_margin_pct}% of cost",
            )
        )

    if envelope.path is DecisionPath.MARKDOWN:
        depth = envelope.max_delta.markdown_max_depth_pct
        found.append(
            _lower(
                RefusalCode.MARKDOWN_EXCEEDS_MAX_DEPTH,
                "markdown_depth",
                price,
                proposal.base_price.euros * (Decimal(1) - depth / HUNDRED),
                f"at most {depth}% below the base price",
            )
        )
        budget = envelope.max_delta.markdown_max_changes_per_sku_per_day
        dispatched = proposal.changes_dispatched_today
        found.append(
            _predicate(
                RefusalCode.INPUT_NOT_AVAILABLE
                if dispatched is None
                else RefusalCode.DAILY_CHANGE_BUDGET_EXHAUSTED,
                "change_budget",
                dispatched is not None and dispatched < budget,
                f"{dispatched} changes dispatched against a budget of {budget}",
            )
        )
    else:
        opening = proposal.week_opening_price
        if opening is None:
            found.append(
                _predicate(
                    RefusalCode.INPUT_NOT_AVAILABLE,
                    "week_opening_price_supplied",
                    False,
                    "a base-price move was proposed with no week-opening price",
                )
            )
        else:
            rise = envelope.max_delta.base_price_max_weekly_increase_pct
            fall = envelope.max_delta.base_price_max_weekly_decrease_pct
            found.append(
                _upper(
                    RefusalCode.BASE_PRICE_MOVE_EXCEEDS_WEEKLY_LIMIT,
                    "weekly_rise",
                    price,
                    opening.euros * (Decimal(1) + rise / HUNDRED),
                    f"at most {rise}% above the week's opening price",
                )
            )
            found.append(
                _lower(
                    RefusalCode.BASE_PRICE_MOVE_EXCEEDS_WEEKLY_LIMIT,
                    "weekly_fall",
                    price,
                    opening.euros * (Decimal(1) - fall / HUNDRED),
                    f"at most {fall}% below the week's opening price",
                )
            )

    cap = envelope.margin_cap
    if cap.in_force and proposal.category_id in cap.regulated_category_ids:
        benchmark = proposal.benchmark_margin_pct
        if cap.basis not in {"per_unit", "per_product_code"}:
            found.append(
                _predicate(
                    RefusalCode.MARGIN_CAP_BASIS_UNEVALUABLE,
                    "cap_basis",
                    False,
                    f"the cap's basis is {cap.basis!r}, which states nothing computable",
                )
            )
        elif benchmark is None or cost is None:
            found.append(
                _predicate(
                    RefusalCode.INPUT_NOT_AVAILABLE,
                    "cap_benchmark_supplied",
                    False,
                    "the cap binds and either the cost or the benchmark margin is missing",
                )
            )
        elif cost is not None:
            found.append(
                _upper(
                    RefusalCode.MARGIN_CAP_EXCEEDED,
                    "margin_cap",
                    price,
                    cost * (Decimal(1) + benchmark / HUNDRED),
                    f"cost plus the benchmark margin of {benchmark}% of cost",
                )
            )

    if proposal.announced_as_reduction and not (
        proposal.is_perishable and envelope.prior_price.perishable_exemption
    ):
        prior = proposal.prior_price
        found.append(
            _predicate(
                RefusalCode.PRIOR_PRICE_NOT_ESTABLISHED,
                "prior_price",
                prior is not None and price < prior.euros,
                (
                    "a reduction is announced with no prior price"
                    if prior is None
                    else f"announced price {price} against a prior price of {prior.euros}"
                ),
            )
        )

    return tuple(found)


def violated(case: Case) -> tuple[Constraint, ...]:
    """The constraints this module says the case breaks. Exact — no tolerance."""
    return tuple(c for c in constraints(case) if not c.satisfied)


def refusal_is_supported(case: Case, code: RefusalCode) -> tuple[bool, str]:
    """Whether the exact arithmetic agrees that `code` had something to refuse.

    Agreement is either an outright violation, or a price inside the exact bound by less
    than a cent — the width of the core's declared conservative rounding. A refusal further
    inside than that is a bound in the wrong place, and this function is what says so.
    """
    matching = [c for c in constraints(case) if c.code is code]
    if not matching:
        return False, f"nothing in this eval's own arithmetic corresponds to {code.value}"
    for constraint in matching:
        if not constraint.satisfied:
            return True, constraint.detail
        if constraint.slack is not None and constraint.slack < ONE_CENT:
            return True, f"{constraint.detail} — inside by {constraint.slack}, under one cent"
    return False, "; ".join(c.detail for c in matching)
