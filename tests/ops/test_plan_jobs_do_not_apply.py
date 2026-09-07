"""A job that presents `:environment:plan` may run Terraform that reads, and nothing that writes.

## What the `plan` environment is for, and why it is dangerous

`infra/bootstrap/github.tf` gives `deploy` and `destroy` a required reviewer and gives `plan`
none, deliberately: a plan is read-only, it is *what the approval on `deploy` is an approval of*,
and an approval collected before the plan exists is an approval of nothing.
`tests/infra/test_environment_reviewers.py` is what keeps that property from being "fixed".

**The consequence is that `:environment:plan` is the one federated subject this repository trusts
with no human in the path.** The trust policy accepts it from any workflow in this repository, for
ever. So a job that declares `environment: plan` and then applies has a fully credentialled,
entirely unattended path to the account — and it would look, in review, like a workflow that plans.

**The jobs that will do this do not exist yet.** `destroy.yml`, `backfill.yml` and `run.yml` are
unwritten, and each is written by somebody who wants a fast unattended path and finds one already
trusted. That is why this gate is written before them rather than after: **the population it
protects is empty today and is the whole reason it exists.**

## The predicate is an allowlist, and that is the point of the file

The obvious form is *no `run:` in a `plan` job contains `terraform apply`*. **That is a denylist,
and a denylist is the `claim-[1-7]` defect moved from the population into the predicate.** It is
defeated by `terraform -chdir=… apply` — the spelling `deploy.yml` itself uses — by
`terraform apply -auto-approve` with an argument in between, by `tofu apply`, by
`terraform import` and `terraform state rm`, which are not `apply` and still write.

**So: every Terraform-shaped invocation must name a subcommand on `READS`, and anything else —
including a subcommand this file has never heard of — is a failure.** That is `Money`'s rule one
layer over: *a bound that rounds toward what it forbids is not a bound.*

## The limits, declared rather than discovered

- **A `run:` block that invokes a script is opaque to this gate.** `./scripts/anything.sh` defeats
  it completely. So does a composite action, which `test_workflow_shell.py` already declares out
  of scope for the same reason. **The value of this gate is that it makes the abuse require an
  obvious extra step, not that it makes it impossible.**
- **It reads configuration, not tokens.** AWS will keep issuing on `:environment:plan` whatever
  this file says. What this guarantees is that no such job reaches `main`, because `ci` is
  required on every pull request — and that composes with
  `deployment_branch_policy { protected_branches = true }`, which makes `main` the only branch
  that can dispatch to the environment at all.
- **That composition rests on `docs/FINDINGS.md`'s finding 3** — whether a branch policy resolves
  a ruleset-protected default branch — which is still open and is first answered by the first
  dispatch. **If it fails open, this gate is the only thing standing there.**

## The population comes from the existing walker rather than a third glob

`_run_blocks()` in `tests/ops/test_workflow_shell.py` already enumerates every `run:` in every
workflow. **This imports it rather than writing another `glob`**: `ops/figures.py` and that file
are already two enumerations of one population, and a third would be the drift this repository
catalogues, arriving in the gate written to prevent an unattended apply.
"""

from __future__ import annotations

import re
from typing import Any

import pytest
import yaml

from tests.ops.test_workflow_shell import WORKFLOWS, _run_blocks

#: The unattended environment. Named once.
PLAN = "plan"

#: Terraform subcommands that only read. **Everything else fails**, including a subcommand nobody
#: here has heard of — `import`, `state`, `taint`, `force-unlock` and `refresh` all write, and so
#: does whatever HashiCorp ships next.
READS = frozenset(
    {"init", "plan", "show", "validate", "fmt", "version", "providers", "output", "graph"}
)

#: The binaries. `tofu` is OpenTofu and `terragrunt` wraps either; all three take the same verbs,
#: and a denylist on the word `terraform` would miss two of the three.
BINARIES = ("terraform", "tofu", "terragrunt")

