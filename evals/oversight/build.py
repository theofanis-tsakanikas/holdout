"""The join: two published vocabularies of person-names, and the types a decision passes through.

`corpus/real/` knows nothing about this system — it imports nothing from `holdout` and
`tests/boundary/test_corpus_imports_nothing.py` fails the build if that changes.
`ops/personhood.py` knows nothing about the corpus. This module is where the two meet, and
it is the only place in the eval that reads both.

Observed, derived, swept
------------------------
Doctrine rule 3 is the easiest rule in this repository to break by accident, so the three
columns are kept sharp.

**observed** — the 156 schema.org properties whose domain or range includes `Person`, and
the 99 PII entity types Microsoft Presidio publishes recognizers for. Both are committed,
digest-checked, and written down in their publisher's own spelling.

**derived** — the spelling. This repository writes fields as `snake_case`; schema.org
publishes `familyName` and Presidio publishes `US_SSN`. `ops.personhood.tokens` breaks a
name into its words whatever style spelled it, and `_.join` puts it back the way a field
here would be written. One further derivation, stated because it is a decision and not a
transcription: **a Presidio entity whose leading token is a two-letter region code also
contributes its remainder** — `US_SSN` yields `us_ssn` *and* `ssn`, `UK_NHS` yields `nhs`,
`DE_TAX_ID` yields `tax_id`. A field in a Greek supermarket's pricing system would not be
called `us_ssn`; it might well be called `tax_id`. The derivation only ever **adds** names,
so it errs towards more attacks and never towards fewer, and the count it adds is published.

**swept** — nothing is drawn at random. The lexicon is sorted, the types are sorted by
module and name, and the attack grid is their product in that order, so a red run reproduces
exactly and the counterexamples a failure prints are the same ones every time.

What this module must never do
------------------------------
Curate. `DATE_TIME`, `LOCATION`, `URL` and `UUID` are on Presidio's published list and they
stay on it; `brand`, `award`, `height` and `weight` are on schema.org's and they stay too.
The moment this file starts deciding which of somebody else's names count as a person, the
inputs are being chosen here again — which is claim 7's trap wearing a filter.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any

from corpus.real import person_properties, pii_entities
from ops.personhood import FIELDS_ON_THE_DECISION_PATH, field_names, person_shaped, tokens

#: A leading token of exactly two characters on a Presidio entity is its region code —
#: `US_SSN`, `UK_NHS`, `ES_NIF`, `IT_FISCAL_CODE`. The tail is the name the identifier is
#: actually known by, and it is the one a field here could plausibly be called.
REGION_CODE_LENGTH = 2


@dataclass(frozen=True, slots=True)
class ExternalName:
    """One name somebody else published for a person, spelled the way a field here would be."""

    name: str
    """`snake_case`, derived. This is what gets planted."""

    published_as: str
    """The publisher's own spelling — `familyName`, `US_SSN`. Printed in counterexamples so
    a reader can go and look it up rather than take this file's word for it."""

    publisher: str
    why: str
    """What the publisher says the name is for, in the publisher's terms: an attribute a
    person has, a field that holds one, or an entity a detector goes looking for."""


@dataclass(frozen=True, slots=True)
class Attack:
    """One planted person: this name, arriving as a field on this type.

    Nothing is written to disk and no class is modified. The attack is evaluated against the
    same two functions the guard is made of, on the field set the type *would* have — which
    is the only honest way to ask "would it be refused" without asking the guard to grade a
    change it never saw.
    """

    cls: type[Any]
    external: ExternalName

    @property
    def where(self) -> str:
        return f"{self.cls.__name__}.{self.external.name}"


