"""`inspect` reads the binding from widget to query to column — the half a dataset run cannot see.

On 2026-09-15 every dataset of both dashboards executed, `inspect` called the screens green, and
the published dashboard showed *Missing query "main_query"* in every widget with data. The check
that would have caught it is `check_widgets`, and this is the plant that proves it bites: the
artefact the estate had, reconstructed by undoing the repair on the compiled one.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from ops.inspect_estate import COLUMN_REF, MAIN_QUERY, check_widgets

READOUT = Path("generated/dashboards/experiment_readout.lvdash.json")


def _columns_from(serialized: dict[str, Any]) -> dict[str, list[str]]:
    """What a dataset run would have returned: every column a field's expression names."""
    columns: dict[str, set[str]] = {}
    for page in serialized["pages"]:
        for item in page["layout"]:
            widget = item["widget"]
            for query in widget.get("queries", []):
                body = query["query"]
                for field in body["fields"]:
                    columns.setdefault(body["datasetName"], set()).update(
                        c for c in COLUMN_REF.findall(field["expression"]) if c != "*"
                    )
    return {name: sorted(cols) for name, cols in columns.items()}


def test_the_compiled_readout_binds_every_widget() -> None:
    serialized = json.loads(READOUT.read_text(encoding="utf-8"))
    assert check_widgets(serialized, _columns_from(serialized)) == []


def test_the_artefact_the_estate_had_is_refused_by_name() -> None:
    """Undo the repair — `main`, no fields, a table at version 3 — and every data widget is named."""
    serialized = json.loads(READOUT.read_text(encoding="utf-8"))
    columns = _columns_from(serialized)
    broken = copy.deepcopy(serialized)
    data_widgets = 0
    for page in broken["pages"]:
        for item in page["layout"]:
            widget = item["widget"]
            if "queries" not in widget:
                continue
            data_widgets += 1
            widget["queries"][0]["name"] = "main"
    faults = check_widgets(broken, columns)
    assert len(faults) == data_widgets, faults
    assert all(MAIN_QUERY in fault for fault in faults), faults


def test_a_field_over_a_column_the_dataset_did_not_return_is_refused() -> None:
    serialized = json.loads(READOUT.read_text(encoding="utf-8"))
    columns = _columns_from(serialized)
    columns["verdict"] = [c for c in columns["verdict"] if c != "p_value"]
    faults = check_widgets(serialized, columns)
    assert faults and all("p_value" in f for f in faults), faults


def test_a_table_at_a_charts_version_is_refused() -> None:
    serialized = json.loads(READOUT.read_text(encoding="utf-8"))
    broken = copy.deepcopy(serialized)
    for page in broken["pages"]:
        for item in page["layout"]:
            spec = item["widget"].get("spec", {})
            if spec.get("widgetType") == "table":
                spec["version"] = 3
    faults = check_widgets(broken, _columns_from(serialized))
    assert faults and all("spec version 3" in f for f in faults), faults
