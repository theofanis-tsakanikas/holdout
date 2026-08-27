"""Materialising a world: the four streams, the three reference tables, the manifest, the seal.

Nothing here is committed to the repository. A world is a pure function of `(world, seed,
scale)`, so it is regenerated rather than stored — which is the exact opposite of
`corpus/real/`, where the data is committed and digest-checked precisely because it *cannot*
be regenerated: it was collected by hand in shops by people who have never seen this
repository. Two corpora, two opposite rules, one reason each.
"""

from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path
from types import GeneratorType

from corpus.world import STREAMS, count, events, prepare, write
from corpus.world.events import field_names
from corpus.world.seal import SEAL_FILENAME

REFERENCE = ("store_master", "product_master", "cost_ledger")


def _rows(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_write_produces_every_stream_the_reference_tables_and_the_seal(tmp_path: Path) -> None:
    run = prepare("W6", seed="write", scale="smoke")
    counts = write(run, tmp_path)
    for stream in STREAMS:
        assert (tmp_path / f"{stream}.csv.gz").is_file()
        assert counts[stream] > 0
    for table in REFERENCE:
        assert (tmp_path / f"{table}.csv.gz").is_file()
    assert (tmp_path / SEAL_FILENAME).is_file()
    assert (tmp_path / "run.json").is_file()


def test_the_written_counts_are_the_counts(tmp_path: Path) -> None:
    """`count` and `write` must not be two different traversals that could disagree."""
    run = prepare("W5", seed="write", scale="smoke")
    written = write(run, tmp_path)
    assert written == count(run)
    for stream, number in written.items():
        assert len(_rows(tmp_path / f"{stream}.csv.gz")) == number


def test_the_csv_header_is_the_dataclass(tmp_path: Path) -> None:
    from corpus.world.events import EslAck, PosLine, PriceDecision, ShelfDay

    run = prepare("W6", seed="write", scale="smoke")
    write(run, tmp_path)
    for stream, record in zip(
        ("pos_lines", "esl_acks", "shelf_days", "price_decisions"),
        (PosLine, EslAck, ShelfDay, PriceDecision),
        strict=True,
    ):
        with gzip.open(tmp_path / f"{stream}.csv.gz", "rt", encoding="utf-8") as handle:
            assert next(csv.reader(handle)) == list(field_names(record))


def test_the_manifest_says_what_was_written(tmp_path: Path) -> None:
    run = prepare("W2", seed="write", scale="smoke")
    counts = write(run, tmp_path)
    manifest = json.loads((tmp_path / "run.json").read_text(encoding="utf-8"))
    assert manifest["world"] == "W2"
    assert manifest["seed"] == "write"
    assert manifest["scale"] == "smoke"
    assert manifest["counts"] == counts
    assert manifest["restricted_to_stores"] is None


def test_the_reference_tables_are_whole_even_under_a_restriction(tmp_path: Path) -> None:
    """A product master truncated to the stores you happened to generate is not one.

    The store master *is* restricted, because a store that was not generated has no events and
    listing it would invite a join that finds nothing. The two behave differently on purpose
    and this is where that decision is written down.
    """
    run = prepare("W6", seed="write", scale="smoke")
    wanted = [run.chain.stores[0].store_id, run.chain.stores[3].store_id]
    write(run, tmp_path, only_stores=wanted)

    assert [row["store_id"] for row in _rows(tmp_path / "store_master.csv.gz")] == wanted
    assert len(_rows(tmp_path / "product_master.csv.gz")) == len(run.chain.products)
    ledger = _rows(tmp_path / "cost_ledger.csv.gz")
    assert {row["sku_id"] for row in ledger} == {p.sku_id for p in run.chain.products}
    assert len(ledger) > len(run.chain.products), "no SKU's cost ever moved"

    manifest = json.loads((tmp_path / "run.json").read_text(encoding="utf-8"))
    assert manifest["restricted_to_stores"] == wanted


def test_the_store_master_carries_the_arm_it_was_assigned(tmp_path: Path) -> None:
    run = prepare("W6", seed="write", scale="smoke")
    write(run, tmp_path)
    rows = _rows(tmp_path / "store_master.csv.gz")
    assert {row["arm"] for row in rows} == {"control", "treatment"}
    for row in rows:
        assert row["arm"] == run.assignment[row["store_id"]].value


def test_an_abandoned_stream_seals_nothing(tmp_path: Path) -> None:
    """Half a world has no truth to tell, so a consumer that stops early gets no seal."""
    run = prepare("W6", seed="write", scale="smoke")
    stream = events(run, seal_into=tmp_path)
    assert isinstance(stream, GeneratorType)
    next(stream)
    stream.close()
    assert not (tmp_path / SEAL_FILENAME).exists()
