"""Consumer 4 — the experiment readout, by arm, against a pinned data version.

Three things make this query different from the dbt model rather than a wrapper around it:

* it reads the assignment table, which was written before the period opened from the
  committed seed and is read-only afterwards — the arm is never recomputed here;
* it pins a Delta version. Without the pin, re-running last month's readout returns a
  different number as late data arrives, and a number that changes when nobody changed
  anything cannot be defended;
* it produces per-unit values, not one aggregate. The estimator is a difference of means
  over randomly assigned units, and it needs the units.

The query stops there. It does not divide, it does not subtract the arms, and it emits no
interval — whether a result may be stated at all is decided by the four validity checks in
`holdout.core`, and a query that produced an uplift would be producing it before anything
had checked that the uplift was allowed to exist.
"""

from __future__ import annotations

from holdout.contracts.compilers.sql import (
    metric_parts,
    pinned,
    qualified,
    sql_header,
    version_parameter,
)
from holdout.contracts.errors import CompilationError
from holdout.contracts.model import Metric

GENERATOR = "holdout.contracts.compilers.readout"

ASSIGNMENT = "gold.experiment_assignment"

#: The unit column the assignment table keys on. The unit of randomisation is a design
#: field, but every admissible unit — store, store_week, store_category, region — is
#: identified by a store, so the join is on the store and the design's unit determines how
#: the rows are grouped afterwards.
UNIT_COLUMN = "store_id"

#: The column the readout windows on. The comparison period is declared in ISO weeks, so a
#: metric that is not defined per ISO week cannot be read out by this template.
PERIOD_COLUMN = "iso_week"

#: Every column this template names by hand. The metric's `grain` must contain all of them
#: or the emitted query would reference a column no CTE selects.
REQUIRED_GRAIN_COLUMNS = (UNIT_COLUMN, PERIOD_COLUMN)


def compile_readout(metric: Metric) -> str:
    missing = [column for column in REQUIRED_GRAIN_COLUMNS if column not in metric.grain]
    if missing:
        raise CompilationError(
            f"the readout template joins on `{UNIT_COLUMN}` and windows on `{PERIOD_COLUMN}`, "
            f"and metric {metric.ref} declares grain {list(metric.grain)}, which is missing "
            f"{missing}. Emitting the query anyway would reference a column no CTE selects: "
            "it would still be valid text, still match the staleness check, and still be "
            "wrong. A compiler may be opinionated; it may not guess. Either give the metric "
            "the grain the readout needs, or teach the readout the unit and period this "
            "metric actually has.",
            source_path=metric.source_path,
            locator="/grain",
        )
    header = sql_header(source_path=metric.source_path, generator=GENERATOR)
    ctes, select = metric_parts(metric, relation=qualified, version_clause=pinned)
    indented = "\n".join(f"    {line}" if line else "" for line in select.splitlines())
    ctes.append("metric as (\n" + indented + "\n)")
    ctes.append(
        "assignment as (\n"
        f"    select\n        {UNIT_COLUMN},\n        arm,\n        assigned_at,\n"
        "        seed\n"
        f"    from {ASSIGNMENT} version as of :{version_parameter(ASSIGNMENT)}\n"
        "    where experiment_id = :experiment_id\n"
        ")"
    )
    pins = [*(s.relation for s in metric.sources), ASSIGNMENT]
    pin_lines = "".join(
        (
            f"--   :{version_parameter(relation)}\n"
            f"--                   the Delta version {relation} is pinned to. **One parameter\n"
            f"--                   per relation**: a Delta version counter is per table, so one\n"
            f"--                   number cannot index two of them. Without the pin, re-running\n"
            f"--                   last month's readout returns a different number as late data\n"
            f"--                   arrives.\n"
        )
        if index == 0
        else (
            f"--   :{version_parameter(relation)}\n"
            f"--                   the Delta version {relation} is pinned to.\n"
        )
        for index, relation in enumerate(pins)
    )
    cte_block = "with " + ",\n\n".join(ctes)
    grain = ", ".join(f"m.{column}" for column in metric.grain)

    return f"""{header}
-- readout: {metric.ref} — unit {metric.unit}, rounded \
{metric.rounding.mode} to {metric.rounding.decimals} decimals
--
-- parameters
--   :experiment_id  the experiment whose assignment is read
{pin_lines}--   :period_start   inclusive, the declared opening of the comparison window
--   :period_end     exclusive, the declared close. Reading before it is blocked by the
--                   engine, not by this query.

{cte_block}

select
    a.arm,
    {grain},
    m.metric_id,
    m.metric_version,
    m.metric_value
from metric m
join assignment a
  on a.{UNIT_COLUMN} = m.{UNIT_COLUMN}
where m.iso_week >= :period_start
  and m.iso_week <  :period_end
order by a.arm, {grain}
"""
