"""dbt's sources are written by a task dbt waits for.

`pipelines/gold/dbt/models/sources.yml` declares two sources, `gold.priced_sales` and
`gold.priced_waste`. Neither is built by dbt: they are written by `pipelines/gold/facts.py`, from
the Python task in the same job. **So the Python task has to finish before dbt starts, and the
first version of `infra/pipelines/jobs.tf` had it the other way round** — the Python task declared
`depends_on { task_key = "dbt" }`, which reads perfectly as *the models, then the extras*.

What that would have produced is `dbt build` failing on a source relation that does not exist,
after `backfill` had spent about ninety minutes loading eight months of history and building
silver. **Each file was correct alone.** The defect exists only in the pair, which is why the gate
reads both.

## What it does not check

- **It does not check that the priced task succeeds**, only that dbt is placed after it.
- **It does not check dbt's own `ref` graph.** dbt resolves that itself and fails loudly.
"""

from __future__ import annotations

import re

import yaml
from pipelines.gold import facts

from tests.infra import tasks

JOBS = tasks.INFRA / "pipelines" / "jobs.tf"
SOURCES = tasks.REPO_ROOT / "pipelines" / "gold" / "dbt" / "models" / "sources.yml"

_DEPENDS_ON = re.compile(r'depends_on\s*\{[^}]*task_key\s*=\s*"([^"]+)"', re.DOTALL)


def _declared_sources(group: str | None = None) -> set[str]:
    """Every table `sources.yml` declares -- in one source group, or across all of them."""
    document = yaml.safe_load(SOURCES.read_text(encoding="utf-8"))
    return {
        table["name"]
        for source in document.get("sources", [])
        if group is None or source["name"] == group
        for table in source.get("tables", [])
    }


def test_there_is_a_dbt_task_to_check() -> None:
    """An empty population passes every assertion below it and proves nothing."""
    assert JOBS.is_file(), f"{JOBS} is gone; this gate and the job it judges move together."
    assert SOURCES.is_file(), f"{SOURCES} is gone, so dbt declares no sources to be written."
    assert any("dbt_task" in body for _, body in tasks.task_blocks(JOBS)), (
        "no task in infra/pipelines/jobs.tf runs dbt. Either the analytical models are built "
        "some other way now — which is a finding — or this reader stopped seeing the task."
    )


def test_dbt_waits_for_the_task_that_writes_its_sources() -> None:
    blocks = dict(tasks.task_blocks(JOBS))
    dbt = next(body for key, body in tasks.task_blocks(JOBS) if "dbt_task" in body)

    waits_for = _DEPENDS_ON.search(dbt)
    assert waits_for, (
        "the dbt task declares no `depends_on`. Its sources — "
        f"{sorted(_declared_sources())} — are written by the Python task in the same job, so "
        "with no dependency the two start together and dbt loses the race it cannot see."
    )

    upstream = blocks.get(waits_for.group(1), "")
    assert "--only" in upstream and "priced" in upstream, (
        f"the dbt task waits for `{waits_for.group(1)}`, which does not run "
        "`pipelines.gold --only priced`.\n\n"
        f"dbt's sources are {sorted(_declared_sources())} and `pipelines/gold/facts.py` is what "
        "writes them. A dbt task placed before that runs against relations nothing has created "
        "— ninety minutes into a backfill."
    )


def test_the_sources_are_the_tables_that_task_writes() -> None:
    """The two files agree on which tables they are talking about.

    **Two source groups since 2026-09-12, and each has a writer this test names.** `priced` is
    written by the Python task dbt waits for, in the same job -- the pair the tests above read.
    `silver` is written by the silver job, which both `backfill` and `run` finish before the
    gold job starts; a table declared there that silver does not write is the same relation
    dbt looks for and nothing creates, one job further up.
    """
    from pipelines.silver.build import SILVER_TABLES

    assert _declared_sources("priced") == set(facts.PRICED_TABLES), (
        f"sources.yml's `priced` group declares {sorted(_declared_sources('priced'))} and "
        f"pipelines/gold/facts.py writes {sorted(facts.PRICED_TABLES)}. The ordering above is "
        "only worth having while these are the same set: a source added to one and not the "
        "other is a relation dbt looks for and no task creates."
    )
    unwritten = _declared_sources("silver") - set(SILVER_TABLES)
    assert not unwritten, (
        f"sources.yml's `silver` group declares {sorted(unwritten)}, which "
        "pipelines/silver/build.py does not write. dbt would look for it after a silver job "
        "that never made it."
    )
    assert _declared_sources() == _declared_sources("priced") | _declared_sources("silver"), (
        "sources.yml has a source group this test does not know the writer of"
    )
