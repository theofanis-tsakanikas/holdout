"""The nine-field form, and the closed lists it must not restate.

Two properties matter here and they pull in opposite directions. The form must be a real
schema — strict enough that a design missing its decision rule cannot be submitted. And it
must not contain a second copy of the metric contract, because the copy is the one that
goes stale: a metric added to `contracts/metrics/` that the form still refuses, or a metric
retired that the form still offers.

So the source form declares `x-closed-list` and writes no enum, and the compiler resolves
it. What is tested here is that the source really is empty of enums and the compiled
artefact really is full of them.
"""

from __future__ import annotations

import json
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from holdout.contracts.compilers import compile_design_form
from holdout.contracts.loader import CONTRACTS_DIR
from holdout.contracts.model import ContractSet

FORM_YAML = yaml.safe_load((CONTRACTS_DIR / "design" / "form.schema.yaml").read_text("utf-8"))

NINE = [
    "hypothesis",
    "intervention",
    "scope",
    "primary_metric",
    "unit",
    "mde",
    "max_duration",
    "exclusions",
    "decision_rule",
]


def compiled(contracts: ContractSet) -> dict[str, Any]:
    schema: dict[str, Any] = json.loads(compile_design_form(contracts))
    return schema


def valid_form() -> dict[str, Any]:
    return {
        "hypothesis": (
            "A steeper markdown ladder on expiring fresh raises category margin per "
            "store-week without raising waste."
        ),
        "intervention": {"treatment": "ladder_policy@v1", "control": "ladder_policy@v1"},
        "scope": {"categories": ["dairy", "bakery"], "products": None, "stores": "all"},
        "primary_metric": "category_margin_per_store_week",
        "unit": "store",
        "mde": {"kind": "relative_pct", "value": 2.0, "direction": "either"},
        "max_duration": {"weeks": 6},
        "exclusions": [
            {"store_id": "S-0412", "reason": "refit closes the fresh counter for four weeks"}
        ],
        "decision_rule": {
            "if_significant": "roll the treatment ladder to every store in the two categories",
            "if_not_significant": "keep the current ladder and close the question for a year",
            "if_refused": "fix the named defect and rerun; state no number in the meantime",
        },
        "filled_by": "human:T. Tsakanikas",
    }


def test_the_form_declares_exactly_nine_design_fields() -> None:
    assert FORM_YAML["x-design-fields"] == NINE


def test_filled_by_is_attribution_and_is_counted_separately() -> None:
    assert "filled_by" not in FORM_YAML["x-design-fields"]
    assert set(FORM_YAML["properties"]) == set(NINE) | {"filled_by"}
    assert set(FORM_YAML["required"]) == set(NINE) | {"filled_by"}


def test_the_source_form_holds_no_hardcoded_metric_or_policy_enum() -> None:
    """The enum belongs to the contract. A copy here is the copy that goes stale."""
    assert "x-closed-list" in json.dumps(FORM_YAML)
    assert FORM_YAML["properties"]["primary_metric"]["x-closed-list"] == "metric_ids"
    assert "enum" not in FORM_YAML["properties"]["primary_metric"]
    intervention = FORM_YAML["properties"]["intervention"]["properties"]
    for arm in ("treatment", "control"):
        assert intervention[arm]["x-closed-list"] == "policy_refs"
        assert "enum" not in intervention[arm]


def test_the_compiled_form_resolves_the_closed_lists_from_the_contracts(
    contracts: ContractSet,
) -> None:
    properties = compiled(contracts)["properties"]
    assert properties["primary_metric"]["enum"] == list(contracts.metric_ids)
    assert properties["intervention"]["properties"]["treatment"]["enum"] == list(
        contracts.policy_refs
    )
    assert "x-closed-list" not in json.dumps(compiled(contracts))


def test_the_agent_never_fills_the_business_constraint_or_the_decision_rule() -> None:
    """The agent proposes how we will find out. Never what we will do once we know."""
    assert FORM_YAML["properties"]["max_duration"]["x-never-filled-by"] == ["agent"]
    assert FORM_YAML["properties"]["decision_rule"]["x-never-filled-by"] == ["agent"]
    for field in set(NINE) - {"max_duration", "decision_rule"}:
        assert "x-never-filled-by" not in FORM_YAML["properties"][field]


def test_a_complete_design_validates(contracts: ContractSet) -> None:
    errors = list(Draft202012Validator(compiled(contracts)).iter_errors(valid_form()))
    assert errors == []


def test_a_metric_outside_the_contract_is_rejected_by_the_closed_list(
    contracts: ContractSet,
) -> None:
    """The schema-level half of METRIC_NOT_IN_CONTRACT. A metric defined inside a design is
    a metric nobody else computes the same way."""
    form = valid_form()
    form["primary_metric"] = "margin_but_the_way_i_like_it"
    assert list(Draft202012Validator(compiled(contracts)).iter_errors(form))


def test_a_control_arm_naming_a_policy_that_does_not_exist_is_rejected(
    contracts: ContractSet,
) -> None:
    form = valid_form()
    form["intervention"] = {"treatment": "ladder_policy@v1", "control": "ladder_policy@v9"}
    assert list(Draft202012Validator(compiled(contracts)).iter_errors(form))


def test_a_design_with_no_decision_rule_is_rejected(contracts: ContractSet) -> None:
    """Declared afterwards, the decision rule is whatever the result made convenient."""
    form = valid_form()
    del form["decision_rule"]
    assert list(Draft202012Validator(compiled(contracts)).iter_errors(form))


def test_a_decision_rule_with_no_plan_for_a_refusal_is_rejected(
    contracts: ContractSet,
) -> None:
    form = valid_form()
    del form["decision_rule"]["if_refused"]
    assert list(Draft202012Validator(compiled(contracts)).iter_errors(form))


def test_filled_by_accepts_all_three_sources_and_nothing_else(
    contracts: ContractSet,
) -> None:
    validator = Draft202012Validator(compiled(contracts))
    for source in ("agent", "human:T. Tsakanikas", "policy:quarterly_fresh_review"):
        form = valid_form()
        form["filled_by"] = source
        assert list(validator.iter_errors(form)) == [], source
    for bad in ("", "robot", "human:", "policy:Not An Id"):
        form = valid_form()
        form["filled_by"] = bad
        assert list(validator.iter_errors(form)), bad
