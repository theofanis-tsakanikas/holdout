"""Build gold from silver, against local Delta, and say what came out.

This is `TASKS.md`'s `stop_at` for `T011` — *"when gold builds against local Delta and the
compiled consumers match byte-for-byte"* — and the two halves meet in one run rather than in two
claims:

* **it builds**: silver is registered from paths, `facts.py` applies the as-of join, and dbt
  builds five models, three of which are compiled from `contracts/metrics/*.yaml`;
* **the consumers match**: those three are reached through `model-paths`, so **no copy exists**
  and `make contracts`' existing byte comparison is the only definition check gold needs.

The registration step is the one place local and the estate genuinely differ
---------------------------------------------------------------------------
On the estate silver is `silver.sales` in Unity Catalog and dbt's sources resolve there. Locally
there is no catalog, so each silver Delta directory is mounted as an external table under the
same name. **Everything below the read is identical**, and the difference is written here rather
than left for a reader to notice — the same shape `pipelines/silver/pipeline.py` uses for bronze.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pipelines.gold import facts, models, session

if TYPE_CHECKING:
    from pathlib import Path

    from pyspark.sql import SparkSession


@dataclass(frozen=True, slots=True)
class Built:
    """What one gold build produced. Counts over this silver directory, never properties."""

    priced: dict[str, int] = field(default_factory=dict)
    tables: dict[str, int] = field(default_factory=dict)
    unpriced_sales: int = 0
    """Receipt lines silver could not price, and which therefore have no margin row.

    **Reported rather than swallowed.** `decision_economics` drops them, because a line with
    revenue and no cost enters `sum(qty*price_paid) - sum(qty*unit_cost_as_of)` as pure margin —
    SQL's `sum` skips the null in the second term and not in the first. Dropping understates the
    week; keeping overstates it and calls the overstatement a profit. The one that is countable
    is the one taken.
    """


def register_silver(spark: SparkSession, silver: Path, *, schema: str) -> tuple[str, ...]:
    """Mount each silver Delta directory as a table, so dbt's sources have something to resolve.

    `create table … using delta location …` rather than a temporary view, because a view is
    session-scoped and dbt resolves its sources through the catalog.
    """
    from pipelines.silver.build import SILVER_TABLES

    spark.sql(f"create schema if not exists {schema}")
    mounted: list[str] = []
    # **Every table silver wrote, not only the three gold's facts read.** `pipelines/gold/
    # experiments.py` reads `stores` for the balance covariates and `price_displayed` for
    # exposure, and a mount list that named facts' three would have left both invisible — on a
    # machine with no catalog, which is every machine except the estate.
    for table in SILVER_TABLES:
        directory = silver / table
        if not (directory / "_delta_log").is_dir():
            raise facts.SilverMissingError(
                f"{directory} is not a Delta table, so gold would build over nothing. "
                "Build silver first: python -m pipelines.silver"
            )
        spark.sql(f"drop table if exists {schema}.{table}")
        spark.sql(f"create table {schema}.{table} using delta location '{directory}'")
        mounted.append(f"{schema}.{table}")
    return tuple(mounted)


def priced(
    spark: SparkSession, silver: Path | None = None, *, silver_schema: str | None = None
) -> tuple[dict[str, int], int]:
    """The two priced tables, and the count of receipt lines that could not be priced.

    **Separated from `build` because on the estate it is a task of its own.** The gold job runs
    `dbt` against `gold.priced_sales` and `gold.priced_waste`, which are written here — so this
    has to have finished before dbt starts. The first version of `infra/pipelines/jobs.tf` had
    the dependency the other way round, which would have run dbt against sources that did not
    exist yet.
    """
    written = facts.write(spark, silver, schema=session.SCHEMA, silver_schema=silver_schema)
    unpriced = spark.sql(
        f"select count(*) as n from {session.SCHEMA}.priced_sales where unit_cost_as_of is null"
    ).collect()[0]["n"]
    return written, int(unpriced)


def build(
    spark: SparkSession, silver: Path, *, root: Path, silver_schema: str | None = None
) -> Built:
    """Everything, in the one order it can happen in, and the counts it produced."""
    if silver_schema is None:
        register_silver(spark, silver, schema=session.SILVER_SCHEMA)
    priced_counts, unpriced = priced(spark, silver, silver_schema=silver_schema)
    built = models.run(spark, target_root=root)
    counts = {
        name: spark.table(f"{session.SCHEMA}.{name}").count()
        for name in built
        if name not in facts.PRICED_TABLES
    }
    return Built(priced=priced_counts, tables=counts, unpriced_sales=unpriced)
