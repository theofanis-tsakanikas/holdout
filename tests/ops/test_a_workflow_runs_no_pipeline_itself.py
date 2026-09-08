"""No workflow runs a pipeline entry point on the runner. The jobs do that.

**Every entry point under `pipelines/` takes filesystem paths**, and the only filesystem where
the estate's paths exist is a Databricks task: `/Volumes/holdout/landing/files` is a FUSE mount
on serverless compute and nothing at all on a GitHub runner.

`run.yml` ran one anyway:

    uv run python -m pipelines.ingest --world "$WORLD" ... --out "s3://${LANDING}"

`--out` is a `pathlib.Path`. `Path("s3://bucket")` is a **relative directory named `s3:`**, so
the driver wrote its whole stream under the runner's working directory, printed its line counts,
exited zero, and the runner went away. Nothing raised, nothing landed, and the step was green
every time. `infra/pipelines/jobs.tf` had already closed this exact trap one layer down — *an
`s3://` string handed to one does not fail — it becomes a local directory named `s3:` on the
worker* — and the workflow above it kept doing it.

**And the format could not have been loaded even if it had landed.** `bulk.load` takes `.csv.gz`
and `.parquet`; the driver wrote JSONL. Two independent reasons the live day reached nothing, and
the run reported success on both.

## What it does not check

- **It does not check that the jobs are started.** A workflow that ran nothing at all would pass
  this and fail its own assertions instead, which is the right place for that to be caught.
- **A comment is not a command**, and comments are removed before this reads anything. The first
  version of this gate went red against the paragraph above, which quotes the defect it forbids —
  a gate that cannot be explained beside the thing it refuses is a gate nobody can document.
- **`ops.` modules are deliberately allowed.** `ops/run_assertions.py` queries a warehouse and an
  endpoint over HTTP and takes no filesystem path; running it on the runner is what it is for.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

#: `python -m pipelines.…`, however it is spelled — `uv run` in front, a full path to the
#: interpreter, `python3`. What is matched is the module, because the module is the defect.
_RUNS_A_PIPELINE = re.compile(r"python[0-9.]*\s+-m\s+(pipelines[.\w]*)")

#: A whole line whose first non-blank character is `#`. In a workflow that is a YAML comment; in
#: a `run:` block it is a shell comment. Either way it is not a command.
_COMMENT = re.compile(r"^\s*#.*$", re.MULTILINE)

FILES = sorted(WORKFLOWS.glob("*.yml")) if WORKFLOWS.is_dir() else []


def test_there_are_workflows_to_check() -> None:
    """An empty population passes every assertion below it and proves nothing."""
    assert FILES, (
        f"no workflows under {WORKFLOWS}. Either they moved — which is a finding, because the "
        "money workflows are what reach AWS — or this reader stopped seeing them."
    )


@pytest.mark.parametrize("path", FILES, ids=[p.name for p in FILES])
def test_a_workflow_starts_jobs_rather_than_running_pipelines(path: Path) -> None:
    text = _COMMENT.sub("", path.read_text(encoding="utf-8"))
    found = sorted(set(_RUNS_A_PIPELINE.findall(text)))
    assert not found, (
        f"{path.name} runs {found} on the runner.\n\n"
        "A pipeline entry point takes filesystem paths and the estate's paths exist only inside "
        "a Databricks task. Passing a bucket URI instead does not fail: `pathlib.Path` turns "
        "`s3://bucket` into a directory named `s3:` beside the checkout, the step prints its "
        "counts and exits zero, and the runner is deleted.\n\n"
        "Start the job that runs it instead — `infra/pipelines/outputs.tf` publishes every id:\n"
        "    JOB=$(aws ssm get-parameter --name /holdout/pipelines/job_live_day …)\n"
        '    databricks jobs run-now "$JOB" --timeout 3h'
    )
