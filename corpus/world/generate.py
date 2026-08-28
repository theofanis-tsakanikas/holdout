"""The simulation. One store at a time, one day at a time, for as long as the scale says.

`CLAUDE.md`, on what the generator produces: *"a synthetic chain — baseline demand by store,
category, hour, weather and season; a non-linear price response with reference-price memory;
cross-price effects between substitutes; stock and per-item expiry; sales censored by
availability; ESL acknowledgements that sometimes fail."* All nine of those are here, and each
one is a named function in `demand.py` or a named step below.

Store-major, and that is load-bearing
-------------------------------------
A store's eight months are simulated end to end before the next store starts, and no draw is
keyed on anything outside that store. Three things follow, and all three are needed:

- **`only_stores` is a window, not a different world.** Generating three stores gives byte-identical
  events for those three, so the scenario-scale world can be inspected without materialising it.
- **Common random numbers hold.** Re-running under all-control redraws the same numbers for every
  store whose policy did not change, so T003's counterfactual differs by the treatment effect and
  by nothing else.
- **Interference has to be built deliberately.** W2's spillover is a function of a neighbour's
  *arm*, never of the neighbour's realised stock — which is enough to break SUTVA, which is the
  whole of that world, and which keeps stores independently generable.

There is no `only_days`, on purpose. Stock, reference prices and the replenishment forecast all
carry across days, so day 200 exists only after days 0 to 199 have happened. A day window would
be a different world wearing the same name, and offering one would be offering a way to be
wrong quietly.
"""

from __future__ import annotations

import math
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from corpus.world import demand, rng
from corpus.world.assignment import Arm, Assignment
from corpus.world.chain import CATEGORY_SHAPE, Chain, Product, Store
from corpus.world.events import EslAck, Event, PosLine, PriceDecision, ShelfDay
from corpus.world.policy import MarkdownPolicy
from corpus.world.scale import CLOSE_HOUR, OPEN_HOUR, Scale
from corpus.world.worlds import BASELINE_ACK_FAILURE_PCT, World

#: How much more than the forecast a store orders. Above 1 there is waste; below it there are
#: stock-outs; at exactly 1 a forecast miss goes one way on one day and the other on the next
#: and neither pathology is reliably present.
SERVICE_FACTOR = 1.30

#: How much of the stock that expires **tonight** the replenishment planner counts as already
#: sold when it nets today's order against what is on the shelf.
#:
#: This one number is where fresh waste comes from, and it is the scenario's flattest
#: assumption about how a real shop is run. A planner that netted expiring stock at face value
#: would order too little and the shelf would look empty by lunchtime; one that ignored it
#: entirely would double up every day. Half is the compromise a category manager makes, and the
#: waste it produces is the thing a markdown ladder exists to reduce — so a corpus that got it
#: to zero would have quietly deleted the treatment's main channel and left the intervention
#: as a price cut with no upside.
EXPIRING_TODAY_CREDIT = 0.5

#: Tills per store, by format. A till is what a basket is rung through, and two baskets at the
#: same till in the same second is the case deduplication must not collapse.
TILLS_BY_FORMAT: dict[str, int] = {"convenience": 3, "supermarket": 8, "hypermarket": 16}

#: Elasticity by category, lifted out of `chain.CATEGORY_SHAPE` once rather than unpacked three
#: million times in the inner loop.
_ELASTICITY: dict[str, float] = {name: shape[4] for name, shape in CATEGORY_SHAPE.items()}


@dataclass(slots=True)
class _SkuState:
    """What carries from one day to the next for one SKU in one store."""

    batches: list[list[int]] = field(default_factory=list)  # [expiry_epoch_hour, qty]
    reference_cents: float = 0.0
    on_hand: int = 0


@dataclass(frozen=True, slots=True)
class _Segment:
    """A stretch of the trading day over which the shelf price does not change.

    Four fields, and it carries `displayed_cents` rather than the decided price because what a
    shopper responds to is what the label says. The decided price and the acknowledgement that
    did or did not accept it are emitted as their own records and are not needed again here —
    a segment holding both would be a second copy of a column that already exists in two
    streams, and the copy is where they would drift apart.
    """

    start_hour: int
    end_hour: int  # exclusive
    step: int
    displayed_cents: int


