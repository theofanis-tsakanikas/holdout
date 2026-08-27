"""Fixtures for the core tests, and the seam claim 1 depends on.

Two envelopes, and the difference between them is the point.

`contract_envelope` is this repository's own `contracts/guardrails/`, resolved as of a date
inside the 2026 window. It is what the production path uses and what proves the projection
works.

`independent_envelope` and `independent_base_price_envelope` are built from literal numbers
written here, with the guardrail contracts never opened. They stand in for the eval claim 1
actually needs — one that reads a real chain's published price list and attacks the gates
with what *it* implies. If the only way to build an envelope were a helper that also built
the proposal, that eval would be one function agreeing with itself, and the trap CLAUDE.md
names for claim 1 would be wide open. Every refusal test in `test_envelope.py` runs against
an independent envelope for that reason.

**There are two of them because there are two decision paths.** A review pointed out that
the markdown twin alone left the base-price refusal arithmetic — the asymmetric weekly
bounds — exercised only through `envelope_as_of` over this repository's own contracts,
which is precisely the planter-reads-the-detector's-contract shape claim 1's trap names.
The bounds differ between the two fixtures on purpose, since the paths bound differently
and no test should be able to pass by confusing them.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from holdout.contracts.model import ContractSet, Policy
from holdout.core.decision import DecisionKey, DecisionPath, PriceSource, SafeState
from holdout.core.guardrails import (
    Envelope,
    FloorRule,
    FrozenCategoriesRule,
    MarginCapRule,
    MaxDeltaRule,
    PriorPriceRule,
    ProposedPrice,
    envelope_as_of,
)
from holdout.core.money import Money

#: Inside the 2026 emergency-measure window: a cap in force, measured per product code,
#: benchmarked on the 2025 average. Also inside the ν. 5111/2024 prior-price window, where
#: the perishable exemption is the provision the whole fresh path stands on.
DECIDED_ON = date(2026, 4, 1)
DECIDED_AT = datetime(2026, 4, 1, 14, 0, tzinfo=UTC)


@pytest.fixture
def contract_envelope(contracts: ContractSet) -> Envelope:
    return envelope_as_of(contracts.guardrails, on=DECIDED_ON, path=DecisionPath.MARKDOWN)


@pytest.fixture
def ladder_policy(contracts: ContractSet) -> Policy:
    return next(p for p in contracts.policies if p.id == "ladder_policy")


@pytest.fixture
def independent_envelope() -> Envelope:
    """An envelope nobody in this repository wrote a contract for.

    The numbers are deliberately unlike the ones on disk — a 12.5% margin floor rather than
    zero, a 40% maximum markdown rather than 70% — so that a test passing against this
    envelope cannot be passing because it happens to agree with `contracts/`.
    """
    return Envelope(
        decided_on=DECIDED_ON,
        path=DecisionPath.MARKDOWN,
        floor=FloorRule(
            minimum_gross_margin_pct=Decimal("12.5"),
            minimum_absolute_price=Money.of("0.10"),
            cost_staleness_hours=6,
            refuse_when_no_legal_price_sells=True,
            safe_state=SafeState.LADDER,
        ),
        max_delta=MaxDeltaRule(
            markdown_max_depth_pct=Decimal(40),
            markdown_max_changes_per_sku_per_day=3,
            base_price_max_weekly_increase_pct=Decimal(5),
            base_price_max_weekly_decrease_pct=Decimal(15),
            safe_state=SafeState.LADDER,
        ),
        frozen_categories=FrozenCategoriesRule(
            category_ids=frozenset({"tobacco"}),
            safe_state=SafeState.NO_ACTION,
        ),
        margin_cap=MarginCapRule(
            in_force=True,
            basis="per_unit",
            benchmark="seller_margin_before_2021_09_01",
            regulated_category_ids=frozenset({"dairy"}),
            safe_state=SafeState.LADDER,
        ),
        prior_price=PriorPriceRule(
            perishable_exemption=True,
            lookback_days=30,
            progressive_reduction_window_days=60,
            safe_state=SafeState.LADDER,
        ),
    )


ProposalFactory = Callable[..., ProposedPrice]


@pytest.fixture
def propose() -> ProposalFactory:
    """A markdown proposal with sane defaults, so each test states only what it is about."""

    def make(**overrides: object) -> ProposedPrice:
        fields: dict[str, object] = {
            "key": DecisionKey(
                path=DecisionPath.MARKDOWN, sku_id="sku-1", store_id="store-7", occasion=2
            ),
            "decided_at": DECIDED_AT,
            "price": Money.of("2.00"),
            "base_price": Money.of("3.00"),
            "category_id": "yoghurt",
            "source": PriceSource.MODEL,
            # `ProposedPrice` has no defaults for facts about the world, so the defaults
            # live here, in the test factory, where they are visible to a reader.
            "is_perishable": False,
            "announced_as_reduction": False,
            "changes_dispatched_today": 0,
            "unit_cost": Money.of("1.00"),
            "cost_known_at": datetime(2026, 4, 1, 12, 0, tzinfo=UTC),
        }
        fields.update(overrides)
        return ProposedPrice(**fields)  # type: ignore[arg-type]

    return make


@pytest.fixture
def independent_base_price_envelope() -> Envelope:
    """The base-price twin, and every number in it differs from the markdown one.

    The base-price path bounds asymmetrically against the week's opening price: a rise is
    held tighter than a fall, because a reduction carries its own constraint from the
    prior-price rule while an increase carries none. The safe state is `NO_ACTION`
    throughout — for a price increase silence *is* safe — and `Envelope.__post_init__`
    would refuse this object if it said otherwise.
    """
    return Envelope(
        decided_on=DECIDED_ON,
        path=DecisionPath.BASE_PRICE,
        floor=FloorRule(
            minimum_gross_margin_pct=Decimal("8"),
            minimum_absolute_price=Money.of("0.15"),
            cost_staleness_hours=48,
            refuse_when_no_legal_price_sells=True,
            safe_state=SafeState.NO_ACTION,
        ),
        max_delta=MaxDeltaRule(
            markdown_max_depth_pct=Decimal(40),
            markdown_max_changes_per_sku_per_day=3,
            base_price_max_weekly_increase_pct=Decimal("7.5"),
            base_price_max_weekly_decrease_pct=Decimal(25),
            safe_state=SafeState.NO_ACTION,
        ),
        frozen_categories=FrozenCategoriesRule(
            category_ids=frozenset({"spirits"}),
            safe_state=SafeState.NO_ACTION,
        ),
        margin_cap=MarginCapRule(
            in_force=True,
            basis="per_unit",
            benchmark="seller_margin_before_2021_09_01",
            regulated_category_ids=frozenset({"bakery"}),
            safe_state=SafeState.NO_ACTION,
        ),
        prior_price=PriorPriceRule(
            perishable_exemption=False,
            lookback_days=30,
            progressive_reduction_window_days=None,
            safe_state=SafeState.NO_ACTION,
        ),
    )


@pytest.fixture
def propose_base_price() -> ProposalFactory:
    """A base-price proposal. A different path, so a different factory — sharing one would
    be the crossing doctrine rule 1 forbids, written into the tests."""

    def make(**overrides: object) -> ProposedPrice:
        fields: dict[str, object] = {
            "key": DecisionKey(
                path=DecisionPath.BASE_PRICE, sku_id="sku-1", store_id="store-7", occasion=14
            ),
            "decided_at": DECIDED_AT,
            "price": Money.of("2.00"),
            "base_price": Money.of("2.00"),
            "week_opening_price": Money.of("2.00"),
            "category_id": "yoghurt",
            "source": PriceSource.HUMAN,
            "is_perishable": False,
            "announced_as_reduction": False,
            "unit_cost": Money.of("1.00"),
            "cost_known_at": datetime(2026, 4, 1, 12, 0, tzinfo=UTC),
        }
        fields.update(overrides)
        return ProposedPrice(**fields)  # type: ignore[arg-type]

    return make
