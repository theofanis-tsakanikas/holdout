"""The envelope and the certificate type — what claim 1 rests on.

    certify(proposal, envelope) -> CertifiedPrice | Refusal

and `dispatch_to_shelf` accepts a `CertifiedPrice` and nothing else. `certificate` explains
exactly which forgery routes are closed and which two Python does not let anyone close;
`envelope` explains the seam that lets an independent corpus drive the gates without
importing anything private, which is what keeps claim 1 from becoming one function agreeing
with itself.
"""

from holdout.core.guardrails.benchmark import (
    BenchmarkError,
    MarginOnPrice,
    MarkupOnCost,
)
from holdout.core.guardrails.certificate import (
    CertificateForgeryError,
    CertifiedPrice,
    Refusal,
    certified,
    certify,
    dispatch_to_shelf,
)
from holdout.core.guardrails.codes import PRECEDENCE, GuardrailId, RefusalCode
from holdout.core.guardrails.envelope import (
    Announcement,
    AnnouncementBasis,
    Assessment,
    Bound,
    Envelope,
    EnvelopeError,
    FloorRule,
    Freshness,
    FrozenCategoriesRule,
    GuardrailRefusal,
    MarginCapRule,
    MaxDeltaRule,
    PriceBounds,
    PriorPriceRule,
    ProposalError,
    ProposedPrice,
    envelope_as_of,
    evaluate,
)

__all__ = [
    "PRECEDENCE",
    "Announcement",
    "AnnouncementBasis",
    "Assessment",
    "BenchmarkError",
    "Bound",
    "CertificateForgeryError",
    "CertifiedPrice",
    "Envelope",
    "EnvelopeError",
    "FloorRule",
    "Freshness",
    "FrozenCategoriesRule",
    "GuardrailId",
    "GuardrailRefusal",
    "MarginCapRule",
    "MarginOnPrice",
    "MarkupOnCost",
    "MaxDeltaRule",
    "PriceBounds",
    "PriorPriceRule",
    "ProposalError",
    "ProposedPrice",
    "Refusal",
    "RefusalCode",
    "certified",
    "certify",
    "dispatch_to_shelf",
    "envelope_as_of",
    "evaluate",
]
