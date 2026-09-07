"""A job that mints AWS credentials must hold them for longer than its own timeout.

**This exists because `deploy.yml` did not.** Its apply job carried `timeout-minutes: 90` and a
credential of **60** — `aws-actions/configure-aws-credentials` requests one hour unless told
otherwise, and it does not refresh. A dispatch that ran past the hour therefore died on an expired
credential **thirty minutes before the timeout that was supposed to end it**, after the
environment approval had been spent and with layers half applied.

**The timeout was not the thing ending the job**, which is the entire reason a timeout is written
down. `CLAUDE.md`'s rule about numbers in configuration is that each is an assertion wearing a
number instead of a verb; here two numbers asserted incompatible things and neither was wrong on
its own.

## Why this is a gate and not a fix

`destroy.yml`, `backfill.yml` and `run.yml` are unwritten. Each will be written by copying the
shape of `deploy.yml` — and `CLAUDE.md` models `backfill` at ~1.5 h and `run` at ~2 h, so **both
will carry timeouts that the default hour cannot cover.** The failure is invisible until a real
dispatch runs long, which is the most expensive moment to discover it: the estate is half built
and the approval is gone.

**And the ceiling is the half that is easy to see.** Raising `max_session_duration` in
`infra/bootstrap/oidc.tf` without setting `role-duration-seconds` changes nothing at all, because
the action asks for an hour regardless of what the role permits. This asserts the half that is
easy to forget.

## What it does not check

- **It does not read `max_session_duration`.** That lives in Terraform, it is a *ceiling* rather
  than a duration, and a request above it fails at `AssumeRoleWithWebIdentity` with a message that
  names the ceiling — loudly, at the start of the job, before anything is applied. The silent
  failure is the one this file is about.
- **It does not know how long a job really takes.** Both numbers are projections until a dispatch
  measures them. What it asserts is their *order*, which is true regardless of either value.
- A job with no `timeout-minutes` inherits GitHub's six-hour default; that is reported as its own
  failure rather than compared, because six hours is longer than any credential this project will
  ever mint.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"

#: The action that mints AWS credentials. Matched on the repository rather than the version, so a
#: bump from `@v4` to `@v5` does not silently empty this gate's population.
CREDENTIALS_ACTION = "aws-actions/configure-aws-credentials"

#: GitHub's own default when a job declares no `timeout-minutes`, in minutes.
GITHUB_DEFAULT_TIMEOUT = 360


def _credential_jobs() -> list[tuple[str, str, dict[str, Any]]]:
    """Every `(workflow, job, spec)` whose steps mint AWS credentials."""
    found: list[tuple[str, str, dict[str, Any]]] = []
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        document: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        for job, spec in (document.get("jobs") or {}).items():
            for step in spec.get("steps") or []:
                if isinstance(step, dict) and CREDENTIALS_ACTION in str(step.get("uses", "")):
                    found.append((path.name, job, spec))
                    break
    return found


JOBS = _credential_jobs()


def test_some_job_mints_credentials() -> None:
    """The reader answers, rather than reporting an empty population.

    A rename of the action, a move to a composite step, or `jobs` reshaping would empty `JOBS` and
    turn every case below green on nothing. This asserts the instrument; the population is
    whatever it finds.
    """
    assert WORKFLOWS.is_dir(), ".github/workflows/ is not where this test looks for it"
    assert JOBS, (
        f"no job in any workflow uses `{CREDENTIALS_ACTION}`. Either nothing federates to AWS any "
        "more — which is a finding — or this reader stopped seeing it, which is a different one. "
        "Neither is a reason for the cases below to pass."
    )


@pytest.mark.parametrize(
    ("workflow", "job", "spec"),
    JOBS,
    ids=[f"{w} :: {j}" for w, j, _ in JOBS],
)
def test_the_credential_outlives_the_jobs_timeout(
    workflow: str, job: str, spec: dict[str, Any]
) -> None:
    timeout = spec.get("timeout-minutes")
    assert timeout is not None, (
        f"{workflow} :: {job} mints AWS credentials and declares no `timeout-minutes`, so it "
        f"inherits GitHub's {GITHUB_DEFAULT_TIMEOUT}-minute default — longer than any credential "
        "this project will mint, which means the credential ends the job and the timeout is "
        "decoration. Declare one."
    )

    step = next(
        s
        for s in spec["steps"]
        if isinstance(s, dict) and CREDENTIALS_ACTION in str(s.get("uses", ""))
    )
    seconds = (step.get("with") or {}).get("role-duration-seconds")
    assert seconds is not None, (
        f"{workflow} :: {job} mints AWS credentials without `role-duration-seconds`, so it asks "
        f"for one hour whatever the role permits — and this job may run for {timeout} minutes. "
        "Raising `max_session_duration` in infra/bootstrap does not fix this: the ceiling is not "
        "the request. Ask for what the job may take."
    )

    assert int(seconds) > int(timeout) * 60, (
        f"{workflow} :: {job} may run for {timeout} minutes and holds credentials for "
        f"{int(seconds) // 60}. A dispatch that runs long dies on an expired credential before "
        "the timeout that is supposed to end it — after the environment approval has been spent, "
        "and with the estate half applied. The timeout must be the thing that ends the job."
    )
