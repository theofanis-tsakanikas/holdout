"""Every task that writes a table names the catalog it writes into.

**A two-part table name is not a location.** `saveAsTable("gold.priced_sales")` resolves against
whatever catalog is current, and on a Databricks workspace that is the workspace's default rather
than this estate's. The tables would be created, the job would report success, and the grants in
`infra/lakehouse/grants.tf`, the dbt task's `catalog`, the dashboards and `ops/run_assertions.py`
would all be pointing at an empty schema.

**Which is a silent failure, and that is why it is a gate.** Nothing raises. The only signal is a
query returning no rows, three jobs and one workflow later, at which point the obvious reading is
that the pipeline produced nothing rather than that it produced it elsewhere.

## What it does not check

- **It does not check the value.** `--catalog` is followed by a Terraform expression here; what it
  resolves to is a plan's business. What this asserts is that the flag is passed at all.
- **It reads the flag, not the code.** An entry point that accepted `--catalog` and ignored it
  would pass. `tests/pipelines/` is where that half lives.
"""

from __future__ import annotations

import pytest

from tests.infra import tasks

#: The modules that write tables and therefore have to be told where. `pipelines.ingest.bulk`
#: writes files into a volume and is deliberately not here: it names no catalog because it uses
#: none, and adding it would make this gate demand a flag that entry point does not accept.
WRITES_TABLES = frozenset({"pipelines.silver", "pipelines.gold", "pipelines.ml"})

LISTS = [
    (where, parameters)
    for where, parameters in tasks.parameter_lists()
    if parameters and parameters[0] in WRITES_TABLES
]


def test_there_are_tasks_to_check() -> None:
    """An empty population passes every assertion below it and proves nothing."""
    modules = {parameters[0] for _, parameters in LISTS}
    assert modules == WRITES_TABLES, (
        f"expected a task for each of {sorted(WRITES_TABLES)} and found {sorted(modules)}. "
        "Either a layer stopped running one — which is a finding — or this reader stopped "
        "seeing it and the assertions below are running over the wrong population."
    )


@pytest.mark.parametrize(
    ("where", "parameters"),
    LISTS,
    ids=[f"{w}::{p[0]}" for w, p in LISTS],
)
def test_a_task_that_writes_tables_names_its_catalog(where: str, parameters: list[str]) -> None:
    assert "--catalog" in parameters, (
        f"{where} runs `{parameters[0]}` without `--catalog`.\n\n"
        "A two-part table name resolves against the workspace's default catalog, so the tables "
        "would be written somewhere nobody named and the job would report success. Pass it:\n"
        '    "--catalog", local.catalog,\n\n'
        "The only signal otherwise is an empty readout in `run`, long after the write."
    )
