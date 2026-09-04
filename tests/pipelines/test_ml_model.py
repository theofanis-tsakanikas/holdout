"""The demand model's own properties: reproducible, shrunk, and fitted only on what it was given.

The gates in `test_ml_promotion.py` judge a model. These check the three things a gate cannot see —
whether two fits of the same data are the same model, whether a thin cell is pulled toward the
whole, and whether the recency level looked at any day it should not have.

**The leak test is the one that matters.** A recency factor fitted over every row it is handed is
correct; one fitted over rows the caller happened to include from the evaluation half is a leak
that improves every number downstream and goes red nowhere.
"""

from __future__ import annotations

from fractions import Fraction

import pytest
from pipelines.ml import model
from pipelines.ml.features import DemandFeature


def _rows(
    units_by_day: dict[int, int],
    *,
    sku: str = "SKU0001",
    store: str = "ST0001",
    category: str = "bakery",
) -> list[DemandFeature]:
    return [
        DemandFeature(
            store_id=store,
            sku_id=sku,
            business_date=f"2026-03-{day:02d}",
            category=category,
            weekday=day % 7,
            units=units,
            censored=False,
            observed_share=Fraction(1),
        )
        for day, units in sorted(units_by_day.items())
    ]


def test_two_fits_of_the_same_features_are_the_same_model() -> None:
    """The property a promotion record pins, and the reason the arithmetic is exact.

    A model built with floats would differ in the last bits between two runs of identical data and
    the digest would move with it, so *which model was approved* would stop being a fact.
    """
    rows = _rows({day: 20 + day % 5 for day in range(1, 31)})
    first = model.fit(rows, recency_days=7)
    second = model.fit(list(reversed(rows)), recency_days=7)
    assert first.digest == second.digest
    assert len(first.digest) == 64


def test_a_change_to_any_number_changes_the_digest() -> None:
    """Otherwise the digest is decoration. Each of the three parts is moved on its own."""
    rows = _rows(dict.fromkeys(range(1, 31), 20))
    base = model.fit(rows, recency_days=7)
    moved = model.DemandModel(
        rates={key: rate + 1 for key, rate in base.rates.items()},
        store_factors=base.store_factors,
        recency_factors=base.recency_factors,
        grand_rate=base.grand_rate,
        fitted_on_days=base.fitted_on_days,
        censored_share=base.censored_share,
    )
    assert moved.digest != base.digest
    other_store = model.DemandModel(
        rates=base.rates,
        store_factors={"ST9999": Fraction(2)},
        recency_factors=base.recency_factors,
        grand_rate=base.grand_rate,
        fitted_on_days=base.fitted_on_days,
        censored_share=base.censored_share,
    )
    assert other_store.digest != base.digest
    other_recency = model.DemandModel(
        rates=base.rates,
        store_factors=base.store_factors,
        recency_factors={"bakery": Fraction(3, 2)},
        grand_rate=base.grand_rate,
        fitted_on_days=base.fitted_on_days,
        censored_share=base.censored_share,
    )
    assert other_recency.digest != base.digest


def test_a_thin_cell_is_pulled_toward_the_grand_rate() -> None:
    """Shrinkage, asserted as a direction rather than as a number.

    One SKU sells a hundred a day on a single day; every other row sells ten. Its fitted rate must
    land strictly between the two — an unshrunk mean would return the hundred, and a rate equal to
    the grand rate would mean the cell's own evidence was ignored.
    """
    common = _rows(dict.fromkeys(range(1, 29), 10), sku="SKU0001")
    rare = _rows({29: 100}, sku="SKU0002")
    fitted = model.fit([*common, *rare], recency_days=7)
    rate = fitted.rates[("SKU0002", 29 % 7)]
    assert fitted.grand_rate < rate < 100


def test_the_recency_factor_reads_only_the_last_declared_dates() -> None:
    """The leak that would flatter every number downstream, planted as a level shift.

    The last seven days sell double. With `recency_days=7` the factor must be near two; with a
    window covering the whole history it must be near one. **Both directions are asserted**: a
    factor that ignored the window would fail the first, and one that read only the last day would
    pass the first while failing the second.
    """
    quiet = dict.fromkeys(range(1, 22), 10)
    loud = dict.fromkeys(range(22, 29), 20)
    rows = _rows({**quiet, **loud})
    recent = model.fit(rows, recency_days=7)
    whole = model.fit(rows, recency_days=28)
    assert recent.recency_factors["bakery"] > Fraction(3, 2)
    assert abs(whole.recency_factors["bakery"] - 1) < Fraction(1, 10)


def test_an_unseen_sku_or_store_falls_back_rather_than_refusing() -> None:
    """A product listed mid-year and a shop that opened are real shapes, not errors.

    The fallback is the shallowest possible answer, which is a judgement this test pins so that a
    later session changing it has to change a test that says why.
    """
    fitted = model.fit(_rows(dict.fromkeys(range(1, 31), 12)), recency_days=7)
    unseen = fitted.predict(sku_id="SKU9999", weekday=3, store_id="ST9999", category="dairy")
    assert unseen == fitted.grand_rate


def test_a_fit_over_no_features_is_refused() -> None:
    """An empty fit calibrates perfectly against nothing. The vacuous green, at the model."""
    with pytest.raises(model.ModelError, match="no features"):
        model.fit([], recency_days=7)
