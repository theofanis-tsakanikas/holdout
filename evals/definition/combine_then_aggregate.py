"""One definition, implemented by combining each row's own contribution and summing those.

**The other half of the pair, and it may not share a line with `aggregate_then_combine.py`.**
See that module for why this pair exists rather than the proven one in `evals/uplift/`, and for
the limit neither of them reaches.

What is deliberately different here
-----------------------------------
The sibling sums each of the contract's three terms over its rows and combines the sums once.
This one turns every row into the signed amount it contributes to its cell and adds those up:

    a sale       +  qty * price_paid  -  qty * unit_cost_as_of
    a disposal   -  qty * unit_cost_as_of

then rounds once, at the end, per cell.

**The two orders agree in exact arithmetic and diverge under every mistake worth catching.**
Round each row and the pennies accumulate; carry a `float` and the sum depends on the order rows
arrived in; drop a cell that only one source has and one order notices while the other does not.
That is what the mutations aimed at this pair plant, and what the comparison is for.

**It is also the order a person would compute by hand**, which is not an argument for it being
right — it is the reason it is a plausible *second* reading of the same contract rather than a
contrived variant of the first. A second implementation nobody would ever have written is a
second implementation that proves nothing about how the definition can be misread.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from holdout.contracts.model import Metric


def per_cell(
    economics: Iterable[Mapping[str, object]],
    waste: Iterable[Mapping[str, object]],
    metric: Metric,
) -> dict[tuple[str, ...], int]:
    """The metric per cell, as an integer in the contract's canonical scale.

    Every row is reduced to its own contribution before anything is grouped, and the rounding
    happens once per cell after every contribution has landed. A row is never rounded: the
    contract declares a rounding of the metric, not of a receipt line.
    """
    columns = list(metric.grain)
    running: dict[tuple[str, ...], Decimal] = defaultdict(Decimal)

    for line in economics:
        key = tuple(str(line[column]) for column in columns)
        count = Decimal(str(line["qty"]))
        running[key] += count * Decimal(str(line["price_paid"])) - count * Decimal(
            str(line["unit_cost_as_of"])
        )

    for disposal in waste:
        key = tuple(str(disposal[column]) for column in columns)
        running[key] -= Decimal(str(disposal["qty"])) * Decimal(str(disposal["unit_cost_as_of"]))

    # A cell exists here as soon as any row touched it, from either source, which is the same
    # `full_outer_on_grain` the sibling reaches by unioning three key sets. The two arrive at it
    # differently on purpose: one asks *which cells did I see*, the other *which cells does
    # either side hold*, and a bug that loses a one-sided cell shows up in only one of them.
    return {key: metric.rounding.canonical_integer(total) for key, total in running.items()}
