"""Eleven questions asked of three worlds, and the numbers behind each.

`C2` is the check that carries the claim — *a stock-out is never read as zero demand* — and
`C5` is the one that makes it worth having, because a system that answers "no number" to every
censored day satisfies `C2` and is useless. The other nine bound the ways those two could be
passing for the wrong reason.

Each check names the function that makes it true, because `CLAUDE.md` requires an assertion
about the system to be written against that function rather than against the table it came
from:

====  ===========================================================  ==========================
`C1`  a stock-out is never a point observation                     `censoring.read`
`C2`  a stock-out is never corrected to zero demand                `censoring.correct`
`C3`  a shape that would hide a stock-out is refused               `DemandEstimate.__post_init__`
`C4`  a day the shelf held is never moved                          `censoring.correct`
`C5`  the reconstruction recovers more of the withheld truth       `AvailabilityCurve.share_before`
`C6`  the curve learns only from days the shelf held               `censoring.fit`
`C7`  the graded days are not the fitted days                      `build.WorldDays`
`C8`  a reconstructed day still says it was reconstructed          `DemandEstimate.censored`
`C9`  every censoring shape is reached                             `build.CENSOR_HOUR_GRID`
`C10` the reconstruction lands where the second arithmetic puts it `reference.reconstruct`
`C11` the naive reading is wrong here, and the corpus says so      the corpus itself
====  ===========================================================  ==========================
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from fractions import Fraction

from evals.censoring import build, reference
from evals.report import Check, Report
from holdout.core.demand.censoring import (
    AvailabilityCurve,
    CensoringError,
    DemandEstimate,
    FullyObserved,
    HourlySales,
    RightCensored,
    ShelfState,
    correct,
    fit,
    read,
)

#: Every censoring shape this eval must reach before it may claim to have tested the claim.
#: Rule 4 of `evals/README.md`: coverage is itself a check, because an eval whose inputs
#: cannot reach half the vocabulary has proved half the claim — and a footnote is where a gate
#: that stopped biting goes to be forgotten.
SHAPES: tuple[str, ...] = (
    "shelf_held",
    "ran_out_mid_day",
    "ran_out_in_the_last_trading_hour",
    "ran_out_before_anything_sold",
    "ran_out_with_no_window_at_all",
)

# Which of the five the corpus reaches on its own and which need the sweep is **measured and
# published**, not declared here. A first draft of this file asserted that both no-evidence
# shapes were unreachable from the corpus, on the reasoning that a shelf empties by being sold
# out. That was wrong: W5's heavy-tailed store-days empty a shelf inside the first trading
# hour three times, having sold up to three units — a shape nobody built for this claim,
# produced by a pathology that exists for claim 2. It was found by a mutation crashing on it,
# not by reading the corpus, which is the whole of `CLAUDE.md`'s third limb: only the
# measurement runs.


def _pct(value: Fraction) -> str:
    return f"{float(value) * 100:+.1f}%"


def _share_pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0/0"
    return f"{numerator}/{denominator} = {100 * numerator / denominator:.1f}%"


@dataclass(slots=True)
class GridPoint:
    """One censor hour, on one world's held-out segment."""

    world: str
    hour: int
    share: Fraction
    days: int = 0
    with_a_point_estimate: int = 0
    truth_units: int = 0
    naive_units: int = 0
    reconstructed_units: int = 0
    all_truth_units: int = 0
    """Every graded day, including the ones that produced no point estimate. The denominator
    of the *unconditional* estimand — see `pooled_recovery`."""
    all_naive_units: int = 0

    @property
    def naive_recovery(self) -> Fraction | None:
        if not self.truth_units:
            return None
        return Fraction(self.naive_units, self.truth_units)

    @property
    def reconstructed_recovery(self) -> Fraction | None:
        """Ratio of sums over the days that produced a point estimate — the conditional one."""
        if not self.truth_units:
            return None
        return Fraction(self.reconstructed_units, self.truth_units)

    @property
    def pooled_recovery(self) -> Fraction | None:
        """The same expansion applied to the **sum** over every graded day, conditioning on
        nothing. It is what separates a selection effect from a broken correction: if the
        overshoot at a thin share is the days with no first-hour sales dropping out, this
        number lands on one and the conditional one does not."""
        if not self.all_truth_units or self.share == 0:
            return None
        return Fraction(self.all_naive_units, 1) / self.share / self.all_truth_units

    def __str__(self) -> str:
        naive, built = self.naive_recovery, self.reconstructed_recovery
        if naive is None or built is None:
            return (
                f"{self.world} censored at {self.hour:02d}:00 — "
                f"{self.days} days, no point estimate on any of them"
            )
        return (
            f"{self.world} censored at {self.hour:02d}:00 — naive {_pct(naive - 1)} · "
            f"reconstructed {_pct(built - 1)} over {self.with_a_point_estimate} days"
        )


