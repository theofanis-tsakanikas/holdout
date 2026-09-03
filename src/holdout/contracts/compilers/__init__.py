"""Compiling a contract into its consumers.

"A contract compiles; it is never interpreted by hand-written code in two places." Every
artefact under `generated/` is written by exactly one function here, from exactly one
parse of the contract, and `make contracts` recompiles all of them in memory and refuses
the build if what is on disk differs. A definition that exists but that nobody demonstrably
uses is not a source of truth; it is a comment.

The four consumers of the metric contract:

* `generated/dbt/models/metrics/` — the model that materialises the metric in the lakehouse
* `generated/sql/functions/`      — a SQL table function, a genuinely different mechanism
* `generated/agent_tools/`        — the agent's tool definition, so the agent never writes SQL
* `generated/readout/`            — the experiment readout, by arm, against a pinned version

and one consumer of the design contracts:

* `generated/design/form.schema.json` — the form with its closed lists resolved from
  `contracts/metrics/` and `contracts/policies/`, so the enum has one origin.
"""

from __future__ import annotations

from holdout.contracts.compilers.agent_tool import compile_agent_tool
from holdout.contracts.compilers.dbt import compile_dbt_model
from holdout.contracts.compilers.design_form import compile_design_form
from holdout.contracts.compilers.readout import compile_readout
from holdout.contracts.compilers.sql_function import compile_sql_function
from holdout.contracts.model import ContractSet, Metric

__all__ = [
    "compile_agent_tool",
    "compile_all",
    "compile_dbt_model",
    "compile_design_form",
    "compile_readout",
    "compile_sql_function",
    "in_force_metrics",
]


def in_force_metrics(contracts: ContractSet) -> tuple[Metric, ...]:
    """The one version of each metric that is still open-ended.

    Superseded versions stay in the repository forever so a closed experiment remains
    interpretable, but they compile into nothing: a consumer generated from a version that
    is no longer in force would be a live artefact computing a retired definition. Which
    version applied to a past experiment is resolved as of that experiment's date, from the
    contracts, at the moment it is read.

    "Still open-ended" rather than "in force today" on purpose — generation must not depend
    on the clock, or every artefact would go stale at midnight on an effective date and the
    staleness check would be reporting the calendar rather than a drift.
    """
    latest: list[Metric] = []
    for metric_id in contracts.metric_ids:
        family = contracts.metric_versions(metric_id)
        open_ended = [m for m in family if m.effective_to is None]
        latest.extend(open_ended if open_ended else [family[-1]])
    return tuple(sorted(latest, key=lambda m: (m.id, m.version)))


def compile_all(contracts: ContractSet) -> dict[str, str]:
    """Every generated artefact, as repository-relative path -> exact file content."""
    artefacts: dict[str, str] = {}
    for metric in in_force_metrics(contracts):
        stem = f"{metric.id}.v{metric.version}"
        # **The dbt artefact is the one whose file name is an identifier**, so it is the one
        # that cannot carry the dot the other three carry. dbt takes a model's relation name
        # from its file name, and `x.v3.sql` reaches the engine as `schema`.`x`.`v3`. See
        # `Metric.identifier`, which carries the measurement and the ruling that allowed it.
        artefacts[f"generated/dbt/models/metrics/{metric.identifier}.sql"] = compile_dbt_model(
            metric
        )
        artefacts[f"generated/sql/functions/{stem}.sql"] = compile_sql_function(metric)
        artefacts[f"generated/agent_tools/{stem}.json"] = compile_agent_tool(metric)
        artefacts[f"generated/readout/{stem}.sql"] = compile_readout(metric)
    artefacts["generated/design/form.schema.json"] = compile_design_form(contracts)
    return artefacts
