"""The bulk load, measured as two things agreeing rather than one thing running.

`TASKS.md`'s `stop_at` for T009 is *"when the bulk load writes what the lakehouse reads"*, and
that is a claim about agreement: what came out of the loader, **read by pyarrow**, must be what
the ERP exported, cell for cell, plus exactly the provenance the loader declares it adds.

pyarrow is the dev-group reader `corpus/world/parquet.py` is checked by, and it is doing the
same job here one layer up: nothing in this file asks our own code what it wrote.

What is asserted, and it is the shape `stop_at` asks for:

- every value equal to the drop's CSV cell parsed to its declared type, row for row;
- the schema equal in name, order, type **and** nullability — the declared columns, then the
  three provenance columns, and nothing else;
- rows equal to what the manifest declares;
- a second load moving zero files and leaving bronze byte-identical;
- a registered file byte-identical to the file that landed.
"""

from __future__ import annotations

import csv
import gzip
import json
from datetime import date, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from corpus.world import Run, prepare
from pipelines.ingest import bulk, erp

SEED = "holdout-w-0001"
DAY = date(2025, 9, 2)
ARRIVED = datetime(2026, 9, 3, 9, 0, 0)  # noqa: DTZ001 — the corpus is naive on purpose

_TYPES = {
    "string": pa.types.is_string,
    "int64": pa.types.is_int64,
    "double": pa.types.is_float64,
    "bool": pa.types.is_boolean,
    "date": pa.types.is_date32,
    "timestamp": pa.types.is_timestamp,
}


def _run() -> Run:
    return prepare("W6", seed=SEED, scale="smoke")


def _landed(tmp_path: Path, *, history: bool = True) -> tuple[Path, Path]:
    run = _run()
    landing, bronze = tmp_path / "landing", tmp_path / "bronze"
    erp.export(run, landing, day=DAY)
    if history:
        erp.history(run, landing)
    return landing, bronze


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


# ------------------------------------------------------- what the lakehouse reads


def test_every_value_in_bronze_is_the_value_the_erp_exported(tmp_path: Path) -> None:
    landing, bronze = _landed(tmp_path)
    result = bulk.load(landing, bronze, arrived_at=ARRIVED)

    checked = 0
    for entry in result.loaded:
        if entry.mode != "materialised":
            continue
        source = landing / entry.source
        manifest = json.loads((source.parent / erp.MANIFEST).read_text(encoding="utf-8"))
        declared = next(f for f in manifest["files"] if f["file"] == source.name)
        columns = declared["columns"]

        table = pq.read_table(bronze / entry.part)
        read_back = table.to_pydict()
        exported = _csv_rows(source)
        assert table.num_rows == len(exported) == declared["rows"]

        for index, row in enumerate(exported):
            for column in columns:
                text = row[column["name"]]
                expected: object
                if text == "" and column["optional"]:
                    expected = None
                elif column["type"] == "int64":
                    expected = int(text)
                elif column["type"] == "double":
                    expected = float(text)
                elif column["type"] == "date":
                    expected = date.fromisoformat(text)
                elif column["type"] == "timestamp":
                    expected = datetime.fromisoformat(text)
                else:
                    expected = text
                assert read_back[column["name"]][index] == expected, (
                    entry.part,
                    column["name"],
                    index,
                )
                checked += 1
    assert checked > 500, f"only {checked} cells were compared; this is not the smoke corpus"


def test_the_schema_is_the_declared_columns_then_the_provenance(tmp_path: Path) -> None:
    landing, bronze = _landed(tmp_path)
    result = bulk.load(landing, bronze, arrived_at=ARRIVED)

    for entry in result.loaded:
        if entry.mode != "materialised":
            continue
        source = landing / entry.source
        manifest = json.loads((source.parent / erp.MANIFEST).read_text(encoding="utf-8"))
        declared = next(f for f in manifest["files"] if f["file"] == source.name)
        schema = pq.read_schema(bronze / entry.part)

        names = [column["name"] for column in declared["columns"]]
        assert schema.names == [*names, "_source_file", "_exported_at", "_arrival_ts"]
        for column in declared["columns"]:
            field = schema.field(column["name"])
            assert _TYPES[column["type"]](field.type), (column, field.type)
            assert field.nullable is column["optional"], column


