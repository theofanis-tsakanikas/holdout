"""The guardrail set as a type: `ProposedPrice -> CertifiedPrice | Refusal`.

Claim 1 is that *the actuation type cannot be constructed without a guardrail certificate*.
The function that pushes to an electronic shelf label accepts a `CertifiedPrice` and
nothing else, so the whole claim reduces to one question: **can a `CertifiedPrice` exist
that the envelope did not produce?**

What is closed
--------------
`CertifiedPrice` is deliberately not a dataclass and deliberately does not use the ordinary
construction protocol. `tests/core/test_certificate_forgery.py` walks every row of this
table and asserts the outcome.

* ``CertifiedPrice(...)`` — ``CertificateForgeryError``. The constructor always refuses; the
  slots are filled by a function that exists only inside a closure, with no importable name
  bound to it.
* ``dataclasses.replace(cert, price=cheaper)`` — ``TypeError``, because it is not a
  dataclass. This is the route a hurried adapter reaches for and it is the reason
  `CertifiedPrice` is written by hand while everything around it is a dataclass.
* ``copy.copy`` / ``copy.deepcopy`` — return the same object. Not a second object whose
  slots could then be filled differently.
* ``pickle.dumps(cert)`` — ``CertificateForgeryError``. A certificate that survived a round
  trip could be restored in a process where the envelope never ran, and the actuator there
  would have no way to tell.
* ``class Fake(CertifiedPrice)`` — ``TypeError`` at class-creation time. A subclass would
  satisfy every ``isinstance`` check while carrying whatever its own constructor put in it.
* ``cert.price = cheaper`` and ``del cert.price`` — ``CertificateForgeryError``.
* a structurally identical look-alike — refused by ``certified()``, which is what the
  actuator calls, and by mypy, which reads the annotation.

What is **not** closed, honestly
--------------------------------
Python has no private state. Two routes remain open and no library can shut them:

1. ``object.__new__(CertifiedPrice)`` makes an instance with unset slots and
   ``object.__setattr__`` will fill them. Nothing a class defines intercepts either: they
   are the machinery ``__setattr__`` is defined in terms of.
2. The witness is reachable. Not, as an earlier version of this docstring claimed, only
   through ``certify.__closure__[0].cell_contents`` — that cell holds ``issue``, and the
   witness is one hop further, in ``issue.__closure__``. It is also reachable in a single
   line with no closure introspection at all:
   ``[o for o in gc.get_objects() if isinstance(o, _Witness)][0]``. ``ctypes`` gets there
   too. The route being open is a declared limit; the sentence describing what it costs to
   walk it was wrong, and being wrong about the cost of an attack is how a claim rots.

What ``certified()`` actually checks
------------------------------------
The check the actuator makes asks five questions, not one, and each of the last four exists
because a specific forgery got past an earlier version of it:

1. **the type** — exactly ``CertifiedPrice``, never a subclass, because subclassing raises;
2. **the stamp** — the witness this process's ``certify`` holds;
3. **at least one lower bound, and the recorded checks recomputed from the bounds** —
   ``evaluate`` appends the absolute-floor bound unconditionally, so every genuine
   certificate has one. This is the question a blanked ``PriceBounds()`` fails. An empty
   bounds object satisfies "the price is inside the bounds" vacuously and "the range is not
   empty" vacuously, so re-checking containment alone let a certified price be lowered to
   one cent by *erasing* the answer rather than by writing a new one — and an erased answer
   is invisible in a diff in a way a forged one is not;
4. **containment** — the price still lies inside the bounds the certificate records;
5. **the marker invariant** — ``source is LADDER`` if and only if a marker is present.
   ``ProposedPrice`` enforces this at the entrance, but without it here doctrine rule 2
   ended at ``certify``: a marked fallback could be stripped of its marker on the way to
   the shelf, and a model decision could be dressed as one. It is an equivalence, so both
   directions are refused.

Together these mean a certificate cannot be *tampered with* after issue — every mutation
either contradicts the recorded bounds, the recomputed checks or the marker invariant. A
wholesale fabrication still works for someone who reaches the witness and writes a
consistent set of attributed bounds by hand; that is an answer written in a diff somebody
reviews, which is the distinction this design is drawn on.

``certified()`` is **process-scoped**, not stateless: the witness is created once per
interpreter, so a certificate is only ever valid in the process that issued it. That is not
a limitation to apologise for — it is exactly what makes pickling refusable, and it is the
honest shape of the guarantee. A certificate is a statement made here, now, by this
envelope, about one decision.

What none of this reaches
-------------------------
**Provenance.** Check 5 closes every *half* tamper on the marker, and cannot close the
coordinated one: clearing ``_marker`` **and** setting ``_source`` to ``MODEL`` produces
something that is byte-for-byte a well-formed model certificate, and no check inside a
certificate can contradict it, because the certificate never held independent evidence of
where its number came from. Provenance is asserted by the caller at the entrance; nothing
downstream can audit that assertion.

The same limit reached the other way, without touching a certificate at all: a caller who
takes the ladder's number and hands it to ``ProposedPrice(source=MODEL, marker=None)`` gets
a genuinely certified model decision carrying a fallback price. That is not tampering, it
is a lie told at the entrance.

Both are caught where the decision path is assembled — by the code that routes to the
ladder being the same code that builds the proposal — and that assembly is not on this
branch. `test_rewriting_source_and_marker_together_is_a_declared_limit` asserts the limit
so that nobody reads doctrine rule 2 as fully closed by these types.

The honest summary: **the type makes the mistake impossible and leaves the forgery
visible.** That is what a type can do here, and claiming more would be exactly the sort of
sentence this project exists to argue against.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol, cast

from holdout.core.decision import DecisionKey, PriceSource, SafeState
from holdout.core.guardrails.codes import (
    GUARDRAIL_ORDER,
    PRECEDENCE,
    GuardrailId,
    RefusalCode,
)
from holdout.core.guardrails.envelope import (
    Announcement,
    Assessment,
    Envelope,
    Freshness,
    GuardrailRefusal,
    PriceBounds,
    ProposedPrice,
    evaluate,
)
from holdout.core.money import Money

_PRECEDENCE_INDEX = {code: index for index, code in enumerate(PRECEDENCE)}


class CertificateForgeryError(TypeError):
    """A `CertifiedPrice` was constructed, altered or serialised outside `certify`."""


class _Witness:
    """The object `certify` stamps a certificate with. One instance, held in a closure."""

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return "<guardrail witness>"


@dataclass(frozen=True, slots=True)
class Refusal:
    """No price may be dispatched, and why — a correct output, not an error.

    Where no legal price sells the item the answer is donation or disposal, and this object
    *is* that answer. It is returned rather than raised, because an exception is something a
    caller handles and a refusal is something a caller records: it goes to the decision
    record, to the decision monitor's refusal table, and — at the same size as an uplift —
    to the experiment readout.
    """

    key: DecisionKey
    decided_at: datetime
    reasons: tuple[GuardrailRefusal, ...]
    bounds: PriceBounds

    def __post_init__(self) -> None:
        if not self.reasons:
            raise ValueError(
                "a refusal names at least one guardrail and one reason. A refusal with no "
                "reason cannot be counted, tested or gated, which is the whole point of a "
                "closed vocabulary."
            )
        # Ordered here rather than by whoever built it, so `code` and `safe_state` are the
        # same for the same set of reasons no matter which caller assembled them.
        #
        # Two keys, not one. `INPUT_NOT_AVAILABLE` can be raised by more than one guardrail
        # in the same assessment, and those two refusals declare different safe states —
        # so sorting on the code alone would let `safe_state`, a doctrine-rule-1 quantity a
        # caller acts on, fall to whichever check happens to be written first in
        # `evaluate`. Reordering that function must not move a safe state.
        object.__setattr__(
            self,
            "reasons",
            tuple(
                sorted(
                    self.reasons,
                    key=lambda r: (
                        _PRECEDENCE_INDEX[r.code],
                        GUARDRAIL_ORDER.index(r.guardrail),
                        r.rule_id,
                    ),
                )
            ),
        )

    @property
    def code(self) -> RefusalCode:
        """The leading code, by the precedence declared in `codes.PRECEDENCE`."""
        return self.reasons[0].code

    @property
    def codes(self) -> tuple[RefusalCode, ...]:
        return tuple(r.code for r in self.reasons)

    @property
    def guardrails(self) -> tuple[GuardrailId, ...]:
        """Every guardrail that fired, deduplicated. Claim 1's evidence is a count of these."""
        seen: list[GuardrailId] = []
        for reason in self.reasons:
            if reason.guardrail not in seen:
                seen.append(reason.guardrail)
        return tuple(seen)

    @property
    def safe_state(self) -> SafeState:
        """What the path does instead, taken from the guardrail that led the refusal.

        Doctrine rule 1: for an expiring product this is the deterministic ladder, because
        silence throws the product away; for a price increase it is no action. The value is
        derived rather than stored, so it cannot disagree with the reason it came from.
        """
        return self.reasons[0].safe_state

    @property
    def is_disposal(self) -> bool:
        """The admissible range is empty, as opposed to this price being the wrong one.

        Nothing may be sold at any price, so the stock is donated or disposed of. That is a
        consequence of legality and not a claim about demand — the envelope never asks
        whether the item would sell, which is why the code is
        `NO_PRICE_SATISFIES_EVERY_GUARDRAIL` and not something about selling.
        """
        return RefusalCode.NO_PRICE_SATISFIES_EVERY_GUARDRAIL in self.codes

    def __str__(self) -> str:
        return f"REFUSED {self.code.value} ({self.key}) — {self.reasons[0].detail}"


