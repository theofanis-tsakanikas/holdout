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
    from collections.abc import Callable
    from pathlib import Path

    from pyspark.sql import DataFrame, SparkSession

#: What silver reads. Bronze is one directory per table, which is what `bulk.load` wrote.
BRONZE_TABLES: tuple[str, ...] = (
    "pos_lines",
    "esl_acks",
    "shelf_days",
    "cost_ledger",
    "product_master",
    # **Sixth of seven, and it enters because something asked.** `tables.stores` carries the
    # argument: three of the five covariates an assignment is balanced on are store attributes
    # and no event stream has any of them.
    "store_master",
)

#: What silver writes. `quarantine` is one table for every source, because its size is a health
#: metric and a metric split five ways is five metrics nobody adds up.
SILVER_TABLES: tuple[str, ...] = (
    "sales",
    "price_displayed",
    "shelf_state",
    "reference",
    "stores",
)


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


def _into_schema(schema: str) -> Callable[[str, DataFrame], None]:
    """Write one table into a Unity Catalog schema."""

    def put(name: str, frame: DataFrame) -> None:
        frame.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
            f"{schema}.{name}"
        )

    return put


def _into_directory(silver: Path) -> Callable[[str, DataFrame], None]:
    """Write one table into a directory under `silver`, as Delta."""

    def put(name: str, frame: DataFrame) -> None:
        frame.write.format("delta").mode("overwrite").save(str(silver / name))

    return put


def build(
    spark: SparkSession,
    bronze: Path,
    silver: Path | None = None,
    *,
    schema: str | None = None,
) -> dict[str, int]:
    """Write every silver table as Delta and return the row counts, quarantine included.

    **Spark reads the Parquet this repository's own stdlib writer produced**, which is a third
    independent reader of that format after pyarrow and this project's tests — and the one that
    matters on the estate, since it is the engine the lakehouse runs.

    **A directory or a schema, never both and never neither.** Locally there is no catalog, so
    silver is five Delta directories under `silver`. On the estate there is one, and silver is
    five Unity Catalog tables — which is what `pipelines/ml/__main__.py` already says in a
    comment (*on the estate silver is a Unity Catalog schema*) and what nothing had made true.
    The alternative, registering the directories as external tables, is refused by Unity Catalog
    itself: the zone paths are inside a volume, and a table may not be created inside one.

    The two are mutually exclusive for the reason `infra/pipelines/variables.tf` gives about
    `branch` and `commit`: a pair where both are accepted is a pair where one is silently
    ignored, and the run stays green while the rows land somewhere nobody named.
    """
    if silver is not None and schema is not None:
        raise ValueError(
            "`silver` (a directory) and `schema` (a Unity Catalog schema) are two places, and "
            "a build writes to one of them. Pass one."
        )
    # **Where the rows go is decided before they are read.** A refusal after `read_bronze` would
    # arrive minutes into a build, having done all of the work and none of the writing.
    if schema is not None:
        spark.sql(f"create schema if not exists {schema}")
        put = _into_schema(schema)
    elif silver is not None:
        put = _into_directory(silver)
    else:
        raise ValueError(
            "Neither `silver` (a directory) nor `schema` (a Unity Catalog schema) was given, "
            "so there is nowhere for silver to go."
        )

    frames = read_bronze(spark, bronze)
    sales, sales_bad = tables.sales(frames["pos_lines"])
    displayed, displayed_bad = tables.price_displayed(frames["esl_acks"])
    shelf, shelf_bad = tables.shelf_state(frames["shelf_days"], sales)
    costs, costs_bad = tables.reference(frames["cost_ledger"], frames["product_master"])
    store_rows, store_bad = tables.stores(frames["store_master"])

    written: dict[str, int] = {}
    for name, frame in (
        ("sales", sales),
        ("price_displayed", displayed),
        ("shelf_state", shelf),
        ("reference", costs),
        ("stores", store_rows),
    ):
        put(name, frame)
        written[name] = frame.count()

    quarantine = sales_bad.union(displayed_bad).union(shelf_bad).union(costs_bad).union(store_bad)
    put("quarantine", quarantine)
    written["quarantine"] = quarantine.count()
    return written
