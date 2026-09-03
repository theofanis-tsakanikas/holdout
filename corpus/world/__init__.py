"""`corpus/world/` — the six adversarial worlds, and the chain they happen in.

Claim 2's trap, in `CLAUDE.md`'s words: *"a simulator generating data from the process the
estimator assumes is the estimator agreeing with itself."* This package is the half of the
answer that produces the data. The other half is that the estimator is design-based and valid
under any process at all — which is a theorem, and which is why the worlds below are not
trying to be right about grocery retail. They are trying to break the **machinery** around the
subtraction: assignment, exposure, the four validity checks, the readout.

Nothing here imports `holdout`
------------------------------
Not the estimator, not `Money`, not a refusal code, not the ladder. `ops/isolation.py` is the
one implementation of that rule; `tests/boundary/test_corpus_imports_nothing.py` is the gate
and `.claude/hooks/corpus_isolation.py` refuses the write before it lands. The reason is
mechanical rather than aesthetic: if the generator and the estimator shared a "compute margin"
function, a bug in it would cancel out and both would agree on a wrong number.

The one thing they share is `contracts/policies/ladder_policy@v1.yaml`, read as **data** by
`policy.contract_ladder`, because the control arm of a fresh-markdown experiment *is* the
existing policy and a generator running some other schedule would be simulating a chain this
system does not run. `policy.py` says more about where that line sits.

What is in here
---------------
=================  ==========================================================================
`scale`            how big a world is: `SMOKE`, `REHEARSAL`, `HARNESS`, `SCENARIO`
`rng`              keyed hashing — reproducible, order-independent, common random numbers
`chain`            stores, products, the cost ledger, and who is next door to whom
`policy`           markdown schedules as plain data; the contract read as data
`demand`           what a shopper does — the behaviour an effect is injected on
`worlds`           the six, W1 through W6, with what each violates
`assignment`       arms as an **input**; the lottery belongs to `core/experiment/`
`events`           one dataclass per bronze table, in the source's shape
`generate`         the simulation, store-major
`seal`             the injected truth, shut until the readout has been written
=================  ==========================================================================

The API
-------
`prepare` builds a run; `events` streams it; `write` materialises it; `count` measures it.
**None of the four ever returns the truth.** The exposure records the simulation produces are
routed straight into `seal.seal` and are not reachable from anything a caller holds — which is
the accident the seal exists to prevent, and the only part of the seal that is a guarantee
rather than a discipline.
"""

from __future__ import annotations

import csv
import gzip
import json
from collections import Counter
from collections.abc import Callable, Iterator, Sequence
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path

from corpus.world import chain as chain_module
from corpus.world import generate as generate_module
from corpus.world import policy as policy_module
from corpus.world import seal as seal_module
from corpus.world.assignment import Arm, Assignment, all_control, alternating
from corpus.world.chain import Chain
from corpus.world.events import STREAM_TYPES, STREAMS, Event, field_names, stream_of
from corpus.world.generate import StoreExposure
from corpus.world.parquet import Column, Kind, ParquetWriter, columns_for
from corpus.world.policy import MarkdownPolicy
from corpus.world.scale import (
    CATEGORIES,
    HARNESS,
    REHEARSAL,
    SCALES,
    SCENARIO,
    SMOKE,
    Scale,
    scale_by_name,
)
from corpus.world.seal import SEAL_FILENAME, WorldTruth
from corpus.world.worlds import WORLDS, World, world_by_id

__all__ = [
    "CATEGORIES",
    "FORMATS",
    "HARNESS",
    "REHEARSAL",
    "SCALES",
    "SCENARIO",
    "SEAL_FILENAME",
    "SMOKE",
    "STREAMS",
    "WORLDS",
    "Arm",
    "Assignment",
    "Chain",
    "Event",
    "Format",
    "MarkdownPolicy",
    "Run",
    "Scale",
    "World",
    "WorldTruth",
    "all_control",
    "alternating",
    "count",
    "events",
    "prepare",
    "scale_by_name",
    "world_by_id",
    "write",
]


