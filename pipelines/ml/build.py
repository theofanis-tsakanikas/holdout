"""The training run, end to end: silver in, an assessed model out.

**Deliberately short, because it is the only place the contract is read.** Every threshold this
pipeline branches on arrives here, in one screen, so a reader can see the whole set of numbers a
run depends on without opening five modules. The modules below take them as arguments and read no
YAML: a function that loads its own thresholds is a function nobody can test at a different one
without editing a contract.

**It does not promote anything.** `train` returns a fitted model and an assessment; doctrine rule
5 says the approval is a human's, and `promotion.Promotion` is the type that cannot be built
without one. A `build` module that ended by promoting would be the pipeline approving its own
output — the exact thing the rule names.

The engine boundary
-------------------
`from_silver` is the only function here that touches Spark, and it does nothing but read a table
and hand over rows. Everything above it is plain data, so the whole of the training logic is
provable with no engine and no cloud — which is `CLAUDE.md`'s *local is the default*, and the
reason `tests/pipelines/test_ml_*.py` need neither.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from holdout.contracts.model import TrainingSettings
from holdout.core.demand import censoring
from pipelines.ml import calibration, features, model, promotion, split

if TYPE_CHECKING:
    from collections.abc import Sequence

# **There is deliberately no default trading window in this module, and there was one for an
# hour.** `censoring.TradingWindow`'s own docstring says why it is an argument: *"a trading day is
# a fact about a chain and `holdout.core` is not allowed to know one"* — and a pipeline that
# defaults it is not allowed to know one either. The constant that stood here read
# `close_hour=22`, guessed from the shape of a markdown ladder, and the corpus takes baskets in
# the hour beginning 22:00. Claim 4 refused it by name — *hour 22 is outside the trading window
# [7, 22)* — which is the guard working, on a number this module had invented.
#
# So the window is required, and whoever has the rows supplies it. `__main__.py` reads
# `corpus.world.scale`, which is where this corpus declares its own hours.


@dataclass(frozen=True, slots=True)
class TrainingRun:
    """Everything one run produced, including what it threw away and why."""

    split: split.TimeSplit
    build: features.FeatureBuild
    model: model.DemandModel
    calibration: calibration.Calibration
    assessment: promotion.Assessment
    settings: TrainingSettings
    """Carried so the summary can name the sizes it reports against, rather than re-reading."""

    @property
    def summary(self) -> tuple[tuple[str, str], ...]:
        """The numbers a model card carries, as pairs. Printed by `__main__`.

        The reconstruction counts are here rather than in a log, because a model fitted mostly on
        rebuilt store-days is a different object from one fitted on receipts and whoever approves
        it has to be told which they are looking at.
        """
        return (
            ("model", self.model.digest[:16]),
            (
                "split",
                f"{len(self.split.train)} training date(s) -> "
                f"{len(self.split.evaluate)} evaluation date(s), boundary {self.split.boundary}",
            ),
            (
                "features",
                f"{len(self.build.features):,} kept · {self.build.dropped:,} dropped "
                f"({self.build.no_stock_out_hour:,} emptied with no sale, "
                f"{self.build.below_min_share:,} below the share floor, "
                f"{self.build.no_point_estimate:,} no point estimate)",
            ),
            (
                "reconstructed",
                f"{self.build.censored_kept:,} of {len(self.build.features):,} kept rows were "
                f"rebuilt by claim 4's correction, on a curve fitted on "
                f"{self.build.curve_days:,} uncensored day(s)",
            ),
            (
                "model shape",
                f"{self.model.segments} (sku, weekday) rate(s) · "
                f"{self.model.stores} store factor(s) · recency "
                + " ".join(
                    f"{category} {float(factor):.3f}"
                    for category, factor in sorted(self.model.recency_factors.items())
                ),
            ),
            (
                "calibration",
                f"{float(self.calibration.error_pct):+.2f}% in total · "
                f"RMSE {self.calibration.rmse} unit(s) · "
                f"{len(self.calibration.judged(self.settings.min_segment_days))} segment(s) "
                f"judged, "
                f"{len(self.calibration.unjudged(self.settings.min_segment_days))} too small",
            ),
        )


def from_silver(
    spark: Any, schema: str, *, window: censoring.TradingWindow
) -> tuple[features.ShelfDay, ...]:
    """Silver's `shelf_state` and `sales`, as the plain records everything above this line takes.

    The one engine call in this package, and it does two things rather than one because claim 4
    needs both: **whether the shelf emptied**, which is `shelf_state`, and **when the day's units
    left it**, which only the receipts know. The hourly breakdown is what `censoring.fit` learns
    an ordinary day's shape from, and there is nowhere else to get it.

    `category` comes from the reference dimension rather than from `shelf_state`, because silver
    keeps attributes in one place and copying the column into every fact table is how two
    definitions of a category begin.

    **The hours are pivoted in SQL rather than collected raw**, so what crosses the engine
    boundary is one row per store-SKU-day instead of one per receipt line — 300,000 rows at
    `rehearsal` against a few thousand. The columns are generated from the trading window, so a
    chain that opens at six gets sixteen of them and no constant here changes.
    """
    columns = tuple(f"h{hour}" for hour in range(window.open_hour, window.close_hour))
    hours = ", ".join(
        f"sum(case when hour(event_ts) = {hour} then qty else 0 end) as h{hour}"
        for hour in range(window.open_hour, window.close_hour)
    )
    # **The hour columns are named one by one rather than taken as `h.*`**, and that is a defect
    # this run produced before it was written this way: `h.*` carries the subquery's own
    # `store_id`, `sku_id` and `business_date`, `Row.asDict()` keeps the last of two identical
    # names, and every left-join miss then arrived with `business_date` of `None`. The split
    # refused it by name — which is the guard working — but the cause was three columns nobody
    # asked for.
    selected = ", ".join(f"h.{column}" for column in columns)
    rows = spark.sql(
        f"""
        with hourly as (
            select store_id, sku_id, cast(to_date(event_ts) as string) as business_date, {hours}
            from {schema}.sales
            group by store_id, sku_id, to_date(event_ts)
        )
        select s.store_id, s.sku_id, cast(s.business_date as string) as business_date,
               r.category, s.sold_qty as units_sold, s.emptied, s.last_sale_hour, {selected}
        from {schema}.shelf_state s
        join (select distinct sku_id, category from {schema}.reference) r
          on s.sku_id = r.sku_id
        left join hourly h
          on h.store_id = s.store_id and h.sku_id = s.sku_id
         and h.business_date = cast(s.business_date as string)
        """
    ).collect()
    return features.from_rows([row.asDict() for row in rows], hour_columns=columns)


def train(
    days: Sequence[features.ShelfDay],
    settings: TrainingSettings,
    *,
    window: censoring.TradingWindow,
) -> TrainingRun:
    """Split, correct, fit, evaluate, assess. In that order, and the order is the point.

    **The curve is fitted on training days only.** Fitting it over everything would let the
    evaluation half's intraday shape into the reconstruction of the training half — the same leak
    the time split exists to prevent, arriving through claim 4 instead of through the model.
    """
    boundaries = split.split(split.dates_of(days), settings)
    training_days = [day for day in days if day.business_date in set(boundaries.train)]
    evaluation_days = [day for day in days if day.business_date in set(boundaries.evaluate)]

    curve = features.fit_curve(training_days, window)
    fitted = features.build(training_days, curve, settings)
    held_out = features.build(evaluation_days, curve, settings)

    demand = model.fit(fitted.features, recency_days=settings.evaluation_days)
    measured = calibration.measure(demand, held_out.features)
    return TrainingRun(
        split=boundaries,
        build=fitted,
        model=demand,
        calibration=measured,
        assessment=promotion.assess(demand, measured, settings),
        settings=settings,
    )
