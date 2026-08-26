"""Consumer 1 — the dbt model that materialises the metric in the lakehouse."""

from __future__ import annotations

from holdout.contracts.compilers.sql import dbt_ref, metric_body, sql_header
from holdout.contracts.model import Metric

GENERATOR = "holdout.contracts.compilers.dbt"


def compile_dbt_model(metric: Metric) -> str:
    header = sql_header(source_path=metric.source_path, generator=GENERATOR)
    config = (
        f"{{{{ config(\n    materialized='table',\n    tags=['metric', '{metric.id}'],\n) }}}}\n"
    )
    about = (
        f"-- metric:   {metric.ref}\n"
        f"-- grain:    {', '.join(metric.grain)}\n"
        f"-- unit:     {metric.unit}\n"
        f"-- rounding: {metric.rounding.mode}, {metric.rounding.decimals} decimals "
        f"(SQL {metric.rounding.sql_function})\n"
    )
    body = metric_body(metric, relation=dbt_ref)
    return f"{header}\n{about}\n{config}\n{body}\n"
