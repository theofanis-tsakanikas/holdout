"""What the evaluation half says about a fitted model. Numbers only — it decides nothing.

Separated from `promotion.py` on purpose. This module measures and that module judges, so a
threshold cannot be quietly relaxed by the code that computes the quantity it is compared
against — which is the same separation `evals/` keeps between a `Report`'s figures and the
`Check` that passes or fails on them.

Why calibration is the gate above RMSE
--------------------------------------
`CLAUDE.md`: *"Calibration is gated above RMSE: a model that is systematically optimistic by 20%
sets systematically low prices, and every individual price still passes every guardrail."* That
last clause is the whole argument. The envelope is a per-price check — floor, cap, prior price,
max delta — and a uniform 20% optimism moves every price by a little, inside every bound, in the
same direction. **No guardrail can see it, and this is the only thing that can.**

RMSE is kept beside it rather than instead of it, because calibration alone passes a model that
is unbiased and useless: predicting the grand mean everywhere is perfectly calibrated.

Why the same test is applied per segment
-----------------------------------------
A total calibration of zero can be two segments wrong in opposite directions by the same amount.
A price is decided inside a segment and never over the average of all of them, so a model that
is 15% high on bakery and 15% low on poultry is wrong twice and reads as perfect once.

**A segment below the declared day count is reported and not judged**, with its size printed. The
alternative — judging a segment of three days — is reading noise as a defect, and the reasonable
response to a gate that fires on noise is to widen it until it stops, which is how a gate is
disarmed by people acting sensibly.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pipelines.ml.features import DemandFeature
    from pipelines.ml.model import DemandModel


class CalibrationError(ValueError):
    """A measurement that cannot be taken over the rows it was handed."""


@dataclass(frozen=True, slots=True)
class SegmentCalibration:
    """One segment's calibration, and whether there were enough days to judge it."""

    segment: tuple[str, int]
    days: int
    observed: int
    predicted: Fraction
    standard_error_pct: Decimal
    """The sampling standard error of this segment's observed total, as a percentage of it.

    **Carried so the gate can be a multiple of it rather than a fixed percentage.** Measured on
    `W1` at `rehearsal`: the median segment's standard error is 5.13%, so a flat ±10% tolerance —
    which is what this contract first declared — is 1.9 standard errors, and over twenty-one
    segments that is an expected 1.2 false alarms every run. A gate that fires on noise most runs
    is a gate somebody widens until it stops.
    """

    @property
    def sigmas(self) -> Decimal:
        """How many of this segment's own standard errors the calibration error is.

        The quantity the per-segment gate judges. A segment with three hundred days and one with
        thirty get the same test in the units that matter, instead of the same percentage in units
        that mean different things.
        """
        if self.standard_error_pct == 0:
            raise CalibrationError(
                f"segment {self.segment} has a standard error of zero, so every deviation is "
                "infinitely many of them. That is a segment whose every day sold exactly the "
                "same, which is a corpus property rather than a model that is certain."
            )
        error = Decimal(self.error_pct.numerator) / Decimal(self.error_pct.denominator)
        return (abs(error) / self.standard_error_pct).quantize(Decimal("0.01"))

    @property
    def error_pct(self) -> Fraction:
        """Signed, as a percentage of observed. Positive is a model predicting too much.

        **Signed rather than absolute**, because the direction is the decision-relevant half: a
        model that predicts too much demand sets prices too high and leaves stock on the shelf; one
        that predicts too little marks down what would have sold. A gate compares the magnitude and
        a human reads the sign.
        """
        if self.observed == 0:
            raise CalibrationError(
                f"segment {self.segment} observed zero units, so a percentage error has no "
                "denominator. A segment with no demand is excluded before this point, not "
                "divided by."
            )
        return (self.predicted - self.observed) * 100 / self.observed


