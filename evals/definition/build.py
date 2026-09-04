"""Build gold once, then hand the same rows to all three mechanisms.

**This module is the only place claim 5 touches an engine**, and it is deliberately not one of
the three mechanisms: it produces the *input* and collects the SQL's *answer*, and does no
arithmetic of its own. A helper that computed any part of the metric here would be a fourth
implementation that two of the three could quietly agree with.

Why this runs the whole pipeline rather than fixture rows
---------------------------------------------------------
`gold.decision_economics` and `gold.waste` are what the contract names as its sources, so the
honest input is what the pipeline actually materialises — including the sales it drops for having
no published cost. Fixture rows would let the comparison agree on data no engine ever produced,
and the SQL mechanism's whole value is that it was compiled and then executed rather than read.

The engine import is inside the function that needs it, for the reason
`tests/boundary/test_the_engine_is_never_skipped.py` gives: an absent extra must be loud at the
first test that asks for it and must not break collection everywhere else.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from pathlib import Path

    from holdout.contracts.model import Metric

#: The corpus this claim is proved on. `rehearsal` rather than `smoke` for the reason `T011`
#: measured: at smoke this corpus throws **nothing** away, so `gold.waste` is empty, the metric's
#: third term is a sum over no rows, and the full-outer join — the one place a one-sided cell can
#: be lost — never has a one-sided cell. A claim-5 proved at smoke would agree on two thirds of
#: its own definition.
SCALE = "rehearsal"
WORLD = "W6"
SEED = "definition"
DAY = "2025-09-02"


@contextmanager
def engine_noise_on_stderr() -> Iterator[None]:
    """Send everything the engine prints to stderr, so stdout carries only the report.

    **An eval's contract with `make gate-proof` is that its stdout is JSON.** `_run_eval` parses
    stdout and treats anything else as *does not run clean* — correctly, because an eval whose
    machine reading it cannot find is an eval that told it nothing.

    Claim 5 is the first eval to start a JVM and to run dbt, and both write to **stdout**: Spark's
    console progress bar and dbt's `OK created sql table model` lines. Neither goes through
    Python's `sys.stdout`, so `contextlib.redirect_stdout` does not reach them — the JVM and dbt
    write to file descriptor 1 directly. This redirects the descriptor itself and puts it back.

    Measured before it was written: with the engine talking, all three of claim 5's mutations
    reported `NOT-ARMED — no JSON on stdout: [Stage 238:====>  (32 + 2) / 50]`, which is the
    harness being exactly right about a cause that names nothing.
    """
    duplicate = os.dup(1)
    try:
        os.dup2(2, 1)
        yield
    finally:
        os.dup2(duplicate, 1)
        os.close(duplicate)


def gold_tables(root: Path) -> tuple[str, Any]:
    """Bronze, silver and gold from one world, and the session they live in.

    Returns the gold schema and the live Spark session — the caller stops it. Everything here is
    `pipelines/`'s own code: this eval builds nothing of its own, so a defect in the pipeline
    shows up as a claim-5 failure rather than being hidden by a private path.
    """
    from datetime import date, datetime

    from corpus.world import prepare
    from pipelines.gold import session as gold_session
    from pipelines.gold.build import build as build_gold
    from pipelines.ingest import bulk, erp
    from pipelines.silver.build import build as build_silver

    run = prepare(WORLD, seed=SEED, scale=SCALE)
    erp.export(run, root / "landing", day=date.fromisoformat(DAY))
    erp.history(run, root / "landing")
    loaded = bulk.load(
        root / "landing",
        root / "bronze",
        arrived_at=datetime(2026, 9, 4, 9, 0),  # noqa: DTZ001 — the corpus is naive on purpose
    )
    if not loaded.files:
        raise RuntimeError(
            "the bulk load moved no files, so every comparison below would be over empty tables "
            "and would agree for the wrong reason"
        )

    spark = gold_session.build(root)
    silver_counts = build_silver(spark, root / "bronze", root / "silver")
    if not silver_counts["sales"]:
        raise RuntimeError("silver built no sales, so gold would be empty and claim 5 vacuous")
    build_gold(spark, root / "silver", root=root)
    return gold_session.SCHEMA, spark


def rows(spark: Any, table: str) -> list[dict[str, Any]]:
    """One gold table as plain dictionaries, so no mechanism is handed an engine object.

    **Plain rows rather than a DataFrame on purpose.** A `DataFrame` would let a Python
    implementation reach for Spark's own aggregation, and the point of the pair is that neither
    of them is the engine.
    """
    return [row.asDict() for row in spark.table(table).collect()]


def sql_answer(spark: Any, schema: str, metric: Metric) -> dict[tuple[str, ...], int]:
    """The compiled SQL's answer, as the same integers the Python paths produce.

    Read out of the table dbt **materialised**, not recomputed here: the mechanism is the
    compiled artefact executed by the engine, and re-running its text from this module would make
    this file the mechanism instead.

    The one transformation is scale — the model emits a decimal in the contract's unit and the
    comparison is in the contract's canonical integer, which is `rounding.canonical_integer`
    applied to an already-rounded value. That is exact and it is the same call both Python paths
    end with, so it cannot hide a disagreement: it is a change of representation, not of value.
    """
    grain = list(metric.grain)
    answer: dict[tuple[str, ...], int] = {}
    for row in spark.table(f"{schema}.{metric.identifier}").collect():
        cell = tuple(str(row[column]) for column in grain)
        answer[cell] = metric.rounding.canonical_integer(row["metric_value"])
    return answer


def drop_counts(spark: Any, schema: str) -> tuple[int, int]:
    """How many priced sales gold kept, and how many it could not price.

    Published beside the comparison rather than inside it: it is a property of the pipeline, and
    folding it in would make a disagreement unable to say whether the definition or the pipeline
    was at fault.
    """
    priced = spark.table(f"{schema}.priced_sales").count()
    unpriced = spark.sql(
        f"select count(*) as n from {schema}.priced_sales where unit_cost_as_of is null"
    ).collect()[0]["n"]
    return int(unpriced), int(priced)


def economics_and_waste(
    spark: Any, schema: str
) -> tuple[Sequence[dict[str, Any]], Sequence[dict[str, Any]]]:
    """The contract's two declared sources, as the rows every mechanism reads."""
    return rows(spark, f"{schema}.decision_economics"), rows(spark, f"{schema}.waste")


