"""The correction, written a second time and written to disagree.

Driving `correct` from outside answers *does it produce a bigger number than the naive
reading*. It does not answer *the right bigger number*, and if the only thing that knows
where the reconstruction lands is the function under test, the eval is asking it to mark its
own paper. So the arithmetic is done twice, and the two share the **rule** and nothing else:

=========  ==================================  ==================================================
           `holdout.core.demand.censoring`     here
=========  ==================================  ==================================================
shape      one normalised `AvailabilityCurve`  no curve and no share at all — raw unit totals
           of exact `Fraction` shares
structure  one accumulating pass over the      one full rescan of every fitted day per hour,
           fitted days, running totals         sixteen times over. Deliberately slow: a fast
                                               second implementation is one that made the same
                                               decisions as the first
operands   `at_least / share`, a division of   `at_least x total_units / units_before_the_hour`,
           a `Fraction`                        three integers, no division until the last step
rounding   twice the remainder against the     the two candidate integers, and the smaller of
           denominator                         the two distances to them
=========  ==================================  ==================================================

They may agree only because both are right. `C10` compares them as integers with **no
tolerance**, over every correction the eval performs — which is the direct check beside the
indirect ones, for the reason `evals/guardrail/README.md` gives about `G10`: a check that
reaches a boundary through a store-day only sees a misplaced boundary where a store-day
happens to land near it.

What the two do share, and it is not a helper
---------------------------------------------
The rule: *the observed window is the hours strictly before the shelf emptied, and the
reconstruction scales the observed units up by the share of an ordinary day those hours
carry.* That is the definition of the correction, so both implement it; it is the sentence
above the code, not a function either of them calls. Nothing in this module imports anything
from `holdout`.
"""

from __future__ import annotations

from collections.abc import Sequence

from holdout.core.demand.censoring import HourlySales, TradingWindow


def units_before(days: Sequence[HourlySales], window: TradingWindow) -> tuple[int, ...]:
    """For each trading hour, how many units the fitted days sold **before** it began.

    One full pass over every day per hour, summing that day's hours from the start each time.
    The core accumulates instead, in a single pass with a running total; a bug in either
    formulation of "before" — an inclusive slice, an index off by one, a running total updated
    after it is read — moves one of these tuples and not the other.
    """
    totals: list[int] = []
    for hour in range(window.open_hour, window.close_hour):
        boundary = hour - window.open_hour
        totals.append(sum(sum(day.units_by_hour[:boundary]) for day in days))
    return tuple(totals)


def total_units(days: Sequence[HourlySales]) -> int:
    """Every unit the fitted days sold, from the shelf record rather than from the hours.

    `HourlySales` refuses a day whose hours do not sum to what the shelf says it sold, so
    these are the same number by construction — which is the point of reading it off the
    other one. The core sums the hours.
    """
    return sum(day.state.units_sold for day in days)


def reconstruct(
    observed_units: int, hour: int, before: Sequence[int], grand_total: int, open_hour: int
) -> int | None:
    """The reconstruction, in integers, with no share ever formed.

    `None` where the core also declines to answer, for the same two reasons written out
    independently: an observed window of zero width, and an observed window that saw nothing.
    Both are *no evidence*, and a zero here would be the claim's own failure committed by the
    thing that checks for it.
    """
    index = hour - open_hour
    if not 0 <= index < len(before):
        raise ValueError(f"hour {hour} is outside the window this curve was fitted over")
    elapsed = before[index]
    if elapsed == 0 or observed_units == 0:
        return None
    return _nearest(observed_units * grand_total, elapsed)


def _nearest(numerator: int, denominator: int) -> int:
    """The whole number nearest `numerator / denominator`, halves to the even one.

    By the two distances rather than by the remainder: take the floor and the one above it,
    measure how far the exact value is from each, and keep the nearer. The core compares twice
    the remainder against the denominator, which is the same decision reached along a
    different road — and a tie is resolved to the even candidate in both, because the
    alternative rounds every half in one direction and a systematic half-unit is exactly the
    kind of drift this claim is about.
    """
    floor = numerator // denominator
    distance_down = numerator - floor * denominator
    distance_up = (floor + 1) * denominator - numerator
    if distance_up < distance_down:
        return floor + 1
    if distance_up > distance_down:
        return floor
    return floor if floor % 2 == 0 else floor + 1
