"""The envelope refuses, and every bound is worked out by hand here.

The refusal tests run against `independent_envelope` — literal numbers written in
`conftest.py`, with the guardrail contracts never opened — because claim 1's declared trap
is that a planter reading the same contract as the detector is one function agreeing with
itself. A separate group of tests drives `contract_envelope` to prove the projection from
`contracts/` produces the numbers the files actually contain.

The independent envelope's numbers, once, so the arithmetic below can be checked:
floor 12.5% of cost and 0.10 EUR absolute, cost stale after 6h, markdown at most 40% below
base, at most 3 changes a day, the cap in force for `dairy` on a per-unit basis, the
perishable exemption in force, `tobacco` frozen.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from types import MappingProxyType

import pytest

from holdout.contracts.model import ContractSet
from holdout.core.decision import DecisionKey, DecisionPath, PriceSource, SafeState
from holdout.core.guardrails import (
    AnnouncementBasis,
    Assessment,
    BenchmarkError,
    Envelope,
    EnvelopeError,
    Freshness,
    GuardrailId,
    MarginOnPrice,
    MarkupOnCost,
    ProposalError,
    ProposedPrice,
    RefusalCode,
    envelope_as_of,
    evaluate,
)
from holdout.core.money import Money

#: `propose` is defined in conftest.py; the alias is repeated here rather than imported,
#: because the tests directory is not a package and does not need to become one.
ProposalFactory = Callable[..., ProposedPrice]

DECIDED_ON = date(2026, 4, 1)
DECIDED_AT = datetime(2026, 4, 1, 14, 0, tzinfo=UTC)


def codes(assessment: Assessment) -> set[RefusalCode]:
    return {r.code for r in assessment.refusals}


# ------------------------------------------------------------------ nothing wrong


def test_a_price_inside_every_bound_is_admitted(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """cost 1.00, so the margin floor is 100 + 12.5% = 112.5 cents, rounded up to 113.
    base 3.00, so the depth floor is 300 - 40% = 180 cents. The binding floor is 180.
    `yoghurt` is not in the regulated basket here, so there is no ceiling at all."""
    assessment = evaluate(propose(price=Money.of("1.85")), independent_envelope)
    assert assessment.passed
    minimum = assessment.bounds.minimum
    assert minimum is not None
    assert minimum.amount == Money.of("1.80")
    assert minimum.rule_id == "markdown_max_depth_pct"
    assert assessment.bounds.maximum is None
    assert assessment.cost_freshness is Freshness.FRESH


# ------------------------------------------------------------------ each guardrail refuses


def test_a_frozen_category_stops_the_path_before_anything_else(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    assessment = evaluate(propose(category_id="tobacco"), independent_envelope)
    assert RefusalCode.CATEGORY_FROZEN in codes(assessment)
    leading = assessment.leading
    assert leading is not None
    assert leading.code is RefusalCode.CATEGORY_FROZEN
    assert leading.safe_state is SafeState.NO_ACTION, (
        "a frozen category is not a category with a tighter bound — no decision is taken, "
        "so the fallback is no action and not the ladder"
    )


def test_the_margin_floor_rounds_up_and_refuses_a_price_half_a_cent_below(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """100 cents of cost plus 12.5% is 112.5 cents. The floor is 113, not 112: a bound that
    rounded to the nearest cent would admit a price below the floor it declares."""
    assessment = evaluate(
        propose(price=Money.of("1.12"), base_price=Money.of("1.20")), independent_envelope
    )
    assert RefusalCode.BELOW_MARGIN_FLOOR in codes(assessment)
    assert evaluate(
        propose(price=Money.of("1.13"), base_price=Money.of("1.20")), independent_envelope
    ).passed


def test_the_absolute_floor_refuses_a_price_no_cost_could_justify(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    assessment = evaluate(
        propose(price=Money(1), unit_cost=Money(0), base_price=Money.of("0.20")),
        independent_envelope,
    )
    assert RefusalCode.BELOW_ABSOLUTE_FLOOR in codes(assessment)


def test_a_markdown_deeper_than_the_envelope_allows_is_refused(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """base 3.00 at 40% maximum depth gives a floor of 1.80. 1.79 is one cent past it."""
    assessment = evaluate(
        propose(price=Money.of("1.79"), unit_cost=Money.of("0.50")), independent_envelope
    )
    assert RefusalCode.MARKDOWN_EXCEEDS_MAX_DEPTH in codes(assessment)


def test_the_daily_change_budget_makes_a_retry_loop_visible(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    assert evaluate(propose(changes_dispatched_today=2), independent_envelope).passed
    assessment = evaluate(propose(changes_dispatched_today=3), independent_envelope)
    assert RefusalCode.DAILY_CHANGE_BUDGET_EXHAUSTED in codes(assessment)


def test_the_margin_cap_binds_only_inside_the_regulated_basket(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """cost 1.00 with a benchmark margin of 25.5% gives a ceiling of 125.5 cents, rounded
    *down* to 125. 1.26 is over it; the same price in an unregulated category is not."""
    over = evaluate(
        propose(
            price=Money.of("1.26"),
            base_price=Money.of("1.40"),
            category_id="dairy",
            benchmark_markup_on_cost=MarkupOnCost(Decimal("25.5")),
        ),
        independent_envelope,
    )
    assert RefusalCode.MARGIN_CAP_EXCEEDED in codes(over)
    assert evaluate(
        propose(
            price=Money.of("1.25"),
            base_price=Money.of("1.40"),
            category_id="dairy",
            benchmark_markup_on_cost=MarkupOnCost(Decimal("25.5")),
        ),
        independent_envelope,
    ).passed
    assert evaluate(
        propose(
            price=Money.of("1.26"),
            base_price=Money.of("1.40"),
            benchmark_markup_on_cost=MarkupOnCost(Decimal("25.5")),
        ),
        independent_envelope,
    ).passed


def test_a_cap_whose_basis_the_instrument_never_stated_is_refused_not_guessed(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """The 2021 Greek measure does not say what the margin is measured on. Borrowing the
    2022 regime's per-unit arithmetic would produce a number that looks right and answers a
    different question, so the window is one this core declines to evaluate."""
    unstated = dataclasses.replace(
        independent_envelope.margin_cap, basis="unspecified_in_the_instrument"
    )
    envelope = dataclasses.replace(independent_envelope, margin_cap=unstated)
    assessment = evaluate(
        propose(category_id="dairy", benchmark_markup_on_cost=MarkupOnCost(Decimal(20))), envelope
    )
    assert RefusalCode.MARGIN_CAP_BASIS_UNEVALUABLE in codes(assessment)


def test_the_benchmark_will_not_take_a_number_that_names_no_denominator(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """The mistake, in the shape it actually arrives in.

    16.81% is the figure Eurostat publishes for Greek supermarkets and it is a margin over
    **turnover** — a fraction of the selling price. `ΥΑ 21330/2026 άρθρο 4 παρ. 4` defines
    the capped margin in the same denominator. The envelope's arithmetic is in the other
    one, and neither of those two numbers was written by whoever wrote this guard: the
    ambiguity was found by reading the instrument the corpus cites, and this is the
    percentage that instrument's own denominator produces.

    Handing it straight in used to be a silently stricter cap. Now it is a refusal, at
    runtime and not only where mypy runs, and the only route through says which way it
    went.
    """
    published_over_the_selling_price = Decimal("16.81")
    with pytest.raises(ProposalError, match="MarginOnPrice"):
        propose(
            category_id="dairy",
            benchmark_markup_on_cost=published_over_the_selling_price,
        )

    converted = MarginOnPrice(published_over_the_selling_price).as_markup_on_cost()
    assert converted.pct.quantize(Decimal("0.01")) == Decimal("20.21")
    assert (
        evaluate(
            propose(category_id="dairy", benchmark_markup_on_cost=converted), independent_envelope
        ).bounds.maximum
        is not None
    )


def test_the_two_denominators_bound_the_price_at_different_places(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """Why the type is worth its weight: the two readings differ by a fifth.

    Against a cost of 1.00 the published margin read as a mark-up caps the price at 1.16;
    read in the denominator its source states, at 1.20. A price of 1.19 is lawful under the
    instrument and refused under the mistake — which fails safe, and is still wrong.
    """
    published = Decimal("16.81")
    at_1_19 = {
        "price": Money.of("1.19"),
        "base_price": Money.of("1.40"),
        "category_id": "dairy",
    }
    misread = evaluate(
        propose(**at_1_19, benchmark_markup_on_cost=MarkupOnCost(published)), independent_envelope
    )
    correct = evaluate(
        propose(**at_1_19, benchmark_markup_on_cost=MarginOnPrice(published).as_markup_on_cost()),
        independent_envelope,
    )
    assert RefusalCode.MARGIN_CAP_EXCEEDED in codes(misread)
    assert RefusalCode.MARGIN_CAP_EXCEEDED not in codes(correct)


def test_a_margin_that_leaves_no_cost_to_mark_up_is_refused_not_computed() -> None:
    """`m / (1 - m)` is undefined at 100% and negative above it. Nothing is invented."""
    with pytest.raises(BenchmarkError, match="leaves no cost"):
        MarginOnPrice(Decimal(100))
    with pytest.raises(BenchmarkError, match="not negative"):
        MarkupOnCost(Decimal(-1))


def test_a_cap_with_no_benchmark_supplied_refuses_rather_than_defaults(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """Doctrine rule 3. A default benchmark would certify a price whose certificate asserts
    a check that never ran."""
    assessment = evaluate(propose(category_id="dairy"), independent_envelope)
    assert RefusalCode.INPUT_NOT_AVAILABLE in codes(assessment)


def test_an_empty_admissible_range_is_donation_or_disposal(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """cost 1.00 puts the margin floor at 113 cents. A 5% benchmark puts the cap's ceiling
    at 105. No price satisfies both, and that is a correct output rather than an error."""
    assessment = evaluate(
        propose(
            price=Money.of("1.10"),
            base_price=Money.of("1.20"),
            category_id="dairy",
            benchmark_markup_on_cost=MarkupOnCost(Decimal(5)),
        ),
        independent_envelope,
    )
    assert RefusalCode.NO_PRICE_SATISFIES_EVERY_GUARDRAIL in codes(assessment)
    assert assessment.bounds.is_empty


# ------------------------------------------------------------------ the cost, and its age


def test_a_model_decision_on_a_stale_cost_is_refused(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """The cost is stale after 6 hours here; this one is 8 hours old."""
    assessment = evaluate(
        propose(cost_known_at=datetime(2026, 4, 1, 6, 0, tzinfo=UTC)), independent_envelope
    )
    assert RefusalCode.COST_STALE in codes(assessment)
    assert assessment.cost_freshness is Freshness.STALE


def test_the_ladder_may_proceed_on_a_stale_cost_because_silence_is_not_safe(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """Doctrine rule 1, at its sharpest. Refusing here would leave the product to be thrown
    away, so the declared safe state proceeds — marked, and with the staleness visible on
    the assessment so it reaches the label, the P&L and the experiment."""
    assessment = evaluate(
        propose(
            source=PriceSource.LADDER,
            marker="FALLBACK_LADDER",
            cost_known_at=datetime(2026, 4, 1, 6, 0, tzinfo=UTC),
        ),
        independent_envelope,
    )
    assert assessment.passed
    assert assessment.cost_freshness is Freshness.STALE


def test_no_cost_at_all_refuses_rather_than_assuming_one(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    assessment = evaluate(propose(unit_cost=None, cost_known_at=None), independent_envelope)
    assert RefusalCode.INPUT_NOT_AVAILABLE in codes(assessment)
    assert assessment.cost_freshness is Freshness.UNKNOWN


# ------------------------------------------------------------------ the prior-price rule


def test_a_perishable_markdown_is_outside_the_prior_price_rule(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """The provision the whole fresh path depends on: inside the exemption there is no
    prior price to state, so the announcement needs none."""
    assessment = evaluate(
        propose(is_perishable=True, announced_as_reduction=True), independent_envelope
    )
    assert assessment.passed
    assert assessment.announcement is not None
    assert assessment.announcement.basis is AnnouncementBasis.PERISHABLE_EXEMPTION
    assert assessment.announcement.prior_price is None


def test_a_non_perishable_reduction_needs_a_prior_price_that_was_really_applied(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    missing = evaluate(propose(announced_as_reduction=True), independent_envelope)
    assert RefusalCode.PRIOR_PRICE_NOT_ESTABLISHED in codes(missing)
    assert missing.announcement is None, "nothing is stated where nothing is established"


def test_a_reduction_announced_against_a_price_that_was_never_higher_is_refused(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    assessment = evaluate(
        propose(
            price=Money.of("2.00"),
            announced_as_reduction=True,
            prior_price=Money.of("1.90"),
        ),
        independent_envelope,
    )
    assert RefusalCode.PRIOR_PRICE_NOT_ESTABLISHED in codes(assessment)


def test_a_real_reduction_carries_the_prior_price_and_the_lookback(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    assessment = evaluate(
        propose(
            price=Money.of("2.00"),
            announced_as_reduction=True,
            prior_price=Money.of("2.50"),
        ),
        independent_envelope,
    )
    assert assessment.passed
    announcement = assessment.announcement
    assert announcement is not None
    assert announcement.basis is AnnouncementBasis.PRIOR_PRICE
    assert announcement.prior_price == Money.of("2.50")
    assert announcement.lookback_days == 30


# ------------------------------------------------------------------ counting what fired


def test_every_guardrail_that_refused_is_reported_not_just_the_first(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """Claim 1's evidence is a count of which guardrails fired. Stopping at the first
    refusal would make that count depend on the order the checks happen to be written in."""
    assessment = evaluate(
        propose(
            price=Money.of("0.05"),
            category_id="tobacco",
            changes_dispatched_today=9,
        ),
        independent_envelope,
    )
    assert {
        GuardrailId.FROZEN_CATEGORIES,
        GuardrailId.FLOOR,
        GuardrailId.MAX_DELTA,
    } <= set(assessment.fired)
    assert len(assessment.refusals) > 3


# ------------------------------------------------------------------ malformed proposals


def test_a_ladder_price_without_its_marker_cannot_be_proposed(
    propose: ProposalFactory,
) -> None:
    """Doctrine rule 2 at the point the marker enters the system."""
    with pytest.raises(ProposalError, match="marker"):
        propose(source=PriceSource.LADDER)


def test_a_model_price_wearing_a_fallback_marker_cannot_be_proposed(
    propose: ProposalFactory,
) -> None:
    with pytest.raises(ProposalError, match="marker"):
        propose(source=PriceSource.MODEL, marker="FALLBACK_LADDER")


def test_a_naive_timestamp_is_refused(propose: ProposalFactory) -> None:
    with pytest.raises(ProposalError, match="timezone"):
        propose(decided_at=datetime(2026, 4, 1, 14, 0))  # noqa: DTZ001


def test_a_decision_may_not_be_judged_by_the_other_path_s_envelope(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """Doctrine rule 1: neither path may inherit the other's answer, and mixing them is a
    wiring error rather than a refusal."""
    base_price_key = DecisionKey(
        path=DecisionPath.BASE_PRICE, sku_id="sku-1", store_id="store-7", occasion=1
    )
    with pytest.raises(EnvelopeError, match="envelope"):
        evaluate(propose(key=base_price_key), independent_envelope)


# ------------------------------------------------------------------ the base-price path


def test_the_base_price_path_is_bound_asymmetrically(
    independent_base_price_envelope: Envelope, propose_base_price: ProposalFactory
) -> None:
    """Against an envelope this repository holds no contract for.

    Numbers: a rise of at most 7.5% and a fall of at most 25% against the week's opening
    price of 2.00. That is a ceiling of 200 + 15 = 215 cents and a floor of 200 - 50 = 150.
    The margin floor sits at 100 + 8% = 108 and the absolute floor at 15, so the weekly
    bound is the one that binds in both directions.
    """

    def at(price: str) -> Assessment:
        return evaluate(propose_base_price(price=Money.of(price)), independent_base_price_envelope)

    assert at("2.15").passed
    assert at("1.50").passed
    assert RefusalCode.BASE_PRICE_MOVE_EXCEEDS_WEEKLY_LIMIT in codes(at("2.16"))
    assert RefusalCode.BASE_PRICE_MOVE_EXCEEDS_WEEKLY_LIMIT in codes(at("1.49"))


def test_the_base_price_bounds_round_outward_on_a_half_cent(
    independent_base_price_envelope: Envelope, propose_base_price: ProposalFactory
) -> None:
    """From an opening price of 1.13, 7.5% is 8.475 cents and 25% is 28.25.

    The ceiling is 121.475, rounded **down** to 121. The floor is 84.75, rounded **up** to
    85. Both bounds move inward, never outward, so the arithmetic can never widen the
    envelope by half a cent. Cost is 0.50 here so the margin floor (54) stays out of the way.
    """

    def at(price: str) -> Assessment:
        return evaluate(
            propose_base_price(
                price=Money.of(price),
                week_opening_price=Money.of("1.13"),
                base_price=Money.of("1.13"),
                unit_cost=Money.of("0.50"),
            ),
            independent_base_price_envelope,
        )

    assert at("1.21").passed
    assert at("0.85").passed
    assert RefusalCode.BASE_PRICE_MOVE_EXCEEDS_WEEKLY_LIMIT in codes(at("1.22"))
    assert RefusalCode.BASE_PRICE_MOVE_EXCEEDS_WEEKLY_LIMIT in codes(at("0.84"))


def test_the_base_price_path_falls_to_no_action_and_never_to_the_ladder(
    independent_base_price_envelope: Envelope, propose_base_price: ProposalFactory
) -> None:
    """Doctrine rule 1 from the other side. For a price increase silence is safe."""
    assessment = evaluate(
        propose_base_price(category_id="spirits"), independent_base_price_envelope
    )
    leading = assessment.leading
    assert leading is not None
    assert leading.code is RefusalCode.CATEGORY_FROZEN
    assert leading.safe_state is SafeState.NO_ACTION
    assert all(r.safe_state is not SafeState.LADDER for r in assessment.refusals)


def test_a_base_price_move_with_no_opening_price_refuses_rather_than_defaults(
    independent_base_price_envelope: Envelope, propose_base_price: ProposalFactory
) -> None:
    assessment = evaluate(
        propose_base_price(week_opening_price=None), independent_base_price_envelope
    )
    assert RefusalCode.INPUT_NOT_AVAILABLE in codes(assessment)


def test_without_the_perishable_exemption_every_reduction_needs_a_prior_price(
    independent_base_price_envelope: Envelope, propose_base_price: ProposalFactory
) -> None:
    """The other branch of the provision the fresh path stands on, exercised against an
    envelope where the exemption is absent — which no window of this repository's
    prior-price contract has been since September 2022."""
    assessment = evaluate(
        propose_base_price(is_perishable=True, announced_as_reduction=True),
        independent_base_price_envelope,
    )
    assert RefusalCode.PRIOR_PRICE_NOT_ESTABLISHED in codes(assessment)
    assert assessment.announcement is None


def test_the_daily_change_budget_is_a_fact_and_not_a_default(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """Doctrine rule 3, in the direction that actually hurts.

    A count that defaulted to zero would mean this guardrail could never refuse anything —
    a default that disarms the check it feeds is worse than no check, because the dashboard
    still shows it as green.
    """
    assessment = evaluate(propose(changes_dispatched_today=None), independent_envelope)
    assert RefusalCode.INPUT_NOT_AVAILABLE in codes(assessment)
    assert GuardrailId.MAX_DELTA in assessment.fired

    # And the same when the field is simply *omitted*, which is the way it actually
    # happens. Asserting only the explicit `None` above left the default itself untested:
    # putting `= 0` back passed every test in this file.
    omitted = ProposedPrice(
        key=DecisionKey(path=DecisionPath.MARKDOWN, sku_id="sku-1", store_id="store-7", occasion=2),
        decided_at=DECIDED_AT,
        price=Money.of("2.00"),
        base_price=Money.of("3.00"),
        category_id="yoghurt",
        source=PriceSource.MODEL,
        is_perishable=False,
        announced_as_reduction=False,
        unit_cost=Money.of("1.00"),
        cost_known_at=datetime(2026, 4, 1, 12, 0, tzinfo=UTC),
    )
    assert omitted.changes_dispatched_today is None, (
        "a count that defaulted to zero would mean this guardrail could never refuse "
        "anything, and nothing anywhere would be red"
    )
    assert RefusalCode.INPUT_NOT_AVAILABLE in codes(evaluate(omitted, independent_envelope))


def test_an_envelope_may_not_be_constructed_across_the_paths(
    independent_envelope: Envelope,
) -> None:
    """Finding 3: doctrine rule 1 was enforced only on the way in from the contracts.

    The public constructor is the door the independent-corpus seam requires an external
    eval to use, so a rule that held only in `envelope_as_of` held on the production path
    and nowhere else — and it is exactly the hand-built envelope, written by someone who
    has not read the module, that would get it wrong.
    """
    ladder_on_the_wrong_path = dataclasses.replace(
        independent_envelope.floor, safe_state=SafeState.LADDER
    )
    with pytest.raises(ValueError, match="ladder"):
        Envelope(
            decided_on=DECIDED_ON,
            path=DecisionPath.BASE_PRICE,
            floor=ladder_on_the_wrong_path,
            max_delta=dataclasses.replace(
                independent_envelope.max_delta, safe_state=SafeState.NO_ACTION
            ),
            frozen_categories=independent_envelope.frozen_categories,
            margin_cap=dataclasses.replace(
                independent_envelope.margin_cap, safe_state=SafeState.NO_ACTION
            ),
            prior_price=dataclasses.replace(
                independent_envelope.prior_price, safe_state=SafeState.NO_ACTION
            ),
        )


def test_the_base_price_path_never_falls_back_to_the_ladder(
    contracts: ContractSet,
) -> None:
    """The same rule on the contract path: a contract that declared `base_price: ladder`
    fails to build an envelope rather than quietly marking down a product nobody asked to
    mark down."""
    floor = contracts.guardrail("floor")
    crossed = dataclasses.replace(
        floor, safe_state=MappingProxyType({"markdown": "ladder", "base_price": "ladder"})
    )
    others = [g for g in contracts.guardrails if g.id != "floor"]
    with pytest.raises(ValueError, match="ladder"):
        envelope_as_of([crossed, *others], on=DECIDED_ON, path=DecisionPath.BASE_PRICE)


# ------------------------------------------------------------ projecting real contracts


def test_the_projection_reads_the_numbers_the_contracts_actually_contain(
    contract_envelope: Envelope,
) -> None:
    assert contract_envelope.floor.minimum_absolute_price == Money.of("0.05")
    assert contract_envelope.floor.minimum_gross_margin_pct == Decimal("0.0")
    assert contract_envelope.floor.cost_staleness_hours == 24
    assert contract_envelope.max_delta.markdown_max_depth_pct == Decimal(70)
    assert contract_envelope.max_delta.markdown_max_changes_per_sku_per_day == 4
    assert contract_envelope.margin_cap.in_force is True
    assert contract_envelope.margin_cap.basis == "per_product_code"
    assert contract_envelope.margin_cap.regulated_category_ids == frozenset(
        {"dairy", "bakery", "poultry"}
    )
    assert contract_envelope.prior_price.perishable_exemption is True
    assert contract_envelope.prior_price.progressive_reduction_window_days == 60


def test_a_decision_is_judged_by_the_window_in_force_when_it_was_taken(
    contracts: ContractSet,
) -> None:
    """The whole reason effective windows exist. `fresh_fish` joins the frozen list in
    November 2025; a decision taken in June 2025 is judged by the list before it,
    permanently."""
    june = envelope_as_of(contracts.guardrails, on=date(2025, 6, 15), path=DecisionPath.MARKDOWN)
    now = envelope_as_of(contracts.guardrails, on=DECIDED_ON, path=DecisionPath.MARKDOWN)
    assert "fresh_fish" not in june.frozen_categories.category_ids
    assert "fresh_fish" in now.frozen_categories.category_ids


def test_a_window_with_no_cap_encoded_leaves_the_basket_unbound(
    contracts: ContractSet,
) -> None:
    """The 2022-2026 hole is a declared statement about what this repository verified. The
    envelope reads it as no cap and does not invent a percentage to fill it."""
    envelope = envelope_as_of(contracts.guardrails, on=date(2025, 6, 1), path=DecisionPath.MARKDOWN)
    assert envelope.margin_cap.in_force is False
    assert envelope.margin_cap.regulated_category_ids == frozenset()
    assert envelope.margin_cap.basis is None


def test_a_partial_envelope_is_refused(contracts: ContractSet) -> None:
    """Four guardrails is not the envelope. A missing one would certify prices against
    checks that were never made."""
    without_floor = [g for g in contracts.guardrails if g.id != "floor"]
    with pytest.raises(EnvelopeError, match="floor"):
        envelope_as_of(without_floor, on=DECIDED_ON, path=DecisionPath.MARKDOWN)


def test_a_date_before_a_timeline_opens_is_refused(contracts: ContractSet) -> None:
    """A decision cannot be judged by a rule that did not exist yet, and reaching for the
    earliest window would be inventing one."""
    with pytest.raises(EnvelopeError, match="no window in force"):
        envelope_as_of(contracts.guardrails, on=date(2019, 1, 1), path=DecisionPath.MARKDOWN)


def test_a_per_product_code_cap_is_evaluated_per_decision_and_that_is_stricter(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """A declared limit, asserted so that it cannot quietly change.

    The 2026 measure compares an aggregate over a product code against the 2025 full-year
    average. This core has no aggregate at decision time — it needs the code's realised
    margin for the period, which is a gold table and not an argument to a pure function —
    so it bounds this decision's own margin instead. That is stricter than the instrument
    requires, and erring toward refusal is the direction this system is built to err in.

    cost 1.00 with a 20% benchmark gives a ceiling of 1.20 under either basis, and the two
    bases are recorded as giving the same bound *today* precisely so that the day they stop
    doing so is a day a test says something.
    """
    per_code = dataclasses.replace(independent_envelope.margin_cap, basis="per_product_code")
    for basis in (independent_envelope.margin_cap, per_code):
        envelope = dataclasses.replace(independent_envelope, margin_cap=basis)
        assessment = evaluate(
            propose(
                price=Money.of("1.21"),
                base_price=Money.of("1.40"),
                category_id="dairy",
                benchmark_markup_on_cost=MarkupOnCost(Decimal(20)),
            ),
            envelope,
        )
        assert RefusalCode.MARGIN_CAP_EXCEEDED in codes(assessment)
        maximum = assessment.bounds.maximum
        assert maximum is not None
        assert maximum.amount == Money.of("1.20")
        assert basis.basis is not None and basis.basis in maximum.why, (
            "the certificate records which basis was applied"
        )
