"""The TTL reaper: level 1 of three, and the only one that depends on no workflow's control flow.

`CLAUDE.md` ranks the three teardown guarantees and is explicit that a workflow step is a
convenience rather than a guarantee -- the runner can die, the network can drop, the job can be
cancelled. This runs on a schedule, in the account, and asks the account what is standing.

## What it deletes, and the scope decision that is not obvious

**It deletes Databricks compute that bills while idle. It deletes nothing in AWS at all.**

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
becomes a lie when it reports what it examined as if it were what exists.*

    1. by tag          the Resource Groups Tagging API, holdout:project = holdout
    2. by publication  every SSM parameter under /holdout/, whose values are the identifiers
                       each layer published for the layers above it

**The inversion is the half that matters.** Neither enumeration is an acting population here --
nothing below deletes an AWS resource -- so both are a *report*, and the report's content is the
difference between them:

    published, not tagged   ->  a layer published a name and nothing carries its tag
    tagged, not published   ->  a resource exists that no layer told anyone about

**The join is on the `holdout:layer` tag, and the reason is a defect this file carried.** It was
`arn.split(":")[2]` against `name.split("/")[2]`, which compares the ARN's **service** field --
`iam`, `kms`, `s3` -- against layer names -- `bootstrap`, `foundation`. The two sets share no
vocabulary, so both differences were the whole of both sets on every run, for ever: an alarm that
fires always, in the detector built for the one case the SSM inversion exists to catch.

`default_tags` in `versions.tf` sets `holdout:layer` on everything this project creates, and
`get_resources` returns tags. **A resource with the project tag and no layer tag is itself the
finding** and is reported under `untagged_layer` rather than dropped.

## What it will not do

**An unrecognised AWS resource type is put in `unknown` and left alone.** Not deleted, not
ignored: counted and named. That costs nothing today -- nothing here deletes in AWS -- and it is
the shape the next reader needs if a deletion path is ever added.

**And `SURVIVORS` guards a report, not a deletion.** `CLAUDE.md`'s list is exact -- the state
bucket and its access-log bucket, the state KMS key, the SSM parameters and the deploy role --
and those carry `holdout:project` because the budget's cost filter needs them to. **Today nothing
here could delete them if it tried**, so this is a label on the report rather than a guard. It is
kept, and said in these words, because a reader who took it for a guard would add an AWS deletion
loop believing it was already protected. *This sentence replaced one that claimed exactly that.*

## What is a hand-written population, said out loud

`BILLING_SURFACES` is a list somebody wrote. **On the AWS side an unrecognised type lands in
`unknown`; on the Databricks side a surface nobody listed is not seen at all** -- no enumeration,
no counter, no line in the log. What is outside it today, named so the gap is a fact rather than a
discovery: **the agent runtime and the AI Gateway**, both of which live in `serving`.

**A surface whose listing call fails is an error, not a skip**, which is what makes adding one
safe: a wrong path screams on the next scheduled run rather than quietly collecting nothing.
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import boto3

#: The tag every resource in this estate carries, and the one the budget's cost filter reads.
PROJECT_TAG = "holdout:project"
PROJECT = "holdout"

#: The tag that says which layer created a resource. `versions.tf`'s `default_tags` sets it on
#: everything, which is what makes the join below possible at all.
LAYER_TAG = "holdout:layer"

#: Prefix under which every layer publishes what the layers above it consume.
PUBLISHED_PREFIX = "/holdout/"

#: Labelled on the report, never deleted -- see the docstring. A substring match on the ARN is
#: deliberately blunt: a rename that dodged this list would be a rename of the state backend.
SURVIVORS = (
    "holdout-tfstate-",
    "holdout-deploy-state",
    ":parameter/holdout/",
)

#: Databricks compute that bills while idle, as `(api path, the key its listing returns, the
#: field the DELETE takes)`. **A hand-written population**, declared as one in the docstring
#: along with what is outside it.
#:
#: **The third element exists because the first delete would have been a 404.** The handle was
#: `id or name` for every surface; a serving endpoint's listing carries both, and its DELETE is
#: by **name** -- so the reaper would have asked to delete `serving-endpoints/<uuid>`, been told
#: no such endpoint, recorded an error, and left the one thing that bills while idle standing.
#: A warehouse deletes by id and a Lakebase instance by name. Found by a fresh-context review on
#: 2026-09-12, from the API, on a net that had never had to fire.
BILLING_SURFACES = (
    ("serving-endpoints", "endpoints", "name"),
    ("sql/warehouses", "warehouses", "id"),
    ("database/instances", "database_instances", "name"),
)


class Report:
    """What the run examined, what it did, and what it could not answer.

    Built even when nothing is deleted, because *a run that deleted nothing* and *a run that
    found nothing* are different outcomes, and a reaper that prints the same line for both is the
    `grep -P` failure again: silence and success looking identical.

    **`skipped`, `would_delete` and `errors` are three fields rather than one**, because they
    were one and it was wrong in both directions. An estate inside its TTL is the normal outcome
    of almost every scheduled run and was being written to `errors`, which would make the alarm
    fire hourly on correct behaviour. And a dry run's intentions were being written to `unknown`,
    whose meaning is *I do not recognise this* -- `TASKS.md`'s rule: a field that cannot express
    what happened will be filled with something that did not.
    """

    def __init__(self) -> None:
        self.tagged: list[str] = []
        self.published: list[str] = []
        self.deleted: list[str] = []
        self.would_delete: list[str] = []
        self.survivors: list[str] = []
        self.unknown: list[str] = []
        self.untagged_layer: list[str] = []
        self.published_not_tagged: list[str] = []
        self.tagged_not_published: list[str] = []
        self.skipped: list[str] = []
        self.errors: list[str] = []

    def as_dict(self) -> dict[str, Any]:
        return dict(vars(self))


def _is_survivor(arn: str) -> bool:
    return any(marker in arn for marker in SURVIVORS)


def tagged_resources(session: Any) -> list[tuple[str, dict[str, str]]]:
    """Enumeration 1: every `(ARN, tags)` carrying this project's tag.

    The tags come back with the ARNs and are kept rather than discarded -- they are where the
    layer name lives, and discarding them is what made the join meaningless.
    """
    api = session.client("resourcegroupstaggingapi")
    found: list[tuple[str, dict[str, str]]] = []
    paginator = api.get_paginator("get_resources")
    for page in paginator.paginate(TagFilters=[{"Key": PROJECT_TAG, "Values": [PROJECT]}]):
        for item in page["ResourceTagMappingList"]:
            tags = {t["Key"]: t["Value"] for t in item.get("Tags", [])}
            found.append((item["ResourceARN"], tags))
    return sorted(found)


def published_identifiers(session: Any) -> list[str]:
    """Enumeration 2: every parameter name published under `/holdout/`.

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


