"""The Spark Declarative Pipelines definitions. **Not importable, and that is the point.**

`spark-pipelines run` reads this file; nothing else may. A decorator here registers a node in a
pipeline graph, and a graph only exists inside a run:

    @dp.materialized_view(name="probe") outside `spark-pipelines run`
      -> PySparkRuntimeError [GRAPH_ELEMENT_DEFINED_OUTSIDE_OF_DECLARATIVE_PIPELINE]

Measured on `pyspark 4.2.0`, which is why the transformations live in `tables.py` and this file
is eight lines of declaration over them. **A repository whose logic lived in the decorators
would have logic no test could reach** — the decorator refuses to run, so the function under it
never exists as anything a test can call.

What this file is evidence of, and what it is not
-------------------------------------------------
**It is the same code Databricks runs.** `CLAUDE.md` chose Spark Declarative Pipelines for this
layer, the framework is open source from Spark 4.1, and these declarations are portable to
Lakeflow without an edit.

**It is not executed by this repository's suite.** `tests/pipelines/test_silver.py` exercises
`build.py`, which calls the same functions against local Delta — that is `TASKS.md`'s `stop_at`,
and it is honest about which half it proves. Running `spark-pipelines run` locally needs a
pipeline spec, a catalog and a warehouse directory, and none of it is written here: **the
declarations are checked by being read, not by being run**, and that is a smaller claim than the
one this file's existence might suggest.

**And the expectations are missing on purpose.** On Databricks each of these would carry the
constraints `expectations.py` applies by hand, because Lakeflow has them and the open-source
framework does not. `pipelines/silver/__init__.py` carries the measurement.
"""

from __future__ import annotations

import pyspark.pipelines as dp
from pyspark.sql import SparkSession

from pipelines.silver import tables

spark = SparkSession.active()


@dp.materialized_view(name="sales", comment="Receipt lines, deduplicated on the business key")
def sales_view():  # type: ignore[no-untyped-def]
    kept, _ = tables.sales(spark.read.table("bronze.pos_lines"))
    return kept


@dp.materialized_view(name="price_displayed", comment="What the shelf showed, from the ack")
def price_displayed_view():  # type: ignore[no-untyped-def]
    kept, _ = tables.price_displayed(spark.read.table("bronze.esl_acks"))
    return kept


@dp.materialized_view(name="shelf_state", comment="Whether the shelf emptied, from movements")
def shelf_state_view():  # type: ignore[no-untyped-def]
    sold, _ = tables.sales(spark.read.table("bronze.pos_lines"))
    kept, _ = tables.shelf_state(spark.read.table("bronze.shelf_days"), sold)
    return kept


@dp.materialized_view(name="reference", comment="Cost by effective_from and known_from")
def reference_view():  # type: ignore[no-untyped-def]
    kept, _ = tables.reference(spark.read.table("bronze.cost_ledger"))
    return kept
