"""A job that runs a command-line tool installs it first.

**This exists because `destroy.yml` did not.** Its first real dispatch derived the layer order
correctly, printed it, and then died:

    ── destroying, in this order: lakehouse foundation
    ##[error]Process completed with exit code 127

**127 is `command not found`.** `terraform` is not on a GitHub runner by default; `deploy.yml`
installs it with `hashicorp/setup-terraform`, and `destroy.yml` was written by copying that file's
shape **without that step**. Everything either file argues about — the four-way branch on the `ci`
run, the backend configured at `init`, the reverse dependency order, the survivor list — was
correct, and the job could not run a single Terraform command.

## Why a gate rather than a fix

`backfill.yml` and `run.yml` are unwritten and both will apply or read Terraform state. Each will
be written the way `destroy.yml` was: by copying the shape of a file that works. **The step that
is easiest to omit is the one that is not about this project at all** — it configures the runner,
so it reads as boilerplate, and boilerplate is what a careful reader skips when they are
concentrating on the argument.

**And the failure is late and expensive.** It happens after the environment approval, after
credentials are minted, and — in `destroy`'s case — with the estate still standing and the run
reported red for a reason that has nothing to do with the estate.

## What it does not check

- **It does not check the action's version.** `@v3` today; a bump is a decision somebody makes,
  not a defect.
- **It reads `run:` blocks, so a `terraform` invoked from inside a script is invisible** — the
  same limit `tests/ops/test_workflow_shell.py` and `tests/ops/test_plan_jobs_do_not_apply.py`
  both declare. The value is that the omission requires an obvious extra step, not that it is
  impossible.
- **It says nothing about `terraform` being on the *runner's* PATH for other reasons.** A job that
  installed it some other way would fail this and be right to; the fix then is to say so here.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"

#: **Three tools, and the third and fourth were found by looking rather than by failing.**
#:
#: `terraform` was the instance: `destroy.yml` died at exit 127 with its layer order already
#: derived and printed. `databricks` and `uv` were then found in `backfill.yml` and `run.yml` by
#: reading them for the same shape — `backfill` would have died on its first job, `run` **after
#: driving a whole day**.
#:
#: Each entry is `(tool, the action that installs it)`. Matched on the action's repository rather
#: than its version, so a bump does not empty this gate's population.
TOOLS: tuple[tuple[str, str], ...] = (
    ("terraform", "hashicorp/setup-terraform"),
    ("databricks", "databricks/setup-cli"),
    ("uv", "astral-sh/setup-uv"),
)


#: An invocation in a shell script. The word boundary matters: `terraform-docs`, `uv.lock` and a
#: path like `infra/terraform.tfstate` are not invocations.
#:
#: **`[-a-z]` rather than `[a-z]`, and the population guard is what said so.** The first version
#: required a letter after the space and every real `terraform` invocation in this repository
#: begins with a flag — `terraform -chdir="infra/$layer" init`. It matched nothing, and the
#: population test refused rather than letting the file pass on an empty population, which is the
#: whole reason that test is written before the case it guards.
def _invocation(tool: str) -> re.Pattern[str]:
    return re.compile(rf"(?:^|[\s;&|(]){tool}\s+[-a-z]", re.MULTILINE)


def _jobs_running_tools() -> list[tuple[str, str, str, str, dict[str, Any]]]:
    """Every `(workflow, job, tool, setup action, spec)` where a `run:` block invokes a tool."""
    found: list[tuple[str, str, str, str, dict[str, Any]]] = []
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        document: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        for job, spec in (document.get("jobs") or {}).items():
            for tool, action in TOOLS:
                pattern = _invocation(tool)
                for step in spec.get("steps") or []:
                    if isinstance(step, dict) and pattern.search(str(step.get("run", ""))):
                        found.append((path.name, job, tool, action, spec))
                        break
    return found


JOBS = _jobs_running_tools()


def test_some_job_runs_a_tool() -> None:
    """The reader answers, rather than reporting an empty population.

    Every assertion below is `for each job that runs terraform`. If the detector stopped matching
    — a rename, `run:` becoming a list, `jobs` reshaping — the population would empty and this
    file would pass on nothing at all.
    """
    assert WORKFLOWS.is_dir(), ".github/workflows/ is not where this test looks for it"
    assert JOBS, (
        "no job in any workflow invokes any of these tools in a `run:` block. Either nothing "
        "applies infrastructure or drives the estate from CI any more — which is a finding — or "
        "this reader stopped seeing it. Neither is a reason for the case below to pass."
    )
    for workflow, job, tool, _, _ in JOBS:
        print(f"  {workflow} :: {job} runs {tool}")


@pytest.mark.parametrize(
    ("workflow", "job", "tool", "action", "spec"),
    JOBS,
    ids=[f"{w} :: {j} :: {t}" for w, j, t, _, _ in JOBS],
)
def test_a_job_that_runs_a_tool_installs_it(
    workflow: str, job: str, tool: str, action: str, spec: dict[str, Any]
) -> None:
    installs = any(
        action in str(step.get("uses", ""))
        for step in spec.get("steps") or []
        if isinstance(step, dict)
    )
    assert installs, (
        f"{workflow} :: {job} runs `{tool}` and no step installs it. It is not on a GitHub "
        "runner by default, so the job fails with exit 127 — command not found — **after** the "
        "environment approval has been spent and the credentials minted, for a reason that has "
        "nothing to do with the estate.\n\n"
        f"Add `- uses: {action}@…` before the step that runs it."
    )
