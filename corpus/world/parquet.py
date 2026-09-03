"""Parquet, written by hand, with nothing imported that is not in the standard library.

`docs/DECISIONS.md` deferred this on 2026-08-27 — *"`corpus/world/` writes gzipped CSV, not
Parquet"* — with an unlock condition naming **the S3 bulk load in T009, which is the first
thing that needs files on disk in the format the lakehouse reads.** That is this branch, so
the writer gains the target the deferral promised, beside the CSV one.

Why the engine is ours and not a library
----------------------------------------
The deferral's argument was that adding a Parquet engine to `corpus/` to write files nothing
reads would be *"a dependency bought for a screenshot"*. Something reads them now, so the
dependency would be earned — but it is still 34.2 MiB downloaded and **122 MB installed**
(measured with `uv pip install pyarrow` into an empty environment, 2026-09-03) against a
project whose runtime dependency set is `dependencies = []` and whose corpus is stdlib-only
apart from one `yaml.safe_load`. A 122 MB C++ library to lay out a few million fixed-width
values is a bad trade at any scale this repository runs.

So the format is written out here, and **the check that it is really Parquet comes from
somewhere else**: `tests/corpus/test_world_parquet.py` reads every file back with `pyarrow`,
which is a development dependency and which no runtime path in this repository imports.
`CLAUDE.md`'s rule about a guard tested by its author is the whole reason it is done that
way, and the rule earned its keep on the first run. **The `LogicalType` union member for a
timestamp is field 8; this file said 7, which is `TIME`.** The output was valid Parquet,
self-consistent and wrong: pyarrow reported `time64[us]` where a timestamp was meant, and a
reader written here would have agreed with the writer and said nothing.

What this writer does not implement, so nobody has to find out by reading it
---------------------------------------------------------------------------
One data page per column chunk, `PLAIN` values, `RLE` definition levels, GZIP or nothing.
**No** dictionary encoding, no `SNAPPY`, no statistics, no page index, no bloom filter, no
`INT96`, no nested or repeated fields, no `FIXED_LEN_BYTE_ARRAY`, no decimals — every column
is a flat primitive, required or optional. The format obliges a reader to cope with all of
that, and the two readers that matter here — pyarrow in the tests, Spark on the estate — do.
**A file this writer produces is readable; it is not what a tuned writer would produce**, and
if a scan ever needs statistics or dictionaries that is a reason to revisit the trade above
rather than to grow this file.

Nulls are the one place a format decision leaks into the corpus
---------------------------------------------------------------
A column is `REQUIRED` unless it is declared optional, and a null in a required column is
refused by name rather than written as a default. That is doctrine rule 3 in the one place a
file format invites the opposite: an empty CSV cell cannot be told apart from an absent
value, which is why `pipelines/ingest/bulk.py` is handed a declared type per column instead
of inferring one.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, fields
from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, cast, get_args, get_type_hints

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path
    from types import TracebackType

#: Both ends of a Parquet file. One that does not start and finish with it is not one.
MAGIC = b"PAR1"

#: Parquet counts days from this date, and microseconds from midnight on it.
EPOCH_DATE = date(1970, 1, 1)
EPOCH_DATETIME = datetime(1970, 1, 1)  # noqa: DTZ001 — naive on purpose; see `_plain`

# `parquet.thrift`, by number. Written out rather than imported, because importing them
# would mean importing a Parquet library, which is the thing this file exists to avoid.
_TYPE_BOOLEAN, _TYPE_INT32, _TYPE_INT64, _TYPE_DOUBLE, _TYPE_BYTE_ARRAY = 0, 1, 2, 5, 6
_CONVERTED_UTF8, _CONVERTED_DATE = 0, 6
_REPETITION_REQUIRED, _REPETITION_OPTIONAL = 0, 1
_ENCODING_PLAIN, _ENCODING_RLE = 0, 3
_CODEC_UNCOMPRESSED, _CODEC_GZIP = 0, 2
_PAGE_TYPE_DATA = 0
#: `union LogicalType`'s member ids. 7 is `TIME` and 8 is `TIMESTAMP` — see the docstring.
_LOGICAL_TIMESTAMP = 8
_TIME_UNIT_MICROS = 2

#: Thrift compact protocol type codes, for the subset used below.
_TC_TRUE, _TC_FALSE, _TC_I32, _TC_I64, _TC_BINARY, _TC_LIST, _TC_STRUCT = 1, 2, 5, 6, 8, 9, 12


class SchemaError(ValueError):
    """A column set that cannot be written, or a value that does not belong in one."""


class Kind(Enum):
    """The column types this corpus has. Adding one is a code change with a test."""

    STRING = "string"
    INT64 = "int64"
    DOUBLE = "double"
    BOOL = "bool"
    DATE = "date"
    TIMESTAMP = "timestamp"


_PHYSICAL: dict[Kind, int] = {
    Kind.STRING: _TYPE_BYTE_ARRAY,
    Kind.INT64: _TYPE_INT64,
    Kind.DOUBLE: _TYPE_DOUBLE,
    Kind.BOOL: _TYPE_BOOLEAN,
    Kind.DATE: _TYPE_INT32,
    Kind.TIMESTAMP: _TYPE_INT64,
}

#: How an annotation becomes a column. Deliberately narrow: an annotation this does not know
#: is a refusal rather than a `BYTE_ARRAY` fallback, because a column quietly written as text
#: is a schema nobody declared. `bool` is looked up before `int` because it is a subclass of
#: one, and a dict lookup by identity is what keeps that from mattering.
_FROM_ANNOTATION: dict[Any, Kind] = {
    str: Kind.STRING,
    bool: Kind.BOOL,
    int: Kind.INT64,
    float: Kind.DOUBLE,
    date: Kind.DATE,
    datetime: Kind.TIMESTAMP,
}


@dataclass(frozen=True, slots=True)
class Column:
    """One column: a name, a type, and whether a value may be absent."""

    name: str
    kind: Kind
    optional: bool = False


def columns_for(record_type: type) -> tuple[Column, ...]:
    """The columns of a dataclass, taken from its annotations rather than restated.

    The same argument `events.field_names` makes about the CSV header: a column list written
    by hand beside the dataclass is a second definition of the schema, and the day somebody
    inserts a field the two stop agreeing silently. `X | None` is the optional column.
    """
    hints = get_type_hints(record_type)
    columns: list[Column] = []
    for field in fields(cast(Any, record_type)):
        annotation = hints[field.name]
        optional = False
        if type(None) in get_args(annotation):
            inner = [arg for arg in get_args(annotation) if arg is not type(None)]
            if len(inner) != 1:
                raise SchemaError(
                    f"{record_type.__name__}.{field.name} is a union of {len(inner)} types; "
                    "a Parquet column holds one"
                )
            annotation, optional = inner[0], True
        kind = _FROM_ANNOTATION.get(annotation)
        if kind is None:
            raise SchemaError(
                f"{record_type.__name__}.{field.name} is {annotation!r}, which this writer "
                f"has no column type for. Declared types: {sorted(k.value for k in Kind)}."
            )
        columns.append(Column(field.name, kind, optional=optional))
    return tuple(columns)


class _Compact:
    """Thrift's compact protocol, write side, in the subset `parquet.thrift` needs.

    A field id is written as a **delta from the previous field of the same struct**, so the
    last id is a stack rather than a variable: a nested struct counts again from zero and its
    parent carries on where it left off. Getting that wrong produces a file that is
    structurally valid and describes a different schema, which is the failure the module
    docstring records.
    """

    def __init__(self) -> None:
        self.out = bytearray()
        self._last: list[int] = [0]

    def varint(self, value: int) -> None:
        while True:
            low = value & 0x7F
            value >>= 7
            if value:
                self.out.append(low | 0x80)
            else:
                self.out.append(low)
                return

    def _zigzag(self, value: int, bits: int) -> None:
        self.varint((value << 1) ^ (value >> (bits - 1)))

    def struct_begin(self) -> None:
        self._last.append(0)

    def struct_end(self) -> None:
        self.out.append(0x00)
        self._last.pop()

    def _field(self, field_id: int, type_code: int) -> None:
        delta = field_id - self._last[-1]
        if 1 <= delta <= 15:
            self.out.append((delta << 4) | type_code)
        else:
            self.out.append(type_code)
            self._zigzag(field_id, 16)
        self._last[-1] = field_id

    def boolean(self, field_id: int, value: bool) -> None:
        # A compact-protocol boolean lives in its field header and has no body.
        self._field(field_id, _TC_TRUE if value else _TC_FALSE)

    def i32(self, field_id: int, value: int) -> None:
        self._field(field_id, _TC_I32)
        self._zigzag(value, 32)

    def i64(self, field_id: int, value: int) -> None:
        self._field(field_id, _TC_I64)
        self._zigzag(value, 64)

    def text(self, field_id: int, value: str) -> None:
        raw = value.encode("utf-8")
        self._field(field_id, _TC_BINARY)
        self.varint(len(raw))
        self.out += raw

    def field_struct(self, field_id: int) -> None:
        self._field(field_id, _TC_STRUCT)
        self.struct_begin()

    def field_list(self, field_id: int, element_type: int, size: int) -> None:
        self._field(field_id, _TC_LIST)
        if size <= 14:
            self.out.append((size << 4) | element_type)
        else:
            self.out.append(0xF0 | element_type)
            self.varint(size)

    def list_of_i32(self, field_id: int, values: Sequence[int]) -> None:
        self.field_list(field_id, _TC_I32, len(values))
        for value in values:
            self._zigzag(value, 32)

    def list_of_text(self, field_id: int, values: Sequence[str]) -> None:
        self.field_list(field_id, _TC_BINARY, len(values))
        for value in values:
            raw = value.encode("utf-8")
            self.varint(len(raw))
            self.out += raw


def _micros(moment: datetime) -> int:
    delta = moment - EPOCH_DATETIME
    return (delta.days * 86_400 + delta.seconds) * 1_000_000 + delta.microseconds


def _plain(column: Column, values: list[object]) -> bytes:
    """PLAIN encoding: the values back to back, little-endian, and nothing else.

    Timestamps go out as microseconds from the epoch with `isAdjustedToUTC = false`, because
    `events.py` is explicit that the corpus's timestamps are **naive on purpose** — *"a
    markdown at 21:00 is 21:00 where the shop is"*. Declaring them UTC-adjusted would assert
    a zone nobody in the scenario has.
    """
    try:
        if column.kind is Kind.BOOL:
            packed = bytearray((len(values) + 7) // 8)
            for index, value in enumerate(values):
                if not isinstance(value, bool):
                    raise TypeError(f"{value!r} is {type(value).__name__}, not bool")
                if value:
                    packed[index // 8] |= 1 << (index % 8)
            return bytes(packed)
        if column.kind is Kind.INT64:
            return struct.pack(f"<{len(values)}q", *values)
        if column.kind is Kind.DOUBLE:
            return struct.pack(f"<{len(values)}d", *values)
        if column.kind is Kind.DATE:
            days = [(cast(date, value) - EPOCH_DATE).days for value in values]
            return struct.pack(f"<{len(days)}i", *days)
        if column.kind is Kind.TIMESTAMP:
            stamps = [_micros(cast(datetime, value)) for value in values]
            return struct.pack(f"<{len(stamps)}q", *stamps)
        out = bytearray()
        for value in values:
            if not isinstance(value, str):
                raise TypeError(f"{value!r} is {type(value).__name__}, not str")
            raw = value.encode("utf-8")
            out += struct.pack("<I", len(raw))
            out += raw
    except (struct.error, TypeError, AttributeError) as exc:
        raise SchemaError(f"column {column.name} is declared {column.kind.value}: {exc}") from exc
    return bytes(out)


def _definition_levels(levels: Sequence[int]) -> bytes:
    """Definition levels, RLE runs only, at bit width 1.

    A flat optional column has exactly two levels — present and absent — so the hybrid
    encoding's bit-packed half is never needed and every page is a handful of runs. The four
    leading bytes are the length prefix a V1 data page requires.
    """
    body = bytearray()
    run_value: int | None = None
    run_length = 0
    for level in [*levels, None]:
        if level == run_value:
            run_length += 1
            continue
        if run_value is not None:
            header = run_length << 1  # bit 0 clear marks an RLE run rather than a packed one
            while True:
                low = header & 0x7F
                header >>= 7
                body.append(low | 0x80 if header else low)
                if not header:
                    break
            body.append(run_value)
        run_value, run_length = level, 1
    return struct.pack("<I", len(body)) + bytes(body)


@dataclass(frozen=True, slots=True)
class _Chunk:
    column: Column
    offset: int
    values: int
    uncompressed: int
    compressed: int


@dataclass(frozen=True, slots=True)
class _RowGroup:
    chunks: tuple[_Chunk, ...]
    rows: int


class ParquetWriter:
    """One file, written a row at a time and laid out column by column at each flush.

    Rows are buffered to `row_group_rows` because Parquet is column-major on disk and the
    corpus emits rows: a row group cannot be written until its last row has been seen. The
    default is the trade every writer makes — a larger group compresses better and holds more
    memory — and it is a parameter so a test can assert against a file with several.
    """

    def __init__(
        self,
        path: Path,
        columns: Sequence[Column],
        *,
        row_group_rows: int = 65_536,
        compress: bool = True,
    ) -> None:
        if not columns:
            raise SchemaError("a Parquet file with no columns describes nothing")
        names = [column.name for column in columns]
        if len(set(names)) != len(names):
            raise SchemaError(f"two columns share a name: {sorted(names)}")
        if row_group_rows < 1:
            raise SchemaError("a row group holds at least one row")
        self.path = path
        self.columns = tuple(columns)
        self.row_group_rows = row_group_rows
        self.codec = _CODEC_GZIP if compress else _CODEC_UNCOMPRESSED
        self.rows = 0
        self._buffer: list[list[object]] = [[] for _ in self.columns]
        self._buffered = 0
        self._groups: list[_RowGroup] = []
        self._handle = path.open("wb")
        self._handle.write(MAGIC)

    def write(self, row: Sequence[object]) -> None:
        if len(row) != len(self.columns):
            raise SchemaError(
                f"{len(row)} values for {len(self.columns)} columns "
                f"({', '.join(column.name for column in self.columns)})"
            )
        for index, value in enumerate(row):
            self._buffer[index].append(value)
        self._buffered += 1
        self.rows += 1
        if self._buffered >= self.row_group_rows:
            self._flush()

    def write_rows(self, rows: Iterable[Sequence[object]]) -> None:
        for row in rows:
            self.write(row)

    def close(self) -> None:
        """Flush, write the footer, stop. Safe to call twice, as `Sink.close` is."""
        if self._handle.closed:
            return
        self._flush()
        footer = self._footer()
        self._handle.write(footer)
        self._handle.write(struct.pack("<I", len(footer)))
        self._handle.write(MAGIC)
        self._handle.close()

    def __enter__(self) -> ParquetWriter:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    # ------------------------------------------------------------------- the bytes

    def _compress(self, raw: bytes) -> bytes:
        if self.codec == _CODEC_UNCOMPRESSED:
            return raw
        # wbits=31 is zlib's gzip container, which is what Parquet's GZIP codec means.
        engine = zlib.compressobj(6, zlib.DEFLATED, 31)
        return engine.compress(raw) + engine.flush()

    def _flush(self) -> None:
        if self._buffered == 0:
            return
        chunks: list[_Chunk] = []
        for index, column in enumerate(self.columns):
            values = self._buffer[index]
            present = [value for value in values if value is not None]
            if not column.optional and len(present) != len(values):
                raise SchemaError(
                    f"column {column.name} is required and {len(values) - len(present)} of "
                    f"{len(values)} values in this row group are absent. Declare it optional "
                    "or supply the value — nothing here writes a default."
                )
            body = b""
            if column.optional:
                body += _definition_levels([0 if value is None else 1 for value in values])
            body += _plain(column, present)
            payload = self._compress(body)
            header = self._page_header(len(values), len(body), len(payload))
            offset = self._handle.tell()
            self._handle.write(header)
            self._handle.write(payload)
            chunks.append(
                _Chunk(
                    column=column,
                    offset=offset,
                    values=len(values),
                    uncompressed=len(header) + len(body),
                    compressed=len(header) + len(payload),
                )
            )
        self._groups.append(_RowGroup(tuple(chunks), self._buffered))
        self._buffer = [[] for _ in self.columns]
        self._buffered = 0

    def _page_header(self, values: int, uncompressed: int, compressed: int) -> bytes:
        out = _Compact()
        out.i32(1, _PAGE_TYPE_DATA)
        out.i32(2, uncompressed)
        out.i32(3, compressed)
        out.field_struct(5)  # DataPageHeader
        out.i32(1, values)
        out.i32(2, _ENCODING_PLAIN)
        out.i32(3, _ENCODING_RLE)  # definition levels
        out.i32(4, _ENCODING_RLE)  # repetition levels: none are written, still declared
        out.struct_end()
        out.struct_end()
        return bytes(out.out)

    def _footer(self) -> bytes:
        out = _Compact()
        out.struct_begin()
        out.i32(1, 1)  # format version
        self._schema(out)
        out.i64(3, self.rows)
        self._row_groups(out)
        out.text(6, "holdout corpus/world/parquet.py")
        out.struct_end()
        return bytes(out.out)

    def _schema(self, out: _Compact) -> None:
        """A flat schema: the root element, then one leaf per column."""
        out.field_list(2, _TC_STRUCT, len(self.columns) + 1)
        out.struct_begin()
        out.text(4, "schema")
        out.i32(5, len(self.columns))  # num_children
        out.struct_end()
        for column in self.columns:
            out.struct_begin()
            out.i32(1, _PHYSICAL[column.kind])
            out.i32(3, _REPETITION_OPTIONAL if column.optional else _REPETITION_REQUIRED)
            out.text(4, column.name)
            if column.kind is Kind.STRING:
                out.i32(6, _CONVERTED_UTF8)
            elif column.kind is Kind.DATE:
                out.i32(6, _CONVERTED_DATE)
            elif column.kind is Kind.TIMESTAMP:
                # No converted type: the deprecated `TIMESTAMP_MICROS` means UTC-adjusted and
                # these timestamps are not. The logical type can say so, and does.
                out.field_struct(10)
                out.field_struct(_LOGICAL_TIMESTAMP)
                out.boolean(1, False)  # isAdjustedToUTC
                out.field_struct(2)  # TimeUnit
                out.field_struct(_TIME_UNIT_MICROS)
                out.struct_end()
                out.struct_end()
                out.struct_end()
                out.struct_end()
            out.struct_end()

    def _row_groups(self, out: _Compact) -> None:
        out.field_list(4, _TC_STRUCT, len(self._groups))
        for group in self._groups:
            out.struct_begin()
            out.field_list(1, _TC_STRUCT, len(group.chunks))
            for chunk in group.chunks:
                out.struct_begin()
                out.i64(2, chunk.offset)  # file_offset
                out.field_struct(3)  # ColumnMetaData
                out.i32(1, _PHYSICAL[chunk.column.kind])
                out.list_of_i32(2, [_ENCODING_PLAIN, _ENCODING_RLE])
                out.list_of_text(3, [chunk.column.name])  # path_in_schema
                out.i32(4, self.codec)
                out.i64(5, chunk.values)
                out.i64(6, chunk.uncompressed)
                out.i64(7, chunk.compressed)
                out.i64(9, chunk.offset)  # data_page_offset
                out.struct_end()
                out.struct_end()
            out.i64(2, sum(chunk.uncompressed for chunk in group.chunks))
            out.i64(3, group.rows)
            out.struct_end()


def write_table(
    path: Path,
    columns: Sequence[Column],
    rows: Iterable[Sequence[object]],
    *,
    row_group_rows: int = 65_536,
) -> int:
    """Write one whole table, and return how many rows it holds."""
    with ParquetWriter(path, columns, row_group_rows=row_group_rows) as writer:
        writer.write_rows(rows)
        return writer.rows
