"""`contracts/design/aa_harness.yaml` — what the eval consumes, and why it is not inference.yaml.

Two contracts hold numbers about the same experiment and neither may be reached for by
mistake. `inference.yaml` is what `holdout.core` reads: alpha, the balance tolerance, the
exposure floor, B. This one is what `evals/uplift/` reads: how many worlds, how many
lotteries, at what level the false-positive rate is tested, and where the line between a
grain and a unit sits. **A number the estimator never reads must not be mistakeable for one
it does**, and the split is what makes that structural rather than remembered — so the first
thing checked here is that the two files do not both hold the same key.

Everything else is the contract layer's ordinary discipline: exact `Decimal`s, a source on
every value, and a `scenario_assumption` on every one of them, because nothing in this file is
law and dressing a budget as a cited instrument would be the failure that split exists for.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import yaml
from corpus.world.scale import SCALES

from holdout.contracts.errors import ContractError
from holdout.contracts.loader import CONTRACTS_DIR, load
from holdout.contracts.model import ContractSet

HARNESS = CONTRACTS_DIR / "design" / "aa_harness.yaml"
INFERENCE = CONTRACTS_DIR / "design" / "inference.yaml"
DOCUMENT = yaml.safe_load(HARNESS.read_text(encoding="utf-8"))


def _sourced(document: Any, prefix: str = "") -> dict[str, Any]:
    """Every `{value, source}` leaf in the document, by dotted path."""
    found: dict[str, Any] = {}
    for key, entry in document.items():
        if not isinstance(entry, dict):
            continue
        path = f"{prefix}{key}"
        if "value" in entry and "source" in entry:
            found[path] = entry
        else:
            found.update(_sourced(entry, f"{path}."))
    return found


def test_the_two_design_contracts_share_no_key() -> None:
    """The split, asserted rather than described.

    A key present in both would be a number with two homes, and the one that gets edited
    would be whichever the editor opened. It is the same argument the repository makes about
    a hard-coded interference table and about two hand-written maps of the same bijection.
    """
    inference = yaml.safe_load(INFERENCE.read_text(encoding="utf-8"))
    structural = {"version", "effective_from", "note"}
    shared = (set(DOCUMENT) & set(inference)) - structural
    assert not shared, (
        f"{sorted(shared)} appear in both design contracts. One of the two files is what the "
        "core reads and the other is what the eval reads; a key in both is a number whose "
        "home depends on who opened which file"
    )


def test_k_is_the_number_the_claim_is_stated_at(contracts: ContractSet) -> None:
    """K = 200, and it is a product rather than a literal.

    CLAUDE.md and TASKS.md both name two hundred draws. It is stored as world seeds times
    lotteries because the two factors cost different things — a seed costs a generation and a
    lottery costs a readout — and a single K would hide which of the two a budget cut spent.
    """
    seeds = contracts.aa_harness.seeds
    assert seeds.draws == 200
    assert seeds.draws == seeds.world * seeds.lotteries_per_world_seed
    assert seeds.world > 1, (
        "a rate measured on one world seed is a rate about that world, and the seed stops "
        "being a choice somebody made only when there is more than one of it"
    )


def test_the_pathology_worlds_get_fewer_draws_and_w2_the_fewest(contracts: ContractSet) -> None:
    """The budget's shape, so a later edit that inverts it is visible.

    W2 is the most expensive draw in the harness — it cannot compose its potential outcomes,
    so it generates a world per lottery, twice over for the pair it publishes — and it is
    therefore the smallest count in the file. If that ever stops being true, either the
    composition property has changed or somebody has stopped counting generations.
    """
    seeds = contracts.aa_harness.seeds
    assert seeds.interference_draws < seeds.pathology_draws < seeds.draws


def test_the_machinery_names_a_scale_the_corpus_actually_has(contracts: ContractSet) -> None:
    """A scale nobody can generate would make every mutation report CRASHED, not a gate.

    The value is a string in a contract and the corpus is where scales are declared, so this
    is the one place the two are compared. `harness` is deliberately admissible here — the
    contract may name it, and the reason it does not is a budget argued in the contract's own
    note rather than a rule this test enforces.
    """
    assert contracts.aa_harness.machinery.scale in SCALES


def test_every_value_is_an_exact_decimal_and_never_a_float(contracts: ContractSet) -> None:
    """The same rule the rest of the contract layer lives by, applied to this file.

    A binary float cannot represent 2.5 exactly, and a threshold that is a hair below what it
    reads as is a threshold that fires on a rate at exactly the declared level.
    """
    harness = contracts.aa_harness
    assert harness.binomial_level == Decimal("0.01")
    assert harness.false_refusal_max_pct == Decimal("10")
    assert harness.coverage_tolerance_pct == Decimal("5")
    assert harness.per_world_min_correct_pct == Decimal("90")
    assert harness.mde_pct_of_pre_period_mean == Decimal("2.5")
    assert harness.unit_exposed_min_ack_pct == Decimal("90")
    for value in (
        harness.binomial_level,
        harness.false_refusal_max_pct,
        harness.mde_pct_of_pre_period_mean,
    ):
        assert isinstance(value, Decimal)


def test_the_binomial_level_is_not_alpha(contracts: ContractSet) -> None:
    """Two numbers, two jobs — the one thing about this file that is easiest to get wrong.

    Alpha is what the system declares about itself. `binomial_level` is the level at which we
    test whether it kept that declaration. Setting them equal would be the estimator grading
    its own homework with the mark it awarded itself.
    """
    assert contracts.aa_harness.binomial_level != contracts.inference.alpha


def test_nothing_here_is_dressed_as_law() -> None:
    """Every source is a `scenario_assumption`, and that is the whole point of the split."""
    kinds = {entry["source"]["kind"] for entry in _sourced(DOCUMENT).values()}
    assert kinds == {"scenario_assumption"}, (
        f"{sorted(kinds)} — a budget cited as a legal instrument is the failure the "
        "legal_instrument / scenario_assumption split exists to make impossible"
    )


def test_every_value_carries_a_source_and_a_verification_date() -> None:
    entries = _sourced(DOCUMENT)
    assert len(entries) >= 12, "the walk found almost nothing, so it is proving almost nothing"
    for path, entry in entries.items():
        assert entry["source"].get("note"), f"{path} has a source with no argument in it"
        assert entry["source"].get("verified_on"), f"{path} has no verification date"


def test_a_value_without_a_source_is_a_build_failure(
    contracts_copy: Path,
    edit_contract: Callable[[Path, Callable[[Any], Any]], None],
) -> None:
    """The provenance walk descends this file too, and a bare number is refused."""

    def unsource(document: Any) -> Any:
        document["draws_i_liked"] = {"value": 7}
        return document

    edit_contract(contracts_copy / "design" / "aa_harness.yaml", unsource)
    with pytest.raises(ContractError) as raised:
        load(contracts_copy)
    rules = {v.rule for v in raised.value.violations}
    assert "value_without_source" in rules


def test_the_loader_names_this_file_so_it_cannot_go_missing_quietly(
    contracts_copy: Path,
) -> None:
    """`CLAIMED_FILES` is exhaustive on purpose: a contract nobody reads fails silently.

    Deleting it must be a build failure rather than a smaller `ContractSet`, because every
    other symptom of a missing contract is that a consumer simply stops seeing it.
    """
    (contracts_copy / "design" / "aa_harness.yaml").unlink()
    with pytest.raises(ContractError) as raised:
        load(contracts_copy)
    assert "missing_contract" in {v.rule for v in raised.value.violations}
