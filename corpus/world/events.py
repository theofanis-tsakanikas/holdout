"""What a world emits. One dataclass per bronze table, in the source's shape.

`CLAUDE.md`'s bronze layer is *"one table per source, in the source's shape"*, and nothing is
transformed at ingestion. These are those shapes, as a chain's own systems would hand them
over — a till, an electronic shelf label, a stock count — and not one of them carries a field
the system would like them to carry.

**Every record carries both its event time and its arrival time.** In this package the two are
equal: a generator that invented lateness would be inventing the pathology `pipelines/ingest`
exists to inject, and two places deciding how late a record is would eventually disagree. The
column is here because the shape is the source's, and the driver in T009 is what moves it.

**`transaction_id` is real.** `CLAUDE.md`: *"Deduplication uses a business key, never a hash of
the payload. The same receipt line delivered twice is one event; two identical baskets in the
same second at the same till are two."* A simulated POS can supply a genuine transaction id, so
it does, and the world deliberately produces the colliding case — two baskets with identical
contents at the same till in the same second, carrying different ids.

**Timestamps are naive, and that is a decision.** A business date and a trading hour belong
to the store: a markdown at 21:00 is 21:00 where the shop is, and the chain in this scenario
runs in one country. Attaching a zone would be attaching a fact nobody in the scenario has, and
converting to UTC would put a store's closing hour on the wrong business date twice a year.

**No customer dimension anywhere.** Not a household, not a loyalty number, not a segment.
Claim 7 is structural in `holdout.core.decision`, and it would be worth much less if the data
underneath it had a person in it. `tests/corpus/test_world_events.py` asserts the field sets.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime
from typing import Any

#: Every stream a world emits, in the order `write` lays them out.
STREAMS: tuple[str, ...] = ("pos_lines", "esl_acks", "shelf_days", "price_decisions")

#: Field names that would make a decision addressable to a person. A world that grew one of
#: these would defeat claim 7 one layer below where claim 7 is proved.
FORBIDDEN_FIELD_MARKERS: tuple[str, ...] = (
    "customer",
    "household",
    "loyalty",
    "shopper",
    "member",
    "segment",
    "person",
    "email",
    "phone",
    "card",
)


@dataclass(frozen=True, slots=True)
class PosLine:
    """One line of one receipt. The revenue side of the margin, and an inventory movement."""

    transaction_id: str
    line_no: int
    store_id: str
    sku_id: str
    till_id: str
    event_ts: datetime
    arrival_ts: datetime
    qty: int
    unit_price_cents: int
    line_total_cents: int


@dataclass(frozen=True, slots=True)
class EslAck:
    """An electronic shelf label answering back — or, when `accepted` is false, not.

    `CLAUDE.md`: *"The ESL acknowledgement is a first-class source, not a log. It is the only
    evidence that a price reached the shelf. Without it every experiment measures intentions
    instead of actions."* A rejected acknowledgement means the label kept the price it had, so
    `price_displayed_cents` is what shoppers actually paid and `price_decided_cents` is what
    the chain meant them to.
    """

    store_id: str
    sku_id: str
    event_ts: datetime
    arrival_ts: datetime
    price_decided_cents: int
    price_displayed_cents: int
    accepted: bool
    policy_id: str
    ladder_step: int


@dataclass(frozen=True, slots=True)
class ShelfDay:
    """One store, one SKU, one day: what arrived, what sold, what was thrown away.

    `stocked_out_from_hour` is observable — it is derivable from inventory movements, which is
    why `CLAUDE.md` puts stock-out marking in silver where the movements are. What is **not**
    here is the demand that went unserved after it: a stock-out means those baskets were never
    recorded, and a corpus that emitted them would be handing claim 4 the answer it is
    supposed to have to reconstruct.
    """

    store_id: str
    sku_id: str
    business_date: str
    delivered_qty: int
    sold_qty: int
    wasted_qty: int
    closing_qty: int
    stocked_out_from_hour: int | None
    unit_cost_cents: int


@dataclass(frozen=True, slots=True)
class PriceDecision:
    """What the chain decided, before anything was dispatched anywhere.

    The world's analogue of `gold.decisions`: written at decision time, immutable, and
    separate from what the shelf ended up showing. `price_decided_cents` here and
    `price_displayed_cents` on the acknowledgement are two columns because they differ.
    """

    store_id: str
    sku_id: str
    event_ts: datetime
    arrival_ts: datetime
    arm: str
    policy_id: str
    ladder_step: int
    base_price_cents: int
    price_decided_cents: int
    hours_to_expiry: int


#: The tagged stream a `generate` call yields. One pass writes every table.
Event = PosLine | EslAck | ShelfDay | PriceDecision

_STREAM_OF: dict[type, str] = {
    PosLine: "pos_lines",
    EslAck: "esl_acks",
    ShelfDay: "shelf_days",
    PriceDecision: "price_decisions",
}


def stream_of(event: Event) -> str:
    return _STREAM_OF[type(event)]


def field_names(record: Any) -> tuple[str, ...]:
    """The column order of one record's table, taken from the dataclass rather than restated.

    A header list written out by hand beside the dataclass is a second definition of the
    schema, and the day someone inserts a field the two stop agreeing silently.
    """
    return tuple(f.name for f in fields(record))