def lexicon() -> tuple[ExternalName, ...]:
    """Every name the two vocabularies yield, deduplicated and sorted.

    Deduplication keeps the first publisher in sorted order and is reported as a number
    rather than done quietly: `US_PASSPORT`, `UK_PASSPORT`, `ES_PASSPORT`, `IT_PASSPORT`,
    `DE_PASSPORT`, `ZA_PASSPORT`, `KR_PASSPORT`, `PH_PASSPORT` and `IN_PASSPORT` all derive
    `passport`, and planting the same field name nine times would inflate every count in this
    eval by the number of countries that issue passports.
    """
    found: dict[str, ExternalName] = {}
    candidates: list[ExternalName] = []

    for published in sorted(person_properties(), key=lambda p: p.property):
        why = (
            "an attribute a person has"
            if published.describes_a_person
            else "a field that holds a person"
        )
        if published.describes_a_person and published.names_a_person:
            why = "an attribute a person has, and a field that holds one"
        candidates.append(
            ExternalName(
                name="_".join(tokens(published.property)),
                published_as=published.property,
                publisher="schema.org",
                why=why,
            )
        )

    for entity in sorted(pii_entities(), key=lambda e: e.entity):
        parts = tokens(entity.entity)
        candidates.append(
            ExternalName(
                name="_".join(parts),
                published_as=entity.entity,
                publisher="presidio",
                why=f"an entity a de-identification tool looks for ({entity.region})",
            )
        )
        if len(parts) > 1 and len(parts[0]) == REGION_CODE_LENGTH:
            candidates.append(
                ExternalName(
                    name="_".join(parts[1:]),
                    published_as=entity.entity,
                    publisher="presidio",
                    why=f"the same entity without its region code ({entity.region})",
                )
            )

    for candidate in candidates:
        found.setdefault(candidate.name, candidate)
    return tuple(sorted(found.values(), key=lambda e: e.name))


def decision_path_types() -> tuple[type[Any], ...]:
    """The types the attack is planted on, in a fixed order.

    Every type in the registry, not only the ones a price literally passes through. The
    registry's own comment gives the reason and it is the right one: an unlisted type is a
    place to put a field nobody asserted, and *"it is only the experiment layer"* is exactly
    how that would start.
    """
    return tuple(sorted(FIELDS_ON_THE_DECISION_PATH, key=lambda c: (c.__module__, c.__name__)))


def attacks(
    names: Sequence[ExternalName] | None = None,
    types: Sequence[type[Any]] | None = None,
) -> Iterator[Attack]:
    """Every (type, name) pair, in a declared deterministic order."""
    for cls in decision_path_types() if types is None else types:
        for external in lexicon() if names is None else names:
            yield Attack(cls=cls, external=external)


def refused_by_the_structure(attack: Attack) -> bool:
    """Would the written-down field set notice this field arriving?

    Computed rather than assumed. The field set the type *would* carry is its live one plus
    the planted name; the guard refuses when that is not the set written down beside it. A
    name that happened to already be a field would be no attack at all, and this returns
    `False` for it honestly instead of counting a refusal that never happened.
    """
    would_carry = field_names(attack.cls) | {attack.external.name}
    return would_carry != FIELDS_ON_THE_DECISION_PATH[attack.cls]


def refused_by_the_word_list(attack: Attack) -> bool:
    """Would the hand-written `PERSON_SHAPED` tuple notice it, in its own arithmetic?"""
    return bool(person_shaped(attack.external.name))


def matched_by(name: str, names: Sequence[ExternalName] | None = None) -> tuple[ExternalName, ...]:
    """Which external names this identifier carries, matched on word boundaries.

    Token containment, not substring: `("family", "name")` is found inside
    `("legal", "family", "name")` and not inside `("familiarity",)`. Substring matching would
    have `nrp` — a real Presidio entity, three characters long — inside any identifier that
    happens to contain those letters, and a check that cries wolf is a check somebody turns
    off. The cost of the boundary rule is stated where it belongs, in this eval's `notes`: a
    field spelled `customerid` with no separator is one token and is **not** matched here.
    That is exactly why the guard this claim rests on is the closed field set, which does not
    read names at all.
    """
    subject = tokens(name)
    return tuple(
        external
        for external in (lexicon() if names is None else names)
        if _contains(subject, tokens(external.name))
    )


def _contains(subject: tuple[str, ...], needle: tuple[str, ...]) -> bool:
    if not needle or len(needle) > len(subject):
        return False
    return any(
        subject[start : start + len(needle)] == needle
        for start in range(len(subject) - len(needle) + 1)
    )
