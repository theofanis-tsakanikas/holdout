"""`DesignForm` mirrors `contracts/design/form.schema.yaml`, and the mirror is checked.

The schema is the source of truth. These dataclasses are the second place the nine fields
exist, for the same reason `guardrails/codes.py` writes out a vocabulary the contract also
holds: `holdout.core` may not import a parser or a validator, so it cannot read the schema at
runtime, and it cannot branch on free-text strings either.

Two places means the two can drift, so the drift is what is tested — **against the YAML
itself**, never against a copy of it in this file. A mirror test that restated the enums here
would be a third definition agreeing with the second while both walked away from the first.

The one thing asserted from memory is the *set* of nine field names, because that set is the
claim: `x-design-fields` naming ten would be a change somebody has to argue for.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from holdout.contracts.model import ContractSet
from holdout.core.design import (
    DecisionRule,
    DesignForm,
    DesignFormError,
    Exclusion,
    FilledBy,
    FilledByKind,
    Intervention,
    MaxDuration,
    Mde,
    MdeDirection,
    MdeKind,
    Scope,
    StoppingKind,
    StoppingRule,
    Unit,
)
from holdout.core.design.form import (
    MAX_DURATION_WEEKS,
    MAX_HYPOTHESIS_CHARS,
    MIN_HYPOTHESIS_CHARS,
    MIN_REASON_CHARS,
)

#: The nine, written out. This is the claim; everything else in the file is read from the
#: schema so that it cannot be a second definition.
THE_NINE = {
    "hypothesis",
    "intervention",
    "scope",
    "primary_metric",
    "unit",
    "mde",
    "max_duration",
    "exclusions",
    "decision_rule",
}


def spec(contracts: ContractSet, field: str) -> Any:
    return contracts.design_form["properties"][field]


# ------------------------------------------------------------------ the field set


def test_the_form_declares_exactly_nine_fields(contracts: ContractSet) -> None:
    assert set(contracts.design_form["x-design-fields"]) == THE_NINE


def test_the_dataclass_carries_the_nine_and_the_attribution(contracts: ContractSet) -> None:
    """`filled_by` is attribution rather than a design field, which is why the schema counts
    it separately — and why the dataclass has ten attributes for nine fields."""
    import dataclasses

    fields = {f.name for f in dataclasses.fields(DesignForm)}
    assert fields == THE_NINE | {"filled_by"}


def test_every_field_is_required_in_the_schema(contracts: ContractSet) -> None:
    """An optional field is a field that will be left empty exactly when it matters."""
    assert set(contracts.design_form["required"]) == THE_NINE | {"filled_by"}


# ------------------------------------------------------------------ the inline enums


def test_the_unit_enum_mirrors_the_schema(contracts: ContractSet) -> None:
    assert {u.value for u in Unit} == set(spec(contracts, "unit")["enum"])


def test_the_mde_kind_enum_mirrors_the_schema(contracts: ContractSet) -> None:
    kinds = spec(contracts, "mde")["properties"]["kind"]["enum"]
    assert {k.value for k in MdeKind} == set(kinds)


def test_the_mde_direction_enum_mirrors_the_schema(contracts: ContractSet) -> None:
    directions = spec(contracts, "mde")["properties"]["direction"]["enum"]
    assert {d.value for d in MdeDirection} == set(directions)


def test_direction_is_optional_in_the_schema_and_required_in_the_core(
    contracts: ContractSet,
) -> None:
    """Not a default, and this is where the argument is written down.

    The schema's own description of the field is *"a one-sided expectation must be declared
    before the period opens or not at all"*, so an absent `direction` in a submitted document
    means the design did not declare one — which is `either`. The adapter reads that sentence
    at the boundary; the core does not carry the ambiguity any further, because a field that
    is sometimes absent is a field every later branch has to remember to handle.
    """
    mde = spec(contracts, "mde")
    assert set(mde["required"]) == {"kind", "value"}
    assert (
        "declared before the period opens or not at all"
        in mde["properties"]["direction"]["description"]
    )
    with pytest.raises(TypeError):
        Mde(kind=MdeKind.ABSOLUTE, value=Decimal(1))  # type: ignore[call-arg]


# ------------------------------------------------------------------ the closed lists


def test_the_three_closed_lists_are_not_written_out_in_the_schema(
    contracts: ContractSet,
) -> None:
    """`x-closed-list` names where they come from, and the compiler resolves them.

    A hand-written enum of metric ids in the form would be a second definition of the metric
    contract, which is the one thing the contract layer exists to prevent — so the core does
    not mirror them either. `METRIC_NOT_IN_CONTRACT` is decided against `metric_ids` handed
    to `assess`, at run time, from the contract.
    """
    assert spec(contracts, "primary_metric")["x-closed-list"] == "metric_ids"
    intervention = spec(contracts, "intervention")["properties"]
    assert intervention["treatment"]["x-closed-list"] == "policy_refs"
    assert intervention["control"]["x-closed-list"] == "policy_refs"
    assert "enum" not in spec(contracts, "primary_metric")


# ------------------------------------------------------------------ the bounds


def test_the_hypothesis_bounds_mirror_the_schema(contracts: ContractSet) -> None:
    hypothesis = spec(contracts, "hypothesis")
    assert hypothesis["minLength"] == MIN_HYPOTHESIS_CHARS
    assert hypothesis["maxLength"] == MAX_HYPOTHESIS_CHARS


def test_the_duration_bounds_mirror_the_schema(contracts: ContractSet) -> None:
    weeks = spec(contracts, "max_duration")["properties"]["weeks"]
    assert weeks["minimum"] == 1
    assert weeks["maximum"] == MAX_DURATION_WEEKS


def test_the_exclusion_reason_bound_mirrors_the_schema(contracts: ContractSet) -> None:
    reason = spec(contracts, "exclusions")["items"]["properties"]["reason"]
    assert reason["minLength"] == MIN_REASON_CHARS


def test_the_decision_rule_bounds_mirror_the_schema(contracts: ContractSet) -> None:
    rule = spec(contracts, "decision_rule")["properties"]
    for branch in ("if_significant", "if_not_significant", "if_refused"):
        assert rule[branch]["minLength"] == MIN_REASON_CHARS, branch


def test_the_mde_is_strictly_positive_in_both_places(contracts: ContractSet) -> None:
    assert spec(contracts, "mde")["properties"]["value"]["exclusiveMinimum"] == 0
    with pytest.raises(DesignFormError, match="positive difference"):
        Mde(kind=MdeKind.ABSOLUTE, value=Decimal(0), direction=MdeDirection.EITHER)


def test_a_named_store_list_needs_at_least_two_in_both_places(
    contracts: ContractSet,
) -> None:
    """One store cannot be split into two arms."""
    stores = spec(contracts, "scope")["properties"]["stores"]["oneOf"]
    listed = next(option for option in stores if option.get("type") == "array")
    assert listed["minItems"] == 2
    with pytest.raises(DesignFormError, match="at least two entries"):
        Scope(categories=("dairy",), products=None, stores=("store-1",))


# ------------------------------------------------------------------ the conversions


def test_an_mde_arrives_as_a_decimal_and_never_as_a_float() -> None:
    """The schema says `number`; JSON and PyYAML both hand back a binary float. The adapter
    converts at the boundary, and a float that got past it is refused here rather than one
    division later."""
    with pytest.raises(DesignFormError, match="not float"):
        Mde(kind=MdeKind.ABSOLUTE, value=1.5, direction=MdeDirection.EITHER)  # type: ignore[arg-type]


def test_all_stores_is_none_rather_than_a_sentinel(contracts: ContractSet) -> None:
    """The schema's `all` and an explicit list are two shapes; `None` is the core's word for
    the first. An empty list is refused rather than read as "every product", because the two
    would then be indistinguishable at exactly the moment it mattered."""
    stores = spec(contracts, "scope")["properties"]["stores"]["oneOf"]
    assert any(option.get("const") == "all" for option in stores)
    assert Scope(categories=("dairy",), products=None, stores=None).stores is None
    with pytest.raises(DesignFormError, match="not 'every product'"):
        Scope(categories=("dairy",), products=(), stores=None)


@pytest.mark.parametrize(
    ("attribution", "rendered"),
    [
        (FilledBy(kind=FilledByKind.AGENT), "agent"),
        (FilledBy(kind=FilledByKind.HUMAN, name="A. Reviewer"), "human:A. Reviewer"),
        (FilledBy(kind=FilledByKind.POLICY, name="quarterly_review"), "policy:quarterly_review"),
    ],
)
def test_filled_by_renders_in_the_shape_the_schema_s_pattern_admits(
    contracts: ContractSet, attribution: FilledBy, rendered: str
) -> None:
    import re

    pattern = spec(contracts, "filled_by")["pattern"]
    assert str(attribution) == rendered
    assert re.match(pattern, rendered), rendered


def test_a_human_attribution_with_nobody_behind_it_is_refused() -> None:
    with pytest.raises(DesignFormError, match="unsigned decision"):
        FilledBy(kind=FilledByKind.HUMAN, name=None)


def test_the_agent_is_one_actor_and_carries_no_name() -> None:
    with pytest.raises(DesignFormError, match="one actor"):
        FilledBy(kind=FilledByKind.AGENT, name="the agent")


# --------------------------------------------- what the schema cannot say and the core can


def test_the_same_store_excluded_twice_with_two_reasons_is_refused() -> None:
    """`uniqueItems` compares whole objects, so two entries for one store with different
    reasons pass the schema. Which one is the reason?"""
    with pytest.raises(DesignFormError, match="excluded twice"):
        DesignForm(
            hypothesis="Deeper early markdowns on fresh dairy raise category margin.",
            intervention=Intervention(treatment="p@v1", control="p@v1"),
            scope=Scope(categories=("dairy",), products=None, stores=None),
            primary_metric="category_margin_per_store_week",
            unit=Unit.STORE,
            mde=Mde(kind=MdeKind.ABSOLUTE, value=Decimal(1), direction=MdeDirection.EITHER),
            max_duration=MaxDuration(weeks=4),
            exclusions=(
                Exclusion(store_id="store-1", reason="refit closes the counters"),
                Exclusion(store_id="store-1", reason="it drags the mean down"),
            ),
            decision_rule=DecisionRule(
                if_significant="Roll the ladder out to every fresh category.",
                if_not_significant="Keep the existing ladder.",
                if_refused="Re-run next quarter.",
            ),
            filled_by=FilledBy(kind=FilledByKind.AGENT),
        )


def test_a_group_sequential_rule_with_no_spending_function_is_constructible() -> None:
    """On purpose. That is exactly the design `STOPPING_RULE_PERMITS_PEEKING` refuses, and a
    type that raised on it would turn a refusal into an error — and make the code
    unreachable in the bargain."""
    rule = StoppingRule(kind=StoppingKind.GROUP_SEQUENTIAL, looks=3)
    assert rule.permits_peeking


def test_a_sequential_design_that_admits_it_will_look_once_is_malformed() -> None:
    """One look is a single readout wearing another name. That is structural incoherence
    rather than a design to refuse."""
    with pytest.raises(DesignFormError, match="at least two"):
        StoppingRule(kind=StoppingKind.GROUP_SEQUENTIAL, spending_function="pocock", looks=1)


def test_a_single_readout_carrying_looks_is_malformed() -> None:
    with pytest.raises(DesignFormError, match="two different designs at once"):
        StoppingRule(kind=StoppingKind.SINGLE_READOUT_AT_END, looks=3)


def test_a_stopping_rule_has_no_default() -> None:
    """Doctrine rule 3. A default here would be a lie with a plausible shape, and the
    plausible shape is the permissive one: assuming a single readout for a design that never
    said so would make the refusal unable to fire."""
    with pytest.raises(TypeError):
        StoppingRule()  # type: ignore[call-arg]
