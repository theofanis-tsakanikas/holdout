"""Consumer 2 — a SQL table function.

A genuinely different mechanism from the dbt model, which is the point: claim 5 is not
"two callers of one function agree", it is "three mechanisms that share only the
definition produce the same integer". This one is a catalog object evaluated on demand
against fully qualified relations; the dbt model is a materialised table built through
`ref()`. If they ever disagree, the definition was interpreted twice.
"""

from __future__ import annotations

from holdout.contracts.compilers.sql import metric_body, qualified, sql_header
from holdout.contracts.model import Metric

GENERATOR = "holdout.contracts.compilers.sql_function"

#: The catalog is a deployment concern, not a contract term, so it is left as a template
#: variable rather than baked in — a generated artefact that named an environment would go
#: stale every time the environment changed and would tell you nothing when it did.
CATALOG = "${catalog}"
SCHEMA = "metrics"


def _sql_type(unit: str, decimals: int) -> str:
    return "bigint" if unit == "units" and decimals == 0 else f"decimal(18, {decimals})"


def compile_sql_function(metric: Metric) -> str:
    header = sql_header(source_path=metric.source_path, generator=GENERATOR)
    name = f"{CATALOG}.{SCHEMA}.{metric.id}_v{metric.version}"
    returns = ", ".join(f"{column} string" for column in metric.grain)
    returns += (
        f", metric_id string, metric_version int, "
        f"metric_value {_sql_type(metric.unit, metric.rounding.decimals)}"
    )
    body = metric_body(metric, relation=qualified)
    indented = "\n".join(f"    {line}" if line else "" for line in body.splitlines())
    return (
        f"{header}\n"
        f"-- metric: {metric.ref} — unit {metric.unit}, "
        f"rounded {metric.rounding.mode} to {metric.rounding.decimals} decimals\n\n"
        f"create or replace function {name}()\n"
        f"returns table ({returns})\n"
        f"return\n"
        f"{indented};\n"
    )
