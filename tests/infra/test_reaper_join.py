"""The reaper's two enumerations are joined on a vocabulary both sides actually speak.

**This exists because they were not.** `reap.py` compared `arn.split(":")[2]` against
`name.split("/")[2]`, and the first of those is the ARN's **service** field:

    arn:aws:iam::…:role/holdout-reaper    ->  'iam'
    arn:aws:kms:eu-west-1:…:key/…         ->  'kms'
    /holdout/foundation/reaper_client_id  ->  'foundation'

The two sets share no vocabulary, so **both differences were the whole of both sets, on every
run, for ever** — `published_not_tagged` named every layer and `tagged_not_published` named every
AWS service. An alarm that fires always is not an alarm, and this one is the detector for the case
the SSM inversion exists to catch: a published name with nothing carrying its tag.

**It went unnoticed because the comment stated the defect without seeing it** — *"a published
parameter names the layer that published it, so the join is by layer"* is true of the SSM side and
false of the ARN side, in the same sentence.

## Why the tests below are the shape they are

The join is the one part of the reaper that is pure: no account, no credentials, no clock. So it
is tested directly, and **the cases come from the estate's real ARN and parameter shapes** rather
than from a shape that would make the join look right — the whole defect was a join tested by
nobody, against strings its author never wrote down.

**`boto3` is stubbed rather than installed.** The Lambda runtime provides it, `[tool.mypy]`
already carries the same reasoning as an override, and adding a large cloud SDK to every
developer's environment for one file is a cost with no benefit. The stub is what lets this test
import a module that imports it; nothing below calls anything on it.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REAP = REPO_ROOT / "infra" / "foundation" / "reaper" / "reap.py"


def _load_reap() -> Any:
    """Load `reap.py` by path, with `boto3` stubbed. See the docstring for why."""
    if "boto3" not in sys.modules:
        sys.modules["boto3"] = types.ModuleType("boto3")
    spec = importlib.util.spec_from_file_location("holdout_reap", REAP)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_reaper_exists_where_this_test_says_it_does() -> None:
    """An empty population passes every assertion below it and proves nothing."""
    assert REAP.is_file(), (
        f"{REAP} does not exist. If the reaper moved, this test moves with it — a file that "
        "cannot be found would otherwise turn every case below green by never running."
    )


reap = _load_reap()


def test_a_consistent_estate_reports_no_difference_in_either_direction() -> None:
    """The case the old join could never produce.

    Every layer that published something has a tagged resource and vice versa, so both
    differences are empty. Under the service-versus-layer join this was impossible: the sets were
    `{'iam', 'kms'}` and `{'bootstrap', 'foundation'}`, and every run reported both as wholly
    mismatched.
    """
    tagged = [
        ("arn:aws:kms:eu-west-1:1:key/a", {"holdout:layer": "bootstrap"}),
        ("arn:aws:s3:::holdout-gold-abc", {"holdout:layer": "foundation"}),
    ]
    published = ["/holdout/bootstrap/state_bucket", "/holdout/foundation/workspace_url"]

    report = reap.Report()
    reap.compare_enumerations(tagged, published, report)

    assert report.published_not_tagged == []
    assert report.tagged_not_published == []


def test_a_layer_that_published_and_carries_no_tagged_resource_is_named() -> None:
    """The orphan case, which is the reason the second enumeration is inverted at all.

    `pipelines` published a name and nothing in the account carries its tag: either the resource
    was deleted outside Terraform, or it never existed. Either way the reaper can report it and
    can never collect it, which is exactly what this direction is for.
    """
    tagged = [("arn:aws:s3:::holdout-gold-abc", {"holdout:layer": "foundation"})]
    published = ["/holdout/foundation/workspace_url", "/holdout/pipelines/job_id"]

    report = reap.Report()
    reap.compare_enumerations(tagged, published, report)

    assert report.published_not_tagged == ["pipelines"]
    assert report.tagged_not_published == []


def test_a_resource_no_layer_published_is_named_in_the_other_direction() -> None:
    tagged = [
        ("arn:aws:s3:::holdout-gold-abc", {"holdout:layer": "foundation"}),
        ("arn:aws:lambda:eu-west-1:1:function:x", {"holdout:layer": "serving"}),
    ]
    published = ["/holdout/foundation/workspace_url"]

    report = reap.Report()
    reap.compare_enumerations(tagged, published, report)

    assert report.tagged_not_published == ["serving"]


def test_a_resource_with_the_project_tag_and_no_layer_tag_is_itself_the_finding() -> None:
    """It cannot be joined, so it is reported rather than dropped.

    Dropping it would be the coverage lie one layer down: a resource this project owns, absent
    from both differences, invisible in a report whose whole subject is what is missing.
    """
    tagged = [("arn:aws:s3:::holdout-mystery", {"holdout:project": "holdout"})]

    report = reap.Report()
    reap.compare_enumerations(tagged, ["/holdout/foundation/workspace_url"], report)

    assert report.untagged_layer == ["arn:aws:s3:::holdout-mystery"]


@pytest.mark.parametrize(
    ("arn", "survivor"),
    [
        ("arn:aws:s3:::holdout-tfstate-abc123", True),
        ("arn:aws:s3:::holdout-tfstate-logs-abc123", True),
        ("arn:aws:ssm:eu-west-1:1:parameter/holdout/bootstrap/region", True),
        ("arn:aws:s3:::holdout-gold-abc123", False),
        ("arn:aws:lambda:eu-west-1:1:function:holdout-reaper", False),
    ],
)
def test_the_survivor_list_labels_what_must_outlive_a_teardown(arn: str, survivor: bool) -> None:
    """`CLAUDE.md`'s survivor list, and it labels a report rather than guarding a deletion.

    Nothing in the reaper deletes an AWS resource, so this is not standing between anything and
    anything today. It is asserted because the day an AWS deletion path is added, this is what
    that path must consult — and a list nobody checked until then is a list that would be wrong.
    """
    assert reap._is_survivor(arn) is survivor


def test_a_dry_run_and_an_unrecognised_type_are_different_fields() -> None:
    """Two meanings that shared one field, which is `TASKS.md`'s rule about arity.

    `would_delete` is *I know what this is and I am not touching it*; `unknown` is *I do not know
    what this is*. They were one list, so a dry run's intentions were reported as things the
    reaper did not recognise.
    """
    report = reap.Report()
    assert report.would_delete == []
    assert report.unknown == []
    assert report.skipped == []
    assert "would_delete" in report.as_dict()
    assert "skipped" in report.as_dict()
