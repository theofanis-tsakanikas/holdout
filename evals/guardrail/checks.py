"""The attack. Real prices in, and one question: does a price ever escape the envelope?

Seven checks. Each is a sentence that would be false if the check failed, each carries a
number whether it passes or not, and each has an id that `make gate-proof` names.

The ids are load-bearing. `evals/gate_proof/mutations/claim-1/` plants a deliberate break in
`src/holdout/` and then demands that a **named** check here refuses it. Renaming one without
updating its mutations is caught: the mutation reports STALE rather than passing.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from corpus.real import quotes

from evals.guardrail import build, reference
from evals.report import Check, Report
from holdout.contracts.loader import load
from holdout.contracts.model import Policy
from holdout.core.decision import DecisionKey, DecisionPath, PriceSource
from holdout.core.guardrails import (
    CertificateForgeryError,
    CertifiedPrice,
    Envelope,
    PriceBounds,
    ProposedPrice,
    Refusal,
    RefusalCode,
    certified,
    certify,
    dispatch_to_shelf,
)
from holdout.core.ladder import quote as ladder_quote
from holdout.core.ladder import step_thresholds_minutes
from holdout.core.money import Money


def _rung_minutes(policy: Policy) -> tuple[int, ...]:
    """Every rung of the policy, plus one before the first fires and one past expiry.

    Read off the contract at run time rather than written out here, so a policy that grows a
    rung is exercised without anyone remembering to come back.
    """
    thresholds = [minutes for _step, minutes in step_thresholds_minutes(policy)]
    return (max(thresholds) + 60, *thresholds, 0)


@dataclass(frozen=True, slots=True)
class Outcome:
    case: build.Case
    result: CertifiedPrice | Refusal


def _run(cases: Iterator[build.Case]) -> list[Outcome]:
    return [Outcome(case=case, result=certify(case.proposal, case.envelope)) for case in cases]


def _fraction(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0/0"
    return f"{numerator}/{denominator} = {100 * numerator / denominator:.2f}%"


# ------------------------------------------------------------------------------- the checks


def check_only_a_certificate_reaches_a_shelf(outcomes: list[Outcome]) -> Check:
    """G1 — the claim in one sentence, driven by every decision the corpus produced."""
    dispatched = 0
    refused = 0
    failures: list[str] = []
    for outcome in outcomes:
        if isinstance(outcome.result, Refusal):
            refused += 1
            # A refusal is not a price. Offering it to the actuator must not merely fail to
            # dispatch — it must be a type error the annotation already forbids and the
            # runtime confirms.
            try:
                dispatch_to_shelf(outcome.result, outcome.case.proposal.key)  # type: ignore[arg-type]
            except CertificateForgeryError:
                pass
            except Exception as error:
                failures.append(f"{outcome.case.origin}: refusal raised {type(error).__name__}")
            else:
                failures.append(f"{outcome.case.origin}: a REFUSAL reached the shelf")
            continue
        if not certified(outcome.result):
            failures.append(f"{outcome.case.origin}: certify returned an uncertified object")
            continue
        dispatch_to_shelf(outcome.result, outcome.case.proposal.key)
        dispatched += 1
    return Check(
        id="G1.only-a-certificate-reaches-a-shelf",
        question=(
            "Over every decision the corpus produced, is a certificate the only thing the "
            "actuator accepts — and is a refusal always rejected by it?"
        ),
        passed=not failures,
        figure=f"{dispatched:,} certified dispatched · {refused:,} refusals rejected",
        detail=f"{len(failures)} decisions escaped",
        counterexamples=tuple(failures),
    )


def check_certified_price_inside_exact_bounds(outcomes: list[Outcome]) -> Check:
    """G2 — the strongest check here: a second implementation, and no tolerance at all."""
    checked = 0
    failures: list[str] = []
    for outcome in outcomes:
        if isinstance(outcome.result, Refusal):
            continue
        checked += 1
        for constraint in reference.violated(outcome.case):
            failures.append(
                f"{outcome.case.origin} [{outcome.case.envelope_id}] "
                f"certified but {constraint.name} says no — {constraint.detail}"
            )
    return Check(
        id="G2.certified-price-inside-exact-bounds",
        question=(
            "Does every price the envelope certified also satisfy this eval's own exact "
            "recomputation of every rule, computed in Decimal euros with no rounding?"
        ),
        passed=not failures,
        figure=f"{len(failures)} violations in {checked:,} certified prices",
        detail="a certified price outside an exactly-computed bound is a hole in the envelope",
        counterexamples=tuple(failures),
    )


def check_refusal_supported_by_exact_arithmetic(outcomes: list[Outcome]) -> Check:
    """G3 — the other direction. A refusal must have something to refuse."""
    checked = 0
    failures: list[str] = []
    for outcome in outcomes:
        if not isinstance(outcome.result, Refusal):
            continue
        for reason in outcome.result.reasons:
            if reason.code in _NOT_MODELLED_HERE:
                continue
            checked += 1
            supported, detail = reference.refusal_is_supported(outcome.case, reason.code)
            if not supported:
                failures.append(
                    f"{outcome.case.origin} [{outcome.case.envelope_id}] refused "
                    f"{reason.code.value} but the exact arithmetic disagrees — {detail}"
                )
    return Check(
        id="G3.refusal-supported-by-exact-arithmetic",
        question=(
            "For every guardrail that refused, does this eval's own exact arithmetic agree "
            "the rule was broken — or place the price within the one cent the core's "
            "conservative rounding is allowed to claim?"
        ),
        passed=not failures,
        figure=f"{len(failures)} unsupported in {checked:,} refusal reasons",
        detail="a refusal further inside the exact bound than a cent is a bound in the wrong place",
        counterexamples=tuple(failures),
    )


#: The one code this eval's reference implementation deliberately does not model.
#: `NO_PRICE_SATISFIES_EVERY_GUARDRAIL` is not a rule of its own: it is a statement that two
#: *other* bounds have crossed, so re-deriving it here would be re-deriving the same two
#: bounds a third time. `check_empty_range_is_really_empty` verifies it on its own terms,
#: from the exact floors and ceilings, which is a stronger question than this one.
_NOT_MODELLED_HERE = frozenset({RefusalCode.NO_PRICE_SATISFIES_EVERY_GUARDRAIL})


def check_empty_range_is_really_empty(outcomes: list[Outcome]) -> Check:
    """G4 — donation or disposal is a correct output, but only when it is true."""
    claimed = 0
    failures: list[str] = []
    for outcome in outcomes:
        if not isinstance(outcome.result, Refusal):
            continue
        if not outcome.result.is_disposal:
            continue
        claimed += 1
        floors = reference.lower_bounds(outcome.case)
        ceilings = reference.upper_bounds(outcome.case)
        if not ceilings:
            failures.append(
                f"{outcome.case.origin} [{outcome.case.envelope_id}] claims an empty range "
                "with no ceiling in force at all"
            )
            continue
        # The range is empty exactly when the highest floor is above the lowest ceiling.
        # Both are recomputed here from this eval's exact bounds — nothing is read off the
        # `PriceBounds` the refusal carries, which is the object under test.
        highest_floor, lowest_ceiling = max(floors), min(ceilings)
        # The same one-cent rounding contract `G3` uses, and for the same reason. The core
        # rounds a floor up and a ceiling down, so an exact range narrower than a cent can
        # contain no whole cent at all and is genuinely empty in integer arithmetic — that
        # is the declared cost of conservative rounding, written down in `docs/DECISIONS.md`
        # as "a price legal by half a cent can be refused". A disposal claimed on a range
        # **wider** than a cent is a different thing entirely, and that is what fails here.
        if highest_floor + reference.ONE_CENT <= lowest_ceiling:
            failures.append(
                f"{outcome.case.origin} [{outcome.case.envelope_id}] claims an empty range, "
                f"but exactly the floor is {highest_floor} and the ceiling {lowest_ceiling}"
            )
    return Check(
        id="G4.empty-range-is-really-empty",
        question=(
            "When the envelope answers 'no legal price sells this item' — donation or "
            "disposal — is the admissible range, recomputed exactly here, either empty or "
            "too narrow to hold a single whole cent?"
        ),
        passed=not failures,
        figure=f"{claimed:,} disposals claimed \u00b7 {len(failures)} unsupported",
        detail="disposal is a correct output; disposal claimed on a non-empty range is not",
        counterexamples=tuple(failures),
    )


def check_frozen_category_never_certified(outcomes: list[Outcome]) -> Check:
    """G5 — real tobacco, spirits, infant-formula and fish prices, and none of them priced."""
    seen = 0
    failures: list[str] = []
    for outcome in outcomes:
        category = outcome.case.proposal.category_id
        if category not in outcome.case.envelope.frozen_categories.category_ids:
            continue
        seen += 1
        if isinstance(outcome.result, Refusal):
            if RefusalCode.CATEGORY_FROZEN not in outcome.result.codes:
                failures.append(
                    f"{outcome.case.origin} refused, but not for being frozen: "
                    f"{outcome.result.code.value}"
                )
            continue
        failures.append(f"{outcome.case.origin} [{category}] was CERTIFIED in a frozen category")
    return Check(
        id="G5.frozen-category-never-certified",
        question=(
            "Of the real cigarette, spirit, infant-formula and fresh-fish prices in the "
            "corpus, does every single one refuse — and name the frozen category as a reason?"
        ),
        passed=not failures,
        figure=f"{seen:,} decisions in frozen categories · {len(failures)} certified or mis-refused",
        detail="a frozen category is a path the system does not enter, not a tighter bound",
        counterexamples=tuple(failures),
    )


#: The bounds the ladder is built to satisfy. It clamps to the floor, so a ladder price
#: refused by any of these is the ladder and the envelope disagreeing — which is exactly the
#: bug a review found by composing two modules that had only ever been tested alone.
_LADDER_MUST_SATISFY = frozenset(
    {
        RefusalCode.MARKDOWN_EXCEEDS_MAX_DEPTH,
        RefusalCode.BELOW_ABSOLUTE_FLOOR,
        RefusalCode.BELOW_MARGIN_FLOOR,
    }
)


@dataclass(frozen=True, slots=True)
class LadderRun:
    check: Check
    refused_by_a_ceiling: int
    quotes: int


def check_ladder_certifies_on_real_base_prices(policy: Policy) -> LadderRun:
    """G6 — the declared safe state, run over every distinct real shelf price.

    The regression that a review found the hard way: at the deepest rung, a ladder price
    rounded as a *price* fell a cent below a max-depth bound rounded as a *bound*, for one
    base price in five. It was invisible because the two modules had never been composed.

    Here the composition is driven by the corpus rather than by a hand-written list of cent
    endings — every distinct price a person wrote down in a shop — and the floor handed to
    the ladder is computed by **this eval's own exact arithmetic**, not read off the
    envelope. So the check does two jobs: the safe state must survive the envelope, and the
    eval's floor and the core's floor must agree to the cent.

    What it asserts is deliberately narrower than "the ladder is never refused". The ladder
    takes a floor and clamps to it; it takes no ceiling and knows of none. A ladder price
    refused by a *ceiling* is therefore not a disagreement between these two modules — it is
    a gap between them, it is counted separately, and `README.md` records it as a finding
    rather than letting a widened assertion swallow it.
    """
    catalogue = build.corpus_items()
    costs = build.unit_costs()
    distinct: dict[tuple[str, int], Money] = {}
    for row in quotes():
        distinct[(row.item_id, Money.of(row.price).cents)] = Money.of(row.price)

    decided_at = datetime(2026, 4, 15, 14, 0, tzinfo=UTC)
    rungs = _rung_minutes(policy)
    quoted_total = 0
    disposal = 0
    by_ceiling = 0
    failures: list[str] = []

    # An envelope whose maximum markdown depth is shallower than the ladder's deepest rung
    # cannot serve this ladder at all, and asking it to is not a finding about the core — it
    # is a contradiction between two contracts. `tests/contracts/test_guardrails.py` already
    # forbids it for *this repository's* contracts; the eval's own sweep contains one on
    # purpose, so that the other families have something to breach the depth bound with, and
    # it is excluded here by name rather than by an assertion quietly widened to admit it.
    deepest_rung = max(Decimal(str(step.depth_pct)) for step in policy.steps)
    usable = {
        envelope_id: envelope
        for envelope_id, envelope in build.markdown_envelopes().items()
        if envelope.max_delta.markdown_max_depth_pct >= deepest_rung
    }
    skipped = sorted(set(build.markdown_envelopes()) - set(usable))

    for envelope_id, envelope in usable.items():
        for (item_id, _cents), base in sorted(distinct.items()):
            item = catalogue[item_id]
            if item.scenario_category in envelope.frozen_categories.category_ids:
                continue
            cost = costs[item_id]
            floor = _exact_floor(envelope, cost)
            for minutes in rungs:
                quote_ = ladder_quote(minutes, base_price=base, policy=policy, floor=floor)
                if quote_ is None:
                    continue
                quoted_total += 1
                proposal = ProposedPrice(
                    key=DecisionKey(
                        path=DecisionPath.MARKDOWN,
                        sku_id=item_id,
                        store_id="ladder-probe",
                        occasion=quote_.step,
                    ),
                    decided_at=decided_at,
                    price=quote_.price,
                    base_price=base,
                    category_id=item.scenario_category,
                    source=PriceSource.LADDER,
                    marker=quote_.marker,
                    is_perishable=True,
                    announced_as_reduction=False,
                    changes_dispatched_today=0,
                    unit_cost=cost,
                    cost_known_at=decided_at,
                    benchmark_margin_pct=build.benchmark_markup_pct(),
                )
                result = certify(proposal, envelope)
                if not isinstance(result, Refusal):
                    continue
                broken = _LADDER_MUST_SATISFY & set(result.codes)
                if broken:
                    failures.append(
                        f"{envelope_id} {item_id} base {base} rung {quote_.step} "
                        f"-> {quote_.price} REFUSED {sorted(c.value for c in broken)}"
                    )
                elif result.is_disposal:
                    # No legal price exists at all, so the answer is donation or disposal.
                    # A correct output, and the one refusal a safe state may produce.
                    disposal += 1
                else:
                    by_ceiling += 1
    check = Check(
        id="G6.ladder-certifies-on-real-base-prices",
        question=(
            "Run over every distinct real shelf price in the corpus and every rung of the "
            "ladder, does the declared safe state ever produce a price refused by one of the "
            "three bounds it is built to satisfy — the max depth, the absolute floor, the "
            "margin floor?"
        ),
        passed=not failures,
        figure=(
            f"{quoted_total:,} ladder quotes over {len(usable)} envelopes \u00b7 "
            f"{len(failures)} refused by a bound the ladder respects \u00b7 "
            f"{disposal:,} disposal \u00b7 {by_ceiling:,} refused by a ceiling"
            + (
                f" \u00b7 skipped {', '.join(skipped)} (max depth below the deepest rung)"
                if skipped
                else ""
            )
        ),
        detail="a safe state the envelope refuses is not a safe state — there is nowhere left to fall",
        counterexamples=tuple(failures),
    )
    return LadderRun(check=check, refused_by_a_ceiling=by_ceiling, quotes=quoted_total)


def _exact_floor(envelope: Envelope, cost: Money) -> Money:
    """The envelope's lower bound, computed here and rounded up to the cent.

    Rounded **up**, because this is a floor and a floor that rounds down rounds into what it
    forbids. The same direction `Money.as_lower_bound` takes — arrived at independently,
    which is what makes the agreement between them worth checking.
    """
    exact_margin_floor = cost.euros * (
        Decimal(1) + envelope.floor.minimum_gross_margin_pct / Decimal(100)
    )
    highest = max(envelope.floor.minimum_absolute_price.euros, exact_margin_floor)
    return Money.as_lower_bound(highest.scaleb(2))


def check_closed_vocabulary_only(outcomes: list[Outcome]) -> Check:
    """G7 — every reason is a code the contract declares, and every code is countable."""
    declared = {code.value for code in RefusalCode}
    seen: Counter[str] = Counter()
    failures: list[str] = []
    for outcome in outcomes:
        if not isinstance(outcome.result, Refusal):
            continue
        for reason in outcome.result.reasons:
            seen[reason.code.value] += 1
            if reason.code.value not in declared:
                failures.append(f"{outcome.case.origin}: {reason.code.value!r} is not declared")
            if not reason.detail:
                failures.append(
                    f"{outcome.case.origin}: {reason.code.value} refused with no detail"
                )
    return Check(
        id="G7.closed-vocabulary-only",
        question=(
            "Is every refusal reason a code from the closed vocabulary, carrying a detail — "
            "so that claim 1's evidence is a count rather than a pile of prose?"
        ),
        passed=not failures,
        figure=f"{len(seen)} distinct codes over {sum(seen.values()):,} reasons",
        detail="a free-text reason cannot be counted, tested or gated",
        counterexamples=tuple(failures),
    )


#: Take every hundredth certificate rather than all of them. The tamper routes below are
#: properties of the type, not of the price, so the marginal certificate proves nothing and
#: the eval stays inside ten seconds. The sample size is published in the figure.
_TAMPER_STRIDE = 100


def check_no_tampered_certificate_reaches_a_shelf(outcomes: list[Outcome]) -> Check:
    """G9 — the actuation type, attacked with certificates the envelope really issued.

    `tests/core/test_certificate_forgery.py` walks the same routes against one hand-built
    certificate and is the authority on which are closed. This is a different question:
    whether the five checks `certified()` makes still hold over certificates issued from
    real prices, real bounds and real markers — where a `PriceBounds` has several attributed
    bounds rather than the single one a unit test constructs.

    `object.__setattr__` is the declared-open route the module docstring names. Using it here
    is deliberate: an attack that only used the closed routes would be attacking a door that
    is already locked.
    """
    attempts = 0
    escapes: list[str] = []
    for outcome in outcomes[::_TAMPER_STRIDE]:
        certificate = outcome.result
        if isinstance(certificate, Refusal):
            continue
        key = outcome.case.proposal.key
        for name, tamper in _TAMPERS.items():
            forged = _clone(certificate)
            if not tamper(forged):
                continue
            attempts += 1
            try:
                dispatch_to_shelf(forged, key)
            except CertificateForgeryError:
                continue
            escapes.append(f"{outcome.case.origin}: tamper {name!r} reached the shelf")
        # A genuine certificate presented for somebody else's decision.
        attempts += 1
        other = DecisionKey(
            path=key.path, sku_id=key.sku_id, store_id=key.store_id, occasion=key.occasion + 1
        )
        try:
            dispatch_to_shelf(certificate, other)
        except CertificateForgeryError:
            pass
        else:
            escapes.append(f"{outcome.case.origin}: a certificate bound to another decision passed")
    return Check(
        id="G9.no-tampered-certificate-reaches-a-shelf",
        question=(
            "Taking certificates the envelope really issued from real prices, does every "
            "declared tamper — erasing the bounds, lowering the price, stripping a "
            "fallback's marker, presenting it for another decision — still fail to dispatch?"
        ),
        passed=not escapes,
        figure=f"{len(escapes)} escapes in {attempts:,} tampering attempts",
        detail="a certificate that survives being altered is a certificate that asserts nothing",
        counterexamples=tuple(escapes),
    )


def _clone(certificate: CertifiedPrice) -> CertifiedPrice:
    """A slot-for-slot copy, built the way the module docstring says the type cannot stop.

    `copy.copy` returns the same object by design, so a forgery has to go through
    `object.__new__` — which is exactly the route `certificate.py` declares open and does not
    pretend to have closed.
    """
    forged = object.__new__(CertifiedPrice)
    for slot in CertifiedPrice.__slots__:
        object.__setattr__(forged, slot, object.__getattribute__(certificate, slot))
    return forged


def _erase_the_bounds(certificate: CertifiedPrice) -> bool:
    """The forgery that got past an earlier `certified()`: erase the answer, do not rewrite it."""
    object.__setattr__(certificate, "_bounds", PriceBounds())
    return True


def _erase_the_bounds_and_the_checks(certificate: CertifiedPrice) -> bool:
    """The same erasure, made self-consistent — and the only tamper the bounds check catches.

    Blanking `_bounds` alone is already refused by a *different* check: the recorded
    `_checks` no longer agree with the bounds they were derived from. That is defence in
    depth and it is worth having, but it means the erasure tamper above cannot show whether
    `if not bounds.lower: return False` is doing anything at all — `gate-proof` removed that
    line and nothing went red.

    An empty `PriceBounds` derives an empty tuple of checks, so setting both leaves a
    certificate that contradicts nothing about itself. What refuses it is the single
    question of whether any bound was ever recorded, and that question is now under test.
    """
    object.__setattr__(certificate, "_bounds", PriceBounds())
    object.__setattr__(certificate, "_checks", ())
    object.__setattr__(certificate, "_price", Money(1))
    return True


def _lower_the_price(certificate: CertifiedPrice) -> bool:
    object.__setattr__(certificate, "_price", Money(1))
    return True


def _strip_the_marker(certificate: CertifiedPrice) -> bool:
    """Doctrine rule 2 at the far end — a marked fallback dressed as a model decision."""
    if object.__getattribute__(certificate, "_marker") is None:
        return False
    object.__setattr__(certificate, "_marker", None)
    return True


def _forge_a_marker(certificate: CertifiedPrice) -> bool:
    """The same equivalence from the other side — a model decision wearing a marker."""
    if object.__getattribute__(certificate, "_marker") is not None:
        return False
    object.__setattr__(certificate, "_marker", "FALLBACK_LADDER")
    return True


_TAMPERS = {
    "erase the bounds": _erase_the_bounds,
    "erase the bounds and the checks together": _erase_the_bounds_and_the_checks,
    "lower the price to one cent": _lower_the_price,
    "strip a fallback's marker": _strip_the_marker,
    "forge a fallback marker": _forge_a_marker,
}


def check_every_code_is_reachable(fired: Counter[str]) -> Check:
    """G8 — the check that stops the other seven from passing by never trying anything.

    An eval whose corpus cannot construct an input for half the vocabulary is an eval that
    has proved half the claim. Claim 1's evidence is *a count of which guardrails refused*,
    so a code that is never reached is a gap in the evidence and it goes red here rather
    than sitting quietly in a footnote.

    A code may be declared unreachable, but only in `_UNREACHABLE_BY_DESIGN` and only with a
    reason written beside it. That list is deliberately hard to add to: it is the place a
    future session would be tempted to hide a gate that stopped biting.
    """
    unreached = sorted({c.value for c in RefusalCode} - set(fired) - set(_UNREACHABLE_BY_DESIGN))
    return Check(
        id="G8.every-refusal-code-is-reached",
        question=(
            "Does this eval actually construct an input for every code in the closed "
            "at_decision vocabulary — so that no gate is passing merely by never being tried?"
        ),
        passed=not unreached,
        figure=f"{len(fired)}/{len(RefusalCode)} codes reached",
        detail="a gate nothing exercises has not been shown to bite",
        counterexamples=tuple(f"{code} was never reached by any case" for code in unreached),
    )


#: Codes this eval cannot reach, each with the reason. Empty, and meant to stay that way.
_UNREACHABLE_BY_DESIGN: dict[str, str] = {}


# --------------------------------------------------------------------------------- report


def run() -> Report:
    policy = next(p for p in load().policies if p.id == "ladder_policy")
    outcomes = _run(build.all_cases())

    certificates = sum(1 for o in outcomes if not isinstance(o.result, Refusal))
    refusals = len(outcomes) - certificates
    leading: Counter[str] = Counter()
    # Every code that fired, not only the one that led. `Refusal.code` reports the leading
    # code by declared precedence, so counting leaders alone would report a guardrail as
    # never exercised whenever something earlier in the precedence order also fired — and
    # "this code is unreachable" is precisely the wrong conclusion to draw from that.
    every: Counter[str] = Counter()
    by_guardrail: Counter[str] = Counter()
    for outcome in outcomes:
        if isinstance(outcome.result, Refusal):
            leading[outcome.result.code.value] += 1
            for reason in outcome.result.reasons:
                every[reason.code.value] += 1
            for guardrail in outcome.result.guardrails:
                by_guardrail[guardrail.value] += 1

    ladder = check_ladder_certifies_on_real_base_prices(policy)
    checks = (
        check_only_a_certificate_reaches_a_shelf(outcomes),
        check_certified_price_inside_exact_bounds(outcomes),
        check_refusal_supported_by_exact_arithmetic(outcomes),
        check_empty_range_is_really_empty(outcomes),
        check_frozen_category_never_certified(outcomes),
        ladder.check,
        check_closed_vocabulary_only(outcomes),
        check_every_code_is_reachable(every),
        check_no_tampered_certificate_reaches_a_shelf(outcomes),
    )

    rows = list(quotes())
    unreached = sorted({c.value for c in RefusalCode} - set(every))
    numbers: list[tuple[str, str]] = [
        ("corpus quotes", f"{len(rows):,} from {len({q.outlet for q in rows}):,} outlet strata"),
        ("envelopes driven", f"{len(build.envelopes())}"),
        ("decisions taken", f"{len(outcomes):,}"),
        ("certified", _fraction(certificates, len(outcomes))),
        ("refused", _fraction(refusals, len(outcomes))),
        ("refusal codes reached", f"{len(every)}/{len(RefusalCode)}"),
    ]
    numbers.extend(
        (f"  code fired \u00b7 {code}", f"{count:,}  (leading {leading.get(code, 0):,})")
        for code, count in every.most_common()
    )
    numbers.extend(
        (f"  guardrail fired \u00b7 {name}", f"{count:,}")
        for name, count in by_guardrail.most_common()
    )
    numbers.append(
        (
            "ladder quotes refused by a ceiling",
            f"{ladder.refused_by_a_ceiling:,}/{ladder.quotes:,} — see README, 'A finding'",
        )
    )

    return Report(
        claim=1,
        title="No price reaches a shelf without the guardrail set",
        checks=checks,
        numbers=tuple(numbers),
        notes=(
            "that the numbers in contracts/guardrails/ are the right numbers — no test can; "
            "this shows the machinery honours whatever envelope it is handed",
            "anything about real retailers' costs: no unit cost is public, so cost is derived "
            "from a published industry margin and corpus/real/MANIFEST.yaml argues which way "
            "that errs",
            "that the guardrails hold against every possible input; this is a large sample of "
            "real prices, not a proof over all prices",
            "that the ladder is a complete safe state where a ceiling binds — "
            f"{ladder.refused_by_a_ceiling:,} of its quotes were refused by one, and that is a "
            "finding recorded in this eval's README rather than something it asserts away",
        )
        + ((f"codes no input in this eval reaches: {', '.join(unreached)}",) if unreached else ()),
    )
