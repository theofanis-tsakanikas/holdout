"""The figures `run` publishes, each asserted by the command that produces it.

`PLAN.md` closes phase 3 on *a `run` whose every figure is asserted by a step that fails when it
is not true — including at least one experiment that produces a number and at least one that
**refuses** for the right reason — with the account confirming afterwards that nothing is left
standing.*

**So the assertions live here rather than in the workflow's shell.** `docs/FINDINGS.md`'s `[M]`
rule is that a number is not published without the command that produces it, and a query written
inline in YAML is a number whose command lives somewhere nobody greps.

## The two halves, and the second is the one that matters

**A run in which everything succeeded is not a passing run.** A system that never refuses has not
demonstrated the thing this project is about — `CLAUDE.md`'s thesis is *an uplift number produced
without a valid holdout is a build failure*, and the refusal is the half that proves the sentence
has teeth. `--require-refusal` fails when every experiment produced a number.

**And a refusal has to be for a declared reason.** `contracts/vocabularies/reason_codes.yaml` is a
closed list; a refusal carrying a code outside it is not a refusal the system understands, and
this checks membership rather than mere presence.

## What has not run

**Nothing here has executed against a live estate.** It is written, it type-checks, its SQL is
readable, and the first `run` dispatch is what will say whether the column names match. That is
stated because this repository's own rule is that *a line can be true of the code and false of the
system*, and this module is currently only the first.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

#: Where the readout lands. `infra/lakehouse` creates the catalog and the schema; `pipelines`'
#: gold job writes the table.
READOUT = "{catalog}.gold.readout"


def _host() -> str:
    host = os.environ.get("DATABRICKS_HOST", "").rstrip("/")
    if not host:
        raise SystemExit("DATABRICKS_HOST is not set. This runs inside `run`, which sets it.")
    return host


def _token() -> str:
    """An OAuth token from the account service principal's client credentials."""
    import base64

    cid = os.environ["DATABRICKS_CLIENT_ID"]
    secret = os.environ["DATABRICKS_CLIENT_SECRET"]
    body = urllib.parse.urlencode({"grant_type": "client_credentials", "scope": "all-apis"})
    request = urllib.request.Request(
        f"{_host()}/oidc/v1/token",
        data=body.encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": "Basic "
            + base64.b64encode(f"{cid}:{secret}".encode()).decode("ascii"),
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return str(json.loads(response.read())["access_token"])


def _api(path: str, payload: dict[str, Any] | None = None, method: str = "GET") -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"{_host()}/api/{path}",
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        raw = response.read().decode("utf-8")
    return dict(json.loads(raw)) if raw else {}


def _sql(statement: str, warehouse_id: str) -> list[list[Any]]:
    """Run one statement and return its rows.

    `wait_timeout` is the API's own limit and is set to its maximum: a readout query over this
    corpus is seconds, and a client-side timeout on top would be a second number that can
    disagree with the first.
    """
    result = _api(
        "2.0/sql/statements",
        {"statement": statement, "warehouse_id": warehouse_id, "wait_timeout": "50s"},
        method="POST",
    )
    state = result.get("status", {}).get("state")
    if state != "SUCCEEDED":
        raise SystemExit(f"the query did not succeed ({state}): {json.dumps(result)[:400]}")
    return list(result.get("result", {}).get("data_array") or [])


def check_experiments(catalog: str, warehouse_id: str) -> int:
    """At least one experiment produced a number, and at least one refused."""
    table = READOUT.format(catalog=catalog)
    rows = _sql(
        f"SELECT experiment_id, uplift, reason_code FROM {table}",
        warehouse_id,
    )
    if not rows:
        print(f"FAIL  {table} is empty. `run` drove a day and no experiment reached a readout.")
        return 1

    numbers = [r for r in rows if r[1] is not None]
    refusals = [r for r in rows if r[2] is not None]

    print(f"  readouts       {len(rows)}")
    print(f"  with a number  {len(numbers)}   {[r[0] for r in numbers]}")
    print(f"  refused        {len(refusals)}  {[(r[0], r[2]) for r in refusals]}")

    failed = 0
    if not numbers:
        print("FAIL  no experiment produced a number. A system that only ever refuses passes")
        print("      every world and is worthless — CLAUDE.md's W6 is the reason W1 is not enough.")
        failed = 1
    if not refusals:
        print("FAIL  no experiment refused. A run in which everything succeeded has not")
        print("      demonstrated the thing this project is about: an uplift number produced")
        print("      without a valid holdout is a build failure, and the refusal is where that")
        print("      sentence has teeth.")
        failed = 1

    # **A refusal has to name a code the contract declares.** A free-text reason cannot be
    # counted, tested or gated, which is why the vocabulary is closed at all.
    declared = _declared_reason_codes()
    for experiment, _, code in refusals:
        if code not in declared:
            print(f"FAIL  {experiment} refused with `{code}`, which is not in the closed")
            print("      vocabulary. Adding a code is a code change with a test.")
            failed = 1

    return failed


def _declared_reason_codes() -> set[str]:
    """Every code `contracts/vocabularies/reason_codes.yaml` declares, read from the contract."""
    from pathlib import Path

    import yaml

    path = Path(__file__).resolve().parents[1] / "contracts" / "vocabularies" / "reason_codes.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    codes: set[str] = set()
    for section in document.values():
        if isinstance(section, list | dict):
            codes.update(str(c) for c in section)
    return codes


def check_endpoint(endpoint: str, expect_version: str) -> int:
    """The endpoint answers, and the version answering is the one that was deployed."""
    served = _api(f"2.0/serving-endpoints/{endpoint}")
    entities = served.get("config", {}).get("served_entities") or []
    versions = [str(e.get("entity_version")) for e in entities]

    print(f"  endpoint       {endpoint}")
    print(f"  serving        {versions}")

    if expect_version not in versions:
        print(f"FAIL  expected version {expect_version} and the endpoint serves {versions}.")
        print("      What answered a question is part of the answer: an endpoint that had")
        print("      silently rolled to another version would make every number in this run")
        print("      belong to a model nobody named.")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default=os.environ.get("HOLDOUT_CATALOG", "holdout"))
    parser.add_argument("--warehouse-id", default=os.environ.get("HOLDOUT_WAREHOUSE_ID", ""))
    parser.add_argument("--require-number", action="store_true")
    parser.add_argument("--require-refusal", action="store_true")
    parser.add_argument("--endpoint")
    parser.add_argument("--expect-version")
    args = parser.parse_args(argv)

    failed = 0
    try:
        if args.require_number or args.require_refusal:
            if not args.warehouse_id:
                raise SystemExit("--warehouse-id is required to query the readout.")
            failed |= check_experiments(args.catalog, args.warehouse_id)
        if args.endpoint:
            if not args.expect_version:
                raise SystemExit("--expect-version is required with --endpoint.")
            failed |= check_endpoint(args.endpoint, args.expect_version)
    except (urllib.error.URLError, KeyError) as error:
        print(f"FAIL  the estate could not be asked: {error}")
        return 1

    print("OK      every figure this step publishes was asserted" if not failed else "")
    return failed


if __name__ == "__main__":
    sys.exit(main())
