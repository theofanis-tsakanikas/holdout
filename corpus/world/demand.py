"""What a shopper does. The behaviour a world injects an effect on.

Everything here is a *multiplier on a rate*, and the rate is a count of receipt lines. Nothing
in this module knows what a margin is, what an arm is, or that an experiment exists. That is
not tidiness: `CLAUDE.md`'s answer to *"your simulator is rigged"* is that validity comes from
the lottery and not from the simulator, and the way that answer stays true is that the
simulator never learns which lottery it is inside.

The shape, stated as an assumption
----------------------------------
Baseline demand by store, category, hour, weather and season; a non-linear price response with
reference-price memory; cross-price effects between substitutes. Those five are the five
`CLAUDE.md` names, and the functional forms below are the scenario's own assumptions about
grocery retail — a constant-elasticity response, an exponentially weighted reference price, a
sinusoidal season. They are shaped to be plausible. **No chain's real figures were obtained and
none is claimed**, which is the same sentence `contracts/policies/ladder_policy@v1.yaml` uses
about its own rungs.

Why the form does not matter as much as it looks like it should
---------------------------------------------------------------
A model-based estimator would have to be right about all of this. A design-based one does not:
a difference of means over randomly assigned units is unbiased whatever generated the data.
So the point of getting these shapes plausible is **not** to make the estimate correct — it is
to make the *machinery* work hard: reference-price memory is what makes a store-week unit
interfere with itself, cross-price effects are what make a store-category unit interfere with
itself, and censoring is what makes a stock-out look like zero demand to anyone not paying
attention.
"""

from __future__ import annotations

import math
from random import Random

from corpus.world import rng

#: Lines per SKU per store per trading day, before every multiplier below. Calibrated so the
#: scenario scale lands near `CLAUDE.md`'s "about 36M POS lines" — the realised count is
#: measured by `python -m corpus.world count --scale scenario` and recorded in the README,
#: never inferred from this constant.
BASE_LINES_PER_SKU_DAY = 13.7

#: Monday through Sunday. Saturday is the week's shop; Sunday is short trading.
DOW_FACTOR: tuple[float, ...] = (0.86, 0.84, 0.92, 1.02, 1.24, 1.38, 0.62)

#: 07:00 to 22:00 inclusive. Two humps — late morning and after work — and a thin middle,
#: which is what gives an afternoon markdown somewhere to bite.
HOURLY_PROFILE: tuple[float, ...] = (
    0.030,
    0.052,
    0.078,
    0.092,
    0.086,
    0.070,
    0.055,
    0.048,
    0.052,
    0.066,
    0.088,
    0.104,
    0.096,
    0.058,
    0.015,
    0.010,
)

#: How far the season swings demand, and where its peak sits in the year.
SEASON_AMPLITUDE = 0.12
SEASON_PEAK_DAY_OF_YEAR = 355

#: A hot day at a Greek supermarket: more dairy, less bread, poultry roughly flat.
WEATHER_SENSITIVITY: dict[str, float] = {"dairy": 0.16, "bakery": -0.11, "poultry": 0.03}

#: How much of last week's price a shopper still carries into today's judgement. 0 would mean
#: no memory at all and a store-week would stop interfering with itself.
REFERENCE_PRICE_DECAY = 0.82

#: How much of a substitute's discount comes out of this SKU's demand.
CROSS_PRICE_PULL = 0.45

#: Two baskets, same till, same second, identical contents, different receipts. Rare, real,
#: and the exact case `CLAUDE.md` says deduplication must not collapse: *"The same receipt
#: line delivered twice is one event; two identical baskets in the same second at the same
#: till are two."* It is injected deliberately rather than waited for, because a pathology
#: that only appears at some scales is a pathology no test can rely on.
TWIN_BASKETS_PER_10K = 6

#: Lines per basket, and units per line, in the ordinary worlds. W5 replaces the second with a
#: Pareto draw and leaves the first alone.
BASKET_LINES: tuple[float, ...] = (0.46, 0.28, 0.14, 0.07, 0.03, 0.02)
LINE_UNITS: tuple[float, ...] = (0.72, 0.19, 0.06, 0.02, 0.01)
MAX_UNITS_PER_LINE = 40


def season_factor(day_of_year: int) -> float:
    """A smooth annual swing. Peaks in the week before Christmas, troughs in June."""
    phase = 2.0 * math.pi * (day_of_year - SEASON_PEAK_DAY_OF_YEAR) / 365.25
    return 1.0 + SEASON_AMPLITUDE * math.cos(phase)


def weather_index(seed: str, store_id: str, business_date: str) -> float:
    """A single number standing in for the day's weather at a store, centred on zero.

    Shared by every SKU in the store that day, because weather is a property of the day and
    not of the product — which is what makes it a *common shock*, the thing that makes two
    stores' outcomes correlated and therefore the thing a paired analysis would want.
    """
    return rng.normal(rng.stream(seed, "weather", store_id, business_date), 0.0, 1.0)


def weather_factor(category: str, index: float) -> float:
    return max(0.4, 1.0 + WEATHER_SENSITIVITY.get(category, 0.0) * index)


def price_factor(displayed_cents: int, reference_cents: float, elasticity: float) -> float:
    """Constant elasticity against the shopper's remembered price, not against the base price.

    Reference-price memory is why this takes a remembered price at all. A store that has been
    marking down all week has taught its shoppers a lower normal, so the same absolute price
    is a smaller cut than it was on Monday — and that is precisely the carryover
    `contracts/design/inference.yaml` declares, and precisely why a `store_week` unit
    guarantees interference with itself.
    """
    if reference_cents <= 0.0:
        return 1.0
    ratio = displayed_cents / reference_cents
    return max(0.05, min(6.0, float(ratio**-elasticity)))


def updated_reference(previous_cents: float, displayed_cents: int) -> float:
    """Today's displayed price folded into the remembered one."""
    return REFERENCE_PRICE_DECAY * previous_cents + (1.0 - REFERENCE_PRICE_DECAY) * displayed_cents


def cross_price_factor(substitute_discount: float) -> float:
    """A substitute on offer takes trade off this SKU, in proportion to how deep the offer is."""
    return max(0.2, 1.0 - CROSS_PRICE_PULL * substitute_discount)


def novelty_factor(day_index: int, boost_pct: int, half_life_days: int | None) -> float:
    """W4's decay. 1.0 everywhere else, so the ordinary worlds pay nothing for it."""
    if half_life_days is None or boost_pct == 0:
        return 1.0
    return 1.0 + (boost_pct / 100.0) * float(0.5 ** (day_index / half_life_days))


def units_on_line(draw: Random, tail_alpha: float | None) -> int:
    """How many of it went into the basket.

    The ordinary answer is one, sometimes two. W5's answer has infinite variance, which is
    what a power calculation assuming a well-behaved basket does not survive — and the reason
    that world's correct behaviour is *the power check fails, or the interval is honestly
    wide*, rather than a number.
    """
    if tail_alpha is not None:
        return rng.pareto_units(draw, tail_alpha, MAX_UNITS_PER_LINE)
    return rng.choice_index(draw, LINE_UNITS) + 1


def lines_in_basket(draw: Random) -> int:
    return rng.choice_index(draw, BASKET_LINES) + 1