@dataclass(slots=True)
class Measured:
    """Everything one world has to say. Assembled in one pass; asserted on afterwards."""

    world: str
    split_date: str
    curve: AvailabilityCurve
    shelf_days: int
    days_the_shelf_held: int
    days_the_shelf_emptied: int
    fitted_on: int
    graded_on: int

    read_as_a_point_observation: list[str] = field(default_factory=list)
    read_as_censored_when_it_held: list[str] = field(default_factory=list)
    corrected_to_zero_demand: list[str] = field(default_factory=list)
    below_the_evidence: list[str] = field(default_factory=list)
    moved_a_day_that_held: list[str] = field(default_factory=list)
    lost_the_marker: list[str] = field(default_factory=list)
    disagreed_with_the_reference: list[str] = field(default_factory=list)
    censored_days_fit_accepted: list[str] = field(default_factory=list)
    keys_in_both_segments: list[str] = field(default_factory=list)

    sales_after_the_recorded_stock_out: list[str] = field(default_factory=list)
    censored_days_with_sales: int = 0
    recorded_hour_later_than_the_last_sale: int = 0
    reconstructed_as_recorded: int = 0
    reconstructed_from_the_last_movement: int = 0

    censored_corrections: int = 0
    no_window_at_all: int = 0
    nothing_sold_in_the_window: int = 0
    reconstructions_compared: int = 0
    boundaries_compared: int = 0
    shapes_from_the_corpus: set[str] = field(default_factory=set)
    shapes_from_the_sweep: set[str] = field(default_factory=set)
    grid: list[GridPoint] = field(default_factory=list)


def _shape_of(state: ShelfState, at_least: int, share: Fraction) -> str:
    if not state.ran_out:
        return "shelf_held"
    if share == 0:
        return "ran_out_with_no_window_at_all"
    if at_least == 0:
        return "ran_out_before_anything_sold"
    if state.stocked_out_from_hour == build.WINDOW.close_hour - 1:
        return "ran_out_in_the_last_trading_hour"
    return "ran_out_mid_day"


def _measure(days: build.WorldDays) -> Measured:
    """One world, in one pass. The order is: fit, then read, then correct, then grade."""
    held = days.held
    fit_days = days.fit_days
    graded = days.graded_days
    curve = fit(fit_days, build.WINDOW)
    before = reference.units_before(fit_days, build.WINDOW)
    grand_total = reference.total_units(fit_days)

    measured = Measured(
        world=days.world,
        split_date=days.split_date,
        curve=curve,
        shelf_days=len(days.days),
        days_the_shelf_held=len(held),
        days_the_shelf_emptied=len(days.ran_out),
        fitted_on=len(fit_days),
        graded_on=len(graded),
    )
    _check_the_split(measured, fit_days, graded)
    _check_the_fit_refuses_censored_days(measured, days.ran_out, held)
    _read_the_corpus(measured, days.days, curve, before, grand_total)
    _grade_on_the_held_out_segment(measured, graded, curve, before, grand_total)
    return measured


def _check_the_split(
    measured: Measured, fit_days: Sequence[HourlySales], graded: Sequence[HourlySales]
) -> None:
    fitted = {day.state.key for day in fit_days}
    measured.keys_in_both_segments = sorted(
        str(day.state.key) for day in graded if day.state.key in fitted
    )[:8]


def _check_the_fit_refuses_censored_days(
    measured: Measured, censored: Sequence[HourlySales], held: Sequence[HourlySales]
) -> None:
    """Offer `fit` every day the shelf emptied on — each one buried in a pile that works.

    **One censored day on its own does not test this**, and the first version of this check
    did exactly that. A `fit` that skipped censored days instead of refusing them still went
    red on a pile of one, because the empty curve it built was then refused by
    `AvailabilityCurve.__post_init__` — a different guard, catching it for a different reason.
    `gate-proof`'s `the-curve-learns-from-the-days-the-shelf-emptied` reported `SURVIVED`, and
    it was right to: *a gate can only be shown to bite where it is the gate that refuses.*

    So each censored day is offered alongside a day the shelf held, which is the shape a
    caller who has not sorted their input actually hands over. A corrector that filters
    silently returns a perfectly good curve from that pile, and only `fit` raising can catch
    it.
    """
    companion = held[0] if held else None
    for day in censored:
        pile = [day] if companion is None else [companion, day]
        try:
            fit(pile, build.WINDOW)
        except CensoringError:
            continue
        measured.censored_days_fit_accepted.append(str(day.state.key))


