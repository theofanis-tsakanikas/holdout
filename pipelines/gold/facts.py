"""The as-of join applied, and nothing else. Everything downstream of it is dbt's.

`CLAUDE.md` names dbt as the silver → gold engine, and this module is the one place gold reaches
for Python instead. The reason is a rule rather than a preference: *"a sale at 14:00 joins to the
cost as it was known at 14:00"* is already implemented, once, in
`pipelines/silver/tables.py::cost_as_of`, with both of its time axes and its two failure
directions tested. **Writing it again in SQL would be one rule in two implementations** — the
defect the contract layer exists to refuse, one layer down and with no compiler to catch it.

So the split falls here: this applies `cost_as_of` and writes two priced tables; the dbt models
read them as sources and do the projection, the cents-to-euro conversion and the ISO week. Every
line of SQL downstream of this point exists once.

**Gold is `cost_as_of`'s first production caller.** Until this branch it was written in silver,
tested in silver, and invoked by nothing outside its own tests — `pipelines/silver/build.py`
writes `sales` and `reference` and never joins them.

The moment each fact is priced at
---------------------------------
A **sale** is priced at `event_ts`, which is the sentence `CLAUDE.md` writes out.

A **disposal** is priced at the **end of its business date**, and that is a stated choice rather
than a derived one. `contracts/metrics/waste_value_per_store_week.v1.yaml` says so about itself —
*"Valuing disposals at the cost known on the day of disposal is a stated choice, not an external
requirement"* — and a cost the ERP published at 15:00 was known on the day of a disposal recorded
against that date. Pricing at the start of the day instead would refuse costs that were in fact
known when the shelf was cleared.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from pyspark.sql import DataFrame, SparkSession

#: What gold reads out of silver. Named rather than globbed, so a silver table that stops being
#: written is a refusal here rather than an empty gold table and a green run — the vacuous pass
#: `pipelines/silver/build.py::read_bronze` refuses one layer down.
SILVER_TABLES: tuple[str, ...] = ("sales", "shelf_state", "reference")

#: What this module writes, and what `pipelines/gold/dbt/models/sources.yml` declares. Two names
#: rather than one because a sale and a disposal are priced at different moments.
PRICED_TABLES: tuple[str, ...] = ("priced_sales", "priced_waste")


class SilverMissingError(FileNotFoundError):
    """A silver table gold needs is not there. Raised rather than treated as empty."""


def read_silver(spark: SparkSession, silver: Path) -> dict[str, DataFrame]:
    """Every silver table gold reads, or a refusal naming the one that is absent."""
    frames: dict[str, DataFrame] = {}
    for table in SILVER_TABLES:
        directory = silver / table
        if not (directory / "_delta_log").is_dir():
            raise SilverMissingError(
                f"{directory} is not a Delta table, so gold would build an empty {table} and "
                "report a clean run. Build silver first: python -m pipelines.silver"
            )
        frames[table] = spark.read.format("delta").load(str(directory))
    return frames


def priced_sales(sales: DataFrame, reference: DataFrame) -> DataFrame:
    """Every receipt line, with the cost as it was known at the moment of the sale."""
    from pipelines.silver import tables

    return tables.cost_as_of(reference, sales, "event_ts")


def priced_waste(shelf_state: DataFrame, reference: DataFrame) -> DataFrame:
    """Every store-day that threw something away, priced at the end of the day it happened on.

    **`shelf_state.unit_cost_cents` is dropped before the join, and that is the point of the
    join.** Silver copies the ERP's cost onto each shelf-day, so a `waste` table could be valued
    from a column that is already sitting there — and it would be the **current** cost rather
    than the one known on the day, which is `CLAUDE.md`'s *"joining to the current cost table
    silently rewrites every historical margin"* available two feet away and needing no join at
    all. Dropping it is also what stops the rename colliding: `cost_as_of` produces
    `unit_cost_as_of` from the reference's own column, and two of them is
    `[COLUMN_ALREADY_EXISTS]` rather than a silent pick.

    `shelf_state` carries one row per store, sku and business date, and `wasted_qty` is zero on
    most of them. The rows that disposed of nothing are dropped **here rather than in the metric**
    — a `waste` table full of zero-quantity rows would make the metric's full outer join produce
    a cell for every store-week that merely traded, and `sum(w.qty * w.unit_cost_as_of)` would be
    the same number computed over a hundred times as many rows.
    """
    from pyspark.sql import functions as sf

    from pipelines.silver import tables

    disposals = (
        shelf_state.filter(sf.col("wasted_qty") > 0)
        .drop("unit_cost_cents")
        .withColumn(
            # The last instant of the business date. `business_date` is a string in the corpus's own
            # shape, so it is cast here rather than assumed to be a date already.
            "disposed_at",
            sf.to_timestamp(sf.to_date(sf.col("business_date")))
            + sf.expr("INTERVAL 1 DAY - INTERVAL 1 SECOND"),
        )
    )
    return tables.cost_as_of(reference, disposals, "disposed_at")


def write(spark: SparkSession, silver: Path, *, schema: str) -> dict[str, int]:
    """Write both priced tables into `schema` as Delta, and return their row counts."""
    frames = read_silver(spark, silver)
    spark.sql(f"create schema if not exists {schema}")
    written: dict[str, int] = {}
    for name, frame in (
        ("priced_sales", priced_sales(frames["sales"], frames["reference"])),
        ("priced_waste", priced_waste(frames["shelf_state"], frames["reference"])),
    ):
        frame.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
            f"{schema}.{name}"
        )
        written[name] = spark.table(f"{schema}.{name}").count()
    return written
