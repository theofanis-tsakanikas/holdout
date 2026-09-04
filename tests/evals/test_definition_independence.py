"""Claim 5's two Python mechanisms may not reach each other, and must not be one algorithm.

`evals/definition/aggregate_then_combine.py`, its sibling and `evals/definition/README.md` all
say this test enforces the independence on the import graph. **It did not exist when they said
so**, which is `CLAUDE.md`'s *prose that claims a check nobody wrote* — in the atom that restated
three deferrals about that defect, written by the session that quoted the rule. It is written here
rather than the sentences being softened, because the sentences are the ones worth keeping.

Two questions, and the second is the one a rename cannot pass. Whether the modules **can reach**
each other is read off the imports; whether they are **two algorithms** is read off the syntax
tree, because both modules describe the other in prose and a search for the word would find the
description rather than the code.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import ModuleType

from evals.definition import aggregate_then_combine, combine_then_aggregate

from evals import definition


def _tree(module: ModuleType) -> ast.Module:
    return ast.parse(Path(str(module.__file__)).read_text(encoding="utf-8"))


def _imports(module: ModuleType) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(_tree(module)):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_neither_implementation_can_reach_the_other() -> None:
    """The independence, as a property of the import graph rather than of anybody's care.

    Two functions that call the same third one are one function agreeing with itself. Neither
    module may import the other, and neither may import **any** module inside `evals.` — a
    shared helper there is exactly where a cancelling bug would live, and there is no helper
    either of them legitimately needs.
    """
    first, second = _imports(aggregate_then_combine), _imports(combine_then_aggregate)

    assert "evals.definition.combine_then_aggregate" not in first
    assert "evals.definition.aggregate_then_combine" not in second

    for name, imports in (("aggregate_then_combine", first), ("combine_then_aggregate", second)):
        inside = sorted(module for module in imports if module.startswith("evals"))
        assert not inside, (
            f"{name} imports {inside} — a module inside the eval is somewhere the two "
            "implementations can meet, and an agreement reached there is one implementation "
            "measured twice"
        )


def test_the_parent_package_is_documentation_and_cannot_be_the_meeting_point() -> None:
    """*Neither may their parents* is half the rule and the half nothing else would catch.

    `evals/definition/__init__.py` is imported by both by construction — it is the package. If it
    executed any arithmetic, or imported either sibling, both would inherit it and the import
    check above would still pass.
    """
    assert not _imports(definition), (
        f"the package __init__ imports {sorted(_imports(definition))}; it is prose and must "
        "stay prose, because it is the one module both implementations load whether they ask "
        "to or not"
    )
    body = [node for node in _tree(definition).body if not isinstance(node, ast.Expr)]
    assert not body, (
        "the package __init__ has statements beyond its docstring, so it is code both "
        "implementations run"
    )


def test_they_share_the_contract_and_nothing_else() -> None:
    """What they are *allowed* to share, stated as an assertion rather than left implicit.

    The claim is *sharing only the definition*. Both read `holdout.contracts.model` for the
    metric's grain and its rounding, and that is the definition. Neither may reach the
    **compilers**, which is where the third mechanism's SQL is rendered: a Python path importing
    the renderer would be agreeing with the artefact it is meant to be independent of.
    """
    for name, imports in (
        ("aggregate_then_combine", _imports(aggregate_then_combine)),
        ("combine_then_aggregate", _imports(combine_then_aggregate)),
    ):
        assert "holdout.contracts.model" in imports, (
            f"{name} stopped reading the contract, so it is no longer an implementation of it"
        )
        compilers = sorted(one for one in imports if one.startswith("holdout.contracts.compilers"))
        assert not compilers, (
            f"{name} imports {compilers} — that is where the SQL mechanism is rendered, and a "
            "Python path that reads it agrees with the third mechanism by construction"
        )


def _has(module: ModuleType, predicate: object) -> bool:
    return any(predicate(node) for node in ast.walk(_tree(module)))  # type: ignore[operator]


def test_the_two_orders_are_actually_two_orders() -> None:
    """A second implementation that aggregated the same way would be the first one, renamed.

    Read off the syntax tree, because the difference this pair rests on is **order of
    operations** and both modules explain it in a docstring. What is checked is the shape of the
    code:

    * the aggregate path keeps the contract's three terms in **separate** accumulators and unions
      their key sets, so a `set | set` appears in it;
    * the combine path keeps **one** accumulator of signed contributions, so a `-=` appears in it
      and no union does.

    Either module drifting toward the other's shape breaks this before the numbers ever move —
    which is the point, because two implementations that have converged still agree.

    **What it therefore does not cover, and the direction it is wrong in.** This reads shape, not
    meaning: rewriting `running[key] -= x` as `running[key] = running[key] - x` changes nothing
    and goes red anyway. That is the safe direction — it asks for a sentence in the diff rather
    than letting a convergence through — and it is stated rather than discovered.

    All four assertions in this file were **proved by planting**: a sibling import, a statement in
    the package `__init__`, an import of the compilers, and the rewrite above. Each plant asserts
    its own site is present before substituting, because a plant that matched nothing would have
    reported the test passing on an unmodified file.
    """
    union = lambda node: isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr)  # noqa: E731
    subtract_in_place = lambda node: (  # noqa: E731
        isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Sub)
    )

    assert _has(aggregate_then_combine, union), (
        "the aggregate path no longer unions its key sets, so it may have stopped carrying the "
        "contract's full outer join as three separate term accumulators"
    )
    assert not _has(aggregate_then_combine, subtract_in_place), (
        "the aggregate path subtracts in place, which is the sibling's shape: it is meant to sum "
        "each term whole and combine once at the end"
    )
    assert _has(combine_then_aggregate, subtract_in_place), (
        "the combine path no longer accumulates a signed contribution per row, so it may have "
        "converged on the sibling's order"
    )
    assert not _has(combine_then_aggregate, union), (
        "the combine path unions key sets, which is the sibling's way of reaching the full outer "
        "join: this one reaches it by a cell existing as soon as any row touches it"
    )
