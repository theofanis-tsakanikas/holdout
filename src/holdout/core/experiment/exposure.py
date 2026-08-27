"""Did the treatment actually happen? — and why there is no exposure-adjusted number.

`exposed_treated / assigned_treated`, against the declared `exposure_min_pct`. Below it the
readout refuses with `EXPOSURE_BELOW_THRESHOLD` and states no number. Above it the estimate
is **intention-to-treat** and the realised rate is printed beside it, pass or fail.

Exposure means the ESL acknowledgement arrived: the price reached the shelf. It is the only
evidence there is. Without it an experiment measures intentions instead of actions, and the
dilution runs toward zero — which is to say it makes a real effect look smaller and a null
look correct, and that is the direction that never gets questioned.

Why ITT is the only number here
-------------------------------
There is no CACE, no instrumental-variable estimate and no exposure-adjusted alternative in
this repository, and the absence is deliberate rather than pending. Three reasons, in
increasing order of how much they matter:

1. the readout vocabulary is **closed** and has no code for an exposure-adjusted refusal;
2. a `Readout` has no field for one, so reporting it would mean inventing a shape;
3. an exposure-adjusted number carries an **exclusion restriction** — the assumption that
   assignment affects the outcome only through exposure — and this readout is built to avoid
   assumptions, not to accumulate them. Where too little of the treatment happened, the
   honest output is a refusal that says so, which is a thing a reader can act on.

Only the treated arm is measured
--------------------------------
A control unit is exposed to the *existing* policy by definition — the holdout does not mean
nothing, it means what was already happening — so there is no acknowledgement to wait for
and nothing to fall short. Measuring "exposure" on both arms would produce a number that
looks symmetric and is not.
"""

from __future__ import annotations

from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from holdout.core.experiment.assignment import SealedAssignment
from holdout.core.money import decimal_of


class ExposureError(ValueError):
    """Exposure was measured over units the assignment does not cover."""


@dataclass(frozen=True, slots=True)
class Exposure:
    """How much of the treatment actually reached a shelf."""

    assigned_treated: int
    exposed_treated: int

    def __post_init__(self) -> None:
        if self.assigned_treated < 1:
            raise ExposureError(
                "no unit was assigned to treatment, so there is no exposure to measure. An "
                "exposure rate over an empty arm is not 100%, it is nothing."
            )
        if not 0 <= self.exposed_treated <= self.assigned_treated:
            raise ExposureError(
                f"{self.exposed_treated} of {self.assigned_treated} treated units exposed. "
                "More exposures than assignments means the acknowledgements are being "
                "counted against the wrong experiment."
            )

    @property
    def rate(self) -> Fraction:
        """The realised rate, exact, as a fraction of one."""
        return Fraction(self.exposed_treated, self.assigned_treated)

    @property
    def rate_pct(self) -> Decimal:
        """The figure the readout prints, pass or fail."""
        return decimal_of(self.rate * 100)

    def meets(self, minimum_pct: Decimal) -> bool:
        """Whether the declared threshold is met. Exact: no float, no rounding, no tolerance."""
        return self.rate >= Fraction(minimum_pct) / 100

    def __str__(self) -> str:
        return (
            f"{self.exposed_treated}/{self.assigned_treated} treated units exposed "
            f"({self.rate_pct:.2f}%)"
        )


def measure(seal: SealedAssignment, exposed: AbstractSet[str]) -> Exposure:
    """The realised exposure of the treated arm.

    `exposed` is every unit whose ESL acknowledgement arrived. Acknowledgements for control
    units and for units outside the roster are **refused rather than ignored**: an
    acknowledgement for a unit this experiment never assigned means the acknowledgements
    belong to a different experiment, or the arms have been crossed, and quietly filtering
    them out would turn either of those into a clean-looking number.
    """
    assigned = frozenset(seal.treatment)
    stray = sorted(frozenset(exposed) - frozenset(seal.roster))
    if stray:
        raise ExposureError(
            f"{len(stray)} acknowledgement(s) name units outside the roster: {stray[:8]}. "
            "Either these belong to another experiment or the assignment table is not the "
            "one the decisions were routed by; neither is something to filter out quietly."
        )
    control_exposed = sorted(frozenset(exposed) & frozenset(seal.control))
    if control_exposed:
        raise ExposureError(
            f"{len(control_exposed)} control unit(s) carry a treatment acknowledgement: "
            f"{control_exposed[:8]}. That is contamination, and it is the contamination "
            "check's finding rather than a number to average away here."
        )
    return Exposure(
        assigned_treated=len(assigned), exposed_treated=len(frozenset(exposed) & assigned)
    )
