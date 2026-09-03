"""The Parquet target, read back by an implementation nobody here wrote.

`corpus/world/parquet.py` is stdlib and ours, for the reason its docstring gives: pyarrow is
34.2 MiB downloaded and 122 MB installed to lay out a few million fixed-width values. What
that buys has to be paid for, and this file is the payment — **pyarrow is a development
dependency and every assertion below is made through it.**

`CLAUDE.md`: *a guard tested by its author is tested in the shape the guard already handles.*
A reader written in this repository would have agreed with the writer in this repository about
a `LogicalType` union member that said `TIME` where `TIMESTAMP` was meant, and the file would
have been valid Parquet the whole time. `test_a_timestamp_is_a_timestamp_and_it_is_naive` is
that bug, kept.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from corpus.world import (
    REFERENCE_TABLES,
    STREAMS,
    Format,
    Run,
    count,
    events,
    prepare,
    write,
)
from corpus.world.events import STREAM_TYPES, field_names, stream_of
from corpus.world.parquet import (
    Column,
    Kind,
    ParquetWriter,
    SchemaError,
    columns_for,
    write_table,
)

SEED = "parquet"


def _written(tmp_path: Path, world: str = "W6") -> tuple[Run, dict[str, int]]:
    run = prepare(world, seed=SEED, scale="smoke")
    counts = write(run, tmp_path, fmt=Format.PARQUET)
    return run, counts


# --------------------------------------------------------------- a whole world


def test_pyarrow_reads_every_table_a_written_world_produces(tmp_path: Path) -> None:
    run, counts = _written(tmp_path)
    for stream in STREAMS:
        table = pq.read_table(tmp_path / f"{stream}.parquet")
        assert table.num_rows == counts[stream] > 0
    for reference in REFERENCE_TABLES:
        table = pq.read_table(tmp_path / f"{reference.name}.parquet")
        assert table.column_names == list(reference.header)
    assert pq.read_table(tmp_path / "store_master.parquet").num_rows == len(run.chain.stores)
    assert pq.read_table(tmp_path / "product_master.parquet").num_rows == len(run.chain.products)


def test_every_value_is_the_value_the_corpus_produced(tmp_path: Path) -> None:
    """Not row counts: every cell, in order, against the records the generator emitted.

    A world is a pure function of `(world, seed, scale)`, so the stream can be produced a
    second time and compared record by record. What is being checked is the whole path —
    dataclass to column to page to footer to pyarrow — and the only thing the two sides share
    is the corpus itself.
    """
    run, _ = _written(tmp_path)
    produced: dict[str, list[tuple[object, ...]]] = {stream: [] for stream in STREAMS}
    for event in events(run):
        produced[stream_of(event)].append(
            tuple(getattr(event, name) for name in field_names(event))
        )

    for stream in STREAMS:
        table = pq.read_table(tmp_path / f"{stream}.parquet")
        columns = table.to_pydict()
        names = list(columns)
        read_back = [
            tuple(columns[name][index] for name in names) for index in range(table.num_rows)
        ]
        # Two empty lists are equal, so the comparison says nothing until this does.
        assert produced[stream], f"{stream} produced no records to compare against"
        assert read_back == produced[stream], stream


def test_the_schema_is_the_dataclass(tmp_path: Path) -> None:
    _written(tmp_path)
    checked = 0
    for stream in STREAMS:
        record_type = STREAM_TYPES[stream]
        schema = pq.read_schema(tmp_path / f"{stream}.parquet")
        assert schema.names == list(field_names(record_type))
        for column in columns_for(record_type):
            field = schema.field(column.name)
            assert field.nullable is column.optional, f"{stream}.{column.name}"
            checked += 1
    # The population as a rule rather than a frozen count: a count written here is an
    # assertion needing its own measurement, and it goes stale the day a dataclass gains a
    # field. What it has to refuse is the loop that ran over nothing.
    expected = sum(len(field_names(STREAM_TYPES[stream])) for stream in STREAMS)
    assert checked == expected > 0, f"{checked} columns checked, {expected} exist"


def test_a_timestamp_is_a_timestamp_and_it_is_naive(tmp_path: Path) -> None:
    """The bug the independent reader found, kept as the test that would find it again.

    `union LogicalType`'s member 7 is `TIME` and its member 8 is `TIMESTAMP`. A file written
    with the first is structurally valid, self-consistent, and describes a different column —
    pyarrow reads `time64[us]` and every value survives, so nothing else notices.

    `tz is None` is the second half and it is `events.py`'s decision rather than this
    writer's: *"a markdown at 21:00 is 21:00 where the shop is"*. A UTC-adjusted timestamp
    would be asserting a zone nobody in the scenario has.
    """
    _written(tmp_path)
    field = pq.read_schema(tmp_path / "pos_lines.parquet").field("event_ts")
    assert pa.types.is_timestamp(field.type), field.type
    assert field.type.unit == "us"
    assert field.type.tz is None


def test_the_reference_tables_carry_types_rather_than_text(tmp_path: Path) -> None:
    """The CSV target writes `2025-09-01` and `''`; this one writes a date and a null.

    That difference is the whole reason the deferral named this branch: an empty cell in a CSV
    cannot be told from an absent value, and the loader in `pipelines/ingest/` is handed a
    declared type per column precisely because text cannot carry one.
    """
    _written(tmp_path)
    stores = pq.read_table(tmp_path / "store_master.parquet")
    assert pa.types.is_date32(stores.schema.field("opened_on").type)
    assert pa.types.is_float64(stores.schema.field("size_index").type)
    assert isinstance(stores.to_pydict()["opened_on"][0], date)

    ledger = pq.read_table(tmp_path / "cost_ledger.parquet")
    assert pa.types.is_timestamp(ledger.schema.field("effective_from").type)
    assert isinstance(ledger.to_pydict()["effective_from"][0], datetime)

    products = pq.read_table(tmp_path / "product_master.parquet")
    substitutes = products.to_pydict()["substitute_of"]
    assert products.schema.field("substitute_of").nullable
    assert None in substitutes, "no SKU substitutes nothing, so the null is untested"
    assert "" not in substitutes


def test_the_counts_do_not_move_with_the_format(tmp_path: Path) -> None:
    run = prepare("W5", seed=SEED, scale="smoke")
    as_parquet = write(run, tmp_path / "parquet", fmt=Format.PARQUET)
    as_csv = write(run, tmp_path / "csv", fmt="csv")
    assert as_parquet == as_csv == count(run)


def test_an_undeclared_format_is_refused_by_name(tmp_path: Path) -> None:
    run = prepare("W6", seed=SEED, scale="smoke")
    with pytest.raises(ValueError, match="unknown format 'orc'"):
        write(run, tmp_path, fmt="orc")


# ------------------------------------------------------------------ the writer


def test_a_null_in_a_required_column_is_refused_rather_than_defaulted(tmp_path: Path) -> None:
    """Doctrine rule 3 where a file format invites the opposite. A default is a lie."""
    columns = [Column("sku_id", Kind.STRING), Column("qty", Kind.INT64)]
    with pytest.raises(SchemaError, match="qty is required"):
        write_table(tmp_path / "x.parquet", columns, [("a", 1), ("b", None)])


def test_a_value_of_the_wrong_type_names_its_column(tmp_path: Path) -> None:
    columns = [Column("qty", Kind.INT64)]
    with pytest.raises(SchemaError, match="column qty is declared int64"):
        write_table(tmp_path / "x.parquet", columns, [("not a number",)])


def test_an_annotation_with_no_column_type_is_refused(tmp_path: Path) -> None:
    """A `BYTE_ARRAY` fallback would make every unknown type a string nobody declared."""

    @dataclass(frozen=True)
    class Odd:
        sku_id: str
        price: Decimal

    with pytest.raises(SchemaError, match=r"Odd\.price"):
        columns_for(Odd)


def test_a_file_with_no_columns_and_a_repeated_column_are_both_refused(tmp_path: Path) -> None:
    with pytest.raises(SchemaError, match="no columns"):
        ParquetWriter(tmp_path / "x.parquet", [])
    with pytest.raises(SchemaError, match="share a name"):
        ParquetWriter(tmp_path / "y.parquet", [Column("a", Kind.INT64), Column("a", Kind.STRING)])


def test_a_row_of_the_wrong_width_is_refused(tmp_path: Path) -> None:
    with (
        ParquetWriter(tmp_path / "x.parquet", [Column("a", Kind.INT64)]) as writer,
        pytest.raises(SchemaError, match="2 values for 1 columns"),
    ):
        writer.write((1, 2))


def test_an_empty_table_is_a_schema_with_no_rows(tmp_path: Path) -> None:
    """Not an empty file: a stream that produced nothing still says what it would have held."""
    path = tmp_path / "empty.parquet"
    assert write_table(path, [Column("a", Kind.INT64), Column("b", Kind.STRING)], []) == 0
    table = pq.read_table(path)
    assert table.num_rows == 0
    assert table.column_names == ["a", "b"]


@pytest.mark.parametrize("compress", [True, False])
def test_both_codecs_read_back_identically(tmp_path: Path, compress: bool) -> None:
    columns = [
        Column("text", Kind.STRING),
        Column("n", Kind.INT64),
        Column("x", Kind.DOUBLE),
        Column("flag", Kind.BOOL),
        Column("day", Kind.DATE),
        Column("moment", Kind.TIMESTAMP),
        Column("maybe", Kind.STRING, optional=True),
    ]
    rows = [
        (
            # A multibyte value on purpose: a BYTE_ARRAY length is bytes, not characters.
            f"caf\u00e9 {index}" if index % 2 else "",
            -index,
            index / 3,
            index % 3 == 0,
            date(2025, 9, 1),
            datetime(2025, 9, 1, 21, 0, index % 60, 250_000),  # noqa: DTZ001 — naive on purpose
            None if index % 4 else f"n{index}",
        )
        for index in range(37)
    ]
    path = tmp_path / f"codec-{compress}.parquet"
    with ParquetWriter(path, columns, row_group_rows=10, compress=compress) as writer:
        writer.write_rows(rows)
    table = pq.read_table(path)
    columns_read = table.to_pydict()
    assert [tuple(columns_read[c.name][i] for c in columns) for i in range(37)] == rows
    assert pq.ParquetFile(path).num_row_groups == 4


def test_a_column_that_is_entirely_absent_still_reads(tmp_path: Path) -> None:
    """Every definition level is zero, so the page holds levels and no values at all."""
    path = tmp_path / "nulls.parquet"
    write_table(path, [Column("maybe", Kind.STRING, optional=True)], [(None,)] * 9)
    assert pq.read_table(path).to_pydict() == {"maybe": [None] * 9}


def test_booleans_pack_past_the_byte_boundary(tmp_path: Path) -> None:
    """PLAIN booleans are bit-packed, so 8 is exactly where an off-by-one would first show."""
    path = tmp_path / "bits.parquet"
    flags = [index % 3 == 0 for index in range(21)]
    write_table(path, [Column("flag", Kind.BOOL)], [(flag,) for flag in flags])
    assert pq.read_table(path).to_pydict()["flag"] == flags
