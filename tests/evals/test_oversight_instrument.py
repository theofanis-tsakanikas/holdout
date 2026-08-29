"""Arm claim 7's eval: break each check that has no mutation, and demand it goes red.

`make claim-7` plants seven mutations in `src/` and `contracts/` and demands that the check
each one names refuses. Six of the twelve checks are covered that way. The other six are not,
and for each of them there is a reason no mutation could be written:

| check | why there is no mutation |
|---|---|
| `O4` | any *field* a mutation could add is caught by `O2` first, and a mutation edits one file — it cannot add the field and update the registry in the same breath |
| `O6` | it asserts that every planted attack is refused. Making it fail means changing what is planted, which is eval code, not system code |
| `O7` | likewise: it is a comparison between two detectors over the same attacks |
| `O8` | coverage. Breaking it means narrowing the detector, and the detector lives in `ops/` — which the planter may not touch, because the planter editing the detector is the independence gone |
| `O11` | the second implementation. Same reason as `O8` |
| `O12` | the staleness of a list that lives in this eval |

That is exactly the arrangement `tests/evals/test_ledger.py` already has for `gate-proof`
itself — *the ledger is the one gate that cannot have a `gate-proof` mutation, because it
**is** `gate-proof`* — and the answer is the same one: break it here, on a deliberately
broken arrangement, and require the red.

Nothing in this file is a fixture somebody invented to be caught. Every break is a real
failure mode named in the check it breaks: a scan that lost `__slots__`, a lexicon whose
words are ours after all, an explanation that outlived the thing it explained.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest
from evals.oversight import checks, reference
from evals.oversight.build import Attack, ExternalName, decision_path_types, lexicon
from ops.personhood import field_names

from holdout.core.decision import DecisionKey
from ops import personhood


def _ours(name: str) -> ExternalName:
    """An external name that is in fact one of ours — the arrangement each break needs."""
    return ExternalName(
        name=name,
        published_as=name,
        publisher="a planted vocabulary",
        why="planted by tests/evals/test_oversight_instrument.py",
    )


# ---------------------------------------------------------------- the derivation itself


def test_tokens_reads_all_three_house_styles() -> None:
    """schema.org publishes camelCase, Presidio publishes SCREAMING_SNAKE, we write snake."""
    assert personhood.tokens("familyName") == ("family", "name")
    assert personhood.tokens("US_SSN") == ("us", "ssn")
    assert personhood.tokens("family_name") == ("family", "name")
    assert personhood.tokens("_loyalty_tier") == ("loyalty", "tier")


def test_the_lexicon_adds_region_tails_and_collapses_the_duplicates_they_create() -> None:
    """`US_PASSPORT` and `UK_PASSPORT` both derive `passport`; planting it twice would
    inflate every count in the eval by the number of countries that issue passports."""
    names = {external.name for external in lexicon()}
    assert "us_ssn" in names and "ssn" in names
    assert "passport" in names
    assert len(names) == len(lexicon()), "the lexicon is deduplicated by name"
    assert "customer" in names, (
        "the schema.org half must include properties whose *range* is Person, not only those "
        "whose domain is. `customer` arrives that way and it is the name a supermarket would "
        "actually reach for"
    )


def test_a_short_entity_does_not_match_inside_a_longer_word() -> None:
    """Presidio publishes `NRP`, three characters long. Substring matching would find it in
    any identifier containing those letters and the check would cry wolf."""
    nrp = (_ours("nrp"),)
    assert checks.matched_by("nrp", nrp)
    assert checks.matched_by("nrp_code", nrp)
    assert not checks.matched_by("enrolment_period", nrp)


# ------------------------------------------------- the names the prose names, pinned

#: The names quoted in prose as ones the hand-written word list **misses**.
#:
#: Pinned because the first version of that prose was wrong, and wrong in this project's own
#: most frequent shape: the examples were picked by reading the 317-name lexicon rather than
#: by asking `ops.personhood.person_shaped`, the function that would make the sentence true.
#: `telephone` contains `phone` and `personnummer` contains `person`, so the word list catches
#: both — and four documents said it missed them. The aggregate figures were right the whole
#: time; only the illustrations were invented. `tests/evals/test_guardrail_instrument.py` pins
#: claim 1's 716 and 6,650 for the same reason: a figure in prose that the code contradicts is
#: red in the suite rather than wrong in a paragraph.
NAMED_AS_MISSED = (
    "family_name",
    "given_name",
    "nationality",
    "job_title",
    "spouse",
    "sibling",
    "buyer",
    "owner",
    "recipient",
    "nif",
    "aadhaar",
    "fiscal_code",
    "passport",
)

#: And the ones prose names as caught, so the claim is pinned in both directions.
NAMED_AS_CAUGHT = ("customer", "telephone", "personnummer")


@pytest.mark.parametrize("name", NAMED_AS_MISSED)
def test_a_name_the_prose_calls_missed_is_really_missed(name: str) -> None:
    assert name in {external.name for external in lexicon()}, f"{name} is not in the lexicon"
    assert not personhood.person_shaped(name), (
        f"the prose in evals/oversight/README.md, CLAUDE.md, PLAN.md and TASKS.md says the "
        f"hand-written word list misses {name!r}, and it does not: "
        f"{personhood.person_shaped(name)}"
    )


@pytest.mark.parametrize("name", NAMED_AS_CAUGHT)
def test_a_name_the_prose_calls_caught_is_really_caught(name: str) -> None:
    assert name in {external.name for external in lexicon()}
    assert personhood.person_shaped(name)


def test_the_published_reach_is_the_one_the_prose_quotes() -> None:
    """35 of 317, and 282 missed. Every document on this branch quotes those three."""
    names = [external.name for external in lexicon()]
    caught = [name for name in names if personhood.person_shaped(name)]
    assert (len(names), len(caught), len(names) - len(caught)) == (317, 35, 282)


# ------------------------------------------------------------------------ O4 · O1 · O10


def test_o1_goes_red_when_a_published_name_is_one_of_the_key_s_four() -> None:
    check = checks.check_the_key((_ours("occasion"),))
    assert not check.passed
    assert any("occasion" in example for example in check.counterexamples)


def test_o4_goes_red_when_a_field_carries_a_published_name() -> None:
    check = checks.check_no_field_is_a_person_name((_ours("store_id"),))
    assert not check.passed
    assert check.counterexamples


def test_o10_goes_red_when_a_contract_declares_a_published_name() -> None:
    """`store_id` really is a metric grain component, so this break needs no fake contract:
    it only needs a vocabulary that calls `store_id` a person."""
    check = checks.check_no_contract_declares_a_customer_dimension((_ours("store_id"),))
    assert not check.passed
    assert any("metric grain" in example for example in check.counterexamples)


# ------------------------------------------------------------------------------ O5 · O12


def test_o5_goes_red_when_a_collision_is_not_explained(monkeypatch: pytest.MonkeyPatch) -> None:
    """Six identifiers in the core collide with a published person-name today. Empty the
    reviewed list and every one of them is unexplained, which is what O5 exists to say."""
    monkeypatch.setattr(checks, "EXPLAINED", {})
    check = checks.check_no_identifier_is_a_person_name(lexicon())
    assert not check.passed
    assert len(check.counterexamples) >= 6


def test_o12_goes_red_on_an_explanation_that_explains_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The failure mode is precise: an entry left behind after the identifier it excused was
    renamed is a name pre-approved for whoever adds it next."""
    monkeypatch.setattr(
        checks,
        "EXPLAINED",
        {**checks.EXPLAINED, ("spouse", "spouse"): "nothing in this repository is called that"},
    )
    check = checks.check_every_explanation_still_explains_something(lexicon())
    assert not check.passed
    assert any("spouse" in example for example in check.counterexamples)


