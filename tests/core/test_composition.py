"""The modules against each other, because two correct modules can still disagree.

This file exists because a review found the branch delivering `ladder/` and `guardrails/`
and never running one into the other. Both were right on their own terms and they disagreed
by a cent: the ladder rounded its quote half-to-even, the envelope's max-depth bound rounded
up, and at rung 4 of `ladder_policy@v1` — 70% off, three hours from expiry — every base
price ending in five cents produced a ladder price the guardrail set **refused**.

That is the declared safe state of the primary decision path failing, which is the one thing
doctrine rule 1 exists to prevent. One in five base prices, at the rung that matters most,
and every unit test passed.

The rule this file is written to enforce, from here on: **no module in `core/` is tested
only alone.** A property that holds inside a module and breaks between two of them is
exactly what a suite of well-isolated unit tests cannot see.

Unlike `test_envelope.py`, these tests deliberately use *this repository's* contracts. The
question here is not whether the gates are right — that is claim 1 and it is attacked from an
independent envelope — but whether our ladder and our envelope, compiled from the same
contract directory, agree. `tests/contracts/test_guardrails.py` already asserts the
percentage version of that (`max(step.depth_pct) <= markdown_max_depth_pct`); this is the
cent-level version, and the cent is where it broke.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from holdout.contracts.model import ContractSet, Policy
from holdout.core.decision import DecisionKey, DecisionPath, PriceSource
from holdout.core.guardrails import (
    CertifiedPrice,
    Envelope,
    ProposedPrice,
    Refusal,
    certified,
    certify,
    dispatch_to_shelf,
    envelope_as_of,
)
from holdout.core.ladder import quote
from holdout.core.money import Money
from holdout.core.pricing import Scenario, select

DECIDED_ON = date(2026, 4, 1)
DECIDED_AT = datetime(2026, 4, 1, 14, 0, tzinfo=UTC)
COST_KNOWN_AT = datetime(2026, 4, 1, 12, 0, tzinfo=UTC)

#: Every rung of `ladder_policy@v1`, named by minutes to expiry, plus one past expiry.
RUNGS = (1440, 1200, 720, 600, 360, 240, 180, 30, 0)

#: Base prices covering all ten cent endings, and every five-cent ending twice over, since
#: a half-cent in a 70% markdown is exactly what broke.
BASE_PRICES = tuple(
    Money(cents)
    for cents in (
        *range(20, 60),
        *range(95, 135),
        199,
        200,
        215,
        333,
        445,
        555,
        665,
        775,
        885,
        999,
        1005,
        1115,
    )
)


@pytest.fixture
def markdown_envelope(contracts: ContractSet) -> Envelope:
    return envelope_as_of(contracts.guardrails, on=DECIDED_ON, path=DecisionPath.MARKDOWN)


def _propose(price: Money, base: Money, *, step: int, marker: str) -> ProposedPrice:
    """A fallback proposal. Cost is zero so that the margin floor stays out of the way and
    the max-depth bound is the one under test."""
    return ProposedPrice(
        key=DecisionKey(
            path=DecisionPath.MARKDOWN, sku_id="sku-1", store_id="store-7", occasion=step
        ),
        decided_at=DECIDED_AT,
        price=price,
        base_price=base,
        category_id="yoghurt",
        source=PriceSource.LADDER,
        marker=marker,
        is_perishable=True,
        announced_as_reduction=False,
        changes_dispatched_today=0,
        unit_cost=Money(0),
        cost_known_at=COST_KNOWN_AT,
    )


# ------------------------------------------------------------------ the safe state holds


@pytest.mark.parametrize("minutes", RUNGS)
def test_the_ladder_never_produces_a_price_the_envelope_refuses(
    minutes: int, markdown_envelope: Envelope, ladder_policy: Policy
) -> None:
    """The regression. Every rung, every cent ending.

    A safe state that the guardrail set refuses is not a safe state — for an expiring
    product the alternative to a markdown is disposal, so "refuse and fall back" has
    nowhere left to fall.
    """
    refused: list[str] = []
    for base in BASE_PRICES:
        quoted = quote(minutes, base_price=base, policy=ladder_policy)
        if quoted is None:
            continue
        result = certify(
            _propose(quoted.price, base, step=quoted.step, marker=quoted.marker),
            markdown_envelope,
        )
        if isinstance(result, Refusal):
            refused.append(
                f"base {base} rung {quoted.step} quoted {quoted.price} -> {result.code.value}"
            )
    assert not refused, (
        "the declared safe state of the markdown path produced prices the envelope refused:\n  "
        + "\n  ".join(refused)
    )


def test_the_ladder_quote_equals_the_envelope_s_own_max_depth_bound_at_the_deepest_rung(
    markdown_envelope: Envelope, ladder_policy: Policy
) -> None:
    """Stronger than "not refused", and the property that actually has to hold.

    The deepest rung of the ladder is 70% and the envelope's maximum markdown depth is 70%,
    so at rung 4 the schedule's price *is* the bound. They are computed by different code
    from different contracts, and they must land on the same cent — including when 30% of
    the base is a half-cent. Both round the same way for the same reason: a markdown price
    rounded down is a deeper markdown, and a lower bound rounded down is not a bound.
    """
    mismatched: list[str] = []
    for base in BASE_PRICES:
        quoted = quote(180, base_price=base, policy=ladder_policy)
        assert quoted is not None and quoted.step == 4
        assessment_bound = None
        result = certify(
            _propose(quoted.price, base, step=4, marker=quoted.marker), markdown_envelope
        )
        bounds = result.bounds
        for bound in bounds.lower:
            if bound.rule_id == "markdown_max_depth_pct":
                assessment_bound = bound.amount
        if assessment_bound != quoted.price:
            mismatched.append(f"base {base}: ladder {quoted.price} vs bound {assessment_bound}")
    assert not mismatched, "\n  ".join(mismatched)


@pytest.mark.parametrize("cents", [5, 6, 10, 15, 19])
def test_a_ladder_price_below_the_absolute_floor_is_clamped_and_then_certifies(
    cents: int, markdown_envelope: Envelope, ladder_policy: Policy
) -> None:
    """The other half of the composition: where the schedule genuinely goes too low.

    On a very cheap item the deepest rung falls under the absolute floor of 0.05. The
    contract's answer is `clamp_to_floor`, so the caller passes the envelope's floor into
    `quote` and the clamped price certifies — the ladder still never refuses, and the
    clamping is visible on the quote so an experiment cannot mistake it for the schedule.
    """
    base = Money(cents)
    floor = markdown_envelope.floor.minimum_absolute_price
    quoted = quote(180, base_price=base, policy=ladder_policy, floor=floor)
    assert quoted is not None
    result = certify(_propose(quoted.price, base, step=4, marker=quoted.marker), markdown_envelope)
    assert isinstance(result, CertifiedPrice), result
    assert quoted.price >= floor


# --------------------------------------------------- the whole path, end to end, once


def test_model_to_selection_to_guardrails_to_actuator(markdown_envelope: Envelope) -> None:
    """The order CLAUDE.md declares: model, then selection, then guardrails, then dispatch.

    Worked by hand. Cost 1.20, eight on the shelf, three candidate prices. At 2.00 three
    sell and five are wasted: 600 - 360 - 600 = -360. At 1.50 six sell and two are wasted:
    900 - 720 - 240 = -60. At 1.00 all eight sell below cost: 800 - 960 = -160. The middle
    price loses least, and 1.50 is inside the envelope, so it certifies and dispatches.
    """
    selection = select(
        [
            Scenario(price=Money.of("2.00"), expected_units=Decimal(3)),
            Scenario(price=Money.of("1.50"), expected_units=Decimal(6)),
            Scenario(price=Money.of("1.00"), expected_units=Decimal(12)),
        ],
        unit_cost=Money.of("1.20"),
        remaining_stock=Decimal(8),
    )
    assert selection.price == Money.of("1.50")
    assert selection.chosen.contribution == Money(-60)

    key = DecisionKey(path=DecisionPath.MARKDOWN, sku_id="sku-1", store_id="store-7", occasion=2)
    result = certify(
        ProposedPrice(
            key=key,
            decided_at=DECIDED_AT,
            price=selection.price,
            base_price=Money.of("2.00"),
            category_id="yoghurt",
            source=PriceSource.MODEL,
            is_perishable=True,
            announced_as_reduction=False,
            changes_dispatched_today=0,
            unit_cost=Money.of("1.20"),
            cost_known_at=COST_KNOWN_AT,
        ),
        markdown_envelope,
    )
    assert isinstance(result, CertifiedPrice)
    assert certified(result)
    assert dispatch_to_shelf(result, key).price == Money.of("1.50")
    assert result.marker is None, "a model decision carries no fallback marker"


def test_a_selected_price_the_envelope_refuses_falls_to_the_ladder_and_that_certifies(
    markdown_envelope: Envelope, ladder_policy: Policy
) -> None:
    """The composition doctrine rule 1 is actually about.

    The model's best scenario is below cost, the envelope refuses it, and the refusal
    declares `LADDER`. The ladder then answers, and its answer certifies — so the path
    always has one. A refusal whose safe state produced another refusal would be an outage
    dressed as a decision.
    """
    selection = select(
        [Scenario(price=Money.of("0.80"), expected_units=Decimal(20))],
        unit_cost=Money.of("1.20"),
        remaining_stock=Decimal(8),
    )
    key = DecisionKey(path=DecisionPath.MARKDOWN, sku_id="sku-1", store_id="store-7", occasion=4)
    refused = certify(
        ProposedPrice(
            key=key,
            decided_at=DECIDED_AT,
            price=selection.price,
            base_price=Money.of("2.00"),
            category_id="yoghurt",
            source=PriceSource.MODEL,
            is_perishable=True,
            announced_as_reduction=False,
            changes_dispatched_today=0,
            unit_cost=Money.of("1.20"),
            cost_known_at=COST_KNOWN_AT,
        ),
        markdown_envelope,
    )
    assert isinstance(refused, Refusal)
    assert refused.safe_state.value == "ladder"

    quoted = quote(180, base_price=Money.of("2.00"), policy=ladder_policy)
    assert quoted is not None
    fallback = certify(
        _propose(quoted.price, Money.of("2.00"), step=quoted.step, marker=quoted.marker),
        markdown_envelope,
    )
    assert isinstance(fallback, CertifiedPrice), fallback
    assert fallback.marker == "FALLBACK_LADDER"
