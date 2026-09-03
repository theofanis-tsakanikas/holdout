"""Silver, built against local Delta, with the quarantine non-empty on planted bad data.

**This is `T010`'s `stop_at`, and it is the only file in this repository that starts a JVM.**
Every test here carries the `silver` mark, so `make test` deselects it and `make silver` runs it
after `uv sync --extra spark` — 713 MB and a Java runtime that thirteen CI jobs do not pay for.

**A missing engine fails this file loudly.** There is no `importorskip` anywhere below, and
`tests/boundary/test_the_engine_is_never_skipped.py` refuses one: a skipped test looks exactly
like a passing one in a summary line, and an engine in an optional group is precisely the
condition under which somebody reaches for a skip.

**One session for the file.** Bringing Spark up is 3.6s warm and 50.9s the first time on a
machine whose Ivy cache is empty, measured on macOS arm64 with Java 17; a session per test would
pay that per test and buy nothing, because nothing here mutates the session.

**And one of these tests was wrong first, in the family this branch spent the day filing.** The
planted bad batch was written with Spark's own writer, which makes a **directory**, and
`spark.read.parquet` over a bronze table does not descend into one — so four bad rows sat in
`pos_lines/planted.parquet/` and the build read none of them. The assertion said *at least four
quarantined* and got zero, which is the assertion doing its job. **Written as `>= 0` it would
have passed over nothing**, which is the third instance in this repository of a check reporting
success over an empty population — after `ops/figures.py`'s instrument that raises rather than
returning a smaller number, and the four tests in `tests/pipelines/test_bulk_load.py` that
needed planting to reveal. `docs/FINDINGS.md` carries them; this one is recorded where it
happened.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from corpus.world import events as world_events
from corpus.world import prepare
from corpus.world.events import PosLine, ShelfDay
from pipelines.ingest import bulk, erp
from pipelines.silver import expectations, session, tables
from pipelines.silver.build import BronzeMissingError, build, read_bronze
from pyspark.sql import functions as sf

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pyspark.sql import DataFrame, SparkSession

pytestmark = pytest.mark.silver

SEED = "silver"
DAY = "2025-09-02"


@pytest.fixture(scope="module")
def spark() -> Iterator[SparkSession]:
    yield from session.sessions("holdout-silver-tests")


@pytest.fixture(scope="module")
def bronze(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One bronze directory for the file: the drops, the history, and one load over both."""
    root = tmp_path_factory.mktemp("estate")
    run = prepare("W6", seed=SEED, scale="smoke")
    erp.export(run, root / "landing", day=date.fromisoformat(DAY))
    erp.history(run, root / "landing")
    result = bulk.load(
        root / "landing",
        root / "bronze",
        arrived_at=datetime(2026, 9, 3, 9, 0),  # noqa: DTZ001 — the corpus is naive on purpose
    )
    assert result.files > 0, "the load moved nothing, so every assertion below would be vacuous"
    return root / "bronze"


