"""Demand features, and the place claim 4 stops being arithmetic and becomes a property.

`docs/DECISIONS.md` has carried *"the censoring correction has no consumer"* since 2026-08-29:
`holdout.core.demand.censoring` is proved by `make claim-4` and called by nothing. This module is
the consumer, and the entry's own words say what that changes — *"a censored day reaching a
feature table unmarked is doctrine rule 2 broken, and it will be provable end to end rather than
one module at a time."*

So the rule this module exists to enforce is rule 2, not rule 3: **a reconstructed store-day
carries its marker to everything downstream.** `DemandFeature` has no way to be built without
`censored` and `observed_share`, and `model.py` reads both.

What a store-day means here, and the one place a source's meaning had to be fixed
---------------------------------------------------------------------------------
`ShelfState.stocked_out_from_hour` is the field claim 4 turns on, and `docs/DECISIONS.md` has
carried *"no source has declared what `stocked_out_from_hour` means"* since the same day: the hour
on-hand reached zero and the hour the first shopper was turned away are the same number only if
somebody was there when the shelf emptied.

**Silver has since declared it, and this module is where the declaration is read.**
`pipelines/silver/tables.py` writes `emptied` — the day closed at zero — and `last_sale_hour`,
which its own docstring calls a lower bound: *"the last unit can leave without a sale — it expires,
or it is thrown away — so an hour derived from sales can only be at or before the truth."*

**So the direction stops being conditional and is stated here.** A stock-out hour that is at or
before the truth gives an observed window that is at or shorter than the truth, so
`curve.share_before` returns a share at or below the true one, so `at_least / share` is at or
above the true demand. **This pipeline's reconstructions err high, never low**, and that is a
consequence of silver's derivation rather than a property of claim 4's arithmetic.

The one shape silver can produce that claim 4 has no hour for
-------------------------------------------------------------
A day that emptied and sold nothing has no `last_sale_hour`. `RightCensored` requires an hour, and
there is no honest one to supply: the shelf emptied at some point nobody observed. **Such a day is
excluded and counted**, never defaulted to the opening hour — a default would be doctrine rule 3,
and it would place every one of them at the maximum possible expansion.

That is exactly the shape `CLAUDE.md` says the corpus almost never produces and `evals/censoring/`
therefore constructs. It is counted here rather than assumed absent, because *almost never* is a
measurement of one corpus and this module will one day read a real one.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING

from holdout.core.demand import censoring

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from holdout.contracts.model import TrainingSettings


class FeatureError(ValueError):
    """A feature row that could not be built without inventing something."""


@dataclass(frozen=True, slots=True)
class ShelfDay:
    """One store-SKU-day as `pipelines/silver/` writes it, before claim 4 has read it.

    A plain record rather than a `Row`, so this module is testable with no engine and so the
    mapping from silver's column names happens in exactly one function — `from_rows` — instead of
    being spread across every caller.
    """

    store_id: str
    sku_id: str
    business_date: str
    category: str
    units_sold: int
    emptied: bool
    last_sale_hour: int | None
    units_by_hour: tuple[int, ...] | None = None
    """Present only for days used to fit the availability curve. A censored day never needs it."""


@dataclass(frozen=True, slots=True)
class DemandFeature:
    """What one store-SKU-day is worth as a training observation, marked if it was reconstructed.

    **`censored` and `observed_share` are not optional and have no defaults.** Doctrine rule 2 is
    about a fallback price reaching the label, the P&L and the experiment; the same rule applies
    to a reconstructed demand reaching a training set, and for the same reason — *a fallback that
    looks like a model decision is worse than an outage, because it is silent and it teaches
    somebody to trust it.*
    """

    store_id: str
    sku_id: str
    business_date: str
    category: str
    weekday: int
    units: int
    censored: bool
    observed_share: Fraction

    @property
    def segment(self) -> tuple[str, int]:
        """The grouping the model fits a rate for. See `model.py` for why it is this one."""
        return (self.category, self.weekday)


@dataclass(frozen=True, slots=True)
class FeatureBuild:
    """The features, and every store-day that did not become one, with the reason.

    Counted rather than filtered silently: each of these three is a population somebody will ask
    about, and a build that reported only what it kept could not answer. `evals/censoring/`
    publishes its drop the same way, and `pipelines/gold/` publishes the sales it cannot price.
    """

    features: tuple[DemandFeature, ...]
    curve_days: int
    """How many uncensored days the availability curve was fitted on."""

    no_stock_out_hour: int
    """Emptied, sold nothing, so no hour exists. Excluded rather than defaulted."""

    below_min_share: int
    """Reconstructed from an observed window smaller than the contract admits."""

    no_point_estimate: int
    """The correction answered with a lower bound and no number."""

    @property
    def dropped(self) -> int:
        return self.no_stock_out_hour + self.below_min_share + self.no_point_estimate

    @property
    def censored_kept(self) -> int:
        return sum(1 for feature in self.features if feature.censored)


def weekday_of(business_date: str) -> int:
    """Monday 0 through Sunday 6, from an ISO date, without importing a calendar.

    Written out rather than handed to `datetime.date.fromisoformat().weekday()` for one reason:
    this module is asked for a *feature*, and a feature computed by a library call that silently
    accepts `2026-9-4` would put a Friday in Thursday's segment. `date.fromisoformat` is strict
    enough in 3.12, so this is a thin wrapper — but the strictness is the property being relied
    on, and `split.dates_of` is where it is checked.
    """
    from datetime import date

    return date.fromisoformat(business_date).weekday()


def _whole(value: object, *, column: str) -> int:
    """An integer column as an integer, refusing anything that is not already one.

    **A float is refused rather than truncated.** `units_sold` of `3.0` means the source is
    writing a different type than silver's schema declares, and `int(3.9)` would answer 3 with no
    error — doctrine rule 3 wearing a cast. `bool` is refused too: it is an `int` in Python and
    would let `emptied` be read as a quantity by a typo nobody sees.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise FeatureError(
            f"{column} arrived as {type(value).__name__} ({value!r}). Silver declares it an "
            "integer, and converting here would hide a schema change behind a cast."
        )
    return value