def _record(
    measured: Measured,
    state: ShelfState,
    estimate: DemandEstimate,
    hour: int | None,
    before: Sequence[int],
    grand_total: int,
    origin: str,
    swept: bool,
) -> None:
    """Every assertion that is about one estimate, applied to every estimate the eval makes."""
    shape = _shape_of(state, estimate.at_least, estimate.observed_share)
    if swept:
        measured.shapes_from_the_sweep.add(shape)
    else:
        measured.shapes_from_the_corpus.add(shape)
    if estimate.censored != state.ran_out:
        measured.lost_the_marker.append(f"{origin} censored={estimate.censored}")
    if state.ran_out:
        measured.censored_corrections += 1
        if estimate.units == 0:
            measured.corrected_to_zero_demand.append(
                f"{origin} sold {estimate.at_least} and was read as 0 units of demand"
            )
        if estimate.units is None:
            if estimate.observed_share == 0:
                measured.no_window_at_all += 1
            else:
                measured.nothing_sold_in_the_window += 1
    if estimate.units is not None and estimate.units < estimate.at_least:
        measured.below_the_evidence.append(
            f"{origin} reconstructed {estimate.units} under {estimate.at_least} sold"
        )
    if hour is None:
        return
    measured.reconstructions_compared += 1
    independent = reference.reconstruct(
        estimate.at_least, hour, before, grand_total, build.WINDOW.open_hour
    )
    if independent != estimate.units:
        measured.disagreed_with_the_reference.append(
            f"{origin} core {estimate.units} · reference {independent}"
        )


def _read_the_corpus(
    measured: Measured,
    days: Sequence[HourlySales],
    curve: AvailabilityCurve,
    before: Sequence[int],
    grand_total: int,
) -> None:
    """Every store-day in the world, read and corrected exactly as the system would."""
    for day in days:
        state = day.state
        reading = read(state, build.WINDOW)
        origin = f"{state.store_id}/{state.sku_id}/{state.business_date}"
        if state.ran_out and isinstance(reading, FullyObserved):
            measured.read_as_a_point_observation.append(origin)
        if not state.ran_out and isinstance(reading, RightCensored):
            measured.read_as_censored_when_it_held.append(origin)
        estimate = correct(reading, curve)
        if not state.ran_out and (
            estimate.units != state.units_sold or estimate.observed_share != 1
        ):
            measured.moved_a_day_that_held.append(
                f"{origin} sold {state.units_sold}, correction returned {estimate.units}"
            )
        hour = state.stocked_out_from_hour
        _record(measured, state, estimate, hour, before, grand_total, origin, swept=False)
        if hour is not None and state.units_sold:
            _weigh_the_recorded_hour(measured, day, curve, estimate, origin)
    measured.boundaries_compared = _compare_the_curve(measured, curve, before, grand_total)


def _weigh_the_recorded_hour(
    measured: Measured,
    day: HourlySales,
    curve: AvailabilityCurve,
    estimate: DemandEstimate,
    origin: str,
) -> None:
    """What `stocked_out_from_hour` means in this corpus, measured rather than taken on trust.

    The correction's declared direction depends on it. If the column is the hour on-hand
    reached zero, the observed units include a partly-traded hour the share excludes and the
    reconstruction errs **high**; if it is the hour the first shopper was turned away, the
    share covers hours in which nothing could have sold and it errs **low**. The two are the
    same number only where somebody was there at the moment the shelf emptied.

    So both are computed: the correction as the column records it, and the correction against a
    stock-out hour derived from the **last inventory movement** — the last hour that sold
    anything, which is what silver's own derivation would produce. The gap is published as a
    number rather than argued about in a paragraph.

    The one thing that must not happen is a sale **after** the recorded hour: those units sit
    in the numerator while the share's window excludes them, and the reconstruction inflates
    without any bound at all. That is `C12`, and it is measured here.
    """
    measured.censored_days_with_sales += 1
    last_selling = max(index for index, units in enumerate(day.units_by_hour) if units)
    last_hour = last_selling + build.WINDOW.open_hour
    recorded = day.state.stocked_out_from_hour
    assert recorded is not None
    if last_hour > recorded:
        measured.sales_after_the_recorded_stock_out.append(
            f"{origin} last sold at {last_hour:02d}:00, recorded empty from {recorded:02d}:00"
        )
    elif last_hour < recorded:
        measured.recorded_hour_later_than_the_last_sale += 1
    derived = correct(
        RightCensored(at_least=day.state.units_sold, stocked_out_from_hour=last_hour), curve
    )
    measured.reconstructed_as_recorded += estimate.units or 0
    measured.reconstructed_from_the_last_movement += derived.units or 0


def _compare_the_curve(
    measured: Measured, curve: AvailabilityCurve, before: Sequence[int], grand_total: int
) -> int:
    """The curve's own boundaries against the second implementation's, as integers.

    `G10`'s argument, one claim along: a reconstruction reaches the curve *through* a
    store-day, so it sees a misplaced boundary only where a store-day's sales happen to land
    in the gap the mistake opens. Comparing the boundaries directly sees all of them.
    """
    compared = 0
    for hour in range(build.WINDOW.open_hour, build.WINDOW.close_hour):
        compared += 1
        core = curve.share_before(hour)
        independent = Fraction(before[hour - build.WINDOW.open_hour], grand_total)
        if core != independent:
            measured.disagreed_with_the_reference.append(
                f"{measured.world} boundary at {hour:02d}:00 — core {core} · "
                f"reference {independent}"
            )
    return compared


