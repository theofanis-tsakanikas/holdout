"""The walked path's metric arithmetic — everything that *reads* `reference.compute`'s cells.

The mirror of `grouped.py`, split from `reference.py` for the same reason and under the same
measurement: by transitive closure from `compute`, `reference.py` held three producers --
`compute`, `_ledger`, `_cost_as_of` -- and the two consumers below, with no function on both
sides.

**These two modules may not share a line, and neither may their parents.** `U10` compares this
path against the grouped one as integers with no tolerance, so a line written once and called
twice is a line whose bug cancels and a check that agrees with itself. `by_unit_week` and
`window_mean` are deliberately a second implementation of what `grouped.py` also does, and the
two agreeing is the thing being checked rather than an accident to be tidied away.

**What this split does not do**, because it will be read as more than it is: a mutation planted
on `compute` -- this path's *producer*, and arguably the side of `U10` worth attacking -- still
invalidates the cache and still pays the full rebuild. Correctly: it genuinely changes what the
cached artefact is. Only mutations on the functions below become cheap.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import TYPE_CHECKING

from evals.uplift.reference import CENTS_PER_EURO, Cell, ReferenceError, Week

if TYPE_CHECKING:
    from holdout.contracts.model import Metric


def by_unit_week(cells: Mapping[Cell, int]) -> dict[tuple[str, Week], int]:
    """The grain's categories added up inside each store-week.

    The experiment randomises stores, so the categories inside a store-week are summed. It is
    written out here rather than shared with the grouped path for the reason the module
    docstring gives about the as-of lookup: a shared line is a line whose bug cancels.
    """
    out: dict[tuple[str, Week], int] = defaultdict(int)
    for (store, year, week, _category), value in cells.items():
        out[(store, (year, week))] += value
    return dict(out)


def window_mean(
    by_week: Mapping[tuple[str, Week], int],
    *,
    units: Sequence[str],
    weeks: Sequence[Week],
    metric: Metric,
) -> dict[str, int]:
    """Each unit's mean over the window, rounded by the contract — this path's own arithmetic.

    A week in which a unit has no record contributes zero rather than shortening the divisor:
    a week a store traded nothing is a week it earned nothing, and dividing by the weeks it
    happened to appear in would pay it for being absent. The grouped path makes the same
    decision, separately, and the two agreeing on it is part of what is being checked.
    """
    if not weeks:
        raise ReferenceError("a window of no weeks has no mean")
    span = Decimal(len(weeks))
    return {
        unit: metric.rounding.canonical_integer(
            sum(
                (Decimal(by_week.get((unit, week), 0)) for week in weeks),
                Decimal(0),
            )
            / CENTS_PER_EURO
            / span
        )
        for unit in units
    }
