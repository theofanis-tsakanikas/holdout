"""Rounding is a contract term, and claim 5 is an integer comparison.

Claim 5 is "one definition, three mechanisms, the same number, compared as integers, no
tolerance". A tolerance is where a disagreement hides, so there is none — which means the
contract has to fix not just the number of decimals but the mode, and every consumer has to
be emitted against both. `half_up` in SQL against Python's `Decimal` default of `half_even`
disagrees on exactly the values that sit on the boundary, which is a small enough fraction
of rows to survive a spot check and large enough to fail a strict comparison.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from holdout.contracts.model import ContractSet, Rounding

EUR = Rounding(mode="half_even", decimals=2)
COUNT = Rounding(mode="half_even", decimals=0)
EUR_HALF_UP = Rounding(mode="half_up", decimals=2)


@pytest.mark.parametrize(
    ("value", "expected"),
    [("1.005", 100), ("1.015", 102), ("1.025", 102), ("2.675", 268), ("-1.005", -100)],
)
def test_half_even_ties_go_to_the_even_neighbour(value: str, expected: int) -> None:
    assert EUR.canonical_integer(value) == expected


@pytest.mark.parametrize(("value", "expected"), [("1.005", 101), ("1.015", 102)])
def test_half_up_disagrees_with_half_even_on_the_boundary(value: str, expected: int) -> None:
    assert EUR_HALF_UP.canonical_integer(value) == expected


def test_the_two_modes_differ_by_one_cent_which_is_why_the_mode_is_in_the_contract() -> None:
    boundary = "1.005"
    assert EUR.canonical_integer(boundary) != EUR_HALF_UP.canonical_integer(boundary)
    assert abs(EUR.canonical_integer(boundary) - EUR_HALF_UP.canonical_integer(boundary)) == 1


def test_a_count_metric_rounds_to_a_different_integer_scale() -> None:
    assert COUNT.canonical_integer("2.5") == 2
    assert COUNT.canonical_integer("3.5") == 4
    assert COUNT.canonical_integer(Decimal("7")) == 7


def test_the_integer_is_the_value_at_the_contract_scale() -> None:
    assert EUR.canonical_integer("12.34") == 1234
    assert EUR.quantize("12.34") == Decimal("12.34")
    assert COUNT.canonical_integer("12") == 12


def test_sql_spelling_follows_the_mode() -> None:
    assert EUR.sql_function == "bround"
    assert EUR_HALF_UP.sql_function == "round"


def test_every_metric_in_the_contract_declares_a_mode_and_a_scale(
    contracts: ContractSet,
) -> None:
    for metric in contracts.metrics:
        assert metric.rounding.mode in {"half_even", "half_up"}
        assert 0 <= metric.rounding.decimals <= 6


def test_the_in_force_euro_metrics_round_half_even(contracts: ContractSet) -> None:
    """A euro metric that rounded half_up would fail claim 5 against the Python reference
    implementation, whose Decimal default is half_even. v3 of the margin metric exists for
    exactly that reason and carries the restatement that says so."""
    for metric in contracts.metrics:
        if metric.effective_to is None and metric.unit == "EUR":
            assert metric.rounding.mode == "half_even", metric.ref