class Format(Enum):
    """What `write` materialises a world as. Two, and both of them are read by something.

    `CSV` is what this package has always written: gzipped text, produced so a world can be
    **looked at**, and the format the ERP's own extract arrives in on the estate.

    `PARQUET` arrives with T009's bulk load, which is the first thing that needs files on disk
    in the format the lakehouse reads — the condition `docs/DECISIONS.md` deferred it on.
    `corpus/world/parquet.py` is the engine, stdlib and ours, and says why it is not a library.
    """

    CSV = "csv"
    PARQUET = "parquet"


#: The declared formats, by name, for a command line and for anything that validates one.
FORMATS: dict[str, Format] = {fmt.value: fmt for fmt in Format}


@dataclass(frozen=True, slots=True)
class Run:
    """Everything a world needs to happen, and nothing about what happened.

    Frozen and inspectable on purpose: the chain, the two policies and the assignment are all
    things an honest consumer is entitled to see before the experiment closes. What it does
    not carry — and cannot be made to carry — is any record of the effect.
    """

    world: World
    seed: str
    scale: Scale
    chain: Chain
    control: MarkdownPolicy
    treatment: MarkdownPolicy
    assignment: dict[str, Arm]

    @property
    def treated(self) -> tuple[str, ...]:
        return tuple(s for s, arm in sorted(self.assignment.items()) if arm is Arm.TREATMENT)


def prepare(
    world: World | str,
    *,
    seed: str,
    scale: Scale | str = SMOKE,
    assignment: Assignment | None = None,
    control: MarkdownPolicy | None = None,
    treatment: MarkdownPolicy | None = None,
) -> Run:
    """Build a run. The chain is a function of `(seed, scale)` and nothing else.

    `assignment` defaults to `alternating`, which is a convenience and not a lottery — an eval
    passes the assignment its own engine drew, because that engine is the thing under test.

    `control` defaults to `ladder_policy@v1` read from the contract and `treatment` to
    `policy.candidate` of it. Both are arguments because an experiment declares its own
    `intervention: {treatment, control}` and the world's job is to simulate the one it is
    handed — and because a test that can only ever be given the pair this package chose is a
    test of this package's taste. W1 is the exception the engine enforces: an A/A world with two
    different policies is refused rather than quietly run.
    """
    the_world = world if isinstance(world, World) else world_by_id(world)
    the_scale = scale if isinstance(scale, Scale) else scale_by_name(scale)
    built = chain_module.build(seed, the_scale, clustered_pct=the_world.clustered_pct)
    ladder = control if control is not None else policy_module.contract_ladder()
    if treatment is not None:
        candidate = treatment
    else:
        candidate = ladder if the_world.is_aa else policy_module.candidate(ladder)
    arms = dict(assignment) if assignment is not None else alternating(built)
    return Run(
        world=the_world,
        seed=seed,
        scale=the_scale,
        chain=built,
        control=ladder,
        treatment=candidate,
        assignment=arms,
    )


def events(
    run: Run,
    *,
    seal_into: Path | None = None,
    only_stores: Sequence[str] | None = None,
) -> Iterator[Event]:
    """The world's events, and only its events.

    The exposure truth the simulation produces on the way past is diverted into the seal if
    `seal_into` is given and dropped on the floor if it is not. Either way it does not come out
    of this function, which is the one structural half of the seal: a harness cannot condition
    on a number it was never handed.

    The seal is written when the stream is exhausted. A consumer that abandons the iterator
    half way gets no seal, which is correct — half a world has no truth to tell.
    """
    exposure: list[StoreExposure] = []
    for item in generate_module.generate(
        run.world,
        seed=run.seed,
        scale=run.scale,
        chain=run.chain,
        assignment=run.assignment,
        control=run.control,
        treatment=run.treatment,
        only_stores=only_stores,
    ):
        if isinstance(item, StoreExposure):
            exposure.append(item)
            continue
        yield item
    if seal_into is not None:
        seal_module.seal(_truth(run, exposure, only_stores), seal_into)


