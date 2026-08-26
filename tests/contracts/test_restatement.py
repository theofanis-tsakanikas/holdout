"""Contract rule 4 — a change that affects past values implies a restatement.

The rule was in CLAUDE.md and `restatement` was in the schema, and nothing joined the two:
a metric could change its arithmetic between versions and say nothing about the numbers
already published under the old one. That is doctrine rule 4's exact failure — a correction
that erases what was previously stated — and it is computable at build time, so it is a
gate rather than a convention.

Deliberately narrow. The check does not ask whether a restatement is *true*. It asks whether
one was written when the definition moved. Nobody can compute honesty; anybody can compute
whether two expressions differ.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from holdout.contracts.errors import ContractError
from holdout.contracts.loader import load
from holdout.contracts.model import ContractSet

MARGIN = "category_margin_per_store_week"


def metric_path(root: Path, version: int) -> Path:
    return root / "metrics" / f"{MARGIN}.v{version}.yaml"


def test_a_version_that_changed_the_arithmetic_carries_a_restatement(
    contracts: ContractSet,
) -> None:
    v2 = contracts.metric_versions(MARGIN)[1]
    assert v2.restatement is not None
    assert v2.restatement.from_version == 1
    assert v2.restatement.affects_past_values is True


def test_a_version_that_changed_only_the_rounding_still_carries_one(
    contracts: ContractSet,
) -> None:
    """The change that reads as cosmetic and is not. v3 is v2's arithmetic exactly; it
    rounds half_even instead of half_up, and every value already stated under v2 that sat on
    a boundary now has a different correct value by one cent — which is a failed claim 5, so
    it is a restatement."""
    v2, v3 = contracts.metric_versions(MARGIN)[1], contracts.metric_versions(MARGIN)[2]
    assert " ".join(v2.expression.split()) == " ".join(v3.expression.split())
    assert v2.rounding != v3.rounding
    assert v3.restatement is not None and v3.restatement.from_version == 2


def test_the_first_version_of_a_metric_restates_nothing(contracts: ContractSet) -> None:
    for metric_id in contracts.metric_ids:
        first = contracts.metric_versions(metric_id)[0]
        if first.supersedes is None:
            assert first.restatement is None, first.ref


def test_a_changed_expression_with_no_restatement_is_a_build_failure(
    contracts_copy: Path, edit_contract: Callable[[Path, Callable[[Any], Any]], None]
) -> None:
    def drop_restatement(document: Any) -> Any:
        del document["restatement"]
        return document

    edit_contract(metric_path(contracts_copy, 2), drop_restatement)
    with pytest.raises(ContractError) as raised:
        load(contracts_copy)
    violations = [v for v in raised.value.violations if v.rule == "restatement_missing"]
    assert violations
    assert "the expression" in violations[0].detail


def test_a_changed_rounding_with_no_restatement_is_a_build_failure(
    contracts_copy: Path, edit_contract: Callable[[Path, Callable[[Any], Any]], None]
) -> None:
    """The one a reviewer would wave through: same formula, different mode, one cent."""

    def drop_restatement(document: Any) -> Any:
        del document["restatement"]
        return document

    edit_contract(metric_path(contracts_copy, 3), drop_restatement)
    with pytest.raises(ContractError) as raised:
        load(contracts_copy)
    violations = [v for v in raised.value.violations if v.rule == "restatement_missing"]
    assert violations
    assert "the rounding" in violations[0].detail


def test_a_restatement_naming_the_wrong_predecessor_is_a_build_failure(
    contracts_copy: Path, edit_contract: Callable[[Path, Callable[[Any], Any]], None]
) -> None:
    def misname(document: Any) -> Any:
        document["restatement"]["from_version"] = 1
        return document

    edit_contract(metric_path(contracts_copy, 3), misname)
    with pytest.raises(ContractError) as raised:
        load(contracts_copy)
    assert any(v.rule == "restatement_mismatched" for v in raised.value.violations)


def test_a_restatement_on_a_version_that_supersedes_nothing_is_a_build_failure(
    contracts_copy: Path, edit_contract: Callable[[Path, Callable[[Any], Any]], None]
) -> None:
    def add_restatement(document: Any) -> Any:
        document["restatement"] = {
            "from_version": 1,
            "reason": "a restatement of numbers that were never stated",
            "affects_past_values": True,
        }
        return document

    edit_contract(contracts_copy / "metrics" / "units_sold_per_store_week.v1.yaml", add_restatement)
    with pytest.raises(ContractError) as raised:
        load(contracts_copy)
    assert any(v.rule == "restatement_without_predecessor" for v in raised.value.violations)


def test_an_unchanged_definition_needs_no_restatement(contracts_copy: Path) -> None:
    """The gate must not fire on a version bump that changed nothing that matters, or it
    would teach people to write a restatement for every edit and mean none of them."""
    import yaml

    v3 = metric_path(contracts_copy, 3)
    document = yaml.safe_load(v3.read_text(encoding="utf-8"))
    v3.write_text(
        yaml.safe_dump({**document, "effective_to": "2026-09-01"}, sort_keys=False), "utf-8"
    )
    successor = {
        **document,
        "version": 4,
        "supersedes": 3,
        "effective_from": "2026-09-01",
        "effective_to": None,
    }
    successor.pop("restatement", None)
    metric_path(contracts_copy, 4).write_text(
        yaml.safe_dump(successor, sort_keys=False), encoding="utf-8"
    )

    loaded = load(contracts_copy)
    v4 = loaded.metric_versions(MARGIN)[3]
    assert v4.version == 4
    assert v4.restatement is None


def test_every_metric_says_whose_definition_it_is(contracts: ContractSet) -> None:
    """The metric family was the only one with nowhere to say 'this is the scenario
    speaking', and v1 and v2 are a fixture rather than a history."""
    for metric in contracts.metrics:
        assert metric.provenance.kind == "scenario_assumption", metric.ref
        assert metric.provenance.note