def from_rows(
    rows: Iterable[Mapping[str, object]], *, hour_columns: Sequence[str] = ()
) -> tuple[ShelfDay, ...]:
    """Silver's `shelf_state`, joined to the reference dimension, as plain records.

    The one place column names are read. A second reader would be a second definition of what
    `emptied` means, and the two would drift the first time silver renamed anything.

    `hour_columns` is passed in rather than derived here, and the order **is** the hour order:
    `censoring.AvailabilityCurve` indexes by position within a trading window, so a caller that
    handed these over sorted as text would put hour 10 before hour 7 and fit a curve on a day that
    ran backwards. `build.from_silver` generates them from the window it is given, in order, which
    is the only caller that can know what the window is.
    """
    built: list[ShelfDay] = []
    for row in rows:
        hour = row["last_sale_hour"]
        by_hour: tuple[int, ...] | None = None
        if hour_columns and all(row.get(column) is not None for column in hour_columns):
            by_hour = tuple(_whole(row[column], column=column) for column in hour_columns)
        built.append(
            ShelfDay(
                store_id=str(row["store_id"]),
                sku_id=str(row["sku_id"]),
                business_date=str(row["business_date"]),
                category=str(row["category"]),
                units_sold=_whole(row["units_sold"], column="units_sold"),
                emptied=bool(row["emptied"]),
                last_sale_hour=(None if hour is None else _whole(hour, column="last_sale_hour")),
                units_by_hour=by_hour,
            )
        )
    return tuple(built)


def _state(day: ShelfDay) -> censoring.ShelfState:
    """A silver row as claim 4's type, with silver's declared derivation applied and nothing else.

    `stocked_out_from_hour` is `last_sale_hour` **only where the day emptied**. On a day that held
    all day the last sale hour is just the last sale hour, and passing it here would mark every
    ordinary evening as a stock-out.
    """
    return censoring.ShelfState(
        store_id=day.store_id,
        sku_id=day.sku_id,
        business_date=day.business_date,
        units_sold=day.units_sold,
        stocked_out_from_hour=day.last_sale_hour if day.emptied else None,
    )


def fit_curve(
    days: Sequence[ShelfDay], window: censoring.TradingWindow
) -> censoring.AvailabilityCurve:
    """One pooled curve, over the uncensored days it is handed.

    **The censored days are removed here rather than by `fit`**, and the difference matters:
    `censoring.fit` *refuses* a censored day, deliberately, so that a caller cannot hand it a
    mixed pile and receive a curve fitted partly on the pathology it is about to correct. The
    selection is the caller's obligation and this is the caller — so it is written where a reader
    can see which days were used, instead of being a filter inside the function that must not
    have one.

    **Pooling is one curve for everything, which `docs/DECISIONS.md` has an open entry about.**
    A curve per category is what a real estimator would want, and adding groupings before a
    consumer needed them would have shown a smaller residual error — the direction that flatters.
    This is that consumer, and the grouping it uses is the one this function declares: none.
    Whether the correction survives being grouped is a measurement, and it belongs to whoever
    changes this line rather than to whoever wrote it.
    """
    hourly: list[censoring.HourlySales] = []
    for day in days:
        if day.emptied or day.units_by_hour is None:
            continue
        if sum(day.units_by_hour) != day.units_sold:
            # **Skipped rather than reconciled, and rather than allowed to raise.** `HourlySales`
            # refuses a day whose hours do not add up to its total, correctly: two sources
            # disagree and neither is safe to pick. Silver already has an expectation for exactly
            # this shape — `receipts_account_for_the_units_sold` — so a day arriving here in
            # disagreement is one that got past it, and the honest response is to leave it out of
            # the curve rather than to stop a training run over one row or to invent a total.
            continue
        hourly.append(censoring.HourlySales(state=_state(day), units_by_hour=day.units_by_hour))
    return censoring.fit(hourly, window)


def build(
    days: Sequence[ShelfDay],
    curve: censoring.AvailabilityCurve,
    settings: TrainingSettings,
) -> FeatureBuild:
    """Every store-day that can honestly be a demand observation, marked where it was rebuilt.

    Three exclusions, each counted rather than filtered in silence, and the contract decides only
    one of them — the share floor. The other two are shapes the arithmetic itself has no answer
    for, and a threshold could not have rescued either.
    """
    floor = Fraction(settings.min_observed_share)
    features: list[DemandFeature] = []
    no_hour = below = no_estimate = 0

    for day in days:
        if day.emptied and day.last_sale_hour is None:
            no_hour += 1
            continue
        state = _state(day)
        estimate = censoring.correct(censoring.read(state, curve.window), curve)
        if estimate.units is None:
            no_estimate += 1
            continue
        if estimate.censored and estimate.observed_share < floor:
            below += 1
            continue
        features.append(
            DemandFeature(
                store_id=day.store_id,
                sku_id=day.sku_id,
                business_date=day.business_date,
                category=day.category,
                weekday=weekday_of(day.business_date),
                units=estimate.units,
                censored=estimate.censored,
                observed_share=estimate.observed_share,
            )
        )

    return FeatureBuild(
        features=tuple(features),
        curve_days=curve.days,
        no_stock_out_hour=no_hour,
        below_min_share=below,
        no_point_estimate=no_estimate,
    )