_INVOCATION = re.compile(rf"\b(?P<binary>{'|'.join(BINARIES)})\b(?P<rest>[^\n;&|]*)")


def _job_environments() -> dict[tuple[str, str], str | None]:
    """`(workflow, job) -> environment name`, read from the same files the walker reads.

    An `environment:` may be a string or a mapping with `name:`; both forms are the same
    declaration to GitHub and both must be the same declaration here.
    """
    found: dict[tuple[str, str], str | None] = {}
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        document: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        for job, spec in (document.get("jobs") or {}).items():
            environment = spec.get("environment")
            if isinstance(environment, dict):
                environment = environment.get("name")
            found[(path.name, job)] = environment
    return found


ENVIRONMENTS = _job_environments()
BLOCKS = _run_blocks()


def _plan_blocks() -> list[tuple[str, str, str]]:
    """Every `(workflow, where, script)` belonging to a job that declares `environment: plan`."""
    return [
        (workflow, where, script)
        for workflow, where, script in BLOCKS
        if ENVIRONMENTS.get((workflow, where.split(" :: ")[0])) == PLAN
    ]


def _subcommand(rest: str) -> str | None:
    """The first token after the binary that is not a flag, or `None` if there is none."""
    for token in rest.split():
        if token.startswith("-"):
            continue
        return token
    return None


def test_the_environment_reader_can_see_an_environment() -> None:
    """The instrument answers, rather than reporting an empty population.

    **`plan` jobs do not exist yet and that is expected** — `destroy.yml`, `backfill.yml` and
    `run.yml` are unwritten. What is *not* acceptable is this file going green because the
    `environment:` key stopped being read at all: a rename, a mapping form nobody handled, or
    `jobs` reshaping would empty `ENVIRONMENTS` and every case below would pass on nothing.

    So the assertion is on the reader, not on the population: **some job in this tree declares
    some environment.** Today that is `deploy.yml`'s apply job, and the day a `plan` job lands it
    is read by machinery this test has already proved works.
    """
    assert ENVIRONMENTS, "no job in any workflow was read at all — the reader, not the population"
    declared = {name for name in ENVIRONMENTS.values() if name}
    assert declared, (
        "no job in this repository declares an `environment:`. Either every environment was "
        "removed — which would mean nothing federates to AWS any more — or this reader stopped "
        "seeing the key. Both are findings; neither is a reason for the cases below to pass."
    )
    print(f"  environments declared: {sorted(declared)}")
    print(f"  jobs on `{PLAN}`: {len(_plan_blocks())} run-block(s)")


@pytest.mark.parametrize(
    ("workflow", "where", "script"),
    _plan_blocks() or [("", "", "")],
    ids=[f"{w} :: {x}" for w, x, _ in _plan_blocks()] or ["no plan job exists yet"],
)
def test_a_plan_job_runs_no_terraform_that_writes(workflow: str, where: str, script: str) -> None:
    if not workflow:
        pytest.skip("no job declares `environment: plan` yet — the reader is asserted above")

    for match in _INVOCATION.finditer(script):
        subcommand = _subcommand(match.group("rest"))
        assert subcommand is not None, (
            f"{workflow} :: {where} invokes `{match.group('binary')}` with no subcommand this "
            "gate can read. It refuses rather than guessing: an invocation it misreads is one it "
            "reports as read-only."
        )
        assert subcommand in READS, (
            f"{workflow} :: {where} declares `environment: {PLAN}` and runs "
            f"`{match.group('binary')} {subcommand}`.\n\n"
            f"`{PLAN}` is the one environment with no required reviewer — deliberately, because a "
            "plan is read-only and an approval collected before the plan exists is an approval of "
            "nothing. A job on it that writes has a fully credentialled, entirely unattended path "
            "to the account, and reads in review like a job that plans.\n\n"
            f"Permitted subcommands: {sorted(READS)}. If this one only reads, add it there with "
            "the reason — the point of this gate is that the decision is written down rather "
            "than inferred from a verb."
        )