def _grade_on_the_held_out_segment(
    measured: Measured,
    graded: Sequence[HourlySales],
    curve: AvailabilityCurve,
    before: Sequence[int],
    grand_total: int,
) -> None:
    """The held-out segment with full shelf availability, censored on purpose.

    The truth each reconstruction is graded against is **what the shelf actually sold on a day
    it never ran out** — a number the corpus emitted, not a latent intensity the simulator
    knows and this eval was told. That is the whole answer to claim 4's trap: the grader never
    consults the process that generated the data, so a correction cannot be right by sharing
    the simulator's assumptions.
    """
    for hour in build.CENSOR_HOUR_GRID:
        point = GridPoint(world=measured.world, hour=hour, share=curve.share_before(hour))
        index = hour - build.WINDOW.open_hour
        for day in graded:
            observed = sum(day.units_by_hour[:index])
            truth = day.units
            reading = RightCensored(at_least=observed, stocked_out_from_hour=hour)
            estimate = correct(reading, curve)
            origin = (
                f"{day.state.store_id}/{day.state.sku_id}/{day.state.business_date} "
                f"censored at {hour:02d}:00"
            )
            _record(
                measured,
                ShelfState(
                    store_id=day.state.store_id,
                    sku_id=day.state.sku_id,
                    business_date=day.state.business_date,
                    units_sold=observed,
                    stocked_out_from_hour=hour,
                ),
                estimate,
                hour,
                before,
                grand_total,
                origin,
                swept=True,
            )
            point.days += 1
            point.all_truth_units += truth
            point.all_naive_units += observed
            if estimate.units is None:
                continue
            point.with_a_point_estimate += 1
            point.truth_units += truth
            point.naive_units += observed
            point.reconstructed_units += estimate.units
        measured.grid.append(point)


# --------------------------------------------------------------------------- the checks


def _c1(worlds: Sequence[Measured]) -> Check:
    missed = [origin for m in worlds for origin in m.read_as_a_point_observation]
    inverted = [origin for m in worlds for origin in m.read_as_censored_when_it_held]
    emptied = sum(m.days_the_shelf_emptied for m in worlds)
    held = sum(m.days_the_shelf_held for m in worlds)
    return Check(
        id="C1.a-stock-out-is-never-a-point-observation",
        question=(
            "does every store-day whose shelf emptied come back as a right-censored reading, "
            "and every day it held as a fully observed one?"
        ),
        passed=not missed and not inverted,
        figure=(
            f"{len(missed)} of {emptied:,} emptied store-days read as fully observed · "
            f"{len(inverted)} of {held:,} held days read as censored"
        ),
        detail=(
            "`read` has no close-enough branch: a shelf that emptied in the last trading hour "
            "hid an unknown amount, and an unknown amount is not none."
        ),
        counterexamples=tuple((missed + inverted)[:5]),
    )


def _c2(worlds: Sequence[Measured]) -> Check:
    zeroes = [origin for m in worlds for origin in m.corrected_to_zero_demand]
    corrections = sum(m.censored_corrections for m in worlds)
    no_window = sum(m.no_window_at_all for m in worlds)
    nothing_sold = sum(m.nothing_sold_in_the_window for m in worlds)
    return Check(
        id="C2.a-stock-out-is-never-corrected-to-zero-demand",
        question=(
            "over every censored store-day the corpus produced and every one the sweep "
            "constructed, does the correction ever answer that demand was zero?"
        ),
        passed=not zeroes,
        figure=(
            f"{len(zeroes)} of {corrections:,} censored corrections returned zero demand · "
            f"{no_window + nothing_sold:,} answered with no point estimate instead"
        ),
        detail=(
            "Where the observed window is empty or saw nothing, `correct` returns `units=None` "
            "and `at_least` stands alone. Dividing zero evidence by any share returns zero, "
            "and that one line is the claim's own failure."
        ),
        counterexamples=tuple(zeroes[:5]),
    )


#: Shapes somebody could hand this module that would let a stock-out become a number, each
#: with the guard that has to refuse it. `G9`'s argument one claim along: driving the happy
#: path proves the arithmetic, never that the types refuse what would corrupt it — and every
#: one of these is a mistake with a plausible motive rather than an invented pathological case.
TAMPERS: tuple[tuple[str, str], ...] = (
    ("a reconstruction one unit under the sales it was built from", "DemandEstimate"),
    ("a negative reconstruction", "DemandEstimate"),
    ("a store-day with negative sales — a return posted as a sale", "ShelfState"),
    ("an hourly breakdown that does not sum to what the shelf record says sold", "HourlySales"),
    ("a shelf that emptied in an hour the shop was shut", "read"),
    ("a curve fitted on days that sold nothing at all", "AvailabilityCurve"),
    ("a curve read at an hour outside the trading day it was fitted over", "AvailabilityCurve"),
)