def test_a_private_type_is_not_exempt_from_the_registry() -> None:
    """A leading underscore exempted a type from `unlisted()` until 2026-08-29.

    It read as hygiene — a private helper is not on the decision path — and what it actually
    did was leave one spelling that walks past the guard while `O3`'s printed question said
    *every* type. Found by oversight level 2 renaming the class that
    `03-a-second-key-rides-alongside-the-first.yaml` plants, and watching it survive.
    `07-the-second-key-arrives-with-a-private-name.yaml` is the same break in that spelling;
    this test is the half that runs without planting anything.
    """

    @dataclasses.dataclass(frozen=True, slots=True)
    class _VisitContext:
        till_id: str
        visit_ordinal: int

    @dataclasses.dataclass(frozen=True, slots=True)
    class VisitContext:
        till_id: str
        visit_ordinal: int

    for cls in (_VisitContext, VisitContext):
        assert personhood.unlisted(types=[cls], registry={}) == [
            f"{cls.__module__}.{cls.__name__}"
        ], f"{cls.__name__} walked past the registry"


# ------------------------------------------------------------------------------ O6 · O7


def _planted(refused_by_structure: bool, refused_by_word_list: bool) -> list[Any]:
    attack = Attack(cls=DecisionKey, external=_ours("customer_id"))
    return [(attack, refused_by_structure, refused_by_word_list)]


