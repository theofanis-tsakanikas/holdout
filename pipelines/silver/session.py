"""A local Spark session with Delta configured, and the numbers it costs.

**There is no cluster here.** `local[2]` in a temporary directory is what *"builds against local
Delta"* means in `TASKS.md`'s `stop_at`, and it is the whole reason the engine sits in an
optional dependency group rather than in the dev group.

Measured on this machine, macOS arm64, Java 17.0.19:

    first session, resolving Delta's jars from Maven   50.9s
    every session after that, from the Ivy cache        3.6s
    what the cache holds afterwards                     14 MB

**The first number is what a CI job pays**, because `~/.ivy2` is empty on a fresh runner unless
something caches it, and it is stated rather than hidden inside a test's duration. Nothing here
caches it yet: that is a decision about a job that has run once, and the measurement comes first.

**The JVM is not optional and not installed by `uv`.** `pyspark` is a Python package around a
Java program; the runner image documents 8, 11, 17, 21 and 25 preinstalled with 17 as default,
and a laptop without one gets an error from Spark rather than a skip from pytest —
`tests/boundary/test_the_engine_is_never_skipped.py` is what keeps it that way.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession

if TYPE_CHECKING:
    from collections.abc import Iterator

#: Two cores rather than every core. A silver build over a smoke world is seconds of work and
#: the parallelism buys nothing; what it costs is a machine that is unusable while the suite
#: runs, on a laptop where the suite is meant to be the thing a session runs before committing.
LOCAL_CORES = 2


def build(name: str = "holdout-silver", *, cores: int = LOCAL_CORES) -> SparkSession:
    """A session with Delta's catalog and extensions, and nothing else configured.

    `configure_spark_with_delta_pip` is Delta's own helper: it names the jar coordinates that
    match the installed `delta-spark`, so the pairing is the package's statement rather than a
    version this repository would have to keep in step by hand.
    """
    builder = (
        SparkSession.builder.appName(name)
        .master(f"local[{cores}]")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        # The UI is a port nobody looks at during a test run, and binding it makes two sessions
        # on one machine fight over 4040.
        .config("spark.ui.enabled", "false")
        # A local build writes small tables; the default 200 shuffle partitions turn a
        # three-row join into 200 empty files.
        .config("spark.sql.shuffle.partitions", str(cores))
    )
    return configure_spark_with_delta_pip(builder).getOrCreate()


def sessions(name: str = "holdout-silver") -> Iterator[SparkSession]:
    """A session that stops when the caller is done with it. For a fixture or a `with`."""
    spark = build(name)
    try:
        yield spark
    finally:
        spark.stop()
