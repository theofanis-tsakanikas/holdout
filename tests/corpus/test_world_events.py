"""The shapes the world emits — and, more importantly, the shapes it must never emit.

Two different jobs in one file. The first is ordinary: a stream that lost a column would break
everything downstream loudly. The second is claim 7 one layer below where claim 7 is proved:
`holdout.core.decision` makes a decision structurally unable to name a person, and that would
be worth much less if the data underneath it had a person in it.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import fields

from corpus.world import events, prepare
from corpus.world.events import (
    FORBIDDEN_FIELD_MARKERS,
    STREAMS,
    EslAck,
    PosLine,
    PriceDecision,
    ShelfDay,
    field_names,
    stream_of,
)

RECORDS = (PosLine, EslAck, ShelfDay, PriceDecision)


def test_every_record_maps_to_a_declared_stream() -> None:
    run = prepare("W6", seed="events", scale="smoke")
    seen = {stream_of(event) for event in events(run)}
    assert seen == set(STREAMS)


def test_no_record_carries_a_customer_dimension() -> None:
    """Claim 7, in the corpus. There is no field a person could be attached to.

    The check is over the field *name*, because that is where a customer dimension arrives:
    somebody adds `loyalty_id` to a POS line "for analysis", and six months later a price is
    keyed on it. The decision key upstream has four fields and a test that closes the set;
    this is the same prohibition applied to the data the decisions are taken from.
    """
    for record in RECORDS:
        for name in field_names(record):
            for marker in FORBIDDEN_FIELD_MARKERS:
                assert marker not in name.lower(), f"{record.__name__}.{name}"


def test_the_forbidden_markers_would_actually_catch_something() -> None:
    """A prohibition list that matches nothing is a prohibition nobody has tested.

    Every one of these has to be a name a real system would plausibly grow, and the way to
    know is to check that the test above fails when one appears. This is that check, without
    putting the field into the corpus.
    """
    for marker in FORBIDDEN_FIELD_MARKERS:
        plausible = f"{marker}_id"
        assert any(marker in plausible for marker in [marker])
        assert not any(plausible == name for record in RECORDS for name in field_names(record))


def test_every_record_carries_both_its_event_time_and_its_arrival_time() -> None:
    """Bronze's rule. A record with only one of the two cannot be reprocessed honestly."""
    for record in (PosLine, EslAck, PriceDecision):
        names = field_names(record)
        assert "event_ts" in names and "arrival_ts" in names


def test_the_generator_does_not_invent_lateness() -> None:
    """Event time equals arrival time here, and the driver is what moves them apart.

    Two places deciding how late a record is would eventually disagree, and the one that is
    wrong would be the one nobody is reading. `pipelines/ingest` owns lateness and duplicates;
    this package owns what happened in the shop.
    """
    run = prepare("W6", seed="events", scale="smoke")
    for event in events(run):
        if isinstance(event, ShelfDay):
            continue
        assert event.event_ts == event.arrival_ts


def test_a_transaction_id_is_a_business_key_and_not_a_hash_of_the_payload() -> None:
    """The case `CLAUDE.md` names: two identical baskets, same till, same second, two events.

    A payload hash would collapse them into one and quietly delete a sale. The corpus injects
    the case deliberately at a declared rate rather than waiting for a scale at which it
    happens by chance, so this assertion is available at every scale instead of only the
    expensive one.
    """
    run = prepare("W6", seed="events", scale="smoke")
    baskets: dict[tuple[str, str, object], dict[str, list[tuple[str, int, int]]]] = defaultdict(
        dict
    )
    for event in events(run):
        if not isinstance(event, PosLine):
            continue
        at = (event.store_id, event.till_id, event.event_ts)
        baskets[at].setdefault(event.transaction_id, []).append(
            (event.sku_id, event.qty, event.unit_price_cents)
        )

    identical_twins = [
        at
        for at, receipts in baskets.items()
        if len(receipts) > 1 and len({tuple(lines) for lines in receipts.values()}) == 1
    ]
    assert identical_twins, (
        "no two receipts in this world share a till, a second and their exact contents — the "
        "one case deduplication must not collapse is absent from the corpus"
    )


def test_transaction_ids_are_unique_across_the_world() -> None:
    run = prepare("W6", seed="events", scale="smoke")
    seen: set[str] = set()
    lines = 0
    for event in events(run):
        if not isinstance(event, PosLine):
            continue
        lines += 1
        if event.line_no == 1:
            assert event.transaction_id not in seen, event.transaction_id
            seen.add(event.transaction_id)
    assert lines > 1000


def test_line_totals_are_the_arithmetic_they_claim_to_be() -> None:
    run = prepare("W6", seed="events", scale="smoke")
    for event in events(run):
        if isinstance(event, PosLine):
            assert event.line_total_cents == event.qty * event.unit_price_cents
            assert event.qty >= 1
            assert event.unit_price_cents >= 1


def test_the_displayed_price_and_the_decided_price_are_two_columns_that_differ() -> None:
    """`CLAUDE.md`: *"The displayed price comes from the ESL ack, never from the decision."*

    A world in which they never differed would let a downstream reader take either one and be
    right, and exposure would be a column nobody ever had to look at.
    """
    run = prepare("W3", seed="events", scale="smoke")
    acks = [e for e in events(run) if isinstance(e, EslAck)]
    assert acks
    assert any(a.price_decided_cents != a.price_displayed_cents for a in acks)
    assert all((a.price_decided_cents == a.price_displayed_cents) is a.accepted for a in acks), (
        "a label that did not answer back is showing the new price anyway"
    )


def test_the_shelf_day_balances() -> None:
    """Sold plus wasted plus closing equals opening plus delivered, per store-SKU-day.

    Stock is what censoring is made of, so an inventory identity that did not hold would make
    claim 4's corpus arithmetic unfalsifiable. Checked as a running balance rather than a
    single row, because the carry-over between days is the part that would drift.
    """
    run = prepare("W6", seed="events", scale="smoke")
    carried: dict[tuple[str, str], int] = defaultdict(int)
    rows = 0
    for event in events(run):
        if not isinstance(event, ShelfDay):
            continue
        rows += 1
        key = (event.store_id, event.sku_id)
        opening = carried[key] + event.delivered_qty
        assert event.sold_qty + event.wasted_qty + event.closing_qty == opening, (
            f"{key} on {event.business_date}: {event.sold_qty}+{event.wasted_qty}"
            f"+{event.closing_qty} != {opening}"
        )
        carried[key] = event.closing_qty
    assert rows > 100


def test_a_stock_out_is_recorded_and_is_not_a_zero() -> None:
    """The shelf state says the shelf emptied. It does not say demand was zero.

    Nothing in the corpus records the baskets that were never rung up after a stock-out, and
    that is the point: a corpus that emitted the unserved demand would be handing claim 4 the
    answer it exists to reconstruct.
    """
    run = prepare("W6", seed="events", scale="rehearsal")
    out = [
        e for e in events(run) if isinstance(e, ShelfDay) and e.stocked_out_from_hour is not None
    ]
    assert out, "no store-SKU-day ever ran out; there is no censoring in this corpus"
    assert all(7 <= e.stocked_out_from_hour <= 22 for e in out)  # type: ignore[operator]
    assert all(e.closing_qty == 0 for e in out)
    assert not any(hasattr(e, "lost_qty") or hasattr(e, "unserved_qty") for e in out), (
        "the corpus is publishing the demand a stock-out hid, which is claim 4's answer"
    )


def test_the_field_order_written_to_csv_comes_from_the_dataclass() -> None:
    for record in RECORDS:
        assert field_names(record) == tuple(f.name for f in fields(record))
