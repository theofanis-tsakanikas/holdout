"""Every history slice is preceded by an ERP export, or silver has nothing to price with.

**A history slice carries the reference tables and the loader will not read them.**
`corpus/world/write` puts `store_master`, `product_master` and `cost_ledger` beside the four
event streams; `bulk._sources` reads each `run.json`'s stream counts rather than globbing, and
says why in as many words: `store_master` there carries the **`arm`** column — the experiment's
answer — which the ERP export withholds on purpose. *An ingestion path cannot carry the injected
truth into bronze even by accident.*

So the master data arrives the way `CLAUDE.md` says it does — *ERP master data → files on S3,
dropped again during a run* — and until this branch **nothing dispatched it**. `backfill` ran
`history` and `load` and then silver refused:

    BronzeMissingError: /Volumes/holdout/bronze/files/cost_ledger holds no Parquet, so silver
    would build an empty cost_ledger and report a clean run.

That refusal is the guard working, three tasks in. What it was refusing was a step nobody had
written.

## What this asserts

Every job that runs `pipelines.ingest.bulk history` also runs `pipelines.ingest.bulk export`, and
the history task waits for it. Both halves: an export that ran afterwards would publish a ledger
the events had already been loaded without.

## What it does not check

- **It does not check the day.** `--slice` derives it from `pipelines/window.py`, and
  `tests/ops/` covers that the slices agree; which reference rows a given day makes visible is
  `pipelines/ingest/erp.py`'s own tests.
- **It reads Terraform, not the account.** The same limit every gate over a file here has.
"""

from __future__ import annotations

import re

from tests.infra import tasks

JOBS = tasks.INFRA / "pipelines" / "jobs.tf"

_DEPENDS_ON = re.compile(r'depends_on\s*\{[^}]*task_key\s*=\s*"([^"]+)"', re.DOTALL)


#: A comment is not a command, and the paragraphs above these tasks quote the subcommands they
#: run. Stripped before anything is matched, which is the third gate here to have needed it.
_COMMENT = re.compile(r"^\s*#.*$", re.MULTILINE)


def _blocks() -> dict[str, str]:
    """Each task in the pipelines layer, by key, with its comments removed."""
    return {key: _COMMENT.sub("", body) for key, body in tasks.task_blocks(JOBS)}


def _runs(body: str, subcommand: str) -> bool:
    """Whether this task's parameters begin `pipelines.ingest.bulk <subcommand>`."""
    found = tasks._PARAMETERS.search(body)
    if not found:
        return False
    parameters = tasks._tokens(tasks._region(body, found))
    return parameters[:2] == ["pipelines.ingest.bulk", subcommand]


def test_there_is_a_history_task_to_check() -> None:
    """An empty population passes every assertion below it and proves nothing."""
    assert JOBS.is_file(), f"{JOBS} is gone; this gate and the jobs move together."
    histories = [key for key, body in _blocks().items() if _runs(body, "history")]
    assert histories, (
        "no task runs `pipelines.ingest.bulk history`. Either the estate loads its history some "
        "other way now — which is a finding — or this reader stopped seeing it."
    )


def test_an_export_runs_and_history_waits_for_it() -> None:
    blocks = _blocks()
    exports = [key for key, body in blocks.items() if _runs(body, "export")]
    assert exports, (
        "no task runs `pipelines.ingest.bulk export`.\n\n"
        "Then bronze never receives `cost_ledger`, `product_master` or `store_master`: a history "
        "slice carries them and the loader refuses to read them, because that copy has the `arm` "
        "column. silver stops with BronzeMissingError, three tasks and one baseline in."
    )

    for key, body in blocks.items():
        if not _runs(body, "history"):
            continue
        waits_for = _DEPENDS_ON.search(body)
        assert waits_for, (
            f"the `{key}` task declares no `depends_on`, so it starts beside the export rather "
            "than after it. The events would be loaded against whatever ledger had landed by "
            "then, which is a race with a number at the end of it."
        )
        assert waits_for.group(1) in exports, (
            f"the `{key}` task waits for `{waits_for.group(1)}`, which is not an export. The "
            "reference tables have to be on disk before the events that resolve against them."
        )
