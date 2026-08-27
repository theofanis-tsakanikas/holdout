"""Scenario selection, with every contribution worked out by hand.

The arithmetic under test, once:

    units        = min(expected_units, remaining_stock)
    contribution = units * (price - cost) - (stock - units) * cost

Each test states the numbers it expects and where they come from, so the assertions do not
depend on the implementation being right.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from holdout.core.money import Money
from holdout.core.pricing import Scenario, ScenarioTableError, outcome_of, select


def scenario(price: str, units: str) -> Scenario:
    return Scenario(price=Money.of(price), expected_units=Decimal(units))


def test_one_row_of_the_arithmetic() -> None:
    """price 2.00, cost 1.20, 8 on the shelf, 3 forecast to sell.
    revenue      3 x 200 =  600
    cost of sales 3 x 120 =  360
    waste         5 x 120 =  600
    contribution 600 - 360 - 600 = -360 cents.
    """
    outcome = outcome_of(
        scenario("2.00", "3"), unit_cost=Money.of("1.20"), remaining_stock=Decimal(8)
    )
    assert outcome.units_sold == Decimal(3)
    assert outcome.units_wasted == Decimal(5)
    assert outcome.revenue == Money.of("6.00")
    assert outcome.cost_of_sales == Money.of("3.60")
    assert outcome.cost_of_waste == Money.of("6.00")
    assert outcome.contribution == Money(-360)


def test_you_cannot_sell_more_than_is_on_the_shelf() -> None:
    """12 forecast against 8 in stock sells 8 and wastes nothing."""
    outcome = outcome_of(
        scenario("1.00", "12"), unit_cost=Money.of("1.20"), remaining_stock=Decimal(8)
    )
    assert outcome.units_sold == Decimal(8)
    assert outcome.units_wasted == Decimal(0)
    # 8 x 100 - 8 x 120 - 0 = -160
    assert outcome.contribution == Money(-160)


def test_the_waste_term_is_what_makes_this_a_markdown_problem() -> None:
    """cost 1.20, 8 in stock. At 2.00 only three sell and five are thrown away (-3.60); at
    1.50 six sell and two are thrown away (900 - 720 - 240 = -60); at 1.00 all eight sell
    below cost (-1.60). The middle price loses least, and without the waste term the
    highest price would always win."""
    table = [scenario("2.00", "3"), scenario("1.50", "6"), scenario("1.00", "12")]
    selection = select(table, unit_cost=Money.of("1.20"), remaining_stock=Decimal(8))
    assert selection.price == Money.of("1.50")
    assert selection.chosen.contribution == Money(-60)
    assert [o.price for o in selection.ranked] == [
        Money.of("1.50"),
        Money.of("1.00"),
        Money.of("2.00"),
    ]
    assert selection.margin_of_victory == Money(100)


def test_the_answer_does_not_depend_on_the_order_of_the_table() -> None:
    """A selection that depended on insertion order would not be reproducible, and a
    readout computed from it could not be checked a year later."""
    table = [scenario("2.00", "3"), scenario("1.50", "6"), scenario("1.00", "12")]
    forwards = select(table, unit_cost=Money.of("1.20"), remaining_stock=Decimal(8))
    backwards = select(
        list(reversed(table)), unit_cost=Money.of("1.20"), remaining_stock=Decimal(8)
    )
    assert forwards == backwards


def test_a_tie_is_broken_by_the_higher_price() -> None:
    """cost 1.00, 10 in stock.
    at 3.00 with 4 selling:  4 x 200 - 6 x 100 = 800 - 600 = 200
    at 2.00 with 6 selling:  6 x 100 - 4 x 100 = 600 - 400 = 200
    A genuine tie, and the higher price wins: at the same contribution a lower price gives
    away margin the customer was willing to pay.
    """
    table = [scenario("2.00", "6"), scenario("3.00", "4")]
    selection = select(table, unit_cost=Money.of("1.00"), remaining_stock=Decimal(10))
    assert selection.chosen.contribution == Money(200)
    assert selection.runner_up is not None
    assert selection.runner_up.contribution == Money(200)
    assert selection.price == Money.of("3.00")
    assert selection.margin_of_victory == Money(0)


def test_fractional_quantities_stay_exact() -> None:
    """Fresh produce sells by weight. 2.50 x 4.4 = 11.00 exactly, and it stays 11.00."""
    outcome = outcome_of(
        scenario("2.50", "4.4"), unit_cost=Money.of("1.00"), remaining_stock=Decimal(10)
    )
    assert outcome.revenue == Money.of("11.00")
    assert outcome.cost_of_sales == Money.of("4.40")
    assert outcome.cost_of_waste == Money.of("5.60")
    assert outcome.contribution == Money.of("1.00")


def test_a_half_cent_in_the_revenue_rounds_half_to_even() -> None:
    """3.33 x 1.5 = 499.5 cents, exactly between two. Half-even takes it to 500."""
    outcome = outcome_of(
        scenario("3.33", "1.5"), unit_cost=Money.of("0.00"), remaining_stock=Decimal("1.5")
    )
    assert outcome.revenue == Money.of("5.00")


def test_an_empty_table_is_not_a_decision() -> None:
    with pytest.raises(ScenarioTableError, match="empty"):
        select([], unit_cost=Money.of("1.00"), remaining_stock=Decimal(1))


def test_the_same_candidate_price_twice_is_refused() -> None:
    """Two rows forecasting different outcomes for the same shelf price is a question
    arithmetic cannot answer, and picking one would be picking silently."""
    with pytest.raises(ScenarioTableError, match="twice"):
        select(
            [scenario("2.00", "3"), scenario("2.00", "5")],
            unit_cost=Money.of("1.00"),
            remaining_stock=Decimal(8),
        )


def test_negative_demand_is_a_defect_not_a_decision() -> None:
    with pytest.raises(ScenarioTableError, match="Negative demand"):
        Scenario(price=Money.of("1.00"), expected_units=Decimal(-1))


def test_the_selection_carries_the_whole_ranking() -> None:
    """ "Why this price" is a question the decision record has to answer, and a winner that
    was one cent ahead is a different fact from one that won by a mile."""
    table = [scenario("2.00", "3"), scenario("1.50", "6")]
    selection = select(table, unit_cost=Money.of("1.20"), remaining_stock=Decimal(8))
    assert len(selection.ranked) == 2
    assert selection.ranked[0] is selection.chosen
