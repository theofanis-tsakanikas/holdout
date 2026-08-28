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
unit                          integer euro cents               exact `Decimal` euros, and
                                                                the cent reached from them
                                                                through `Fraction`
rounding                      `Money`, quantised at a           `rounding.py`, integer
                              declared precision                division of a rational
structure                     one pass appending `Bound`        one predicate per rule,
                              objects, with tie-breaks and      evaluated independently,
                              precedence                        with no notion of which
                                                                one leads
============================  ==============================  =============================

Sharing nothing but the rule *values* is the most independence available, and the limit is
worth naming: this cannot show that the numbers in `contracts/guardrails/` are the right
numbers. Nothing can. It shows that the machinery honours whatever envelope it is handed,
on real prices, at the cent.

Two bounds per rule, and the tolerance that used to stand in for the second
---------------------------------------------------------------------------
Every bounded rule here carries **two** numbers: the exact edge in euros, and that edge
rounded to the cent the conservative way — floors up, ceilings down — by `rounding.py`,
which shares no arithmetic with `Money`. The second is where the core's bound must land,
to the cent, and having it is what lets every comparison below be exact:

* a **certified** price must satisfy every *exact* constraint, with no tolerance at all. A
  certified price outside an exact bound is a hole in the envelope;
* a **refused** price must fall outside the *rounded* bound this module computed. No
  tolerance either — and this is the half that was wrong before.

What was there instead was a one-cent tolerance: a refusal was supported if the exact
constraint was violated *or* the price sat inside the exact bound by less than a cent. Every
price in this eval is a whole number of cents, so under a correctly rounded core that second
branch is unreachable — the only way to enter it is for the core's bound to sit a cent
**above** where it belongs. The tolerance was therefore not slack for conservative rounding.
It was an exemption for exactly one bug, the too-strict bound, which is the shape this
project's own history says its bugs appear in: the ladder's deepest rung once fell below the
guardrail that was supposed to admit it. `docs/DECISIONS.md` still records the declared cost
of conservative rounding — a price legal by half a cent can be refused — and that cost is
paid at the *rounded* bound, which is now computed rather than tolerated.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from evals.guardrail import rounding
from evals.guardrail.build import Case
from holdout.core.decision import DecisionPath, PriceSource
from holdout.core.guardrails import Envelope, RefusalCode
from holdout.core.money import Money

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

    rule_id: str | None = None
    """The `Bound.rule_id` the core attributes this edge to, so the two can be lined up and
    compared as integers. `None` for a predicate, which produces no bound to compare."""

    rounded: Money | None = None
    """The same edge at the cent, rounded the conservative way by `rounding.py`. This is
    where the core's bound must land — exactly, with nothing tolerated."""

    _price: Decimal | None = None

    @property
    def satisfied_at_the_rounded_bound(self) -> bool:
        """Whether the price is inside the bound *as a whole number of cents*.

        The core cannot place a bound anywhere but on a cent, so this — not the exact edge —
        is the question a refusal has to answer. A predicate has no edge and answers with
        itself.
        """
        if self.rounded is None or self._price is None:
            return self.satisfied
        edge = self.rounded.euros
        return self._price >= edge if self.side == "lower" else self._price <= edge


def _price(case: Case) -> Decimal:
    return case.proposal.price.euros


#: What `constraints` returns, passed around rather than recomputed. Every function below
#: takes this instead of a `Case`, because five checks ask five questions of the same answer
#: and computing it five times made the eval — and therefore `gate-proof`, which runs it once
#: per mutation — five times slower for nothing.
Constraints = tuple[Constraint, ...]


def rounded_lower_bounds(found: Constraints) -> tuple[Money, ...]:
    """Every floor at the cent — what the core's own lower bounds must equal."""
    return tuple(c.rounded for c in found if c.side == "lower" and c.rounded is not None)


def rounded_upper_bounds(found: Constraints) -> tuple[Money, ...]:
    """Every ceiling at the cent — what the core's own upper bounds must equal."""
    return tuple(c.rounded for c in found if c.side == "upper" and c.rounded is not None)


def _lower(
    code: RefusalCode, name: str, rule_id: str, price: Decimal, bound: Decimal, why: str
) -> Constraint:
    return Constraint(
        code=code,
        name=name,
        side="lower",
        satisfied=price >= bound,
        bound=bound,
        detail=f"{why}: price {price} against a floor of {bound}",
        rule_id=rule_id,
        rounded=rounding.as_floor(bound),
        _price=price,
    )