def _truth(
    run: Run, exposure: list[StoreExposure], only_stores: Sequence[str] | None
) -> WorldTruth:
    world = run.world
    return WorldTruth(
        world=world.id,
        title=world.title,
        seed=run.seed,
        scale=run.scale.name,
        control_policy={
            "policy_id": run.control.policy_id,
            "steps": [asdict(s) for s in run.control.steps],
        },
        treatment_policy={
            "policy_id": run.treatment.policy_id,
            "steps": [asdict(s) for s in run.treatment.steps],
        },
        injection={
            "clustered_pct": world.clustered_pct,
            "treats": world.treats,
            "spillover_pct": world.spillover_pct,
            "ack_failure_pct_treated": world.ack_failure_pct_treated,
            "novelty_half_life_days": world.novelty_half_life_days,
            "novelty_boost_pct": world.novelty_boost_pct,
            "demand_tail_alpha": world.demand_tail_alpha,
            "violates": world.violates,
            "correct_behaviour": world.correct_behaviour,
        },
        exposure_by_store=[asdict(record) for record in exposure],
        restricted_to_stores=list(only_stores) if only_stores is not None else None,
        totals={
            "stores": len(exposure),
            "treated_stores": sum(1 for r in exposure if r.arm == Arm.TREATMENT.value),
            "decisions": sum(r.decisions for r in exposure),
            "acks_accepted": sum(r.acks_accepted for r in exposure),
            "acks_failed": sum(r.acks_failed for r in exposure),
            "neighbour_pairs": len(run.chain.neighbour_pairs),
        },
    )


def count(run: Run, *, only_stores: Sequence[str] | None = None) -> dict[str, int]:
    """How many records of each kind, without keeping any of them.

    A count over `only_stores` is a count over those stores. `CLAUDE.md` forbids extrapolating
    a corpus-size figure to the full estate, and the same rule applies one level down: nothing
    here multiplies a slice up into a total, and the README's scenario figure comes from a run
    with no restriction at all.
    """
    tally: Counter[str] = Counter()
    for event in events(run, only_stores=only_stores):
        tally[stream_of(event)] += 1
    return {stream: tally.get(stream, 0) for stream in STREAMS}


