"""The dashboards are compiled from contracts, and every number on them has an origin.

`terraform validate` cannot check any of this — measured, in `infra/lakehouse/README.md`: a
`databricks_dashboard` whose `serialized_dashboard` contains `select nonsense from
table_that_does_not_exist where 1=` validates clean, because the field is a string. So these are
the checks that make *both dashboards consume the metric contract* structural rather than
asserted, and `make contracts`' byte comparison is what makes them binding.

**The load-bearing one is `test_the_readout_dataset_is_the_compiled_readout_itself`.** The others
would all pass over a dashboard that had copied the query once and drifted since.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pytest

from holdout.contracts.compilers import compile_all
from holdout.contracts.compilers.dashboard import (
    MAIN_QUERY,
    MONITOR_PATH,
    READOUT_COLUMNS,
    READOUT_METRIC,
    READOUT_PATH,
    SPEC_VERSION,
    DashboardError,
    compile_decision_monitor,
    compile_readout_dashboard,
)
from holdout.contracts.compilers.readout import compile_readout
from holdout.contracts.loader import load

CONTRACTS = load()


@pytest.fixture(scope="module")
def readout_dashboard() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(compile_readout_dashboard(CONTRACTS))
    return loaded


@pytest.fixture(scope="module")
def monitor() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(compile_decision_monitor(CONTRACTS))
    return loaded


def _dataset(document: dict[str, Any], name: str) -> dict[str, Any]:
    for dataset in document["datasets"]:
        if dataset["name"] == name:
            return dict(dataset)
    raise AssertionError(f"no dataset named {name!r}")


def test_the_readout_dataset_is_the_compiled_readout_itself(
    readout_dashboard: dict[str, Any],
) -> None:
    """Not a copy of the query — the same call, so the screen cannot drift from the contract.

    A dashboard holding its own SQL would be a second definition of the metric in the one artefact
    nobody re-derives. Comparing the joined lines against `compile_readout` is what makes that
    impossible rather than merely discouraged.
    """
    metric = next(m for m in CONTRACTS.metrics if m.id == READOUT_METRIC and m.effective_to is None)
    lines = _dataset(readout_dashboard, "arm_metric")["queryLines"]
    assert "".join(lines) == compile_readout(metric)


def test_the_readout_columns_are_the_columns_the_pipeline_writes() -> None:
    """The screen reads the table that exists, compared with the code that writes it.

    **This test compared the compiler with the wrong thing for eight days.** Until 2026-09-12
    it asserted `READOUT_COLUMNS` equalled the fields of `holdout.core.experiment.readout.Readout`
    -- the type -- and it was green while `T022` wrote `gold.readout` in a different shape: the
    interval flattened to `ci_low`/`ci_high`, the period to two dates, `alpha` and `statistic` and
    `balance` not carried, `reason_code` added because a refusal is a row and the type has no
    field for one. The dashboard's `verdict` dataset selected `confidence_interval` and `alpha`
    from a table with neither. Two projections of one thing, each compared with the compiler and
    never with each other; the table is what the screen reads, so the table is what this compares.

    **Compared in both directions**, for the reason the first version gave: a subset check passes
    a compiler that dropped a column, a superset check passes one that invented one.

    `holdout/contracts/` does not import `pipelines/` and this test is why it does not need to:
    the coupling lives here, where a test may import both.
    """
    from pipelines.gold.experiments import SCHEMA

    written = tuple(column.strip().split(" ")[0] for column in SCHEMA.split(","))
    assert written == READOUT_COLUMNS, (
        "the dashboard's column list and the pipeline's readout schema have diverged. Whichever "
        "moved, the screen is now naming a column the table does not have or missing one it has."
    )


def test_the_verdict_dataset_selects_every_column_and_one_verdict(
    readout_dashboard: dict[str, Any],
) -> None:
    """One column carries both cases, and nothing the table has is left off the screen."""
    text = "".join(_dataset(readout_dashboard, "verdict")["queryLines"])
    for column in READOUT_COLUMNS:
        assert f"  {column}" in text, f"the verdict dataset does not select {column}"
    assert "coalesce(cast(uplift as string), reason_code) as verdict" in text
    assert ":" not in text.replace("::", ""), "the verdict dataset takes no parameter"
    placed = next(
        widget
        for widget in readout_dashboard["pages"][0]["layout"]
        if widget["widget"]["name"] == "verdicts"
    )
    shown = [c["fieldName"] for c in placed["widget"]["spec"]["encodings"]["columns"]]
    assert "verdict" in shown and placed["position"]["width"] == 12


def test_every_parameter_the_readout_carries_is_declared(
    readout_dashboard: dict[str, Any],
) -> None:
    """A dataset naming a parameter its dashboard does not declare cannot draw.

    Measured by `ops/inspect_estate.py` on 2026-09-12: the compiled readout carries six markers
    and the dataset declared none, so the two data widgets on the project's central screen could
    not have run on any day since the dashboard was applied.
    """
    import re

    for dataset in readout_dashboard["datasets"]:
        text = "".join(dataset["queryLines"])
        markers = set(re.findall(r"(?<![:\w]):([A-Za-z_]\w*)", text))
        declared = {p["keyword"] for p in dataset.get("parameters", [])}
        assert markers <= declared, (
            f"{dataset['name']} names undeclared parameters {markers - declared}"
        )
        for parameter in dataset.get("parameters", []):
            default = parameter["defaultSelection"]["values"]["values"][0]["value"]
            assert default != "", (
                f"{parameter['keyword']} has no default and the screen cannot open"
            )


def test_every_check_tile_comes_from_the_closed_vocabulary(
    readout_dashboard: dict[str, Any],
) -> None:
    """Four tiles, four `at_readout` codes, and the mapping is the contract's own `check` field.

    A hand-written list of four names would look identical on the screen and would not move when
    a fifth check was added — which is exactly the failure a closed vocabulary exists to prevent.
    """
    codes = [code for code in CONTRACTS.reason_codes.at_readout if code.check]
    widgets = readout_dashboard["pages"][0]["layout"]
    tiles = {
        widget["widget"]["name"]: widget["widget"]["textbox_spec"]
        for widget in widgets
        if widget["widget"]["name"].startswith("check_")
    }
    assert len(tiles) == len(codes) == 4
    for code in codes:
        assert f"check_{code.check}" in tiles
        assert code.code in tiles[f"check_{code.check}"], (
            f"the {code.check} tile does not name {code.code}, so a refusal would appear on a "
            "screen that never says which rule produced it"
        )


def test_the_monitor_names_every_decision_time_code(monitor: dict[str, Any]) -> None:
    """All twelve, not the handful somebody remembered.

    Doctrine rule 2 is what this screen exists for, and a guardrail breakdown missing a code is a
    fallback that is invisible for exactly the reason nobody would notice.
    """
    text = "".join(
        widget["widget"].get("textbox_spec", "") for widget in monitor["pages"][0]["layout"]
    )
    missing = [code.code for code in CONTRACTS.reason_codes.at_decision if code.code not in text]
    assert not missing, f"the monitor does not name {missing}"
    assert len(CONTRACTS.reason_codes.at_decision) == 12


def test_the_readout_screen_shows_a_refusal_at_the_same_size_as_a_number(
    readout_dashboard: dict[str, Any],
) -> None:
    """`closes`: *the refused version of this screen is the single most important screenshot.*

    So the hero widget must say so in its own text. Asserted on the artefact rather than left to
    a reader's eye, because a screen whose failure case is smaller than its success case teaches
    everyone to read only the successes — and nothing else in this repository would catch that.
    """
    hero = next(
        widget["widget"]
        for widget in readout_dashboard["pages"][0]["layout"]
        if widget["widget"]["name"] == "hero"
    )
    assert "same size" in hero["textbox_spec"]
    assert "refusal" in hero["textbox_spec"].lower()


def test_both_dashboards_are_compiled_artefacts_that_make_contracts_compares() -> None:
    """Otherwise every check above is about a string nobody ships.

    `compile_all` is what `make contracts` recompiles and byte-compares, so a dashboard reachable
    only through its own function would be checked here and unchecked on disk.
    """
    artefacts = compile_all(CONTRACTS)
    assert READOUT_PATH in artefacts
    assert MONITOR_PATH in artefacts


def test_a_screen_compiled_from_a_retired_metric_is_refused() -> None:
    """A live artefact showing a retired definition, refused by name rather than by luck.

    Planted by asking for a metric that is not in force. `in_force_metrics` already keeps
    superseded versions out of every other consumer; this asserts the dashboard is in that set
    rather than reaching around it.
    """
    from holdout.contracts.compilers import dashboard as module

    original = module.READOUT_METRIC
    module.READOUT_METRIC = "a_metric_no_contract_declares"
    try:
        with pytest.raises(DashboardError, match="not an in-force metric"):
            module.compile_readout_dashboard(CONTRACTS)
    finally:
        module.READOUT_METRIC = original


# ── the widget grammar ────────────────────────────────────────────────────────────────────
#
# **The datasets ran and the screens did not draw.** `inspect` executes every dataset the way
# the dashboard executes it and reported both screens green on 2026-09-15; opened at the
# console, every widget with data read *Missing query "main_query"* or *Invalid widget
# definition is imported*. A widget spec binds to a query by the one name Lakeview gives it,
# and the first compiler named it `main`, declared no fields, and put a table at a chart's
# spec version. None of that is visible to a dataset run, so this is the check that reads the
# binding — the half of "the screens draw" that no query can answer.


def _data_widgets(document: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        w["widget"]
        for page in document["pages"]
        for w in page["layout"]
        if "queries" in w["widget"]
    ]


@pytest.mark.parametrize("compile", [compile_readout_dashboard, compile_decision_monitor])
def test_every_data_widget_binds_to_main_query_with_its_fields_declared(
    compile: Callable[[Any], str],
) -> None:
    document = json.loads(compile(CONTRACTS))
    datasets = {d["name"] for d in document["datasets"]}
    widgets = _data_widgets(document)
    assert widgets, "a screen with no data widget draws nothing"
    for widget in widgets:
        (query,) = widget["queries"]
        assert query["name"] == MAIN_QUERY, (
            f"{widget['name']}: the spec reads `main_query`, not {query['name']!r}"
        )
        body = query["query"]
        assert body["datasetName"] in datasets, (
            f"{widget['name']}: dataset {body['datasetName']!r} is not declared"
        )
        assert body["fields"], f"{widget['name']}: a query with no fields draws no columns"
        assert isinstance(body["disaggregated"], bool)
        names = {f["name"] for f in body["fields"]}
        spec = widget["spec"]
        assert spec["version"] == SPEC_VERSION[spec["widgetType"]], (
            f"{widget['name']}: spec version"
        )
        used = _field_names(spec["encodings"])
        assert used <= names, (
            f"{widget['name']}: encodings name fields the query does not carry: {used - names}"
        )


def _field_names(encodings: dict[str, Any]) -> set[str]:
    found: set[str] = set()
    for value in encodings.values():
        if isinstance(value, dict) and "fieldName" in value:
            found.add(value["fieldName"])
        elif isinstance(value, list):
            found |= {v["fieldName"] for v in value if isinstance(v, dict) and "fieldName" in v}
    return found


def test_a_table_widget_declares_every_column_it_shows_as_a_field(
    readout_dashboard: dict[str, Any],
) -> None:
    """A table's columns are the query's fields, one to one — a column with no field is empty."""
    tables = [w for w in _data_widgets(readout_dashboard) if w["spec"]["widgetType"] == "table"]
    assert tables
    for table in tables:
        columns = [c["fieldName"] for c in table["spec"]["encodings"]["columns"]]
        fields = [f["name"] for f in table["queries"][0]["query"]["fields"]]
        assert columns == fields, table["name"]
        assert table["queries"][0]["query"]["disaggregated"] is True, table["name"]