def test_the_provenance_is_the_drop_it_came_from_and_the_moment_it_arrived(
    tmp_path: Path,
) -> None:
    """A master-data row carries neither an event time nor an arrival of its own.

    `CLAUDE.md` requires bronze to carry both, so the loader adds the source's own statement of
    when it exported and its own of when it took the file — and nothing else. Two snapshots of
    a table that never changes are otherwise indistinguishable in one bronze table.
    """
    landing, bronze = _landed(tmp_path, history=False)
    result = bulk.load(landing, bronze, arrived_at=ARRIVED)
    exported_at = {
        drop.name: json.loads((drop / erp.MANIFEST).read_text(encoding="utf-8"))["exported_at"]
        for drop in erp.drop_directories(landing)
    }
    for entry in result.loaded:
        columns = pq.read_table(bronze / entry.part).to_pydict()
        drop = entry.source.split("/")[0]
        assert set(columns["_source_file"]) == {entry.source}
        assert set(columns["_exported_at"]) == {datetime.fromisoformat(exported_at[drop])}
        assert set(columns["_arrival_ts"]) == {ARRIVED}


def test_a_registered_file_is_the_file_that_landed(tmp_path: Path) -> None:
    """Byte for byte: bronze is the source's shape, and this one already had it."""
    landing, bronze = _landed(tmp_path)
    result = bulk.load(landing, bronze, arrived_at=ARRIVED)
    registered = [entry for entry in result.loaded if entry.mode == "registered"]
    assert {entry.table for entry in registered} == {
        "pos_lines",
        "esl_acks",
        "shelf_days",
        "price_decisions",
    }
    for entry in registered:
        assert (bronze / entry.part).read_bytes() == (landing / entry.source).read_bytes()
        assert pq.read_table(bronze / entry.part).num_rows == entry.rows


def test_the_seal_and_the_reference_tables_of_the_history_are_not_sources(
    tmp_path: Path,
) -> None:
    """Declared by nothing, so loaded by nothing — including a `.parquet` planted by hand."""
    landing, bronze = _landed(tmp_path)
    (landing / erp.HISTORY / "not_declared.parquet").write_bytes(b"PAR1 not a real file")
    result = bulk.load(landing, bronze, arrived_at=ARRIVED)
    sources = {entry.source for entry in result.loaded}
    assert not [source for source in sources if source.endswith("not_declared.parquet")]
    assert not [source for source in sources if "truth.sealed" in source]
    assert not (bronze / "store_master" / "history-store_master.parquet").exists()
    for entry in result.loaded:
        if entry.table == "store_master":
            assert "arm" not in pq.read_schema(bronze / entry.part).names


# --------------------------------------------------------------- incremental


def test_a_second_load_moves_nothing(tmp_path: Path) -> None:
    landing, bronze = _landed(tmp_path)
    first = bulk.load(landing, bronze, arrived_at=ARRIVED)
    before = _tree(bronze)

    again = bulk.load(landing, bronze, arrived_at=datetime(2026, 9, 4, 9, 0))  # noqa: DTZ001
    assert again.files == 0
    assert again.rows == 0
    assert len(again.skipped) == first.files
    assert _tree(bronze) == before, "a second load rewrote something"


def test_a_later_drop_is_the_only_thing_a_second_load_takes(tmp_path: Path) -> None:
    """What incremental means here: the checkpoint, and nothing cleverer than it."""
    run = _run()
    landing, bronze = tmp_path / "landing", tmp_path / "bronze"
    erp.export(run, landing, day=DAY, schedule=erp.Schedule((7, 11)))
    first = bulk.load(landing, bronze, arrived_at=ARRIVED)
    assert first.files == 2 * len(erp.EXPORTED)

    erp.export(run, landing, day=DAY, schedule=erp.Schedule((7, 11, 15, 19)))
    second = bulk.load(landing, bronze, arrived_at=ARRIVED)
    assert second.files == 2 * len(erp.EXPORTED)
    assert {entry.source.split("/")[0] for entry in second.loaded} == {"drop=002", "drop=003"}


