"""Every refusal vocabulary is closed, in all three places at once.

The set of codes lives in `contracts/schemas/reason_codes.schema.json`; their meanings live
in `contracts/vocabularies/reason_codes.yaml`; the core branches on an enum. A code added to
one of the three and not the others turns this file red, which is the friction that stops a
closed vocabulary becoming free text one exception at a time.

Three places and not two on purpose. The core cannot read the contract at runtime — it may
not import a YAML parser — and it cannot use free-text strings either, because claim 1's
evidence is a *count* of which guardrails fired and claim 6's is "N proposed, M refused,
K would have been wrong". Nobody can count free text.

**All three moments are checked here**, because the system refuses three different things —
a price, an experiment and a number — and each has its own enum in `core/`. The design and
readout halves were the ones with no core-side check until the design engine existed to
branch on them, which is exactly how a vocabulary drifts: the half nothing reads is the half
nobody notices moving.
"""

from __future__ import annotations

import json

import yaml

from holdout.contracts.loader import CONTRACTS_DIR, REASON_CODES, SCHEMA_DIR
from holdout.contracts.model import ContractSet
from holdout.core.design import DESIGN_PRECEDENCE, DesignRefusalCode
from holdout.core.experiment import CHECK_OF, CODE_OF, ReadoutRefusalCode, ValidityCheck
from holdout.core.guardrails import PRECEDENCE, GuardrailId, RefusalCode

SCHEMA = json.loads((SCHEMA_DIR / "reason_codes.schema.json").read_text(encoding="utf-8"))
DOCUMENT = yaml.safe_load((CONTRACTS_DIR / REASON_CODES).read_text("utf-8"))


def schema_codes(moment: str) -> set[str]:
    return set(SCHEMA["properties"][moment]["items"]["properties"]["code"]["enum"])


SCHEMA_CODES = schema_codes("at_decision")


def test_the_core_enum_and_the_schema_enumerate_the_same_codes() -> None:
    assert {code.value for code in RefusalCode} == SCHEMA_CODES


def test_every_code_in_the_schema_has_a_meaning_and_vice_versa(
    contracts: ContractSet,
) -> None:
    assert contracts.reason_codes.decision_codes == SCHEMA_CODES


def test_every_code_names_the_guardrail_that_produces_it(contracts: ContractSet) -> None:
    """Claim 1's evidence is which guardrails fired, so every code maps to one of the five —
    or to `any`, for the two no single guardrail owns."""
    admissible = {g.value for g in GuardrailId} | {"any"}
    for code in contracts.reason_codes.at_decision:
        assert code.guardrail in admissible, code.code


def test_only_the_two_codes_that_genuinely_span_guardrails_are_any(
    contracts: ContractSet,
) -> None:
    """An empty admissible range is a crossing between two guardrails, and a missing input
    can be missed by whichever rule needed it. Everything else belongs to exactly one."""
    spanning = {c.code for c in contracts.reason_codes.at_decision if c.guardrail == "any"}
    assert spanning == {"NO_PRICE_SATISFIES_EVERY_GUARDRAIL", "INPUT_NOT_AVAILABLE"}


def test_every_refusal_names_what_would_fix_it(contracts: ContractSet) -> None:
    """Even when the answer is "nothing, and disposal is correct". A refusal that names no
    remedy is an obstacle rather than a system telling you something."""
    for code in contracts.reason_codes.at_decision:
        assert code.what_would_fix_it, code.code


def test_the_precedence_order_covers_the_vocabulary_exactly() -> None:
    """The order decides which code leads a refusal. A code missing from it would raise a
    KeyError the first time it fired, which is a bad way to find out."""
    assert set(PRECEDENCE) == set(RefusalCode)
    assert len(PRECEDENCE) == len(RefusalCode)


def test_the_three_moments_do_not_share_a_code(contracts: ContractSet) -> None:
    """A refusal of a price, a refusal of an experiment and a refusal of a number are
    different events. A code that meant one thing at design and another at decision would
    make every count ambiguous."""
    codes = contracts.reason_codes
    at_decision = {c.code for c in codes.at_decision}
    at_design = {c.code for c in codes.at_design}
    at_readout = {c.code for c in codes.at_readout}
    assert not at_decision & at_design
    assert not at_decision & at_readout
    assert len(codes.all_codes) == len(at_decision) + len(at_design) + len(at_readout)


def test_the_vocabulary_has_no_duplicates() -> None:
    listed = [entry["code"] for entry in DOCUMENT["at_decision"]]
    assert len(listed) == len(set(listed))


# ------------------------------------------------------------------ the design moment


def test_the_design_enum_and_the_schema_enumerate_the_same_codes() -> None:
    assert {code.value for code in DesignRefusalCode} == schema_codes("at_design")


def test_every_design_code_in_the_schema_has_a_meaning_and_vice_versa(
    contracts: ContractSet,
) -> None:
    assert {c.code for c in contracts.reason_codes.at_design} == schema_codes("at_design")


def test_the_design_precedence_covers_the_design_vocabulary_exactly() -> None:
    """The order decides which code leads a refusal, so a code missing from it would raise a
    KeyError the first time it fired — which is a bad way to find out."""
    assert set(DESIGN_PRECEDENCE) == set(DesignRefusalCode)
    assert len(DESIGN_PRECEDENCE) == len(DesignRefusalCode)


def test_the_design_vocabulary_has_no_duplicates() -> None:
    listed = [entry["code"] for entry in DOCUMENT["at_design"]]
    assert len(listed) == len(set(listed))


# ------------------------------------------------------------------ the readout moment


def test_the_readout_enum_and_the_schema_enumerate_the_same_codes() -> None:
    assert {code.value for code in ReadoutRefusalCode} == schema_codes("at_readout")


def test_every_readout_code_in_the_schema_has_a_meaning_and_vice_versa(
    contracts: ContractSet,
) -> None:
    assert {c.code for c in contracts.reason_codes.at_readout} == schema_codes("at_readout")


def test_the_four_checks_and_the_four_codes_are_a_bijection() -> None:
    """A code with two checks, or a check producing none, would be a readout that reports
    four figures and refuses for a reason none of them explains."""
    assert set(CHECK_OF) == set(ReadoutRefusalCode)
    assert set(CODE_OF) == set(ValidityCheck)
    for code, check in CHECK_OF.items():
        assert CODE_OF[check] is code


def test_the_core_and_the_contract_agree_on_which_check_produces_which_code(
    contracts: ContractSet,
) -> None:
    """The contract carries a `check` field for exactly this, and until the readout existed
    nothing compared the two. A mapping asserted in one place and used in the other is a
    mapping that drifts."""
    declared = {c.code: c.check for c in contracts.reason_codes.at_readout}
    for code, check in CHECK_OF.items():
        assert declared[code.value] == check.value, code


def test_the_readout_vocabulary_has_no_duplicates() -> None:
    listed = [entry["code"] for entry in DOCUMENT["at_readout"]]
    assert len(listed) == len(set(listed))
