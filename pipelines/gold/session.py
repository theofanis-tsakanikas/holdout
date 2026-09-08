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

from pipelines import session as runtime

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


def build(
    root: Path | None = None, *, name: str = "holdout-gold", cores: int = LOCAL_CORES
) -> SparkSession:
    """The runtime's session where there is one, and a local Delta session where there is not.

    `root` is what the local session needs and what the estate's has no use for: on serverless
    there is no warehouse directory and no Derby metastore to place, so it is optional here and
    refused only on the machine that cannot do without it. `pipelines/session.py` carries why the
    local builder cannot run on the estate at all.
    """
    existing = runtime.provided()
    if existing is not None:
        return existing
    if root is None:
        raise ValueError(
            "A local session needs a root to put its warehouse and metastore in, and no "
            "runtime supplied one. Pass --root, or run where a session already exists."
        )
    return _local(root, name=name, cores=cores)


def _local(root: Path, *, name: str, cores: int) -> SparkSession:
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
        # What `pipelines/session.py::release` reads back. Set here and nowhere else.
        .config(runtime.LOCAL, "true")
        # **`spark.hadoop.` prefixed, and the prefix is the whole of it.** Spark passes
        # `spark.hadoop.*` through to the Hadoop configuration the Hive metastore reads and
        # warns on anything else: written bare, this prints `Ignoring non-Spark config
        # property: javax.jdo.option.ConnectionURL` and the metastore lands in the working
        # directory anyway. A warning on stderr among a hundred Spark lines is not a refusal.
        .config(
            "spark.hadoop.javax.jdo.option.ConnectionURL",
            f"jdbc:derby:;databaseName={metastore};create=true",
        )
    )
    return configure_spark_with_delta_pip(builder).getOrCreate()


def sessions(root: Path, *, name: str = "holdout-gold") -> Iterator[SparkSession]:
    """A session that stops when the caller is done with it — unless it was never ours."""
    spark = build(root, name=name)
    try:
        yield spark
    finally:
        runtime.release(spark)
