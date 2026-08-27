"""Claim 7 — a decision that targets a person is structurally impossible.

The decision key has no customer dimension, and this file is the test that goes red if one
appears. It is cheap, it needs nothing but the core, and PLAN.md puts it in phase 1 for
exactly that reason.

Why this file is written the way it is
---------------------------------------
It started as a substring blacklist over `dataclasses.fields`, and a review broke it three
ways in about a minute: `subject_hash` on `ProposedPrice` passed because the word was not on
the list; `_customer_id` in `CertifiedPrice.__slots__` passed because `CertifiedPrice` is
deliberately **not** a dataclass — the design choice that makes claim 1 strong made claim 7
blind to the actuation type itself; and `basket_id` on `DecisionKey` was caught only by the
exact-field-set assertion, not by the scan.

A blacklist only ever catches an honest mistake. Claim 7 is a structural claim, so the
structure is what is asserted:

* **the exact field set of every type on the decision path**, written out here, so that
  adding *any* field — however innocent, however unrelated to a person — turns this red and
  somebody has to say what it is for;
* the blacklist as well, over dataclass fields **and** `__slots__`, because it is what
  catches a person-shaped field arriving on a type nobody thought to list.

The first is the claim. The second is a net under it.
"""

from __future__ import annotations

import dataclasses
import importlib
import pkgutil
from typing import Any

import pytest

import holdout.core
from holdout.contracts.model import ContractSet
from holdout.core.decision import DecisionKey, DecisionPath
from holdout.core.design import (
    DecisionRule,
    DesignForm,
    DesignRefusal,
    DesignRefusalReason,
    Exclusion,
    Feasible,
    FilledBy,
    Intervention,
    MaxDuration,
    Mde,
    Scope,
    StoppingRule,
)
from holdout.core.experiment import (
    CheckResult,
    Contamination,
    CovariateMatrix,
    Design,
    Exposure,
    Period,
    Readout,
    ReadoutRefusal,
    ReferencePlan,
    SealedAssignment,
    Standardised,
    Statistic,
)
from holdout.core.guardrails import Announcement, Assessment, CertifiedPrice, ProposedPrice, Refusal
from holdout.core.guardrails.envelope import (
    Bound,
    Envelope,
    FloorRule,
    FrozenCategoriesRule,
    GuardrailRefusal,
    MarginCapRule,
    MaxDeltaRule,
    PriceBounds,
    PriorPriceRule,
)
from holdout.core.ladder import LadderQuote
from holdout.core.money import Money
from holdout.core.pricing import Outcome, Scenario, Selection

