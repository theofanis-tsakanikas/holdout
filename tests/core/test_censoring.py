"""The censoring correction, as a unit — claim 4's arithmetic without a corpus behind it.

`evals/censoring/` is where the claim is attacked, on eighty thousand store-days nobody here
chose. This file is the other half: the small, exact cases where an answer can be written down
by hand, including the two the eval can only reach by sweeping.
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from holdout.core.demand.censoring import (
    AvailabilityCurve,
    CensoringError,
    DemandEstimate,
    FullyObserved,
    HourlySales,
    RightCensored,
    ShelfState,
    TradingWindow,
    correct,
    fit,
    read,
    round_half_even,
)

WINDOW = TradingWindow(open_hour=7, close_hour=11)


def _state(units: int, stocked_out_from_hour: int | None = None) -> ShelfState:
    return ShelfState(
        store_id="S001",
        sku_id="K001",
        business_date="2025-09-01",
        units_sold=units,
        stocked_out_from_hour=stocked_out_from_hour,
    )


def _day(units_by_hour: tuple[int, ...], stocked_out_from_hour: int | None = None) -> HourlySales:
    return HourlySales(
        state=_state(sum(units_by_hour), stocked_out_from_hour), units_by_hour=units_by_hour
    )


#: One unit in each of the first three hours and seven in the last: shares of 0, 1/10, 2/10,
#: 3/10 before each hour. Chosen so every boundary is a different fraction and so that the
#: last hour carries most of the day, which is where a rounding mistake is visible.
CURVE = fit([_day((1, 1, 1, 7))], WINDOW)


class TestRead:
    def test_a_day_the_shelf_held_is_a_point_observation(self) -> None:
        assert read(_state(9), WINDOW) == FullyObserved(units=9)

    def test_a_day_the_shelf_emptied_has_no_units_attribute_at_all(self) -> None:
        reading = read(_state(9, 10), WINDOW)
        assert reading == RightCensored(at_least=9, stocked_out_from_hour=10)
        assert not hasattr(reading, "units")

    def test_the_last_trading_hour_is_censored_like_any_other(self) -> None:
        assert isinstance(read(_state(9, WINDOW.close_hour - 1), WINDOW), RightCensored)

    def test_an_hour_the_shop_was_shut_is_refused(self) -> None:
        with pytest.raises(CensoringError, match="outside the trading window"):
            read(_state(9, WINDOW.close_hour), WINDOW)


class TestFit:
    def test_a_censored_day_is_refused_rather_than_skipped(self) -> None:
        with pytest.raises(CensoringError, match="cannot"):
            fit([_day((1, 1, 1, 7)), _day((2, 0, 0, 0), 8)], WINDOW)

    def test_a_curve_with_no_evidence_in_it_is_not_a_curve(self) -> None:
        with pytest.raises(CensoringError, match="not a curve"):
            fit([_day((0, 0, 0, 0))], WINDOW)

    def test_the_boundaries_are_exact_fractions_of_what_was_observed(self) -> None:
        assert [CURVE.share_before(hour) for hour in range(7, 11)] == [
            Fraction(0),
            Fraction(1, 10),
            Fraction(2, 10),
            Fraction(3, 10),
        ]


class TestCorrect:
    def test_a_day_the_shelf_held_is_returned_untouched(self) -> None:
        estimate = correct(read(_state(9), WINDOW), CURVE)
        assert estimate == DemandEstimate(
            at_least=9, units=9, censored=False, observed_share=Fraction(1)
        )

    def test_a_censored_day_is_expanded_by_the_share_of_itself_that_was_open(self) -> None:
        # Emptied at 09:00 having sold 2, and 1/5 of an ordinary day has arrived by then.
        estimate = correct(RightCensored(at_least=2, stocked_out_from_hour=9), CURVE)
        assert estimate.units == 10
        assert estimate.censored and estimate.observed_share == Fraction(1, 5)

    def test_a_shelf_bare_from_the_first_hour_gets_no_number(self) -> None:
        """The claim's sentence, in the branch where there is nothing at all to expand."""
        estimate = correct(RightCensored(at_least=0, stocked_out_from_hour=7), CURVE)
        assert estimate.units is None and estimate.at_least == 0
        assert not estimate.is_point_estimate

    def test_a_shelf_that_emptied_before_it_sold_anything_gets_no_number(self) -> None:
        """The other one — and the one where a zero would satisfy every other guard here.

        `DemandEstimate` refuses a reconstruction under the units the receipts show, so a zero
        written over a day that sold eleven is already impossible. Zero is not below zero, so
        this is the only day on which the claim can be violated, and only this branch stops it.
        """
        estimate = correct(RightCensored(at_least=0, stocked_out_from_hour=9), CURVE)
        assert estimate.units is None
        assert estimate.observed_share == Fraction(1, 5)

    def test_a_reconstruction_under_its_own_receipts_cannot_be_built(self) -> None:
        with pytest.raises(CensoringError, match="contradicts a receipt"):
            DemandEstimate(at_least=9, units=8, censored=True, observed_share=Fraction(1, 2))


class TestRounding:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (Fraction(1, 2), 0),
            (Fraction(3, 2), 2),
            (Fraction(5, 2), 2),
            (Fraction(7, 2), 4),
            (Fraction(2, 3), 1),
            (Fraction(1, 3), 0),
            (Fraction(11), 11),
        ],
    )
    def test_halves_go_to_the_even_neighbour(self, value: Fraction, expected: int) -> None:
        assert round_half_even(value) == expected

    def test_a_negative_quantity_is_refused(self) -> None:
        with pytest.raises(CensoringError, match="not a negative quantity"):
            round_half_even(Fraction(-1, 2))


class TestShapes:
    def test_hours_that_do_not_sum_to_the_shelf_record_are_refused(self) -> None:
        with pytest.raises(CensoringError, match="do not add up"):
            HourlySales(state=_state(9), units_by_hour=(1, 1, 1, 1))

    def test_a_return_posted_as_a_sale_is_refused(self) -> None:
        with pytest.raises(CensoringError, match="Negative sales"):
            _state(-3)

    def test_a_window_that_closes_before_it_opens_is_refused(self) -> None:
        with pytest.raises(CensoringError, match="not a trading day"):
            TradingWindow(open_hour=11, close_hour=7)

    def test_a_curve_may_not_be_read_under_a_different_window(self) -> None:
        with pytest.raises(CensoringError, match="cannot be read under"):
            AvailabilityCurve(
                window=TradingWindow(open_hour=7, close_hour=23), units_by_hour=(1, 1, 1, 7), days=1
            )