@dataclass(frozen=True, slots=True)
class StoreExposure:
    """What the seal records per store: how much of the intended price actually reached a shelf.

    This is the evidence claim 2's exposure check is graded against, and it is deliberately an
    aggregate. A per-decision ledger at scenario scale would be tens of millions of rows, and
    nothing that reads the seal needs one: the question the seal answers is *what fraction of
    this store's price changes reached a label*, and the answer is two integers.
    """

    store_id: str
    arm: str
    decisions: int
    acks_accepted: int
    acks_failed: int
    treated_neighbours: int


def _epoch_hour(moment: datetime) -> int:
    return int(moment.timestamp()) // 3600


def _segments(
    policy: MarkdownPolicy,
    base_price_cents: int,
    expiry_hour: int,
    day_open_hour_abs: int,
) -> list[tuple[int, int, int, int, int]]:
    """The day's price schedule as (start_hour, end_hour, step, price, hours_to_expiry).

    Computed from the rung thresholds rather than by walking sixteen hours and asking each one,
    because at scenario scale that walk is 47 million questions with the same four answers.
    """
    out: list[tuple[int, int, int, int, int]] = []
    boundaries: list[tuple[int, int]] = [(OPEN_HOUR, 0)]
    for rung in policy.steps:
        crossing = expiry_hour - rung.hours_to_expiry_at_most - day_open_hour_abs + OPEN_HOUR
        hour = max(OPEN_HOUR, min(CLOSE_HOUR, crossing))
        if hour < CLOSE_HOUR:
            boundaries.append((hour, rung.step))
    # Two rungs can cross inside the same hour on a short shelf life; the deeper one wins,
    # because the shop does not put the shallower label back on.
    deepest: dict[int, int] = {}
    for hour, step in sorted(boundaries):
        deepest[hour] = max(deepest.get(hour, 0), step)
    ordered = sorted(deepest.items())
    for index, (hour, step) in enumerate(ordered):
        end = ordered[index + 1][0] if index + 1 < len(ordered) else CLOSE_HOUR
        if end <= hour:
            continue
        hours_left = expiry_hour - (day_open_hour_abs - OPEN_HOUR + hour)
        price, _ = policy.price_cents(base_price_cents, float(hours_left))
        out.append((hour, end, step, price, hours_left))
    return out


def _pulls_trade(control: MarkdownPolicy, treatment: MarkdownPolicy) -> Arm:
    """Which arm's shelf a shopper crosses the road for.

    Derived from the two schedules rather than assumed, and this is the second time in this
    package that assuming would have been wrong. The candidate in `policy.candidate` cuts
    *shallower* than the ladder it replaces, so trade crosses **toward the control store**,
    not away from it — the opposite of what the first version of this function hard-coded. A
    world whose interference points the wrong way still breaks SUTVA and would still have been
    detected, which is exactly why nothing would have caught it.

    Ties go to control: if the two schedules cut equally deep there is nothing to cross the
    road for, and the caller has already established that `spillover_pct` is non-zero.
    """
    depth = sum(step.depth_pct for step in treatment.steps)
    return Arm.TREATMENT if depth > sum(step.depth_pct for step in control.steps) else Arm.CONTROL


def _spillover(
    world: World,
    arm: Arm,
    treated_neighbours: int,
    control_neighbours: int,
    pulling: Arm,
) -> float:
    """W2's demand multiplier for this store, and 1.0 in every other world.

    A store beside a neighbour on the *other* arm, where that other arm is the one cutting
    deeper, loses `spillover_pct` of its trade to it; the store on the pulling side gains half
    of that. Both are functions of the **neighbour's arm**, which is exactly what makes them
    interference: a unit's outcome depends on another unit's assignment, and no difference of
    arm means what it says any more.

    **It applies all day, not only during the marked-down hours.** That is the stronger
    reading and the deliberate one. A shopper who has learned that the shop across the road
    marks down harder moves their habitual shop, not just their late-evening trip — the
    generator already carries that kind of memory at the price level, and confining the
    spillover to the markdown segments would have made it a rounding error rather than the
    thing a contamination check has to catch.

    The gain is half the loss rather than all of it, because trade that crosses the road is
    not the only thing that happens — some of it simply does not get bought. Nothing rests on
    the halving; what rests on the mechanism is that it is *there*, and that the readout has
    to notice.
    """
    if world.spillover_pct == 0:
        return 1.0
    share = world.spillover_pct / 100.0
    on_the_other_side = control_neighbours if pulling is Arm.TREATMENT else treated_neighbours
    on_the_pulling_side = treated_neighbours if pulling is Arm.TREATMENT else control_neighbours
    if arm is pulling:
        return 1.0 + share / 2.0 if on_the_other_side else 1.0
    return 1.0 - share if on_the_pulling_side else 1.0