def write(
    run: Run,
    directory: Path,
    *,
    fmt: Format | str = Format.CSV,
    only_stores: Sequence[str] | None = None,
) -> dict[str, int]:
    """Materialise a world: four event streams, three reference tables, and the seal.

    **Two targets, and the second one arrived with the thing that reads it.** Gzipped CSV is
    what this package has written since it existed, and it stays the default: the product of
    this package is a **stream**, consumed in process by the A/A harness, and `write` is how a
    world is looked at. `docs/DECISIONS.md` deferred Parquet on exactly that argument —
    *"adding a Parquet engine to `corpus/` … to write files nothing in this phase reads would
    be a dependency bought for a screenshot"* — and named the unlock: **the S3 bulk load in
    T009, the first thing that needs files on disk in the format the lakehouse reads.**

    So `fmt=Format.PARQUET` is that target, and `corpus/world/parquet.py` is the engine. What
    it is not is a second definition of anything: the event streams take their columns from
    the same dataclasses the CSV header comes from, and the reference tables from the one
    declaration in `REFERENCE_TABLES` below.

    The seal, the manifest and the counts do not move with the format.
    """
    target = as_format(fmt)
    directory.mkdir(parents=True, exist_ok=True)
    tally: Counter[str] = Counter()
    # All four files open at once, because the generator emits one interleaved stream and
    # writing them one at a time would mean generating the world four times.
    streams = _parquet_streams if target is Format.PARQUET else _csv_streams
    with streams(directory) as deliver:
        for event in events(run, seal_into=directory, only_stores=only_stores):
            stream = stream_of(event)
            deliver(stream, event)
            tally[stream] += 1
    _write_reference(run, directory, only_stores, target)
    (directory / "run.json").write_text(
        json.dumps(
            {
                "world": run.world.id,
                "title": run.world.title,
                "seed": run.seed,
                "scale": run.scale.name,
                "format": target.value,
                "stores": len(run.chain.stores),
                "skus": len(run.chain.products),
                "days": run.scale.days,
                "control_policy": run.control.policy_id,
                "treatment_policy": run.treatment.policy_id,
                "restricted_to_stores": list(only_stores) if only_stores else None,
                "counts": {stream: tally.get(stream, 0) for stream in STREAMS},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {stream: tally.get(stream, 0) for stream in STREAMS}


def as_format(fmt: Format | str) -> Format:
    """A declared format, or a refusal naming the declared ones. Never a silent default."""
    if isinstance(fmt, Format):
        return fmt
    try:
        return FORMATS[fmt]
    except KeyError:
        raise ValueError(
            f"unknown format {fmt!r}; declared formats are {sorted(FORMATS)}"
        ) from None


@contextmanager
def _csv_streams(directory: Path) -> Iterator[Callable[[str, Event], None]]:
    """One gzipped CSV per stream, header written when that stream's first record arrives."""
    with ExitStack() as open_files:
        writers = {
            stream: csv.writer(
                open_files.enter_context(
                    gzip.open(directory / f"{stream}.csv.gz", "wt", newline="", encoding="utf-8")
                )
            )
            for stream in STREAMS
        }
        headers_written: set[str] = set()

        def deliver(stream: str, event: Event) -> None:
            if stream not in headers_written:
                writers[stream].writerow(field_names(event))
                headers_written.add(stream)
            writers[stream].writerow(_row(event))

        yield deliver


@contextmanager
def _parquet_streams(directory: Path) -> Iterator[Callable[[str, Event], None]]:
    """One Parquet file per stream, the schema taken from the dataclass behind it.

    A Parquet file carries its schema in the footer whether or not a row was ever written, so
    there is no lazy header here and an empty stream is an empty table rather than an empty
    file — which is the one thing this target does that the CSV one cannot.
    """
    with ExitStack() as open_files:
        writers = {
            stream: open_files.enter_context(
                ParquetWriter(directory / f"{stream}.parquet", columns_for(STREAM_TYPES[stream]))
            )
            for stream in STREAMS
        }

        def deliver(stream: str, event: Event) -> None:
            writers[stream].write(list(asdict(event).values()))

        yield deliver


def _row(event: Event) -> list[object]:
    return [_cell(value) for value in asdict(event).values()]


def _cell(value: object) -> object:
    return "" if value is None else value


def _reference_cell(value: object) -> object:
    """A reference table's CSV cell, exactly as this package has always written one.

    It is not `_cell`: the event streams stringify a `datetime` the way `str()` does, with a
    space, and the reference tables call `isoformat()`, with a `T`. **The two have differed
    since both were written and this branch does not unify them** — changing either rewrites
    the bytes of files something already reads, which is a restatement rather than a format.
    """
    if isinstance(value, datetime | date):
        return value.isoformat()
    return "" if value is None else value


@dataclass(frozen=True, slots=True)
class ReferenceTable:
    """One ERP table, declared once and rendered into whichever format was asked for.

    The columns are the Parquet schema **and** the CSV header, for the reason
    `events.field_names` gives about the event streams one file over: a header list written
    out by hand beside a column list is a second definition of the same table, and the day
    somebody inserts a column the two stop agreeing without a word.
    """

    name: str
    columns: tuple[Column, ...]
    rows: Callable[[Run, set[str] | None], Iterator[tuple[object, ...]]]

    @property
    def header(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.columns)


def _store_rows(run: Run, wanted: set[str] | None) -> Iterator[tuple[object, ...]]:
    for store in run.chain.stores:
        if wanted is not None and store.store_id not in wanted:
            continue
        yield (
            store.store_id,
            store.town,
            store.x_m,
            store.y_m,
            store.store_format,
            store.size_index,
            store.size_band,
            store.pricing_zone,
            store.opened_on,
            run.assignment[store.store_id].value,
        )


def _product_rows(run: Run, wanted: set[str] | None) -> Iterator[tuple[object, ...]]:
    del wanted  # a product master is not restricted; see `_write_reference`
    for product in run.chain.products:
        yield (
            product.sku_id,
            product.category,
            product.name,
            product.base_price_cents,
            product.shelf_life_days,
            product.substitute_of,
        )


def _cost_rows(run: Run, wanted: set[str] | None) -> Iterator[tuple[object, ...]]:
    del wanted  # nor is the ledger: an as-of join needs every step, whoever sold the item
    for product in run.chain.products:
        for step in run.chain.cost_steps(product.sku_id):
            yield (step.sku_id, step.effective_from, step.unit_cost_cents)


#: The three tables the ERP hands over rather than the till. Declared here in one place, so
#: `pipelines/ingest/` can export a drop and load it back without a second opinion about what
#: a column is called or what type it holds.
REFERENCE_TABLES: tuple[ReferenceTable, ...] = (
    ReferenceTable(
        name="store_master",
        columns=(
            Column("store_id", Kind.STRING),
            Column("town", Kind.STRING),
            Column("x_m", Kind.INT64),
            Column("y_m", Kind.INT64),
            Column("store_format", Kind.STRING),
            Column("size_index", Kind.DOUBLE),
            Column("size_band", Kind.STRING),
            Column("pricing_zone", Kind.STRING),
            Column("opened_on", Kind.DATE),
            Column("arm", Kind.STRING),
        ),
        rows=_store_rows,
    ),
    ReferenceTable(
        name="product_master",
        columns=(
            Column("sku_id", Kind.STRING),
            Column("category", Kind.STRING),
            Column("name", Kind.STRING),
            Column("base_price_cents", Kind.INT64),
            Column("shelf_life_days", Kind.INT64),
            # A SKU that substitutes nothing is absent rather than empty. In the CSV it is
            # written as `''` and cannot be told from a blank name; the Parquet column says
            # null, which is why the loader is handed a type per column rather than guessing.
            Column("substitute_of", Kind.STRING, optional=True),
        ),
        rows=_product_rows,
    ),
    ReferenceTable(
        name="cost_ledger",
        columns=(
            Column("sku_id", Kind.STRING),
            Column("effective_from", Kind.TIMESTAMP),
            Column("unit_cost_cents", Kind.INT64),
        ),
        rows=_cost_rows,
    ),
)


def _write_reference(
    run: Run, directory: Path, only_stores: Sequence[str] | None, fmt: Format
) -> None:
    """The three tables the ERP's file drops carry, not the till.

    They are written whole even under a store restriction — a product master truncated to the
    stores you happened to generate is not a product master, and the cost ledger is what makes
    an as-of join possible at all.
    """
    wanted = set(only_stores) if only_stores is not None else None
    for table in REFERENCE_TABLES:
        if fmt is Format.PARQUET:
            with ParquetWriter(directory / f"{table.name}.parquet", table.columns) as writer:
                writer.write_rows(table.rows(run, wanted))
            continue
        with gzip.open(
            directory / f"{table.name}.csv.gz", "wt", newline="", encoding="utf-8"
        ) as handle:
            out = csv.writer(handle)
            out.writerow(table.header)
            for row in table.rows(run, wanted):
                out.writerow([_reference_cell(value) for value in row])
