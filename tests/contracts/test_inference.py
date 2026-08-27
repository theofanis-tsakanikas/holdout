"""`contracts/design/inference.yaml` — the dials, and the two constants computed twice.

Why the file exists at all is argued in the contract's own header: an alpha chosen per
experiment is a degree of freedom, and anything that can be chosen after the fact will be
chosen after the fact. What is checked here is that the file behaves like every other
contract — schema, provenance, exact `Decimal` values — plus one thing no other contract
needs.

**The quantiles are recomputed.** `holdout.core` may not import a statistics library, so
three standard-normal quantiles are written out as literals. A literal is exactly the shape
of number this repository refuses to take on trust, and a `note` saying "this is
inv_cdf(0.975)" is prose. So this module recomputes all three with
`statistics.NormalDist().inv_cdf` — legal here, outside `core/` — and asserts agreement to
the six decimal places the contract declares. That is `evals/`'s rule 5, *a boundary that
has to be known is computed twice*, applied to a constant.

The recomputation is a genuinely different mechanism and not a second reading of the same
number: `NormalDist.inv_cdf` is the standard library's rational approximation to the
inverse normal CDF, and it knows nothing about this repository.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from statistics import NormalDist
from typing import Any

import pytest
import yaml

from holdout.contracts.errors import ContractError
from holdout.contracts.loader import CONTRACTS_DIR, load, validator_for
from holdout.contracts.model import ContractSet

INFERENCE = CONTRACTS_DIR / "design" / "inference.yaml"
DOCUMENT = yaml.safe_load(INFERENCE.read_text(encoding="utf-8"))

#: The declared precision of the three quantiles. Six places, because the power calculation
#: is a normal approximation whose answer is a ceiling over whole units: a seventh place
#: could not move a decision, and claiming one would be claiming precision the method has
#: not got.
PLACES = Decimal("0.000001")


def _rounded(value: float) -> Decimal:
    """The stdlib's answer, at the contract's declared precision.

    `str()` and not `Decimal(value)`: the float is a binary approximation and
    `Decimal(0.975)` would carry fifty digits of it into the comparison. The shortest
    round-tripping decimal string is what a person would have written down.
    """
    return Decimal(str(value)).quantize(PLACES)


# ------------------------------------------------------------------ the two quantiles


def test_the_two_sided_quantile_is_the_one_the_standard_library_computes(
    contracts: ContractSet,
) -> None:
    alpha = contracts.inference.alpha
    upper = Decimal(1) - alpha / Decimal(2)
    assert upper == Decimal("0.975")
    assert contracts.inference.z_two_sided_alpha == _rounded(NormalDist().inv_cdf(float(upper)))


def test_the_one_sided_quantile_is_the_one_the_standard_library_computes(
    contracts: ContractSet,
) -> None:
    """Declared separately because a one-sided design sizes on a smaller quantile.

    A design that declared a direction and then sized on 1.959964 would ask for more units
    than its own hypothesis requires — not wrong, but not what it said it was doing.
    """
    upper = Decimal(1) - contracts.inference.alpha
    assert contracts.inference.z_one_sided_alpha == _rounded(NormalDist().inv_cdf(float(upper)))
    assert contracts.inference.z_one_sided_alpha < contracts.inference.z_two_sided_alpha


def test_the_power_quantile_is_the_one_the_standard_library_computes(
    contracts: ContractSet,
) -> None:
    power = contracts.inference.target_power
    assert contracts.inference.z_power == _rounded(NormalDist().inv_cdf(float(power)))


def test_the_quantiles_are_not_asserted_against_themselves() -> None:
    """The check above would be vacuous if it read the contract on both sides.

    Written out here as the numbers a reader can check by hand against any normal table,
    so that a future edit which "fixed" the recomputation to read the YAML would have to
    walk past this line to do it.
    """
    assert _rounded(NormalDist().inv_cdf(0.975)) == Decimal("1.959964")
    assert _rounded(NormalDist().inv_cdf(0.95)) == Decimal("1.644854")
    assert _rounded(NormalDist().inv_cdf(0.80)) == Decimal("0.841621")


# ------------------------------------------------------------------ the values themselves


def test_every_value_is_an_exact_decimal_and_never_a_float(contracts: ContractSet) -> None:
    """PyYAML made `0.05` a binary float; nothing downstream may ever see one.

    `Decimal(0.05)` is `0.05000000000000000277...`, and an alpha that is a fraction above
    what was declared is an alpha nobody declared.
    """
    settings = contracts.inference
    for name in (
        "alpha",
        "target_power",
        "z_two_sided_alpha",
        "z_one_sided_alpha",
        "z_power",
        "balance_tolerance_smd",
        "exposure_min_pct",
        "holdout_share_pct",
    ):
        value = getattr(settings, name)
        assert isinstance(value, Decimal), name
    assert settings.alpha == Decimal("0.05")
    assert settings.target_power == Decimal("0.80")
    assert settings.balance_tolerance_smd == Decimal("0.10")


def test_the_budgets_and_the_radius_are_whole_numbers(contracts: ContractSet) -> None:
    settings = contracts.inference
    assert settings.permutation_draws == 1000
    assert settings.max_assignment_attempts == 10000
    assert settings.neighbour_radius_m == 1000
    for name in ("permutation_draws", "max_assignment_attempts", "neighbour_radius_m"):
        assert isinstance(getattr(settings, name), int), name


def test_the_holdout_share_leaves_both_arms_non_empty(contracts: ContractSet) -> None:
    """A holdout of nothing is not a holdout; a holdout of everything has no treatment.

    The schema refuses both ends, and this is the assertion a reader can find without
    opening the schema.
    """
    share = contracts.inference.holdout_share_pct
    assert Decimal(0) < share < Decimal(100)


# ------------------------------------------------------------------ the carryover block


def test_the_carryover_block_declares_two_facts_and_one_absence(contracts: ContractSet) -> None:
    """`washout_weeks: null` is the load-bearing entry, and null is not zero.

    Zero would assert that no washout is needed. Null says none is declared, which is why
    `store_week` is refused — by a paragraph in a contract, not by a calculation.
    """
    carryover = contracts.inference.carryover
    assert carryover.reference_price_memory is True
    assert carryover.cross_price_substitution is True
    assert carryover.washout_weeks is None
    assert carryover.reference_price_is_exhausted is False


def test_a_declared_washout_exhausts_the_reference_price() -> None:
    """The other side of the same predicate, built here rather than read from the contract.

    `interference_of` is a pure function of this block, so the engine's refusal has to
    disappear when a washout is declared. That is asserted over the engine in
    `tests/core/test_design_engine.py`; this is the predicate underneath it.
    """
    from holdout.contracts.model import Carryover

    assert Carryover(
        reference_price_memory=True, cross_price_substitution=True, washout_weeks=4
    ).reference_price_is_exhausted


# ------------------------------------------------------------------ the contract layer's rules


def test_a_value_without_a_source_is_a_build_failure(
    contracts_copy: Path,
    edit_contract: Callable[[Path, Callable[[Any], Any]], None],
) -> None:
    """The reason `design` had to join `PROVENANCE_FAMILIES`.

    Before this file the walk descended guardrails and policies only, on the description
    "numbers that come from outside the repository". These come from inside and still need
    an argument beside them, and the schema alone would not catch a block added later.
    """

    def unsource(document: Any) -> Any:
        document["stopping"] = {"value": 3}
        return document

    edit_contract(contracts_copy / "design" / "inference.yaml", unsource)
    with pytest.raises(ContractError) as raised:
        load(contracts_copy)
    rules = {v.rule for v in raised.value.violations}
    assert "value_without_source" in rules


def test_a_legal_instrument_source_would_be_refused_here() -> None:
    """Not by the schema — by a reader, and this is where the argument is written down.

    Nothing in this file is law. An alpha of 0.05 is a convention this repository adopts,
    and dressing it as a cited instrument would be exactly the failure the
    `legal_instrument` / `scenario_assumption` split exists to make impossible.
    """
    kinds = {
        entry["source"]["kind"]
        for entry in DOCUMENT.values()
        if isinstance(entry, dict) and "source" in entry
    }
    nested = {
        inner["source"]["kind"]
        for key in ("quantiles", "carryover")
        for inner in DOCUMENT[key].values()
    }
    assert kinds | nested == {"scenario_assumption"}


def test_an_unknown_key_does_not_validate() -> None:
    """`additionalProperties: false`, so a setting added here without a schema entry is red.

    The failure it prevents: a threshold introduced in a hurry, read by nothing, and
    believed by everyone who finds it in the file.
    """
    document = yaml.safe_load(INFERENCE.read_text(encoding="utf-8"))
    document["peeking_allowance"] = {"value": 2}
    errors = list(validator_for("inference.schema.json").iter_errors(document))
    assert errors


def test_a_missing_setting_does_not_validate() -> None:
    """Every setting is required. An optional alpha is an alpha somebody supplies at the
    call site, which is the whole thing this contract exists to prevent."""
    document = yaml.safe_load(INFERENCE.read_text(encoding="utf-8"))
    del document["alpha"]
    errors = list(validator_for("inference.schema.json").iter_errors(document))
    assert errors


def test_the_file_is_claimed_by_the_loader(contracts_copy: Path) -> None:
    """An unclaimed file under `contracts/` is a build failure — the rename check, applied
    to the newest family member."""
    (contracts_copy / "design" / "inference.yaml").rename(
        contracts_copy / "design" / "inference_v2.yaml"
    )
    with pytest.raises(ContractError) as raised:
        load(contracts_copy)
    rules = {v.rule for v in raised.value.violations}
    assert "missing_contract" in rules
    assert "unclaimed_contract" in rules
