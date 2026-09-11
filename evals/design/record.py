"""`make record-designs` — ask the model every question in the bank and seal the answers.

The one step in this eval that opens a socket, and it is never run by CI. It is run by a
person, on purpose, on a day the manifest names, and what it writes is committed: a recording
cannot be regenerated identically, which is the same reason `corpus/real/` is committed and
`corpus/world/` is not.

The tools answer from the pre-period and refuse the window
----------------------------------------------------------
The agent's three metric tools are real here. `LedgerExecutor` answers them from the harness
ledger — the same all-control ledger the pre-period was measured on — restricted to the weeks
before the comparison window opens. A query whose dates reach into the window is answered with
the tool's own documented refusal: *results are refused before the declared end date.* So the
model can ask for a store's margin history and get it, and cannot ask for an outcome, and the
line between the two is the one `pipelines/window.py` draws for the estate.

Why the executor lives here and not in `holdout.agent`
------------------------------------------------------
Because it reads a ledger that only exists inside `evals/`, and `holdout.agent` opens no file
it was not handed. On the estate the same protocol is answered by a warehouse query; here it is
answered by the world the design will be judged against, which is the honest local equivalent.
"""

from __future__ import annotations

import argparse
import statistics
import sys
from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Any

from evals.design import build
from evals.uplift.outcomes import Ledger, Week
from holdout.agent.record import record
from holdout.agent.registry import Tool

METRIC_COLUMNS = {
    "metric_category_margin_per_store_week": ("margin",),
    "metric_waste_value_per_store_week": ("waste",),
    "metric_units_sold_per_store_week": (),
}


class LedgerExecutor:
    """Answers a metric tool from the pre-period of the harness ledger, and nothing later."""

    def __init__(self, ledger: Ledger, pre_weeks: tuple[Week, ...]) -> None:
        self._pre = set(pre_weeks)
        self._first, self._last = min(pre_weeks), max(pre_weeks)
        self._by_cell: dict[str, dict[tuple[str, Week, str], int]] = {
            "margin": {},
            "waste": {},
        }
        for cell in ledger.revenue_cents:
            store, year, week, category = cell
            key = (store, (year, week), category)
            self._by_cell["margin"][key] = (
                ledger.revenue_cents[cell] - ledger.cogs_cents[cell] - ledger.waste_cents[cell]
            )
            self._by_cell["waste"][key] = ledger.waste_cents[cell]

    def run(self, tool: Tool, arguments: dict[str, Any]) -> str:
        columns = METRIC_COLUMNS.get(tool.name, ())
        if not columns:
            return (
                f"{tool.name}: no history is available in this estate for this metric. The "
                "pre-period figures in your context are for the other two."
            )
        try:
            wanted = _weeks_between(str(arguments["date_from"]), str(arguments["date_to"]))
        except (KeyError, ValueError) as bad:
            return f"{tool.name}: the date range could not be read ({bad})."
        if any(week not in self._pre for week in wanted):
            return (
                f"{tool.name}: the range reaches past the pre-period. Results inside the "
                "comparison window are refused before the declared end date; the pre-period "
                f"runs from ISO week {self._first} to {self._last}."
            )
        stores = set(arguments.get("store_id") or [])
        categories = set(arguments.get("category") or [])
        per_store_week: dict[tuple[str, Week], int] = defaultdict(int)
        for (store, week, category), value in self._by_cell[columns[0]].items():
            if week not in wanted:
                continue
            if stores and store not in stores:
                continue
            if categories and category not in categories:
                continue
            per_store_week[(store, week)] += value
        if not per_store_week:
            return f"{tool.name}: no rows match those filters in the pre-period."
        values = list(per_store_week.values())
        return (
            f"{tool.name} over {len(wanted)} pre-period week(s), {len(values)} store-week rows: "
            f"mean {statistics.fmean(values):.0f} cents, min {min(values)}, max {max(values)}, "
            f"stdev {statistics.pstdev(values):.0f}. Grain is (store_id, iso_week); categories "
            f"{'restricted to ' + ', '.join(sorted(categories)) if categories else 'summed'}."
        )


def _weeks_between(date_from: str, date_to: str) -> set[Week]:
    """ISO weeks from `date_from` inclusive to `date_to` exclusive."""
    start = date.fromisoformat(date_from)
    end = date.fromisoformat(date_to)
    if end <= start:
        raise ValueError("date_to must be after date_from")
    weeks: set[Week] = set()
    day = start
    while day < end:
        iso = day.isocalendar()
        weeks.add((iso.year, iso.week))
        day = date.fromordinal(day.toordinal() + 7)
    iso = date.fromordinal(end.toordinal() - 1).isocalendar()
    weeks.add((iso.year, iso.week))
    return weeks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        default=None,
        help="the directory to write; defaults to recordings/<today>, and refuses to overwrite",
    )
    args = parser.parse_args(argv)

    contracts = build.contracts()
    built = build.world(contracts)
    ledger = build._control_ledger(built.fixture)
    pre_weeks = built.pre_by_metric[build.MARGIN].pre_weeks
    today = datetime.now(UTC).date()
    out = build.RECORDINGS / (args.out or today.isoformat())

    print(f"recording {len(build.questions())} question(s) into {out}")
    print(f"  proposer   {contracts.runtime.model_id}")
    print(f"  world      {build.WORLD} / {build.WORLD_SEED} at {build.SCALE.name}")
    result = record(
        list(build.questions()),
        context=build.context(contracts, built),
        contracts=contracts,
        executor=LedgerExecutor(ledger, pre_weeks),
        out=out,
        recorded_on=today,
    )
    print(
        f"  recorded   {result.questions} question(s): {result.proposals} proposal(s), "
        f"{result.failed} failed"
    )
    print(f"  digest     {result.digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
