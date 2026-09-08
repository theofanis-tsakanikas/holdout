"""The failure reporter's own filter reads both shapes the CLI returns.

**The diagnostic written to explain a failure failed instead of explaining it.** `ops/run_job.sh`
was added because `backfill` reported *Workload failed, see run output for details* and nothing
else. Its first dispatch printed:

    ── the baseline, under all-control arms, into bronze FAILED; fetching what the job said
    jq: error (at <stdin>:35): Cannot index array with string "runs"

`databricks jobs list-runs --output json` returns a **bare array**; the REST API documents
`{"runs": [...]}`, and the script was written against the documentation. So the second dispatch
cost what the first one did — which is the exact cost the script exists to stop paying.

**The filter is read out of the script rather than copied here.** A test asserting that a copy of
a filter works is a test of the copy: `ops/ci_pack.py`'s own comment makes the same point about
declared costs, and this repository has now filed three findings whose shape is *two copies of one
thing, one of them wrong*.

## What it does not check

- **It does not check the CLI's real output**, which would need a workspace. What it checks is
  that the filter survives both shapes, which is what the failure was about.
- **`jq` is required rather than skipped.** A skipped test looks exactly like a passing one, and
  `tests/boundary/test_the_engine_is_never_skipped.py` refuses that arrangement one directory
  over. `jq` is preinstalled on GitHub runners; on a laptop, install it.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPO_ROOT / "ops" / "run_job.sh"

#: The two shapes, and an empty one. `list-runs` returns the first; the REST API documents the
#: second; a job that never started returns nothing to index either way.
SHAPES: tuple[tuple[str, str, str], ...] = (
    ("bare array", json.dumps([{"run_id": 42}]), "42"),
    ("documented object", json.dumps({"runs": [{"run_id": 42}]}), "42"),
    ("array with nothing in it", json.dumps([]), ""),
    ("object with nothing in it", json.dumps({"runs": []}), ""),
)

_FILTER = re.compile(r"run_id=\$\(printf '%s' \"\$runs\" \| jq -r '([^']*)'")


def _run_id_filter() -> str:
    """The filter `ops/run_job.sh` actually uses to find the run id."""
    match = _FILTER.search(RUNNER.read_text(encoding="utf-8"))
    assert match, (
        "the run-id filter is not where this gate looks for it in ops/run_job.sh. Either it "
        "moved — in which case this reader moves with it — or the script stopped extracting a "
        "run id, and then the reporter has nothing to fetch."
    )
    return match.group(1)


def test_jq_is_installed() -> None:
    """Required rather than skipped: a skipped test looks exactly like a passing one."""
    assert shutil.which("jq"), (
        "jq is not on PATH. `ops/run_job.sh` parses the Databricks CLI's JSON with it, so this "
        "gate cannot run without it and neither can the workflows. GitHub runners have it "
        "preinstalled; on macOS, `brew install jq`."
    )


@pytest.mark.parametrize(
    ("name", "payload", "expected"),
    SHAPES,
    ids=[name for name, _p, _e in SHAPES],
)
def test_the_filter_reads_the_shape(name: str, payload: str, expected: str) -> None:
    result = subprocess.run(
        ["jq", "-r", _run_id_filter()],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"the run-id filter failed on the {name} shape:\n{result.stderr.strip()}\n\n"
        "This is what the first version did on a real dispatch: the reporter written to explain "
        "a failed job failed itself, and the cost of one diagnosis became two."
    )
    assert result.stdout.strip() == expected, (
        f"the {name} shape produced {result.stdout.strip()!r} and not {expected!r}."
    )