def _attempt_the_tampers(curve: AvailabilityCurve) -> list[str]:
    """Each declared tamper, attempted for real. What is not refused is returned."""
    window = build.WINDOW
    held = ShelfState(
        store_id="S001",
        sku_id="K001",
        business_date="2025-09-01",
        units_sold=4,
        stocked_out_from_hour=None,
    )
    attempts: tuple[tuple[str, Callable[[], object]], ...] = (
        (
            TAMPERS[0][0],
            lambda: DemandEstimate(
                at_least=9, units=8, censored=True, observed_share=Fraction(1, 2)
            ),
        ),
        (
            TAMPERS[1][0],
            lambda: DemandEstimate(
                at_least=0, units=-1, censored=True, observed_share=Fraction(1, 2)
            ),
        ),
        (
            TAMPERS[2][0],
            lambda: ShelfState(
                store_id="S001",
                sku_id="K001",
                business_date="2025-09-01",
                units_sold=-3,
                stocked_out_from_hour=None,
            ),
        ),
        (TAMPERS[3][0], lambda: HourlySales(state=held, units_by_hour=(0,) * window.hours)),
        (
            TAMPERS[4][0],
            lambda: read(
                ShelfState(
                    store_id="S001",
                    sku_id="K001",
                    business_date="2025-09-01",
                    units_sold=4,
                    stocked_out_from_hour=window.close_hour + 1,
                ),
                window,
            ),
        ),
        (
            TAMPERS[5][0],
            lambda: AvailabilityCurve(window=window, units_by_hour=(0,) * window.hours, days=11),
        ),
        (TAMPERS[6][0], lambda: curve.share_before(window.close_hour)),
    )
    survived: list[str] = []
    for (name, guard), (_, attempt) in zip(TAMPERS, attempts, strict=True):
        try:
            attempt()
        except CensoringError:
            continue
        except Exception as error:
            # Refused, but by the wrong thing. A `TypeError` three lines later is not the
            # contract refusing; it is the interpreter, and it would stop being raised the day
            # somebody adds an annotation. `gate-proof` calls the same shape `CRASHED`.
            survived.append(f"{name} — {guard} raised {type(error).__name__}, not CensoringError")
            continue
        survived.append(f"{name} — {guard} accepted it")
    return survived


def _c3(worlds: Sequence[Measured]) -> Check:
    survived = _attempt_the_tampers(worlds[0].curve)
    below = [origin for m in worlds for origin in m.below_the_evidence]
    return Check(
        id="C3.a-shape-that-would-hide-a-stock-out-is-refused",
        question=(
            "are all seven declared tampers refused — a reconstruction under its own evidence, "
            "a curve with no evidence in it, an hour outside the trading day?"
        ),
        passed=not survived and not below,
        figure=(
            f"{len(TAMPERS) - len(survived)}/{len(TAMPERS)} declared tampers refused · "
            f"{len(below)} corpus reconstructions under the units the receipts show"
        ),
        detail=(
            "The observed units are a receipt, so an estimate under them contradicts one and "
            "the type refuses to be built. Driving the happy path proves the arithmetic; it "
            "never proves that the shapes around it refuse what would corrupt it."
        ),
        counterexamples=tuple((survived + below)[:5]),
    )


def _c4(worlds: Sequence[Measured]) -> Check:
    moved = [origin for m in worlds for origin in m.moved_a_day_that_held]
    held = sum(m.days_the_shelf_held for m in worlds)
    return Check(
        id="C4.a-day-the-shelf-held-is-never-moved",
        question=(
            "on a store-day with full shelf availability, does the correction return exactly "
            "what sold — as integers, with no tolerance?"
        ),
        passed=not moved,
        figure=f"{len(moved)} of {held:,} store-days with full availability moved",
        detail=(
            "Nothing was hidden, so there is nothing to reconstruct. A correction that moved "
            "such a day would be inventing demand out of a curve rather than out of evidence, "
            "which is doctrine rule 3 in the one place it is easiest to break by accident."
        ),
        counterexamples=tuple(moved[:5]),
    )


def _c5(worlds: Sequence[Measured]) -> Check:
    beaten: list[str] = []
    compared = 0
    worst = Fraction(0)
    best_naive = Fraction(1)
    for measured in worlds:
        for point in measured.grid:
            naive, built = point.naive_recovery, point.reconstructed_recovery
            if naive is None or built is None:
                continue
            compared += 1
            worst = max(worst, abs(built - 1))
            best_naive = min(best_naive, abs(naive - 1))
            if abs(built - 1) >= abs(naive - 1):
                beaten.append(str(point))
    return Check(
        id="C5.the-reconstruction-recovers-more-of-the-withheld-truth",
        question=(
            "at every censor hour, on every world, does the reconstruction land closer to the "
            "withheld truth than reading the truncated number as the day's demand?"
        ),
        passed=not beaten and compared > 0,
        figure=(
            f"{compared} censor hours · worst reconstruction {_pct(worst)} from the truth, "
            f"against the naive reading's best of {_pct(-best_naive)}"
        ),
        detail=(
            "The truth is what the shelf sold on a day it never emptied — a number the corpus "
            "emitted. The grader never consults the process that generated it."
        ),
        counterexamples=tuple(beaten[:5]),
    )


