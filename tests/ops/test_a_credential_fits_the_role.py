"""No workflow asks for a credential the role cannot issue.

    Could not assume role with OIDC: The requested DurationSeconds exceeds the
    MaxSessionDuration set for this role.

`run.yml` asked for **15600** seconds. `infra/bootstrap/oidc.tf` caps the role at **14400**. Both
numbers were projections, both said so in their own comments — *four hours against a modelled ~2*
and *twice the longest modelled workflow… the first real run replaces it, downward* — and
**nothing compared them**. So the first dispatch of that workflow failed before its first step, on
arithmetic that had been wrong since the day both were written.

`tests/ops/test_credential_outlives_job.py` already holds the other end: the credential must
outlive the job it is issued for. That one looks down from the timeout; this one looks up at the
role. **A number bounded on one side is bounded on one side**, and the gap between them is where
this sat.

## What it does not check

- **It does not check that the ceiling is right.** `oidc.tf` argues for it and says it comes down
  once a real dispatch has been measured; what a workflow may *ask* for is a different question
  from what the role *should* allow.
- **It reads Terraform and YAML, not AWS.** A role edited in the console is invisible here, which
  is `CLAUDE.md`'s *IaC only* promise being checked rather than the account being read.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
OIDC = REPO_ROOT / "infra" / "bootstrap" / "oidc.tf"

_COMMENT_YAML = re.compile(r"^\s*#.*$", re.MULTILINE)
_DURATION = re.compile(r"^\s*role-duration-seconds:\s*(\d+)\s*$", re.MULTILINE)
_MAX = re.compile(r"^\s*max_session_duration\s*=\s*(\d+)\s*$", re.MULTILINE)


def _ceiling() -> int:
    """What `infra/bootstrap` allows the role to issue."""
    text = _COMMENT_YAML.sub("", OIDC.read_text(encoding="utf-8"))
    found = _MAX.findall(text)
    assert len(found) == 1, (
        f"expected exactly one `max_session_duration` in {OIDC.name} and found {len(found)}. "
        "Two would mean two roles or a stale copy, and this gate would be comparing against "
        "whichever the regex reached first."
    )
    return int(found[0])


def _asked() -> list[tuple[str, int]]:
    """Every `(workflow, seconds)` any workflow asks the role for, comments removed first."""
    found: list[tuple[str, int]] = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        text = _COMMENT_YAML.sub("", path.read_text(encoding="utf-8"))
        found.extend((path.name, int(seconds)) for seconds in _DURATION.findall(text))
    return found


CEILING = _ceiling()
ASKED = _asked()


def test_there_are_credentials_to_check() -> None:
    """An empty population passes every assertion below it and proves nothing."""
    assert ASKED, (
        "no workflow asks for `role-duration-seconds`. Either every one of them now takes the "
        "action's default of one hour — which `oidc.tf` records as having killed a dispatch "
        "thirty minutes before its own timeout — or this reader stopped seeing them."
    )


@pytest.mark.parametrize(("workflow", "seconds"), ASKED, ids=[f"{w}:{s}" for w, s in ASKED])
def test_a_workflow_asks_for_no_more_than_the_role_allows(workflow: str, seconds: int) -> None:
    assert seconds <= CEILING, (
        f"{workflow} asks for {seconds}s and the role allows {CEILING}s.\n\n"
        "AWS refuses the assume-role outright, so the workflow fails before its first step — "
        "after the environment approval has been spent. Lower the request, or raise "
        "`max_session_duration` and say why: that number is a ceiling on how long a stolen "
        "credential is useful, and `oidc.tf` argues it should come down rather than up."
    )