def test_o6_goes_red_when_a_planted_person_is_not_refused() -> None:
    check = checks.check_every_planted_person_is_refused(_planted(False, True))
    assert not check.passed
    assert check.figure.startswith("0/1")


def test_o7_goes_red_when_only_the_word_list_refuses() -> None:
    """The whole argument of this eval in one assertion: if the hand-written words are ever
    the only thing that catches an attack, claim 7 is resting on a list somebody here wrote."""
    check = checks.check_the_word_list_never_refuses_alone(_planted(False, True))
    assert not check.passed
    assert "caught by the list alone" in check.figure


def test_o7_is_green_when_the_structure_refuses_whatever_the_word_list_does() -> None:
    assert checks.check_the_word_list_never_refuses_alone(_planted(True, False)).passed
    assert checks.check_the_word_list_never_refuses_alone(_planted(True, True)).passed


# ------------------------------------------------------------------------------ O8 · O2


def test_field_names_reads_slots_as_well_as_dataclass_fields() -> None:
    class Slotted:
        __slots__ = ("_key", "_price")

    class OneSlot:
        __slots__ = "_key"

    @dataclasses.dataclass(frozen=True, slots=True)
    class Fielded:
        key: str

    assert field_names(Slotted) == frozenset({"_key", "_price"})
    assert field_names(OneSlot) == frozenset({"_key"})
    assert field_names(Fielded) == frozenset({"key"})


def test_o8_and_o2_go_red_when_the_scan_loses_slots(monkeypatch: pytest.MonkeyPatch) -> None:
    """The exact hole a review found: `CertifiedPrice` is not a dataclass because its
    constructor has to refuse, and a scan built on `dataclasses.fields` alone sees the
    actuation type as carrying nothing at all — while reporting a clean sweep of everything
    it can still see."""

    def blind(cls: type[Any]) -> frozenset[str]:
        if dataclasses.is_dataclass(cls):
            return frozenset(f.name for f in dataclasses.fields(cls))
        return frozenset()

    monkeypatch.setattr(personhood, "field_names", blind)
    monkeypatch.setattr(checks, "field_names", blind)
    assert not checks.check_the_scan_reaches_what_is_not_a_dataclass().passed
    assert not checks.check_every_type_carries_what_is_written_down().passed


# ----------------------------------------------------------------------------- O11


def test_o11_goes_red_when_the_source_and_the_objects_disagree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A field that exists at runtime and appears nowhere in the source — or the reverse —
    shows up here and in no other check."""
    real = reference.field_sets()
    key = f"{DecisionKey.__module__}.{DecisionKey.__name__}"
    monkeypatch.setattr(reference, "field_sets", lambda: {**real, key: real[key] | {"customer_id"}})
    check = checks.check_the_source_and_the_objects_agree()
    assert not check.passed
    assert any("customer_id" in example for example in check.counterexamples)


def test_o11_reads_every_type_the_registry_names() -> None:
    """A second implementation that silently covered half the types would agree easily."""
    from_source = reference.field_sets()
    for cls in decision_path_types():
        assert f"{cls.__module__}.{cls.__name__}" in from_source
