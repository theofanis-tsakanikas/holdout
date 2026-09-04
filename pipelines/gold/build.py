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
    spark.sql(f"create schema if not exists {schema}")
    mounted: list[str] = []
    for table in facts.SILVER_TABLES:
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


def build(spark: SparkSession, silver: Path, *, root: Path) -> Built:
    """Everything, in the one order it can happen in, and the counts it produced."""
    register_silver(spark, silver, schema=session.SILVER_SCHEMA)
    priced = facts.write(spark, silver, schema=session.SCHEMA)
    unpriced = spark.sql(
        f"select count(*) as n from {session.SCHEMA}.priced_sales where unit_cost_as_of is null"
    ).collect()[0]["n"]
    built = models.run(spark, target_root=root)
    counts = {
        name: spark.table(f"{session.SCHEMA}.{name}").count()
        for name in built
        if name not in facts.PRICED_TABLES
    }
    return Built(priced=priced, tables=counts, unpriced_sales=int(unpriced))
