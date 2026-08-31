"""Claim 7's rule: a decision is addressed by what is priced and where, never by who buys it.

`CLAUDE.md`, claim 7: *a decision that targets a person is structurally impossible. The
decision key has no customer dimension, and a test goes red if one appears.*

This module exists so that rule has **one** implementation, in the way `ops/isolation.py`
exists for the corpus barrier. It has two callers, running at two different moments and
asking two different questions:

- `tests/core/test_decision_key.py` — on every push: *is it true right now?*
- `evals/oversight/` — `make claim-7`: *is it true against 317 names two published
  vocabularies use for a person, and does it still refuse when each of them is planted?*

Two hand-written copies of the same registry would drift, and the copy that drifts is the
one nobody reads.

What is here and what is deliberately not
-----------------------------------------
Here: the field set of every type on the decision path, **written down by hand**; the
hand-written list of person-shaped words; and the two mechanical questions — does a type
carry exactly what is written down, and is there a type nobody wrote down.

Not here: any opinion about which *external* names count as a person. That question is
claim 7's trap — a list of person-shaped words written by whoever also wrote the field names
is one function agreeing with itself — and the answer is that the names come from outside
this repository entirely. `corpus/real/` holds them and `evals/oversight/build.py` joins the
two. Measured, the `PERSON_SHAPED` tuple below catches **35 of the 317** names schema.org and
Presidio publish. It is a net under the claim; it is not the claim.

Why the registry is written out and not derived
-----------------------------------------------
A registry read off the classes could never disagree with the classes. `FIELDS_ON_THE_DECISION_PATH`
is what a human wrote and a reviewer can read against the claim, which is why adding *any*
field — however innocent, however unrelated to a person — turns something red and somebody
has to say what it is for.
"""

from __future__ import annotations

import dataclasses
import importlib
import pkgutil
import re
from collections.abc import Mapping, Sequence
from typing import Any

import holdout.core
from holdout.core.decision import DecisionKey
from holdout.core.demand.censoring import (
    AvailabilityCurve,
    DemandEstimate,
    FullyObserved,
    HourlySales,
    RightCensored,
    ShelfState,
    TradingWindow,
)
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
from holdout.core.experiment.estimator import _ArmPlan, _Shifted, _Sums
from holdout.core.guardrails import Announcement, Assessment, CertifiedPrice, ProposedPrice, Refusal
from holdout.core.guardrails.benchmark import MarginOnPrice, MarkupOnCost
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
    Renaming,
)
from holdout.core.ladder import LadderQuote
from holdout.core.money import Money
from holdout.core.pricing import Outcome, Scenario, Selection

