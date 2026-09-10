"""The loop that removes the network Databricks left, and the two ways it reached outside it.

`destroy.yml` deletes the VPC that Databricks-managed networking leaves behind. The loop is
scoped to one VPC — the one whose name carries the workspace id this run destroyed — and twice
that scope was true of the comment and not of the commands under it.

**One: an enumeration with no VPC in it.** The elastic-IP step read
`describe-addresses --query 'Addresses[?AssociationId==null]'`, which is every unassociated
address **in the region**, in an account holding four other projects. It would have released an
address somebody else had allocated and not yet attached, from inside a loop whose entire subject
is one VPC. Nothing caught it because the account has held exactly one spare address every time
it ran — *a check is not tested by the data that happens to be there.*

**Two: a delete grant conditioned on a tag the resources do not carry.** Measured 2026-09-10, run
34471563253: the VPC carries `Name = databricks-WorkerEnvId(workerenv-…)` and **nothing else in
the set does** — not the NAT gateway, the address, the endpoint or the internet gateway, and not
most of the subnets, security groups and route tables. `ec2:Vpc` is available as a condition key
for three of those types and for none of the rest, read out of AWS's service reference rather than
assumed. So the loop now names every child after its parent before deleting it, and the IAM
condition becomes true instead of vacuous.

## What this asserts

- **Every enumeration inside the loop names the VPC.** A `describe` that does not is a question
  asked of the whole region inside a block scoped to one network.
- **The set that is tagged is the set that is deleted.** Every variable a delete loop iterates
  over appears in the list handed to `create-tags`, so a resource type added to the cleanup and
  forgotten in the tagging goes red here rather than at three in the morning with half a VPC
  removed.
- **The tagging precedes the first deletion.** Afterwards there is nothing left to tag.

**Measured biting, four planted mutations, each restored after:**

    the address list read region-wide again        ->  red
    one type deleted and left out of `children`    ->  red
    the tagging moved below the first deletion     ->  red
    the tagging removed entirely                   ->  red
    the tree as it stands                          ->  green

## What it does not check

- **It does not check that the tag is accepted**, only that it is asked for. IAM is the account's
  answer and `destroy`'s own closing step is what asks it.
- **It reads text.** A `describe` built from a variable assembled elsewhere would satisfy this and
  could still be region-wide — the limit every reader over a shell script here declares.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

DESTROY = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "destroy.yml"

#: The loop, from the line that announces it to the deletion of the VPC itself.
_BLOCK = re.compile(
    r"removing the network Databricks left.*?delete-vpc --vpc-id \"\$v\"", re.DOTALL
)

#: An enumeration, and the removals. `release-address` is a removal that is not spelled `delete`,
#: which is exactly the one the region-wide read was hiding behind.
_DESCRIBE = re.compile(r"aws ec2 (describe-[a-z-]+)(.*?)--output text", re.DOTALL)
_REMOVES = re.compile(r"aws ec2 (?:delete-[a-z-]+|release-address|detach-[a-z-]+)")
_TAGS = re.compile(r"aws ec2 create-tags")
_LOOP = re.compile(r"for\s+\w+\s+in\s+\$(\w+);\s*do(.*?)\n\s*done", re.DOTALL)
_CHILDREN = re.compile(r"children=\"([^\"]*)\"")


def _block() -> str:
    document: Any = yaml.safe_load(DESTROY.read_text(encoding="utf-8"))
    for spec in (document.get("jobs") or {}).values():
        for step in spec.get("steps") or []:
            if not isinstance(step, dict):
                continue
            found = _BLOCK.search(str(step.get("run", "")))
            if found:
                return found.group(0)
    return ""


BLOCK = _block()


def test_there_is_a_cleanup_to_check() -> None:
    """An empty population passes everything below it and proves nothing."""
    assert BLOCK, (
        "no step in destroy.yml removes the network Databricks left behind. Either the leak "
        "stopped happening -- which would be a finding worth writing down, since it is a "
        "property of Databricks-managed networking rather than of this repository -- or this "
        "reader stopped seeing the block."
    )


def test_every_enumeration_inside_the_loop_names_the_vpc() -> None:
    found = _DESCRIBE.findall(BLOCK)
    assert found, "the cleanup enumerates nothing, so it can delete nothing it looked up"

    unscoped = [call for call, body in found if "$v" not in body]
    assert not unscoped, (
        f"{unscoped} asks the whole region from inside a loop scoped to one VPC. This account "
        "holds four other projects; an enumeration with no VPC in it will return their "
        "resources, and the next line deletes what the enumeration returned."
    )


def test_the_set_that_is_tagged_is_the_set_that_is_deleted() -> None:
    declared = _CHILDREN.search(BLOCK)
    assert declared, (
        "the cleanup does not build a `children` list. The delete grant in "
        "infra/bootstrap/oidc.tf is conditioned on a Name tag that only the VPC carries, so "
        "without this the destroy is authorised to remove exactly the one resource that cannot "
        "go until the others have."
    )
    tagged = set(re.findall(r"\$(\w+)", declared.group(1)))

    deleted = {name for name, body in _LOOP.findall(BLOCK) if _REMOVES.search(body)}
    assert deleted, "no loop in the cleanup deletes anything"

    missing = sorted(deleted - tagged)
    assert not missing, (
        f"{missing} is deleted and never tagged. Its resources carry no Name of their own -- "
        "measured -- so the IAM condition cannot match them and the destroy stops on the first "
        "one, with the layers already gone and the VPC still standing."
    )


def test_the_tagging_precedes_the_first_deletion() -> None:
    tags = _TAGS.search(BLOCK)
    removes = _REMOVES.search(BLOCK)
    assert tags and removes, "the cleanup either tags nothing or deletes nothing"
    assert tags.start() < removes.start(), (
        "the children are tagged after the first deletion. By then the resource the tag was for "
        "is either gone or was refused, which is the failure this ordering exists to prevent."
    )
