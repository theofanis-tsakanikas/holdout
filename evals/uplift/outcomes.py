"""The grouped path — the world's events aggregated to the metric's declared grain.

This is the shape a `GROUP BY` has: one pass over the stream, accumulating the metric's three
terms into a dictionary keyed by `(store_id, iso_year, iso_week, category)`. It is what feeds
`close()`, and it is one of the two implementations `U10` compares. The other is
`reference.py`, which loops over every event holding a running ledger and resolves the as-of
cost by walking forward rather than by indexing. **They may not share a line**, and the only
thing they have in common is the contract they were both written from.

The metric, from `contracts/metrics/category_margin_per_store_week.v3.yaml`::

    sum(s.qty * s.price_paid)
    - sum(s.qty * s.unit_cost_as_of)
    - sum(w.qty * w.unit_cost_as_of)

Three things about it are decisions rather than transcription, so they are here rather than
implied.

**The cost is resolved as of the moment of the sale, never the current one.** `CLAUDE.md`: *"A
sale at 14:00 joins to the cost as it was known at 14:00. Joining to the current cost table
silently rewrites every historical margin."* The ledger is read from the chain as data and
indexed here; the disposal's cost is the one the `ShelfDay` record already carries, which is
the cost as it was known when the day opened.

**A unit's outcome is the window mean, not the window total.** The metric is *per store-week*
and the experiment's unit is a store, so the quantity a difference of means is taken over is
the store's mean over the declared window. It is also the one place in this harness where the
contract's `rounding` decides anything: every term of the metric is an exact integer number of
cents, so `half_even` and `half_up` cannot differ on a cell — they differ on a mean, and only
over an even number of weeks. `HARNESS`'s 112 days are eight of them.

**Nothing here reads an arm.** The aggregation does not know which store was treated, which is
what lets `potential.py` compose the same numbers from two counterfactual runs.
"""

from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING

from corpus.world import Run, events
from corpus.world.chain import Chain
from corpus.world.events import EslAck, Event, PosLine, ShelfDay

if TYPE_CHECKING:
    pass

#: `(store_id, iso_year, iso_week, category)` — the metric's grain, written out.
Cell = tuple[str, int, int, str]

#: `(iso_year, iso_week)`. Sorted lexicographically, which is chronological for ISO weeks.
Week = tuple[int, int]


class OutcomesError(ValueError):
    """The stream cannot be aggregated to the metric's grain."""


@dataclass(frozen=True, slots=True)
class Ledger:
    """One world's events, grouped — and the three other things a whole system run needs.

    The exposure counts and the delivered policies are collected on the same pass because
    they come from the same stream and a second pass over five million events to fetch two
    integers per store would be five million events. They are **read from the corpus**, never
    inferred from the assignment: an acknowledgement is the only evidence a price reached a
    shelf, and a `delivered` map derived from the arms would make the contamination check a
    statement about itself.
    """

    revenue_cents: Mapping[Cell, int]
    cogs_cents: Mapping[Cell, int]
    waste_cents: Mapping[Cell, int]

    #: Per store: how many price changes were dispatched, and how many labels answered.
    dispatched: Mapping[str, int]
    acknowledged: Mapping[str, int]

    #: Per store: every policy ref that actually ran on it, read off the decision records.
    delivered: Mapping[str, frozenset[str]]

    @property
    def cells(self) -> tuple[Cell, ...]:
        return tuple(sorted(self.revenue_cents))

    @property
    def weeks(self) -> tuple[Week, ...]:
        return tuple(sorted({(cell[1], cell[2]) for cell in self.revenue_cents}))

    @property
    def units(self) -> tuple[str, ...]:
        return tuple(sorted({cell[0] for cell in self.revenue_cents}))


def cost_index(chain: Chain) -> dict[str, tuple[list[datetime], list[int]]]:
    """The cost ledger, indexed for as-of lookup — this path's own index, not the chain's.

    `Chain.cost_as_of` exists and is not called. The point of two implementations is that a
    bug in one does not cancel out of the comparison, and a shared accessor is a shared line.
    Both read `Chain.cost_steps`, which is the *data*; neither borrows the other's arithmetic.
    """
    index: dict[str, tuple[list[datetime], list[int]]] = {}
    for product in chain.products:
        steps = chain.cost_steps(product.sku_id)
        index[product.sku_id] = (
            [step.effective_from for step in steps],
            [step.unit_cost_cents for step in steps],
        )
    return index


def _cost_as_of(
    index: Mapping[str, tuple[list[datetime], list[int]]], sku_id: str, moment: datetime
) -> int:
    starts, values = index[sku_id]
    position = bisect_right(starts, moment)
    if position == 0:
        raise OutcomesError(
            f"{sku_id} sold at {moment.isoformat()} and the cost ledger opens after it. "
            "Nothing is inferred before a ledger opens; a margin computed from a cost that "
            "was not known is not a margin."
        )
    return values[position - 1]


def collect(run: Run, *, stream: Iterable[Event] | None = None) -> Ledger:
    """One pass over a world, grouped to the metric's grain.

    `stream` is an argument so a test can hand in a stream it built by hand; it defaults to
    the world's own events, which is what every caller in this package does.
    """
    index = cost_index(run.chain)
    category = {product.sku_id: product.category for product in run.chain.products}
    revenue: dict[Cell, int] = defaultdict(int)
    cogs: dict[Cell, int] = defaultdict(int)
    waste: dict[Cell, int] = defaultdict(int)
    dispatched: dict[str, int] = defaultdict(int)
    acknowledged: dict[str, int] = defaultdict(int)
    delivered: dict[str, set[str]] = defaultdict(set)

    for event in stream if stream is not None else events(run):
        kind = type(event)
        if kind is PosLine:
            line: PosLine = event  # type: ignore[assignment]
            year, week, _day = line.event_ts.date().isocalendar()
            cell = (line.store_id, year, week, category[line.sku_id])
            revenue[cell] += line.qty * line.unit_price_cents
            cogs[cell] += line.qty * _cost_as_of(index, line.sku_id, line.event_ts)
        elif kind is ShelfDay:
            shelf: ShelfDay = event  # type: ignore[assignment]
            if not shelf.wasted_qty:
                continue
            year, week, _day = date.fromisoformat(shelf.business_date).isocalendar()
            cell = (shelf.store_id, year, week, category[shelf.sku_id])
            waste[cell] += shelf.wasted_qty * shelf.unit_cost_cents
        elif kind is EslAck:
            ack: EslAck = event  # type: ignore[assignment]
            dispatched[ack.store_id] += 1
            if ack.accepted:
                acknowledged[ack.store_id] += 1
            delivered[ack.store_id].add(ack.policy_id)

    keys = set(revenue) | set(cogs) | set(waste)
    return Ledger(
        revenue_cents={cell: revenue.get(cell, 0) for cell in keys},
        cogs_cents={cell: cogs.get(cell, 0) for cell in keys},
        waste_cents={cell: waste.get(cell, 0) for cell in keys},
        dispatched=dict(dispatched),
        acknowledged=dict(acknowledged),
        delivered={store: frozenset(refs) for store, refs in delivered.items()},
    )
