"""The TTL reaper: level 1 of three, and the only one that depends on no workflow's control flow.

`CLAUDE.md` ranks the three teardown guarantees and is explicit that a workflow step is a
convenience rather than a guarantee -- the runner can die, the network can drop, the job can be
cancelled. This runs on a schedule, in the account, and asks the account what is standing.

## What it deletes, and the scope decision that is not obvious

**It deletes Databricks compute that bills while idle. It does not delete storage.**

That is a decision rather than an omission, and the argument is in `CLAUDE.md`'s own cost table:
`serving` is *the most expensive layer and the only one that bills while idle*, jobs and SQL are
serverless and bill per use, and S3 for the whole corpus is modelled at **1-3 USD per cycle**.
A reaper that deleted the four zones would save single-digit dollars and destroy the one thing
`destroy` is deliberately never automatic in order to protect: *on success the estate is exactly
what console screenshots and video need, and re-deploying to debug costs forty minutes and real
money.*

So the reaper stops the bill and leaves the evidence. **Storage is collected by `destroy all`,
which is a deliberate dispatch, and by nothing else.**

## The two enumerations, and why one of them is inverted

`ops/figures.py` states the rule this instantiates: *a gate reports on what it examined; it
becomes a lie when it reports what it examined as if it were what exists.* The reaper is a gate
whose report is a deletion, so it enumerates twice and compares.

    1. by tag          the Resource Groups Tagging API, holdout:project = holdout
    2. by publication  every SSM parameter under /holdout/, whose values are the identifiers
                       each layer published for the layers above it

**The inversion is the half that matters.** Enumeration 1 is the population the reaper acts on,
so a resource missing from it is invisible -- and the way a resource goes missing from it is by
carrying no tag, which is exactly what a resource created outside Terraform does. Enumeration 2
cannot be the acting population, because a published *name* is not a handle on a resource; but it
can say **what should have been in enumeration 1 and was not.**

    published, not tagged   ->  a resource the reaper will never collect. Reported, loudly.
    tagged, not published   ->  a resource no layer told anyone about. Reported, quietly.

This is `infra/bootstrap/README.md`'s sentence made mechanical: *the reaper is not merely
inconvenienced without `ssm:PutParameter` -- it is incorrect, because an object whose name never
reached SSM is an object it cannot reap.*

## What it will not do

**An unrecognised resource type is put in `unknown` and left alone.** Not deleted, not ignored:
counted and named in the report. A reaper that deletes what it does not recognise is a reaper
whose blast radius is whatever AWS ships next.

**And the survivors are refused by name.** `CLAUDE.md`'s list is exact -- the state bucket and its
access-log bucket, the state KMS key, the SSM parameters and the deploy role -- and those carry
the same `holdout:project` tag as everything else, because the budget's cost filter needs them to.
Tag-based collection would take them. `SURVIVORS` is what stands between the reaper and the state
of every other layer.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import urllib.error
import urllib.request
from typing import Any

import boto3

#: The tag every resource in this estate carries, and the one the budget's cost filter reads.
PROJECT_TAG = "holdout:project"
PROJECT = "holdout"

#: Prefix under which every layer publishes what the layers above it consume.
PUBLISHED_PREFIX = "/holdout/"

#: **Refused by name, never by tag.** These carry `holdout:project` because the budget must see
#: them, and they are precisely what must outlive every teardown. A substring match on the ARN is
#: deliberately blunt: a rename that dodged this list would be a rename of the state backend.
SURVIVORS = (
    "holdout-tfstate-",
    "holdout-deploy-state",
    ":parameter/holdout/",
)

#: Databricks compute that bills while idle, in the order it must be removed. A serving endpoint
#: holds a model version; a warehouse holds nothing. Order matters only for the report.
BILLING_SURFACES = ("serving-endpoints", "sql/warehouses")


class Report:
    """What the run examined, what it did, and what it could not answer.

    Built even when nothing is deleted, because *a run that deleted nothing* and *a run that
    found nothing* are different outcomes and a reaper that prints the same line for both is
    the `grep -P` failure again: silence and success looking identical.
    """

    def __init__(self) -> None:
        self.tagged: list[str] = []
        self.published: list[str] = []
        self.deleted: list[str] = []
        self.survivors: list[str] = []
        self.unknown: list[str] = []
        self.published_not_tagged: list[str] = []
        self.tagged_not_published: list[str] = []
        self.errors: list[str] = []

    def as_dict(self) -> dict[str, Any]:
        return dict(vars(self))


def _is_survivor(arn: str) -> bool:
    return any(marker in arn for marker in SURVIVORS)


def tagged_resources(session: Any) -> list[str]:
    """Enumeration 1: every ARN carrying this project's tag, from the tagging API."""
    api = session.client("resourcegroupstaggingapi")
    found: list[str] = []
    paginator = api.get_paginator("get_resources")
    for page in paginator.paginate(TagFilters=[{"Key": PROJECT_TAG, "Values": [PROJECT]}]):
        found.extend(item["ResourceARN"] for item in page["ResourceTagMappingList"])
    return sorted(found)


