"""Consumer 3 — the agent's tool definition.

The agent never writes SQL. It receives a tool whose parameters are filters over the
metric's own grain, and the tool carries the metric's id, version, unit and rounding as
metadata so that whatever the agent reports can be checked against the same integer the
other consumers produce. An agent free to write its own aggregate would be a fourth
definition of the metric, written afresh on every call.
"""

from __future__ import annotations

import json

from holdout.contracts.compilers.sql import DO_NOT_EDIT
from holdout.contracts.model import Metric

GENERATOR = "holdout.contracts.compilers.agent_tool"


def compile_agent_tool(metric: Metric) -> str:
    properties: dict[str, object] = {
        "date_from": {
            "type": "string",
            "description": "ISO date, inclusive. The metric version in force on this date applies.",
        },
        "date_to": {"type": "string", "description": "ISO date, exclusive."},
    }
    for column in metric.grain:
        if column in {"iso_week"}:
            continue
        properties[column] = {
            "type": "array",
            "items": {"type": "string"},
            "description": f"Restrict to these {column} values. Omit for all.",
        }
    properties["experiment_id"] = {
        "type": "string",
        "description": (
            "Optional. Restrict to the units assigned to this experiment and return the "
            "result split by arm. Results are refused before the declared end date."
        ),
    }

    tool = {
        "$comment": (
            f"{DO_NOT_EDIT}. source: {metric.source_path}; generator: {GENERATOR}; "
            "regenerate: make contracts."
        ),
        "name": f"metric_{metric.id}",
        "description": (
            (metric.description or "").strip().replace("\n", " ")
            + f" Returns the metric at grain ({', '.join(metric.grain)}) in {metric.unit}, "
            f"rounded {metric.rounding.mode} to {metric.rounding.decimals} decimals. "
            "The definition is fixed by contract; this tool does not accept a formula."
        ).strip(),
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["date_from", "date_to"],
            "properties": properties,
        },
        "metric": {
            "id": metric.id,
            "version": metric.version,
            "effective_from": metric.effective_from.isoformat(),
            "grain": list(metric.grain),
            "unit": metric.unit,
            "rounding": {
                "mode": metric.rounding.mode,
                "decimals": metric.rounding.decimals,
            },
            "canonical_integer_scale": 10**metric.rounding.decimals,
        },
    }
    return json.dumps(tool, indent=2, ensure_ascii=False) + "\n"
