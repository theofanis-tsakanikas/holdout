"""The time split, and the leaks it refuses. `CLAUDE.md`: *time-based split, never random.*

Every refusal here is planted, and the plants are chosen for one reason: **each is a way the leak
actually arrives**, not a way it could be written down. A date in both halves is what a `<=` gives
where a `<` was meant; a boundary that touches is what an off-by-one in the slice gives; a
non-ISO date is what a source with a different locale gives. None of the three is exotic and all
three are silent — the model simply scores better than it is.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from pipelines.ml import split

from holdout.contracts.loader import load

SETTINGS = load().training


@dataclass(frozen=True)
class Row:
    business_date: str


def _dates(count: int) -> list[str]:
    return [f"2026-03-{day:02d}" for day in range(1, count + 1)]


def test_the_last_declared_days_evaluate_and_everything_before_trains() -> None:
    """The split point is derived from the contract and the data, never passed in."""
    dates = _dates(40)
    made = split.split(dates, SETTINGS)
    assert len(made.evaluate) == SETTINGS.evaluation_days
    assert len(made.train) == 40 - SETTINGS.evaluation_days
    assert made.boundary == dates[-SETTINGS.evaluation_days]
    assert max(made.train) < min(made.evaluate)


def test_a_date_in_both_halves_is_refused() -> None:
    """The leak this module exists to prevent, constructed directly rather than through `split`.

    Reached by building a `TimeSplit` rather than by calling `split`, because `split` cannot
    produce this shape — which is exactly why the type checks it: a caller that builds one by
    hand, or a future `split` with an off-by-one, is where it would come from.
    """
    with pytest.raises(split.SplitError, match="both halves"):
        split.TimeSplit(train=("2026-03-01", "2026-03-02"), evaluate=("2026-03-02",))


def test_a_boundary_that_touches_is_refused() -> None:
    """`>=` rather than `>`: training must end strictly before evaluation opens."""
    with pytest.raises(split.SplitError, match="strictly before"):
        split.TimeSplit(train=("2026-03-05",), evaluate=("2026-03-04",))


def test_an_empty_evaluation_half_is_refused() -> None:
    """A gate with nothing to judge passes. That is the vacuous green, at the split."""
    with pytest.raises(split.SplitError, match=r"empty population|no evaluation"):
        split.TimeSplit(train=("2026-03-01",), evaluate=())


def test_too_little_history_is_refused_rather_than_caveated() -> None:
    """Below `min_training_days` there is no model, not a model with a warning."""
    dates = _dates(SETTINGS.evaluation_days + SETTINGS.min_training_days - 1)
    with pytest.raises(split.SplitError, match="declared minimum"):
        split.split(dates, SETTINGS)


def test_a_corpus_shorter_than_the_evaluation_window_is_refused() -> None:
    """And the window is not shrunk to fit, which would be choosing the split after seeing it."""
    with pytest.raises(split.SplitError, match="would leave nothing"):
        split.split(_dates(SETTINGS.evaluation_days), SETTINGS)


def test_a_date_this_module_cannot_order_is_refused_rather_than_parsed() -> None:
    """The assumption `dates_of` relies on, guarded instead of trusted.

    This module orders dates by sorting their **text**. That is chronological for `YYYY-MM-DD` and
    for nothing else, so a source writing `04/03/2026` would be sorted into the wrong half with no
    error anywhere. The spellings planted here are the ones a real source produces — a European
    day-first date, an American month-first one, and a date with no padding — rather than
    gibberish, which no source has ever emitted.
    """
    for spelling in ("04/03/2026", "03/04/2026", "2026-3-4", "20260304", "March 4 2026"):
        with pytest.raises(split.SplitError, match="ISO business date"):
            split.dates_of([Row(business_date=spelling)])


def test_dates_are_deduplicated_and_ordered() -> None:
    """A corpus has many rows per date; the split is over dates, not over rows."""
    rows = [Row("2026-03-02"), Row("2026-03-01"), Row("2026-03-02")]
    assert split.dates_of(rows) == ("2026-03-01", "2026-03-02")
