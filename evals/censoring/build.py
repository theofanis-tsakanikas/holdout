"""Turn three adversarial worlds into store-days this system has to read demand off.

This is the only module that imports both sides. `corpus/world/` knows nothing about
`holdout` — `ops/isolation.py` is the one implementation of that rule, the boundary test is
the gate and the hook refuses the write — and `holdout.core.demand` knows nothing about the
corpus. The join lives here, where it can be read as one thing.

What comes from the corpus, and what does not
---------------------------------------------
===========================  ==========================================================
observed                     every unit sold, the hour it sold in, and whether the shelf
                             emptied that day and when. All four come out of the
                             simulation's stock arithmetic — a naive replenishment
                             forecast against a service factor, first-expired-first-out —
                             and **nobody chose which store-days run out**
---------------------------  ----------------------------------------------------------
derived, arithmetic stated   the hourly breakdown of a store-SKU-day, summed from POS
                             lines by `event_ts.hour`. `HourlySales` refuses a day whose
                             hours do not add up to the shelf record's `sold_qty`, so the
                             derivation cannot drift from the source it came from
---------------------------  ----------------------------------------------------------
**swept**, not claimed       the hour at which a held-out day is artificially censored.
                             A declared, deterministic grid — never drawn — so a red run
                             reproduces exactly. `CENSOR_HOUR_GRID` says what each
                             member is for
===========================  ==========================================================

Three worlds, and the third one is not decoration
-------------------------------------------------
`W1` is the null world running the contract ladder on every store; `W6` runs the candidate
markdown schedule on half of them, which moves trade later in the day and therefore changes
the very shape the correction is fitted on. `W5` is the world whose store-day demand is
heavy-tailed from half way through its calendar — built for claim 2, and the hardest possible
input for this one, because a shock the replenishment planner ordered for and the analyst
never saw is precisely what empties a shelf. None of the three was built to exercise claim 4.

**No module in this package may import `corpus.world.demand`.** That is where the simulator's
own intraday shape lives — `HOURLY_PROFILE`, the elasticities, the seasonal swing — and an
eval that read it would be handing the corrector the answer sheet.
`tests/evals/test_censoring_instrument.py` scans for it.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache

from corpus.world import events as world_events
from corpus.world import prepare
from corpus.world.events import PosLine, ShelfDay
from corpus.world.scale import CLOSE_HOUR, OPEN_HOUR

from holdout.core.demand.censoring import HourlySales, ShelfState, TradingWindow

#: The seed every figure this eval publishes was produced under. A world is a pure function
#: of `(world, seed, scale)`, so naming it is what makes a number reproducible rather than
#: anecdotal — and another seed is another chain with another mix of stock-outs.
SEED = "holdout-w-0001"

#: `rehearsal`: 20 stores x 24 SKUs x 56 days, about 27,000 store-days and 380,000 POS lines
#: per world, in under two seconds. Claim 4 is graded on store-**days**, and this scale
#: supplies about eighty thousand of them across three worlds. The A/A harness's `harness`
#: scale trades SKUs for stores because claim 2 is graded on the surviving *roster*; nothing
#: here draws a lottery, so the roster is not the constraint and the calendar is.
SCALE = "rehearsal"

#: The three worlds, and why each earns its run — see the module docstring.
WORLDS: tuple[str, ...] = ("W1", "W5", "W6")

#: Where the calendar is cut. The curve is fitted on full-availability store-days **before**
#: this point and graded on full-availability store-days after it — a time split, never a
#: random one, for the same reason `CLAUDE.md` gives about training: a random split lets the
#: fit see a neighbouring day of the same week and grades itself on what it already knows.
#:
#: It costs accuracy and that cost is published rather than tuned away: the two halves fall in
#: different weeks of a season, so the shape drifts between them and the reconstruction comes
#: out slightly low. A random split would have made every figure in `C5` look better and would
#: have measured less.
FIT_SHARE_PCT = 60

#: The hours a held-out day is artificially censored at. Deterministic, declared, and three of
#: the six are here for a named reason rather than to fill a range:
#:
#: * `OPEN_HOUR` — the observed window has zero width, so the share is exactly 0 and there is
#:   no evidence to expand. **The corpus cannot reach this branch**: a shelf empties by being
#:   sold out, so a real stock-out at the first trading hour needs a delivery that rounded to
#:   nothing, which the generator's arithmetic does not currently produce. It is reached here
#:   the same way claim 1 reaches the guardrail window no contract date can resolve to;
#: * `OPEN_HOUR + 1` — a day that sold nothing in its first hour arrives with `at_least == 0`
#:   and a share above zero. That is the one line where dividing the evidence by the share
#:   returns zero, which is claim 4's sentence exactly: a stock-out read as zero demand;
#: * `CLOSE_HOUR - 1` — the last trading hour, where the naive reading looks most defensible
#:   and the correction is closest to a no-op. A gate shown to bite only where the error is
#:   enormous has not been shown to bite.
CENSOR_HOUR_GRID: tuple[int, ...] = (OPEN_HOUR, OPEN_HOUR + 1, 12, 16, 19, CLOSE_HOUR - 1)

#: The trading window the corpus's stores keep. Read off the corpus's own scale rather than
#: restated here: an hour index means nothing without the window it is an index into, and two
#: places declaring the shop's opening time is one place too many.
WINDOW = TradingWindow(open_hour=OPEN_HOUR, close_hour=CLOSE_HOUR)


@dataclass(frozen=True, slots=True)
class WorldDays:
    """One world's store-days, split by the calendar into what fits and what grades."""

    world: str
    split_date: str
    days: tuple[HourlySales, ...]

    @property
    def held(self) -> tuple[HourlySales, ...]:
        """Store-days on which the shelf never emptied — the only ones a curve is fitted on."""
        return tuple(day for day in self.days if not day.state.ran_out)

    @property
    def ran_out(self) -> tuple[HourlySales, ...]:
        """Store-days the shelf emptied on. The population claim 4 is about."""
        return tuple(day for day in self.days if day.state.ran_out)

    @property
    def fit_days(self) -> tuple[HourlySales, ...]:
        return tuple(d for d in self.held if d.state.business_date < self.split_date)

    @property
    def graded_days(self) -> tuple[HourlySales, ...]:
        """The held-out segment with full shelf availability — where there is no censoring to
        correct, so a correction has nowhere to hide and its error is measurable against a
        truth the corpus emitted rather than one the simulator declared."""
        return tuple(d for d in self.held if d.state.business_date >= self.split_date)


