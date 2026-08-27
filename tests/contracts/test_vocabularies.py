"""The closed vocabularies are closed.

Three moments now, because the system refuses three different things: a price, an
experiment and a number. The decision-time half is asserted from the core's side in
`tests/core/test_refusal_codes.py`, where the enum that branches on it lives; what is
checked here is the design and readout halves and the shape they all share.

Claim 6 reports "N designs proposed, M refused, K of those would have produced a
confidently wrong number". That sentence is only countable because the reasons are
enumerable, so the set of codes lives in a JSON Schema, their meanings live in the YAML,
and the two must agree in both directions. Adding a code is then a code change with a test,
which is the friction that keeps the vocabulary from becoming free text one exception at a
time.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from holdout.contracts.errors import ContractError
from holdout.contracts.loader import (
    CONTRACTS_DIR,
    REASON_CODES,
    SCHEMA_DIR,
    load,
    validator_for,
)
from holdout.contracts.model import ContractSet

SCHEMA = json.loads((SCHEMA_DIR / "reason_codes.schema.json").read_text(encoding="utf-8"))
DOCUMENT = yaml.safe_load((CONTRACTS_DIR / REASON_CODES).read_text("utf-8"))

# The vocabulary as CLAUDE.md enumerates it. Written out here on purpose: this is the third
# place, and it is the one a reviewer reads against the document. If a code is added to the
# schema and the YAML and nowhere else, this test is what notices.
AT_DESIGN = {
    "UNDERPOWERED_FOR_DURATION",
    "UNDERPOWERED_FOR_CAPACITY",
    "UNIT_GUARANTEES_INTERFERENCE",
    "STOPPING_RULE_PERMITS_PEEKING",
    "EXCLUSIONS_DEFINED_POST_HOC",
    "METRIC_NOT_IN_CONTRACT",
    "UNITS_ALREADY_COMMITTED",
    # Added with the design engine. Without it a roster on which the re-randomisation
    # screen never accepts has no correct output at all: raising would make an infeasible
    # design an error, and the whole point of the engine is that infeasibility is a refusal
    # that names what would fix it.
    "NO_ADMISSIBLE_ASSIGNMENT",
}
AT_READOUT = {
    "IMBALANCED_PRE_PERIOD",
    "EXPOSURE_BELOW_THRESHOLD",
    "CONTAMINATED_ASSIGNMENT",
    "POWER_NOT_REACHED",
}


def _schema_codes(where: str) -> set[str]:
    return set(SCHEMA["properties"][where]["items"]["properties"]["code"]["enum"])


def test_the_schema_enumerates_exactly_the_codes_claude_md_names() -> None:
    assert _schema_codes("at_design") == AT_DESIGN
    assert _schema_codes("at_readout") == AT_READOUT


def test_every_code_in_the_schema_has_a_meaning_and_vice_versa(contracts: ContractSet) -> None:
    assert {c.code for c in contracts.reason_codes.at_design} == _schema_codes("at_design")
    assert {c.code for c in contracts.reason_codes.at_readout} == _schema_codes("at_readout")


def test_an_unknown_reason_code_is_rejected() -> None:
    """The refusal a future session will be tempted to invent rather than justify."""
    document = json.loads(json.dumps(DOCUMENT))
    document["at_design"].append(
        {
            "code": "LOOKED_WRONG_TO_ME",
            "meaning": "a free-text reason nobody can count, test or gate against",
        }
    )
    errors = list(validator_for("reason_codes.schema.json").iter_errors(document))
    assert errors, "an unenumerated reason code must not validate"


def test_a_readout_code_names_which_of_the_four_checks_produces_it(
    contracts: ContractSet,
) -> None:
    checks = {c.check for c in contracts.reason_codes.at_readout}
    assert checks == {"balance", "exposure", "contamination", "power"}


def test_every_design_refusal_names_what_would_fix_it(contracts: ContractSet) -> None:
    """A refusal that names no remedy is an obstacle, not a design partner."""
    for code in contracts.reason_codes.at_design:
        assert code.what_would_fix_it, code.code


def test_the_balance_covariates_are_fixed_and_measured_pre_period(
    contracts: ContractSet,
) -> None:
    covariates = contracts.balance_covariates
    assert set(covariates.ids) == {
        "category_revenue_8w",
        "store_format",
        "store_size_sqm",
        "waste_rate",
        "pricing_zone",
    }
    for covariate in covariates.covariates:
        assert covariate.measured == "pre_period", covariate.id


def test_a_covariate_measured_inside_the_window_is_rejected() -> None:
    """Screening on anything from inside the comparison window uses the same data twice."""
    document = yaml.safe_load(
        (CONTRACTS_DIR / "design" / "balance_covariates.yaml").read_text("utf-8")
    )
    document["covariates"][0]["measured"] = "in_period"
    errors = list(validator_for("balance_covariates.schema.json").iter_errors(document))
    assert errors


@pytest.mark.parametrize("family", ["at_decision", "at_design", "at_readout"])
def test_the_vocabulary_has_no_duplicates(family: str) -> None:
    codes = [entry["code"] for entry in DOCUMENT[family]]
    assert len(codes) == len(set(codes))


# ------------------------------------------------- the vocabulary's address is checked


def test_the_vocabulary_is_read_from_the_address_the_loader_names(repo_root: Path) -> None:
    """It moved from `contracts/design/` to `contracts/vocabularies/`.

    `design/` is named for the experiment-design engine and the file is two thirds about
    prices, so the address was wrong even though keeping one closed vocabulary in one file
    is right. Contract rule 1 makes a move cheap while the file is new and expensive later.
    """
    assert (repo_root / "contracts" / REASON_CODES).is_file()
    assert not (repo_root / "contracts" / "design" / "reason_codes.yaml").exists()


def test_a_contract_the_loader_no_longer_names_is_a_build_failure(
    contracts_copy: Path,
) -> None:
    """A rename must be red, not a silent skip.

    Without this, moving a contract and forgetting the loader leaves every consumer quietly
    not seeing it — the worst possible failure for a source of truth, because nothing
    breaks and nothing is reported.
    """
    (contracts_copy / REASON_CODES).rename(contracts_copy / "vocabularies" / "renamed.yaml")
    with pytest.raises(ContractError) as raised:
        load(contracts_copy)
    rules = {v.rule for v in raised.value.violations}
    assert "missing_contract" in rules
    assert "unclaimed_contract" in rules, "and the file at its new address is read by nothing"


def test_a_copy_left_behind_by_a_move_is_a_build_failure(contracts_copy: Path) -> None:
    """The failure a `cp`-and-forget move leaves behind, and the one a merge can resurrect.

    A stale, fully-valid-looking second copy of a source of truth sitting in the repository
    is worse than no copy: the loader goes on reading the new address while human beings
    read whichever they find first.
    """
    stale = contracts_copy / "design" / "reason_codes.yaml"
    stale.write_text((contracts_copy / REASON_CODES).read_text(encoding="utf-8"), "utf-8")
    with pytest.raises(ContractError) as raised:
        load(contracts_copy)
    offenders = [v for v in raised.value.violations if v.rule == "unclaimed_contract"]
    assert offenders and "reason_codes" in offenders[0].path