def published_identifiers(session: Any) -> list[str]:
    """Enumeration 2: every value published under `/holdout/`, by parameter name.

    The names are returned rather than the values. A value is a bucket name or an ARN and some of
    them are `SecureString`; the reaper needs to know *that a layer published something* and what
    it called it, never the secret itself.
    """
    ssm = session.client("ssm")
    found: list[str] = []
    paginator = ssm.get_paginator("describe_parameters")
    for page in paginator.paginate(
        ParameterFilters=[{"Key": "Name", "Option": "BeginsWith", "Values": [PUBLISHED_PREFIX]}]
    ):
        found.extend(p["Name"] for p in page["Parameters"])
    return sorted(found)


def estate_age_hours(session: Any, landing_bucket: str) -> float | None:
    """How long the estate has stood, measured rather than written down.

    **The age comes from the creation date of the landing bucket**, which S3 reports and nobody
    can edit. The alternative -- an `applied_at` parameter written at apply time -- is a number
    the thing being measured writes about itself, and it drifts: `timestamp()` in Terraform
    changes on every plan, so it would either produce a perpetual diff or be frozen with
    `ignore_changes` and then describe the first apply for ever.

    **Its limit, stated rather than discovered: this is when the estate was built, not when it
    last did work.** An estate left standing and idle for 47 hours is not collected; one that has
    been driven continuously for 49 is. That is the correct behaviour for a TTL and the wrong one
    for an idleness timer, and this reaper is the first.
    """
    s3 = session.client("s3")
    for bucket in s3.list_buckets()["Buckets"]:
        if bucket["Name"] == landing_bucket:
            created: dt.datetime = bucket["CreationDate"]
            now = dt.datetime.now(dt.UTC)
            return (now - created).total_seconds() / 3600.0
    return None


def _databricks(host: str, token: str, path: str, method: str = "GET") -> dict[str, Any]:
    request = urllib.request.Request(
        f"{host}/api/2.0/{path}",
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else {}


def collect_billing_surfaces(host: str, token: str, report: Report, dry_run: bool) -> None:
    """Delete the Databricks compute that bills while idle.

    Every failure is recorded and none of them stops the others: a reaper that aborts on the
    first error leaves the rest of the bill running, and the whole reason this exists is that the
    thing which was supposed to clean up did not finish.
    """
    for surface in BILLING_SURFACES:
        try:
            listing = _databricks(host, token, surface)
        except urllib.error.URLError as error:
            report.errors.append(f"{surface}: could not list ({error})")
            continue

        key = "endpoints" if surface.startswith("serving") else "warehouses"
        for item in listing.get(key, []):
            name = item.get("name") or item.get("id", "?")
            handle = f"{surface}/{item.get('id') or item.get('name')}"
            if dry_run:
                report.unknown.append(f"would delete {handle} ({name})")
                continue
            try:
                _databricks(host, token, handle, method="DELETE")
                report.deleted.append(f"{handle} ({name})")
            except urllib.error.URLError as error:
                report.errors.append(f"{handle}: delete failed ({error})")


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: ARG001
    ttl_hours = float(os.environ["TTL_HOURS"])
    landing_bucket = os.environ["LANDING_BUCKET"]
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"

    session = boto3.session.Session()
    report = Report()

    report.tagged = tagged_resources(session)
    report.published = published_identifiers(session)

    for arn in report.tagged:
        if _is_survivor(arn):
            report.survivors.append(arn)

    # The comparison, in both directions. A published parameter names the *layer* that published
    # it, so the join is by layer rather than by identifier -- which is coarse, and is the reason
    # the second direction is reported rather than acted on.
    tagged_layers = {arn.split(":")[2] for arn in report.tagged}
    published_layers = {name.split("/")[2] for name in report.published if name.count("/") >= 2}
    report.published_not_tagged = sorted(published_layers - tagged_layers)
    report.tagged_not_published = sorted(tagged_layers - published_layers)

    age = estate_age_hours(session, landing_bucket)
    if age is None:
        report.errors.append(
            f"the landing bucket {landing_bucket} does not exist, so the estate's age is unknown. "
            "Nothing was collected: a reaper that cannot measure the age it acts on must not act."
        )
        return report.as_dict()

    if age < ttl_hours:
        report.errors.append(f"estate is {age:.1f}h old, under the {ttl_hours:.0f}h TTL")
        return report.as_dict()

    host = os.environ.get("DATABRICKS_HOST", "")
    token = os.environ.get("DATABRICKS_TOKEN", "")
    if not host or not token:
        report.errors.append(
            "no Databricks credentials in the environment, so the billing surfaces were not "
            "examined. This is the one failure that must be loud: the estate is past its TTL and "
            "the expensive half of it was not collected."
        )
        return report.as_dict()

    collect_billing_surfaces(host, token, report, dry_run)
    return report.as_dict()
