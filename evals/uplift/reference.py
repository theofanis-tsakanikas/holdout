"""The deliberately slow one. Every event, one at a time, and no shortcut anywhere.

`outcomes.py` is the grouped path: one pass, a dictionary keyed by the metric's grain, three
accumulators. This is the other implementation, and **it may not share a line with it**. It
was written from `contracts/metrics/category_margin_per_store_week.v3.yaml` and from nothing
else — the expression, the grain, the unit, the rounding — and it differs from the grouped
path everywhere it is allowed to:

===============================  ==========================  ==========================
                                 `outcomes.py`               here
===============================  ==========================  ==========================
the as-of cost                   a sorted index, bisected    **walked forward** from the
                                                             first step of the ledger,
                                                             every time
the arithmetic                   integer cents               **`Decimal` euros**, which
                                                             is the shape the SQL
                                                             consumer will have
the accumulation                 three sums per grain cell   **one running ledger** of
                                                             signed entries, in the order
                                                             the events arrive
===============================  ==========================  ==========================

They agree **as integers, with no tolerance**, per world and per unit. A one-cent
disagreement is a failed check with the offending units named, and it is exactly the failure
v3 of the metric contract exists to have made impossible: v2 rounded `half_up`, a SQL
`round()` and a Python `Decimal` default disagreed by a cent, and claim 5 compares with no
tolerance. This is the first thing that would notice if it came back.

**The honest limit, printed on every run.** Two Python implementations are not the three
genuinely different mechanisms claim 5 needs. This is that check's *first* leg; the dbt model
and the SQL function are T011 and T012, and `docs/DECISIONS.md` carries the deferral with
those as its unlock.

**Why slow is the point.** A fast second implementation is one that made the same decisions as
the first. Walking the ledger forward is O(steps) per line where an index is O(log steps), and
the whole reason to pay it is that an index shared between the two would be an index whose bug
cancels out of the comparison.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from corpus.world import Run, events
from corpus.world.chain import Chain, CostStep
from corpus.world.events import Event, PosLine, ShelfDay

if TYPE_CHECKING:
    from holdout.contracts.model import Metric

#: `(iso_year, iso_week)`, as the grain's `iso_week` resolves to.
Week = tuple[int, int]

#: `(store_id, iso_year, iso_week, category)` — the metric's declared grain.
Cell = tuple[str, int, int, str]

#: One euro, as a `Decimal`. The metric's `unit` is EUR and its `rounding` is two decimals, so
#: this path works in the unit the contract declares rather than in the minor unit the corpus
#: happens to emit. That the two land on the same integer is the thing being checked.
CENTS_PER_EURO = Decimal(100)


class ReferenceError(ValueError):
    """The reference implementation was handed an event it cannot price."""


def _cost_as_of(steps: Sequence[CostStep], moment: datetime) -> Decimal:
    """The unit cost known at `moment`, in euros, by walking the ledger from its first entry.

    Deliberately linear. The grouped path bisects a sorted index; this reads the steps in the
    order they were appended and keeps the last one that had taken effect. Two implementations
    of an as-of join that shared a lookup would be one implementation with two callers, and
    the whole value of the comparison is that a mistake in either does not cancel.
    """
    known: CostStep | None = None
    for step in steps:
        if step.effective_from <= moment:
            known = step
        else:
            break
    if known is None:
        raise ReferenceError(
            f"{steps[0].sku_id if steps else '?'} is priced at {moment.isoformat()} and its "
            "cost ledger opens after that. Nothing is inferred before a ledger opens."
        )
    return Decimal(known.unit_cost_cents) / CENTS_PER_EURO


def _ledger(chain: Chain) -> dict[str, tuple[CostStep, ...]]:
    return {product.sku_id: chain.cost_steps(product.sku_id) for product in chain.products}


def compute(run: Run, *, metric: Metric, stream: Iterable[Event] | None = None) -> dict[Cell, int]:
    """The metric at its own grain, event by event, as the canonical integer it declares.

    The expression, transcribed from the contract and kept in its own shape::

        sum(s.qty * s.price_paid)
        - sum(s.qty * s.unit_cost_as_of)
        - sum(w.qty * w.unit_cost_as_of)

    Three signed contributions into one running total per cell, applied in the order the
    events arrive rather than gathered into three sums — which is the difference between a
    ledger and a `GROUP BY`, and the reason this is the slow one.
    """
    ledger = _ledger(run.chain)
    category = {product.sku_id: product.category for product in run.chain.products}
    running: dict[Cell, Decimal] = defaultdict(Decimal)

    for event in stream if stream is not None else events(run):
        if isinstance(event, PosLine):
            year, week, _day = event.event_ts.date().isocalendar()
            cell = (event.store_id, year, week, category[event.sku_id])
            quantity = Decimal(event.qty)
            price_paid = Decimal(event.unit_price_cents) / CENTS_PER_EURO
            unit_cost_as_of = _cost_as_of(ledger[event.sku_id], event.event_ts)
            running[cell] += quantity * price_paid
            running[cell] -= quantity * unit_cost_as_of
        elif isinstance(event, ShelfDay):
            if not event.wasted_qty:
                continue
            year, week, _day = date.fromisoformat(event.business_date).isocalendar()
            cell = (event.store_id, year, week, category[event.sku_id])
            # The disposal's as-of cost is the one the record already carries: it is what the
            # cost was when that shelf day opened, which is when the stock was written off.
            running[cell] -= Decimal(event.wasted_qty) * (
                Decimal(event.unit_cost_cents) / CENTS_PER_EURO
            )

    return {cell: metric.rounding.canonical_integer(total) for cell, total in running.items()}
