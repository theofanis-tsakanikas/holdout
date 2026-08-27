"""Can a `CertifiedPrice` exist that the envelope did not produce?

Claim 1 is that the actuation type cannot be constructed without a guardrail certificate.
This file attacks that from every direction Python offers, and it is deliberately written
as an attacker rather than as a user: each test is a way somebody would actually get a
price onto a shelf without passing the gates.

The last two tests are the honest half. They document the routes Python does not let a
library close, and assert the mitigation that exists instead — because a claim whose limits
are not written down is a claim nobody can check.
"""

from __future__ import annotations

import copy
import dataclasses
import pickle
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from holdout.core.decision import DecisionKey, DecisionPath, PriceSource, SafeState
from holdout.core.guardrails import (
    Bound,
    CertificateForgeryError,
    CertifiedPrice,
    Envelope,
    Freshness,
    GuardrailId,
    PriceBounds,
    ProposedPrice,
    Refusal,
    RefusalCode,
    certified,
    certify,
    dispatch_to_shelf,
)
from holdout.core.money import Money

ProposalFactory = Callable[..., ProposedPrice]


@pytest.fixture
def certificate(independent_envelope: Envelope, propose: ProposalFactory) -> CertifiedPrice:
    issued = certify(propose(price=Money.of("2.00")), independent_envelope)
    assert isinstance(issued, CertifiedPrice)
    return issued


# ------------------------------------------------------------------ the ordinary path


def test_a_price_that_passes_is_issued_a_certificate(certificate: CertifiedPrice) -> None:
    assert certified(certificate)
    assert certificate.price == Money.of("2.00")
    assert certificate.checks, "a certificate records which rules produced its bounds"


