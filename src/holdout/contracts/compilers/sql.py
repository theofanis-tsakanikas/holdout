"""The shared SQL body for a metric, and the generated-file headers.

The dbt model and the SQL function are different mechanisms — one materialises a table
through `ref()`, the other returns rows from fully qualified names — but they must compute
the identical number, so they are rendered from the same parsed terms with a different
relation renderer. Two hand-written SQL bodies would be the second definition the contract
layer exists to prevent.
"""

from __future__ import annotations

from collections.abc import Callable

from holdout.contracts.expression import combine, parse
from holdout.contracts.model import Metric, MetricSource

DO_NOT_EDIT = "GENERATED FILE — DO NOT EDIT"

#: Every intermediate sum is exact decimal, never floating point. A float sum depends on the
#: order the rows arrived in, so two consumers of the same definition can differ in the last
#: cent for no reason anyone can find — and claim 5 compares as integers with no tolerance.
DECIMAL = "decimal(38, 6)"


def sql_header(*, source_path: str, generator: str) -> str:
    return (
        f"-- {DO_NOT_EDIT}\n"
        f"-- source:     {source_path}\n"
        f"-- generator:  {generator}\n"
        f"-- regenerate: make contracts\n"
        f"--\n"
        f"-- `make contracts` recompiles this file and fails the build if what is on disk\n"
        f"-- differs, so an edit here does not survive and does not go unnoticed either.\n"
    )


def qualified(source: MetricSource) -> str:
    return source.relation


def dbt_ref(source: MetricSource) -> str:
    return "{{ ref('" + source.relation_name + "') }}"


def version_parameter(relation: str) -> str:
    """The parameter name that pins one relation, derived from the relation itself.

    **One per relation, because a Delta version counter is per table.** The readout used to emit
    a single `:data_version` on every source and describe it as *"the Delta version every source
    is pinned to"* — a sentence that cannot be true of Delta: each table's counter starts at 0
    and advances on its own writes, so one integer indexes three unrelated points in history.

    Measured on a gold build, which is what found it: `gold.decision_economics` and `gold.waste`
    at version 0 while `gold.experiment_assignment` was at 1, and a readout pinned at 0 read the
    assignment table's **empty CREATE** and returned no rows at all. And it is structural rather
    than accidental — `gold.experiment_assignment` is written once before the period opens and
    never again, so it is by design the one relation that will not advance with the others.

    `docs/DECISIONS.md`'s *"The generated SQL has never been executed"* is what deferred this to
    the moment gold was built, and its ruling is what settles it: **if gold does not match, the
    contracts move.**
    """
    return "data_version_" + relation.replace(".", "_")


def no_version(_: MetricSource) -> str:
    """No time travel at all — the dbt model and the SQL function, which read the live table."""
    return ""


def pinned(source: MetricSource) -> str:
    """The relation's own `version as of`, with the parameter that names it."""
    return f" version as of :{version_parameter(source.relation)}"


def metric_body(
    metric: Metric,
    *,
    relation: Callable[[MetricSource], str],
    version_clause: Callable[[MetricSource], str] = no_version,
) -> str:
    """The full statement — `with <ctes> <select>` — that computes the metric at its grain."""
    ctes, select = metric_parts(metric, relation=relation, version_clause=version_clause)
    return "with " + ",\n\n".join(ctes) + "\n\n" + select


def metric_parts(
    metric: Metric,
    *,
    relation: Callable[[MetricSource], str],
    version_clause: Callable[[MetricSource], str] = no_version,
) -> tuple[list[str], str]:
    """The CTE definitions and the final SELECT, separately.

    Handed back separately so a consumer that has CTEs of its own — the readout, which also
    reads the assignment table — can put them all in one `with` clause instead of nesting a
    `with` inside a subquery. Nesting parses on some engines and not others, and a generated
    artefact that depends on which engine reads it is not one definition.

    Each source is aggregated to the grain in its own CTE and the aggregates are combined
    afterwards. Joining the relations row-first would fan out — three sale rows against two
    waste rows in one cell become six — and the metric would silently double-count.
    """
    terms = parse(metric.expression, tuple(s.alias for s in metric.sources))
    grain = list(metric.grain)
    ctes: list[str] = []

    for source in metric.sources:
        own = [t for t in terms if t.alias == source.alias]
        select_lines = [f"        {column}," for column in grain]
        select_lines += [
            f"        sum(cast({term.inner} as {DECIMAL})) as {term.column}," for term in own
        ]
        select_lines[-1] = select_lines[-1].rstrip(",")
        ctes.append(
            f"{source.alias} as (\n"
            "    select\n"
            + "\n".join(select_lines)
            + f"\n    from {relation(source)}{version_clause(source)}\n"
            + "    group by "
            + ", ".join(grain)
            + "\n"
            ")"
        )

    rounding = metric.rounding
    measure = f"{rounding.sql_function}({combine(terms)}, {rounding.decimals}) as metric_value"

    if len(metric.sources) == 1:
        alias = metric.sources[0].alias
        select = (
            "select\n"
            + "".join(f"    {alias}.{column},\n" for column in grain)
            + f"    '{metric.id}' as metric_id,\n"
            + f"    {metric.version} as metric_version,\n"
            + f"    {measure}\n"
            + f"from {alias}"
        )
        return ctes, select

    spine = "\n    union\n".join(
        f"    select {', '.join(grain)} from {s.alias}" for s in metric.sources
    )
    ctes.append("grain as (\n" + spine + "\n)")
    joins = "".join(
        f"\nleft join {s.alias} on " + " and ".join(f"{s.alias}.{c} = g.{c}" for c in grain)
        for s in metric.sources
    )
    select = (
        "select\n"
        + "".join(f"    g.{column},\n" for column in grain)
        + f"    '{metric.id}' as metric_id,\n"
        + f"    {metric.version} as metric_version,\n"
        + f"    {measure}\n"
        + "from grain g"
        + joins
    )
    return ctes, select
