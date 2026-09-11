"""The two fields the agent never fills have nowhere to go, and the delivery tool is the form.

`CLAUDE.md`: *the agent proposes how we will find out. Never what we will do once we know.*
The contract marks the fields with `x-never-filled-by: [agent]`, and this suite reads that
marker rather than naming the fields, so that a contract that moved the marker moves the
assertion with it.

## What this asserts

- `ProposedDesign` carries exactly the form's fields minus the marked ones minus `filled_by`.
  Read off the dataclass and off the compiled schema; compared as sets.
- `complete()` cannot be called without both withheld fields, and the form it returns is
  stamped `filled_by: agent` with the seven fields carried across unchanged.
- The delivery tool's schema is the compiled form minus the withheld fields, modulo the four
  keyword translations the API forced -- and those are listed by name, so a fifth one added
  without an argument is a diff in this file.
- A delivery carrying a withheld field is not a proposal. The API's `strict` mode would
  refuse it first; `parse()` is what stands behind that, and it is what this checks.

**Measured biting, 2026-09-11, two mutations:** `complete()` given a default `decision_rule`
-- red on the `TypeError` assertion; `ProposedDesign` given a `decision_rule: ... = None`
field -- red on the field-set comparison. Restored, green.

## What it does not check

- **That the API refuses the extra field.** That is the API's behaviour, measured once on
  2026-09-11 when it refused four keywords, and not something a local test can promise.
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from holdout.agent import propose as proposing
from holdout.agent.proposal import ProposalError, ProposedDesign
from holdout.core.design.form import DecisionRule, FilledByKind, MaxDuration

FORM = json.loads(proposing.FORM_SCHEMA.read_text(encoding="utf-8"))
WITHHELD = proposing.not_the_agents(FORM)


def test_the_contract_marks_something_as_never_the_agents() -> None:
    """An empty marker set would make every assertion below vacuous."""
    marked = WITHHELD - {proposing.ATTRIBUTION}
    assert marked, "no field in the compiled form carries x-never-filled-by: [agent]"
    assert marked == {"max_duration", "decision_rule"}, (
        f"the contract marks {sorted(marked)}; CLAUDE.md names max_duration and decision_rule. "
        "If the contract moved, this line is the record of what it said before."
    )


def test_the_proposal_type_has_exactly_the_agents_fields() -> None:
    proposal_fields = {f.name for f in dataclasses.fields(ProposedDesign)}
    form_fields = set(FORM["properties"])
    assert proposal_fields == form_fields - WITHHELD, (
        f"ProposedDesign carries {sorted(proposal_fields)}; the form minus the withheld fields "
        f"is {sorted(form_fields - WITHHELD)}"
    )


def test_complete_requires_both_withheld_fields_and_stamps_the_agent() -> None:
    proposal = proposing.parse(
        {
            "hypothesis": "A deeper end-of-day markdown on bakery reduces waste value per week.",
            "intervention": {"treatment": "ladder_policy@v1", "control": "ladder_policy@v1"},
            "scope": {"categories": ["bakery"], "products": None, "stores": "all"},
            "primary_metric": "waste_value_per_store_week",
            "unit": "store",
            "mde": {"kind": "relative_pct", "value": 5, "direction": "decrease"},
            "exclusions": [],
        }
    )
    with pytest.raises(TypeError):
        proposal.complete(max_duration=MaxDuration(weeks=8))  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        proposal.complete(  # type: ignore[call-arg]
            decision_rule=DecisionRule(
                "adopt the treatment", "keep the ladder", "redesign it first"
            )
        )
    form = proposal.complete(
        max_duration=MaxDuration(weeks=8),
        decision_rule=DecisionRule("adopt the treatment", "keep the ladder", "redesign it first"),
    )
    assert form.filled_by.kind is FilledByKind.AGENT
    for name in {f.name for f in dataclasses.fields(ProposedDesign)}:
        assert getattr(form, name) == getattr(proposal, name), f"{name} changed on completion"


def test_the_delivery_tool_is_the_form_minus_the_withheld_fields() -> None:
    tool = proposing.proposal_tool()
    schema = tool["input_schema"]
    assert set(schema["properties"]) == set(FORM["properties"]) - WITHHELD
    assert set(schema["required"]) == set(FORM["required"]) - WITHHELD
    assert schema["additionalProperties"] is False
    assert tool["strict"] is True

    # The translation is the declared set and nothing else: every keyword the compiled form
    # uses is either carried across or in the list this module names.
    def keywords(node: object, found: set[str]) -> set[str]:
        if isinstance(node, dict):
            for key, value in node.items():
                found.add(key)
                keywords(value, found)
        elif isinstance(node, list):
            for item in node:
                keywords(item, found)
        return found

    in_form = keywords({k: v for k, v in FORM["properties"].items() if k not in WITHHELD}, set())
    in_tool = keywords(schema["properties"], set())
    dropped = in_form - in_tool
    assert dropped <= proposing.UNSUPPORTED_BY_TOOLS | {"oneOf"}, (
        f"{sorted(dropped - proposing.UNSUPPORTED_BY_TOOLS - {'oneOf'})} vanished from the delivery tool "
        "and nothing declares why"
    )
    assert "anyOf" in in_tool or "oneOf" not in in_form, "oneOf was dropped rather than translated"


def test_a_delivery_carrying_a_withheld_field_is_not_a_proposal() -> None:
    delivered = {
        "hypothesis": "A deeper end-of-day markdown on bakery reduces waste value per week.",
        "intervention": {"treatment": "ladder_policy@v1", "control": "ladder_policy@v1"},
        "scope": {"categories": ["bakery"], "products": None, "stores": "all"},
        "primary_metric": "waste_value_per_store_week",
        "unit": "store",
        "mde": {"kind": "relative_pct", "value": 5, "direction": "decrease"},
        "exclusions": [],
        "decision_rule": {
            "if_significant": "adopt",
            "if_not_significant": "keep",
            "if_refused": "x",
        },
    }
    proposal = proposing.parse(delivered)
    assert not hasattr(proposal, "decision_rule"), "the type grew a place to put it"


def test_a_negative_mde_is_a_malformed_delivery_not_a_refusal() -> None:
    """The shape a real model produced twice on 2026-09-11, with the direction in the sign."""
    with pytest.raises(ProposalError) as malformed:
        proposing.parse(
            {
                "hypothesis": "A deeper end-of-day markdown on bakery reduces waste value per week.",
                "intervention": {"treatment": "ladder_policy@v1", "control": "ladder_policy@v1"},
                "scope": {"categories": ["bakery"], "products": None, "stores": "all"},
                "primary_metric": "waste_value_per_store_week",
                "unit": "store",
                "mde": {"kind": "absolute", "value": -2.0},
                "exclusions": [],
            }
        )
    assert "positive difference" in str(malformed.value)
