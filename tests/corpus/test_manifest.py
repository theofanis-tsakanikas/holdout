"""The corpus is evidence, and evidence that can be edited without anything going red is not.

`corpus/real/MANIFEST.yaml` records a digest for every committed file, alongside the URL, the
licence and the date each was retrieved. This is what makes those records load-bearing rather
than decorative: change a price in the corpus and the build goes red, exactly as it does when
a generated contract artefact is hand-edited.

It is also the check that makes `evals/gate_proof/` mean something. Its engine argues that the
planter cannot tune the inputs to make a mutation catchable — and that argument is only true
while nobody can quietly add a row to the corpus.
"""

from __future__ import annotations

import hashlib
import statistics
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import yaml
from corpus.real import (
    items,
    margin_series,
    median_gross_margin_fraction,
    quotes,
    regulated_basket,
)

CORPUS = Path(__file__).resolve().parents[2] / "corpus" / "real"
MANIFEST = CORPUS / "MANIFEST.yaml"


@pytest.fixture(scope="module")
def manifest() -> dict[str, Any]:
    document: dict[str, Any] = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    return document


def _declared_files(manifest: dict[str, Any]) -> dict[str, str]:
    declared = {source["file"]: source["sha256"] for source in manifest["sources"]}
    declared.update({entry["file"]: entry["sha256"] for entry in manifest["ours"]})
    return declared


def test_every_committed_file_matches_its_declared_digest(manifest: dict[str, Any]) -> None:
    for relative, expected in _declared_files(manifest).items():
        actual = hashlib.sha256((CORPUS / relative).read_bytes()).hexdigest()
        assert actual == expected, (
            f"{relative} no longer hashes to what MANIFEST.yaml records. If the corpus was "
            "deliberately rebuilt, rerun corpus/real/fetch.py and update the digest and the "
            "row count together — the two are the whole of the provenance."
        )


def test_no_committed_data_file_is_undeclared(manifest: dict[str, Any]) -> None:
    """A file nobody declared is a source nobody cited."""
    on_disk = {f"data/{p.name}" for p in (CORPUS / "data").iterdir() if p.is_file()}
    assert on_disk == set(_declared_files(manifest)), (
        "corpus/real/data/ and MANIFEST.yaml disagree about which files exist"
    )


def test_every_source_carries_a_url_and_a_retrieval_date(manifest: dict[str, Any]) -> None:
    for source in manifest["sources"]:
        assert source.get("url", "").startswith("https://"), source["id"]
        assert source.get("retrieved_on"), source["id"]


def test_declared_row_counts_are_the_rows_that_are_there(manifest: dict[str, Any]) -> None:
    counted = {
        "data/ons-price-quotes-2025.csv.gz": sum(1 for _ in quotes()),
        "data/greek-regulated-basket-2026.csv": len(regulated_basket()),
        "data/eurostat-sbs-gross-margin-el.csv": len(margin_series()),
        "data/item_categories.csv": len(items()),
    }
    declared = {source["file"]: source["rows"] for source in manifest["sources"]}
    declared.update({entry["file"]: entry["rows"] for entry in manifest["ours"]})
    assert counted == declared


def test_the_greek_table_is_the_63_the_decision_states(manifest: dict[str, Any]) -> None:
    basket = regulated_basket()
    assert [c.ordinal for c in basket] == list(range(1, 64))
    assert all(c.category_el.strip() for c in basket)


def test_the_derived_margin_is_the_one_the_manifest_argues_for(manifest: dict[str, Any]) -> None:
    """The manifest states 0.1681 and the reader recomputes it. They must not drift apart.

    The manifest is where the derivation is *argued* — why a median rather than a mean, what
    the 2018 break is, which way the resulting cost errs. An argument about a number that is
    no longer the number is worse than no argument.
    """
    formula = manifest["derived"]["unit_cost"]["formula"]
    assert "m = 0.1681" in formula
    assert median_gross_margin_fraction() == Decimal("0.1681")
    published = [o.gross_margin_pct_of_turnover for o in margin_series()]
    assert statistics.median(published) / 100 == median_gross_margin_fraction()


def test_the_2018_break_is_still_in_the_file() -> None:
    """It is an outlier and it stays. Deleting it would make the median honest by accident."""
    by_year = {o.year: o.gross_margin_pct_of_turnover for o in margin_series()}
    assert by_year[2018] > Decimal(40), (
        "the 2018 observation is a break in the Eurostat series and MANIFEST.yaml explains "
        "that a median was chosen because of it. Removing the row would leave the "
        "explanation describing a decision nobody had to make."
    )


def test_every_item_in_the_data_is_mapped_and_every_mapping_is_used() -> None:
    """Both directions. An unmapped item is a silent gap; an unused mapping is silent drift."""
    mapped = set(items())
    present = {q.item_id for q in quotes()}
    assert mapped == present


def test_a_regulated_item_names_which_ordinal_of_the_decision_it_matched() -> None:
    ordinals = {c.ordinal for c in regulated_basket()}
    for item in items().values():
        if item.greek_basket_ordinal is None:
            assert item.match == "", item.item_id
            continue
        assert item.greek_basket_ordinal in ordinals, item.item_id
        assert item.match in {"exact", "equivalent"}, item.item_id
        assert item.note.strip(), f"{item.item_id} claims a match with no reasoning beside it"
