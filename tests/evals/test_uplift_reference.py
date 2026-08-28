"""Two implementations of one metric, and the ways they are kept from being one.

`evals/uplift/outcomes.py` groups the stream to the metric's grain the way a `GROUP BY`
does. `evals/uplift/reference.py` walks every event in order, holds a running ledger, works
in `Decimal` euros rather than integer cents, and resolves the as-of cost by reading the
ledger forward instead of bisecting an index. They agree **as integers, with no tolerance**.

The value of that is entirely in the *independence*, so the independence is what is tested
hardest: a shared helper would make a bug in it cancel out of every comparison, and the
comparison would keep passing while both were wrong. So one test compares the numbers and
another reads the two modules' imports.

**What this does not prove**, and the eval prints it on every run: two Python implementations
are not the three genuinely different mechanisms claim 5 needs. The dbt model and the SQL
function are T011 and T012.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import ModuleType

import pytest
from corpus.world import prepare
from corpus.world.scale import SMOKE
from evals.uplift import outcomes, reference

from holdout.contracts.model import ContractSet, Metric

SEED = "reference"
WORLDS = ("W1", "W2", "W5", "W6")


@pytest.fixture(scope="module")
def metric(contracts: ContractSet) -> Metric:
    return contracts.metric_versions("category_margin_per_store_week")[-1]


@pytest.mark.parametrize("world_id", WORLDS)
def test_the_two_implementations_agree_as_integers(world_id: str, metric: Metric) -> None:
    """Per grain cell, exactly. Not close: equal.

    W5 is in the list on purpose — its heavy-tailed baskets produce the largest line
    quantities in the corpus, which is where a `Decimal` in euros and a sum of integer cents
    have the most room to come apart.
    """
    run = prepare(world_id, seed=SEED, scale=SMOKE)
    grouped = outcomes.cell_margins(outcomes.collect(run), metric.rounding)
    walked = reference.compute(run, metric=metric)
    assert grouped.keys() == walked.keys(), (
        f"{world_id}: the two implementations disagree about which cells exist at all"
    )
    disagreeing = {cell for cell, value in grouped.items() if walked[cell] != value}
    assert not disagreeing, (
        f"{world_id}: {len(disagreeing)} of {len(grouped)} cells differ by at least a cent — "
        f"{sorted(disagreeing)[:3]}. That is the failure v3 of the metric contract exists to "
        "have made impossible, and claim 5 compares with no tolerance"
    )


def test_they_agree_on_the_window_mean_too(metric: Metric) -> None:
    """The one division either path takes, and therefore the one place rounding decides a cent.

    Every term of the metric is an exact integer number of cents, so `half_even` and `half_up`
    cannot differ on a cell. They differ on a mean over an even number of weeks — which is
    what the harness's unit outcome is, and why this comparison is not the one above repeated.
    """
    run = prepare("W6", seed=SEED, scale=SMOKE)
    ledger = outcomes.collect(run)
    weeks, units = ledger.weeks, ledger.units
    grouped = outcomes.window_mean(
        outcomes.unit_weeks(ledger, metric.rounding),
        units=units,
        weeks=weeks,
        rounding=metric.rounding,
    )
    walked = reference.window_mean(
        reference.by_unit_week(reference.compute(run, metric=metric)),
        units=units,
        weeks=weeks,
        metric=metric,
    )
    assert grouped == walked


def _source(module: ModuleType) -> str:
    return Path(str(module.__file__)).read_text(encoding="utf-8")


def _imports(module: ModuleType) -> set[str]:
    source = _source(module)
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_neither_implementation_can_reach_the_other() -> None:
    """The independence, as a property of the import graph rather than of anybody's care.

    An agreement between two functions that call the same third one is one function agreeing
    with itself, which is the trap CLAUDE.md names for claim 1 and which applies here word for
    word. Neither module may import the other, and neither may import a shared helper that
    computes any part of the metric.
    """
    assert "evals.uplift.reference" not in _imports(outcomes)
    assert "evals.uplift.outcomes" not in _imports(reference)
    shared = _imports(outcomes) & _imports(reference)
    assert not any(name.startswith("evals.") for name in shared), (
        f"both implementations import {sorted(n for n in shared if n.startswith('evals.'))} — "
        "a shared module inside the eval is where a cancelling bug would live"
    )


def _attributes(module: ModuleType) -> set[str]:
    return {
        node.attr
        for node in ast.walk(ast.parse(_source(module)))
        if isinstance(node, ast.Attribute)
    }


def test_the_slow_one_is_actually_the_other_algorithm() -> None:
    """A second implementation that bisected the same index would be the first one, renamed.

    Read off the **syntax tree** rather than off the text, because both modules describe each
    other in prose and a search for the word would find the description. What is checked is
    what the code does: the grouped path imports `bisect`, the reference path does not, and
    neither reaches for `Chain.cost_as_of` — the corpus's own accessor, which either could
    have called and which would have made the comparison two callers of one function.
    """
    assert "bisect" in _imports(outcomes), (
        "the grouped path stopped indexing, so the two implementations may have converged on "
        "one algorithm and the comparison stopped being between two of them"
    )
    assert "bisect" not in _imports(reference), (
        "the reference path bisects an index. A second implementation that answers the as-of "
        "question the same way as the first is the first one, renamed"
    )
    for module in (outcomes, reference):
        assert "cost_as_of" not in _attributes(module), (
            f"{module.__name__} reaches for the corpus's own as-of accessor. Both read the "
            "ledger as data and each does its own arithmetic with it; sharing the lookup is "
            "where a cancelling bug would live"
        )
