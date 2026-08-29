"""A stock-out is never read as zero demand — claim 4, as three functions.

`read` turns what silver knows about a store-SKU-day into one of two things, and they are
different **types** rather than the same type with a flag:

======================  ====================================================================
`FullyObserved`         the shelf held all day. `units` is the day's demand
`RightCensored`         the shelf emptied at a known hour. There is no `units` attribute at
                        all — only `at_least`, which is evidence rather than an answer
======================  ====================================================================

That is the structural half, and it is the same argument `CertifiedPrice` makes one claim
along: a caller who wants a number out of a censored day has to say what it did about the
censoring, because there is no attribute to reach for. `mypy` refuses `reading.units` on the
union, and the union is the only thing `read` returns.

The correction, and where it refuses to answer
----------------------------------------------
`fit` estimates one **availability curve** — what share of an ordinary day's demand has
arrived by the end of each trading hour — pooled over store-days on which the shelf *held*.
`correct` then expands a censored day's observed units by the share of the day its open
window ordinarily carries.

`correct` produces **no point estimate** in two cases, and neither of them is a threshold
somebody chose:

* **the shelf was empty from the first trading hour** — the observed window has zero width,
  so there is no evidence to expand. Not "approximately zero demand": no evidence;
* **the shelf sold nothing before it emptied** — dividing zero by any share gives zero, and
  reporting that would be reading a stock-out as zero demand in the one line where it is
  easiest to do by accident.

In both, `DemandEstimate.units` is `None` and `at_least` stands alone. `CLAUDE.md`: *where
the comparison cannot be trusted, the system produces no number.* This is that rule, one
layer down from the readout.

Which way it errs, and the fact about the source that decides it
----------------------------------------------------------------
The share is read **through the end of the hour before** the shelf emptied, while the observed
units include whatever sold inside the emptying hour itself. Where the recorded hour *is* the
hour trade stopped, the numerator therefore covers slightly more of the day than the
denominator does and the reconstruction errs **high** — which is the chosen direction, because
understating is the failure this module exists to prevent.

**That holds only if the source means by `stocked_out_from_hour` the hour the shelf emptied.**
A source that records the hour the *first shopper was turned away* means something later, and
the two come apart by however long the shelf stood bare before anyone reached for it. Then the
denominator covers hours in which nothing could have sold, and the reconstruction errs **low**
instead. It is not a rounding-sized difference: measured on this repository's own corpus, the
recorded hour is strictly later than the last hour that sold anything on **7,290 of 16,942
censored store-days (43.0%)**, by up to fourteen hours, and correcting against a hour derived
from the last inventory movement instead raises the reconstructed total by **6.3%**.

So the direction this module errs in is **a property of the source, not of this arithmetic**,
and it is stated that way rather than as a flat guarantee. What the arithmetic does guarantee
is the half that does not depend on the source: the reconstruction is never below the units the
receipts show, whatever the recorded hour means, because the share can never exceed one.

The one thing a source must not do is record an hour **earlier** than the last sale, which
would put units in the numerator that the denominator's window excludes and inflate without
bound. `evals/censoring/`'s `C12` measures that against the corpus rather than assuming it.

The expansion rounds **half-even**, not down. A rule that rounded a reconstruction toward the
number that was observed would be the censoring bias in miniature, applied by the very
function written to remove it.

What this module is not
-----------------------
It is not a demand model and it does not forecast. It reconstructs the demand that a day's
own observed window is evidence of, using an empirical shape fitted on days where nothing was
hidden. The counterfactual question — *what would have sold if the shelf had been full* — is
not answered here and no data in this repository contains its answer.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction


class CensoringError(ValueError):
    """A shelf-day, a trading window or a curve that does not describe a possible day."""


@dataclass(frozen=True, slots=True)
class TradingWindow:
    """The store's trading hours, closed at the top: `[open_hour, close_hour)`.

    An argument rather than a constant, because a trading day is a fact about a chain and
    `holdout.core` is not allowed to know one. A window is also what makes an hour index
    meaningful: "hour 16" is the tenth hour of a day that opens at 07:00 and a different hour
    of a day that opens at 06:00, and a curve fitted under one window may not be read under
    the other.
    """

    open_hour: int
    close_hour: int

    def __post_init__(self) -> None:
        if not 0 <= self.open_hour < self.close_hour <= 24:
            raise CensoringError(
                f"[{self.open_hour}, {self.close_hour}) is not a trading day. A window must "
                "open before it closes and both hours must fall inside a calendar day."
            )

    @property
    def hours(self) -> int:
        return self.close_hour - self.open_hour

    def index_of(self, hour: int) -> int:
        """Where an hour sits in this window, refusing one that falls outside it."""
        if not self.open_hour <= hour < self.close_hour:
            raise CensoringError(
                f"hour {hour} is outside the trading window [{self.open_hour}, "
                f"{self.close_hour}). A shelf cannot empty in an hour the shop is shut, and "
                "silently clamping it to the nearest open hour would move the stock-out."
            )
        return hour - self.open_hour


@dataclass(frozen=True, slots=True)
class ShelfState:
    """One store, one SKU, one day, as silver records it.

    `stocked_out_from_hour` is observable — stock-out marking belongs in silver because that is
    where the inventory movements are. **What a source means by it is a fact about that
    source**, and there are two readings a real one might supply: the hour on-hand reached
    zero, and the hour the first shopper was turned away. They are the same number only if
    somebody was there at the moment it emptied. Which one arrives decides the direction the
    correction errs in — see the module docstring, and the 43.0% this repository's own corpus
    measures.

    It is not defaulted, inferred or reconciled here. A field that quietly picked one reading
    would be doctrine rule 3 broken in the one column claim 4 rests on.

    What is deliberately not a field is the demand that went unserved: nothing in this system
    has ever seen it.
    """

    store_id: str
    sku_id: str
    business_date: str
    units_sold: int
    stocked_out_from_hour: int | None

    def __post_init__(self) -> None:
        if self.units_sold < 0:
            raise CensoringError(
                f"{self.key} sold {self.units_sold} units. Negative sales are a returns "
                "posting arriving as a sale, not a quantity."
            )

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.store_id, self.sku_id, self.business_date)

    @property
    def ran_out(self) -> bool:
        return self.stocked_out_from_hour is not None


@dataclass(frozen=True, slots=True)
class HourlySales:
    """A store-SKU-day broken down by trading hour — what `fit` learns a shape from.

    The daily total is **derived from the hours** rather than carried alongside them. Two
    fields holding the same quantity is two fields that eventually disagree, and the one that
    would be wrong is the one nobody recomputes.
    """

    state: ShelfState
    units_by_hour: tuple[int, ...]

    def __post_init__(self) -> None:
        if any(units < 0 for units in self.units_by_hour):
            raise CensoringError(f"{self.state.key} has a negative hour in {self.units_by_hour}.")
        if sum(self.units_by_hour) != self.state.units_sold:
            raise CensoringError(
                f"{self.state.key} sold {self.state.units_sold} units and its hours sum to "
                f"{sum(self.units_by_hour)}. A day whose hours do not add up to its total is "
                "two sources disagreeing, and neither one is safe to pick."
            )

    @property
    def units(self) -> int:
        return sum(self.units_by_hour)


# --------------------------------------------------------------------------- the reading


@dataclass(frozen=True, slots=True)
class FullyObserved:
    """The shelf held all day, so what sold is what was wanted."""

    units: int


@dataclass(frozen=True, slots=True)
class RightCensored:
    """The shelf emptied. `at_least` is evidence; there is no `units` on this type.

    Deliberately not `units`, and deliberately not `units_sold` either. Both names invite a
    caller to average the field and call the result demand, which is the exact mistake claim 4
    names. `at_least` cannot be read that way without reading a lie.
    """

    at_least: int
    stocked_out_from_hour: int


#: What `read` returns. A caller that wants a number handles both arms or does not compile.
DemandReading = FullyObserved | RightCensored


def read(state: ShelfState, window: TradingWindow) -> DemandReading:
    """What one store-SKU-day is evidence of. The claim's first sentence, as a function.

    There is no "close enough" branch. A shelf that emptied in the last trading hour hid less
    demand than one that emptied at noon, but it hid an unknown amount and the difference
    between an unknown amount and none is the whole of this claim — so the last hour is
    censored exactly like the first.
    """
    if state.stocked_out_from_hour is None:
        return FullyObserved(units=state.units_sold)
    window.index_of(state.stocked_out_from_hour)
    return RightCensored(
        at_least=state.units_sold, stocked_out_from_hour=state.stocked_out_from_hour
    )


# --------------------------------------------------------------------------- the curve


@dataclass(frozen=True, slots=True)
class AvailabilityCurve:
    """How much of an ordinary day's demand has arrived by the end of each trading hour.

    It holds the pooled **unit counts** rather than pre-divided shares, so every share it
    reports is an exact `Fraction` of two integers this curve actually observed. A tuple of
    stored shares would be a rounding decision taken once at fit time and inherited by every
    reconstruction afterwards.
    """

    window: TradingWindow
    units_by_hour: tuple[int, ...]
    days: int

    def __post_init__(self) -> None:
        if len(self.units_by_hour) != self.window.hours:
            raise CensoringError(
                f"a curve over {len(self.units_by_hour)} hours cannot be read under a "
                f"{self.window.hours}-hour trading window."
            )
        if self.units < 1:
            raise CensoringError(
                "a curve fitted on zero units is not a curve. There is no shape to learn "
                "from days on which nothing sold, and a flat default would be invented."
            )

    @property
    def units(self) -> int:
        return sum(self.units_by_hour)

    def share_before(self, hour: int) -> Fraction:
        """The share of an ordinary day's demand that has arrived **before** `hour` begins.

        Before, not through. A shelf that emptied at 16:00 was on sale for the hours up to
        15:59 and for part of 16:00; counting the whole of 16:00 as traded would credit the
        day with demand that arrived after the shelf was bare, and the reconstruction would
        come out low. Low is the direction this module exists to prevent.
        """
        elapsed = self.units_by_hour[: self.window.index_of(hour)]
        return Fraction(sum(elapsed), self.units)

    def __str__(self) -> str:
        return (
            f"availability curve over {self.days} store-days, {self.units} units, "
            f"{self.window.hours} hours from {self.window.open_hour:02d}:00"
        )


def fit(days: Iterable[HourlySales], window: TradingWindow) -> AvailabilityCurve:
    """The intraday shape, learned only from store-days on which the shelf held.

    A censored day is **refused, not filtered**. Filtering would let a caller hand over a
    mixed pile and receive a curve fitted partly on the pathology it is about to correct —
    which is claim 4's trap wearing its plainest clothes: the corrector learning the
    censoring, then removing exactly as much of it as it learned and no more.

    Pooling is the caller's decision. This function fits one curve over whatever it is given,
    so a caller that wants a curve per category, per store format or per day of week calls it
    once per group. A grouping rule baked in here would be a second, silent modelling choice.
    """
    totals = [0] * window.hours
    counted = 0
    for day in days:
        if day.state.ran_out:
            raise CensoringError(
                f"{day.state.key} emptied at hour {day.state.stocked_out_from_hour} and cannot "
                "be fitted on. The curve is what a full day looks like; a censored day is "
                "what this curve is for."
            )
        if len(day.units_by_hour) != window.hours:
            raise CensoringError(
                f"{day.state.key} has {len(day.units_by_hour)} hours under a "
                f"{window.hours}-hour trading window."
            )
        for index, units in enumerate(day.units_by_hour):
            totals[index] += units
        counted += 1
    return AvailabilityCurve(window=window, units_by_hour=tuple(totals), days=counted)


# --------------------------------------------------------------------------- the correction


@dataclass(frozen=True, slots=True)
class DemandEstimate:
    """What one store-day is worth as a demand observation, and how much of it is evidence.

    `censored` travels with the number to whatever consumes it. Doctrine rule 2 is about a
    fallback price and it is the same rule here: a reconstructed store-day that arrives
    looking like an observed one is worse than a missing one, because it is silent and it
    teaches somebody to trust it.
    """

    at_least: int
    """What the shelf actually sold. Evidence, and a floor no reconstruction may go under."""

    units: int | None
    """The reconstruction, or `None` where the observed window is evidence of no rate."""

    censored: bool
    observed_share: Fraction
    """The share of an ordinary day the observed window covers. `1` on an uncensored day."""

    def __post_init__(self) -> None:
        if self.units is not None and self.units < self.at_least:
            raise CensoringError(
                f"a reconstruction of {self.units} units under the {self.at_least} the shelf "
                "actually sold. The observed units are evidence; an estimate below them "
                "contradicts a receipt."
            )

    @property
    def is_point_estimate(self) -> bool:
        return self.units is not None

    def __str__(self) -> str:
        if self.units is None:
            return f"at least {self.at_least} units, no point estimate"
        mark = " (reconstructed)" if self.censored else ""
        return f"{self.units} units{mark}"


def correct(reading: DemandReading, curve: AvailabilityCurve) -> DemandEstimate:
    """Expand a censored day by the share of itself that was on sale.

    An uncensored day passes through untouched, as an identity and not as an approximation
    that happens to land on the same integer: nothing was hidden, so there is nothing to
    reconstruct, and a correction that moved such a day would be inventing demand out of a
    curve rather than out of evidence.
    """
    if isinstance(reading, FullyObserved):
        return DemandEstimate(
            at_least=reading.units,
            units=reading.units,
            censored=False,
            observed_share=Fraction(1),
        )
    share = curve.share_before(reading.stocked_out_from_hour)
    if share == 0 or reading.at_least == 0:
        return DemandEstimate(
            at_least=reading.at_least, units=None, censored=True, observed_share=share
        )
    return DemandEstimate(
        at_least=reading.at_least,
        units=round_half_even(Fraction(reading.at_least) / share),
        censored=True,
        observed_share=share,
    )


def round_half_even(value: Fraction) -> int:
    """A non-negative exact fraction to the nearest whole unit, halves to the even one.

    Written out on integers rather than handed to `Decimal`, for the same reason
    `holdout.core.money` writes its three roundings out: a rounding that goes through a
    context has a mode somebody can change from a distance, and this one is part of the
    answer rather than a presentation detail.
    """
    if value < 0:
        raise CensoringError(f"{value} units. A demand estimate is not a negative quantity.")
    whole, remainder = divmod(value.numerator, value.denominator)
    twice = 2 * remainder
    if twice > value.denominator or (twice == value.denominator and whole % 2):
        whole += 1
    return whole
