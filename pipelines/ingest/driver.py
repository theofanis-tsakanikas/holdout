"""The driver: when a record arrives, and how many times.

`corpus/world/generate.py` says what this module is for, in its own docstring, and the division
is deliberate:

> *"Not in event-time order: interleaving a hundred stores into one timeline is the ingest
> driver's job (T009), which is also where lateness and duplicates are injected. A generator
> that ordered by time would be deciding what 'late' means in a second place."*

And `corpus/world/events.py`, on the two timestamps every record carries:

> *"In this package the two are equal ... the driver in T009 is what moves it."*

So the corpus produces records whose `event_ts` and `arrival_ts` are equal, store by store. This
module produces the same records in **arrival order**, with `arrival_ts` moved, some of them
delivered twice. Nothing else about a record changes: bronze is the source's shape, and a driver
that corrected a field would be a second place where that shape is decided.

Four pathologies, which are the four `TASKS.md` names for T009
-------------------------------------------------------------
**Interleaving.** The corpus is store-major — a store's eight months, then the next store's. A
till does not wait for another store to finish, so the driver merges every store's stream into
one timeline ordered by arrival. That is the *"correct distribution over time"* half, and it is
the only one of the four that is not an injury: it is what the data would have looked like all
along if the generator had not been organised for reproducibility.

**Late arrivals.** A share of records arrive after their event time, by a lognormal delay. Late
is not a synonym for out-of-order — most late records still arrive in order relative to each
other, and the ones that do not are what an as-of join has to survive.

**Duplicates.** A share of records are delivered **twice, unchanged**, which is what an
at-least-once transport does. `CLAUDE.md` is explicit that deduplication is a business key and
never a payload hash, so the duplicate carries the same `transaction_id` and is genuinely the
same event — and the corpus separately produces two *different* baskets with identical contents
at one till in one second, which are two events and must survive.

**An outage.** One store stops delivering for a window and then sends everything at once: every
record whose event time falls inside the window arrives at the moment the window ends, in event
order, in one burst. It is the shape that breaks a watermark, and it is the reason silver's
quarantine and the as-of reference exist.

What this module does not do
----------------------------
**It serves no claim.** It produces the input the pipelines are built on. Nothing here is
evidence for claims 1 to 7, and `pipelines/ingest/__init__.py` says so at more length.

**It does not drop records.** A transport that lost them would be a fifth pathology nobody
declared, and the counts a downstream test asserts would stop being checkable against the
corpus. Every record the corpus produced is delivered at least once.

**It has no opinion about arms.** It never reads one, and `PriceDecision.arm` passes through
untouched like every other field.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import timedelta
from typing import TYPE_CHECKING

from corpus.world import rng
from corpus.world.events import EslAck, PosLine, PriceDecision, ShelfDay, field_names, stream_of

#: The records that carry an arrival. **Named by type rather than found by `getattr`**, because
#: which tables have an arrival time is a fact about bronze and belongs where a reader can see
#: it: `ShelfDay` is a day's summary with a `business_date` and no timestamps, and a driver that
#: invented an arrival for it would be inventing a fact about a table that does not have one.
Timed = PosLine | EslAck | PriceDecision

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import datetime

    from corpus.world.events import Event

    from pipelines.ingest.sink import Sink


class OutageError(ValueError):
    """An outage that could never happen: no store, or a window with no hours in it."""


@dataclass(frozen=True, slots=True)
class Outage:
    """One store, silent from `start` for `hours`, then everything at once.

    Two hours is what `TASKS.md` names. It is a parameter rather than a constant because the
    number is the scenario's and not the mechanism's, and a mechanism that hard-coded it could
    not be tested on a window short enough to assert against.
    """

    store_id: str
    start: datetime
    hours: int

    def __post_init__(self) -> None:
        if not self.store_id:
            raise OutageError("an outage needs a store; a chain-wide one is a different event")
        if self.hours < 1:
            raise OutageError(
                f"an outage of {self.hours}h is not an outage. A store that stops for no time "
                "delivers exactly as it would have, and the pathology would be silently absent."
            )

    @property
    def end(self) -> datetime:
        return self.start + timedelta(hours=self.hours)

    def holds(self, record: Event) -> bool:
        store = getattr(record, "store_id", None)
        if store != self.store_id:
            return False
        moment = _event_time(record)
        return moment is not None and self.start <= moment < self.end


@dataclass(frozen=True, slots=True)
class Pathologies:
    """How injured the stream is. Every field is a share or a shape, never a count.

    **Shares rather than counts**, so the same declaration describes a smoke world and the
    scenario without being re-derived per scale — which is the defect `TASKS.md`'s own
    *"100 stores"* carried until it was restated.
    """

    #: Share of records that arrive after their event time.
    late_share: float = 0.05
    #: Median and sigma of the lognormal delay, in seconds, for a record that is late.
    late_median_seconds: float = 90.0
    late_sigma: float = 1.2
    #: Share of records delivered twice, unchanged.
    duplicate_share: float = 0.01
    #: The store that goes silent, or `None`.
    outage: Outage | None = None

    def __post_init__(self) -> None:
        for name in ("late_share", "duplicate_share"):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} is a share and {value} is not one")
        if self.late_median_seconds <= 0 or self.late_sigma <= 0:
            raise ValueError("a lateness with no spread and no median is not a delay")


#: Declared pathologies and nothing beyond them. The values are a starting point rather than a
#: measurement of any real chain — nobody here has a real chain's arrival distribution, and a
#: number invented and then quoted as though it were measured is the defect this repository
#: spends most of its time correcting. They are declared, and they are named as declared.
DECLARED = Pathologies()


def _event_time(record: Event) -> datetime | None:
    return None if isinstance(record, ShelfDay) else record.event_ts


def _identity(record: Event) -> tuple[object, ...]:
    """What a draw about this record is keyed on.

    Keyed by the record rather than by its position, for the reason `corpus/world/rng.py`
    gives about the world itself: whether a record is late must not depend on how many records
    came before it, or driving one store would produce a different stream from driving a
    hundred and neither would be reproducible.
    """
    fields = field_names(record)
    return (type(record).__name__, *(str(getattr(record, name)) for name in fields))


def _delay(seed: str, key: tuple[object, ...], pathologies: Pathologies) -> timedelta:
    if rng.unit_interval(seed, "late?", *key) >= pathologies.late_share:
        return timedelta(0)
    stream = rng.stream(seed, "late-by", *key)
    seconds = rng.lognormal(stream, pathologies.late_median_seconds, pathologies.late_sigma)
    return timedelta(seconds=round(seconds, 3))


def _duplicated(seed: str, key: tuple[object, ...], pathologies: Pathologies) -> bool:
    return rng.unit_interval(seed, "duplicate?", *key) < pathologies.duplicate_share


def deliveries(
    records: Iterable[Event],
    *,
    seed: str,
    pathologies: Pathologies = DECLARED,
) -> list[tuple[str, Event]]:
    """Every delivery, in arrival order: `(stream, record)`, duplicates included.

    A list rather than an iterator, and deliberately: arrival order is not knowable until every
    record has been seen, because a record generated last can arrive first. Streaming this would
    mean buffering the whole world anyway and pretending otherwise.

    **A record with no `arrival_ts` is delivered unchanged and on time.** `ShelfDay` is one — it
    is a day's summary rather than an event, it has a `business_date` and no timestamps, and a
    driver that invented an arrival for it would be inventing a fact about a table that does not
    have one.
    """
    delivered: list[tuple[datetime | None, int, str, Event]] = []
    for position, record in enumerate(records):
        stream = stream_of(record)
        if isinstance(record, ShelfDay):
            delivered.append((None, position, stream, record))
            continue

        # One identity per record, two draws from it. Computing it twice was 38,621 extra
        # field walks on a smoke world, which is the sort of cost that arrives in `make check`
        # and is noticed weeks later.
        key = _identity(record)
        moment = record.arrival_ts + _delay(seed, key, pathologies)
        outage = pathologies.outage
        if outage is not None and outage.holds(record):
            # Everything at once: the burst leaves when the window closes, and a record that
            # was already going to be later than that stays later.
            moment = max(moment, outage.end)
        delivered.append((moment, position, stream, replace(record, arrival_ts=moment)))
        if _duplicated(seed, key, pathologies):
            delivered.append((moment, position, stream, replace(record, arrival_ts=moment)))

    dated = [row for row in delivered if row[0] is not None]
    undated = [row for row in delivered if row[0] is None]
    dated.sort(key=lambda row: (row[0], row[1]))
    return [(stream, record) for _, _, stream, record in [*dated, *undated]]


def drive(
    records: Iterable[Event],
    sink: Sink,
    *,
    seed: str,
    pathologies: Pathologies = DECLARED,
) -> dict[str, int]:
    """Deliver every record to `sink` in arrival order. Returns the count per stream."""
    counts: dict[str, int] = {}
    for stream, record in deliveries(records, seed=seed, pathologies=pathologies):
        sink.deliver(stream, record)
        counts[stream] = counts.get(stream, 0) + 1
    sink.close()
    return counts


def out_of_order(delivered: Iterable[tuple[str, Event]]) -> int:
    """How many deliveries carry an event time earlier than one already delivered.

    Published rather than asserted: it is the figure that says whether the stream is worth
    driving at all, and a silver layer that handled it would be handling something measured.
    """
    seen: dict[str, datetime] = {}
    behind = 0
    for stream, record in delivered:
        moment = _event_time(record)
        if moment is None:
            continue
        high = seen.get(stream)
        if high is not None and moment < high:
            behind += 1
        else:
            seen[stream] = moment
    return behind
