"""The ERP's successive drops: what makes two of them differ, and what they never carry.

The rule under test is the exporter's one sentence — *the extract at `T` carries every cost
step with `effective_from <= T`* — and the two things that follow from it: successive extracts
differ exactly where the corpus's ledger stepped, and a table with no time dimension produces
the same bytes every time.
"""

from __future__ import annotations

import csv
import gzip
import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from corpus.world import Run, prepare
from pipelines.ingest import erp

SEED = "holdout-w-0001"
#: The second day of the smoke corpus. Measured on this seed: three cost steps fall on it, at
#: 08:00, 09:00 and 17:00, so the drops at 11:00 and 19:00 each carry something the one before
#: them did not. `test_the_driven_day_has_something_to_carry` is what stops that going quiet.
DAY = date(2025, 9, 2)


def _run(scale: str = "smoke") -> Run:
    return prepare("W6", seed=SEED, scale=scale)


def _rows(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_the_driven_day_has_something_to_carry() -> None:
    """A day with no cost step is a real day and a demonstration on one shows nothing.

    `erp.py`'s docstring carries the fractions — at `harness` nine days in ten have nothing —
    and this is the assertion that the day these tests drive is not one of them. If the corpus
    moves under it, this fails here rather than making every drop below trivially equal.
    """
    steps = erp.cost_steps_on(_run(), DAY)
    assert len(steps) >= 2, f"{DAY} carries {len(steps)} cost steps; the drops cannot differ"


def test_successive_drops_differ_exactly_where_the_ledger_stepped(tmp_path: Path) -> None:
    run = _run()
    drops = erp.export(run, tmp_path, day=DAY)
    assert len(drops) == len(erp.DECLARED.hours)

    for drop in drops:
        ledger = _rows(drop.directory / "cost_ledger.csv.gz")
        visible = [
            step
            for product in run.chain.products
            for step in run.chain.cost_steps(product.sku_id)
            if step.effective_from <= drop.exported_at
        ]
        assert len(ledger) == len(visible)
        assert max(datetime.fromisoformat(row["effective_from"]) for row in ledger) <= (
            drop.exported_at
        )

    counts = [len(_rows(drop.directory / "cost_ledger.csv.gz")) for drop in drops]
    assert counts[-1] > counts[0], "the ledger never moved during the driven day"


def test_newly_visible_is_the_difference_and_the_exporter_states_it(tmp_path: Path) -> None:
    """The source declares what became visible. A loader working it out would be change capture."""
    run = _run()
    drops = erp.export(run, tmp_path, day=DAY)
    counts = [len(_rows(drop.directory / "cost_ledger.csv.gz")) for drop in drops]
    for index, drop in enumerate(drops[1:], start=1):
        declared = next(f.newly_visible for f in drop.files if f.table == "cost_ledger")
        assert declared == counts[index] - counts[index - 1]
    assert drops[0].newly_visible == 0, "the first drop has no predecessor to be newer than"


def test_a_table_with_no_time_dimension_is_the_same_extract_every_time(tmp_path: Path) -> None:
    drops = erp.export(_run(), tmp_path, day=DAY)
    for table in ("store_master", "product_master"):
        digests = {next(f.digest for f in drop.files if f.table == table) for drop in drops}
        assert len(digests) == 1, f"{table} changed during a day in which nothing changes it"


def test_the_export_withholds_the_arm(tmp_path: Path) -> None:
    """An ERP does not know which stores are in an experiment's control group.

    A bronze master-data table carrying the arm would let a join take it from there instead of
    from the assignment written before the period opened, which is claim 3's door with a
    column through it.
    """
    run = _run()
    drops = erp.export(run, tmp_path, day=DAY)
    header = _rows(drops[0].directory / "store_master.csv.gz")[0].keys()
    assert "arm" not in header
    assert "store_id" in header
    assert {store.store_id for store in run.chain.stores} == {
        row["store_id"] for row in _rows(drops[0].directory / "store_master.csv.gz")
    }


def test_the_manifest_declares_every_file_it_wrote(tmp_path: Path) -> None:
    drops = erp.export(_run(), tmp_path, day=DAY)
    for drop in drops:
        manifest = json.loads((drop.directory / erp.MANIFEST).read_text(encoding="utf-8"))
        assert manifest["drop"] == drop.seq
        assert datetime.fromisoformat(manifest["exported_at"]) == drop.exported_at
        assert "not change capture" in manifest["demonstrates"]
        assert [entry["table"] for entry in manifest["files"]] == list(erp.EXPORTED)
        for entry, written in zip(manifest["files"], drop.files, strict=True):
            path = drop.directory / str(entry["file"])
            assert entry["rows"] == len(_rows(path)) == written.rows
            assert entry["sha256"] == written.digest
            assert [column["name"] for column in entry["columns"]] == list(_rows(path)[0].keys())
        types = {
            column["name"]: column["type"]
            for entry in manifest["files"]
            if entry["table"] == "cost_ledger"
            for column in entry["columns"]
        }
        assert types == {
            "sku_id": "string",
            "effective_from": "timestamp",
            "unit_cost_cents": "int64",
        }


def test_the_optional_column_is_declared_optional(tmp_path: Path) -> None:
    """`substitute_of` is written as `''` and can only be read back as absent if declared."""
    drops = erp.export(_run(), tmp_path, day=DAY)
    manifest = json.loads((drops[0].directory / erp.MANIFEST).read_text(encoding="utf-8"))
    columns = {
        column["name"]: column["optional"]
        for entry in manifest["files"]
        if entry["table"] == "product_master"
        for column in entry["columns"]
    }
    assert columns["substitute_of"] is True
    assert columns["sku_id"] is False


def test_exporting_the_same_drop_twice_produces_the_same_bytes(tmp_path: Path) -> None:
    """A digest must describe the content, not the second the file was written in.

    `gzip.open` stamps the current time into the header, so two exports of identical rows a
    second apart differ in bytes — and `bulk.load` refuses a path whose bytes changed, because a
    drop is immutable. **That passed on a fast machine and failed on a slow one**: CI run
    `33739596010` went red on `test_the_load_log_records_every_file_and_never_rewrites_one`, a
    test that had been green locally and on three earlier runs. The exporter now writes with
    `mtime=0`; this is the assertion that keeps it that way.
    """
    run = _run()
    first = erp.export(run, tmp_path / "a", day=DAY)
    second = erp.export(run, tmp_path / "b", day=DAY)
    for left, right in zip(first, second, strict=True):
        assert [f.digest for f in left.files] == [f.digest for f in right.files]
        for file in left.files:
            a = (left.directory / file.filename).read_bytes()
            b = (right.directory / file.filename).read_bytes()
            assert a == b, file.filename


def test_a_day_outside_the_corpus_is_refused(tmp_path: Path) -> None:
    run = _run()
    outside = run.scale.start_date + timedelta(days=run.scale.days)
    with pytest.raises(erp.ExportError, match="outside the corpus"):
        erp.export(run, tmp_path, day=outside)


@pytest.mark.parametrize(
    ("hours", "message"),
    [
        ((11,), "not several drops"),
        ((15, 11), "distinct and in order"),
        ((11, 11), "distinct and in order"),
        ((7, 25), "outside the day"),
    ],
)
def test_a_schedule_that_cannot_produce_successive_drops_is_refused(
    hours: tuple[int, ...], message: str
) -> None:
    with pytest.raises(erp.ExportError, match=message):
        erp.Schedule(hours)


def test_the_history_lands_in_its_own_directory(tmp_path: Path) -> None:
    """Because a world's Parquet output also carries the reference tables, arm and all."""
    run = _run()
    counts = erp.history(run, tmp_path)
    assert sum(counts.values()) > 0
    assert (tmp_path / erp.HISTORY / "pos_lines.parquet").is_file()
    assert (tmp_path / erp.HISTORY / "store_master.parquet").is_file()
    assert not (tmp_path / "pos_lines.parquet").exists()
