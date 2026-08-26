"""The metric expression grammar.

The grammar exists so that a multi-relation metric can be aggregated to its grain without
fanning out. It is enforced at load time, so a metric whose expression cannot be compiled
is a build failure rather than a query that returns a plausible wrong number.
"""

from __future__ import annotations

import pytest

from holdout.contracts.expression import ExpressionError, combine, parse
from holdout.contracts.model import ContractSet


def test_a_two_relation_expression_assigns_each_term_to_one_relation() -> None:
    terms = parse(
        "sum(s.qty * s.price_paid) - sum(s.qty * s.unit_cost_as_of) - sum(w.qty * w.cost)",
        ("s", "w"),
    )
    assert [t.alias for t in terms] == ["s", "s", "w"]
    assert [t.sign for t in terms] == ["+", "-", "-"]
    assert terms[0].inner == "qty * price_paid"


def test_the_combination_treats_a_missing_relation_as_zero_not_null() -> None:
    """A week with sales and no waste is a real cell, not a null one."""
    terms = parse("sum(s.qty) - sum(w.qty)", ("s", "w"))
    assert combine(terms) == "coalesce(s.term_0, 0) - coalesce(w.term_1, 0)"


def test_a_term_straddling_two_relations_is_refused() -> None:
    with pytest.raises(ExpressionError, match="straddles aliases"):
        parse("sum(s.qty * w.unit_cost)", ("s", "w"))


def test_a_bare_column_is_refused() -> None:
    with pytest.raises(ExpressionError, match="must be a single sum"):
        parse("s.qty - sum(w.qty)", ("s", "w"))


def test_an_unqualified_column_is_refused() -> None:
    with pytest.raises(ExpressionError, match="references no source alias"):
        parse("sum(qty)", ("s",))


def test_an_undeclared_alias_is_refused() -> None:
    with pytest.raises(ExpressionError, match="not declared in `sources`"):
        parse("sum(x.qty)", ("s",))


def test_a_declared_relation_the_expression_never_reads_is_refused() -> None:
    with pytest.raises(ExpressionError, match="never uses"):
        parse("sum(s.qty)", ("s", "w"))


def test_every_metric_in_the_contract_parses(contracts: ContractSet) -> None:
    for metric in contracts.metrics:
        terms = parse(metric.expression, tuple(s.alias for s in metric.sources))
        assert terms