def _forecast_units(product: Product, store: Store, business_date: date) -> float:
    """The chain's own naive forecast — and it is naive on purpose.

    Popularity, store size, day of week and season: four things a replenishment planner has
    on the morning of the order. Not weather, and not the markdown that has not happened yet.
    So a hot Saturday sells out and a wet Tuesday is thrown away, which is where both
    censoring and waste come from — rather than from a random number drawn to produce them.
    """
    return (
        demand.BASE_LINES_PER_SKU_DAY
        * product.popularity
        * store.size_index
        * demand.DOW_FACTOR[business_date.weekday()]
        * demand.season_factor(business_date.timetuple().tm_yday)
        * 1.35  # units per line, on average, in the ordinary worlds
    )


def _emit_store(
    *,
    world: World,
    seed: str,
    scale: Scale,
    chain: Chain,
    store: Store,
    arm: Arm,
    control: MarkdownPolicy,
    treatment: MarkdownPolicy,
    treated_neighbours: int,
    control_neighbours: int,
    pulling: Arm,
) -> Iterator[Event | StoreExposure]:
    """One store's whole history. Yields events, then its `StoreExposure` last."""
    policy = treatment if arm is Arm.TREATMENT else control
    # A label fails on the control arm too — batteries go flat wherever the store is. What W3
    # raises is the *treated* rate, so that assignment and exposure come apart on the arm where
    # coming apart dilutes the estimate.
    ack_failure_pct = (
        world.ack_failure_pct_treated if arm is Arm.TREATMENT else BASELINE_ACK_FAILURE_PCT
    )
    spillover = _spillover(world, arm, treated_neighbours, control_neighbours, pulling)
    tills = TILLS_BY_FORMAT[store.store_format]
    products = chain.products
    state = {p.sku_id: _SkuState(reference_cents=float(p.base_price_cents)) for p in products}
    decisions = accepted = failed = 0

    for day_index in range(scale.days):
        business_date = scale.start_date + timedelta(days=day_index)
        iso_date = business_date.isoformat()
        day_open = datetime.combine(business_date, datetime.min.time()) + timedelta(hours=OPEN_HOUR)
        day_open_abs = _epoch_hour(day_open)
        weather = demand.weather_index(seed, store.store_id, iso_date)
        day_factor = demand.DOW_FACTOR[business_date.weekday()] * demand.season_factor(
            business_date.timetuple().tm_yday
        )
        novelty = (
            demand.novelty_factor(day_index, world.novelty_boost_pct, world.novelty_half_life_days)
            if arm is Arm.TREATMENT
            else 1.0
        )
        # W5, and 1.0 everywhere else. One heavy-tailed multiplier for the whole store-day.
        # It does not know which arm the store is in, so it makes the world wilder without
        # making the intervention look different.
        #
        # **The replenishment planner sees it and the analyst does not**, which is the whole
        # point and was worth one wrong version to learn. Applied to demand alone it produced
        # a world that loses money: a mean-one multiplicative shock against a fixed order is
        # censored on every big day and wasted on every small one, and W5's mean margin came
        # out at minus nine euros a store-week. That is not a world with more variance in it,
        # it is a different and broken world. A shop that knows a bank holiday is coming
        # orders for it; what nobody knows in advance is how a *store-week* built out of seven
        # such days will land, and that is the variance a power calculation assumes away.
        #
        # **And it begins half way through the world**, which is the second thing one wrong
        # version taught. A pathology present in the history a design is sized on is not
        # "variance far above what the power calculation assumed" — it is variance the
        # calculation assumed, and the engine refuses the design at moment 1 rather than
        # letting the readout notice. W5's row says the power check fails or the interval is
        # honestly wide, and a design refusal is neither. So the quiet half is what a
        # calculation is sized on and the wild half is what the experiment runs in, which is
        # the sentence the row was always making.
        shock = (
            demand.store_day_shock(seed, store.store_id, iso_date, world.demand_tail_alpha)
            if day_index >= scale.days // 2
            else 1.0
        )

        schedules: dict[str, list[_Segment]] = {}
        discounts: dict[str, float] = {}
        delivered: dict[str, int] = {}
        sold: dict[str, int] = {product.sku_id: 0 for product in products}
        stocked_out: dict[str, int | None] = dict.fromkeys(sold, None)
        tonight = _epoch_hour(
            datetime.combine(business_date, datetime.min.time()) + timedelta(hours=CLOSE_HOUR)
        )

        # ---- pass one: deliver, decide, dispatch to the labels ----------------------
        for product in products:
            sku = product.sku_id
            st = state[sku]
            counted = math.fsum(
                float(qty) if expiry > tonight else EXPIRING_TODAY_CREDIT * qty
                for expiry, qty in st.batches
            )
            order = max(
                0,
                math.ceil(_forecast_units(product, store, business_date) * shock * SERVICE_FACTOR)
                - int(counted),
            )
            if order:
                expiry = _epoch_hour(
                    datetime.combine(
                        business_date + timedelta(days=product.shelf_life_days),
                        datetime.min.time(),
                    )
                    + timedelta(hours=CLOSE_HOUR)
                )
                st.batches.append([expiry, order])
                st.on_hand += order
            delivered[sku] = order
            if not st.batches:
                # Reachable only if a forecast ever rounds to nothing, which the arithmetic
                # above does not currently allow. If it ever does, a shelf that is empty from
                # the moment the doors open is a stock-out from the moment the doors open, and
                # it is recorded as one rather than left blank.
                schedules[sku] = []
                discounts[sku] = 0.0
                stocked_out[sku] = OPEN_HOUR
                continue

            oldest = st.batches[0][0]
            raw = _segments(policy, product.base_price_cents, oldest, day_open_abs)
            segments: list[_Segment] = []
            previous_displayed = product.base_price_cents
            weighted = 0.0
            for start, end, step, price, hours_left in raw:
                if step == 0:
                    segments.append(_Segment(start, end, 0, price))
                    previous_displayed = price
                    weighted += (end - start) * (1.0 - price / product.base_price_cents)
                    continue
                decisions += 1
                ts = day_open + timedelta(hours=start - OPEN_HOUR)
                fails = (
                    rng.unit_interval(seed, "ack", store.store_id, sku, iso_date, step) * 100.0
                    < ack_failure_pct
                )
                displayed = previous_displayed if fails else price
                if fails:
                    failed += 1
                else:
                    accepted += 1
                yield PriceDecision(
                    store_id=store.store_id,
                    sku_id=sku,
                    event_ts=ts,
                    arrival_ts=ts,
                    arm=arm.value,
                    policy_id=policy.policy_id,
                    ladder_step=step,
                    base_price_cents=product.base_price_cents,
                    price_decided_cents=price,
                    hours_to_expiry=hours_left,
                )
                yield EslAck(
                    store_id=store.store_id,
                    sku_id=sku,
                    event_ts=ts,
                    arrival_ts=ts,
                    price_decided_cents=price,
                    price_displayed_cents=displayed,
                    accepted=not fails,
                    policy_id=policy.policy_id,
                    ladder_step=step,
                )
                segments.append(_Segment(start, end, step, displayed))
                previous_displayed = displayed
                weighted += (end - start) * (1.0 - displayed / product.base_price_cents)
            schedules[sku] = segments
            discounts[sku] = weighted / (CLOSE_HOUR - OPEN_HOUR)

        # ---- pass two: what shoppers did about it -----------------------------------
        lines: list[tuple[int, int, str, int, int]] = []  # (hour, tick, sku, qty, price)

        for product in products:
            sku = product.sku_id
            st = state[sku]
            segments = schedules[sku]
            if not segments:
                continue
            cross = (
                demand.cross_price_factor(discounts.get(product.substitute_of, 0.0))
                if product.substitute_of
                else 1.0
            )
            base_rate = (
                demand.BASE_LINES_PER_SKU_DAY
                * product.popularity
                * store.size_index
                * day_factor
                * demand.weather_factor(product.category, weather)
                * cross
                * spillover
                * shock
            )
            draw = rng.stream(seed, "sales", store.store_id, sku, iso_date)
            for segment in segments:
                width = segment.end_hour - segment.start_hour
                share = math.fsum(
                    demand.HOURLY_PROFILE[hour - OPEN_HOUR]
                    for hour in range(segment.start_hour, segment.end_hour)
                )
                rate = (
                    base_rate
                    * share
                    * demand.price_factor(
                        segment.displayed_cents,
                        st.reference_cents,
                        _ELASTICITY[product.category],
                    )
                    * (novelty if segment.step else 1.0)
                )
                # The hours are drawn and then **sorted**, so the shelf empties at the hour it
                # actually empties. Serving the segment's baskets in draw order instead would
                # put the stock-out at a random hour inside the segment, and the column that
                # records it is the one claim 4 is going to be graded on.
                arrivals = sorted(
                    segment.start_hour + int(draw.random() * width)
                    for _ in range(rng.poisson(draw, rate))
                )
                for hour in arrivals:
                    wanted = demand.units_on_line(draw)
                    if st.on_hand <= 0:
                        if stocked_out[sku] is None:
                            stocked_out[sku] = hour
                        break
                    units = min(wanted, st.on_hand)
                    _consume(st, units)
                    sold[sku] += units
                    lines.append((hour, draw.randrange(3600), sku, units, segment.displayed_cents))
                if st.on_hand <= 0 and stocked_out[sku] is None and arrivals:
                    stocked_out[sku] = arrivals[-1]

        # ---- baskets, receipts and the twin ------------------------------------------
        yield from _receipts(seed, store, iso_date, business_date, tills, lines, state, sold)

        # ---- close the day: expire, waste, remember ---------------------------------
        expiry_cut = _epoch_hour(
            datetime.combine(business_date, datetime.min.time()) + timedelta(hours=CLOSE_HOUR)
        )
        opened_at = datetime.combine(business_date, datetime.min.time())
        for product in products:
            sku = product.sku_id
            st = state[sku]
            wasted = 0
            kept: list[list[int]] = []
            for batch in st.batches:
                if batch[0] <= expiry_cut:
                    wasted += batch[1]
                else:
                    kept.append(batch)
            st.batches = kept
            st.on_hand -= wasted
            segments = schedules[sku]
            closing_price = segments[-1].displayed_cents if segments else product.base_price_cents
            st.reference_cents = demand.updated_reference(st.reference_cents, closing_price)
            yield ShelfDay(
                store_id=store.store_id,
                sku_id=sku,
                business_date=iso_date,
                delivered_qty=delivered[sku],
                sold_qty=sold.get(sku, 0),
                wasted_qty=wasted,
                closing_qty=st.on_hand,
                stocked_out_from_hour=stocked_out.get(sku),
                unit_cost_cents=chain.cost_as_of(sku, opened_at),
            )

    yield StoreExposure(
        store_id=store.store_id,
        arm=arm.value,
        decisions=decisions,
        acks_accepted=accepted,
        acks_failed=failed,
        treated_neighbours=treated_neighbours,
    )


