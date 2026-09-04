"""Claim 4's first consumer, and doctrine rule 2 as a property of the pipeline.

`docs/DECISIONS.md` carried *"the censoring correction has no consumer"* from 2026-08-29: claim 4
proved the arithmetic and the refusals were right, not that the system uses them. These tests are
the difference — a censored store-day travelling all the way to a training row, still marked.

**And the model on the other side reads the mark.** A test asserting only that `censored` is set
would pass on a pipeline that set it and then dropped it, which is doctrine rule 2 broken with a
field that looks right.
"""

from __future__ import annotations

from fractions import Fraction

import pytest
from pipelines.ml import features, model

from holdout.contracts.loader import load
from holdout.core.demand import censoring

SETTINGS = load().training
WINDOW = censoring.TradingWindow(open_hour=7, close_hour=23)
HOURS = WINDOW.hours


def _flat_day(store: str, sku: str, date: str, per_hour: int) -> features.ShelfDay:
    """A day that held all the way, selling the same amount every trading hour."""
    return features.ShelfDay(
        store_id=store,
        sku_id=sku,
        business_date=date,
        category="bakery",
        units_sold=per_hour * HOURS,
        emptied=False,
        last_sale_hour=WINDOW.close_hour - 1,
        units_by_hour=(per_hour,) * HOURS,
    )


def _curve() -> censoring.AvailabilityCurve:
    """A flat curve: every trading hour carries the same share of the day.

    Flat on purpose, because the share it returns is then an exactly known fraction and every
    assertion below is about the pipeline rather than about the curve's shape.
    """
    days = [
        _flat_day(f"ST{index:04d}", "SKU0001", f"2026-03-{index:02d}", 2) for index in range(1, 6)
    ]
    return features.fit_curve(days, WINDOW)


def test_an_uncensored_day_passes_through_unmarked_and_unchanged() -> None:
    """The identity claim 4 insists on: nothing was hidden, so nothing is reconstructed."""
    curve = _curve()
    built = features.build([_flat_day("ST0009", "SKU0001", "2026-03-09", 3)], curve, SETTINGS)
    (row,) = built.features
    assert row.units == 3 * HOURS
    assert row.censored is False
    assert row.observed_share == Fraction(1)