def test_a_path_whose_bytes_changed_is_refused_rather_than_loaded_twice(
    tmp_path: Path,
) -> None:
    """A re-export over a drop that was already taken: manifest and all, consistently.

    The file agrees with its manifest, so the digest check passes and the **checkpoint** is
    what refuses. Loading it again would put drop=000 into bronze twice, with two different
    contents under one name, and nothing downstream could tell that had happened.
    """
    landing, bronze = _landed(tmp_path, history=False)
    bulk.load(landing, bronze, arrived_at=ARRIVED)

    drop = next(iter(erp.drop_directories(landing)))
    rewritten = drop / "cost_ledger.csv.gz"
    rows = _csv_rows(rewritten)
    with gzip.open(rewritten, "wt", newline="", encoding="utf-8") as handle:
        out = csv.writer(handle)
        out.writerow(rows[0].keys())
        for row in rows[:-1]:
            out.writerow(row.values())
    manifest = json.loads((drop / erp.MANIFEST).read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        if entry["table"] == "cost_ledger":
            entry["sha256"] = bulk.digest_of(rewritten)
            entry["rows"] = len(rows) - 1
    (drop / erp.MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(bulk.BulkLoadError, match="A drop is immutable"):
        bulk.load(landing, bronze, arrived_at=ARRIVED)


def test_a_file_that_does_not_match_its_manifest_is_refused_before_it_is_read(
    tmp_path: Path,
) -> None:
    """The other refusal, and it fires on the first load rather than the second."""
    landing, bronze = _landed(tmp_path, history=False)
    drop = next(iter(erp.drop_directories(landing)))
    path = drop / "store_master.csv.gz"
    path.write_bytes(gzip.compress(b"store_id\nS-000\n"))
    with pytest.raises(bulk.BulkLoadError, match="not the one that was exported"):
        bulk.load(landing, bronze, arrived_at=ARRIVED)


# ------------------------------------------------------------------ refusals


def test_a_file_that_is_not_what_its_manifest_says_is_refused(tmp_path: Path) -> None:
    landing, bronze = _landed(tmp_path, history=False)
    drop = next(iter(erp.drop_directories(landing)))
    manifest = json.loads((drop / erp.MANIFEST).read_text(encoding="utf-8"))
    manifest["files"][0]["sha256"] = "0" * 64
    (drop / erp.MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(bulk.BulkLoadError, match="not the one that was exported"):
        bulk.load(landing, bronze, arrived_at=ARRIVED)


def test_a_manifest_that_names_a_type_nobody_declared_is_refused(tmp_path: Path) -> None:
    landing, bronze = _landed(tmp_path, history=False)
    drop = next(iter(erp.drop_directories(landing)))
    manifest = json.loads((drop / erp.MANIFEST).read_text(encoding="utf-8"))
    manifest["files"][0]["columns"][0]["type"] = "varchar"
    (drop / erp.MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(bulk.BulkLoadError, match="'varchar'"):
        bulk.load(landing, bronze, arrived_at=ARRIVED)


def test_a_value_that_is_not_its_declared_type_names_the_line_and_the_column(
    tmp_path: Path,
) -> None:
    """The whole reason a drop carries a schema: text cannot refuse itself."""
    landing, bronze = _landed(tmp_path, history=False)
    drop = next(iter(erp.drop_directories(landing)))
    path = drop / "cost_ledger.csv.gz"
    rows = _csv_rows(path)
    rows[0]["unit_cost_cents"] = "a lot"
    with gzip.open(path, "wt", newline="", encoding="utf-8") as handle:
        out = csv.writer(handle)
        out.writerow(rows[0].keys())
        for row in rows:
            out.writerow(row.values())
    manifest = json.loads((drop / erp.MANIFEST).read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        if entry["table"] == "cost_ledger":
            entry["sha256"] = bulk.digest_of(path)
    (drop / erp.MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(bulk.BulkLoadError, match="line 2: column unit_cost_cents"):
        bulk.load(landing, bronze, arrived_at=ARRIVED)


def test_a_manifest_naming_a_file_that_is_not_there_is_refused(tmp_path: Path) -> None:
    landing, bronze = _landed(tmp_path)
    (landing / erp.HISTORY / "pos_lines.parquet").unlink()
    with pytest.raises(bulk.BulkLoadError, match="is not there"):
        bulk.load(landing, bronze, arrived_at=ARRIVED)


def test_the_load_log_records_every_file_and_never_rewrites_one(tmp_path: Path) -> None:
    landing, bronze = _landed(tmp_path, history=False)
    first = bulk.load(landing, bronze, arrived_at=ARRIVED)
    erp.export(_run(), landing, day=DAY, schedule=erp.Schedule((7, 11, 15, 19, 22, 23)))
    second = bulk.load(landing, bronze, arrived_at=ARRIVED)

    lines = [
        json.loads(line)
        for line in (bronze / bulk.LOAD_LOG).read_text(encoding="utf-8").splitlines()
    ]
    assert len(lines) == first.files + second.files
    assert [entry["source"] for entry in lines[: first.files]] == [
        entry.source for entry in first.loaded
    ]
    assert {entry["mode"] for entry in lines} == {"materialised"}
