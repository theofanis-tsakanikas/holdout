"""The ERP's own export: successive drops of master data, during a driven day.

`CLAUDE.md`'s sources table, since the author's route-2 ruling on 2026-09-02:

> *ERP tables, competitor prices | **bulk load from files on S3** | several drops during the
> day rather than one: master data changes while the day runs, and no connector, no gateway
> and no ingestion code to maintain*

**Several drops, and the reason is exact.** A single static snapshot leaves the decision path's
declared trigger — *"a cost change in the ERP that moved the floor"* — with nothing to fire on,
and a declared thing that never runs is the defect this repository spent 2026-09-02 finding
four instances of. So this module exports the master data **as the ERP knows it at a moment**,
several times across one trading day.

What makes two drops differ is the corpus, not a parameter of mine
------------------------------------------------------------------
`corpus/world/chain.py` gives every SKU one to four `CostStep`s whose `effective_from` is a
**datetime**, with an hour. The export rule is therefore the honest one and the only one:

> *the ERP's extract at `T` carries every cost step with `effective_from <= T`.*

Nothing is injected, no lateness is invented, and two extracts an hour apart differ exactly
when the ledger stepped between them. `store_master` and `product_master` have no time
dimension in this corpus, so their successive extracts are **byte-identical** — which is what a
snapshot-drop ERP produces and is left as it is: collapsing successive snapshots into one
answer is silver's as-of `reference`, not an exporter's and not a loader's.

Which day is driven is a choice, and the number that makes it one
------------------------------------------------------------------
A day with no cost step is a real day and this module exports it as one, printing zero. But a
demonstration driven on such a day shows successive drops with nothing in them, so the day
gets chosen — and how much choosing that is depends entirely on the scale. Measured on
`holdout-w-0001`, counting steps that fall **after the corpus opens**; the ledger is a function
of `(seed, scale)` and not of the world, so one column covers all six:

| scale | SKUs | steps | days | days with a step | **days with one in trading hours** |
|---|---:|---:|---:|---:|---:|
| `smoke` | 9 | 32 | 21 | 13 (62%) | **9 (43%)**, busiest 3 |
| `harness` | 12 | 39 | 112 | 25 (22%) | **11 (10%)**, busiest 2 |
| `scenario` | 120 | 402 | 244 | 175 (72%) | **126 (52%)**, busiest 5 |

**At `harness` nine days in ten have nothing for a drop to carry**, so the driven day there is
picked rather than found, and saying so is the whole of the disclosure. At `scenario` it mostly
need not be. The table is here because this is the file somebody reads when choosing a day, and
`--day` prints what that day actually carries before anything is written.

What the ERP does not know
--------------------------
**The arm is not exported**, though `corpus/world/`'s `store_master` declaration carries it. An
ERP does not know which stores are in an experiment's control group, and a bronze master-data
table that carried the arm would let a downstream join take it from there rather than from the
assignment written before the period opened — which is claim 3's one door, opened by a column.

**Four of the seven ERP tables `CLAUDE.md` names in bronze have no source here** —
`supplier_terms`, `planogram` and `competitor_prices` are not in this corpus, and
`regulated_basket` is a *contract* rather than corpus data. They are named as absent. Inventing
three tables so a list could be complete is doctrine rule 3 with a schema on it.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from corpus.world import REFERENCE_TABLES, Format, Run, write
from corpus.world.parquet import Column, Kind

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from pathlib import Path

    from corpus.world import ReferenceTable

#: The file every drop carries, and the only thing the loader is allowed to read a schema from.
MANIFEST = "_manifest.json"

#: What an ERP hands over. The other four bronze tables have no source in this corpus; see the
#: module docstring, which names them rather than inventing them.
EXPORTED: tuple[str, ...] = ("store_master", "product_master", "cost_ledger")

#: Columns the export withholds, by table. `arm` is an experiment's fact and not the ERP's.
WITHHELD: dict[str, tuple[str, ...]] = {"store_master": ("arm",)}

#: The column whose value decides whether a row is visible yet, by table. `None` means the
#: table has no time dimension in this corpus and every extract of it is the same extract.
KNOWN_AT: dict[str, str | None] = {
    "store_master": None,
    "product_master": None,
    "cost_ledger": "effective_from",
}


class ExportError(ValueError):
    """A day outside the corpus, or a schedule that could not produce successive drops."""


@dataclass(frozen=True, slots=True)
class Schedule:
    """When the ERP exports during a driven day. Declared, and named as declared.

    Five extracts across a trading day is a shape, not a measurement of any real chain — the
    same sentence `pipelines/ingest/driver.py` makes about its own pathology shares. Nobody
    here has an ERP's export timetable, and a number invented and then quoted as though it
    were measured is the defect this repository spends most of its time correcting.
    """

    hours: tuple[int, ...] = (7, 11, 15, 19, 22)

    def __post_init__(self) -> None:
        if len(self.hours) < 2:
            raise ExportError(
                f"{len(self.hours)} export(s) in a day is not several drops, and one snapshot "
                "is the thing the ruling refused: nothing for incremental load to do."
            )
        if sorted(set(self.hours)) != list(self.hours):
            raise ExportError("the export hours must be distinct and in order")
        if not all(0 <= hour < 24 for hour in self.hours):
            raise ExportError("an export hour outside the day is not an hour")

    def moments(self, day: date) -> tuple[datetime, ...]:
        return tuple(
            datetime.combine(day, datetime.min.time()) + timedelta(hours=h) for h in self.hours
        )


#: Five drops across the trading day. `corpus/world/scale.py` opens a store at 07:00 and takes
#: its last basket in the hour beginning 22:00, so this brackets the day the shops are open.
DECLARED = Schedule()


@dataclass(frozen=True, slots=True)
class ExportedFile:
    """One table in one drop: what was written, how much of it, and its digest."""

    table: str
    filename: str
    columns: tuple[Column, ...]
    rows: int
    digest: str
    bytes_written: int
    #: Rows this extract carries that the previous one did not, by the visibility rule above.
    #: Zero for a table with no time dimension, and it is the source's own statement rather
    #: than a comparison of two files: the exporter knows what became visible because it is
    #: what applied the rule. **A loader computing this would be doing change capture**, which
    #: is what route 2 gave up.
    newly_visible: int


@dataclass(frozen=True, slots=True)
class Drop:
    """One export: a directory, a moment, and the files in it."""

    seq: int
    exported_at: datetime
    directory: Path
    files: tuple[ExportedFile, ...]

    @property
    def rows(self) -> int:
        return sum(file.rows for file in self.files)

    @property
    def newly_visible(self) -> int:
        return sum(file.newly_visible for file in self.files)


def _exported_columns(table: ReferenceTable) -> tuple[Column, ...]:
    withheld = WITHHELD.get(table.name, ())
    return tuple(column for column in table.columns if column.name not in withheld)


def _visible(
    table: ReferenceTable, run: Run, moment: datetime, since: datetime | None
) -> tuple[list[tuple[object, ...]], int]:
    """The rows of one table as the ERP knows them at `moment`, and how many are new."""
    keep = {column.name for column in _exported_columns(table)}
    positions = [index for index, column in enumerate(table.columns) if column.name in keep]
    clock = KNOWN_AT[table.name]
    at = next((index for index, c in enumerate(table.columns) if c.name == clock), None)

    rows: list[tuple[object, ...]] = []
    new = 0
    for row in table.rows(run, None):
        if at is not None:
            effective = row[at]
            if not isinstance(effective, datetime):
                raise ExportError(f"{table.name}.{clock} is not a moment: {effective!r}")
            if effective > moment:
                continue
            if since is not None and effective > since:
                new += 1
        rows.append(tuple(row[index] for index in positions))
    return rows, new


def _cell(value: object) -> str:
    """One CSV cell. An absent value is the empty string, which is all text can say.

    That is the loss the drop's declared schema exists to repair: `_manifest.json` says which
    columns may be absent, so `pipelines/ingest/bulk.py` reads `''` in an optional column as
    absent and in a required one as the empty string it is.
    """
    if value is None:
        return ""
    if isinstance(value, datetime | date):
        return value.isoformat()
    return str(value)


def _write_csv(
    path: Path, columns: Sequence[Column], rows: Sequence[tuple[object, ...]]
) -> tuple[str, int]:
    """Gzipped CSV, because that is the shape an ERP extract actually arrives in.

    The lakehouse's own format is written by `corpus/world/parquet.py` and loaded by the other
    half of `bulk.py`; master data arrives as text with no types at all, which is exactly why
    the manifest declares them.

    **`mtime=0`, and it is the difference between a digest of the content and a digest of the
    second it was written in.** `gzip.open` stamps the current time into the header, so exporting
    the same rows twice produces different bytes — and `bulk.load` refuses a path whose bytes
    changed, on the grounds that a drop is immutable. Two exports a second apart therefore looked
    like a **rewritten** drop rather than an identical one. It passed on a fast machine, where
    both landed in the same second, and CI failed on run `33739596010` where they did not.
    With the timestamp fixed, a drop's digest describes what is in it, and *a drop is immutable*
    is true by construction rather than by how quickly the exporter ran.
    """
    with (
        path.open("wb") as raw,
        gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed,
        io.TextIOWrapper(compressed, encoding="utf-8", newline="") as handle,
    ):
        out = csv.writer(handle)
        out.writerow([column.name for column in columns])
        for row in rows:
            out.writerow([_cell(value) for value in row])
    written = path.read_bytes()
    return hashlib.sha256(written).hexdigest(), len(written)


def cost_steps_on(run: Run, day: date) -> tuple[datetime, ...]:
    """Every moment the cost ledger steps on one day. The figure `--day` prints, and zero is a
    real answer — see the table in the module docstring."""
    return tuple(
        sorted(
            step.effective_from
            for product in run.chain.products
            for step in run.chain.cost_steps(product.sku_id)
            if step.effective_from.date() == day
        )
    )


def export(
    run: Run,
    landing: Path,
    *,
    day: date,
    schedule: Schedule = DECLARED,
) -> list[Drop]:
    """Write one drop per scheduled moment into `landing`, and say what each carries.

    Each drop is `drop=NNN/` holding one gzipped CSV per exported table and a `_manifest.json`
    declaring, per file, its columns and their types, its row count and its sha256. The digest
    is what makes a drop immutable: `bulk.load` refuses a path it has already loaded whose
    bytes have changed, rather than reloading it and doubling a table.
    """
    opens = run.scale.start_date
    closes = opens + timedelta(days=run.scale.days - 1)
    if not opens <= day <= closes:
        raise ExportError(
            f"{day} is outside the corpus, which runs {opens} to {closes}. Nothing is "
            "extrapolated past the days the world actually generated."
        )
    landing.mkdir(parents=True, exist_ok=True)
    by_name = {table.name: table for table in REFERENCE_TABLES}
    drops: list[Drop] = []
    previous: datetime | None = None
    for seq, moment in enumerate(schedule.moments(day)):
        directory = landing / f"drop={seq:03d}"
        directory.mkdir(parents=True, exist_ok=True)
        files: list[ExportedFile] = []
        for name in EXPORTED:
            table = by_name[name]
            columns = _exported_columns(table)
            rows, new = _visible(table, run, moment, previous)
            filename = f"{name}.csv.gz"
            digest, size = _write_csv(directory / filename, columns, rows)
            files.append(
                ExportedFile(
                    table=name,
                    filename=filename,
                    columns=columns,
                    rows=len(rows),
                    digest=digest,
                    bytes_written=size,
                    newly_visible=new,
                )
            )
        drop = Drop(seq=seq, exported_at=moment, directory=directory, files=tuple(files))
        _write_manifest(run, drop)
        drops.append(drop)
        previous = moment
    return drops


def _write_manifest(run: Run, drop: Drop) -> None:
    (drop.directory / MANIFEST).write_text(
        json.dumps(
            {
                "drop": drop.seq,
                "exported_at": drop.exported_at.isoformat(),
                "source": "erp",
                "world": run.world.id,
                "seed": run.seed,
                "scale": run.scale.name,
                # What this extract is and what it is not, carried in the drop itself so a
                # reader of the landing area does not have to find this module to know.
                "demonstrates": (
                    "incremental load of successive drops, not change capture against a live source"
                ),
                "files": [
                    {
                        "table": file.table,
                        "file": file.filename,
                        "rows": file.rows,
                        "bytes": file.bytes_written,
                        "sha256": file.digest,
                        "newly_visible": file.newly_visible,
                        "columns": [
                            {
                                "name": column.name,
                                "type": column.kind.value,
                                "optional": column.optional,
                            }
                            for column in file.columns
                        ],
                    }
                    for file in drop.files
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


#: Where the eight months land, beside the drops rather than among them.
HISTORY = "history"


def history(run: Run, landing: Path, *, only_stores: Sequence[str] | None = None) -> dict[str, int]:
    """The eight months, written where the bulk load will find them, in Parquet.

    `CLAUDE.md`: *"eight months of transaction history | bulk load from files on S3 |
    streaming eight months through Zerobus would be slow and costly, and no real deployment
    does it: backfill from files, then stream."* This is that side of the same landing area,
    and it is one call into `corpus/world/`'s Parquet target — the history *is* a world.

    **Its own directory, and the reason is what it also writes.** A world's Parquet output
    carries the three reference tables beside the four event streams, and the store master
    among them carries `arm`. The ERP export withholds that column on purpose, so the two must
    not be tipped into one landing area where a loader globbing for files would take whichever
    it found. `bulk.load` reads `run.json` rather than globbing, which is the guarantee; this
    directory is the legibility.
    """
    return write(run, landing / HISTORY, fmt=Format.PARQUET, only_stores=only_stores)


def declared_types() -> dict[str, Kind]:
    """The type names a manifest may use, by name. A manifest naming another is refused."""
    return {kind.value: kind for kind in Kind}


def drop_directories(landing: Path) -> Iterator[Path]:
    """Every drop in a landing area, in export order, by the name the exporter gave it."""
    yield from sorted(path for path in landing.glob("drop=*") if (path / MANIFEST).is_file())
