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
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from pyspark.sql import SparkSession

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


@contextmanager
def owned(build: Callable[[], SparkSession]) -> Iterator[SparkSession]:
    """The runtime's session where there is one, and one built here where there is not.

    **Only the second is stopped, and the caller does not have to know which it got.** A task that
    stops the session the runtime handed it does not fail — it ends the compute out from under
    whatever runs next.

    **Ownership is lexical, and the first version asked the session instead.** The local builders
    set a config, `spark.holdout.session.local`, and `release` read it back with a default; the
    argument was that ownership recorded anywhere else is a second thing to keep in step. On
    serverless that read is refused outright:

        AnalysisException: [CONFIG_NOT_AVAILABLE.WITHOUT_SUGGESTION]
        Configuration spark.holdout.session.local is not available.  SQLSTATE: 42K0I

    A default argument is not a default there — `spark.conf.get` raises for a key the platform
    does not know rather than returning what it was given. So the module written so that the
    estate's session would not be stopped failed on being asked whether to stop it, in the silver
    job, after the baseline had loaded.

    **The knowledge was never the session's to hold.** The code that decides whether to build one
    is the code that knows whether it did; a `with` block carries that without asking anybody.
    """
    existing = provided()
    if existing is not None:
        yield existing
        return
    spark = build()
    try:
        yield spark
    finally:
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
