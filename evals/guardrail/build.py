"""Turn the public corpus into decisions this system would have had to take.

This is the only module that imports both sides. `corpus/real/` knows nothing about a
guardrail and `holdout.core` knows nothing about the ONS; the join lives here, in the eval,
where it can be read as one thing.

What comes from the corpus, and what does not
---------------------------------------------
Three inputs the guardrails need are simply not public, anywhere, and inventing them is
what doctrine rule 3 forbids. They are handled differently from the prices, and the
difference is stated rather than blurred:

===========================  ==========================================================
observed                     every price, every base price, every prior price, every
                             week-opening price, the regulated-category list, the
                             industry gross margin
---------------------------  ----------------------------------------------------------
derived, arithmetic stated   the unit cost — the item's median shelf price across the
                             corpus, less the published margin. `MANIFEST.yaml` argues
                             the derivation and which way it errs
---------------------------  ----------------------------------------------------------
**swept**, not claimed       how old the cost is, how many changes have already been
                             dispatched today, and whether a decision announces a
                             reduction. No public source carries these for a real
                             retailer. The eval does not guess a value: it walks a
                             **declared grid** of them, so every branch is entered and
                             none of them is presented as a fact about the world
===========================  ==========================================================

The unit cost is derived from the item's **median price across the whole corpus**, not from
the row's own price. That matters more than it looks. A cost derived from the row's own
price would make the margin identical on every row, and the margin floor would answer the
same question 32,480 times. Deriving it from the item makes the *real dispersion between
811 outlets* drive the margin: the cheap outlet is selling near or below cost and the dear
one is not, which is both what happens in a real chain and the only way this corpus can
exercise the floor at all. About a fifth of the rows land below the derived cost.

Currency
--------
The ONS collects in pounds and the scenario prices in euros. The numeric value is used as
an amount of euros, unconverted. That is a stated modelling choice, not an oversight, and
it costs nothing here: four of the five guardrails are percentages and therefore
scale-free, and the fifth — the €0.05 absolute floor — sits an order of magnitude below the
cheapest quote in the corpus. A conversion would add a rate that changes daily and would
buy no additional proof.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from functools import lru_cache
from itertools import pairwise

from corpus.real import Item, Quote, items, median_gross_margin_fraction, quotes

from holdout.contracts.loader import load
from holdout.core.decision import DecisionKey, DecisionPath, PriceSource, SafeState
from holdout.core.guardrails import (
    Envelope,
    FloorRule,
    FrozenCategoriesRule,
    MarginCapRule,
    MarginOnPrice,
    MarkupOnCost,
    MaxDeltaRule,
    PriorPriceRule,
    ProposedPrice,
    envelope_as_of,
)
from holdout.core.money import Money

#: Inside the 2026 emergency-measure window — ΠΝΠ 11.03.2026, in force to 30.06.2026 — so
#: the contract envelope built for this date carries a margin cap that binds.
CAP_IN_FORCE_ON = date(2026, 4, 1)

#: After the measure lapsed on its own terms. The same contracts resolve to an envelope
#: with no cap, and the eval runs both: a gate that is only ever exercised in the
#: configuration where it fires has not been shown to stay quiet when it should.
CAP_LAPSED_ON = date(2026, 7, 15)

#: The scenario's frozen categories, from `contracts/guardrails/frozen_categories.yaml` as
#: of a date in the second window. Named here only so the eval can *say which corpus items
#: it expects to be refused*; the refusal itself is decided by the envelope, never by this.
FROZEN_IN_SCENARIO = frozenset({"tobacco", "spirits", "infant_formula", "pharmacy", "fresh_fish"})

#: The declared sweep over the inputs no public source carries. Deterministic — indexed by
#: position, never drawn at random — so a red run reproduces exactly.
COST_AGE_HOURS_GRID: tuple[int, ...] = (1, 12, 30)
#: `4` is here on purpose and equals the change budget of two of the envelopes below. A
#: budget guardrail is an inequality, and the only input that tells `>=` from `>` is the one
#: that lands exactly on the bound.
CHANGES_DISPATCHED_GRID: tuple[int, ...] = (0, 3, 4, 7)


@dataclass(frozen=True, slots=True)
class Case:
    """One decision the system is asked to take, and where every number in it came from."""

    family: str
    envelope_id: str
    envelope: Envelope
    proposal: ProposedPrice
    unit_cost: Money
    origin: str
    """Traceable back to the corpus rows, so a counterexample can be looked up by hand."""

    item: Item


# ------------------------------------------------------------------------- derived inputs


@lru_cache(maxsize=1)
def unit_costs() -> dict[str, Money]:
    """One derived cost per ONS item — the median shelf price, less the published margin.

    `median_low` and not `median`: the low median of an even-length series is a price that
    was actually observed, where the ordinary median would be the average of two and could
    land on a half-cent that no shop ever charged. `Money.of` refuses a third decimal place
    rather than rounding it, so this is not a matter of taste — an averaged median would
    raise, and rounding it here would be a decision hidden inside a helper.

    The final `as_price`, half-to-even, because a cost is an input rather than a bound: it
    is not protecting anything, so there is no side for a half-cent to fall toward. The
    bounds computed *from* it round in their own declared directions.
    """
    margin = median_gross_margin_fraction()
    prices: dict[str, list[Decimal]] = defaultdict(list)
    for quote in quotes():
        prices[quote.item_id].append(quote.price)
    return {
        item_id: Money.as_price(
            Decimal(Money.of(statistics.median_low(values)).cents) * (Decimal(1) - margin)
        )
        for item_id, values in prices.items()
    }


@lru_cache(maxsize=1)
def _corpus() -> tuple[tuple[Quote, ...], dict[str, Item]]:
    return tuple(quotes()), items()


def corpus_items() -> dict[str, Item]:
    return _corpus()[1]


@lru_cache(maxsize=1)
def _by_item_and_outlet() -> dict[tuple[str, str], dict[str, Quote]]:
    """Every quote indexed by product, outlet and month — the real price history."""
    index: dict[tuple[str, str], dict[str, Quote]] = defaultdict(dict)
    for quote in _corpus()[0]:
        index[(quote.item_id, quote.outlet)][quote.quote_month] = quote
    return index


def _decided_at(month: str) -> datetime:
    """Mid-month, mid-afternoon, in UTC. The day within the month is not in the source."""
    return datetime(int(month[:4]), int(month[4:]), 15, 14, 0, tzinfo=UTC)


def _regulated_scenario_categories() -> frozenset[str]:
    """Which of this scenario's categories ΥΑ 21330/2026 άρθρο 6 actually reaches.

    Decided from the **decision's own table**, through the ordinal recorded for each item in
    `corpus/real/data/item_categories.csv`, and never from
    `contracts/guardrails/regulated_basket.yaml` — which names three categories and declares
    them an assumption, because when it was written the decision had not been obtained.
    """
    _, catalogue = _corpus()
    return frozenset(item.scenario_category for item in catalogue.values() if item.is_regulated)


# ----------------------------------------------------------------------------- envelopes


def _sweep_envelope(
    envelope_id: str,
    *,
    path: DecisionPath,
    margin_floor_pct: str,
    absolute_floor: str,
    staleness_hours: int,
    markdown_depth_pct: str,
    change_budget: int,
    weekly_rise_pct: str,
    weekly_fall_pct: str,
    cap_in_force: bool,
    perishable_exemption: bool,
    cap_basis: str = "per_product_code",
) -> tuple[str, Envelope]:
    """One point of the declared grid.

    These numbers are **not** claims about any retailer. They exist so that claim 1 is not
    demonstrated at a single point of the parameter space: an envelope's arithmetic that
    happens to be right for a 0% margin floor and wrong for a 25% one is wrong, and only a
    sweep finds that. The regulated categories, in contrast, are real — they come from the
    Greek decision through the corpus.
    """
    safe = SafeState.LADDER if path is DecisionPath.MARKDOWN else SafeState.NO_ACTION
    return envelope_id, Envelope(
        decided_on=CAP_IN_FORCE_ON,
        path=path,
        floor=FloorRule(
            minimum_gross_margin_pct=Decimal(margin_floor_pct),
            minimum_absolute_price=Money.of(absolute_floor),
            cost_staleness_hours=staleness_hours,
            refuse_when_no_legal_price_sells=True,
            safe_state=safe,
        ),
        max_delta=MaxDeltaRule(
            markdown_max_depth_pct=Decimal(markdown_depth_pct),
            markdown_max_changes_per_sku_per_day=change_budget,
            base_price_max_weekly_increase_pct=Decimal(weekly_rise_pct),
            base_price_max_weekly_decrease_pct=Decimal(weekly_fall_pct),
            safe_state=safe,
        ),
        frozen_categories=FrozenCategoriesRule(
            category_ids=FROZEN_IN_SCENARIO,
            safe_state=SafeState.NO_ACTION,
        ),
        margin_cap=MarginCapRule(
            in_force=cap_in_force,
            basis=cap_basis,
            benchmark="average_gross_margin_2025",
            regulated_category_ids=_regulated_scenario_categories(),
            safe_state=safe,
        ),
        prior_price=PriorPriceRule(
            perishable_exemption=perishable_exemption,
            lookback_days=30,
            progressive_reduction_window_days=60,
            safe_state=safe,
        ),
    )


@lru_cache(maxsize=1)
def envelopes() -> dict[str, Envelope]:
    """Every envelope the corpus is driven through, contract-derived and swept.

    The two `contract.*` entries are what the production path would use, resolved from this
    repository's own `contracts/guardrails/` — attacking those with the corpus is the test
    that matters. The `sweep.*` entries answer the separate question of whether the
    machinery is right across the parameter space or only at the point on disk.
    """
    guardrails = load().guardrails
    built: dict[str, Envelope] = {
        "contract.markdown.cap_in_force": envelope_as_of(
            guardrails, on=CAP_IN_FORCE_ON, path=DecisionPath.MARKDOWN
        ),
        "contract.markdown.cap_lapsed": envelope_as_of(
            guardrails, on=CAP_LAPSED_ON, path=DecisionPath.MARKDOWN
        ),
        "contract.base_price.cap_in_force": envelope_as_of(
            guardrails, on=CAP_IN_FORCE_ON, path=DecisionPath.BASE_PRICE
        ),
    }
    for envelope_id, envelope in (
        _sweep_envelope(
            "sweep.markdown.tight",
            path=DecisionPath.MARKDOWN,
            margin_floor_pct="25",
            absolute_floor="0.20",
            staleness_hours=6,
            markdown_depth_pct="30",
            change_budget=2,
            weekly_rise_pct="5",
            weekly_fall_pct="15",
            cap_in_force=True,
            perishable_exemption=True,
        ),
        _sweep_envelope(
            "sweep.markdown.slack",
            path=DecisionPath.MARKDOWN,
            margin_floor_pct="0",
            absolute_floor="0.01",
            staleness_hours=72,
            markdown_depth_pct="90",
            change_budget=99,
            weekly_rise_pct="50",
            weekly_fall_pct="50",
            cap_in_force=False,
            perishable_exemption=False,
        ),
        _sweep_envelope(
            "sweep.markdown.binding",
            path=DecisionPath.MARKDOWN,
            # Every number here is chosen so that a rule which the other envelopes never
            # give anything to refuse has something to refuse. An absolute floor above the
            # cheapest real quotes, a depth bound tighter than real month-to-month moves,
            # and a change budget the declared sweep exceeds. Claim 1's evidence is a count
            # of which guardrails fired, and a guardrail that never fires contributes
            # nothing to it — `G8.every-refusal-code-is-reached` is what makes that a build
            # failure rather than a footnote.
            margin_floor_pct="0",
            # High enough to sit **above** the derived cost of the cheaper items, which is
            # the whole reason it is not 0.05. With a margin floor of 0% the two lower bounds
            # are the cost and this, and if this one is always the lower of the two then
            # removing it entirely changes nothing anyone can observe — a gate can only be
            # shown to bite where it is the gate that refuses. `gate-proof`'s
            # `absolute-floor-is-not-applied` survived at 0.50 for exactly that reason.
            absolute_floor="1.50",
            staleness_hours=72,
            markdown_depth_pct="5",
            change_budget=1,
            weekly_rise_pct="10",
            weekly_fall_pct="20",
            cap_in_force=False,
            perishable_exemption=True,
        ),
        _sweep_envelope(
            "sweep.markdown.unevaluable_cap",
            path=DecisionPath.MARKDOWN,
            # The 2021 regime, in the shape `docs/REGULATORY.md` records it: ν. 4818/2021
            # άρθρο 58 imposes a cap and never says what the margin is measured on.
            # `docs/DECISIONS.md` notes that window is unreachable through `envelope_as_of`,
            # because the other three guardrails only open in 2025 — so the branch that
            # refuses rather than borrowing a neighbouring regime's arithmetic is live code
            # nothing drives. Here it is driven, by real prices.
            margin_floor_pct="0",
            absolute_floor="0.05",
            staleness_hours=24,
            markdown_depth_pct="70",
            change_budget=4,
            weekly_rise_pct="10",
            weekly_fall_pct="20",
            cap_in_force=True,
            perishable_exemption=True,
            cap_basis="unspecified_in_the_instrument",
        ),
        _sweep_envelope(
            "sweep.base_price.tight",
            path=DecisionPath.BASE_PRICE,
            margin_floor_pct="12.5",
            absolute_floor="0.15",
            staleness_hours=24,
            markdown_depth_pct="70",
            change_budget=4,
            weekly_rise_pct="2",
            weekly_fall_pct="3",
            cap_in_force=True,
            perishable_exemption=False,
        ),
    ):
        built[envelope_id] = envelope
    return built


def markdown_envelopes() -> dict[str, Envelope]:
    return {k: v for k, v in envelopes().items() if v.path is DecisionPath.MARKDOWN}


def base_price_envelopes() -> dict[str, Envelope]:
    return {k: v for k, v in envelopes().items() if v.path is DecisionPath.BASE_PRICE}


# --------------------------------------------------------------------------- the families


def _markdown_proposal(
    *,
    index: int,
    key_occasion: int,
    quote: Quote,
    item: Item,
    base_price: Money,
    price: Money,
    announced: bool,
    prior_price: Money | None,
) -> tuple[ProposedPrice, Money]:
    cost = unit_costs()[quote.item_id]
    decided_at = _decided_at(quote.quote_month)
    age = COST_AGE_HOURS_GRID[index % len(COST_AGE_HOURS_GRID)]
    dispatched = CHANGES_DISPATCHED_GRID[index % len(CHANGES_DISPATCHED_GRID)]
    proposal = ProposedPrice(
        key=DecisionKey(
            path=DecisionPath.MARKDOWN,
            sku_id=quote.item_id,
            store_id=quote.outlet,
            occasion=key_occasion,
        ),
        decided_at=decided_at,
        price=price,
        base_price=base_price,
        category_id=item.scenario_category,
        source=PriceSource.MODEL,
        is_perishable=item.scenario_category in {"dairy", "bakery", "poultry", "fresh_fish"},
        announced_as_reduction=announced,
        unit_cost=cost,
        cost_known_at=decided_at.replace(hour=14) - timedelta(hours=age),
        changes_dispatched_today=dispatched,
        prior_price=prior_price,
        benchmark_markup_on_cost=sector_wide_benchmark(),
    )
    return proposal, cost


@lru_cache(maxsize=1)
def sector_wide_benchmark_on_price() -> MarginOnPrice:
    """The corpus's derived benchmark level, in the denominator its source publishes it in.

    **A sector median over 2008-2020, standing in for a quantity no public dataset contains.**
    Eurostat's figure is a margin over an industry's **turnover**; ΥΑ 21330/2026 άρθρο 4 παρ. 4
    defines the capped margin over the **selling price** of one product code, and άρθρο 4
    παρ. 5 fixes the period as the trader's own last closed financial year of 2025. Both are
    selling-side denominators, which is why one can stand in for the other in a synthetic
    corpus; they are not the same quantity and this is not the instrument's level.

    What the type buys is the half that can be got right: the number arrives in the
    denominator its publisher used, nothing here converts it, so nothing here can convert it
    wrongly. `contracts/guardrails/regulated_basket.yaml` keeps the contract's own benchmark
    symbolic and sourced to the instrument, so a figure this repository derived never stands in
    a contract as the law's.

    *Restated 2026-08-31.* This docstring opened *"The published 2025 gross margin"*, which is
    wrong on both words that matter — it is neither 2025 nor published as a benchmark by
    anybody — at the point in the tree closest to the arithmetic. See `docs/FINDINGS.md`.
    """
    return MarginOnPrice(median_gross_margin_fraction() * 100)


@lru_cache(maxsize=1)
def sector_wide_benchmark() -> MarkupOnCost:
    """The same sector figure in the denominator the envelope's arithmetic is in.

    **It takes no argument and that is the point.** The core's `ProposedPrice` carries a
    benchmark per proposal and `envelope.py` bounds each decision against its own, so the shape
    the instrument requires — a benchmark per product code — is already there. What is flat is
    this corpus: one sector level for all 232,373 decisions, because no public dataset contains
    a per-undertaking, per-code cost and nothing that can be rebuilt from published sources ever
    will.

    *Named rather than shaped, and the alternatives were both disguises.* Computing a per-code
    margin from the corpus's own derived cost returns `m` exactly for every code — `cost =
    price x (1 - m)` is that identity — so it would manufacture per-code numbers that are the
    flat number wearing a disguise. And a per-item signature returning one constant everywhere
    would manufacture per-code *structure* around a single number, which is the same disguise in
    the other direction. Both would look like fidelity. A name cannot: a reader of the four call
    sites below sees `sector_wide_benchmark()` and cannot make the inference that produced the
    2026-08-27 finding. If a real per-item benchmark ever arrives, it arrives as a real change
    against a name that never lied.

    The conversion is `m / (1 - m)` and it happens in exactly one place, in the core's own
    `MarginOnPrice.as_markup_on_cost`. That the eval calls the core's converter rather than
    writing a second one is deliberate and is *not* a second implementation: the quantity
    being checked here is the envelope's bound, and the converter is an input to it, on the
    same footing as the rule values the eval reads out of the contract. What the type buys
    is that the number cannot arrive in the wrong denominator by accident — 16.81% of the
    price is 20.21% of the cost, and the field will not take the first.
    """
    return sector_wide_benchmark_on_price().as_markup_on_cost()


def observed_price_moves() -> Iterator[Case]:
    """Family M1 and B1 — a price a retailer actually moved, one month to the next.

    The same product in the same outlet, in two consecutive months of the corpus. Offered to
    the markdown path as a reduction from the earlier price, and to the base-price path as a
    move against the week's opening price. Nothing about the pair is constructed: both
    numbers were collected in a shop.
    """
    catalogue = corpus_items()
    index = 0
    for (item_id, _outlet), history in sorted(_by_item_and_outlet().items()):
        item = catalogue[item_id]
        months = sorted(history)
        for earlier, later in pairwise(months):
            previous, current = history[earlier], history[later]
            index += 1
            base = Money.of(previous.price)
            price = Money.of(current.price)
            for envelope_id, envelope in markdown_envelopes().items():
                proposal, cost = _markdown_proposal(
                    index=index,
                    key_occasion=1,
                    quote=current,
                    item=item,
                    base_price=base,
                    price=price,
                    announced=False,
                    prior_price=None,
                )
                yield Case(
                    family="M1",
                    envelope_id=envelope_id,
                    envelope=envelope,
                    proposal=proposal,
                    unit_cost=cost,
                    origin=f"{item_id}@{current.outlet} {earlier}->{later} {previous.price}->{current.price}",
                    item=item,
                )
            for envelope_id, envelope in base_price_envelopes().items():
                cost = unit_costs()[item_id]
                decided_at = _decided_at(current.quote_month)
                proposal = ProposedPrice(
                    key=DecisionKey(
                        path=DecisionPath.BASE_PRICE,
                        sku_id=item_id,
                        store_id=current.outlet,
                        occasion=1,
                    ),
                    decided_at=decided_at,
                    price=price,
                    base_price=base,
                    week_opening_price=base,
                    category_id=item.scenario_category,
                    source=PriceSource.HUMAN,
                    is_perishable=False,
                    announced_as_reduction=False,
                    unit_cost=cost,
                    cost_known_at=decided_at
                    - timedelta(hours=COST_AGE_HOURS_GRID[index % len(COST_AGE_HOURS_GRID)]),
                    benchmark_markup_on_cost=sector_wide_benchmark(),
                )
                yield Case(
                    family="B1",
                    envelope_id=envelope_id,
                    envelope=envelope,
                    proposal=proposal,
                    unit_cost=cost,
                    origin=f"{item_id}@{current.outlet} {earlier}->{later} {previous.price}->{current.price}",
                    item=item,
                )


def announced_reductions() -> Iterator[Case]:
    """Family A1 — a real reduction, announced on the label.

    Only pairs where the price actually fell, so the announcement is about something that
    happened. `prior_price` is the lowest price this corpus saw for the same product in the
    same outlet in any earlier month — an upper bound on the thirty-day lowest that Art. 6a
    of Directive 98/6/EC defines, which makes announcing against it at least as hard as
    announcing against the real one.
    """
    catalogue = corpus_items()
    index = 0
    for (item_id, _outlet), history in sorted(_by_item_and_outlet().items()):
        item = catalogue[item_id]
        months = sorted(history)
        for position, month in enumerate(months):
            if position == 0:
                continue
            current = history[month]
            earlier = [history[m].price for m in months[:position]]
            lowest = min(earlier)
            if current.price >= lowest:
                continue
            index += 1
            for envelope_id, envelope in markdown_envelopes().items():
                proposal, cost = _markdown_proposal(
                    index=index,
                    key_occasion=2,
                    quote=current,
                    item=item,
                    base_price=Money.of(max(earlier)),
                    price=Money.of(current.price),
                    announced=True,
                    prior_price=Money.of(lowest),
                )
                yield Case(
                    family="A1",
                    envelope_id=envelope_id,
                    envelope=envelope,
                    proposal=proposal,
                    unit_cost=cost,
                    origin=f"{item_id}@{current.outlet} {month} {current.price} announced vs prior {lowest}",
                    item=item,
                )


def announced_non_reductions() -> Iterator[Case]:
    """Family A2 — a reduction announced against a price that was never higher.

    Real rows, and the practice Art. 6a of Directive 98/6/EC exists to stop: the price went
    **up**, and the label says it came down. Nothing is fabricated — the two prices are both
    from a shop and the corpus is simply read the other way round. The envelope must refuse
    with `PRIOR_PRICE_NOT_ESTABLISHED`, and only the envelopes that do not take the
    perishable derogation can be asked the question at all, since inside the derogation
    there is no prior price to be wrong about.
    """
    catalogue = corpus_items()
    index = 0
    envelopes_without_the_derogation = {
        envelope_id: envelope
        for envelope_id, envelope in markdown_envelopes().items()
        if not envelope.prior_price.perishable_exemption
    }
    if not envelopes_without_the_derogation:
        return
    for (item_id, _outlet), history in sorted(_by_item_and_outlet().items()):
        item = catalogue[item_id]
        months = sorted(history)
        for position, month in enumerate(months):
            if position == 0:
                continue
            current = history[month]
            lowest = min(history[m].price for m in months[:position])
            if current.price < lowest:
                continue
            index += 1
            for envelope_id, envelope in envelopes_without_the_derogation.items():
                proposal, cost = _markdown_proposal(
                    index=index,
                    key_occasion=3,
                    quote=current,
                    item=item,
                    base_price=Money.of(current.price),
                    price=Money.of(current.price),
                    announced=True,
                    prior_price=Money.of(lowest),
                )
                yield Case(
                    family="A2",
                    envelope_id=envelope_id,
                    envelope=envelope,
                    proposal=proposal,
                    unit_cost=cost,
                    origin=(
                        f"{item_id}@{current.outlet} {month} {current.price} announced as a "
                        f"reduction against a prior price of {lowest}"
                    ),
                    item=item,
                )


def missing_inputs() -> Iterator[Case]:
    """Family N1 — a real price, with an input the operational store did not supply.

    Doctrine rule 3 from the other side. A cost the ERP has not published, and a
    week-opening price the pricing system has not written yet, are ordinary Tuesday
    conditions in a real chain; they are not error states. The envelope must refuse with
    `INPUT_NOT_AVAILABLE` rather than reading the missing number as zero — which, for the
    daily change budget, would mean the guardrail could never fire at all.

    One row per month per envelope rather than the whole corpus: the question is whether the
    branch is taken, and taking it thirty thousand times says nothing the first time did not.
    """
    catalogue = corpus_items()
    first_of_month: dict[str, Quote] = {}
    for row in _corpus()[0]:
        first_of_month.setdefault(row.quote_month, row)

    for month, row in sorted(first_of_month.items()):
        item = catalogue[row.item_id]
        decided_at = _decided_at(month)
        for envelope_id, envelope in markdown_envelopes().items():
            # Two variants, and they are separate on purpose. A decision missing *both* the
            # cost and the change count is refused twice over, so removing either refusal
            # leaves the other one standing and a gate that had stopped biting would look
            # exactly like a gate that still does. One missing input at a time is the only
            # way each refusal is the one that decides the answer.
            for missing, cost, dispatched in (
                ("no cost", None, 0),
                ("no change count", unit_costs()[row.item_id], None),
            ):
                yield Case(
                    family="N1",
                    envelope_id=envelope_id,
                    envelope=envelope,
                    proposal=ProposedPrice(
                        key=DecisionKey(
                            path=DecisionPath.MARKDOWN,
                            sku_id=row.item_id,
                            store_id=row.outlet,
                            occasion=4,
                        ),
                        decided_at=decided_at,
                        price=Money.of(row.price),
                        base_price=Money.of(row.price),
                        category_id=item.scenario_category,
                        source=PriceSource.MODEL,
                        is_perishable=True,
                        announced_as_reduction=False,
                        # Absent rather than zero, which is the whole point.
                        unit_cost=cost,
                        cost_known_at=decided_at if cost is not None else None,
                        changes_dispatched_today=dispatched,
                        benchmark_markup_on_cost=sector_wide_benchmark(),
                    ),
                    unit_cost=unit_costs()[row.item_id],
                    origin=f"{row.item_id}@{row.outlet} {month} with {missing}",
                    item=item,
                )
        for envelope_id, envelope in base_price_envelopes().items():
            yield Case(
                family="N1",
                envelope_id=envelope_id,
                envelope=envelope,
                proposal=ProposedPrice(
                    key=DecisionKey(
                        path=DecisionPath.BASE_PRICE,
                        sku_id=row.item_id,
                        store_id=row.outlet,
                        occasion=4,
                    ),
                    decided_at=decided_at,
                    price=Money.of(row.price),
                    base_price=Money.of(row.price),
                    week_opening_price=None,
                    category_id=item.scenario_category,
                    source=PriceSource.HUMAN,
                    is_perishable=False,
                    announced_as_reduction=False,
                    unit_cost=unit_costs()[row.item_id],
                    cost_known_at=decided_at,
                    benchmark_markup_on_cost=sector_wide_benchmark(),
                ),
                unit_cost=unit_costs()[row.item_id],
                origin=f"{row.item_id}@{row.outlet} {month} with no week-opening price",
                item=item,
            )


def all_cases() -> Iterator[Case]:
    yield from observed_price_moves()
    yield from announced_reductions()
    yield from announced_non_reductions()
    yield from missing_inputs()
