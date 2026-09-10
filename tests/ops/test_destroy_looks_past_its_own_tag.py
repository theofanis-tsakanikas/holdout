"""`destroy` checks for the workspace's managed VPC, which carries none of this project's tags.

**The survivor check enumerates by `holdout:project`, deliberately** — that is the tag the budget
filters on and the reaper reads, so anything this project *created* carries it. Databricks-managed
networking is the exception: `infra/foundation/workspace.tf` declares no `network_id`, so
Databricks creates a VPC in this account named `databricks-WorkerEnvId(workerenv-<id>-…)`, with a
NAT gateway and a public IPv4 in it, and tags it with none of ours.

**Deleting the workspace did not remove it.** Measured 2026-09-08: two such VPCs, one per destroy
cycle, the older 24 hours old and still running — about 35 USD a month for the NAT gateway and 4
for the address, each. Every destroy reported success. The tagged survivor list was correct and
complete about the population it enumerates, and the population did not contain the money.

> **A population enumerated by a property is blind to whatever does not have it.** That is the
> same sentence as `ops/figures.py`'s coverage rows and as the three findings in this register
> about hand-kept lists; here the property was a tag and the thing without it was the only thing
> still costing anything.

## What this asserts

That `destroy.yml` reads the workspace id **before** the layer publishing it is destroyed, and
that it looks for that workspace's VPC afterwards. Both halves: the id is only available before,
and the check is only meaningful after.

## What it does not check

- **It does not check that the deletion succeeds.** The workflow asks the account afterwards and
  fails if anything is left, which is where that is caught — *verified by asking the account,
  never by reading a workflow's exit code.*
- **It reads the workflow, not a run.** The same limit every gate over a file here has.

> **This gate said the workflow reports rather than deletes, and that was right for one day.**
> Three destroys later, reporting had cost three manual cleanups; the authority question answers
> itself, because this project's deploy created the workspace whose network this is. What the
> gate holds now is the *scope*: the workspace id this run destroyed, and nothing wider.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DESTROY = REPO_ROOT / ".github" / "workflows" / "destroy.yml"

#: The parameter that names the workspace, and the shape Databricks gives its VPC.
WORKSPACE_PARAMETER = "/holdout/foundation/workspace_id"
VPC_NAME = "databricks-WorkerEnvId(workerenv-"

#: A whole line whose first non-blank character is `#`: a YAML comment, or a shell comment inside
#: a `run:` block. Either way it is not a command — and both halves of this gate name the strings
#: they look for, in prose, above the lines that use them. **The first version went red against
#: its own explanation**, which is the third gate in this repository to do that; a gate that
#: cannot be documented beside the thing it checks is one nobody can keep.
_COMMENT = re.compile(r"^\s*#.*$", re.MULTILINE)


def _script() -> str:
    """The workflow with its comments removed, which is what it actually runs."""
    return _COMMENT.sub("", DESTROY.read_text(encoding="utf-8"))


def test_the_workflow_exists() -> None:
    assert DESTROY.is_file(), f"{DESTROY} is gone; this gate and the workflow move together."


def test_the_workspace_id_is_read_before_it_is_destroyed() -> None:
    text = _script()
    assert WORKSPACE_PARAMETER in text, (
        f"destroy.yml never reads {WORKSPACE_PARAMETER}. It is published by `foundation` and "
        "destroyed with it, so after the destroy there is nothing left that names the workspace "
        "— and without the name, the VPC Databricks made for it cannot be looked for."
    )
    read_at = text.index(WORKSPACE_PARAMETER)
    looked_at = text.index(VPC_NAME) if VPC_NAME in text else -1
    assert looked_at > read_at, (
        "destroy.yml looks for the managed VPC before it reads the workspace id, or does not "
        "look at all. The id is available only before the destroy and the check is meaningful "
        "only after it."
    )


def test_the_workflow_looks_for_the_managed_vpc() -> None:
    text = _script()
    assert VPC_NAME in text, (
        "destroy.yml does not look for `databricks-WorkerEnvId(workerenv-…)`.\n\n"
        "That VPC carries none of this project's tags, so the survivor list — which enumerates "
        "by `holdout:project` — reports OK while a NAT gateway inside it costs about 35 USD a "
        "month. Two of them accumulated that way, one per destroy cycle, and every destroy "
        "exited zero."
    )


def test_the_cleanup_is_scoped_to_the_workspace_this_run_destroyed() -> None:
    """Every VPC the workflow deletes came from the id it read before the destroy.

    **The blast radius is the whole of this.** This account holds four other projects, and a
    cleanup that searched for `databricks-WorkerEnvId(workerenv-*` would match any workspace's
    network, including one this project never created. `infra/bootstrap/oidc.tf` narrows the same
    thing again in IAM — a condition on the tag — so the two have to be wrong together for a
    stranger's VPC to be reachable.
    """
    script = _script()
    assert "delete-vpc" in script, (
        "destroy.yml no longer deletes the network Databricks left. Three cycles of reporting "
        "cost three manual cleanups at about 39 USD a month each; if this went back to "
        "reporting, the reason belongs beside it."
    )
    for line in script.splitlines():
        if VPC_NAME not in line:
            continue
        assert "${workspace_id}" in line, (
            f"this line searches for a Databricks workspace network without naming the workspace "
            f"this run destroyed:\n    {line.strip()}\n\n"
            "Unscoped, it matches any workspace's VPC in an account that holds four other "
            "projects — and the deletion below it is not a report."
        )
