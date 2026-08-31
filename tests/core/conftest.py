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
from fractions import Fraction

import pytest

from holdout.contracts.model import ContractSet, InferenceSettings, Metric, Policy
from holdout.contracts.windows import resolve_as_of
from holdout.core.decision import DecisionKey, DecisionPath, PriceSource, SafeState
from holdout.core.design import (
    DecisionRule,
    DesignForm,
    DesignRefusal,
    Feasible,
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
    assess,
)
from holdout.core.experiment import CovariateKind, CovariateMatrix
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
            refuse_when_no_price_satisfies_every_guardrail=True,
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
            refuse_when_no_price_satisfies_every_guardrail=True,
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


# --------------------------------------------------------------- the experiment core

#: A roster shaped so that the re-randomisation screen actually accepts something.
#:
#: This is not a convenience, it is a measured fact, and `test_assignment.py` measures it:
#: at the declared tolerance of 0.10 standardised differences over the contract's five
#: covariates, a **20% holdout on an unstructured roster of 100 stores accepts roughly one
#: draw in a thousand**. The arithmetic is not mysterious — the standardised difference has
#: a spread of about `sqrt(1/n_T + 1/n_C)`, which is 0.25 at 80 against 20, so each of the
#: seven comparisons passes about 31% of the time and seven of them pass about 0.03% of the
#: time.
#:
#: A roster in identical blocks accepts far more often, because many splits land on exactly
#: the same block counts and score zero. Two blocks of forty at a 20% share accepts roughly
#: one draw in four, so the whole path — including a reference set of ninety-nine draws — runs
#: in under a second.
#:
#: **Eighty rather than forty**, because the granularity of the control arm is what decides
#: whether the screen can ever accept. A binary covariate split evenly needs the two arms'
#: proportions within 0.05 of each other, and a control arm of seven can only take
#: proportions in steps of 1/7 = 0.143 — so a forty-store roster with one store excluded is
#: not merely unlucky, it is **arithmetically unbalanceable**, and four tests here failed
#: for that reason before the size moved. That is a real property of the declared tolerance
#: and not a quirk of the fixture; the wider consequence is a deferral in
#: `docs/DECISIONS.md`.
#:
#: Every covariate is a function of the block, so the estimator's design matrix has rank two
#: and three of its five columns are dropped as dependent. That is deliberate here — it
#: exercises the column-dropping path on every composition run — and it is why a *richer*
#: adjustment, where the covariates actually carry information, is built by hand in
#: `test_estimator.py` rather than taken from this fixture.
BLOCKS = 2
ROSTER_SIZE = 80

#: A seed a session committed to, spelled out so a reader can see there is nothing in it.
COMMITTED_SEED = "holdout-t001-committed-seed"


@pytest.fixture
def inference(contracts: ContractSet) -> InferenceSettings:
    return contracts.inference


@pytest.fixture
def covariate_kinds(contracts: ContractSet) -> tuple[CovariateKind, ...]:
    return tuple(CovariateKind(c.type) for c in contracts.balance_covariates.covariates)


def blocked_rows(size: int, blocks: int) -> dict[str, tuple[Fraction | str, ...]]:
    """`size` units in `blocks` groups, identical inside a group.

    The columns are in `contracts/design/balance_covariates.yaml`'s declared order —
    category revenue, format, selling area, waste rate, pricing zone — because the engine
    refuses a matrix whose columns are not exactly the contract's, in exactly that order.
    """
    formats = ("hypermarket", "supermarket", "convenience")
    zones = ("zone_north", "zone_south")
    rows: dict[str, tuple[Fraction | str, ...]] = {}
    for index in range(size):
        block = index % blocks
        rows[f"store-{index:03d}"] = (
            Fraction(10_000 + 500 * block),
            formats[block % len(formats)],
            Fraction(800 + 100 * block),
            Fraction(3 + block, 100),
            zones[block % len(zones)],
        )
    return rows


@pytest.fixture
def matrix(contracts: ContractSet, covariate_kinds: tuple[CovariateKind, ...]) -> CovariateMatrix:
    return CovariateMatrix.of(
        contracts.balance_covariates.ids,
        covariate_kinds,
        blocked_rows(ROSTER_SIZE, BLOCKS),
    )


@pytest.fixture
def roster(matrix: CovariateMatrix) -> tuple[str, ...]:
    return matrix.units


@pytest.fixture
def metric(contracts: ContractSet) -> Metric:
    """The metric in force, resolved as of the same date the envelopes are."""
    versions = contracts.metric_versions("category_margin_per_store_week")
    resolved = resolve_as_of(versions, DECIDED_ON)
    assert resolved is not None
    return resolved


DesignFormFactory = Callable[..., DesignForm]


@pytest.fixture
def design_form() -> DesignFormFactory:
    """A well-formed design, so each test states only the field it is about."""

    def make(**overrides: object) -> DesignForm:
        fields: dict[str, object] = {
            "hypothesis": (
                "Deeper early markdowns on fresh dairy raise category margin per store-week."
            ),
            "intervention": Intervention(treatment="ladder_policy@v1", control="ladder_policy@v1"),
            "scope": Scope(categories=("dairy",), products=None, stores=None),
            "primary_metric": "category_margin_per_store_week",
            "unit": Unit.STORE,
            "mde": Mde(kind=MdeKind.ABSOLUTE, value=Decimal(3000), direction=MdeDirection.EITHER),
            "max_duration": MaxDuration(weeks=8),
            "exclusions": (),
            "decision_rule": DecisionRule(
                if_significant="Roll the treatment ladder out to every fresh category.",
                if_not_significant="Keep the existing ladder and close the experiment.",
                if_refused="Re-run next quarter with a wider window and a fresh roster.",
            ),
            "filled_by": FilledBy(kind=FilledByKind.AGENT),
        }
        fields.update(overrides)
        return DesignForm(**fields)  # type: ignore[arg-type]

    return make


AssessFactory = Callable[..., "Feasible | DesignRefusal"]


@pytest.fixture
def assess_design(
    contracts: ContractSet,
    inference: InferenceSettings,
    metric: Metric,
    matrix: CovariateMatrix,
    roster: tuple[str, ...],
    design_form: DesignFormFactory,
) -> AssessFactory:
    """`assess` with every argument defaulted to something admissible.

    Each test overrides exactly the one it is about, so a refusal in a test is traceable to
    the one thing that test changed rather than to the six it did not.
    """

    def run(**overrides: object) -> Feasible | DesignRefusal:
        form = overrides.pop("form", None) or design_form()
        arguments: dict[str, object] = {
            "experiment_id": "exp-t001",
            "seed": COMMITTED_SEED,
            "metric": metric,
            "metric_ids": contracts.metric_ids,
            "covariates": contracts.balance_covariates,
            "inference": inference,
            "roster": roster,
            "matrix": matrix,
            "variance_per_unit_week": Decimal(1_000_000),
            "mean_per_unit_week": Decimal(40_000),
            "committed_elsewhere": frozenset(),
            "neighbour_pairs": (),
            "stopping": StoppingRule(kind=StoppingKind.SINGLE_READOUT_AT_END),
            "previously_locked": None,
        }
        arguments.update(overrides)
        return assess(form, **arguments)  # type: ignore[arg-type]

    return run