def test_a_censored_day_is_reconstructed_and_arrives_marked() -> None:
    """Doctrine rule 2: the marker travels with the number, to the training set.

    The day's recorded stock-out hour is the halfway hour of a flat curve, and `share_before` is
    the share that arrived **before** that hour begins — so the observed share is exactly one half
    and the reconstruction is exactly twice what the shelf sold. An exact number rather than an
    approximate one, so a change in the correction shows up as a wrong integer instead of as a
    tolerance somebody widens.
    """
    curve = _curve()
    half = WINDOW.open_hour + HOURS // 2
    day = features.ShelfDay(
        store_id="ST0001",
        sku_id="SKU0001",
        business_date="2026-03-10",
        category="bakery",
        units_sold=2 * (HOURS // 2),
        emptied=True,
        last_sale_hour=half,
        units_by_hour=None,
    )
    built = features.build([day], curve, SETTINGS)
    (row,) = built.features
    assert row.censored is True
    assert row.observed_share == Fraction(HOURS // 2, HOURS)
    assert row.units == 2 * HOURS
    assert built.censored_kept == 1


def test_a_day_that_emptied_with_no_sale_is_excluded_and_counted() -> None:
    """The one shape silver can produce that claim 4 has no hour for.

    **Never defaulted to the opening hour.** A default would be doctrine rule 3 and it would place
    every such day at the maximum possible expansion — the largest reconstruction in the corpus,
    invented, on the days with the least evidence.
    """
    curve = _curve()
    day = features.ShelfDay(
        store_id="ST0002",
        sku_id="SKU0001",
        business_date="2026-03-11",
        category="bakery",
        units_sold=0,
        emptied=True,
        last_sale_hour=None,
    )
    built = features.build([day], curve, SETTINGS)
    assert built.features == ()
    assert built.no_stock_out_hour == 1
    assert built.dropped == 1


def test_a_reconstruction_below_the_declared_share_is_excluded_and_counted() -> None:
    """The contract's floor, applied where the number is more model than receipt.

    The day empties two hours in, so the observed share is 2/16 — well under the declared 0.5, and
    the reconstruction would be eight times the receipts.
    """
    curve = _curve()
    day = features.ShelfDay(
        store_id="ST0003",
        sku_id="SKU0001",
        business_date="2026-03-12",
        category="bakery",
        units_sold=4,
        emptied=True,
        last_sale_hour=WINDOW.open_hour + 1,
    )
    built = features.build([day], curve, SETTINGS)
    assert built.features == ()
    assert built.below_min_share == 1


def test_the_curve_is_never_fitted_on_a_censored_day() -> None:
    """Claim 4's trap in its plainest clothes, and the selection is this module's obligation.

    `censoring.fit` **refuses** a censored day rather than filtering it, so that a caller cannot
    hand over a mixed pile and get a curve fitted partly on the pathology it is about to correct.
    This asserts that `fit_curve` does the selecting — a pile with a censored day in it must still
    produce a curve, over the good days only.
    """
    good = [
        _flat_day(f"ST{index:04d}", "SKU0001", f"2026-03-{index:02d}", 2) for index in range(1, 4)
    ]
    bad = features.ShelfDay(
        store_id="ST0099",
        sku_id="SKU0001",
        business_date="2026-03-20",
        category="bakery",
        units_sold=5,
        emptied=True,
        last_sale_hour=WINDOW.open_hour + 3,
        units_by_hour=None,
    )
    curve = features.fit_curve([*good, bad], WINDOW)
    assert curve.days == len(good)


def test_a_day_whose_hours_disagree_with_its_total_is_left_out_of_the_curve() -> None:
    """Two sources disagreeing, which silver has an expectation for and this must survive.

    **Skipped rather than allowed to raise**, because `HourlySales` refuses such a day — correctly
    — and a training run that stopped on one row would be a pipeline taken down by a defect it
    already reports elsewhere.
    """
    good = [
        _flat_day(f"ST{index:04d}", "SKU0001", f"2026-03-{index:02d}", 2) for index in range(1, 4)
    ]
    inconsistent = features.ShelfDay(
        store_id="ST0050",
        sku_id="SKU0001",
        business_date="2026-03-21",
        category="bakery",
        units_sold=999,
        emptied=False,
        last_sale_hour=WINDOW.close_hour - 1,
        units_by_hour=(1,) * HOURS,
    )
    curve = features.fit_curve([*good, inconsistent], WINDOW)
    assert curve.days == len(good)


def test_the_censored_mark_reaches_the_model_rather_than_stopping_at_the_feature() -> None:
    """Rule 2 all the way to the end, which is the half a field-level assertion cannot see.

    A pipeline that set `censored` and then discarded it would pass every test above. The model
    carries `censored_share`, so *what fraction of this model is reconstruction* is a property of
    the object a human is asked to approve.
    """
    rows = [
        features.DemandFeature(
            store_id="ST0001",
            sku_id="SKU0001",
            business_date=f"2026-03-{day:02d}",
            category="bakery",
            weekday=day % 7,
            units=30,
            censored=day % 4 == 0,
            observed_share=Fraction(1) if day % 4 else Fraction(3, 4),
        )
        for day in range(1, 41)
    ]
    fitted = model.fit(rows, recency_days=SETTINGS.evaluation_days)
    assert fitted.censored_share == Fraction(sum(1 for row in rows if row.censored), len(rows))
    assert fitted.censored_share > 0


def test_a_non_integer_column_is_refused_rather_than_cast() -> None:
    """Doctrine rule 3 at the engine boundary: a cast would hide a schema change.

    The spellings are the ones a source actually produces — a float where silver declares an
    integer, a string, and a `bool`, which is an `int` in Python and would let `emptied` be read
    as a quantity by a typo nobody sees.
    """
    for value in (3.0, "3", True):
        with pytest.raises(features.FeatureError, match="units_sold"):
            features.from_rows(
                [
                    {
                        "store_id": "ST0001",
                        "sku_id": "SKU0001",
                        "business_date": "2026-03-01",
                        "category": "bakery",
                        "units_sold": value,
                        "emptied": False,
                        "last_sale_hour": 12,
                    }
                ]
            )