def _upper(
    code: RefusalCode, name: str, rule_id: str, price: Decimal, bound: Decimal, why: str
) -> Constraint:
    return Constraint(
        code=code,
        name=name,
        side="upper",
        satisfied=price <= bound,
        bound=bound,
        detail=f"{why}: price {price} against a ceiling of {bound}",
        rule_id=rule_id,
        rounded=rounding.as_ceiling(bound),
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
    # Read off the *proposal*, which is what `evaluate` sees. `Case` carries the same amount
    # in `unit_cost`, and gating on one field while taking the value from the other means a
    # family that ever set them apart would have this module bounding on an input the core
    # was never handed — a second implementation checking a different question.
    cost = proposal.unit_cost.euros if proposal.unit_cost is not None else None
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
            "minimum_absolute_price_eur",
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
                "minimum_gross_margin_pct",
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
                "markdown_max_depth_pct",
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
                    "base_price_max_weekly_increase_pct",
                    price,
                    opening.euros * (Decimal(1) + rise / HUNDRED),
                    f"at most {rise}% above the week's opening price",
                )
            )
            found.append(
                _lower(
                    RefusalCode.BASE_PRICE_MOVE_EXCEEDS_WEEKLY_LIMIT,
                    "weekly_fall",
                    "base_price_max_weekly_decrease_pct",
                    price,
                    opening.euros * (Decimal(1) - fall / HUNDRED),
                    f"at most {fall}% below the week's opening price",
                )
            )

    cap = envelope.margin_cap
    if cap.in_force and proposal.category_id in cap.regulated_category_ids:
        markup = proposal.benchmark_markup_on_cost
        if cap.basis not in {"per_unit", "per_product_code"}:
            found.append(
                _predicate(
                    RefusalCode.MARGIN_CAP_BASIS_UNEVALUABLE,
                    "cap_basis",
                    False,
                    f"the cap's basis is {cap.basis!r}, which states nothing computable",
                )
            )
        elif markup is None or cost is None:
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
                    "cap_benchmark",
                    price,
                    cost * (Decimal(1) + markup.pct / HUNDRED),
                    f"cost plus a benchmark mark-up of {markup}",
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


def violated(found: Constraints) -> Constraints:
    """The constraints this module says the case breaks. Exact — no tolerance."""
    return tuple(c for c in found if not c.satisfied)


def refusal_is_supported(found: Constraints, code: RefusalCode) -> tuple[bool, str]:
    """Whether this module's own arithmetic agrees that `code` had something to refuse.

    Agreement is the price falling outside the bound **this module rounded**, or a predicate
    this module says is unsatisfied. There is no tolerance: the bound is computed to the
    cent here, by arithmetic the core does not share, so "close enough" has nothing left to
    mean. A refusal at a bound a cent stricter than this one is a bound in the wrong place,
    and this function is what says so — which the one-cent tolerance it replaced could not,
    because that was the only case the tolerance ever admitted.
    """
    matching = [c for c in found if c.code is code]
    if not matching:
        return False, f"nothing in this eval's own arithmetic corresponds to {code.value}"
    for constraint in matching:
        if not constraint.satisfied_at_the_rounded_bound:
            return True, constraint.detail
    return False, "; ".join(
        f"{c.detail}"
        + (f" — at the cent the bound is {c.rounded}" if c.rounded is not None else "")
        for c in matching
    )


def ladder_floor(envelope: Envelope, cost: Money) -> Money:
    """The envelope's lower bound for a markdown, computed here, at the cent.

    The declared safe state is fed this rather than a floor read off the envelope, so `G6`
    asks two questions at once: does the ladder's answer survive the envelope, and do the
    eval's floor and the core's floor agree to the cent?

    It used to end in `Money.as_lower_bound` — the core's own rounding — under a docstring
    claiming the direction had been arrived at independently. It had not: patch that
    primitive and this moved with it, so the agreement `G6` was checking was an agreement
    with itself. The direction is re-decided in `rounding.py` and the arithmetic that
    carries it out shares nothing with `Money`.
    """
    exact_margin_floor = cost.euros * (
        Decimal(1) + envelope.floor.minimum_gross_margin_pct / HUNDRED
    )
    return rounding.as_floor(max(envelope.floor.minimum_absolute_price.euros, exact_margin_floor))
