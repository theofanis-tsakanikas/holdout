"""The S3 bulk load: files that landed become bronze, once each.

This is the ERP path. `CLAUDE.md`, since the author's route-2 ruling:

> *ERP tables, competitor prices | **bulk load from files on S3** | several drops during the
> day rather than one*
> *eight months of transaction history | **bulk load from files on S3** | streaming eight
> months through Zerobus would be slow and costly … backfill from files, then stream*

**What is demonstrated is incremental load of successive drops. It is not change capture
against a live source.** That is a smaller claim than the design carried before the ruling, it
was chosen deliberately in exchange for *serverless only* — the connector that would have made
the larger one runs a continuous gateway on classic compute — and it is written here as the
smaller claim so that no later reader has to work out which one this file supports. Concretely:

- **no row-level delta, no before-image, no delete detection.** A row that leaves the ERP
  leaves by not appearing in the next snapshot, and nothing here notices or reports that.
- **this loader never compares two snapshots.** Working out what changed between drop 3 and
  drop 4 *is* change capture. What became visible is the source's own statement, carried in
  each drop's manifest by the exporter that applied the visibility rule.
- **what makes a load incremental is the checkpoint**, and nothing else: a file already loaded
  is not loaded again, so driving the same landing area twice moves nothing the second time.

Two modes, and the asymmetry is the bronze rule rather than an inconsistency
----------------------------------------------------------------------------
**A schemaless extract is materialised.** The ERP's drops are gzipped CSV, which is what an
extract actually is: no types, and no way to tell an absent value from an empty one. Each file
is parsed against the types its drop's manifest declares and written as Parquet, with three
columns added — `_source_file`, `_exported_at`, `_arrival_ts`. Those are not a transformation
of the record: `CLAUDE.md` requires that *every record carries both its event time and its
arrival time*, a master-data row carries neither of its own, and a snapshot with no provenance
cannot be reprocessed or told apart from the snapshot before it.

**A file already in the lakehouse's format is registered unchanged.** The eight months of
history are Parquet whose records carry `event_ts` and `arrival_ts` from the source that
produced them, so there is nothing to add and rewriting them would be a transformation bronze
forbids — *nothing is transformed at ingestion; bronze is the source's shape*. **That mode is
thin, and the thinness is the rule being obeyed rather than a corner cut.** It is also what
`COPY INTO` of a Parquet file does: move the bytes, record what was moved.

What this refuses
-----------------
A path already loaded whose bytes have changed, and a file whose digest is not the one its
manifest declares. Both are refusals by name rather than a reload: a drop is immutable, and a
second load of a changed file would double a table in a place where nothing downstream could
tell that had happened.

What it never touches
---------------------
Anything that is not a declared file or a `.parquet`. `truth.sealed.json` sits in the same
directory as the history it belongs to, and it is not a source: the seal is opened after a
readout has been written, by a harness, and never by an ingestion path.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from csv import DictReader
from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING

from corpus.world.parquet import Column, Kind, ParquetWriter

from pipelines.ingest.erp import MANIFEST, declared_types, drop_directories

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from pathlib import Path

#: What the loader has already taken, so that it does not take it twice.
CHECKPOINT = "_checkpoint.json"

#: Every load, appended. The ledger of the load, as opposed to the state of it.
LOAD_LOG = "_load_log.jsonl"

#: The provenance a materialised row carries, and nothing beyond it.
PROVENANCE: tuple[Column, ...] = (
    Column("_source_file", Kind.STRING),
    Column("_exported_at", Kind.TIMESTAMP),
    Column("_arrival_ts", Kind.TIMESTAMP),
)

#: How much of a file is read at a time when its digest is taken. Files here are megabytes,
#: not gigabytes; this exists so the estate's eight months do not have to be resident.
_DIGEST_BLOCK = 1 << 20


class BulkLoadError(ValueError):
    """A drop that changed under a path already loaded, or a file that is not what it says."""


@dataclass(frozen=True, slots=True)
class Loaded:
    """One file, taken once."""

    source: str
    table: str
    rows: int
    part: str
    digest: str
    #: `materialised` — parsed from a declared schema and written as Parquet.
    #: `registered` — already in the lakehouse's format, moved unchanged.
    mode: str


@dataclass(frozen=True, slots=True)
class LoadResult:
    """What one call took, and what it left because it had taken it before."""

    loaded: tuple[Loaded, ...]
    skipped: tuple[str, ...]

    @property
    def files(self) -> int:
        return len(self.loaded)

    @property
    def rows(self) -> int:
        return sum(entry.rows for entry in self.loaded)

    def by_table(self) -> dict[str, int]:
        tally: dict[str, int] = {}
        for entry in self.loaded:
            tally[entry.table] = tally.get(entry.table, 0) + entry.rows
        return tally


def digest_of(path: Path) -> str:
    reader = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(_DIGEST_BLOCK):
            reader.update(block)
    return reader.hexdigest()


def _parse(text: str, column: Column, where: str) -> object:
    """One cell, against the type its manifest declared. Never inferred, never defaulted.

    An empty cell in an **optional** column is read as absent, and in a required one as the
    empty string it is. That distinction cannot be made by looking at the file, which is the
    whole reason a drop carries a schema — and the reason `corpus/world/`'s Parquet target
    exists rather than the CSV one being loaded straight through.
    """
    if text == "" and column.optional:
        return None
    try:
        if column.kind is Kind.STRING:
            return text
        if column.kind is Kind.INT64:
            return int(text)
        if column.kind is Kind.DOUBLE:
            return float(text)
        if column.kind is Kind.DATE:
            return date.fromisoformat(text)
        if column.kind is Kind.TIMESTAMP:
            return datetime.fromisoformat(text)
        if text in ("True", "true"):
            return True
        if text in ("False", "false"):
            return False
        raise ValueError(f"{text!r} is not a boolean")
    except ValueError as exc:
        raise BulkLoadError(
            f"{where}: column {column.name} is declared {column.kind.value} and holds "
            f"{text!r} — {exc}"
        ) from exc


def _columns(declared: Sequence[dict[str, object]], where: str) -> tuple[Column, ...]:
    kinds = declared_types()
    columns: list[Column] = []
    for entry in declared:
        name, type_name = str(entry["name"]), str(entry["type"])
        if type_name not in kinds:
            raise BulkLoadError(
                f"{where}: column {name} is declared {type_name!r}, which is not a declared "
                f"type. Declared types are {sorted(kinds)}."
            )
        columns.append(Column(name, kinds[type_name], optional=bool(entry["optional"])))
    return tuple(columns)


def _rows(path: Path, columns: Sequence[Column], where: str) -> Iterator[list[object]]:
    with gzip.open(path, "rt", newline="", encoding="utf-8") as handle:
        reader = DictReader(handle)
        header = list(reader.fieldnames or ())
        if header != [column.name for column in columns]:
            raise BulkLoadError(
                f"{where}: the file's header is {header} and its manifest declares "
                f"{[column.name for column in columns]}"
            )
        for number, row in enumerate(reader, start=2):
            yield [_parse(row[c.name], c, f"{where} line {number}") for c in columns]


def _part_name(source: str) -> str:
    """A bronze part file named after the file it came from, so the two can be lined up."""
    stem = source.replace("/", "-")
    for suffix in (".csv.gz", ".parquet"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
    return f"{stem}.parquet"


def _read_checkpoint(bronze: Path) -> dict[str, dict[str, object]]:
    path = bronze / CHECKPOINT
    if not path.is_file():
        return {}
    parsed: dict[str, dict[str, object]] = json.loads(path.read_text(encoding="utf-8"))["files"]
    return parsed


def _write_checkpoint(bronze: Path, taken: dict[str, dict[str, object]]) -> None:
    (bronze / CHECKPOINT).write_text(
        json.dumps({"files": taken}, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _already_taken(source: str, digest: str, taken: dict[str, dict[str, object]]) -> bool:
    seen = taken.get(source)
    if seen is None:
        return False
    if seen["sha256"] != digest:
        raise BulkLoadError(
            f"{source} was loaded with digest {str(seen['sha256'])[:12]} and now has "
            f"{digest[:12]}. A drop is immutable: a path whose bytes changed is refused rather "
            "than loaded again, because a second load would double a table and nothing "
            "downstream could tell."
        )
    return True


def load(landing: Path, bronze: Path, *, arrived_at: datetime) -> LoadResult:
    """Take everything in `landing` that has not been taken, and write it into `bronze`.

    `arrived_at` is passed rather than read off a clock, because it is the one value in a
    bronze row that this repository's own machinery decides: a test that could not fix it
    would be asserting against `datetime.now()`, and a run that could not fix it could not be
    reproduced.
    """
    bronze.mkdir(parents=True, exist_ok=True)
    taken = _read_checkpoint(bronze)
    loaded: list[Loaded] = []
    skipped: list[str] = []

    for entry in _sources(landing):
        source, path = entry.relative, entry.path
        digest = digest_of(path)
        if entry.declared_digest is not None and entry.declared_digest != digest:
            raise BulkLoadError(
                f"{source} has digest {digest[:12]} and its manifest declares "
                f"{entry.declared_digest[:12]}. The file is not the one that was exported."
            )
        if _already_taken(source, digest, taken):
            skipped.append(source)
            continue
        # A source with a declared schema is an extract to parse; one without is already in
        # the lakehouse's format. Nothing else distinguishes the two modes.
        record = (
            _materialise(entry, entry.columns, entry.exported_at, bronze, arrived_at=arrived_at)
            if entry.columns is not None and entry.exported_at is not None
            else _register(entry, bronze)
        )
        loaded.append(record)
        taken[source] = {
            "sha256": digest,
            "rows": record.rows,
            "part": record.part,
            "mode": record.mode,
            "loaded_at": arrived_at.isoformat(),
        }

    _write_checkpoint(bronze, taken)
    _append_log(bronze, loaded, arrived_at)
    return LoadResult(tuple(loaded), tuple(skipped))


@dataclass(frozen=True, slots=True)
class _Source:
    """One file the landing area offers, with whatever its drop declared about it."""

    relative: str
    path: Path
    table: str
    columns: tuple[Column, ...] | None
    declared_rows: int | None
    declared_digest: str | None
    exported_at: datetime | None


def _sources(landing: Path) -> Iterator[_Source]:
    """Every file the landing area declares, drops first, in the order they were exported.

    **The population, stated as a rule: a source is a file some manifest names.** Each declared
    file of each `drop=NNN/_manifest.json`, then each event stream each `run.json` counts. A
    `.parquet` nobody declared is not loaded, and that is not tidiness — it is what keeps the
    history drop from carrying the ERP's tables in by a second route. `corpus/world/`'s Parquet
    target writes `store_master`, `product_master` and `cost_ledger` beside the four streams,
    **with the `arm` column the ERP export deliberately withholds**, and `run.json`'s `counts`
    names the streams only. Globbing for `*.parquet` loaded them; reading the manifest does not.

    `truth.sealed.json` sits in that same directory and is declared by nothing at all, which is
    the second thing this rule buys: an ingestion path cannot carry the injected truth into
    bronze even by accident.
    """
    for directory in drop_directories(landing):
        manifest = json.loads((directory / MANIFEST).read_text(encoding="utf-8"))
        exported_at = datetime.fromisoformat(str(manifest["exported_at"]))
        for declared in manifest["files"]:
            path = directory / str(declared["file"])
            relative = path.relative_to(landing).as_posix()
            yield _Source(
                relative=relative,
                path=path,
                table=str(declared["table"]),
                columns=_columns(declared["columns"], relative),
                declared_rows=int(declared["rows"]),
                declared_digest=str(declared["sha256"]),
                exported_at=exported_at,
            )
    for run_manifest in _history_manifests(landing):
        counts: dict[str, int] = json.loads(run_manifest.read_text(encoding="utf-8"))["counts"]
        for stream, rows in sorted(counts.items()):
            path = run_manifest.parent / f"{stream}.parquet"
            if not path.is_file():
                raise BulkLoadError(
                    f"{run_manifest.relative_to(landing).as_posix()} counts {rows} rows of "
                    f"{stream} and {path.name} is not there. A manifest naming a file that "
                    "does not exist is a drop that was interrupted, not a drop with no rows."
                )
            yield _Source(
                relative=path.relative_to(landing).as_posix(),
                path=path,
                table=stream,
                columns=None,
                declared_rows=rows,
                declared_digest=None,
                exported_at=None,
            )


def _history_manifests(landing: Path) -> list[Path]:
    """`run.json`, in the landing area or one directory down. Written by `corpus/world/write`.

    **It declares counts and no digests**, which the ERP's own manifest does declare. So a
    history file is checked against the checkpoint — the same path may not come back with
    different bytes — and *not* against what wrote it. That is a smaller guarantee than the
    drops get, and it is stated rather than blurred: adding digests to the corpus's manifest is
    a change to `corpus/world/`, and this branch did not need one to load what it writes.
    """
    here = [landing / "run.json"] if (landing / "run.json").is_file() else []
    return here + sorted(landing.glob("*/run.json"))


def _materialise(
    source: _Source,
    declared: tuple[Column, ...],
    exported_at: datetime,
    bronze: Path,
    *,
    arrived_at: datetime,
) -> Loaded:
    """Parse a declared extract and write it as Parquet, with its provenance."""
    table = bronze / source.table
    table.mkdir(parents=True, exist_ok=True)
    part = table / _part_name(source.relative)
    columns = (*declared, *PROVENANCE)
    provenance = (source.relative, exported_at, arrived_at)
    written = 0
    with ParquetWriter(part, columns) as writer:
        for row in _rows(source.path, declared, source.relative):
            writer.write([*row, *provenance])
            written += 1
    if source.declared_rows is not None and written != source.declared_rows:
        raise BulkLoadError(
            f"{source.relative} holds {written} rows and its manifest declares "
            f"{source.declared_rows}"
        )
    return Loaded(
        source=source.relative,
        table=source.table,
        rows=written,
        part=part.relative_to(bronze).as_posix(),
        digest=digest_of(part),
        mode="materialised",
    )


def _register(source: _Source, bronze: Path) -> Loaded:
    """Move a file that is already in the lakehouse's format, byte for byte.

    The rows are not read, counted or rewritten. Their `event_ts` and `arrival_ts` came from
    the system that produced them, and a loader that added its own would be inventing a second
    arrival for a record that has one.

    **The row count is the manifest's, not this function's**, and the two are different kinds
    of statement: nothing here opened the file. It is reported as what was declared.
    """
    table = bronze / source.table
    table.mkdir(parents=True, exist_ok=True)
    part = table / _part_name(source.relative)
    part.write_bytes(source.path.read_bytes())
    return Loaded(
        source=source.relative,
        table=source.table,
        rows=source.declared_rows or 0,
        part=part.relative_to(bronze).as_posix(),
        digest=digest_of(part),
        mode="registered",
    )


def _append_log(bronze: Path, loaded: Sequence[Loaded], arrived_at: datetime) -> None:
    """One line per file taken, appended and never rewritten.

    A `registered` file's `rows` is **what its manifest declared**, and `mode` is on the line
    beside it so the distinction survives: a materialised count was produced by parsing every
    line, a registered one was copied from the source's own statement.
    """
    if not loaded:
        return
    with (bronze / LOAD_LOG).open("a", encoding="utf-8") as handle:
        for entry in loaded:
            handle.write(
                json.dumps(
                    {
                        "loaded_at": arrived_at.isoformat(),
                        "source": entry.source,
                        "table": entry.table,
                        "mode": entry.mode,
                        "rows": entry.rows,
                        "part": entry.part,
                        "sha256": entry.digest,
                    },
                    sort_keys=True,
                )
                + "\n"
            )


def _summary(result: LoadResult) -> Iterator[str]:
    yield f"  files taken                   {result.files}"
    yield f"  files already loaded          {len(result.skipped)}"
    yield f"  rows                          {result.rows}"
    for table, rows in sorted(result.by_table().items()):
        mode = next(entry.mode for entry in result.loaded if entry.table == table)
        source = "parsed" if mode == "materialised" else "declared by the source"
        yield f"    {table:<20}{rows:>8}  {mode:<14} {source}"


def main(argv: list[str] | None = None) -> int:
    """`python -m pipelines.ingest.bulk` — export the drops, then load what landed.

        python -m pipelines.ingest.bulk export --scale smoke --day 2025-09-02 --landing .land
        python -m pipelines.ingest.bulk history --scale smoke --landing .land
        python -m pipelines.ingest.bulk load --landing .land --bronze .bronze

    Every number it prints is a measurement of one seed, one scale and one day, and the header
    says so: a share is a parameter and what a share produced is not.
    """
    import argparse
    from pathlib import Path as _Path

    from corpus.world import prepare

    from pipelines.ingest import erp

    parser = argparse.ArgumentParser(prog="pipelines.ingest.bulk", description=main.__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("export", "history"):
        job = sub.add_parser(name)
        job.add_argument("--world", default="W6")
        job.add_argument("--seed", default="holdout-w-0001")
        job.add_argument("--scale", default="smoke")
        job.add_argument("--landing", type=_Path, required=True)
        if name == "export":
            job.add_argument("--day", required=True, help="an ISO date inside the corpus")
            job.add_argument(
                "--hours",
                default=",".join(str(hour) for hour in erp.DECLARED.hours),
                help="the export moments, declared rather than measured",
            )

    loader = sub.add_parser("load")
    loader.add_argument("--landing", type=_Path, required=True)
    loader.add_argument("--bronze", type=_Path, required=True)
    loader.add_argument(
        "--arrived-at",
        default="2026-09-03T09:00:00",
        help="the arrival stamped on every materialised row; passed, never read off a clock",
    )

    args = parser.parse_args(argv)

    if args.command == "load":
        result = load(args.landing, args.bronze, arrived_at=datetime.fromisoformat(args.arrived_at))
        print(f"bulk load  {args.landing} -> {args.bronze}")
        print("        incremental load of successive drops, not change capture\n")
        for line in _summary(result):
            print(line)
        return 0

    run = prepare(args.world, seed=args.seed, scale=args.scale)
    if args.command == "history":
        counts = erp.history(run, args.landing)
        print(f"history  {args.world} at {args.scale}, seed {args.seed} -> {args.landing}")
        for stream, number in sorted(counts.items()):
            print(f"  {stream:<18} {number:>10,}")
        return 0

    day = date.fromisoformat(args.day)
    schedule = erp.Schedule(tuple(int(hour) for hour in args.hours.split(",")))
    steps = erp.cost_steps_on(run, day)
    print(f"erp drops  {args.world} at {args.scale}, seed {args.seed}, {day}")
    print("        measurements of this seed, this scale and this day\n")
    print(f"  cost steps effective on this day   {len(steps)}")
    for moment in steps:
        print(f"    {moment.isoformat()}")
    drops = erp.export(run, args.landing, day=day, schedule=schedule)
    print("")
    for drop in drops:
        print(
            f"  drop={drop.seq:03d}  {drop.exported_at.isoformat()}  "
            f"{drop.rows:>6} rows  {drop.newly_visible:>3} newly visible"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
