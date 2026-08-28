"""The design engine — one form, three sources, and the same answer for all of them.

    assess(form, ...) -> Feasible | DesignRefusal

Moment 1 of three: *can this experiment exist?* A human, a declared policy or the agent may
fill the nine fields; the engine does not know and does not care which, and a test runs one
identical form under all three attributions and asserts the three results are equal.

`form` mirrors `contracts/design/form.schema.yaml`; `feasibility` is the eight refusals and
the sizing arithmetic, including the interference table that is **derived** from the
contract's `carryover:` block rather than written out; `codes` is the closed vocabulary and
the scope-versus-judgment split claim 6's numbers have to be reported against; `refusal` is
the answer, returned rather than raised.

**The engine never chooses what to test and never decides what to do about the answer.** It
decides only what may be claimed.
"""

from holdout.core.design.codes import (
    DESIGN_PRECEDENCE,
    JUDGMENT_REFUSALS,
    SCOPE_REFUSALS,
    DesignRefusalCode,
)
from holdout.core.design.feasibility import (
    FeasibilityError,
    Feasible,
    assess,
    form_digest_of,
    interference_of,
    neighbour_exclusions,
)
from holdout.core.design.form import (
    DecisionRule,
    DesignForm,
    DesignFormError,
    Exclusion,
    FilledBy,
    FilledByKind,
    Intervention,
    MaxDuration,
    Mde,
    MdeDirection,
    MdeKind,
    Scope,
    StoppingKind,
    StoppingRule,
    Unit,
)
from holdout.core.design.refusal import DesignRefusal, DesignRefusalReason

__all__ = [
    "DESIGN_PRECEDENCE",
    "JUDGMENT_REFUSALS",
    "SCOPE_REFUSALS",
    "DecisionRule",
    "DesignForm",
    "DesignFormError",
    "DesignRefusal",
    "DesignRefusalCode",
    "DesignRefusalReason",
    "Exclusion",
    "FeasibilityError",
    "Feasible",
    "FilledBy",
    "FilledByKind",
    "Intervention",
    "MaxDuration",
    "Mde",
    "MdeDirection",
    "MdeKind",
    "Scope",
    "StoppingKind",
    "StoppingRule",
    "Unit",
    "assess",
    "form_digest_of",
    "interference_of",
    "neighbour_exclusions",
]