def _c6(worlds: Sequence[Measured]) -> Check:
    accepted = [origin for m in worlds for origin in m.censored_days_fit_accepted]
    offered = sum(m.days_the_shelf_emptied for m in worlds)
    return Check(
        id="C6.the-curve-learns-only-from-days-the-shelf-held",
        question=(
            "offered a store-day whose shelf emptied, does `fit` refuse it rather than "
            "quietly leave it out?"
        ),
        passed=not accepted and offered > 0,
        figure=f"{offered - len(accepted):,} of {offered:,} censored store-days refused by fit",
        detail=(
            "Claim 4's trap in its plainest clothes: a corrector fitted on the pathology it is "
            "about to remove will remove exactly as much of it as it learned and no more. "
            "Refused rather than filtered, because filtering looks identical from outside."
        ),
        counterexamples=tuple(accepted[:5]),
    )


def _c7(worlds: Sequence[Measured]) -> Check:
    overlap = [origin for m in worlds for origin in m.keys_in_both_segments]
    fitted = sum(m.fitted_on for m in worlds)
    graded = sum(m.graded_on for m in worlds)
    dates = " · ".join(f"{m.world} from {m.split_date}" for m in worlds)
    return Check(
        id="C7.the-graded-days-are-not-the-days-the-curve-was-fitted-on",
        unarmed_because=(
            "its disjointness half is a tautology — the two segments are complementary predicates "
            " over one business date — and only its non-emptiness half can go red, which is a pro "
            "perty of the corpus rather than of the system."
        ),
        question=(
            "is the held-out segment disjoint from the fitting segment, and is neither of "
            "them empty?"
        ),
        passed=not overlap and fitted > 0 and graded > 0,
        figure=(f"fitted on {fitted:,} store-days · graded on {graded:,} · {len(overlap)} in both"),
        detail=f"A time split, never a random one: {dates}.",
        counterexamples=tuple(overlap[:5]),
    )


def _c8(worlds: Sequence[Measured]) -> Check:
    lost = [origin for m in worlds for origin in m.lost_the_marker]
    total = sum(m.shelf_days + sum(p.days for p in m.grid) for m in worlds)
    return Check(
        id="C8.a-reconstructed-day-still-says-it-was-reconstructed",
        question=(
            "does every estimate carry whether the day it came from was censored, all the way "
            "out of the function?"
        ),
        passed=not lost,
        figure=f"{total - len(lost):,} of {total:,} estimates carry their own censoring mark",
        detail=(
            "Doctrine rule 2, one claim along: a reconstructed store-day that arrives looking "
            "like an observed one is worse than a missing one, because it is silent."
        ),
        counterexamples=tuple(lost[:5]),
    )


def _c9(worlds: Sequence[Measured]) -> Check:
    from_corpus: set[str] = set()
    from_sweep: set[str] = set()
    for measured in worlds:
        from_corpus |= measured.shapes_from_the_corpus
        from_sweep |= measured.shapes_from_the_sweep
    missing = [shape for shape in SHAPES if shape not in from_corpus | from_sweep]
    only_swept = sorted(shape for shape in SHAPES if shape not in from_corpus)
    return Check(
        id="C9.every-censoring-shape-is-reached",
        question=(
            "does this eval construct an input for every declared censoring shape, so that no "
            "branch of the correction passes by never being tried?"
        ),
        passed=not missing,
        figure=(
            f"{len(SHAPES) - len(missing)}/{len(SHAPES)} shapes reached · "
            f"{len(only_swept)} of them only by the declared sweep"
        ),
        detail=(
            "Reached only by the sweep: "
            + (", ".join(only_swept) if only_swept else "none — the corpus produces all five")
            + ". A shelf that empties before it sells anything is the shape where the claim's "
            "own sentence would be violated, and no corpus here produces one."
        ),
        counterexamples=tuple(missing),
    )


def _c10(worlds: Sequence[Measured]) -> Check:
    disagreements = [origin for m in worlds for origin in m.disagreed_with_the_reference]
    reconstructions = sum(m.reconstructions_compared for m in worlds)
    boundaries = sum(m.boundaries_compared for m in worlds)
    return Check(
        id="C10.the-reconstruction-lands-where-the-independent-arithmetic-puts-it",
        question=(
            "does a second implementation — integers, no share ever formed, the curve rescanned "
            "per hour — land on exactly the same unit count and the same hourly boundaries?"
        ),
        passed=not disagreements,
        figure=(
            f"{len(disagreements)} disagreements in {reconstructions:,} reconstructions and "
            f"{boundaries} hourly boundaries, compared as integers with no tolerance"
        ),
        detail=(
            "The boundaries are compared directly as well as through a store-day, because a "
            "reconstruction only sees a misplaced boundary where a day's sales land in the gap "
            "it opens."
        ),
        counterexamples=tuple(disagreements[:5]),
    )