#: Every type a decision passes through, with its fields written out. This is claim 7.
#:
#: Deliberately not derived from the classes: a test that read the field set off the class
#: could never disagree with the class. These are the names a human wrote down and a
#: reviewer can read against the claim.
EXACT_FIELDS: dict[type[Any], frozenset[str]] = {
    DecisionKey: frozenset({"path", "sku_id", "store_id", "occasion"}),
    ProposedPrice: frozenset(
        {
            "key",
            "decided_at",
            "price",
            "base_price",
            "category_id",
            "source",
            "is_perishable",
            "announced_as_reduction",
            "unit_cost",
            "cost_known_at",
            "marker",
            "changes_dispatched_today",
            "prior_price",
            "benchmark_margin_pct",
            "week_opening_price",
        }
    ),
    CertifiedPrice: frozenset(
        {
            "_witness",
            "_key",
            "_price",
            "_decided_at",
            "_decided_on",
            "_source",
            "_marker",
            "_cost_freshness",
            "_announcement",
            "_bounds",
            "_checks",
        }
    ),
    Refusal: frozenset({"key", "decided_at", "reasons", "bounds"}),
    GuardrailRefusal: frozenset({"code", "guardrail", "rule_id", "detail", "safe_state"}),
    Assessment: frozenset({"key", "bounds", "cost_freshness", "announcement", "refusals"}),
    Bound: frozenset({"amount", "guardrail", "rule_id", "code", "why"}),
    PriceBounds: frozenset({"lower", "upper"}),
    Announcement: frozenset({"basis", "prior_price", "lookback_days"}),
    LadderQuote: frozenset({"step", "depth_pct", "price", "marker", "clamped_to_floor"}),
    Scenario: frozenset({"price", "expected_units"}),
    Outcome: frozenset(
        {
            "scenario",
            "units_sold",
            "units_wasted",
            "revenue",
            "cost_of_sales",
            "cost_of_waste",
            "contribution",
        }
    ),
    Selection: frozenset({"chosen", "ranked"}),
    # The envelope itself. Not on the decision path in the sense that a person could ride
    # in on it, but listed for the reason the test above gives: an unlisted type is a place
    # to put a field nobody asserted, and "it is only configuration" is how that starts.
    Envelope: frozenset(
        {
            "decided_on",
            "path",
            "floor",
            "max_delta",
            "frozen_categories",
            "margin_cap",
            "prior_price",
        }
    ),
    FloorRule: frozenset(
        {
            "minimum_gross_margin_pct",
            "minimum_absolute_price",
            "cost_staleness_hours",
            "refuse_when_no_legal_price_sells",
            "safe_state",
        }
    ),
    MaxDeltaRule: frozenset(
        {
            "markdown_max_depth_pct",
            "markdown_max_changes_per_sku_per_day",
            "base_price_max_weekly_increase_pct",
            "base_price_max_weekly_decrease_pct",
            "safe_state",
        }
    ),
    FrozenCategoriesRule: frozenset({"category_ids", "safe_state"}),
    MarginCapRule: frozenset(
        {"in_force", "basis", "benchmark", "regulated_category_ids", "safe_state"}
    ),
    PriorPriceRule: frozenset(
        {"perishable_exemption", "lookback_days", "progressive_reduction_window_days", "safe_state"}
    ),
    Money: frozenset({"cents"}),
    # ------------------------------------------------------- the design engine
    #
    # Not on the decision path: an experiment design is about *which* units get *which
    # policy*, never about who buys anything. Listed anyway, for the reason this file's
    # docstring gives — an unlisted type is a place to put a field nobody asserted, and
    # "it is only the experiment layer" is exactly how that would start. The vocabulary
    # here is arm, unit, stratum and roster. Never cohort, never segment.
    DesignForm: frozenset(
        {
            "hypothesis",
            "intervention",
            "scope",
            "primary_metric",
            "unit",
            "mde",
            "max_duration",
            "exclusions",
            "decision_rule",
            "filled_by",
        }
    ),
    Intervention: frozenset({"treatment", "control"}),
    Scope: frozenset({"categories", "products", "stores"}),
    Mde: frozenset({"kind", "value", "direction"}),
    MaxDuration: frozenset({"weeks"}),
    Exclusion: frozenset({"store_id", "reason"}),
    DecisionRule: frozenset({"if_significant", "if_not_significant", "if_refused"}),
    StoppingRule: frozenset({"kind", "spending_function", "looks"}),
    FilledBy: frozenset({"kind", "name"}),
    DesignRefusal: frozenset({"experiment_id", "reasons"}),
    DesignRefusalReason: frozenset({"code", "detail", "what_would_fix_it"}),
    Feasible: frozenset(
        {
            "experiment_id",
            "form_digest",
            "metric_ref",
            "roster",
            "declared_exclusions",
            "automatic_exclusions",
            "required_per_arm",
            "weeks",
            "mde_absolute",
            "two_sided",
            "assignment",
            "balance",
        }
    ),
    # ------------------------------------------------------- the experiment core
    #
    # `SealedAssignment` is the second type in this repository that is deliberately not a
    # dataclass — its constructor raises, which is most of doctrine rule 7 — so it is
    # `__slots__` that has to be read here. That is the hole a review found in an earlier
    # version of this file for `CertifiedPrice`, and it stays closed by listing both.
    SealedAssignment: frozenset(
        {
            "_witness",
            "_experiment_id",
            "_seed",
            "_draw_index",
            "_strata",
            "_arms",
            "_form_digest",
            "_covariate_digest",
            "_digest",
        }
    ),
    CovariateMatrix: frozenset({"ids", "kinds", "rows"}),
    Standardised: frozenset({"covariate_id", "level", "squared"}),
    Contamination: frozenset(
        {
            "digest_matches",
            "redraw_matches",
            "reassigned",
            "misdelivered",
            "undelivered",
            "comparison_is_vacuous",
        }
    ),
    Exposure: frozenset({"assigned_treated", "exposed_treated"}),
    Design: frozenset({"units", "columns", "rows"}),
    Statistic: frozenset({"difference", "variance", "squared", "sign"}),
    ReferencePlan: frozenset({"design", "grand_mean", "plans"}),
    Period: frozenset({"opens_on", "ends_on"}),
    CheckResult: frozenset({"check", "passed", "figure"}),
    Readout: frozenset(
        {
            "experiment_id",
            "metric_ref",
            "data_version",
            "period",
            "seed",
            "draw_index",
            "digest",
            "uplift",
            "confidence_interval",
            "p_value",
            "draws",
            "alpha",
            "statistic",
            "checks",
            "balance",
        }
    ),
    ReadoutRefusal: frozenset(
        {
            "experiment_id",
            "metric_ref",
            "data_version",
            "period",
            "seed",
            "draw_index",
            "digest",
            "checks",
            "balance",
        }
    ),
}

#: Substrings that name a person or a way of reaching one. Broad on purpose — a false
#: positive costs a conversation and a false negative costs the claim.
PERSON_SHAPED = (
    "customer",
    "consumer",
    "shopper",
    "member",
    "loyalty",
    "household",
    "person",
    "individual",
    "subject",
    "basket",
    "pseudonym",
    "user_",
    "email",
    "phone",
    "msisdn",
    "card_",
    "cardholder",
    "segment",
    "cohort",
    "profile",
    "identity",
    "citizen",
    "vat_number",
    "tax_id",
    "birth",
    "gender",
    "postcode",
    "address",
)


