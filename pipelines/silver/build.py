"""Build silver from bronze, against local Delta, and say what went to quarantine.

This is `TASKS.md`'s `stop_at` for `T010` — *"when silver builds against local Delta with
quarantine non-empty on planted bad data"* — and it is deliberately a plain function rather than
a pipeline run: `pipeline.py` carries the same transformations as Spark Declarative Pipelines
definitions, and those **cannot be imported outside a pipeline run at all**. Measured:

    @dp.materialized_view(...) outside `spark-pipelines run`
      -> PySparkRuntimeError [GRAPH_ELEMENT_DEFINED_OUTSIDE_OF_DECLARATIVE_PIPELINE]

So a repository that only had the declarations would have transformations no test could reach.
The functions in `tables.py` are the logic, this builds them, and `pipeline.py` declares the
same functions to the engine that will run them on the estate.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pipelines.silver import tables

if TYPE_CHECKING:
    from pathlib import Path

    from pyspark.sql import DataFrame, SparkSession

#: What silver reads. Bronze is one directory per table, which is what `bulk.load` wrote.
BRONZE_TABLES: tuple[str, ...] = (
    "pos_lines",
    "esl_acks",
    "shelf_days",
    "cost_ledger",
    "product_master",
)

#: What silver writes. `quarantine` is one table for every source, because its size is a health
#: metric and a metric split five ways is five metrics nobody adds up.
SILVER_TABLES: tuple[str, ...] = ("sales", "price_displayed", "shelf_state", "reference")


class BronzeMissingError(FileNotFoundError):
    """A bronze table silver needs is not there. Raised rather than treated as empty."""


def read_bronze(spark: SparkSession, bronze: Path) -> dict[str, DataFrame]:
    """Every bronze table silver reads, or a refusal naming the one that is absent.

    **An absent table is not an empty one.** A build over a missing `pos_lines` would produce an
    empty `sales`, an empty quarantine and a green run — the vacuous pass this repository filed
    a finding about this morning, one layer along.
    """
    frames: dict[str, DataFrame] = {}
    for table in BRONZE_TABLES:
        directory = bronze / table
        if not directory.is_dir() or not any(directory.glob("*.parquet")):
            raise BronzeMissingError(
                f"{directory} holds no Parquet, so silver would build an empty {table} and "
                "report a clean run. Load bronze first: python -m pipelines.ingest.bulk load"
            )
        frames[table] = spark.read.parquet(str(directory))
    return frames


def build(spark: SparkSession, bronze: Path, silver: Path) -> dict[str, int]:
    """Write every silver table as Delta and return the row counts, quarantine included.

    **Spark reads the Parquet this repository's own stdlib writer produced**, which is a third
    independent reader of that format after pyarrow and this project's tests — and the one that
    matters on the estate, since it is the engine the lakehouse runs.
    """
    frames = read_bronze(spark, bronze)
    sales, sales_bad = tables.sales(frames["pos_lines"])
    displayed, displayed_bad = tables.price_displayed(frames["esl_acks"])
    shelf, shelf_bad = tables.shelf_state(frames["shelf_days"], sales)
    costs, costs_bad = tables.reference(frames["cost_ledger"], frames["product_master"])

    written: dict[str, int] = {}
    for name, frame in (
        ("sales", sales),
        ("price_displayed", displayed),
        ("shelf_state", shelf),
        ("reference", costs),
    ):
        frame.write.format("delta").mode("overwrite").save(str(silver / name))
        written[name] = frame.count()

    quarantine = sales_bad.union(displayed_bad).union(shelf_bad).union(costs_bad)
    quarantine.write.format("delta").mode("overwrite").save(str(silver / "quarantine"))
    written["quarantine"] = quarantine.count()
    return written