def _c11(worlds: Sequence[Measured]) -> Check:
    """The armed check: if the corpus had no censoring, every check above would pass on air."""
    quiet = [m.world for m in worlds if m.days_the_shelf_emptied == 0]
    not_understated: list[str] = []
    measured_at = 0
    for measured in worlds:
        for point in measured.grid:
            naive = point.naive_recovery
            if naive is None:
                continue
            measured_at += 1
            if naive >= 1:
                not_understated.append(str(point))
    emptied = sum(m.days_the_shelf_emptied for m in worlds)
    shelf_days = sum(m.shelf_days for m in worlds)
    grid_points = sum(len(m.grid) for m in worlds)
    return Check(
        id="C11.the-naive-reading-is-wrong-here-and-the-corpus-says-so",
        unarmed_because=(
            "it asserts how much of the **corpus** is censored. No break planted in `src/holdout/ "
            "` can move a figure about the inputs."
        ),
        question=(
            "is there enough censoring in these worlds for the checks above to mean anything, "
            "and does reading a truncated day as its demand understate at every censor hour "
            "that produced a measurement?"
        ),
        passed=not quiet and not not_understated and measured_at > 0,
        figure=(
            f"{_share_pct(emptied, shelf_days)} of store-days emptied · the naive reading "
            f"understates at {measured_at} of the {grid_points} censor hours and overstates at "
            f"none — the other {grid_points - measured_at} produce no estimate to compare"
        ),
        detail=(
            "A gate shown to bite on a corpus with nothing to bite on has not been shown to "
            "bite. Nobody chose which store-days run out: they come out of the simulation's "
            "replenishment arithmetic, which was written for claim 2."
        ),
        counterexamples=tuple((quiet + not_understated)[:5]),
    )


def _c12(worlds: Sequence[Measured]) -> Check:
    """The corpus property the correction's whole direction argument rests on."""
    after = [origin for m in worlds for origin in m.sales_after_the_recorded_stock_out]
    days = sum(m.censored_days_with_sales for m in worlds)
    later = sum(m.recorded_hour_later_than_the_last_sale for m in worlds)
    recorded = sum(m.reconstructed_as_recorded for m in worlds)
    movement = sum(m.reconstructed_from_the_last_movement for m in worlds)
    drift = (movement - recorded) / recorded if recorded else 0.0
    return Check(
        id="C12.no-sale-falls-after-the-hour-the-shelf-is-recorded-as-empty",
        unarmed_because=(
            "likewise a property of the corpus: no store-day sells after its recorded stock-out,  "
            "whatever the correction does with it."
        ),
        question=(
            "does any censored store-day sell something after the hour its shelf is recorded "
            "as empty from — which would put units in the numerator the share's window "
            "excludes, and inflate the reconstruction without bound?"
        ),
        passed=not after and days > 0,
        figure=(
            f"{len(after)} of {days:,} censored store-days sold after their recorded stock-out "
            f"· {_share_pct(later, days)} recorded strictly later than the last sale"
        ),
        detail=(
            "The column is the hour the first shopper was turned away, not the hour on-hand "
            "reached zero, and the two come apart by however long the shelf stood bare. That "
            "is safe — it costs accuracy, never a bound — but it reverses the direction the "
            f"correction errs in on those days: against a stock-out hour derived from the last "
            f"inventory movement the reconstructed total is {drift:+.1%}. Published, not "
            "reconciled: what a source means by this column is a fact about that source."
        ),
        counterexamples=tuple(after[:5]),
    )


def run() -> Report:
    worlds = tuple(_measure(days) for days in build.worlds())
    checks = (
        _c1(worlds),
        _c2(worlds),
        _c3(worlds),
        _c4(worlds),
        _c5(worlds),
        _c6(worlds),
        _c7(worlds),
        _c8(worlds),
        _c9(worlds),
        _c10(worlds),
        _c11(worlds),
        _c12(worlds),
    )
    return Report(
        claim=4,
        title="a stock-out is never read as zero demand",
        checks=checks,
        numbers=_numbers(worlds),
        notes=NOTES,
    )


