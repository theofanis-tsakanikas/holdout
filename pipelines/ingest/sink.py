"""Where the driver's records go, behind one small interface.

**A sink rather than a file path, and the reason is phase 3.** On the estate this driver writes
to **Zerobus**; here there is no workspace and no credentials, so it writes locally. Those are
two sinks and one driver. Writing the driver against files would mean rewriting it when the
workspace exists; writing it against an iterator would mean wrapping it. Neither is a decision
worth making twice, and the record already says which side moves: `CLAUDE.md`'s sources table
puts POS lines, scale labels and ESL acknowledgements through Zerobus **for the live day only**.

**What a sink may not do is change a record.** It receives what the driver produced and is
responsible for nothing else — no ordering, no deduplication, no schema. A sink that corrected
anything would be a second place where the shape of bronze is decided, and bronze's whole rule
is that it is the source's shape.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import TracebackType

    from corpus.world.events import Event


class Sink(Protocol):
    """Somewhere a record can be delivered. Two methods, and neither returns anything."""

    def deliver(self, stream: str, record: Event) -> None:
        """Take one record. `stream` is the bronze table it belongs to."""

    def close(self) -> None:
        """Release whatever was held. Called once, and a sink may be closed twice safely."""


class MemorySink:
    """Everything delivered, in delivery order, kept in a list.

    For tests and for the pathology assertions: the order a record arrives in **is** the thing
    under test, so a sink that sorted or grouped would be answering the question.
    """

    def __init__(self) -> None:
        self.delivered: list[tuple[str, Event]] = []
        self.closed = False

    def deliver(self, stream: str, record: Event) -> None:
        self.delivered.append((stream, record))

    def close(self) -> None:
        self.closed = True

    def records(self, stream: str) -> list[Event]:
        return [record for name, record in self.delivered if name == stream]


def _plain(value: Any) -> Any:
    """JSON has no datetime and no date. Both go out in ISO 8601 and nothing else changes.

    Not a schema and not a transformation: a `datetime` that reached `json.dumps` unconverted
    would raise, so the choice is between this and no local sink at all. The gzipped-CSV
    decision in `docs/DECISIONS.md` is the same shape one directory over — a materialisation
    that exists so a stream can be looked at.
    """
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


class JsonlSink:
    """One newline-delimited JSON file per bronze table, under a directory.

    **Delivery order is preserved and event order is not**, which is the point: a file whose
    lines are sorted by `event_ts` would have thrown away the lateness the driver was asked to
    inject. Reading one of these back and finding it out of order is the artefact working.
    """

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self._open: dict[str, Any] = {}
        self.counts: dict[str, int] = {}

    def deliver(self, stream: str, record: Event) -> None:
        handle = self._open.get(stream)
        if handle is None:
            handle = (self.directory / f"{stream}.jsonl").open("w", encoding="utf-8")
            self._open[stream] = handle
        row = {key: _plain(value) for key, value in asdict(record).items()}
        handle.write(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n")
        self.counts[stream] = self.counts.get(stream, 0) + 1

    def close(self) -> None:
        for handle in self._open.values():
            handle.close()
        self._open.clear()

    def __enter__(self) -> JsonlSink:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def read(self, stream: str) -> Iterator[dict[str, Any]]:
        path = self.directory / f"{stream}.jsonl"
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                parsed: dict[str, Any] = json.loads(line)
                yield parsed