def test_a_price_that_fails_is_refused_and_not_raised(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """A refusal is a correct output, so it is returned. An exception is something a caller
    handles; a refusal is something a caller records."""
    result = certify(propose(price=Money.of("0.06")), independent_envelope)
    assert isinstance(result, Refusal)
    assert RefusalCode.BELOW_MARGIN_FLOOR in result.codes
    assert result.guardrails, "a refusal names every guardrail that fired"


def test_an_actuator_accepts_a_certificate_and_nothing_else(
    certificate: CertifiedPrice, independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    assert dispatch_to_shelf(certificate, certificate.key) is certificate
    refusal = certify(propose(price=Money.of("0.06")), independent_envelope)
    with pytest.raises(CertificateForgeryError):
        dispatch_to_shelf(refusal, certificate.key)  # type: ignore[arg-type]
    with pytest.raises(CertificateForgeryError):
        dispatch_to_shelf(Money.of("2.00"), certificate.key)  # type: ignore[arg-type]


def test_a_certificate_cannot_be_replayed_onto_another_decision(
    certificate: CertifiedPrice,
) -> None:
    """Without this, a certificate issued for a cheap item is a licence to write its price
    onto an expensive one."""
    elsewhere = DecisionKey(
        path=DecisionPath.MARKDOWN, sku_id="sku-2", store_id="store-7", occasion=2
    )
    with pytest.raises(CertificateForgeryError, match="binds to one decision"):
        dispatch_to_shelf(certificate, elsewhere)


# ------------------------------------------------------------------ the closed routes


def test_the_constructor_refuses() -> None:
    with pytest.raises(CertificateForgeryError, match="issued"):
        CertifiedPrice()
    with pytest.raises(CertificateForgeryError):
        CertifiedPrice(price=Money.of("0.01"))


def test_dataclasses_replace_does_not_apply_to_a_certificate(
    certificate: CertifiedPrice,
) -> None:
    """The one-liner a hurried adapter reaches for. `CertifiedPrice` is written by hand,
    while everything around it is a dataclass, exactly so that this does not work."""
    with pytest.raises(TypeError):
        dataclasses.replace(certificate, price=Money.of("0.01"))  # type: ignore[type-var]


def test_a_certificate_cannot_be_mutated(certificate: CertifiedPrice) -> None:
    with pytest.raises(CertificateForgeryError):
        certificate.price = Money.of("0.01")  # type: ignore[misc]
    with pytest.raises(CertificateForgeryError):
        del certificate.price
    with pytest.raises(CertificateForgeryError):
        certificate.anything = 1


def test_a_certificate_cannot_be_pickled(certificate: CertifiedPrice) -> None:
    """One that survived a round trip could be restored in a process where the envelope
    never ran, and the actuator there would have no way to tell."""
    with pytest.raises(CertificateForgeryError, match="serialisable"):
        pickle.dumps(certificate)


def test_copying_yields_the_same_object_rather_than_a_fillable_one(
    certificate: CertifiedPrice,
) -> None:
    assert copy.copy(certificate) is certificate
    assert copy.deepcopy(certificate) is certificate


def test_a_certificate_cannot_be_subclassed() -> None:
    with pytest.raises(TypeError, match="subclassed"):

        class Forged(CertifiedPrice):
            pass


def test_a_look_alike_is_not_a_certificate() -> None:
    """Duck typing is what claim 1 has to survive: an object with all the right attributes
    and none of the checks behind them."""

    class LooksRight:
        key = DecisionKey(
            path=DecisionPath.MARKDOWN, sku_id="sku-1", store_id="store-7", occasion=2
        )
        price = Money.of("0.01")
        source = PriceSource.MODEL
        marker = None
        decided_at = datetime(2026, 4, 1, 14, 0, tzinfo=UTC)

    assert not certified(LooksRight())
    with pytest.raises(CertificateForgeryError):
        dispatch_to_shelf(LooksRight(), LooksRight.key)  # type: ignore[arg-type]


# ------------------------------------------------------------------ the honest limits


def test_an_empty_shell_from_object_new_is_not_a_certificate() -> None:
    """Route one that Python does not let a class close: `object.__new__` always works.

    What is closed is what happens next. The instance has no slots set, `certified()` says
    no, the actuator refuses it, and reading any field raises rather than returning None —
    so the failure is loud at the first touch instead of silent all the way to a shelf.
    """
    shell = object.__new__(CertifiedPrice)
    assert not certified(shell)
    with pytest.raises(CertificateForgeryError, match=r"object\.__new__"):
        _ = shell.price
    with pytest.raises(CertificateForgeryError):
        dispatch_to_shelf(
            shell,
            DecisionKey(path=DecisionPath.MARKDOWN, sku_id="sku-1", store_id="store-7", occasion=1),
        )


def test_blanking_the_bounds_does_not_launder_a_price(
    certificate: CertifiedPrice,
) -> None:
    """The forgery that got past the first version of `certified()`.

    `PriceBounds` is a public export whose two fields both default to `()`. An **empty**
    bounds object satisfies containment vacuously — both ends are None, so every price is
    inside — and non-emptiness vacuously, for the same reason. So re-checking only "is the
    price inside its bounds" let a certified price be lowered to one cent by *erasing* the
    answer instead of writing a new one, while `cert.checks` went on naming three guardrails
    that no longer bounded anything.

    That distinction is the whole point: an erased answer is indistinguishable in a diff
    from a legitimate "no rule applied", whereas a forged one has to be written out. Two
    checks close it — at least one lower bound, since `evaluate` appends the absolute floor
    unconditionally, and the recorded checks recomputed from the bounds.
    """
    object.__setattr__(certificate, "_price", Money.of("0.01"))
    object.__setattr__(certificate, "_bounds", PriceBounds())
    assert not certified(certificate)
    with pytest.raises(CertificateForgeryError):
        dispatch_to_shelf(certificate, certificate.key)


def test_bounds_that_contradict_the_recorded_checks_are_refused(
    certificate: CertifiedPrice, independent_envelope: Envelope
) -> None:
    """Blanking both leaves `checks == ()`, which the lower-bound rule catches. Replacing
    the bounds with a *plausible* single floor is caught by the recomputation instead: the
    certificate would then be carrying a contradiction about itself."""
    permissive = PriceBounds(
        lower=(
            Bound(
                amount=Money(1),
                guardrail=GuardrailId.FLOOR,
                rule_id="minimum_absolute_price_eur",
                code=RefusalCode.BELOW_ABSOLUTE_FLOOR,
                why="forged",
            ),
        )
    )
    object.__setattr__(certificate, "_price", Money.of("0.01"))
    object.__setattr__(certificate, "_bounds", permissive)
    assert not certified(certificate)
    # And blanking the checks too, to make them agree, still fails — the recomputation of
    # an empty bounds object is empty, but an empty `lower` is refused outright.
    object.__setattr__(certificate, "_bounds", PriceBounds())
    object.__setattr__(certificate, "_checks", ())
    assert not certified(certificate)


def test_clearing_a_fallback_marker_is_caught(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """Doctrine rule 2 used to end at `certify`.

    `ProposedPrice` enforces "`LADDER` if and only if a marker" at the entrance, but the
    actuator's re-check ignored both fields, so a marked fallback could be stripped of its
    marker on the way to the shelf and the decision monitor's amber band would be a lie.
    The invariant is re-asserted in `certified()`, and it is an *equivalence*: a marker on a
    model decision is caught too, because that inflates the fallback rate and hides a real
    outage in the other direction.
    """
    issued = certify(
        propose(source=PriceSource.LADDER, marker="FALLBACK_LADDER"), independent_envelope
    )
    assert isinstance(issued, CertifiedPrice)
    assert certified(issued)
    object.__setattr__(issued, "_marker", None)
    assert not certified(issued)
    with pytest.raises(CertificateForgeryError):
        dispatch_to_shelf(issued, issued.key)


def test_a_model_decision_cannot_be_dressed_as_a_fallback_either(
    certificate: CertifiedPrice,
) -> None:
    object.__setattr__(certificate, "_marker", "FALLBACK_LADDER")
    assert not certified(certificate)


def test_rewriting_source_and_marker_together_is_a_declared_limit(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """The honest half of finding 4, asserted rather than claimed away.

    Re-asserting the marker invariant closes every *half* tamper. It cannot close the
    coordinated one — clearing `_marker` **and** setting `_source` to `MODEL` — and no check
    inside the certificate can, because the result is byte-for-byte a well-formed model
    certificate. The certificate never held independent evidence of where its number came
    from; provenance is asserted by the caller at the entrance and nothing downstream can
    audit that assertion.

    It is the same limit as the non-tamper route: a caller who takes the ladder's number and
    hands it to `ProposedPrice(source=MODEL, marker=None)` gets a genuinely certified model
    decision carrying a fallback price. Both are caught where the decision path is assembled
    — by the code that routes to the ladder being the code that builds the proposal — and
    that assembly is not on this branch. Written down here so nobody reads doctrine rule 2
    as fully closed by these types.
    """
    issued = certify(
        propose(source=PriceSource.LADDER, marker="FALLBACK_LADDER"), independent_envelope
    )
    assert isinstance(issued, CertifiedPrice)
    object.__setattr__(issued, "_marker", None)
    object.__setattr__(issued, "_source", PriceSource.MODEL)
    assert certified(issued), (
        "this is the declared limit, not a passing check. If this assertion ever fails, "
        "something has started binding provenance to the certificate and the limit above "
        "should be rewritten rather than the test."
    )


def test_tampering_through_object_setattr_is_detected_by_the_actuator(
    certificate: CertifiedPrice,
) -> None:
    """Route two: `object.__setattr__` bypasses `__setattr__`, and no class can stop it.

    The mitigation is that `certified()` re-checks the price against the bounds the
    certificate itself carries. Lowering a certified price to one cent leaves it below its
    own recorded floor, so the actuator refuses it. A forger who wants this to work has to
    rewrite the bounds too — which means writing the envelope's answer by hand, in a diff
    somebody reviews. That is the honest boundary of what a type can do here.
    """
    object.__setattr__(certificate, "_price", Money.of("0.01"))
    assert certificate.price == Money.of("0.01"), "the mutation itself cannot be prevented"
    assert not certified(certificate), "and it is caught at the only place that matters"
    with pytest.raises(CertificateForgeryError):
        dispatch_to_shelf(certificate, certificate.key)


def test_the_witness_is_not_reachable_by_any_name(certificate: CertifiedPrice) -> None:
    """It lives in a closure, so nothing in the module namespace exposes it. A determined
    forger reads `certify.__closure__`; nobody does that by accident, which is the
    distinction this design is drawn on."""
    import holdout.core.guardrails.certificate as module

    exposed = [name for name, value in vars(module).items() if isinstance(value, module._Witness)]
    assert not exposed, f"the witness is bound to {exposed} and can simply be imported"


# ------------------------------------------------------------------ what a refusal says


def test_a_refusal_declares_the_safe_state_of_the_guardrail_that_led_it(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """Doctrine rule 1, at the object a caller actually acts on.

    A floor refusal on the markdown path falls to the ladder, because for an expiring
    product silence throws it away. A frozen category falls to no action, because there the
    right answer is that no decision was taken at all. Two refusals, two safe states, from
    the same path — which is why the safe state is per guardrail and per path rather than
    per system.
    """
    floor_refusal = certify(propose(price=Money.of("0.20")), independent_envelope)
    frozen_refusal = certify(propose(category_id="tobacco"), independent_envelope)
    assert isinstance(floor_refusal, Refusal)
    assert isinstance(frozen_refusal, Refusal)
    assert floor_refusal.safe_state is SafeState.LADDER
    assert frozen_refusal.safe_state is SafeState.NO_ACTION


def test_a_refusal_with_no_legal_price_is_disposal_rather_than_a_wrong_price(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """cost 1.00 puts the margin floor at 113 cents; a 5% benchmark puts the cap at 105.
    No price satisfies both, and donation or disposal is the correct output."""
    refusal = certify(
        propose(
            price=Money.of("1.10"),
            base_price=Money.of("1.20"),
            category_id="dairy",
            benchmark_margin_pct=Decimal(5),
        ),
        independent_envelope,
    )
    assert isinstance(refusal, Refusal)
    assert refusal.is_disposal


def test_a_ladder_price_carries_its_marker_onto_the_certificate(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """Doctrine rule 2 at the far end. The marker is on the certificate, the certificate has
    no setter and no `replace`, and the actuator returns the same object — so nothing
    between here and the label can make this look like a model decision."""
    issued = certify(
        propose(source=PriceSource.LADDER, marker="FALLBACK_LADDER"), independent_envelope
    )
    assert isinstance(issued, CertifiedPrice)
    assert issued.marker == "FALLBACK_LADDER"
    assert issued.source is PriceSource.LADDER
    assert dispatch_to_shelf(issued, issued.key).marker == "FALLBACK_LADDER"


def test_a_stale_cost_stays_visible_on_a_certified_fallback(
    independent_envelope: Envelope, propose: ProposalFactory
) -> None:
    """The ladder may proceed on a stale cost; the certificate says so, so the staleness
    reaches the P&L and the experiment instead of being absorbed silently."""
    issued = certify(
        propose(
            source=PriceSource.LADDER,
            marker="FALLBACK_LADDER",
            cost_known_at=datetime(2026, 4, 1, 6, 0, tzinfo=UTC),
        ),
        independent_envelope,
    )
    assert isinstance(issued, CertifiedPrice)
    assert issued.cost_freshness is Freshness.STALE
