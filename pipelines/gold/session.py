"""A Spark session gold can name tables in, with nothing written into the working directory.

**Why this is not `pipelines/silver/session.py`.** Silver writes Delta to paths and reads them
back by path, so it needs no catalog at all. Gold cannot: every one of its consumers names a
**relation**.

    generated/dbt/models/metrics/…   {{ ref('decision_economics') }}
    generated/readout/…              from gold.decision_economics version as of :data_version
    generated/sql/functions/…        ${catalog}.metrics.category_margin_per_store_week_v3

A path has no name, and `version as of` is a clause on a named relation. So gold runs against a
metastore — Derby's, locally; Unity Catalog on the estate — and the difference is written here
rather than left for a reader to notice.

**Both of Spark's scratch directories are caller-chosen, and that is a defect this repository
already has.** A default session puts `spark-warehouse/`, `metastore_db/` and `derby.log` in the
**current working directory**, which for a session run from the repository root is the repository.
Measured: probing this branch left an untracked `spark-warehouse/` in the worktree, and nothing
in `.gitignore` covers any of the three. Passing both is what stops a test writing into the tree
it is testing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from pyspark.sql import SparkSession

#: Two cores, for the reason `pipelines/silver/session.py` gives: a gold build over a smoke world
#: is seconds of work, and the parallelism costs a machine that is unusable while the suite runs.
LOCAL_CORES = 2

#: The schema gold's tables live in. `generated/readout/*.sql` names `gold.decision_economics` by
#: hand, so this is not a preference — it is the name the compiled consumer already reads, and a
#: different one here would make the generated query unrunnable rather than merely inconsistent.
SCHEMA = "gold"

#: Where silver's tables are registered from paths. Locally there is no catalog to have written
#: them into, so `build` mounts each Delta directory under this name; on the estate silver is
#: `silver.sales` in Unity Catalog and nothing below the read differs.
SILVER_SCHEMA = "silver"


def build(root: Path, *, name: str = "holdout-gold", cores: int = LOCAL_CORES) -> SparkSession:
    """A session whose warehouse and metastore live under `root`, and nowhere else.

    The engine imports are inside the function on purpose. `pipelines/gold/` is imported by tests
    that `make test` deselects, and a module-level `import pyspark` here would make importing
    anything from this package fail on every machine without the extra — which is every machine
    except the one CI job that installs it. That is the shape
    `tests/boundary/test_the_engine_is_never_skipped.py` polices in `tests/`, arriving one
    directory over.
    """
    from delta import configure_spark_with_delta_pip
    from pyspark.sql import SparkSession

    warehouse = root / "warehouse"
    metastore = root / "metastore_db"
    builder = (
        SparkSession.builder.appName(name)
        .master(f"local[{cores}]")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", str(cores))
        .config("spark.sql.warehouse.dir", str(warehouse))
        .config(
            "javax.jdo.option.ConnectionURL",
            f"jdbc:derby:;databaseName={metastore};create=true",
        )
    )
    return configure_spark_with_delta_pip(builder).getOrCreate()


def sessions(root: Path, *, name: str = "holdout-gold") -> Iterator[SparkSession]:
    """A session that stops when the caller is done with it. For a fixture or a `with`."""
    spark = build(root, name=name)
    try:
        yield spark
    finally:
        spark.stop()
