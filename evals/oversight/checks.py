"""Claim 7's checks — eleven questions, and the numbers behind each of them.

`CLAUDE.md`, claim 7: *a decision that targets a person is structurally impossible. The
decision key has no customer dimension, and a test goes red if one appears.*

The trap, written out before any of this was built
---------------------------------------------------
Every claim in `CLAUDE.md` carries one and they are all the same trap in different clothes:
*something checking its own work and calling the agreement evidence.* Claim 7's row was the
one row in the table with no trap written beside it, and here it is:

> **A list of person-shaped words written by whoever also wrote the field names is one
> function agreeing with itself.** It contains exactly the words its author thought of while
> looking at the fields they had just written, so it is guaranteed to find nothing and
> guaranteed to feel like a guard.

The answer is that the words are not ours. `corpus/real/` carries 156 schema.org properties
that touch `Person` and 99 PII entity types Microsoft Presidio ships recognizers for — two
publishers who have never coordinated with each other and have certainly never read
`contracts/`. Measured, the hand-written list this repository was carrying catches **35 of
the 317 names** they yield between them. It is a net. The guard is the closed field set.

What each check is for
----------------------
`O1` to `O3` are the structure: the key, every type's field set, and no unlisted type. `O4` and `O5`
read names — the fields, and then every identifier the core defines, which is where a person
would arrive as a *parameter* or an *enum member* rather than as a field. `O6` and `O7` plant
each external name on each type and ask who refuses. `O8` is coverage. `O9` asks the question
at runtime instead of by reading. `O10` leaves Python entirely: a customer dimension can
arrive through a contract and compile into a dbt model, an agent tool definition and the
readout query without a single dataclass changing. `O11` is the second implementation.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path
from typing import Any

from ops.personhood import (
    FIELDS_ON_THE_DECISION_PATH,
    PERSON_SHAPED,
    core_types,
    field_names,
    misdeclared,
    unlisted,
)

from evals.oversight import reference
from evals.oversight.build import (
    ExternalName,
    attacks,
    decision_path_types,
    lexicon,
    matched_by,
    refused_by_the_structure,
    refused_by_the_word_list,
)
from evals.report import Check, Report
from holdout.contracts.loader import load
from holdout.core.decision import DecisionKey, DecisionPath


def _one_line(text: str, width: int = 72) -> str:
    """A reason, on the one line the report gives it. Truncation is marked, never silent."""
    flattened = " ".join(text.split())
    return flattened if len(flattened) <= width else flattened[: width - 1] + "…"


REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATED = REPO_ROOT / "generated"

#: The key claim 7's sentence is about, and the fields it is allowed to have.
#:
#: Written out here as well as in `ops/personhood.py`, and that is deliberate rather than a
#: duplicate: `O1` is the one assertion in this eval that a reader should be able to check
#: without opening another file. If the two ever disagree, `O1` fails and says which.
THE_KEY_IS = frozenset({"path", "sku_id", "store_id", "occasion"})

#: Names the core defines that a published person-vocabulary also uses, with the reason each
#: one means something else here.
#:
#: **Every entry was found by the scan, not by anticipation.** Ordinary engineering English
#: and the vocabulary of personhood overlap — that is not a defect in either list, it is the
#: reason a word list can never be the guard — and the honest response is to publish the
#: overlap in full rather than to quietly filter the input. A name arriving here that is not
#: on this list turns `O5` red, and the fix is a conversation, never an addition made in the
#: same commit as the name.
#:
#: Reviewed 2026-08-29 (T006), against schema.org 30.0 and Presidio eb93051b.
EXPLAINED: dict[str, str] = {
    "AGENT": (
        "`FilledBy.AGENT` — one of the three sources that may fill a design form. schema.org's "
        "`agent` names a person; this one is the LLM, and `CLAUDE.md` is explicit that it "
        "never fills `max_duration` or `decision_rule` and never goes near the decision path"
    ),
    "agent": "the same enum value and the same word, as it is spelled on the wire",
    "agent_tool": (
        "the metric contract's third consumer — the JSON tool definition the design agent is "
        "given so that it never writes SQL"
    ),
    "candidate": (
        "a candidate *price* in `pricing/selection.py`. schema.org's `candidate` is a person "
        "standing for election"
    ),
    "candidate_weeks": "the durations feasibility scans over before it refuses one",
    "members": (
        "the units in a stratum. The experiment layer's vocabulary is arm, unit, stratum and "
        "roster; schema.org's `member` is a person belonging to an organisation"
    ),
    "weight_c": "the control arm's weight in the estimator's variance, not a person's mass",
    "weight_t": "the treatment arm's, likewise",
}


# ------------------------------------------------------------------ O1 · the key itself


def check_the_key(names: tuple[ExternalName, ...]) -> Check:
    carried = field_names(DecisionKey)
    written = FIELDS_ON_THE_DECISION_PATH[DecisionKey]
    offences = [
        f"{name} is not one of the four this eval writes down"
        for name in sorted(carried - THE_KEY_IS)
    ]
    offences += [
        f"{name} is written down here and is not on the key"
        for name in sorted(THE_KEY_IS - carried)
    ]
    if written != THE_KEY_IS:
        offences.append(
            f"ops/personhood.py and this eval disagree about the key: {sorted(written ^ THE_KEY_IS)}"
        )
    person = [
        f"{field} matches {external.published_as} ({external.publisher})"
        for field in sorted(carried)
        for external in matched_by(field, names)
    ]
    return Check(
        id="O1.the-key-is-what-is-priced-and-where",
        question=(
            "Is a decision addressed by a SKU, a store, a path and an occasion — those four "
            f"and nothing else — and is none of the four a name any of the {len(names)} "
            "published person-names would recognise?"
        ),
        passed=not offences and not person,
        figure=f"{len(carried)} fields · {len(person)} of them a published person-name",
        detail=(
            "the key is the whole of claim 7. There is no customer dimension, no household, "
            "no loyalty id, and no field from which one could be derived"
        ),
        counterexamples=tuple(offences + person),
    )


# ------------------------------------------------- O2 · O3 · the registry, both directions


def check_every_type_carries_what_is_written_down() -> Check:
    offences = misdeclared()
    return Check(
        id="O2.every-decision-path-type-carries-exactly-the-fields-written-down",
        question=(
            "Does every type on the decision path carry exactly the fields a human wrote "
            "down beside it — so that adding any field at all is a red gate and a conversation?"
        ),
        passed=not offences,
        figure=(
            f"{len(FIELDS_ON_THE_DECISION_PATH) - len(offences)}/"
            f"{len(FIELDS_ON_THE_DECISION_PATH)} types agree"
        ),
        detail=(
            "this is the check that carries the claim, and it does not read names at all: a "
            "field called `nationality` and a field called `q7` are the same finding here"
        ),
        counterexamples=tuple(offences),
    )


def check_every_type_is_written_down() -> Check:
    offences = unlisted()
    found = core_types()
    return Check(
        id="O3.every-type-in-the-core-is-written-down",
        question=(
            "Is every type in `holdout.core` that carries fields written down in the "
            "registry — so that claim 7 cannot be defeated by adding a type rather than a field?"
        ),
        passed=not offences,
        figure=f"{len(found)} types found · {len(offences)} nobody wrote down",
        detail=(
            "a `CustomerContext` nobody listed, carried on a proposal and asserted nowhere, "
            "would pass every field-set check in this eval"
        ),
        counterexamples=tuple(offences),
    )


# ------------------------------------------------------------ O4 · O5 · the names, twice


def check_no_field_is_a_person_name(names: tuple[ExternalName, ...]) -> Check:
    fields = [(cls, name) for cls in core_types() for name in sorted(field_names(cls))]
    offences = [
        f"{cls.__module__}.{cls.__name__}.{field} matches {external.published_as} — {external.why}"
        for cls, field in fields
        for external in matched_by(field, names)
    ]
    return Check(
        id="O4.no-field-is-a-name-a-person-is-known-by",
        question=(
            f"Of the {len(fields)} fields every type in the core carries, does any one of "
            f"them carry a name from the {len(names)} that schema.org and Presidio publish "
            "for a person?"
        ),
        passed=not offences,
        figure=f"{len(offences)} of {len(fields)} fields · against {len(names)} published names",
        detail=(
            "the words are not ours, which is the whole of this check. A list written here "
            "would contain exactly the words whoever wrote the fields thought of"
        ),
        counterexamples=tuple(offences),
    )


def collisions_in_the_core(names: tuple[ExternalName, ...]) -> set[str]:
    """Which identifiers defined under `src/holdout/core/` a published person-name matches."""
    return {
        identifier.name
        for identifier in reference.identifiers()
        if matched_by(identifier.name, names)
    }


def check_no_identifier_is_a_person_name(names: tuple[ExternalName, ...]) -> Check:
    identifiers = reference.identifiers()
    distinct = {identifier.name for identifier in identifiers}
    hits = [
        (identifier, external)
        for identifier in identifiers
        for external in matched_by(identifier.name, names)
    ]
    unexplained = [
        f"{identifier.name} ({identifier.kind}, {identifier.where}) matches "
        f"{external.published_as} — {external.why}"
        for identifier, external in hits
        if identifier.name not in EXPLAINED
    ]
    return Check(
        id="O5.no-new-identifier-in-the-core-is-a-name-a-person-is-known-by",
        question=(
            "Every name the core defines — class, function, parameter, enum member, "
            "constant — read from the source text: is each one that a published "
            "person-vocabulary also uses on the reviewed list, with the reason it means "
            "something else here?"
        ),
        passed=not unexplained,
        figure=(
            f"{len({i.name for i, _ in hits})} of {len(distinct)} names collide · "
            f"{len(unexplained)} unexplained"
        ),
        detail=(
            "a person does not have to arrive as a field. A `customer` parameter on the "
            "actuator or a `loyalty_tier` member on `PriceSource` is caught here or nowhere, "
            "because neither is a dataclass field and no field-set comparison would see it"
        ),
        counterexamples=tuple(unexplained),
    )


# ------------------------------------------------------ O6 · O7 · plant each one and look


def check_every_planted_person_is_refused(planted: list[tuple[Any, bool, bool]]) -> Check:
    escaped = [
        f"{attack.where} — {attack.external.published_as} ({attack.external.publisher})"
        for attack, structure, _ in planted
        if not structure
    ]
    return Check(
        id="O6.every-planted-person-is-refused",
        question=(
            f"Planting each of the published person-names as a field on each of the "
            f"{len(decision_path_types())} types on the decision path — "
            f"{len(planted):,} attacks — does the structural assertion refuse every one?"
        ),
        passed=not escaped,
        figure=f"{len(planted) - len(escaped):,}/{len(planted):,} refused",
        detail=(
            "nothing is written to disk and no class is modified: the attack is evaluated "
            "against the field set the type *would* carry, by the same function the suite "
            "calls. `gate-proof` does the other half — it edits the source and runs this "
            "whole eval against the edit"
        ),
        counterexamples=tuple(escaped),
    )


def check_the_word_list_never_refuses_alone(planted: list[tuple[Any, bool, bool]]) -> Check:
    alone = [
        f"{attack.where} — refused only by the hand-written word list"
        for attack, structure, word_list in planted
        if word_list and not structure
    ]
    by_list = sum(1 for _, _, word_list in planted if word_list)
    return Check(
        id="O7.the-word-list-never-refuses-alone",
        question=(
            "Is every attack the hand-written word list catches also caught by the closed "
            "field set — so that claim 7 never rests on a list of words somebody here thought of?"
        ),
        passed=not alone,
        figure=(
            f"word list {by_list:,}/{len(planted):,} · structure {len(planted):,}/{len(planted):,} "
            f"· {len(alone)} caught by the list alone"
        ),
        detail=(
            f"the {len(PERSON_SHAPED)} hand-written substrings catch "
            f"{by_list * 100 // max(len(planted), 1)}% of the published names. That figure is "
            "the argument for this eval existing, and it is why the word list is a net rather "
            "than the claim"
        ),
        counterexamples=tuple(alone),
    )


# ---------------------------------------------------------------------- O8 · coverage


def check_the_scan_reaches_what_is_not_a_dataclass() -> Check:
    """Rule 4 of `evals/README.md`: coverage is itself a check.

    This is the hole a review found in the first version of the suite's own test, and it is
    the one that matters most: `CertifiedPrice` is deliberately not a dataclass, because its
    constructor has to refuse — that design choice is most of claim 1, and it made claim 7
    blind to the actuation type. A scan that silently lost it would report a clean sweep of
    every type it could still see.
    """
    found = core_types()
    not_dataclasses = [cls for cls in found if not dataclasses.is_dataclass(cls)]
    blind = [
        f"{cls.__module__}.{cls.__name__} is not a dataclass and the scan reads no fields from it"
        for cls in not_dataclasses
        if cls in FIELDS_ON_THE_DECISION_PATH and not field_names(cls)
    ]
    reached = [cls for cls in not_dataclasses if field_names(cls)]
    if not reached:
        blind.append(
            "no non-dataclass in the core reports any field — the __slots__ half of the scan "
            "is doing nothing and this eval would pass vacuously over the actuation type"
        )
    return Check(
        id="O8.the-scan-reaches-the-types-that-are-not-dataclasses",
        question=(
            "Do the types whose constructors refuse — the ones that are deliberately not "
            "dataclasses — report their fields to this scan, rather than being invisible to it?"
        ),
        passed=not blind,
        figure=f"{len(reached)} non-dataclass type(s) reached · {len(found)} types in all",
        detail=(
            "`CertifiedPrice` and `SealedAssignment` are the two, and both are read through "
            "`__slots__`. A scan built on `dataclasses.fields` alone would see neither"
        ),
        counterexamples=tuple(blind),
    )


# --------------------------------------------------------- O9 · ask it at runtime instead


def check_nothing_can_be_attached_at_runtime(names: tuple[ExternalName, ...]) -> Check:
    """Three routes onto an object, tried with every published person-name.

    Reading the source says what was written down. This says what the interpreter will
    actually allow, which is a different question and the one an attacker asks: construct it
    with the field, assign the field afterwards, or rebuild the object with `replace`.
    """
    key = DecisionKey(path=DecisionPath.MARKDOWN, sku_id="sku-1", store_id="store-7", occasion=2)
    attached: list[str] = []
    attempts = 0

    for external in names:
        name = external.name
        attempts += 3
        try:
            DecisionKey(
                **{  # type: ignore[arg-type]
                    "path": DecisionPath.MARKDOWN,
                    "sku_id": "sku-1",
                    "store_id": "store-7",
                    "occasion": 2,
                    name: "whoever",
                }
            )
        except TypeError:
            pass
        else:
            attached.append(f"DecisionKey(..., {name}=...) constructed")

        try:
            setattr(key, name, "whoever")
        except (AttributeError, TypeError):
            # `FrozenInstanceError` subclasses `AttributeError`; a frozen **slotted**
            # dataclass raises a bare `TypeError` out of the `__setattr__` the decorator
            # synthesised, because the class the closure captured is not the class the
            # decorator ultimately produced. Both are refusals and neither is caught by
            # naming only the one this eval's author expected — which is the shape of
            # defect this whole claim is about, met once while writing it.
            pass
        else:
            attached.append(f"key.{name} = ... was accepted after the key was built")

        try:
            dataclasses.replace(key, **{name: "whoever"})  # type: ignore[arg-type]
        except TypeError:
            pass
        else:
            attached.append(f"dataclasses.replace(key, {name}=...) produced a key carrying it")

    seals = reference.seals()
    unsealed: list[str] = []
    for cls in decision_path_types():
        qualified = f"{cls.__module__}.{cls.__name__}"
        seal = seals.get(qualified)
        if seal is None:
            unsealed.append(
                f"{qualified} exists at runtime and the source text defines no class of that name"
            )
        elif not seal.sealed:
            unsealed.append(f"{qualified} is not sealed: frozen={seal.frozen} slots={seal.slotted}")
    return Check(
        id="O9.no-person-can-be-attached-to-a-key-at-runtime",
        question=(
            "Can a person be stapled to a decision after the fact — by construction, by "
            "assignment, or by `replace` — and is every type on the path frozen and slotted "
            "so that there is no name to assign to and no assignment to make?"
        ),
        passed=not attached and not unsealed,
        figure=(
            f"{attempts - len(attached):,}/{attempts:,} attempts refused · "
            f"{len(decision_path_types()) - len(unsealed)}/{len(decision_path_types())} types sealed"
        ),
        detail=(
            "frozen refuses the assignment and slots refuse the *name*; either alone leaves "
            "a route open, which is why both are read"
        ),
        counterexamples=tuple(attached + unsealed),
    )


# ------------------------------------------------- O10 · the surface that is not Python


_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def declared_contract_names() -> tuple[tuple[str, str, str], ...]:
    """Every name the contract layer and its compiled consumers declare, with where it is.

    Structural names only — a grain component, a source relation, an idempotency component,
    a covariate id, a column reference inside a metric expression — plus every identifier
    token in `generated/`, which is machine-written and therefore almost entirely names. The
    prose in a contract's `description` or `provenance` is deliberately **not** read: a
    guardrail that quotes a ministerial decision about consumers would light this up for a
    sentence, and a check that cries wolf is a check somebody turns off.
    """
    contracts = load()
    declared: list[tuple[str, str, str]] = []
    for metric in contracts.metrics:
        where = f"{metric.id}@v{metric.version}"
        declared += [("metric grain", where, component) for component in metric.grain]
        declared += [("metric source", where, source.relation) for source in metric.sources]
        declared += [
            ("metric expression", where, token)
            for token in sorted(set(_IDENTIFIER.findall(metric.expression)))
        ]
    for policy in contracts.policies:
        declared += [
            ("policy idempotency key", f"{policy.id}@v{policy.version}", component)
            for component in policy.idempotency_key
        ]
    for covariate in contracts.balance_covariates.covariates:
        declared.append(("balance covariate", covariate.id, covariate.id))
        declared.append(("balance covariate source", covariate.id, covariate.source_relation or ""))
    for path in sorted(GENERATED.rglob("*")):
        if not path.is_file():
            continue
        where = str(path.relative_to(REPO_ROOT))
        declared += [
            ("generated consumer", where, token)
            for token in sorted(set(_IDENTIFIER.findall(path.read_text(encoding="utf-8"))))
        ]
    return tuple(declared)


def check_no_contract_declares_a_customer_dimension(names: tuple[ExternalName, ...]) -> Check:
    """A customer dimension does not have to arrive as a Python field.

    `contracts/metrics/*.yaml` declares the grain a metric is defined per, and that grain
    compiles into a dbt model, a SQL function, the agent's tool definition and the readout
    query. `contracts/policies/*.yaml` declares the idempotency key a decision is taken per —
    add `customer_id` there and a decision is, by definition, taken per customer. Neither
    would move a single dataclass, and every check above this one would stay green.
    """
    declared = declared_contract_names()
    offences = [
        f"{kind} {where}: {token} matches {external.published_as} — {external.why}"
        for kind, where, token in declared
        for external in matched_by(token, names)
        if token not in EXPLAINED
    ]
    return Check(
        id="O10.no-contract-declares-a-customer-dimension",
        question=(
            "Does any metric grain, metric source, policy idempotency key, balance covariate "
            "or compiled consumer name a person — so that a decision could be defined per "
            "customer without a single Python type changing?"
        ),
        passed=not offences,
        figure=f"{len(offences)} of {len(declared):,} declared names",
        detail=(
            "the grain compiles into a dbt model, a SQL function, the agent's tool definition "
            "and the readout query. A customer dimension entering here would reach all four "
            "and would move no dataclass at all"
        ),
        counterexamples=tuple(offences),
    )


# -------------------------------------------------- O11 · the second implementation


def check_the_source_and_the_objects_agree() -> Check:
    """The eval reads the text; the guard reads the objects. They must say the same thing.

    If both sides asked Python, the only thing that would know what a class carries would be
    the class. This is the answer to that: `reference.field_sets()` never imports a module
    from the core, so it is blind to anything a decorator or a metaclass does at import time
    and sighted on everything written down. A field that exists at runtime and appears
    nowhere in the source — or the reverse — shows up here and in no other check.
    """
    from_source = reference.field_sets()
    disagreements: list[str] = []
    for cls in decision_path_types():
        qualified = f"{cls.__module__}.{cls.__name__}"
        if qualified not in from_source:
            disagreements.append(f"{qualified} exists at runtime and no source file defines it")
            continue
        live = field_names(cls)
        text = from_source[qualified]
        if live != text:
            only_live = sorted(live - text)
            only_text = sorted(text - live)
            disagreements.append(
                f"{qualified}: runtime-only {only_live or '—'} · source-only {only_text or '—'}"
            )
    return Check(
        id="O11.the-source-text-and-the-live-objects-agree",
        question=(
            "Does a second reading of every type — parsed out of the source text, never "
            "imported — produce exactly the field set the running objects report?"
        ),
        passed=not disagreements,
        figure=(
            f"{len(decision_path_types()) - len(disagreements)}/{len(decision_path_types())} "
            f"types agree · {len(from_source)} classes parsed"
        ),
        detail=(
            "two mechanisms, sharing only `tokens`: `dataclasses.fields` and `__slots__` on "
            "one side, annotated assignments and string literals on the other"
        ),
        counterexamples=tuple(disagreements),
    )


# --------------------------------------------------- O12 · the explanations still explain


def check_every_explanation_still_explains_something(names: tuple[ExternalName, ...]) -> Check:
    """Doctrine rule 6 in miniature: an exception that outlives its reason is a hole.

    `EXPLAINED` is the one place in this eval where somebody here decided that a match is
    innocent. Every entry earns its place by matching something *now*. An entry left behind
    after the identifier it excused was renamed is a name pre-approved for whoever adds it
    next, and it would be approved by a line nobody remembers writing.
    """
    live = collisions_in_the_core(names) | {
        token for _, _, token in declared_contract_names() if matched_by(token, names)
    }
    stale = [
        f"{name} is explained here and nothing in the core or the contracts is called that "
        "any more — the explanation is now a pre-approval"
        for name in sorted(EXPLAINED)
        if name not in live
    ]
    return Check(
        id="O12.every-explanation-still-explains-something",
        question=(
            "Does every entry on the reviewed list of innocent collisions still match a name "
            "that is actually there — so that no explanation survives the thing it explained?"
        ),
        passed=not stale,
        figure=f"{len(EXPLAINED) - len(stale)}/{len(EXPLAINED)} explanations still in use",
        detail=(
            "the list is the only judgment this eval makes about somebody else's words, and "
            "an unused entry is a name pre-approved for whoever adds it next"
        ),
        counterexamples=tuple(stale),
    )


# ------------------------------------------------------------------------------- the run


def run() -> Report:
    names = lexicon()
    planted = [
        (attack, refused_by_the_structure(attack), refused_by_the_word_list(attack))
        for attack in attacks(names)
    ]

    checks = (
        check_the_key(names),
        check_every_type_carries_what_is_written_down(),
        check_every_type_is_written_down(),
        check_no_field_is_a_person_name(names),
        check_no_identifier_is_a_person_name(names),
        check_every_planted_person_is_refused(planted),
        check_the_word_list_never_refuses_alone(planted),
        check_the_scan_reaches_what_is_not_a_dataclass(),
        check_nothing_can_be_attached_at_runtime(names),
        check_no_contract_declares_a_customer_dimension(names),
        check_the_source_and_the_objects_agree(),
        check_every_explanation_still_explains_something(names),
    )

    by_publisher: dict[str, int] = {}
    for external in names:
        by_publisher[external.publisher] = by_publisher.get(external.publisher, 0) + 1
    caught_by_the_word_list = {
        attack.external.name for attack, _, word_list in planted if word_list
    }
    fields = sum(len(field_names(cls)) for cls in core_types())

    return Report(
        claim=7,
        title="oversight — a decision that targets a person is structurally impossible",
        checks=checks,
        numbers=(
            ("published person-names", f"{len(names)}"),
            *((f"  {publisher}", str(count)) for publisher, count in sorted(by_publisher.items())),
            ("types on the decision path", str(len(decision_path_types()))),
            ("fields scanned", str(fields)),
            ("identifiers scanned", str(len({i.name for i in reference.identifiers()}))),
            ("attacks planted", f"{len(planted):,}"),
            ("  refused by the closed field set", f"{sum(1 for _, s, _ in planted if s):,}"),
            (
                "  refused by the hand-written word list",
                f"{sum(1 for _, _, w in planted if w):,} "
                f"({len(caught_by_the_word_list)}/{len(names)} = "
                f"{len(caught_by_the_word_list) * 100 / len(names):.1f}% of the names)",
            ),
            ("explained collisions", str(len(EXPLAINED))),
            *((f"  {name}", _one_line(why)) for name, why in sorted(EXPLAINED.items())),
        ),
        notes=(
            "that a name neither vocabulary publishes would be *recognised* — O4 and O5 read "
            "names, and they can only read the 317 somebody else wrote down. What does not "
            "depend on any list is O2: the closed field set refuses a field called `q7` as "
            "readily as one called `nationality`, and that is the guard this claim rests on",
            "that a field spelled without word boundaries would be matched. `customerid` is "
            "one token and O4 would not see it; `customer_id` is two and it would. The "
            "boundary rule is what keeps a three-letter Presidio entity from crying wolf, and "
            "its cost is stated here rather than discovered",
            "that no person appears anywhere in the data this system reads. The claim is "
            "about what a decision is addressed by, not about what a POS line contains — "
            "bronze carries whatever the source sends, and that is the pipelines' business",
            "that a person could not be re-identified by joining store, SKU and time outside "
            "this system. Claim 7 is that no decision *targets* a person; it is not a "
            "statement about what somebody else could infer from an aggregate",
            "that the eight explained collisions are the only ones that will ever be "
            "innocent. Ordinary engineering English overlaps with the vocabulary of "
            "personhood, and each new overlap is a conversation rather than an addition",
        ),
    )