def _numbers(worlds: Sequence[Measured]) -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = [
        (
            "corpus",
            f"{len(worlds)} worlds ({', '.join(m.world for m in worlds)}) at "
            f"{build.SCALE} scale, seed {build.SEED}",
        )
    ]
    for measured in worlds:
        rows.append(
            (
                f"{measured.world} store-days",
                f"{measured.shelf_days:,} · "
                f"{_share_pct(measured.days_the_shelf_emptied, measured.shelf_days)} emptied · "
                f"fitted on {measured.fitted_on:,}, graded on {measured.graded_on:,}",
            )
        )
    rows.append(
        (
            "the estimand",
            "a ratio of sums over the days that produced a point estimate; `pooled` beside it "
            "is the same expansion over the sum of **every** graded day, conditioning on "
            "nothing. The pair is what tells a selection effect from a broken correction",
        )
    )
    for hour in build.CENSOR_HOUR_GRID:
        points = [p for m in worlds for p in m.grid if p.hour == hour]
        naive = [p.naive_recovery for p in points if p.naive_recovery is not None]
        built = [p.reconstructed_recovery for p in points if p.reconstructed_recovery is not None]
        pooled = [p.pooled_recovery for p in points if p.pooled_recovery is not None]
        share = points[0].share if points else Fraction(0)
        if not naive or not built:
            rows.append(
                (
                    f"censored at {hour:02d}:00",
                    f"share {float(share):.4f} — no point estimate on any of "
                    f"{sum(p.days for p in points):,} held-out store-days",
                )
            )
            continue
        rows.append(
            (
                f"censored at {hour:02d}:00",
                f"share {float(share):.4f} · naive "
                f"{_pct(min(naive) - 1)}…{_pct(max(naive) - 1)} · reconstructed "
                f"{_pct(min(built) - 1)}…{_pct(max(built) - 1)} · pooled "
                f"{_pct(min(pooled) - 1)}…{_pct(max(pooled) - 1)}",
            )
        )
    recorded = sum(m.reconstructed_as_recorded for m in worlds)
    movement = sum(m.reconstructed_from_the_last_movement for m in worlds)
    rows.append(
        (
            "the stock-out hour",
            f"the corpus's censored days correct to {recorded:,} units as the column records "
            f"the hour and {movement:,} against one derived from the last inventory movement "
            f"({(movement - recorded) / recorded:+.1%}) — the column is the hour a shopper was "
            "turned away, not the hour the shelf emptied, and which one a source supplies "
            "decides the direction the correction errs in",
        )
    )
    rows.append(
        (
            "no point estimate",
            f"{sum(m.no_window_at_all for m in worlds):,} with no open window at all · "
            f"{sum(m.nothing_sold_in_the_window for m in worlds):,} that sold nothing before "
            "the shelf emptied — a lower bound and no number, in both",
        )
    )
    rows.append(
        (
            "never below evidence",
            f"{sum(m.reconstructions_compared for m in worlds):,} reconstructions, "
            f"{sum(len(m.below_the_evidence) for m in worlds)} of them under the units the "
            "receipts show",
        )
    )
    return tuple(rows)


#: Rule 6 of `evals/README.md`: what this does not prove is printed on every run, not kept in
#: a README where it can quietly stop being true.
NOTES: tuple[str, ...] = (
    "A day censored on purpose is not a stock-out. A real shelf empties on unusually busy "
    "days, so real censoring is correlated with the very quantity being reconstructed and the "
    "sweep's is not. Nothing in this repository holds the unserved demand that would close "
    "that gap — the corpus deliberately does not emit it.",
    "The reconstruction answers how much of a day's demand the observed window saw. It does "
    "not answer what would have sold had the shelf been full, and no data here contains that.",
    "The corpus spreads a price segment's arrivals uniformly across its hours, so the intraday "
    "shape this curve has to learn is close to a straight line. A lumpier real profile would "
    "be harder, and the residual error published above is a floor rather than an estimate.",
    "The error is not monotone in the share, and the 08:00 row is why: +36% to +40% at a share "
    "of 0.06 against under 1% at 0.94. It is **selection, not a correction that breaks in a "
    "thin window**, and the pooled column is the evidence rather than the argument — the same "
    "expansion over every graded day, conditioning on nothing, lands at -1.5% to -0.6% on the "
    "same hour. A day only yields a point estimate if it sold something inside the observed "
    "window, so conditioning on that in a thin window keeps the days that over-performed in "
    "it. Either way the reconstruction is trustworthy in proportion to how much of the day it "
    "saw, and this eval declares no threshold at which it stops being: that number is not "
    "something the corpus can supply.",
    "C5 is weakest exactly where the published error is largest. At a share of 0.06 the bar it "
    "sets is 'beat -91.2%', which almost any reconstruction clears — so the +36% to +40% is "
    "bounded by nothing in this eval, it is only measured and printed. What C5 does bound is "
    "the wide-window end, where the naive reading is already close.",
    "Which way the correction errs is a property of the **source**, not of the arithmetic. "
    "This corpus records the hour a shopper was turned away rather than the hour the shelf "
    "emptied, and the two differ on 43.0% of censored store-days — see C12 and the stock-out "
    "hour row. Against a hour derived from the last inventory movement the same corpus "
    "corrects 6.3% higher. Nothing here reconciles the two: what a column means belongs to "
    "whoever writes it.",
    "A real stock-out hour is partly traded and a constructed one is not, so the direction the "
    "correction errs in on a real stock-out is argued from the arithmetic rather than measured.",
    "One pooled curve per world. A curve per category, store format or day of week is a "
    "caller's decision and none is exercised here.",
    "Three worlds, one seed, one scale, and a correction that is one of several a real "
    "estimator could use. These are the failure modes we thought of.",
)