def field_names(cls: type[Any]) -> frozenset[str]:
    """What a type carries, whether or not it is a dataclass.

    `CertifiedPrice` is not one — its constructor refuses, which is most of claim 1 — so a
    scan built on `dataclasses.fields` could not see the actuation type at all. Reading
    `__slots__` as well is what closes that.
    """
    if dataclasses.is_dataclass(cls):
        return frozenset(f.name for f in dataclasses.fields(cls))
    slots = getattr(cls, "__slots__", ())
    if isinstance(slots, str):
        slots = (slots,)
    return frozenset(slots) - {"__weakref__", "__dict__"}


def _core_types() -> list[type[Any]]:
    """Every dataclass and every slotted class defined under `holdout.core`."""
    found: list[type[Any]] = []
    for module_info in pkgutil.walk_packages(holdout.core.__path__, "holdout.core."):
        module = importlib.import_module(module_info.name)
        for value in vars(module).values():
            if not isinstance(value, type) or value.__module__ != module_info.name:
                continue
            if dataclasses.is_dataclass(value) or hasattr(value, "__slots__"):
                found.append(value)
    return found


# ------------------------------------------------------------------ the structural claim


@pytest.mark.parametrize("cls", list(EXACT_FIELDS), ids=lambda c: c.__name__)
def test_the_type_carries_exactly_the_fields_written_down_here(cls: type[Any]) -> None:
    """Adding any field to a decision-path type is a red test and a conversation."""
    assert field_names(cls) == EXACT_FIELDS[cls]


def test_every_decision_path_type_is_listed() -> None:
    """The list above is the claim, so a new type on the path must join it.

    Without this, claim 7 could be defeated by adding a *type* rather than a field — a
    `CustomerContext` nobody listed, carried on a proposal, asserted nowhere.
    """
    unlisted = [
        f"{cls.__module__}.{cls.__name__}"
        for cls in _core_types()
        if cls not in EXACT_FIELDS and not cls.__name__.startswith("_") and field_names(cls)
    ]
    assert not unlisted, (
        "a type in holdout.core carries fields and is not in EXACT_FIELDS. Either it is on "
        "the decision path — in which case write its fields down — or it is not, in which "
        "case say so by listing it anyway:\n  " + "\n  ".join(unlisted)
    )


# ------------------------------------------------------------------ the net under it


def test_no_type_in_the_core_carries_a_customer_dimension() -> None:
    classes = _core_types()
    assert len(classes) >= 10, "the scan found almost nothing and would pass vacuously"
    assert CertifiedPrice in classes, (
        "the actuation type is not a dataclass, and a scan that cannot see it is a scan "
        "with a hole exactly where claim 7 matters most"
    )
    offences = [
        f"{cls.__module__}.{cls.__name__}.{name}"
        for cls in classes
        for name in sorted(field_names(cls))
        for needle in PERSON_SHAPED
        if needle in name.lower()
    ]
    assert not offences, (
        "a decision in this system is addressed by what is being priced and where. These "
        "fields would give it somewhere to attach a person:\n  " + "\n  ".join(offences)
    )


# ------------------------------------------------------------------ the key itself


def test_the_key_is_the_contract_s_idempotency_key(contracts: ContractSet) -> None:
    """`ladder_policy@v1` declares `[sku_id, store_id, ladder_step]`, and the key answers all
    three. Re-running a decision therefore never produces a second price change."""
    ladder = next(p for p in contracts.policies if p.id == "ladder_policy")
    assert ladder.idempotency_key == ("sku_id", "store_id", "ladder_step")
    key = DecisionKey(path=DecisionPath.MARKDOWN, sku_id="sku-1", store_id="store-7", occasion=3)
    assert key.sku_id == "sku-1"
    assert key.store_id == "store-7"
    assert key.ladder_step == 3


def test_the_base_price_path_has_no_ladder_step() -> None:
    """The occasion means something different on each path, and the path is in the key, so
    a markdown rung and a pricing-week ordinal can never collide."""
    key = DecisionKey(path=DecisionPath.BASE_PRICE, sku_id="sku-1", store_id="store-7", occasion=3)
    assert key.ladder_step is None
    markdown = DecisionKey(
        path=DecisionPath.MARKDOWN, sku_id="sku-1", store_id="store-7", occasion=3
    )
    assert key != markdown


def test_two_decisions_for_the_same_rung_are_the_same_decision() -> None:
    first = DecisionKey(path=DecisionPath.MARKDOWN, sku_id="sku-1", store_id="store-7", occasion=2)
    second = DecisionKey(path=DecisionPath.MARKDOWN, sku_id="sku-1", store_id="store-7", occasion=2)
    assert first == second
    assert len({first, second}) == 1


@pytest.mark.parametrize(
    ("sku", "store", "occasion"),
    [("", "store-7", 1), ("sku-1", "", 1), ("sku-1", "store-7", 0)],
)
def test_a_key_that_names_nothing_is_refused(sku: str, store: str, occasion: int) -> None:
    with pytest.raises(ValueError, match=r"decision|occasion"):
        DecisionKey(path=DecisionPath.MARKDOWN, sku_id=sku, store_id=store, occasion=occasion)
