"""`inspect` — ask the standing estate what every screen a demo would open is going to show.

`run` asserts the figures it publishes: the readout's two rows, the endpoint's version. It does
not open a dashboard, count a table, or try the door. Those are what a person at the console
would do before a recording, and on 2026-09-12 the person at the console was the author, with
the estate billing while he looked. **This is that look, as a command**, so the answer is a
transcript rather than a memory of one — the `[M]` rule one layer up.

What it asks, and what it does not
----------------------------------
* every table in bronze, silver and gold, with its row count — an estate that built a schema
  and left a table empty is one whose demo opens on nothing;
* `gold.readout`, in full, so the two refusals are read beside every column the dashboard
  will ask for;
* `gold.experiment_assignment` — its `delta.appendOnly` property, its rows, and **the door
  tried**: a `DELETE` that matches no row. Refused by name is the answer this repository
  claims; accepted over zero rows is *inconclusive*, because a delete that removes nothing
  writes no remove action and there was nothing for the storage to refuse. Never tried with a
  predicate that could match: the one probe that would settle it is the one that would open
  the door if the claim were false;
* **every dataset of every dashboard, executed the way the dashboard executes it** — fetched
  from the workspace, not read off `generated/`, so what is checked is what was applied. A
  dataset whose SQL names a parameter the dashboard does not declare cannot run, and is
  reported as *cannot draw* without being sent, because the warehouse's answer to an unbound
  marker is the same sentence in a different font;
* the serving endpoint's state and served versions;
* Unity Catalog lineage for the catalog, where the system table is readable, and *unreadable*
  where it is not — an instrument that cannot answer says so rather than reporting zero.

It writes nothing anywhere except the failed probe above. It exits 1 when any screen would
not draw, so a red run is the finding and a green one is the demo.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
from pathlib import Path
from typing import Any

from ops.run_assertions import _api, _declared_reason_codes

#: What `pipelines/silver` and `pipelines/gold` write, by name, so an absent one is a failure
#: and not a shorter list. Bronze is one table per source and is counted, not named.
EXPECTED = {
    "silver": (
        "sales",
        "shelf_state",
        "price_displayed",
        "reference",
        "stores",
        "decisions",
        "quarantine",
    ),
    "gold": (
        "decision_economics",
        "waste",
        "experiment_assignment",
        "readout",
        "policies",
        "decisions",
    ),
}
DASHBOARD_PREFIX = "Holdout — "
PARAMETER = re.compile(r"(?<![:\w]):([A-Za-z_]\w*)")


class Statement:
    """One statement's outcome: rows, or the warehouse's own words for why not."""

    def __init__(self, state: str, rows: list[list[Any]], error: str, columns: list[str]) -> None:
        self.state, self.rows, self.error, self.columns = state, rows, error, columns

    @property
    def ok(self) -> bool:
        return self.state == "SUCCEEDED"


def sql(
    statement: str,
    warehouse_id: str,
    *,
    catalog: str | None = None,
    parameters: list[dict[str, Any]] | None = None,
) -> Statement:
    payload: dict[str, Any] = {
        "statement": statement,
        "warehouse_id": warehouse_id,
        "wait_timeout": "50s",
    }
    if catalog:
        payload["catalog"] = catalog
    if parameters:
        payload["parameters"] = parameters
    try:
        result = _api("2.0/sql/statements", payload, method="POST")
    except urllib.error.HTTPError as bad:
        body = bad.read().decode("utf-8", "replace")[:600]
        return Statement("HTTP_ERROR", [], f"{bad.code}: {body}", [])
    statement_id = result.get("statement_id", "")
    # The API's own timeout is 50s; a slower statement is polled rather than abandoned.
    for _ in range(24):
        state = result.get("status", {}).get("state")
        if state not in ("PENDING", "RUNNING"):
            break
        time.sleep(5)
        result = _api(f"2.0/sql/statements/{statement_id}")
    state = str(result.get("status", {}).get("state"))
    error = result.get("status", {}).get("error", {}).get("message", "")
    columns = [c["name"] for c in result.get("manifest", {}).get("schema", {}).get("columns", [])]
    return Statement(state, list(result.get("result", {}).get("data_array") or []), error, columns)


def _one(statement: str, warehouse_id: str, catalog: str) -> Any:
    got = sql(statement, warehouse_id, catalog=catalog)
    if not got.ok:
        raise RuntimeError(got.error or got.state)
    return got.rows[0][0] if got.rows else None


# ------------------------------------------------------------------ the tables
def check_tables(catalog: str, warehouse_id: str, bronze_volume: str) -> int:
    failed = 0
    print("── tables, with their rows")
    # **Bronze is files in a volume, not tables in a schema** -- measured on run 34676694580,
    # where `SHOW TABLES IN holdout.bronze` returned nothing over an estate whose silver held
    # six million sales. `pipelines/ingest` lands one directory per source under the bronze
    # volume and `pipelines/silver` reads them by path; the schema exists for the volume.
    listed = sql(f"LIST '{bronze_volume}'", warehouse_id)
    if not listed.ok:
        print(f"FAIL  LIST {bronze_volume}: {listed.error or listed.state}")
        failed = 1
    else:
        sources = sorted(r[1].rstrip("/").rsplit("/", 1)[-1] for r in listed.rows)
        print(f"  bronze volume {bronze_volume}: {len(sources)} source(s) {sources}")
        if not sources:
            print("FAIL  the bronze volume is empty; nothing was ingested")
            failed = 1
    for schema, expected in (
        ("silver", EXPECTED["silver"]),
        ("gold", EXPECTED["gold"]),
    ):
        listed = sql(f"SHOW TABLES IN {catalog}.{schema}", warehouse_id)
        if not listed.ok:
            print(f"FAIL  SHOW TABLES IN {catalog}.{schema}: {listed.error or listed.state}")
            failed = 1
            continue
        names = sorted(r[1] for r in listed.rows)
        for name in names:
            try:
                n = _one(f"SELECT count(*) FROM {catalog}.{schema}.{name}", warehouse_id, catalog)
                print(
                    f"  {schema}.{name:<32} {int(n):>12,}" + ("   <- EMPTY" if int(n) == 0 else "")
                )
            except RuntimeError as bad:
                print(f"  {schema}.{name:<32} unreadable: {str(bad)[:120]}")
                failed = 1
        for name in expected:
            if name not in names:
                print(f"FAIL  {catalog}.{schema}.{name} is not there, and the pipelines write it")
                failed = 1
    return failed


# ------------------------------------------------------------------ the readout
def check_readout(catalog: str, warehouse_id: str) -> int:
    print("── gold.readout, every column")
    got = sql(f"SELECT * FROM {catalog}.gold.readout ORDER BY experiment_id", warehouse_id)
    if not got.ok:
        print(f"FAIL  {got.error or got.state}")
        return 1
    print(f"  columns  {got.columns}")
    for row in got.rows:
        print("  " + json.dumps(dict(zip(got.columns, row, strict=True)), default=str))
    if not got.rows:
        print("FAIL  the readout is empty")
        return 1
    declared = _declared_reason_codes()
    failed = 0
    by = {c: i for i, c in enumerate(got.columns)}
    for row in got.rows:
        uplift, code = row[by["uplift"]], row[by["reason_code"]]
        if (uplift is None) == (code is None):
            print(
                f"FAIL  {row[by['experiment_id']]}: exactly one of uplift and reason_code must be set"
            )
            failed = 1
        if code is not None and code not in declared:
            print(f"FAIL  {row[by['experiment_id']]}: `{code}` is not a declared reason code")
            failed = 1
    return failed


# ------------------------------------------------------------------ the door
def check_assignment(catalog: str, warehouse_id: str) -> int:
    print("── gold.experiment_assignment, and the door tried")
    table = f"{catalog}.gold.experiment_assignment"
    props = sql(f"SHOW TBLPROPERTIES {table}", warehouse_id)
    if not props.ok:
        print(f"FAIL  {props.error or props.state}")
        return 1
    properties = {r[0]: r[1] for r in props.rows}
    append_only = properties.get("delta.appendOnly")
    print(f"  delta.appendOnly = {append_only}")
    failed = 0
    if str(append_only).lower() != "true":
        print("FAIL  the assignment table is not append-only, so the storage refuses nothing")
        failed = 1
    try:
        n = _one(f"SELECT count(*) FROM {table}", warehouse_id, catalog)
        arms = sql(
            f"SELECT experiment_id, arm, count(*) FROM {table} GROUP BY 1, 2 ORDER BY 1, 2",
            warehouse_id,
        )
        print(f"  rows {int(n):,}  " + str([tuple(r) for r in arms.rows]))
    except RuntimeError as bad:
        print(f"FAIL  {bad}")
        failed = 1
    probe = sql(
        f"DELETE FROM {table} WHERE experiment_id = 'no-such-experiment-{int(time.time())}'",
        warehouse_id,
    )
    if probe.ok:
        print("  probe    DELETE matching no row was ACCEPTED — inconclusive: no remove action was")
        print(
            "           written, so the storage had nothing to refuse. Not tried with a live predicate."
        )
    elif "APPEND_ONLY" in (probe.error or "").upper() or "append" in (probe.error or "").lower():
        print(f"  probe    DELETE refused by the storage: {probe.error[:140]}")
    else:
        print(f"  probe    DELETE failed for another reason: {(probe.error or probe.state)[:200]}")
    return failed


# ------------------------------------------------------------------ the dashboards
def _dashboards() -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    token = ""
    while True:
        page = _api("2.0/lakeview/dashboards" + (f"?page_token={token}" if token else ""))
        found.extend(
            d
            for d in page.get("dashboards", [])
            if d.get("display_name", "").startswith(DASHBOARD_PREFIX)
        )
        token = page.get("next_page_token", "")
        if not token:
            return found


def check_dashboards(warehouse_id: str) -> int:
    print("── dashboards, every dataset executed as the dashboard would")
    boards = _dashboards()
    if not boards:
        print("FAIL  no dashboard named `Holdout — …` is in the workspace")
        return 1
    failed = 0
    for board in boards:
        full = _api(f"2.0/lakeview/dashboards/{board['dashboard_id']}")
        serialized = json.loads(full.get("serialized_dashboard") or "{}")
        widgets = sum(len(p.get("layout", [])) for p in serialized.get("pages", []))
        print(
            f"  {board['display_name']}  ({widgets} widget(s), lifecycle {full.get('lifecycle_state')})"
        )
        for dataset in serialized.get("datasets", []):
            text = "\n".join(dataset.get("queryLines", []))
            declared = {p.get("keyword") for p in dataset.get("parameters", [])}
            markers = set(PARAMETER.findall(text))
            unbound = sorted(markers - declared)
            if unbound:
                print(
                    f"    {dataset['name']:<20} CANNOT DRAW: names parameters the dashboard does not declare {unbound}"
                )
                failed = 1
                continue
            parameters = [
                {
                    "name": p["keyword"],
                    "value": str(
                        (p.get("defaultSelection") or {})
                        .get("values", {})
                        .get("values", [{}])[0]
                        .get("value", "")
                    ),
                }
                for p in dataset.get("parameters", [])
            ]
            got = sql(text, warehouse_id, parameters=parameters or None)
            if got.ok:
                print(
                    f"    {dataset['name']:<20} draws: {len(got.rows)} row(s)"
                    + ("   <- EMPTY" if not got.rows else "")
                )
            else:
                print(f"    {dataset['name']:<20} CANNOT DRAW: {(got.error or got.state)[:900]}")
                failed = 1
    return failed


# ------------------------------------------------------------------ the demo's own queries
DEMO_QUERIES = Path(__file__).with_name("demo_queries.sql")


def demo_blocks(text: str) -> list[tuple[str, str, bool]]:
    """`(name, sql, expect_refused)` per `-- @name` block, comments stripped from the SQL."""
    blocks: list[tuple[str, str, bool]] = []
    name, refused = "", False
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("-- @name"):
            if name:
                blocks.append((name, "\n".join(lines).strip().rstrip(";"), refused))
            name, refused, lines = stripped.split(None, 2)[2], False, []
        elif stripped.startswith("-- @expect refused"):
            refused = True
        elif name and not stripped.startswith("--"):
            lines.append(line)
    if name:
        blocks.append((name, "\n".join(lines).strip().rstrip(";"), refused))
    return blocks


def check_demo_queries(warehouse_id: str) -> int:
    """Every query the recording will type, run now, so the recording shows a measurement."""
    print(f"── the demo's queries, from {DEMO_QUERIES.name}")
    failed = 0
    for name, statement, expect_refused in demo_blocks(DEMO_QUERIES.read_text(encoding="utf-8")):
        got = sql(statement, warehouse_id)
        if expect_refused:
            if got.ok:
                print(f"  {name:<48} ACCEPTED, and the estate had to refuse it")
                failed = 1
            else:
                print(f"  {name:<48} refused: {(got.error or got.state)[:90]}")
        elif got.ok:
            first = json.dumps(got.rows[0], default=str)[:110] if got.rows else "-"
            print(f"  {name:<48} {len(got.rows):>6} row(s)  {first}")
        else:
            print(f"  {name:<48} FAILED: {(got.error or got.state)[:300]}")
            failed = 1
    return failed


# ------------------------------------------------------------------ the rest
def check_endpoint(endpoint: str) -> int:
    print("── the endpoint")
    try:
        served = _api(f"2.0/serving-endpoints/{endpoint}")
    except urllib.error.HTTPError as bad:
        print(f"FAIL  {endpoint}: {bad.code}")
        return 1
    state = served.get("state", {})
    entities = served.get("config", {}).get("served_entities", [])
    print(
        f"  {endpoint}  ready={state.get('ready')}  config={state.get('config_update')}  "
        f"versions={[str(e.get('entity_version')) for e in entities]}"
    )
    return 0 if state.get("ready") == "READY" else 1


def check_lineage(catalog: str, warehouse_id: str) -> int:
    print("── lineage, from the system table")
    got = sql(
        "SELECT count(*), count(distinct target_table_full_name) FROM system.access.table_lineage "
        f"WHERE target_table_catalog = '{catalog}' OR source_table_catalog = '{catalog}'",
        warehouse_id,
    )
    if got.ok:
        print(f"  edges {got.rows[0][0]}  target tables {got.rows[0][1]}")
    else:
        print(f"  unreadable from this principal: {(got.error or got.state)[:160]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--warehouse-id", required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--bronze-volume", required=True)
    args = parser.parse_args(argv)

    failed = 0
    failed |= check_tables(args.catalog, args.warehouse_id, args.bronze_volume)
    failed |= check_readout(args.catalog, args.warehouse_id)
    failed |= check_assignment(args.catalog, args.warehouse_id)
    failed |= check_dashboards(args.warehouse_id)
    failed |= check_demo_queries(args.warehouse_id)
    failed |= check_endpoint(args.endpoint)
    failed |= check_lineage(args.catalog, args.warehouse_id)
    print()
    if failed:
        print(
            "RED     a screen a demo would open does not draw, or a table it would show is not there"
        )
    else:
        print(
            "OK      every table, both readouts, the door, every dashboard dataset and the endpoint answer"
        )
    return failed


if __name__ == "__main__":
    sys.exit(main())
