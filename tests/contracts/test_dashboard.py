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

import dataclasses
import json
from typing import Any

import pytest

from holdout.contracts.compilers import compile_all
from holdout.contracts.compilers.dashboard import (
    MONITOR_PATH,
    READOUT_COLUMNS,
    READOUT_METRIC,
    READOUT_PATH,
    DashboardError,
    compile_decision_monitor,
    compile_readout_dashboard,
)
from holdout.contracts.compilers.readout import compile_readout
from holdout.contracts.loader import load
from holdout.core.experiment.readout import Readout

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


def test_the_readout_columns_are_the_core_types_own_fields() -> None:
    """The one place this compiler names a table that does not exist, bound to a declaration.

    `gold.readout` is phase 3's, so the dashboard names columns for a table nobody has built.
    **They are not invented**: they are the fields of `holdout.core.experiment.readout.Readout`,
    the type the core already returns and the one phase 3 will materialise.

    **Compared in both directions**, because either half alone is satisfiable by an accident: a
    subset check passes a compiler that dropped a field, and a superset check passes one that
    invented one. This is the arrangement `tests/core/test_refusal_codes.py` uses for the refusal
    enums — three mechanisms, no imports between them, and a test that they agree.

    `holdout/contracts/` does not import `holdout/core/` and this test is why it does not need
    to: the coupling lives here, where a test may import both, rather than in the contract layer.
    """
    declared = tuple(field.name for field in dataclasses.fields(Readout))
    assert declared == READOUT_COLUMNS, (
        "the dashboard's column list and the Readout type have diverged. Whichever moved, the "
        "dashboard is now naming a column nobody declares or missing one that exists."
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
