"""The reaper asks to delete each surface by the field its DELETE takes.

A serving endpoint's listing carries an `id` (a UUID) and a `name`, and `DELETE
/api/2.0/serving-endpoints/{name}` is by name; a SQL warehouse deletes by `id`; a Lakebase
instance by `name`. The reaper's handle was `id or name` for every surface, so the one surface
that bills while idle would have been asked for by a UUID and answered *not found* -- a net that
records an error and leaves the endpoint standing. Found by a fresh-context review on
2026-09-12, from the API, on a net that had never had to fire.

**The attack is a workspace that answers listings the way the real one does** -- both fields on
every row -- and records the paths the reaper asks it to delete.
"""

from __future__ import annotations

from typing import Any

from tests.infra.test_reaper_join import _load_reap


def _fake_workspace(calls: list[tuple[str, str]]) -> Any:
    listings = {
        "serving-endpoints": {"endpoints": [{"id": "0b1e-uuid", "name": "holdout-demand"}]},
        "sql/warehouses": {"warehouses": [{"id": "ee47", "name": "holdout — estate"}]},
        "database/instances": {"database_instances": [{"uid": "u-1", "name": "holdout-lakebase"}]},
    }

    def databricks(host: str, token: str, path: str, method: str = "GET") -> dict[str, Any]:
        calls.append((method, path))
        if method == "GET":
            return listings[path]
        return {}

    return databricks


def test_each_surface_is_deleted_by_the_field_its_api_takes() -> None:
    reap = _load_reap()
    calls: list[tuple[str, str]] = []
    reap._databricks = _fake_workspace(calls)
    report = reap.Report()
    reap.collect_billing_surfaces("https://example.invalid", "token", report, dry_run=False)

    deleted = {path for method, path in calls if method == "DELETE"}
    assert deleted == {
        "serving-endpoints/holdout-demand",
        "sql/warehouses/ee47",
        "database/instances/holdout-lakebase",
    }, deleted
    assert report.errors == [], report.errors
    assert len(report.deleted) == 3


def test_a_listing_row_without_the_field_is_an_error_not_a_skip() -> None:
    reap = _load_reap()
    calls: list[tuple[str, str]] = []

    def databricks(host: str, token: str, path: str, method: str = "GET") -> dict[str, Any]:
        calls.append((method, path))
        return {"endpoints": [{"id": "only-an-id"}], "warehouses": [], "database_instances": []}

    reap._databricks = databricks
    report = reap.Report()
    reap.collect_billing_surfaces("https://example.invalid", "token", report, dry_run=False)
    assert not any(method == "DELETE" for method, _ in calls)
    assert report.errors and "no 'name'" in report.errors[0], report.errors