@lru_cache(maxsize=1)
def worlds() -> tuple[WorldDays, ...]:
    """Every world, generated once. The eval runs several passes over the same store-days."""
    return tuple(_one_world(world) for world in WORLDS)


def _one_world(world: str) -> WorldDays:
    run = prepare(world, seed=SEED, scale=SCALE)
    hours: dict[tuple[str, str, str], list[int]] = defaultdict(lambda: [0] * WINDOW.hours)
    shelf: list[ShelfDay] = []
    for event in world_events(run):
        if isinstance(event, ShelfDay):
            shelf.append(event)
        elif isinstance(event, PosLine):
            key = (event.store_id, event.sku_id, event.event_ts.date().isoformat())
            hours[key][WINDOW.index_of(event.event_ts.hour)] += event.qty
    days = tuple(
        HourlySales(
            state=ShelfState(
                store_id=record.store_id,
                sku_id=record.sku_id,
                business_date=record.business_date,
                units_sold=record.sold_qty,
                stocked_out_from_hour=record.stocked_out_from_hour,
            ),
            units_by_hour=tuple(
                hours.get(
                    (record.store_id, record.sku_id, record.business_date), [0] * WINDOW.hours
                )
            ),
        )
        for record in shelf
    )
    return WorldDays(world=world, split_date=_split_date(days), days=days)


def _split_date(days: tuple[HourlySales, ...]) -> str:
    """The first business date of the held-out segment.

    Taken from the calendar the world actually produced rather than from the scale's declared
    start and length, so a world that ever emitted a shorter calendar splits its own days and
    does not silently grade on all of them.
    """
    dates = sorted({day.state.business_date for day in days})
    if len(dates) < 2:
        raise ValueError(
            f"{len(dates)} business date(s) in the corpus. A time split needs a calendar; "
            "grading a curve on the days it was fitted on is the thing this split exists to "
            "make impossible."
        )
    return dates[len(dates) * FIT_SHARE_PCT // 100]
