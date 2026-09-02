"""The grouped path's metric arithmetic — everything that *reads* a `Ledger`.

**This module exists because of a cache key, and that is the whole of it.**
`evals/uplift/cache.py` digests `outcomes.py` and `reference.py` whole, because every cached
artefact is produced by `outcomes.collect` or `reference.compute` and a mutation to either
must not be handed a cache built before it. A digest over a **file** cannot see that
`window_mean` produces nothing cached: it runs on a `Ledger` that has already come back out.

So editing a consumer used to throw away every cached artefact built by a producer it does not
touch. Measured on run 33600284036, that cost the one mutation planted on a consumer **806s
against its seven siblings' 32-87s**, and killed it outright at the 900s budget on run
33610996234 -- taking `claims-complete`, a required context, red on a branch of five Markdown
files.

**The fix is not a cleverer digest. It is a file that deserves to be hashed whole.** After the
split `outcomes.py` holds producers only, so hashing all of it is exactly right, and
`DEPENDS_ON`, `key()` and `source_digest()` are untouched.

**The partition is measured, not chosen.** By transitive closure from `collect`, `outcomes.py`
held three producers -- `collect`, `cost_index`, `_cost_as_of` -- and three consumers, which
are the three below. No function was on both sides. `walked.py` is the same split of
`reference.py`, and the two must stay apart for the reason `reference.py`'s docstring gives:
a shared line is a line whose bug cancels.

**And the partition is enforced by something that is not this docstring.**
`tests/evals/test_uplift_cache.py::test_every_module_a_cached_artefact_is_produced_by_is_in_the_digest`
walks the import closure of the producing roots and requires every module it reaches to be in
the digest. Move a **producer** here and `outcomes.py` must import this module, it enters that
closure, it is not in `DEPENDS_ON`, and the test goes red. Move a **consumer**, as these are,
and the import runs the other way -- this module imports `outcomes`, never the reverse -- so
the walk never reaches it and never should.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import TYPE_CHECKING

from evals.uplift.outcomes import Cell, Ledger, OutcomesError, Week

if TYPE_CHECKING:
    from holdout.contracts.model import Rounding


def cell_margins(ledger: Ledger, rounding: Rounding) -> dict[Cell, int]:
    """The metric's value at its own grain, as the canonical integer the contract declares.

    Routed through `Rounding.canonical_integer` rather than returned as the cent count it
    already is. On this corpus the two are the same number — every term is an exact integer
    number of cents — and going through the contract anyway is what makes the rounding a
    contract term here rather than a coincidence of the data.
    """
    return {
        cell: rounding.canonical_integer(
            Decimal(ledger.revenue_cents[cell] - ledger.cogs_cents[cell] - ledger.waste_cents[cell])
            / 100
        )
        for cell in ledger.revenue_cents
    }


def unit_weeks(ledger: Ledger, rounding: Rounding) -> dict[tuple[str, Week], int]:
    """The metric summed across the categories in scope, per store and ISO week.

    The grain carries a category and the experiment's unit is a store, so the categories
    inside a store-week are added. Summing a metric across the grain dimensions the unit does
    not split on is what a readout does; it is not an average and there is nothing to round.
    """
    out: dict[tuple[str, Week], int] = defaultdict(int)
    for (store, year, week, _category), value in cell_margins(ledger, rounding).items():
        out[(store, (year, week))] += value
    return dict(out)


def window_mean(
    by_unit_week: Mapping[tuple[str, Week], int],
    *,
    units: Sequence[str],
    weeks: Sequence[Week],
    rounding: Rounding,
) -> dict[str, int]:
    """Each unit's mean over the declared window, as a canonical integer.

    **The mean, not the total**, because the metric is per store-week and the MDE is declared
    against a per-store-week mean. A unit with no record in a week contributes zero to the
    mean rather than shortening the divisor: a week a store traded nothing is a week it earned
    nothing, and dividing by the weeks it happened to appear in would pay it for being absent.

    This is the one division in the grouped path, so it is the one place the contract's
    rounding decides a cent — see the module docstring.
    """
    if not weeks:
        raise OutcomesError("a window of no weeks has no mean")
    span = len(weeks)
    return {
        unit: rounding.canonical_integer(
            Decimal(sum(by_unit_week.get((unit, week), 0) for week in weeks)) / (100 * span)
        )
        for unit in units
    }
