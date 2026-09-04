"""One definition, implemented by summing each term first and combining the sums.

**This module and `combine_then_aggregate.py` may not share a line, and neither may their
parents.** `evals/uplift/walked_metric.py` carries the rule for the pair that came before this
one, and it applies here word for word: a line written once and called twice is a line whose bug
cancels, and two implementations that agree because they share it are one implementation measured
twice. `tests/evals/test_definition_independence.py` enforces it on the import graph rather than
on anybody's care.

Why *this* pair, rather than reusing the one that exists
--------------------------------------------------------
`evals/uplift/`'s `grouped_metric` and `walked_metric` are proven independent and were the obvious
candidates. They are independent **in the wrong half**: both consume a `Ledger` whose three terms
are *already aggregated*, so they implement the combination and the rounding and nothing else.
Reusing them here would mean writing the aggregation once, handing it to both, and getting
agreement by construction in exactly the half the SQL does differently.

**A mechanism that is independent in the wrong half is the thing claim 5's trap describes.**

So the difference between this module and its sibling is the **order of operations**, which is
where the failures actually live:

    this module           sum each term per cell   ->  subtract  ->  round once
    combine_then_aggregate   subtract per row      ->  sum       ->  round once

In exact arithmetic those must agree. They stop agreeing the moment either rounds early, uses a
float where a `Decimal` belongs, or disagrees about a cell that one side of the full outer join
has and the other does not. Those are the three planted in `evals/gate_proof/mutations/claim-5/`,
and the comparison catching each is what makes *genuinely different* a measurement rather than a
description of two files.

The limit no rule here reaches
------------------------------
**Non-sharing prevents shared code. It does not prevent a shared misconception.** These two
modules were written by one session in one sitting, and both could be wrong in the same way about
what the contract means — every plant would pass and the numbers would agree.

**Which is why the SQL is the load-bearing third.** It was compiled from the same contract by a
different mechanism, at a different time, for a different purpose. The two Python paths mostly
guard the arithmetic; **the SQL is what guards the reading.** A reader who sees three mechanisms
should not assume all three are equally independent — one of them is carrying more than the
others.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from holdout.contracts.model import Metric

#: One metric cell, in the grain the contract declares. Built as a tuple in the contract's own
#: column order rather than as a named type, because a named type would be somewhere for the two
#: implementations to meet.
Cell = tuple[str, ...]


def cells(
    economics: Iterable[Mapping[str, object]],
    waste: Iterable[Mapping[str, object]],
    metric: Metric,
) -> dict[Cell, int]:
    """The metric per cell, as an integer in the contract's canonical scale.

    Each of the three terms is summed over its rows first, in exact `Decimal`, and the sums are
    combined once at the end. Nothing is rounded until the combination is complete — the contract
    declares one rounding, at one place, and a sum of rounded terms is a different number from a
    rounded sum.
    """
    grain = list(metric.grain)
    revenue: dict[Cell, Decimal] = defaultdict(Decimal)
    cogs: dict[Cell, Decimal] = defaultdict(Decimal)
    thrown: dict[Cell, Decimal] = defaultdict(Decimal)

    for row in economics:
        cell = tuple(str(row[column]) for column in grain)
        quantity = Decimal(str(row["qty"]))
        revenue[cell] += quantity * Decimal(str(row["price_paid"]))
        cogs[cell] += quantity * Decimal(str(row["unit_cost_as_of"]))

    for row in waste:
        cell = tuple(str(row[column]) for column in grain)
        thrown[cell] += Decimal(str(row["qty"])) * Decimal(str(row["unit_cost_as_of"]))

    # **Every cell either side carries, which is the contract's `full_outer_on_grain`.** A cell
    # present in one source and absent from the other contributes zero from the absent side
    # rather than vanishing: a store-week that traded and threw nothing away has a margin, and a
    # store-week that only threw something away has a negative one. Treating an absent side as an
    # absent *cell* is one of the three mutations planted against this pair.
    every: set[Cell] = set(revenue) | set(cogs) | set(thrown)
    return {
        cell: metric.rounding.canonical_integer(
            revenue.get(cell, Decimal(0))
            - cogs.get(cell, Decimal(0))
            - thrown.get(cell, Decimal(0))
        )
        for cell in every
    }
