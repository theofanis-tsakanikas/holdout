"""The four pathologies T009 declares, each asserted on a stream the corpus actually produced.

**Driven from a real world rather than from hand-made records**, at the smallest declared scale.
A driver tested on three records invented here would be tested on the shape its author pictured
— `CLAUDE.md` names that as this project's most frequent defect and lists six instances of it.
The corpus is the one source of records nobody in this file chose.

**What is asserted is a property, never a count.** The pathologies are shares, the world is a
draw, and an assertion that 47 records were late is an assertion about one seed. The exception
is the outage, which is deterministic by construction: every record inside the window arrives at
the moment the window closes, and *every* is checkable.
"""

from __future__ import annotations

from datetime import timedelta
from itertools import pairwise
from typing import TYPE_CHECKING

import pytest
from corpus.world import events as world_events
from corpus.world import prepare
from corpus.world.events import stream_of
from pipelines.ingest.driver import DECLARED, Outage, OutageError, Pathologies, deliveries, drive
from pipelines.ingest.sink import JsonlSink, MemorySink

if TYPE_CHECKING:
    from pathlib import Path

    from corpus.world.events import Event

SEED = "t009-driver"


def _world_records() -> list[Event]:
    """One smoke world through the corpus's own entry point: store-major, arrival == event.

    `prepare` + `events` rather than `generate` directly, because `generate`'s docstring says a
    caller that consumes it is holding the exposure truth in its hand and should not be.
    """
    return list(world_events(prepare("W1", seed=SEED, scale="smoke")))


@pytest.fixture(scope="module")
def records() -> list[Event]:
    return _world_records()


# ------------------------------------------------------------------ nothing is lost or altered


def test_every_record_is_delivered_at_least_once(records: list[Event]) -> None:
    """A transport that dropped records would be a fifth pathology nobody declared."""
    delivered = deliveries(records, seed=SEED)
    assert len(delivered) >= len(records)
    once = {(stream, id(record)) for stream, record in delivered}
    assert len(once) >= len(records)


def test_only_the_arrival_time_ever_changes(records: list[Event]) -> None:
    """Bronze is the source's shape. A driver that corrected a field would be a second place
    where that shape is decided, which is what `CLAUDE.md` forbids at ingestion.

    Compared as **multisets keyed on every field but `arrival_ts`**, which is O(n) — the first
    version of this test matched each original against every delivery and was quadratic: 28k x
    28k on a smoke world, six minutes of `make check`. A test that is correct and unaffordable
    goes the way of the file this session spent the morning taking back out of the suite.
    """
    from collections import Counter
    from dataclasses import asdict

    def shape(record: Event) -> tuple[str, str]:
        row = {k: v for k, v in asdict(record).items() if k != "arrival_ts"}
        return (stream_of(record), repr(sorted(row.items(), key=str)))

    produced = Counter(shape(record) for record in records)
    delivered = Counter(shape(record) for _, record in deliveries(records, seed=SEED))

    assert set(delivered) == set(produced), (
        "a record came back with a field other than arrival_ts moved, or one went missing"
    )
    for key, count in produced.items():
        assert delivered[key] >= count, f"{key[0]} lost a record"


# ---------------------------------------------------------------------------- the four of them


def test_the_stream_is_interleaved_rather_than_store_major(records: list[Event]) -> None:
    """The corpus emits one store's whole history, then the next. A till does not wait."""
    stores_in_corpus = [record.store_id for record in records if hasattr(record, "store_id")]
    runs_before = sum(1 for a, b in pairwise(stores_in_corpus) if a != b)

    delivered = [
        record.store_id
        for _, record in deliveries(records, seed=SEED)
        if hasattr(record, "store_id")
    ]
    runs_after = sum(1 for a, b in pairwise(delivered) if a != b)

    assert len({*stores_in_corpus}) > 1, "a one-store world cannot show interleaving"
    assert runs_after > runs_before, (
        f"the delivered stream changes store {runs_after} times against the corpus's "
        f"{runs_before}; it is still store-major and nothing was interleaved"
    )


def test_some_records_arrive_after_their_event_time(records: list[Event]) -> None:
    late = [
        record
        for _, record in deliveries(records, seed=SEED)
        if getattr(record, "arrival_ts", None) is not None and record.arrival_ts > record.event_ts  # type: ignore[union-attr]
    ]
    assert late, "no record arrived late, so the lateness pathology is absent"


def test_nothing_arrives_before_it_happened(records: list[Event]) -> None:
    """The one direction that is not a pathology but a broken clock."""
    for _, record in deliveries(records, seed=SEED):
        arrival = getattr(record, "arrival_ts", None)
        if arrival is not None:
            assert arrival >= record.event_ts  # type: ignore[union-attr]


