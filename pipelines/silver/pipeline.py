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

**And it is executed by this repository's suite**, which is the half a reviewer asked for before
it existed. `tests/pipelines/test_silver.py` writes a pipeline spec, copies this file into it and
runs `spark-pipelines run`, then asserts that all four flows reach `COMPLETED` — the engine
building the graph, ordering it and materialising it, rather than a reader agreeing that the
decorators look right. `build.py` exercises the same functions directly, because a transformation
that can only be reached through a pipeline run is a transformation no unit test can hold.

**Bronze arrives as a configured path rather than a catalog table.** On the estate these read
`bronze.pos_lines` from Unity Catalog; locally there is no catalog, so the root comes from
`spark.conf` and the file says so rather than pretending the two are the same call. What is
identical either way is everything below the read: the transformations are `tables.py`'s, whole.

**And the expectations are missing on purpose.** On Databricks each of these would carry the
constraints `expectations.py` applies by hand, because Lakeflow has them and the open-source
framework does not. `pipelines/silver/__init__.py` carries the measurement.
"""

from __future__ import annotations

from pyspark import pipelines as dp

from pipelines.silver import tables

#: The Spark configuration key the spec sets to say where bronze is. There is no default: a
#: pipeline that fell back to a path would build silver out of whatever happened to be there,
#: which is doctrine rule 3 with a directory instead of a value.
BRONZE_ROOT = "holdout.bronze"


def _bronze(table: str):  # type: ignore[no-untyped-def]
    """One bronze table, from the root the spec configured. `spark` is injected by the engine."""
    root = spark.conf.get(BRONZE_ROOT)  # type: ignore[name-defined]  # noqa: F821
    if not root:
        raise ValueError(f"{BRONZE_ROOT} is not set, so this pipeline has no bronze to read")
    return spark.read.parquet(f"{root}/{table}")  # type: ignore[name-defined]  # noqa: F821


@dp.materialized_view(name="sales", comment="Receipt lines, deduplicated on the business key")
def sales_view():  # type: ignore[no-untyped-def]
    kept, _ = tables.sales(_bronze("pos_lines"))
    return kept


@dp.materialized_view(name="price_displayed", comment="What the shelf showed, from the ack")
def price_displayed_view():  # type: ignore[no-untyped-def]
    kept, _ = tables.price_displayed(_bronze("esl_acks"))
    return kept


@dp.materialized_view(name="shelf_state", comment="Whether the shelf emptied, from movements")
def shelf_state_view():  # type: ignore[no-untyped-def]
    sold, _ = tables.sales(_bronze("pos_lines"))
    kept, _ = tables.shelf_state(_bronze("shelf_days"), sold)
    return kept


@dp.materialized_view(
    name="reference",
    comment="Cost by effective_from and known_from; the product by its key, which has neither",
)
def reference_view():  # type: ignore[no-untyped-def]
    kept, _ = tables.reference(_bronze("cost_ledger"), _bronze("product_master"))
    return kept