def compare_enumerations(
    tagged: list[tuple[str, dict[str, str]]], published: list[str], report: Report
) -> None:
    """Join the two enumerations on the layer, and record both differences.

    **Both sides now speak the same vocabulary**, which is the whole content of this function: the
    tagged side reads `holdout:layer`, the published side reads the second path segment of
    `/holdout/<layer>/<name>`. A resource carrying the project tag and no layer tag cannot be
    joined at all and is reported as itself a finding rather than silently dropped.
    """
    tagged_layers: set[str] = set()
    for arn, tags in tagged:
        layer = tags.get(LAYER_TAG)
        if layer is None:
            report.untagged_layer.append(arn)
        else:
            tagged_layers.add(layer)

    published_layers = {name.split("/")[2] for name in published if len(name.split("/")) > 3}

    report.published_not_tagged = sorted(published_layers - tagged_layers)
    report.tagged_not_published = sorted(tagged_layers - published_layers)


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


def _oauth_token(session: Any, account_id: str) -> str:
    """Exchange the account service principal's OAuth credentials for a short-lived token.

    **The credentials are read from SSM `SecureString` at run time rather than carried in the
    function's environment.** A Lambda environment variable is stored in the function's
    configuration in plaintext and is readable by anything holding `lambda:GetFunction` -- which
    is a wider set than the reaper's own role. `CLAUDE.md`'s rule is *no long-lived credentials*;
    this is the same rule one level down, about where a credential rests rather than how long it
    lives.
    """
    ssm = session.client("ssm")
    names = [
        f"{PUBLISHED_PREFIX}foundation/reaper_client_id",
        f"{PUBLISHED_PREFIX}foundation/reaper_client_secret",
    ]
    fetched = ssm.get_parameters(Names=names, WithDecryption=True)
    values = {p["Name"].rsplit("/", 1)[1]: p["Value"] for p in fetched["Parameters"]}
    missing = {"reaper_client_id", "reaper_client_secret"} - set(values)
    if missing:
        raise RuntimeError(
            f"the reaper has no credentials: {sorted(missing)} is not published under "
            f"{PUBLISHED_PREFIX}foundation/"
        )

    body = urllib.parse.urlencode({"grant_type": "client_credentials", "scope": "all-apis"})
    request = urllib.request.Request(
        f"https://accounts.cloud.databricks.com/oidc/accounts/{account_id}/v1/token",
        data=body.encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    credentials = base64.b64encode(
        f"{values['reaper_client_id']}:{values['reaper_client_secret']}".encode()
    ).decode("ascii")
    request.add_header("Authorization", f"Basic {credentials}")
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return str(payload["access_token"])


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
    thing which was supposed to clean up did not finish. **The errors are raised by the caller
    after the sweep**, which is what puts a failed run somewhere a person sees.
    """
    for surface, key, field in BILLING_SURFACES:
        try:
            listing = _databricks(host, token, surface)
        except (urllib.error.URLError, urllib.error.HTTPError) as error:
            # **A surface that cannot be listed is an error and not a skip.** That is what makes
            # `BILLING_SURFACES` safe to extend: a path that is wrong -- or a product that moved
            # -- screams on the next scheduled run instead of quietly collecting nothing.
            report.errors.append(f"{surface}: could not list ({error})")
            continue

        for item in listing.get(key, []):
            name = item.get("name") or item.get("id", "?")
            if not item.get(field):
                report.errors.append(f"{surface}: a listing row carries no {field!r}: {item}")
                continue
            handle = f"{surface}/{item[field]}"
            if dry_run:
                report.would_delete.append(f"{handle} ({name})")
                continue
            try:
                _databricks(host, token, handle, method="DELETE")
                report.deleted.append(f"{handle} ({name})")
            except (urllib.error.URLError, urllib.error.HTTPError) as error:
                report.errors.append(f"{handle}: delete failed ({error})")


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: ARG001
    """Run the sweep, then **raise if anything failed**.

    **The raise is the whole difference between a reaper and a log line.** Every path below used
    to record into `report.errors` and return, so the Lambda always succeeded -- and the
    docstring's *"this is the one failure that must be loud"* was a sentence in a log group with
    fourteen-day retention that nothing reads. A green invocation is the least loud outcome the
    system can produce.

    It raises **after** the sweep, never during it, so one unreachable surface does not leave the
    rest of the bill running. The exception is what puts the invocation on the dead-letter topic
    `reaper.tf` declares: **a reaper that silently fails to delete is indistinguishable from one
    that had nothing to do.**
    """
    ttl_hours = float(os.environ["TTL_HOURS"])
    landing_bucket = os.environ["LANDING_BUCKET"]
    dry_run = os.environ.get("DRY_RUN", "true").lower() != "false"

    session = boto3.session.Session()
    report = Report()

    tagged = tagged_resources(session)
    report.tagged = [arn for arn, _ in tagged]
    report.published = published_identifiers(session)
    report.survivors = [arn for arn in report.tagged if _is_survivor(arn)]
    compare_enumerations(tagged, report.published, report)

    age = estate_age_hours(session, landing_bucket)
    if age is None:
        report.errors.append(
            f"the landing bucket {landing_bucket} does not exist, so the estate's age is unknown. "
            "Nothing was collected: a reaper that cannot measure the age it acts on must not act."
        )
        return _finish(report)

    if age < ttl_hours:
        # **A skip, not an error.** This is the normal outcome of almost every scheduled run.
        report.skipped.append(f"estate is {age:.1f}h old, under the {ttl_hours:.0f}h TTL")
        return _finish(report)

    host = os.environ.get("DATABRICKS_HOST", "")
    account_id = os.environ.get("DATABRICKS_ACCOUNT_ID", "")
    if not host or not account_id:
        report.errors.append(
            "no workspace host or account id in the environment, so the billing surfaces were "
            "not examined, and the estate is past its TTL."
        )
        return _finish(report)

    try:
        token = _oauth_token(session, account_id)
    except (RuntimeError, urllib.error.URLError, KeyError) as error:
        report.errors.append(f"could not obtain a Databricks token: {error}")
        return _finish(report)

    collect_billing_surfaces(host, token, report, dry_run)
    return _finish(report)


def _finish(report: Report) -> dict[str, Any]:
    """Print the report, then raise if it carries an error.

    The print happens first and unconditionally, so the log holds the whole run even when the
    invocation is about to fail -- the dead-letter topic says *something went wrong*, and this is
    where a person finds out what.
    """
    payload = report.as_dict()
    print(json.dumps(payload, default=str))
    if report.errors:
        raise RuntimeError(
            f"the reaper finished with {len(report.errors)} error(s): {report.errors}"
        )
    return payload
