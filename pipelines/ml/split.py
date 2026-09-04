"""The time-based split, and the four ways it refuses.

`CLAUDE.md`: *"Time-based split, never random."* The sentence is one line and the reason is the
whole of this module: a random split puts a Tuesday in the evaluation half whose Wednesday is in
the training half, so the model is asked to predict a day it has already been shown the answer to
either side of. The error that produces is not large — it is *flattering*, which is worse, because
nothing goes red and the number that reaches a model card is better than the model.

**The split point is derived, never chosen.** `evaluation_days` is declared in
`contracts/ml/training.yaml` and the boundary falls that many distinct business dates before the
last one in the data. A split point passed as an argument is a split point somebody can move after
seeing the result, which is the same degree of freedom `balance_covariates.yaml` closes for
experiments: anything that can be chosen after the fact will be chosen after the fact.

What it refuses, and why each one is a refusal rather than a warning
--------------------------------------------------------------------
* **too few training dates** — below `min_training_days` the fit does not happen. A model fitted
  on ten days and shipped with a caveat is a model shipped, because the caveat is not read;
* **an empty evaluation half** — a gate with nothing to judge passes, which is the vacuous green
  this repository files against itself more often than any other defect;
* **a date in both halves** — the leak this module exists to prevent, checked rather than assumed;
* **a training date after the boundary** — the same leak wearing the other direction, and the one
  a `>=` written as `>` produces.

The dates are compared as ISO strings, which sort as dates for exactly the format silver writes.
That is a property of the format rather than a coincidence, and `tests/pipelines/test_ml_split.py`
plants a non-ISO date to check that the assumption is guarded rather than relied upon.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from holdout.contracts.model import TrainingSettings

#: Exactly what silver writes, and the only shape whose lexical order is its chronological one.
#: Anything else is refused rather than parsed, because a parser here would accept `03/09/2026`
#: and sort it into the wrong half in silence.
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SplitError(ValueError):
    """A split that would leak, or one there is not enough history to make."""


@dataclass(frozen=True, slots=True)
class TimeSplit:
    """Which business dates train and which evaluate. Disjoint, ordered, and non-empty."""

    train: tuple[str, ...]
    evaluate: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.train:
            raise SplitError("a split with no training dates is not a split")
        if not self.evaluate:
            raise SplitError(
                "a split with no evaluation dates would let every gate below it pass over an "
                "empty population, which is a green run that measured nothing"
            )
        overlap = sorted(set(self.train) & set(self.evaluate))
        if overlap:
            raise SplitError(
                f"{len(overlap)} date(s) are in both halves, beginning {overlap[:3]}. A date "
                "the model was fitted on cannot also be a date it is judged on."
            )
        if max(self.train) >= min(self.evaluate):
            raise SplitError(
                f"training runs to {max(self.train)} and evaluation opens at "
                f"{min(self.evaluate)}. Every training date must fall strictly before every "
                "evaluation date, or the model is being shown days on both sides of the ones "
                "it is asked to predict."
            )

    @property
    def boundary(self) -> str:
        """The first evaluation date. Named, because a reader checking a leak looks for it."""
        return min(self.evaluate)


def dates_of(rows: Iterable[object], *, attribute: str = "business_date") -> tuple[str, ...]:
    """Every distinct business date in a pile of rows, sorted, validated as ISO.

    Separated from `split` so the validation has a caller that is not the split: a helper only
    the expensive path exercises is a helper nobody exercises.
    """
    found: set[str] = set()
    for row in rows:
        value = getattr(row, attribute)
        if not isinstance(value, str) or not ISO_DATE.match(value):
            raise SplitError(
                f"{value!r} is not an ISO business date. This module orders dates by sorting "
                "their text, which is chronological for `YYYY-MM-DD` and for nothing else — a "
                "date in another format would be sorted into the wrong half without an error."
            )
        found.add(value)
    return tuple(sorted(found))


def split(dates: Sequence[str], settings: TrainingSettings) -> TimeSplit:
    """The last `evaluation_days` distinct dates evaluate; everything before them trains.

    Takes the dates rather than the rows, so the same function is used by the pipeline and by a
    test that never builds a corpus. Takes the settings rather than two integers, so the numbers
    arrive from the contract and cannot be passed in from a call site that liked them better.
    """
    ordered = tuple(sorted(set(dates)))
    if len(ordered) <= settings.evaluation_days:
        raise SplitError(
            f"{len(ordered)} distinct date(s) against an evaluation half of "
            f"{settings.evaluation_days}. Holding out the declared window would leave nothing "
            "to train on, and shrinking the window to fit the data is choosing the split after "
            "seeing it."
        )
    train = ordered[: -settings.evaluation_days]
    if len(train) < settings.min_training_days:
        raise SplitError(
            f"{len(train)} training date(s) against a declared minimum of "
            f"{settings.min_training_days}. The fit is refused rather than produced: a model "
            "fitted on too little history and shipped with a caveat is a model shipped, "
            "because the caveat is not what reaches the shelf."
        )
    return TimeSplit(train=train, evaluate=ordered[-settings.evaluation_days :])