class CertifiedPrice:
    """A price that passed the whole envelope. The only thing an actuator accepts.

    Not a dataclass and not constructible by any ordinary route — the module docstring says
    exactly which routes are closed and which two are not.
    """

    __slots__ = (
        "_announcement",
        "_bounds",
        "_checks",
        "_cost_freshness",
        "_decided_at",
        "_decided_on",
        "_key",
        "_marker",
        "_price",
        "_source",
        "_witness",
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise CertificateForgeryError(
            "a CertifiedPrice is not constructed; it is issued. The only way to obtain one "
            "is holdout.core.guardrails.certify(proposal, envelope), which returns it or a "
            "Refusal. In a test, certify a proposal: building the object directly would be "
            "asserting that the type can be bypassed, and it cannot."
        )

    def __init_subclass__(cls, **_kwargs: object) -> None:
        raise TypeError(
            "CertifiedPrice may not be subclassed. A subclass satisfies every isinstance "
            "check the actuator makes while carrying whatever its own constructor put in it."
        )

    # ------------------------------------------------------------------ read-only fields

    @property
    def key(self) -> DecisionKey:
        """What this certificate is for.

        The actuator compares it against the decision it is about to dispatch, so a
        certificate cannot be replayed onto a different SKU, store or occasion.
        """
        return cast(DecisionKey, self._read("_key"))

    @property
    def price(self) -> Money:
        return cast(Money, self._read("_price"))

    @property
    def decided_at(self) -> datetime:
        return cast(datetime, self._read("_decided_at"))

    @property
    def decided_on(self) -> date:
        """The date whose guardrail windows judged this decision — permanently, even after
        the rules change again."""
        return cast(date, self._read("_decided_on"))

    @property
    def source(self) -> PriceSource:
        return cast(PriceSource, self._read("_source"))

    @property
    def marker(self) -> str | None:
        """Doctrine rule 2, carried to the end.

        A ladder price arrives with its policy's marker and leaves with it. There is no
        setter, no `replace` and no constructor a downstream caller could use to build an
        otherwise identical certificate without it: dropping the marker means forging the
        certificate, not forgetting a field.
        """
        return cast("str | None", self._read("_marker"))

    @property
    def cost_freshness(self) -> Freshness:
        """`STALE` here means a marked ladder price taken on a stale cost, which is
        admissible and must stay visible. A model price on a stale cost never gets here."""
        return cast(Freshness, self._read("_cost_freshness"))

    @property
    def announcement(self) -> Announcement:
        """What the label may say about a reduction, and on what footing."""
        return cast(Announcement, self._read("_announcement"))

    @property
    def bounds(self) -> PriceBounds:
        """The admissible range this price was found inside, with each end attributed to
        the guardrail and rule that produced it."""
        return cast(PriceBounds, self._read("_bounds"))

    @property
    def checks(self) -> tuple[str, ...]:
        """Every guardrail rule that produced a bound, as `guardrail/rule_id`."""
        return cast("tuple[str, ...]", self._read("_checks"))

    def _read(self, slot: str) -> Any:
        try:
            return object.__getattribute__(self, slot)
        except AttributeError as error:
            raise CertificateForgeryError(
                "this object has the shape of a certificate and not its contents. It came "
                "from object.__new__ rather than from certify(), so no guardrail was ever "
                "evaluated for it."
            ) from error

    # ------------------------------------------------------------------ closed routes

    def __setattr__(self, name: str, value: object) -> None:
        raise CertificateForgeryError(
            f"a certificate is immutable; {name!r} cannot be set. Certify again with the "
            "value you want — which runs the envelope, which is the point."
        )

    def __delattr__(self, name: str) -> None:
        raise CertificateForgeryError("a certificate is immutable; nothing is deleted from it")

    def __reduce__(self) -> Any:
        raise CertificateForgeryError(
            "a certificate is not serialisable. One that survived a round trip could be "
            "restored in a process where the envelope never ran. Persist the decision "
            "record instead, and certify again wherever the price is needed."
        )

    def __copy__(self) -> CertifiedPrice:
        return self

    def __deepcopy__(self, _memo: dict[int, object]) -> CertifiedPrice:
        return self

    def __repr__(self) -> str:
        marker = f" [{self.marker}]" if self.marker else ""
        return f"<CertifiedPrice {self.price} {self.key} via {self.source.value}{marker}>"


def _checks_of(bounds: PriceBounds) -> tuple[str, ...]:
    """The guardrail rules that produced a certificate's bounds, as `guardrail/rule_id`.

    One function, called both when a certificate is issued and when it is verified. Two
    copies of this derivation that drifted apart would turn a real certificate into an
    unverifiable one, which fails in the same direction as accepting a forged one.
    """
    return tuple(
        f"{bound.guardrail.value}/{bound.rule_id}" for bound in (*bounds.lower, *bounds.upper)
    )


class _Certifier(Protocol):
    def __call__(self, proposal: ProposedPrice, envelope: Envelope) -> CertifiedPrice | Refusal: ...


class _Verifier(Protocol):
    def __call__(self, candidate: object) -> bool: ...


def _build() -> tuple[_Certifier, _Verifier]:
    """Create the witness and the only two functions that know it.

    Everything private to certification lives in this closure. There is no module-level
    name bound to the witness or to the function that fills a certificate's slots, so
    neither can be imported, monkeypatched or reached by autocomplete.
    """
    witness = _Witness()

    def issue(assessment: Assessment, proposal: ProposedPrice, on: date) -> CertifiedPrice:
        certificate = object.__new__(CertifiedPrice)
        put = object.__setattr__
        put(certificate, "_witness", witness)
        put(certificate, "_key", proposal.key)
        put(certificate, "_price", proposal.price)
        put(certificate, "_decided_at", proposal.decided_at)
        put(certificate, "_decided_on", on)
        put(certificate, "_source", proposal.source)
        put(certificate, "_marker", proposal.marker)
        put(certificate, "_cost_freshness", assessment.cost_freshness)
        put(certificate, "_announcement", assessment.announcement)
        put(certificate, "_bounds", assessment.bounds)
        put(certificate, "_checks", _checks_of(assessment.bounds))
        return certificate

    def certify(proposal: ProposedPrice, envelope: Envelope) -> CertifiedPrice | Refusal:
        """Run the whole envelope over a proposal. The only source of a `CertifiedPrice`.

        Returns a `CertifiedPrice` when every guardrail admitted the price, and otherwise a
        `Refusal` naming every guardrail that did not. It never raises because it disliked
        a price: a refusal is a correct output, and the caller applies the safe state the
        refusal declares.
        """
        assessment = evaluate(proposal, envelope)
        if assessment.refusals:
            return Refusal(
                key=proposal.key,
                decided_at=proposal.decided_at,
                reasons=assessment.refusals,
                bounds=assessment.bounds,
            )
        return issue(assessment, proposal, envelope.decided_on)

    def certified(candidate: object) -> bool:
        """Whether `candidate` is a certificate this process issued and nobody has touched.

        Five questions, enumerated and argued in the module docstring. The three beyond
        type-and-stamp are each here because a specific forgery got past a version of this
        function that did not ask them.
        """
        if type(candidate) is not CertifiedPrice:
            return False
        try:
            stamp = object.__getattribute__(candidate, "_witness")
            price = object.__getattribute__(candidate, "_price")
            bounds = object.__getattribute__(candidate, "_bounds")
            checks = object.__getattribute__(candidate, "_checks")
            source = object.__getattribute__(candidate, "_source")
            marker = object.__getattribute__(candidate, "_marker")
        except AttributeError:
            return False

        if stamp is not witness or not isinstance(bounds, PriceBounds):
            return False

        # Every certificate the envelope issues has at least one lower bound, because
        # `evaluate` appends the absolute floor unconditionally. A `PriceBounds()` with
        # nothing in it satisfies containment and non-emptiness *vacuously*, so without
        # this a price could be lowered to one cent by erasing the answer rather than by
        # writing one — and an erasure is invisible in a diff in a way a forgery is not.
        if not bounds.lower:
            return False
        # The recorded checks are derived from the bounds, so they must still agree with
        # them. Replacing one and not the other is a contradiction the certificate carries
        # about itself.
        if checks != _checks_of(bounds):
            return False

        if not bounds.contains(price) or bounds.is_empty:
            return False

        # Doctrine rule 2, re-asserted at the far end. `ProposedPrice` enforces this at the
        # entrance; without it here, clearing the marker and setting the source to `model`
        # turned a marked fallback into a model decision on the way to the shelf.
        return (source is PriceSource.LADDER) == bool(marker)

    return certify, certified


certify, certified = _build()


def dispatch_to_shelf(price: CertifiedPrice, key: DecisionKey) -> CertifiedPrice:
    """The shape every actuator must have: it accepts a certificate and nothing else.

    The real dispatcher lives in an adapter and talks to an electronic shelf label. This is
    the part of it that belongs in the core, because this is the part claim 1 is about. It
    takes the key separately and compares, because a certificate is a statement about one
    specific decision and not a licence to write a number: without the comparison, a
    certificate issued for a cheap item could be presented for an expensive one.
    """
    if not certified(price):
        raise CertificateForgeryError(
            "this is not a certificate issued by the envelope in this process, or its "
            "price no longer lies inside its own recorded bounds. Nothing reaches a shelf "
            "on the strength of an object that merely has the right shape."
        )
    if price.key != key:
        raise CertificateForgeryError(
            f"the certificate was issued for {price.key} and the dispatch is for {key}. "
            "A certificate binds to one decision."
        )
    return price