#: Every type a decision passes through, with its fields written out. This is claim 7.
#:
#: Deliberately not derived from the classes: a test that read the field set off the class
#: could never disagree with the class. These are the names a human wrote down and a
#: reviewer can read against the claim.
FIELDS_ON_THE_DECISION_PATH: dict[type[Any], frozenset[str]] = {
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
            "benchmark_markup_on_cost",
            "week_opening_price",
        }
    ),
    MarkupOnCost: frozenset({"pct"}),
    MarginOnPrice: frozenset({"pct"}),
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
            "refuse_when_no_price_satisfies_every_guardrail",
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
    # ------------------------------------------------------- reading demand off a shelf
    #
    # Claim 4's types, and they are the closest thing in this package to a place a person
    # could be smuggled in: a demand observation is exactly where a real retailer would be
    # tempted to carry a basket, a loyalty number or a shopper segment, because that is what
    # makes a demand model better. The grain here is a store, a SKU and a business date, and
    # the addition of anything finer is a red test rather than a design review.
    TradingWindow: frozenset({"open_hour", "close_hour"}),
    ShelfState: frozenset(
        {"store_id", "sku_id", "business_date", "units_sold", "stocked_out_from_hour"}
    ),
    HourlySales: frozenset({"state", "units_by_hour"}),
    FullyObserved: frozenset({"units"}),
    #: No `units`, and the absence is the claim. See `censoring.RightCensored`.
    RightCensored: frozenset({"at_least", "stocked_out_from_hour"}),
    AvailabilityCurve: frozenset({"window", "units_by_hour", "days"}),
    DemandEstimate: frozenset({"at_least", "units", "censored", "observed_share"}),
    # Not on the decision path: `Renaming` is contract bookkeeping — what a guardrail rule
    # used to be called and from when — and it never reaches a price, a proposal or a key.
    # Listed anyway, for the reason this file's docstring gives. It arrived on
    # `contracts/floor-rule-id` and this registry is what refused it until it was written
    # down, which is the guard doing exactly what claim 7 says it does.
    Renaming: frozenset({"since", "previously"}),
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
            "dropped",
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
    # The estimator's three private helpers. They are not on the decision path and their
    # names say so — which is exactly why they were exempt until 2026-08-29, and exactly the
    # hole that exemption opened. A leading underscore is a convention, not a boundary, and a
    # registry that any spelling can walk past is not a registry. See `unlisted`.
    _ArmPlan: frozenset({"rank", "rows", "solve"}),
    _Shifted: frozenset(
        {
            "difference_at_zero",
            "difference_slope",
            "variance_at_zero",
            "variance_curve",
            "variance_slope",
        }
    ),
    _Sums: frozenset({"cross", "right", "shift_right", "total_square", "treated_count"}),
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

    `CertifiedPrice` is not one — its constructor refuses, which is most of claim 1 — and
    neither is `SealedAssignment`, whose constructor refusal is most of doctrine rule 7. A
    scan built on `dataclasses.fields` could not see either of them, which is a hole exactly
    where claim 7 matters most: the actuation type is the last thing a price passes through.
    Reading `__slots__` as well is what closes it, and `evals/oversight/` publishes the count
    of non-dataclasses reached so that the hole cannot quietly reopen.
    """
    if dataclasses.is_dataclass(cls):
        return frozenset(f.name for f in dataclasses.fields(cls))
    slots = getattr(cls, "__slots__", ())
    if isinstance(slots, str):
        slots = (slots,)
    return frozenset(slots) - {"__weakref__", "__dict__"}


def core_types() -> list[type[Any]]:
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


def unlisted(
    types: Sequence[type[Any]] | None = None,
    registry: Mapping[type[Any], frozenset[str]] | None = None,
) -> list[str]:
    """Types in the core that carry fields and that nobody wrote down.

    Without this, claim 7 could be defeated by adding a *type* rather than a field — a
    `CustomerContext` nobody listed, carried on a proposal, asserted nowhere.

    **A leading underscore exempted a type from this until 2026-08-29, and it should never
    have.** The exemption was inherited from the version of this rule that lived in
    `tests/core/test_decision_key.py`, where it read as ordinary hygiene: private helpers are
    not on the decision path, so why write them down. What it actually did was leave one
    spelling that walks straight past the guard — rename the type `_VisitContext` and it is
    invisible — and the guard's own printed question said *every* type. That is this project's
    most frequent defect in the shape its own naming convention produces, and it was found by
    oversight level 2 renaming the mutation's planted class. The three private types the
    estimator carries are now written down like everything else, and
    `evals/gate_proof/mutations/claim-7/07-…` plants the underscored version so that nothing
    but the code decides whether the hole is closed.
    """
    found = core_types() if types is None else list(types)
    written = FIELDS_ON_THE_DECISION_PATH if registry is None else registry
    return [
        f"{cls.__module__}.{cls.__name__}"
        for cls in found
        if cls not in written and field_names(cls)
    ]


def misdeclared(
    registry: Mapping[type[Any], frozenset[str]] | None = None,
) -> list[str]:
    """Types whose live field set is not the one written down beside them.

    This is the check that carries the claim, and it does not care what the new field is
    called. A field named `nationality` and a field named `q7` are the same finding here.
    """
    written = FIELDS_ON_THE_DECISION_PATH if registry is None else registry
    offences: list[str] = []
    for cls, expected in written.items():
        actual = field_names(cls)
        if actual == expected:
            continue
        added = sorted(actual - expected)
        gone = sorted(expected - actual)
        detail = ", ".join(
            part
            for part in (
                f"+{', +'.join(added)}" if added else "",
                f"-{', -'.join(gone)}" if gone else "",
            )
            if part
        )
        offences.append(f"{cls.__module__}.{cls.__name__}: {detail}")
    return offences


def person_shaped(name: str) -> tuple[str, ...]:
    """Which of the hand-written substrings this field name matches, in its own arithmetic.

    Substring matching, because that is the rule the tuple was written under — `user_`,
    `card_` and `vat_number` are prefixes and fragments rather than whole words, and judging
    them by anything else would be judging a detector by arithmetic it was never given.
    """
    lowered = name.lower()
    return tuple(needle for needle in PERSON_SHAPED if needle in lowered)


def tokens(name: str) -> tuple[str, ...]:
    """A name broken into its words, whatever house style spelled it.

    `familyName`, `family_name`, `FAMILY_NAME` and `Family-Name` all come back as
    `("family", "name")`. This is the one piece of arithmetic the eval shares with nothing
    else: it is how a name published as camelCase by schema.org and as SCREAMING_SNAKE by
    Presidio is compared with a field spelled the way this repository spells fields.
    """
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", spaced).strip("_").lower()
    return tuple(part for part in cleaned.split("_") if part)