def _consume(state: _SkuState, units: int) -> None:
    """First expired, first out — which is what a shop actually does with fresh."""
    left = units
    while left and state.batches:
        batch = state.batches[0]
        take = min(batch[1], left)
        batch[1] -= take
        left -= take
        if batch[1] == 0:
            state.batches.pop(0)
    state.on_hand -= units - left


def _receipts(
    seed: str,
    store: Store,
    iso_date: str,
    business_date: date,
    tills: int,
    lines: list[tuple[int, int, str, int, int]],
    state: dict[str, _SkuState],
    sold: dict[str, int],
) -> Iterator[PosLine]:
    """Group the day's lines into baskets and give each basket a real transaction id.

    The id is a business key from the source — a till and a running receipt number — and
    emphatically not a hash of the payload. `CLAUDE.md` is explicit about why: two identical
    baskets in the same second at the same till are two events, and a payload hash would
    collapse them into one. So the world produces that case deliberately, at a declared rate,
    rather than waiting for a scale at which it happens by chance.
    """
    if not lines:
        return
    lines.sort()
    draw = rng.stream(seed, "receipts", store.store_id, iso_date)
    receipt = 0
    index = 0
    while index < len(lines):
        size = min(demand.lines_in_basket(draw), len(lines) - index)
        basket = lines[index : index + size]
        index += size
        receipt += 1
        till = f"T{draw.randrange(tills) + 1:02d}"
        hour, tick = basket[0][0], basket[0][1]
        moment = datetime.combine(business_date, datetime.min.time()) + timedelta(
            hours=hour, seconds=tick
        )
        transaction = f"{store.store_id}-{iso_date}-{till}-{receipt:06d}"
        for line_no, (_, _, sku, qty, price) in enumerate(basket, start=1):
            yield PosLine(
                transaction_id=transaction,
                line_no=line_no,
                store_id=store.store_id,
                sku_id=sku,
                till_id=till,
                event_ts=moment,
                arrival_ts=moment,
                qty=qty,
                unit_price_cents=price,
                line_total_cents=qty * price,
            )
        if draw.random() * 10_000 >= demand.TWIN_BASKETS_PER_10K:
            continue
        if any(state[sku].on_hand < qty for _, _, sku, qty, _ in basket):
            continue
        receipt += 1
        twin = f"{store.store_id}-{iso_date}-{till}-{receipt:06d}"
        for line_no, (_, _, sku, qty, price) in enumerate(basket, start=1):
            _consume(state[sku], qty)
            sold[sku] += qty
            yield PosLine(
                transaction_id=twin,
                line_no=line_no,
                store_id=store.store_id,
                sku_id=sku,
                till_id=till,
                event_ts=moment,
                arrival_ts=moment,
                qty=qty,
                unit_price_cents=price,
                line_total_cents=qty * price,
            )


