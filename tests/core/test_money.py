"""Money is integer cents, and the rounding of a bound is not the rounding of a price.

Every expected value here is worked out in the test rather than taken from the code. A test
that asserts what the function just computed proves the function is deterministic and
nothing else.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from holdout.core.money import Money, MoneyError


def test_an_amount_is_an_integer_number_of_cents() -> None:
    assert Money.of("1.99").cents == 199
    assert Money.of("0.05").cents == 5
    assert Money.of(Decimal("12")).cents == 1200
    assert Money.of(0).cents == 0


def test_a_binary_float_is_refused_rather_than_converted() -> None:
    """`Decimal(0.1)` is 0.1000000000000000055511151231257827…, and a system that quietly
    accepts that has a rounding bug it will never find."""
    with pytest.raises(MoneyError):
        Money.of(1.99)  # type: ignore[arg-type]
    with pytest.raises(MoneyError):
        Money(cents=Decimal("199"))  # type: ignore[arg-type]


def test_money_never_becomes_a_float() -> None:
    with pytest.raises(TypeError):
        float(Money.of("1.99"))  # type: ignore[arg-type]


def test_a_third_decimal_place_is_refused_rather_than_rounded() -> None:
    """`Money.of('1.005')` is a caller who has not decided what they meant."""
    with pytest.raises(MoneyError):
        Money.of("1.005")


def test_a_price_rounds_half_to_even_because_the_metric_contract_says_so() -> None:
    # 188.5 cents lands exactly between 188 and 189; banker's rounding takes the even one.
    assert Money.as_price(Decimal("188.5")).cents == 188
    assert Money.as_price(Decimal("189.5")).cents == 190
    assert Money.as_price(Decimal("129.35")).cents == 129


def test_a_lower_bound_rounds_up_and_an_upper_bound_rounds_down() -> None:
    """The direction is the whole argument.

    A floor of 112.5 cents rounded to the nearest cent is 112, and 112 is below the floor —
    a bound that rounds toward what it forbids is not a bound. Half-even would give exactly
    that, which is why a bound does not use it.
    """
    assert Money.as_lower_bound(Decimal("112.5")).cents == 113
    assert Money.as_lower_bound(Decimal("112.01")).cents == 113
    assert Money.as_upper_bound(Decimal("125.5")).cents == 125
    assert Money.as_upper_bound(Decimal("125.99")).cents == 125
    # Half-even would have taken both of these to 112 and 126 respectively.
    assert Money.as_price(Decimal("112.5")).cents == 112


def test_percentages_are_exact() -> None:
    # 12.5% of 100 cents is 12.5 cents, and it stays 12.5 rather than becoming 12.499999…
    assert Money.of("1.00").pct(Decimal("12.5")) == Decimal("12.5")
    assert Money.of("2.00").pct(Decimal(70)) == Decimal(140)


def test_a_quantity_times_a_price_is_not_yet_an_amount() -> None:
    """`times` returns a Decimal on purpose: the caller has to name the rounding."""
    raw = Money.of("3.33").times(Decimal("1.5"))
    assert raw == Decimal("499.5")
    assert Money.as_price(raw).cents == 500


def test_arithmetic_and_ordering() -> None:
    assert Money.of("1.50") + Money.of("0.75") == Money.of("2.25")
    assert Money.of("1.50") - Money.of("2.00") == Money(-50)
    assert -Money.of("1.50") == Money(-150)
    assert Money.of("1.00") < Money.of("1.01")
    assert max(Money.of("1.00"), Money.of("0.99")) == Money.of("1.00")


def test_the_euro_view_is_an_exact_decimal() -> None:
    assert Money(199).euros == Decimal("1.99")
    assert str(Money(5)) == "0.05 EUR"
    assert str(Money(-50)) == "-0.50 EUR"
