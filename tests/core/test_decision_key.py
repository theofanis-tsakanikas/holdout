"""Claim 7 — a decision that targets a person is structurally impossible.

The decision key has no customer dimension, and this file is the test that goes red if one
appears. It is cheap, it needs nothing but the core, and PLAN.md puts it in phase 1 for
exactly that reason.

Why this file is written the way it is
---------------------------------------
It started as a substring blacklist over `dataclasses.fields`, and a review broke it three
ways in about a minute: `subject_hash` on `ProposedPrice` passed because the word was not on
the list; `_customer_id` in `CertifiedPrice.__slots__` passed because `CertifiedPrice` is
deliberately **not** a dataclass — the design choice that makes claim 1 strong made claim 7
blind to the actuation type itself; and `basket_id` on `DecisionKey` was caught only by the
exact-field-set assertion, not by the scan.

A blacklist only ever catches an honest mistake. Claim 7 is a structural claim, so the
structure is what is asserted:

* **the exact field set of every type on the decision path**, written out, so that adding
  *any* field — however innocent, however unrelated to a person — turns this red and
  somebody has to say what it is for;
* the blacklist as well, over dataclass fields **and** `__slots__`, because it is what
  catches a person-shaped field arriving on a type nobody thought to list.

The first is the claim. The second is a net under it.

Where the rule moved, and why — 2026-08-29, T006
------------------------------------------------
The registry and the word list used to live in this file. They now live in
`ops/personhood.py`, with this file and `evals/oversight/` as the two callers — the same
arrangement `ops/isolation.py` has for the corpus barrier, for the same reason: two
hand-written copies of one rule drift, and the copy that drifts is the one nobody reads.

Nothing about the assertions changed in the move. What changed is that a second caller now
exists that asks a question this file cannot: **against 317 names two published vocabularies
use for a person, does the guard still refuse when each of them is planted?** Measured, the
`PERSON_SHAPED` tuple below catches 35 of those 317. That is the answer to *who wrote the
case this guard is tested on* — and it is why the sentence above says the word list is a net
and not the claim. `make claim-7`.
"""

from __future__ import annotations

from typing import Any

import pytest
from ops.personhood import (
    FIELDS_ON_THE_DECISION_PATH,
    core_types,
    field_names,
    misdeclared,
    person_shaped,
    unlisted,
)

from holdout.contracts.model import ContractSet
from holdout.core.decision import DecisionKey, DecisionPath
from holdout.core.guardrails import CertifiedPrice

# ------------------------------------------------------------------ the structural claim


@pytest.mark.parametrize("cls", list(FIELDS_ON_THE_DECISION_PATH), ids=lambda c: c.__name__)
def test_the_type_carries_exactly_the_fields_written_down_here(cls: type[Any]) -> None:
    """Adding any field to a decision-path type is a red test and a conversation."""
    assert field_names(cls) == FIELDS_ON_THE_DECISION_PATH[cls]


def test_the_registry_reports_the_same_offences_as_the_parametrised_assertion() -> None:
    """`misdeclared()` is what `evals/oversight/` calls; this file asserts type by type.

    Two readings of one rule, and they must agree. The parametrised assertion above names
    the offending type in the test id, which is what a session wants; `misdeclared()` returns
    the whole list at once, which is what a report wants. If they could disagree, the eval
    and the suite would be two guards rather than two callers.
    """
    assert misdeclared() == []


def test_every_decision_path_type_is_listed() -> None:
    """The registry is the claim, so a new type on the path must join it.

    Without this, claim 7 could be defeated by adding a *type* rather than a field — a
    `CustomerContext` nobody listed, carried on a proposal, asserted nowhere.
    """
    assert not unlisted(), (
        "a type in holdout.core carries fields and is not in FIELDS_ON_THE_DECISION_PATH. "
        "Either it is on the decision path — in which case write its fields down — or it is "
        "not, in which case say so by listing it anyway:\n  " + "\n  ".join(unlisted())
    )


# ------------------------------------------------------------------ the net under it


def test_no_type_in_the_core_carries_a_customer_dimension() -> None:
    classes = core_types()
    assert len(classes) >= 10, "the scan found almost nothing and would pass vacuously"
    assert CertifiedPrice in classes, (
        "the actuation type is not a dataclass, and a scan that cannot see it is a scan "
        "with a hole exactly where claim 7 matters most"
    )
    offences = [
        f"{cls.__module__}.{cls.__name__}.{name} ({', '.join(person_shaped(name))})"
        for cls in classes
        for name in sorted(field_names(cls))
        if person_shaped(name)
    ]
    assert not offences, (
        "a decision in this system is addressed by what is being priced and where. These "
        "fields would give it somewhere to attach a person:\n  " + "\n  ".join(offences)
    )


# ------------------------------------------------------------------ the key itself


def test_the_key_is_the_contract_s_idempotency_key(contracts: ContractSet) -> None:
    """`ladder_policy@v1` declares `[sku_id, store_id, ladder_step]`, and the key answers all
    three. Re-running a decision therefore never produces a second price change."""
    ladder = next(p for p in contracts.policies if p.id == "ladder_policy")
    assert ladder.idempotency_key == ("sku_id", "store_id", "ladder_step")
    key = DecisionKey(path=DecisionPath.MARKDOWN, sku_id="sku-1", store_id="store-7", occasion=3)
    assert key.sku_id == "sku-1"
    assert key.store_id == "store-7"
    assert key.ladder_step == 3


def test_the_base_price_path_has_no_ladder_step() -> None:
    """The occasion means something different on each path, and the path is in the key, so
    a markdown rung and a pricing-week ordinal can never collide."""
    key = DecisionKey(path=DecisionPath.BASE_PRICE, sku_id="sku-1", store_id="store-7", occasion=3)
    assert key.ladder_step is None
    markdown = DecisionKey(
        path=DecisionPath.MARKDOWN, sku_id="sku-1", store_id="store-7", occasion=3
    )
    assert key != markdown


def test_two_decisions_for_the_same_rung_are_the_same_decision() -> None:
    first = DecisionKey(path=DecisionPath.MARKDOWN, sku_id="sku-1", store_id="store-7", occasion=2)
    second = DecisionKey(path=DecisionPath.MARKDOWN, sku_id="sku-1", store_id="store-7", occasion=2)
    assert first == second
    assert len({first, second}) == 1


@pytest.mark.parametrize(
    ("sku", "store", "occasion"),
    [("", "store-7", 1), ("sku-1", "", 1), ("sku-1", "store-7", 0)],
)
def test_a_key_that_names_nothing_is_refused(sku: str, store: str, occasion: int) -> None:
    with pytest.raises(ValueError, match=r"decision|occasion"):
        DecisionKey(path=DecisionPath.MARKDOWN, sku_id=sku, store_id=store, occasion=occasion)