def test_some_records_are_delivered_twice_unchanged(records: list[Event]) -> None:
    """At-least-once, with the business key intact — `CLAUDE.md`: deduplication uses a business
    key and never a payload hash, so a duplicate has to be the *same* event."""
    from dataclasses import asdict

    counts: dict[tuple[str, str], int] = {}
    for stream, record in deliveries(records, seed=SEED):
        key = (stream, repr(sorted(asdict(record).items())))
        counts[key] = counts.get(key, 0) + 1
    assert any(n > 1 for n in counts.values()), "nothing was delivered twice"


def test_a_store_that_drops_sends_everything_at_once(records: list[Event]) -> None:
    """Deterministic by construction, so *every* record in the window is checkable."""
    timed = [r for r in records if getattr(r, "event_ts", None) is not None]
    store = getattr(timed[0], "store_id", None)
    assert store is not None
    start = min(r.event_ts for r in timed if getattr(r, "store_id", None) == store)  # type: ignore[union-attr]
    outage = Outage(store_id=store, start=start + timedelta(hours=6), hours=2)

    quiet = Pathologies(late_share=0.0, duplicate_share=0.0, outage=outage)
    delivered = deliveries(records, seed=SEED, pathologies=quiet)

    held = [
        record
        for _, record in delivered
        if getattr(record, "store_id", None) == store
        and getattr(record, "event_ts", None) is not None
        and outage.start <= record.event_ts < outage.end  # type: ignore[union-attr]
    ]
    assert held, "the window caught no records, so the outage asserts nothing"
    assert {record.arrival_ts for record in held} == {outage.end}, (  # type: ignore[union-attr]
        "records inside the outage did not all arrive together when it ended"
    )

    others = [
        record
        for _, record in delivered
        if getattr(record, "store_id", None) != store
        and getattr(record, "event_ts", None) is not None
    ]
    assert all(record.arrival_ts == record.event_ts for record in others), (  # type: ignore[union-attr]
        "an outage at one store delayed another store's records"
    )


# ------------------------------------------------------------------------------ reproducibility


def test_the_same_seed_gives_the_same_stream(records: list[Event]) -> None:
    from dataclasses import asdict

    first = [(s, asdict(r)) for s, r in deliveries(records, seed=SEED)]
    second = [(s, asdict(r)) for s, r in deliveries(records, seed=SEED)]
    assert first == second


def test_a_record_s_lateness_does_not_depend_on_what_came_before_it(
    records: list[Event],
) -> None:
    """The property `corpus/world/rng.py` has and the reason this module borrows it rather than
    writing a second one: driving one store must produce the same arrivals as driving all of
    them, or nothing about the stream is reproducible in pieces."""
    from dataclasses import asdict

    store = getattr(records[0], "store_id", None)
    assert store is not None
    one = [r for r in records if getattr(r, "store_id", None) == store]

    whole = {
        (s, repr(sorted((k, v) for k, v in asdict(r).items() if k != "arrival_ts"))): r.arrival_ts  # type: ignore[union-attr]
        for s, r in deliveries(records, seed=SEED)
        if getattr(r, "arrival_ts", None) is not None
    }
    alone = {
        (s, repr(sorted((k, v) for k, v in asdict(r).items() if k != "arrival_ts"))): r.arrival_ts  # type: ignore[union-attr]
        for s, r in deliveries(one, seed=SEED)
        if getattr(r, "arrival_ts", None) is not None
    }
    assert alone, "the single store produced nothing"
    for key, arrival in alone.items():
        assert whole[key] == arrival


# -------------------------------------------------------------------------------- the refusals


@pytest.mark.parametrize("hours", [0, -1])
def test_an_outage_with_no_hours_is_refused(hours: int) -> None:
    timed_start = DECLARED
    assert timed_start.outage is None
    with pytest.raises(OutageError, match="not an outage"):
        Outage(store_id="S001", start=__import__("datetime").datetime(2026, 1, 1), hours=hours)


def test_a_share_outside_zero_to_one_is_refused() -> None:
    with pytest.raises(ValueError, match="is a share"):
        Pathologies(late_share=1.5)


# ------------------------------------------------------------------------------------ the sink


def test_the_local_sink_writes_one_file_per_stream(records: list[Event], tmp_path: Path) -> None:
    sink = JsonlSink(tmp_path)
    counts = drive(records, sink, seed=SEED)
    assert counts
    for stream, n in counts.items():
        assert (tmp_path / f"{stream}.jsonl").exists()
        assert sum(1 for _ in sink.read(stream)) == n


def test_the_memory_sink_keeps_delivery_order(records: list[Event]) -> None:
    sink = MemorySink()
    drive(records, sink, seed=SEED)
    assert sink.closed
    assert [s for s, _ in sink.delivered] == [s for s, _ in deliveries(records, seed=SEED)]