@pytest.fixture(scope="module")
def silver(spark: SparkSession, bronze: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("silver")
    counts = build(spark, bronze, out)
    assert counts["sales"] > 0
    return out


def _rows(spark: SparkSession, table: Path) -> DataFrame:
    return spark.read.format("delta").load(str(table))


# ------------------------------------------------------------------ it builds


def test_silver_builds_against_local_delta(spark: SparkSession, silver: Path) -> None:
    """Five tables, written as Delta and read back by the engine that wrote them."""
    for name in ("sales", "price_displayed", "shelf_state", "reference", "quarantine"):
        assert (silver / name / "_delta_log").is_dir(), f"{name} is not a Delta table"
        _rows(spark, silver / name).count()


def test_spark_reads_the_parquet_this_repository_wrote_by_hand(
    spark: SparkSession, silver: Path
) -> None:
    """The third reader of `corpus/world/parquet.py`'s output, and the one the estate uses.

    The history in bronze is the corpus's Parquet, written with the standard library and never
    touched by a Parquet engine; pyarrow reads it in `tests/corpus/`. **Spark is a different
    implementation again**, and `sales` existing at the corpus's own count is that check.
    """
    run = prepare("W6", seed=SEED, scale="smoke")
    produced = sum(1 for event in world_events(run) if isinstance(event, PosLine))
    assert _rows(spark, silver / "sales").count() == produced


def test_a_bronze_table_that_is_not_there_is_refused(spark: SparkSession, tmp_path: Path) -> None:
    """An absent table is not an empty one: it would build a clean silver and report success."""
    with pytest.raises(BronzeMissingError, match="pos_lines"):
        read_bronze(spark, tmp_path)


# ----------------------------------------------------- quarantine, not drop


def test_planted_bad_rows_are_quarantined_by_name_and_absent_from_the_table(
    spark: SparkSession, bronze: Path, tmp_path: Path
) -> None:
    """`stop_at`: the quarantine is non-empty on planted bad data, and says which rule refused.

    Four rows, each breaking one declared expectation, written into bronze as an extra part
    file — which is what a real bad batch looks like: it arrives beside the good ones rather
    than replacing them.
    """
    lines = spark.read.parquet(str(bronze / "pos_lines"))
    good = lines.limit(1).collect()[0].asDict()

    def planted(**changes: object) -> dict[str, object]:
        row = dict(good)
        row.update(changes)
        return row

    bad = spark.createDataFrame(
        [
            planted(transaction_id="ZERO-QTY", line_no=1, qty=0, line_total_cents=0),
            planted(transaction_id="NO-PRICE", line_no=1, unit_price_cents=0, line_total_cents=0),
            planted(transaction_id="BAD-TOTAL", line_no=1, line_total_cents=1),
            planted(transaction_id="", line_no=99),
        ],
        schema=lines.schema,
    )
    # **Written as a part file beside the good ones, not as a nested directory.** Spark's
    # writer produces a directory, and `spark.read.parquet` over a bronze table does not descend
    # into one — the first version of this test planted four bad rows the build never saw and
    # asserted a quarantine of zero. A bad batch arrives as another file in the table.
    staged = tmp_path / "staged"
    bad.coalesce(1).write.parquet(str(staged), mode="overwrite")
    part = next(staged.glob("part-*.parquet"))
    planted_at = bronze / "pos_lines" / "planted.parquet"
    shutil.copyfile(part, planted_at)
    try:
        counts = build(spark, bronze, tmp_path / "silver")
        quarantine = _rows(spark, tmp_path / "silver" / "quarantine")
        refused = {
            row["business_key"]: row["expectation"]
            for row in quarantine.filter("source_table = 'sales'").collect()
        }
        assert counts["quarantine"] >= 4
        assert refused["ZERO-QTY|1"] == "qty_positive"
        assert refused["NO-PRICE|1"] == "price_positive"
        assert refused["BAD-TOTAL|1"] == "line_total_is_the_arithmetic"
        assert refused["|99"] == "transaction_id_present"

        sold = _rows(spark, tmp_path / "silver" / "sales")
        planted_ids = {"ZERO-QTY", "NO-PRICE", "BAD-TOTAL", ""}
        surviving = {
            row["transaction_id"] for row in sold.select("transaction_id").distinct().collect()
        }
        assert not (planted_ids & surviving), "a refused row reached the table it was refused from"
    finally:
        # Spark writes a *directory* of part files, not a file — which is why this is `rmtree`
        # and why the first version of this cleanup raised PermissionError on a path it had
        # just written itself.
        planted_at.unlink(missing_ok=True)


def test_a_row_whose_condition_is_null_is_quarantined_rather_than_lost(
    spark: SparkSession,
) -> None:
    """`col > 0` is NULL where `col` is null, and `filter` drops nulls silently.

    This is the one place the mechanism could lose exactly the rows it exists to keep, so it is
    tested on a frame built for it rather than on the corpus, which offers no nulls.
    """
    frame = spark.createDataFrame([("a", 5), ("b", None)], "id string, qty int")
    kept, quarantined = expectations.apply(
        frame,
        [expectations.Expectation("qty_positive", sf.col("qty") > 0, "a sale of nothing")],
        table="probe",
        business_key=("id",),
    )
    assert [row["id"] for row in kept.collect()] == ["a"]
    assert [(row["business_key"], row["expectation"]) for row in quarantined.collect()] == [
        ("b", "qty_positive")
    ]


def test_a_table_with_no_expectations_is_refused(spark: SparkSession) -> None:
    """A quarantine that could never be non-empty is a health metric that reports health."""
    frame = spark.createDataFrame([("a",)], "id string")
    with pytest.raises(ValueError, match="declares no expectations"):
        expectations.apply(frame, [], table="probe", business_key=("id",))


# ------------------------------------------- the stock-out, derived rather than copied


def test_silver_marks_the_same_store_days_the_corpus_did(spark: SparkSession, silver: Path) -> None:
    """Two independent answers to *did this shelf empty*, and they are compared rather than shared.

    Silver derives it from the movements — a store-day that **closed at zero** — and never reads
    `stocked_out_from_hour`, which is the corpus's own marking. The corpus computed its answer
    while simulating; silver computed its answer from what the till and the stock count emitted.
    """
    run = prepare("W6", seed=SEED, scale="smoke")
    corpus_marked = {
        (event.store_id, event.sku_id, event.business_date)
        for event in world_events(run)
        if isinstance(event, ShelfDay) and event.stocked_out_from_hour is not None
    }
    derived = {
        (row["store_id"], row["sku_id"], row["business_date"])
        for row in _rows(spark, silver / "shelf_state").filter("emptied").collect()
    }
    assert derived == corpus_marked
    assert len(derived) > 100, f"only {len(derived)} store-days emptied; the check is thin"


def test_the_derived_hour_is_a_lower_bound_and_the_gap_is_published(
    spark: SparkSession, silver: Path
) -> None:
    """`last_sale_hour` cannot exceed the hour the shelf actually emptied, and usually is earlier.

    The last unit can leave without a sale — it expires, or it is thrown away — so an hour
    derived from receipts is a bound rather than the moment. **The gap is measured rather than
    assumed away**, and printed, because a bound whose slack nobody has looked at is a bound
    nobody can use.
    """
    run = prepare("W6", seed=SEED, scale="smoke")
    truth = {
        (event.store_id, event.sku_id, event.business_date): event.stocked_out_from_hour
        for event in world_events(run)
        if isinstance(event, ShelfDay) and event.stocked_out_from_hour is not None
    }
    gaps: Counter[int] = Counter()
    for row in _rows(spark, silver / "shelf_state").filter("emptied").collect():
        marked = truth[(row["store_id"], row["sku_id"], row["business_date"])]
        assert row["last_sale_hour"] is not None
        assert row["last_sale_hour"] <= marked, (row["store_id"], row["sku_id"], marked)
        gaps[marked - row["last_sale_hour"]] += 1
    print(f"\n  hours between the last sale and the marked stock-out, over {sum(gaps.values())}:")
    for gap, count in sorted(gaps.items()):
        print(f"    +{gap}h  {count}")
    assert gaps[0] > 0, "the bound is never tight, which would mean it is measuring something else"


# ------------------------------------------- the declarations, run by the engine


def test_the_declarations_are_run_by_the_engine_not_only_read(bronze: Path, tmp_path: Path) -> None:
    """`spark-pipelines run` over `pipeline.py`, and all four flows must reach COMPLETED.

    **This test exists because a reviewer asked which of two things was true** — that the
    declarations cannot be run locally, or that they can and nobody had. It was the second. The
    engine builds the graph, orders it, and materialises every view; nothing here reads the
    decorators and agrees they look right.

    **The module is copied by path and never imported.** `pipeline.py` raises
    `GRAPH_ELEMENT_DEFINED_OUTSIDE_OF_DECLARATIVE_PIPELINE` on import, so a test that reached it
    through `import` could not exist — which is the same fact the file's own docstring carries.

    A pipeline spec's `configuration:` block sets **runtime** config only. `spark.sql.extensions`
    is static and is refused there with `CANNOT_MODIFY_STATIC_CONFIG`, so this spec sets neither
    it nor the Delta catalog: the engine writes its own storage, and the Delta configuration
    `build.py` needs is a property of *our* session rather than of a pipeline run.
    """
    project = tmp_path / "project"
    (project / "transformations").mkdir(parents=True)
    declarations = Path(__file__).resolve().parents[2] / "pipelines" / "silver" / "pipeline.py"
    shutil.copyfile(declarations, project / "transformations" / "pipeline.py")
    (project / "spark-pipeline.yml").write_text(
        "\n".join(
            [
                "name: holdout-silver",
                f"storage: file://{project / 'storage'}",
                "configuration:",
                f'  holdout.bronze: "{bronze}"',
                "libraries:",
                "  - glob:",
                "      include: transformations/**",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
    # **The console script, not `python -m pyspark.pipelines.cli`.** The module entry point
    # reaches the CLI without the launcher that starts a Spark Connect server, and the run dies
    # with `ONLY_SUPPORTED_WITH_SPARK_CONNECT` — measured, after the module form was tried first.
    cli = Path(sys.executable).parent / "spark-pipelines"
    assert cli.is_file(), f"{cli} is not there, so this test would be asserting about nothing"
    finished = subprocess.run(
        [str(cli), "run"],
        cwd=project,
        env=environment,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    output = finished.stdout + finished.stderr
    for flow in ("sales", "price_displayed", "shelf_state", "reference"):
        assert f"{flow} has COMPLETED" in output, output[-2000:]
    assert "Run is COMPLETED" in output
    assert finished.returncode == 0


# --------------------------------------------------- as of, on both of its axes


def test_a_cost_is_never_joined_before_the_erp_published_it(
    spark: SparkSession, silver: Path
) -> None:
    """The half of *as-of* that a single static snapshot could never have tested.

    Every joined cost must satisfy both axes: effective by the sale's moment **and** known by
    it. `known_from` exists only because the ERP dropped its master data several times during
    the day and the loader stamped each row with the drop that carried it.
    """
    sales = _rows(spark, silver / "sales")
    reference = _rows(spark, silver / "reference")
    priced = tables.cost_as_of(reference, sales, "event_ts")
    late = priced.filter("cost_known_from > event_ts OR cost_effective_from > event_ts")
    assert late.count() == 0
    assert priced.count() == sales.count(), "the as-of join changed the number of sales"


def test_a_sale_with_no_published_cost_keeps_a_null_rather_than_borrowing_one(
    spark: SparkSession, silver: Path
) -> None:
    """Doctrine rule 3 at a join: nothing is invented, so a row with no answer says so."""
    reference = _rows(spark, silver / "reference")
    before_everything = spark.createDataFrame(
        [("SKU-nothing-knows", datetime(2020, 1, 1, 12, 0))],  # noqa: DTZ001
        "sku_id string, event_ts timestamp",
    )
    priced = tables.cost_as_of(reference, before_everything, "event_ts")
    assert priced.count() == 1
    assert priced.collect()[0]["unit_cost_as_of"] is None
