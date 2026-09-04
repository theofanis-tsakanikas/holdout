"""The checks claim 5 rests on. Three mechanisms, one contract, integers with no tolerance.

Read `evals/definition/__init__.py` first: it carries why the three *named* consumers are one
mechanism, why the agent tool definition cannot be one at all, and which of the three here is
load-bearing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from evals.definition import aggregate_then_combine, combine_then_aggregate
from evals.report import Check, Report

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from holdout.contracts.model import Metric

#: The metric claim 5 is proved on. The primary metric of the experiments this project defends,
#: and the only one whose contract exercises **two** sources and therefore the full-outer join
#: where a one-sided cell can be lost. A single-source metric would agree trivially.
METRIC_ID = "category_margin_per_store_week"


def _disagreements(
    left: Mapping[tuple[str, ...], int],
    right: Mapping[tuple[str, ...], int],
    limit: int = 5,
) -> list[str]:
    """Every cell the two do not agree on, including cells one has and the other does not.

    **A missing cell is a disagreement, not an absence.** Comparing only the intersection would
    let a mechanism that lost a store-week pass, and losing a one-sided cell is one of the three
    failures this pair exists to separate.
    """
    found: list[str] = []
    for cell in sorted(set(left) | set(right)):
        a, b = left.get(cell), right.get(cell)
        if a != b:
            found.append(f"{'/'.join(cell)}: {a} vs {b}")
        if len(found) >= limit:
            break
    return found


def compare(
    sql: Mapping[tuple[str, ...], int],
    economics: Sequence[Mapping[str, Any]],
    waste: Sequence[Mapping[str, Any]],
    metric: Metric,
) -> tuple[Check, ...]:
    """The three pairwise comparisons, as integers, with no tolerance anywhere.

    Three checks rather than one, because *which two disagree* is the whole diagnostic value: a
    Python pair that agrees with each other and not with the SQL is a shared misconception, and a
    Python path that disagrees with both is an arithmetic slip in that path.
    """
    first = aggregate_then_combine.cells(economics, waste, metric)
    second = combine_then_aggregate.per_cell(economics, waste, metric)

    pairs = (
        ("D1", "the compiled SQL and the aggregate-then-combine path", sql, first),
        ("D2", "the compiled SQL and the combine-then-aggregate path", sql, second),
        ("D3", "the two Python paths", first, second),
    )
    checks: list[Check] = []
    for identifier, subject, left, right in pairs:
        broken = _disagreements(left, right)
        checks.append(
            Check(
                id=f"{identifier}.integer-equal",
                question=(
                    f"over every cell the corpus produced and the one the eval constructed, "
                    f"do {subject} produce the same integer, with no tolerance?"
                ),
                passed=not broken,
                figure=f"{len(set(left) | set(right))} cell(s), {len(broken)} disagreeing",
                detail=("" if not broken else "cell: left vs right — " + " · ".join(broken)),
            )
        )
    return tuple(checks)


def tool_definition_agrees(metric: Metric, compiled: Mapping[str, Any]) -> Check:
    """`D4` — the one thing the agent's tool definition can be held to.

    **It computes nothing**, so it has no number to compare and cannot be one of the three
    mechanisms. What it can be wrong about is the contract's own terms, and a tool that declared
    a different rounding or a different grain would have the agent asking for a metric this
    repository does not define — which is a real failure with no arithmetic in it.
    """
    declared = compiled.get("metric", {})
    rounding = declared.get("rounding", {})
    mismatches = [
        f"{name}: {found!r} against the contract's {expected!r}"
        for name, found, expected in (
            ("id", declared.get("id"), metric.id),
            ("version", declared.get("version"), metric.version),
            ("grain", list(declared.get("grain", [])), list(metric.grain)),
            ("unit", declared.get("unit"), metric.unit),
            ("rounding.mode", rounding.get("mode"), metric.rounding.mode),
            ("rounding.decimals", rounding.get("decimals"), metric.rounding.decimals),
            (
                "canonical_integer_scale",
                declared.get("canonical_integer_scale"),
                10**metric.rounding.decimals,
            ),
        )
        if found != expected
    ]
    return Check(
        id="D4.tool-definition-matches-the-contract",
        question=(
            "Does the agent's tool definition declare the contract's own id, version, grain, "
            "unit, rounding and canonical scale?"
        ),
        passed=not mismatches,
        figure=f"7 term(s) compared, {len(mismatches)} disagreeing",
        detail=" · ".join(mismatches),
    )


def report(
    sql: Mapping[tuple[str, ...], int],
    economics: Sequence[Mapping[str, Any]],
    waste: Sequence[Mapping[str, Any]],
    metric: Metric,
    compiled_tool: Mapping[str, Any],
    unpriced: int,
    priced: int,
) -> Report:
    """Everything claim 5 has to say, with the pipeline's drop published beside it."""
    checks = (
        *compare(sql, economics, waste, metric),
        tool_definition_agrees(metric, compiled_tool),
    )
    return Report(
        claim=5,
        title="No uplift without one definition — three mechanisms, the same integer",
        checks=checks,
        numbers=(
            ("metric", metric.ref),
            ("rows compared", f"{len(economics):,} economics · {len(waste):,} waste"),
            ("cells", f"{len(sql):,} — {len(sql) - 1:,} from the corpus, 1 constructed"),
            (
                "the constructed cell",
                "exact 0.1250, where half_even gives 0.12 and half_up 0.13 — the corpus has no "
                "sub-cent content, so nothing in it can exercise the contract's rounding",
            ),
            (
                "sales with no published cost",
                f"{unpriced:,} of {priced:,} — dropped upstream by the pipeline, not by any "
                "mechanism here",
            ),
        ),
        notes=(
            "The three consumers CLAUDE.md names — dbt model, SQL function, readout — are ONE "
            "mechanism: all three are rendered by `metric_parts` and their arithmetic is "
            "byte-identical. Comparing them to each other proves Spark is deterministic.",
            "The agent's tool definition computes nothing and is not one of the three. D4 holds "
            "it to the contract's terms, which is not an arithmetic claim.",
            "Non-sharing prevents shared code, not a shared misconception. The two Python paths "
            "were written together and could misread the contract the same way; the SQL is the "
            "load-bearing third because it was compiled by a different mechanism at a different "
            "time.",
            "The drop above is the pipeline's, measured and published rather than folded into "
            "the comparison: all three mechanisms read the rows gold materialised.",
            "One cell of the ones compared was written by this eval, because the corpus cannot "
            "exercise the contract's `rounding` at all: every corpus cell is an exact number of "
            "cents, so bround(x, 2) is the identity and half_even and half_up never differ. That "
            "is a fact about the contract and the corpus, filed against them; a constructed cell "
            "proves three mechanisms round alike on a value the corpus never produces, and does "
            "NOT prove the corpus should produce one.",
        ),
    )
