"""Every Databricks job a workflow starts is started through `ops/run_job.sh`.

**Because a failure that says nothing costs a dispatch to diagnose.** `backfill`'s first real run
ended like this:

    Error: failed to reach TERMINATED or SKIPPED, got INTERNAL_ERROR:
    Task history failed with message: Workload failed, see run output for details.

*See run output for details* is advice to open a console. The step had already asserted a green
suite, taken an environment approval, assumed a role and started an hour of compute; what it
reported was that something had gone wrong somewhere. The error existed in exactly one place —
a page — and `CLAUDE.md`'s rule about consoles is that nothing this repository does depends on
one.

`ops/run_job.sh` starts the job, and on failure fetches the run, prints the run page, prints every
task's state, and prints the output of **every** task that did not succeed. This asserts that no
workflow starts a job around it.

## What it does not check

- **It does not check that the output is readable.** A task that failed before it logged anything
  prints an empty section, which is itself a fact worth seeing.
- **`databricks jobs get-run` and friends are allowed**, and the script uses them. What is refused
  is starting a job without the reporting behind it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
RUNNER = REPO_ROOT / "ops" / "run_job.sh"

_STARTS_A_JOB = re.compile(r"databricks\s+jobs\s+run-now")
_COMMENT = re.compile(r"^\s*#.*$", re.MULTILINE)

FILES = sorted(WORKFLOWS.glob("*.yml")) if WORKFLOWS.is_dir() else []


def test_the_runner_exists_and_is_executable() -> None:
    """An absent script makes every assertion below it vacuous."""
    assert RUNNER.is_file(), f"{RUNNER} is gone; this gate and the workflows move with it."
    assert RUNNER.stat().st_mode & 0o111, (
        f"{RUNNER} is not executable, so every workflow calling it fails with Permission denied "
        "— after the approval and before the job. `git update-index --chmod=+x` it."
    )
    assert FILES, f"no workflows under {WORKFLOWS} for this to be about."


@pytest.mark.parametrize("path", FILES, ids=[p.name for p in FILES])
def test_a_workflow_starts_jobs_through_the_runner(path: Path) -> None:
    text = _COMMENT.sub("", path.read_text(encoding="utf-8"))
    assert not _STARTS_A_JOB.search(text), (
        f"{path.name} starts a job with `databricks jobs run-now` directly.\n\n"
        "On failure that reports `Workload failed, see run output for details` and nothing else, "
        "from a step that has already spent an environment approval and started compute. Use "
        "the runner, which prints the run page and every failed task's output:\n"
        '    ops/run_job.sh "$JOB_ID" "what this job is doing"'
    )
