"""`ops/run_job.sh` exits 1 on a job whose run *ended* without succeeding.

`databricks jobs run-now --timeout` returns 0 when the run reaches TERMINATED or SKIPPED,
whatever `result_state` says: a task that raised is TERMINATED / FAILED, exit 0. The script read
that as success for as long as it existed, and a green step would have let `backfill` apply the
previous model's version and `run` assert yesterday's readout. Found by a fresh-context review on
2026-09-12, from the SDK's waiter.

**The attack is a `databricks` on PATH that answers the way the real one does on that path** --
exit 0 from `run-now`, a run whose `result_state` is FAILED from `get-run` -- and the assertion
is the script's exit code. The shim answers every subcommand the script calls, so a script that
grew a call the shim does not know fails loudly here rather than passing on an empty answer.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPO_ROOT / "ops" / "run_job.sh"

_SHIM = """#!/usr/bin/env bash
# A databricks CLI that ends every run the way $RESULT_STATE says, and exits 0 from run-now.
case "$1 $2" in
  "jobs run-now") exit 0 ;;
  "jobs list-runs") printf '[{"run_id": 4242}]' ;;
  "jobs get-run") printf '{"run_page_url": "https://example.invalid/run/4242", "state": {"life_cycle_state": "TERMINATED", "result_state": "%s"}, "tasks": [{"task_key": "t", "run_id": 4243, "state": {"result_state": "%s", "state_message": "shim"}}]}' "$RESULT_STATE" "$RESULT_STATE" ;;
  "jobs get-run-output") printf '{"error": "the shim says the task failed"}' ;;
  *) echo "shim: unexpected call: $*" >&2; exit 97 ;;
esac
"""


def _run(tmp_path: Path, result_state: str) -> subprocess.CompletedProcess[str]:
    shim = tmp_path / "databricks"
    shim.write_text(_SHIM, encoding="utf-8")
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR)
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "RESULT_STATE": result_state}
    return subprocess.run(
        ["bash", str(RUNNER), "1", "a job"], env=env, capture_output=True, text=True, check=False
    )


@pytest.mark.parametrize("result_state", ["FAILED", "CANCELED", "TIMEDOUT"])
def test_a_run_that_ended_without_success_fails_the_step(tmp_path: Path, result_state: str) -> None:
    finished = _run(tmp_path, result_state)
    assert finished.returncode == 1, (
        f"run-now exited 0 and the run's result_state was {result_state}; the step exited "
        f"{finished.returncode}.\n{finished.stdout}\n{finished.stderr}"
    )
    assert result_state in finished.stdout, "the diagnostic does not name the result state"
    assert "the shim says the task failed" in finished.stdout, (
        "the failing task's output was not fetched"
    )


def test_a_run_that_succeeded_passes_the_step(tmp_path: Path) -> None:
    finished = _run(tmp_path, "SUCCESS")
    assert finished.returncode == 0, finished.stdout + finished.stderr
    assert "result_state SUCCESS" in finished.stdout
