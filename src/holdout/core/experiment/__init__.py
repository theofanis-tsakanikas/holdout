"""The experiment core — the lottery, the four validity checks, and the design-based estimator.

    draw(...)  -> SealedAssignment | None      the committed lottery, stratified
    close(...) -> Readout | ReadoutRefusal     four checks, then a number or a reason code

`strata` matches units into strata on a composite distance over the declared covariates —
the restriction the lottery draws under. `assignment` is the keyed-hash draw within those
strata and the seal — **the one door with no key**. `balance` is the standardised
difference, judged once, at readout, over what actually arrived. `exposure` is the ITT
threshold and the argument for why there is no exposure-adjusted number. `contamination`
re-derives the draw and compares what was delivered. `estimator` is Lin's adjustment, the
studentized statistic, the permutation test under the same restriction, and the interval
that inverts it. `readout` is moments 2 and 3.

**Validity comes from the lottery, not from the arithmetic.** A difference of means over
randomly assigned units is unbiased under any data-generating process; what the code here
has to do is not lose that on the way. Whether it does is claim 2, and claim 2 is measured
rather than asserted.
"""

from holdout.core.experiment.assignment import (
    AssignmentError,
    SealedAssignment,
    SealForgeryError,
    candidate,
    control_size_for,
    covariate_digest,
    digest_for,
    draw,
    rank_of,
    redraw,
    reference_set,
    sealed,
)
from holdout.core.experiment.balance import (
    BalanceError,
    CovariateKind,
    CovariateMatrix,
    CovariateValue,
    Standardised,
    standardised,
    worst_of,
)
from holdout.core.experiment.codes import (
    CHECK_OF,
    CHECK_ORDER,
    CODE_OF,
    Arm,
    ReadoutRefusalCode,
    ValidityCheck,
)
from holdout.core.experiment.contamination import Contamination
from holdout.core.experiment.estimator import (
    Design,
    EstimatorError,
    ReferencePlan,
    Statistic,
    adjusted_difference,
    design_of,
    difference_in_means,
    interval,
    permutation_p,
    plan_for,
    studentized,
)
from holdout.core.experiment.exposure import Exposure, ExposureError
from holdout.core.experiment.readout import (
    CheckResult,
    PeekError,
    Period,
    Readout,
    ReadoutError,
    ReadoutRefusal,
    close,
    may_read,
)
from holdout.core.experiment.strata import StrataError, composite_distance, strata_of

__all__ = [
    "CHECK_OF",
    "CHECK_ORDER",
    "CODE_OF",
    "Arm",
    "AssignmentError",
    "BalanceError",
    "CheckResult",
    "Contamination",
    "CovariateKind",
    "CovariateMatrix",
    "CovariateValue",
    "Design",
    "EstimatorError",
    "Exposure",
    "ExposureError",
    "PeekError",
    "Period",
    "Readout",
    "ReadoutError",
    "ReadoutRefusal",
    "ReadoutRefusalCode",
    "ReferencePlan",
    "SealForgeryError",
    "SealedAssignment",
    "Standardised",
    "Statistic",
    "StrataError",
    "ValidityCheck",
    "adjusted_difference",
    "candidate",
    "close",
    "composite_distance",
    "control_size_for",
    "covariate_digest",
    "design_of",
    "difference_in_means",
    "digest_for",
    "draw",
    "interval",
    "may_read",
    "permutation_p",
    "plan_for",
    "rank_of",
    "redraw",
    "reference_set",
    "sealed",
    "standardised",
    "strata_of",
    "studentized",
    "worst_of",
]
