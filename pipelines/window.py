"""When the comparison window opens and closes, derived once from the corpus's own calendar.

**Three consumers have to agree about this and none of them can be the authority.** The design
step measures covariates over the eight weeks before the window; the ingest step generates the
window's days under the committed assignment; the readout step reads outcomes over the window.
A date computed separately in three places is three chances for a slice to overlap or leave a
gap, and both of those look exactly like data.

**Derived rather than passed.** The alternative is three command-line arguments threaded through
a workflow, which is the same three definitions with a longer path between them. What the window
actually is is a property of the scale: the last whole ISO weeks of the world the estate loaded,
and the eight before them.

Nothing here reads a clock. `corpus/world/scale.py` declares a start date and a length, and this
is arithmetic over the two — so a readout replayed a year from now looks at the same days.
"""

from __future__ import annotations

from datetime import date, timedelta

from corpus.world.scale import Scale, scale_by_name

#: The comparison window and the covariates' declared lookback, in ISO weeks. Both eight, and
#: `evals/uplift/design.py` declares the same two — `tests/pipelines/test_experiments.py` compares
#: them, because a window that differed between the harness and the estate would make the
#: harness's measured refusal rate a rate about a different experiment.
PERIOD_WEEKS = 8
PRE_PERIOD_WEEKS = 8


class WindowError(ValueError):
    """The world is too short to carry a pre-period and a comparison window."""


def _scale(scale: Scale | str) -> Scale:
    return scale if isinstance(scale, Scale) else scale_by_name(scale)


def last_monday(scale: Scale | str) -> date:
    """The first day after the last **whole** ISO week the world covers.

    A world that ends mid-week has a final partial week, and a window whose last week is partial
    is a window one store-week short in every arm. The boundary is taken at a Monday so that the
    metric models' `YYYY-Www` and this arithmetic mean the same thing by a week.
    """
    the_scale = _scale(scale)
    end = the_scale.start_date + timedelta(days=the_scale.days)
    return end - timedelta(days=end.isoweekday() - 1)


def window(scale: Scale | str) -> tuple[date, date]:
    """`[opens, closes)` — the comparison window, as a half-open range of days."""
    closes = last_monday(scale)
    opens = closes - timedelta(weeks=PERIOD_WEEKS)
    if opens < _scale(scale).start_date + timedelta(weeks=PRE_PERIOD_WEEKS):
        raise WindowError(
            f"a world of {_scale(scale).days} days cannot carry {PRE_PERIOD_WEEKS} weeks of "
            f"pre-period and {PERIOD_WEEKS} weeks of comparison window. The scale is the "
            "decision here, not this arithmetic: load a longer one."
        )
    return opens, closes


def baseline(scale: Scale | str) -> tuple[date, date]:
    """`[opens, closes)` — everything before the window. The estate's baseline."""
    return _scale(scale).start_date, window(scale)[0]


def iso_weeks(opens: date, closes: date) -> tuple[str, ...]:
    """Every `YYYY-Www` in a half-open range of days, in the shape the metric models write."""
    weeks: list[str] = []
    day = opens
    while day < closes:
        year, week, _ = day.isocalendar()
        label = f"{year:04d}-W{week:02d}"
        if label not in weeks:
            weeks.append(label)
        day += timedelta(days=1)
    return tuple(weeks)


#: What `--day` accepts in place of a date, so the live day has one definition rather than a
#: date computed in a workflow and hoped to match the window's end.
AFTER_WINDOW = "after-window"


def live_day(scale: Scale | str) -> date:
    """The first day after the comparison window closes. The day `run` drives.

    **Held out by construction rather than by declaration.** `backfill.yml` says the time split
    *falls out of the sequence rather than being imposed*: training ends where the loaded history
    ends, the window ends there too, and this is the day after. Nothing that produced the model
    or the readout has seen it.
    """
    return window(scale)[1]
