"""The closed vocabularies of the experiment moment: the arms, the checks, the refusals.

The third place for the readout codes, exactly as `guardrails/codes.py` and
`design/codes.py` are for their moments: the set lives in
`contracts/schemas/reason_codes.schema.json`, the meanings live in
`contracts/vocabularies/reason_codes.yaml`, and this enum is the one the readout branches
on. `tests/core/test_refusal_codes.py` asserts all three agree in both directions.

The four checks are 1:1 with the four codes, and the map is written out
--------------------------------------------------------------------
Not because the mapping is hard, but because it is the thing that must not drift. The
contract already declares which check produces each code — `at_readout` carries a `check`
field for exactly this — so a code that acquired a second check, or a check that stopped
producing one, would be a readout that reports four figures and refuses for a reason none
of them explains. The bijection is asserted in both directions by a test.

`Arm` lives here rather than in `assignment`
--------------------------------------------
Both the lottery and the statistic it is judged by need it, and `assignment` calls
`balance`. Putting it in the module that names the vocabularies keeps the import direction
one-way, and it is a closed vocabulary like the other two: there are two arms, and the
holdout runs the *existing* policy rather than nothing.
"""

from __future__ import annotations

from enum import StrEnum
from types import MappingProxyType


class Arm(StrEnum):
    """Two, and only two.

    `CONTROL` is the holdout, and the holdout does not mean *nothing*: it runs the existing
    policy. Comparing a treatment against abandonment would inflate every uplift, which is
    a way of being wrong that always flatters.
    """

    TREATMENT = "treatment"
    CONTROL = "control"

    @property
    def other(self) -> Arm:
        return Arm.CONTROL if self is Arm.TREATMENT else Arm.TREATMENT


class ValidityCheck(StrEnum):
    """The four mandatory checks at close. All four run, always.

    A readout carries four figures whether or not one of them failed — a refusal that
    reported only the check that fired would make it impossible to see how close the others
    came, which is most of what a reader of a refused readout wants to know.
    """

    BALANCE = "balance"
    EXPOSURE = "exposure"
    CONTAMINATION = "contamination"
    POWER = "power"


class ReadoutRefusalCode(StrEnum):
    """The experiment ran; no number may be stated from it."""

    IMBALANCED_PRE_PERIOD = "IMBALANCED_PRE_PERIOD"
    EXPOSURE_BELOW_THRESHOLD = "EXPOSURE_BELOW_THRESHOLD"
    CONTAMINATED_ASSIGNMENT = "CONTAMINATED_ASSIGNMENT"
    POWER_NOT_REACHED = "POWER_NOT_REACHED"


#: The declared order the four checks run and are reported in. Balance first because it is
#: about the lottery, which everything else assumes held; then whether the treatment
#: actually happened; then whether the assignment survived; then whether the result can
#: carry the weight of the declared MDE.
CHECK_ORDER: tuple[ValidityCheck, ...] = (
    ValidityCheck.BALANCE,
    ValidityCheck.EXPOSURE,
    ValidityCheck.CONTAMINATION,
    ValidityCheck.POWER,
)

#: The bijection, written out. `CODE_OF` is derived from it rather than written twice: two
#: hand-written maps are two definitions, and the second one is the one that goes stale.
CHECK_OF: MappingProxyType[ReadoutRefusalCode, ValidityCheck] = MappingProxyType(
    {
        ReadoutRefusalCode.IMBALANCED_PRE_PERIOD: ValidityCheck.BALANCE,
        ReadoutRefusalCode.EXPOSURE_BELOW_THRESHOLD: ValidityCheck.EXPOSURE,
        ReadoutRefusalCode.CONTAMINATED_ASSIGNMENT: ValidityCheck.CONTAMINATION,
        ReadoutRefusalCode.POWER_NOT_REACHED: ValidityCheck.POWER,
    }
)

CODE_OF: MappingProxyType[ValidityCheck, ReadoutRefusalCode] = MappingProxyType(
    {check: code for code, check in CHECK_OF.items()}
)