@dataclass(frozen=True, slots=True)
class Calibration:
    """The whole evaluation half's verdict, as numbers with no threshold applied.

    `Fraction` for the ratios and `Decimal` for RMSE, and the split is not cosmetic: the ratios
    are exact rational arithmetic over counts, while a root is irrational and has to be rounded
    somewhere. Rounding it here, once, in a named place, beats rounding it wherever it is printed.
    """

    rows: int
    observed: int
    predicted: Fraction
    squared_error: Fraction
    baseline_squared_error: Fraction
    """The same quantity for a model that predicts the training grand rate everywhere.

    **Carried so the RMSE gate can be a ratio rather than a count of units.** A ceiling in units
    has to know the scale of demand, and the scale is a property of the corpus: this repository's
    first attempt declared six units against a corpus whose mean store-SKU-day is thirty-four, so
    the gate refused every model that could ever be fitted. A ratio against the do-nothing
    baseline asks the question the gate is actually for — *did this model learn anything* — and it
    asks it at any scale.
    """

    segments: tuple[SegmentCalibration, ...]
    censored_rows: int

    @property
    def error_pct(self) -> Fraction:
        """The total calibration error, signed, as a percentage of observed units."""
        if self.observed == 0:
            raise CalibrationError(
                "the evaluation half observed zero units in total. There is nothing to be "
                "calibrated against, and a model cannot pass a test with no denominator."
            )
        return (self.predicted - self.observed) * 100 / self.observed

    @property
    def rmse(self) -> Decimal:
        """Root mean squared error in units per store-SKU-day, to four places.

        Rounded rather than exact because it is the one quantity here that is not rational, and
        four places is far below any threshold this contract declares — so the rounding cannot
        move a verdict, which is the property that makes rounding it acceptable at all.
        """
        mean = self.squared_error / self.rows
        return (
            (Decimal(mean.numerator) / Decimal(mean.denominator)).sqrt().quantize(Decimal("0.0001"))
        )

    @property
    def baseline_rmse(self) -> Decimal:
        """What predicting the training grand rate everywhere would have scored."""
        mean = self.baseline_squared_error / self.rows
        return (
            (Decimal(mean.numerator) / Decimal(mean.denominator)).sqrt().quantize(Decimal("0.0001"))
        )

    @property
    def rmse_share_of_baseline(self) -> Decimal:
        """The model's RMSE as a share of the baseline's. Below 1 is better than doing nothing.

        The quantity the gate judges, and the reason it is a share: it is scale-free, so the same
        threshold means the same thing on a corpus of fifty units a day and one of five.
        """
        if self.baseline_rmse == 0:
            raise CalibrationError(
                "the baseline predicts the evaluation half exactly, so every model divides by "
                "zero here. That is a corpus with no variation in it, not a perfect model."
            )
        return (self.rmse / self.baseline_rmse).quantize(Decimal("0.0001"))

    def judged(self, min_segment_days: int) -> tuple[SegmentCalibration, ...]:
        """The segments large enough to be judged at the given size, and able to be.

        **A method taking the threshold, not a stored flag** — and it was a stored flag for an
        hour. `measure` computed `judged` from a `min_segment_days` it was handed, `assess` then
        read the result and compared its own contract value against a decision already made, and
        `P4`'s plant could not move it: raising the bar in `assess` changed nothing because the
        judging had happened one module earlier.

        That contradicted both modules' own docstrings — *this module measures and that module
        judges* — which is the defect this repository names most often: **prose describing a
        separation the code does not have.** It was found by a planted test failing, not by
        reading either file.
        """
        return tuple(
            segment
            for segment in self.segments
            if segment.days >= min_segment_days
            and segment.observed > 0
            and segment.standard_error_pct > 0
        )

    def unjudged(self, min_segment_days: int) -> tuple[SegmentCalibration, ...]:
        judged = set(self.judged(min_segment_days))
        return tuple(segment for segment in self.segments if segment not in judged)


def _standard_error_pct(units: Sequence[int]) -> Decimal:
    """The standard error of a segment's mean, as a percentage of that mean.

    Written out over integers rather than handed to `statistics`, for the reason
    `censoring.round_half_even` gives about its own rounding: this quantity is part of the answer
    a gate is judged on, not a presentation detail, and a function imported for it would put the
    definition somewhere a reader has to go and look.

    Returns zero for a segment of one day or a segment that sold nothing — both are shapes the
    gate must not divide by, and `SegmentCalibration.sigmas` refuses them by name rather than
    letting a zero become an infinite tolerance.
    """
    count = len(units)
    if count < 2:
        return Decimal(0)
    total = sum(units)
    if total == 0:
        return Decimal(0)
    mean = Fraction(total, count)
    # `sum` over an empty generator returns `int` 0, so the annotation is what keeps this exact
    # rather than letting one branch produce a float and the digest move with it.
    squared: Fraction = sum(((Fraction(value) - mean) ** 2 for value in units), Fraction(0))
    standard_error = squared / (count - 1) / count
    root = (Decimal(standard_error.numerator) / Decimal(standard_error.denominator)).sqrt()
    return (root * 100 / (Decimal(mean.numerator) / Decimal(mean.denominator))).quantize(
        Decimal("0.0001")
    )


def measure(model: DemandModel, features: Sequence[DemandFeature]) -> Calibration:
    """Predict every evaluation row and total the errors. **No threshold is applied here at all.**

    That sentence used to be true of everything except one argument: this function took
    `min_segment_days` and stamped a `judged` flag onto every segment, which is a threshold
    applied by the module that is not supposed to apply any. `Calibration.judged` now takes it, so
    the only numbers that cross into this file are the ones being measured.
    """
    if not features:
        raise CalibrationError(
            "no evaluation rows. A calibration over an empty half passes every threshold, which "
            "is a green run that measured nothing."
        )

    observed = sum(feature.units for feature in features)
    predicted = Fraction(0)
    units_by_segment: dict[tuple[str, int], list[int]] = {}
    squared = Fraction(0)
    baseline_squared = Fraction(0)
    per_segment: dict[tuple[str, int], list[Fraction | int]] = {}

    for feature in features:
        estimate = model.predict(
            sku_id=feature.sku_id,
            weekday=feature.weekday,
            store_id=feature.store_id,
            category=feature.category,
        )
        predicted += estimate
        squared += (estimate - feature.units) ** 2
        baseline_squared += (model.grand_rate - feature.units) ** 2
        units_by_segment.setdefault(feature.segment, []).append(feature.units)
        bucket = per_segment.setdefault(feature.segment, [0, 0, Fraction(0)])
        bucket[0] = int(bucket[0]) + 1
        bucket[1] = int(bucket[1]) + feature.units
        bucket[2] = Fraction(bucket[2]) + estimate

    segments = tuple(
        SegmentCalibration(
            segment=segment,
            days=int(count),
            observed=int(units),
            predicted=Fraction(total),
            standard_error_pct=_standard_error_pct(units_by_segment[segment]),
        )
        for segment, (count, units, total) in sorted(per_segment.items())
    )
    return Calibration(
        rows=len(features),
        observed=observed,
        predicted=predicted,
        squared_error=squared,
        baseline_squared_error=baseline_squared,
        segments=segments,
        censored_rows=sum(1 for feature in features if feature.censored),
    )