def generate(
    world: World,
    *,
    seed: str,
    scale: Scale,
    chain: Chain,
    assignment: Assignment,
    control: MarkdownPolicy,
    treatment: MarkdownPolicy,
    only_stores: Sequence[str] | None = None,
) -> Iterator[Event | StoreExposure]:
    """Every event the world produces, store by store, in generation order.

    Not in event-time order: interleaving a hundred stores into one timeline is the ingest
    driver's job (T009), which is also where lateness and duplicates are injected. A generator
    that ordered by time would be deciding what "late" means in a second place.

    The `StoreExposure` records are yielded among the events and are **not** part of the
    corpus. `run()` in `__init__.py` separates them and seals them; a caller that consumes this
    function directly is holding the exposure truth in its hand and should not be.
    """
    missing = [s.store_id for s in chain.stores if s.store_id not in assignment]
    if missing:
        raise ValueError(
            f"{len(missing)} stores have no arm ({missing[:3]}...). A store with no arm would "
            "quietly take the control path and silently shrink the experiment."
        )
    if world.is_aa and control.policy_id != treatment.policy_id:
        raise ValueError(
            f"{world.id} is the A/A world: both arms get the same policy and nothing is "
            f"applied. Got {control.policy_id!r} against {treatment.policy_id!r}."
        )
    pulling = _pulls_trade(control, treatment)
    wanted = set(only_stores) if only_stores is not None else None
    for store in chain.stores:
        if wanted is not None and store.store_id not in wanted:
            continue
        neighbours = chain.neighbours_of(store.store_id)
        treated_neighbours = sum(1 for n in neighbours if assignment[n] is Arm.TREATMENT)
        yield from _emit_store(
            world=world,
            seed=seed,
            scale=scale,
            chain=chain,
            store=store,
            arm=assignment[store.store_id],
            control=control,
            treatment=treatment,
            treated_neighbours=treated_neighbours,
            control_neighbours=len(neighbours) - treated_neighbours,
            pulling=pulling,
        )
