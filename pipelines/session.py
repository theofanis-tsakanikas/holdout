"""The session a run gets, and who is entitled to stop it.

**Two runtimes, one entry point, and the difference is not a preference.** On a laptop and in CI
there is no Spark until this repository starts one: `pipelines/silver/session.py` and
`pipelines/gold/session.py` build `local[2]` with Delta's extensions and a Derby metastore, which
is what *"builds against local Delta"* means in `TASKS.md`. On the estate every task runs on
**serverless compute, which is Spark Connect** — Databricks' own limitations page says *only Spark
Connect APIs are supported* — and there the session already exists before a line of this
repository runs.

**The local builder cannot run there and the failure would not have been the interesting one.**
`.master("local[2]")`, `spark.sql.extensions`, `spark.sql.catalog.spark_catalog` and
`configure_spark_with_delta_pip` are Spark Classic; `from delta import …` is a module the
serverless environment does not carry. A `spark_python_task` would have died on the import, in
the first seconds of a `backfill` that had already loaded eight months of history.

**And `spark.stop()` is the half that would have been worse.** A task that stops the session the
runtime handed it does not fail — it ends the compute out from under whatever runs next. So this
module answers two questions rather than one: *is there a session already*, and *did we make the
one we are holding*. The second is answered by the session itself, through a config only the
local builder sets, because ownership recorded anywhere else is a second place to keep in step.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyspark.sql import SparkSession

#: Set by the local builders and by nothing else. `release` reads it back off the session, so a
#: session this repository did not build cannot claim to have been built by it.
LOCAL = "spark.holdout.session.local"

#: Databricks sets this on every compute it runs code on, serverless included. It is the second
#: signal rather than the first: `getActiveSession` is what actually answers the question, and
#: this covers the case where the runtime has a session to give but has not yet built it.
RUNTIME = "DATABRICKS_RUNTIME_VERSION"


def provided() -> SparkSession | None:
    """The session the runtime already has, or `None` on a machine that has none."""
    from pyspark.sql import SparkSession

    active = SparkSession.getActiveSession()
    if active is not None:
        return active
    if os.environ.get(RUNTIME):
        # No configuration of any kind: on serverless the settings a local build needs are
        # unsupported, and the ones that matter are the platform's to make.
        return SparkSession.builder.getOrCreate()
    return None


def release(spark: SparkSession) -> None:
    """Stop the session if this repository built it, and otherwise leave it alone."""
    if spark.conf.get(LOCAL, "false") == "true":
        spark.stop()


def use_catalog(spark: SparkSession, catalog: str | None) -> None:
    """Make `catalog` the one two-part table names resolve against, when there is one.

    **A two-part name is not a location.** `saveAsTable("gold.priced_sales")` on the estate
    resolves against whatever catalog the workspace defaults to, writes there, and reports
    success — the tables would exist, under a catalog nobody named, and every grant and every
    dashboard would be pointed at an empty schema. Locally there is no catalog to choose and
    `None` is the honest value.
    """
    if catalog:
        spark.sql(f"use catalog {catalog}")