#: The one cell this eval writes itself, and every number in it is chosen rather than found.
#:
#: **The corpus cannot exercise the contract's `rounding` block at all.** Gold builds
#: `price_paid` and `unit_cost_as_of` as `cents / 100` and `qty` is an integer, so every cell is
#: an exact number of cents — `bround(x, 2)` is the identity, and `half_even` and `half_up`
#: differ only on an exact half at the third decimal that this data never has. Measured by
#: planting: two mutations that round early and accumulate in float both **SURVIVED**, not
#: because the mechanisms agree by accident but because the arithmetic they break is not
#: present.
#:
#: So one cell is constructed, at the value where the two rounding rules part company:
#:
#:     row A   qty 1 · price 0.1000 · cost 0.0050   ->  0.0950
#:     row B   qty 1 · price 0.2000 · cost 0.1700   ->  0.0300
#:     exact                                            0.1250
#:     half_even 0.12   ·   half_up 0.13                the modes disagree
#:     rounding each row first                     ->   0.13   the first plant bites
#:     revenue accumulated in float 0.30000000000000004 -> 0.13   the second bites
#:
#: **One cell rather than a scattering**, because the smaller the construction the smaller the
#: part of the claim it weakens — and this one is sufficient: both surviving plants bite on it,
#: and it is the only value that makes them.
#:
#: **This is claim 4's practice, not a new one.** `evals/censoring/`'s `C2` asks its question
#: *"over every censored store-day the corpus produced and every one the sweep constructed"*,
#: and `CLAUDE.md` endorses it: the zero route is one *"which this corpus never produces and
#: `evals/censoring/` therefore constructs."* The form matters as much as the permission — the
#: check's question names both populations, so a reader sees which half the eval wrote.
CONSTRUCTED_CELL = ("ST-CONSTRUCTED", "2026-W01", "constructed")
CONSTRUCTED_ROWS = (("0.1000", "0.0050"), ("0.2000", "0.1700"))

#: The models that must be rebuilt after the cell is appended. Only these: a full `dbt run`
#: rebuilds `decision_economics` from `priced_sales` and the constructed cell disappears.
METRIC_MODELS = (
    "category_margin_per_store_week_v3",
    "units_sold_per_store_week_v1",
    "waste_value_per_store_week_v1",
)


def append_constructed_cell(spark: Any, schema: str, root: Path) -> None:
    """Append the constructed cell to gold and recompute the metric models over it.

    **Appended to `gold.decision_economics` rather than upstream, because sub-cent content
    cannot enter through `priced_sales`**: its cost is a bigint of cents, so anything arriving
    that way is exact to two places by construction. `decision_economics` is `decimal(18,4)` and
    is the contract's own declared source, so a cell written here is seen by **all three**
    mechanisms — the metric model reads `ref('decision_economics')`, and both Python paths read
    the same table. No mechanism sees a row the others do not.

    There is deliberately **no waste row** for this cell. The contract joins waste
    `full_outer_on_grain`, so a cell that traded and threw nothing away is a real shape, and
    giving it one would add a second constructed fact for no gain.
    """
    from pipelines.gold import models

    store, week, category = CONSTRUCTED_CELL
    values = ", ".join(
        f"('{store}', '{week}', '{category}', 1, cast({price} as decimal(18, 4)), "
        f"cast({cost} as decimal(18, 4)))"
        for price, cost in CONSTRUCTED_ROWS
    )
    spark.sql(f"insert into {schema}.decision_economics values {values}")
    models.run(spark, target_root=root, select=list(METRIC_MODELS))
