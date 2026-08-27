"""Scenario selection — the arithmetic that turns a model's table into one price.

"The model returns a scenario table, never a price. Code picks the scenario by arithmetic."

That sentence is the whole of this module. The model is asked *what would happen at each
candidate price*; it is never asked *which price*. The second question has exactly one
correct answer given the inputs, and by the test this project applies to every row — is
there exactly one correct answer here? — it is therefore code.

Nothing here estimates, forecasts or fits. `Scenario.expected_units` arrives as data. A
function in this module that computed it would have quietly moved the boundary.

The objective
-------------
The same arithmetic the metric contract declares for
`category_margin_per_store_week`: revenue, less the cost of what sells, less the cost of
what is thrown away.

    units      = min(expected_units, remaining_stock)      # you cannot sell what is gone
    contribution = units * (price - unit_cost) - (remaining_stock - units) * unit_cost

The waste term is what makes this a markdown problem rather than a margin problem. Without
it the best price is always the highest one the guardrails allow, and the ladder would
never have been invented.

Ties
----
Broken by a stated rule and never by dict ordering, because a selection that depends on
insertion order is not reproducible and a readout computed from it cannot be checked a year
later. Contributions are quantised to whole cents *before* they are compared, so two
scenarios that differ in the tenth decimal of a forecast tie honestly instead of being
separated by a difference no SQL implementation would reproduce. Among genuine ties the
**higher price** wins: at the same contribution the higher price gives away less margin
that the customer was willing to pay, and it keeps the reference price higher for the next
decision. Candidate prices are unique by construction — a table with the same price twice
is refused — so price is a total order and there is never a third tie-break.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from holdout.core.money import Money


class ScenarioTableError(ValueError):
    """A scenario table this module will not choose from."""


@dataclass(frozen=True, slots=True)
class Scenario:
    """One row of the model's answer: a candidate price and what is expected to happen.

    `expected_units` is a `Decimal` because fresh produce sells by weight, and because a
    float would put a binary approximation one multiplication away from a euro amount.
    """

    price: Money
    expected_units: Decimal

    def __post_init__(self) -> None:
        if self.expected_units < 0:
            raise ScenarioTableError(
                f"a scenario forecasts {self.expected_units} units at {self.price}. "
                "Negative demand is a defect in the table, not a decision to be taken."
            )


@dataclass(frozen=True, slots=True)
class Outcome:
    """A scenario with the deterministic arithmetic applied to it."""

    scenario: Scenario
    units_sold: Decimal
    units_wasted: Decimal
    revenue: Money
    cost_of_sales: Money
    cost_of_waste: Money
    contribution: Money

    @property
    def price(self) -> Money:
        return self.scenario.price


@dataclass(frozen=True, slots=True)
class Selection:
    """The chosen scenario and the whole ranking behind it.

    The ranking is returned, not discarded, because "why this price" is a question the
    decision record has to be able to answer and because a selection whose runner-up was
    one cent behind is a different fact from one that won by a mile.
    """

    chosen: Outcome
    ranked: tuple[Outcome, ...]

    @property
    def price(self) -> Money:
        return self.chosen.price

    @property
    def runner_up(self) -> Outcome | None:
        return self.ranked[1] if len(self.ranked) > 1 else None

    @property
    def margin_of_victory(self) -> Money | None:
        """How much better the winner was than the next scenario, in whole cents."""
        second = self.runner_up
        return None if second is None else self.chosen.contribution - second.contribution


def outcome_of(scenario: Scenario, *, unit_cost: Money, remaining_stock: Decimal) -> Outcome:
    """The arithmetic for one scenario. Public, so that an eval can check a single row."""
    if remaining_stock < 0:
        raise ScenarioTableError("remaining_stock is a quantity on a shelf; it is never negative")
    units = min(scenario.expected_units, remaining_stock)
    wasted = remaining_stock - units
    revenue = Money.as_price(scenario.price.times(units))
    cost_of_sales = Money.as_price(unit_cost.times(units))
    cost_of_waste = Money.as_price(unit_cost.times(wasted))
    return Outcome(
        scenario=scenario,
        units_sold=units,
        units_wasted=wasted,
        revenue=revenue,
        cost_of_sales=cost_of_sales,
        cost_of_waste=cost_of_waste,
        contribution=revenue - cost_of_sales - cost_of_waste,
    )


def select(
    scenarios: Sequence[Scenario], *, unit_cost: Money, remaining_stock: Decimal
) -> Selection:
    """Pick the scenario with the highest contribution, ties broken by the higher price.

    Deterministic in the strong sense: the same table in a different order gives the same
    answer, and gives it as the same object graph. The guardrail envelope has not been
    consulted at all — the decision path is model, then selection, then guardrails, and a
    selection that pre-filtered on the envelope would be answering a different question
    from the one the readout later re-computes.
    """
    if not scenarios:
        raise ScenarioTableError(
            "an empty scenario table is not a decision the code can take. The model returns "
            "at least one candidate, or the path falls to its declared safe state."
        )
    prices = [s.price for s in scenarios]
    if len(set(prices)) != len(prices):
        raise ScenarioTableError(
            "the scenario table contains the same candidate price twice, so two rows "
            "forecast different outcomes for the same shelf price. Which one is right is "
            "not a question arithmetic can answer."
        )
    outcomes = [
        outcome_of(s, unit_cost=unit_cost, remaining_stock=remaining_stock) for s in scenarios
    ]
    ranked = tuple(sorted(outcomes, key=lambda o: (-o.contribution.cents, -o.price.cents)))
    return Selection(chosen=ranked[0], ranked=ranked)
