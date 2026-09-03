"""An expectation, and where a row goes when it fails one: quarantine, never the floor.

`CLAUDE.md`: *"**Quarantine, not drop.** The size of the quarantine table is a health metric."*
A dropped row is a row nobody can count, and a silver layer that dropped its bad rows would
report a clean pipeline by construction — which is the shape of every gate this repository
refuses.

**This is hand-written because the framework that runs locally has no expectations.** See
`pipelines/silver/__init__.py`: the measurement is there and so is the reason it is not a design
choice being dressed up.

What an expectation is here
---------------------------
A name, a condition that must hold, and a note saying what a violation means. The condition is a
Spark `Column` rather than a string, so it is checked by the engine that will run it rather than
by a parser written here — and a condition that is `NULL` for a row **fails**, because
`col > 0` is null when the column is null and a row with a missing value is exactly the row this
mechanism exists to catch.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pyspark.sql import functions as sf

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyspark.sql import Column, DataFrame

#: The columns every quarantined row carries, whatever table it came from. A quarantine that
#: kept only the row would be a pile nobody could act on: the table says where to look, the
#: expectation says which rule, and the key says which record.
QUARANTINE_COLUMNS: tuple[str, ...] = ("source_table", "expectation", "note", "business_key")


@dataclass(frozen=True, slots=True)
class Expectation:
    """One rule a row must satisfy to enter a silver table."""

    name: str
    condition: Column
    note: str


def apply(
    frame: DataFrame,
    expectations: Sequence[Expectation],
    *,
    table: str,
    business_key: Sequence[str],
) -> tuple[DataFrame, DataFrame]:
    """Split a frame into what passes every expectation and what failed one.

    Returns `(kept, quarantined)`. **A row fails on the first expectation it violates**, so a
    row breaking two rules appears once with the earlier rule's name rather than twice — the
    quarantine counts rows, not violations, and a row counted twice would inflate the health
    metric `CLAUDE.md` says to watch.

    **A null condition is a failure.** In Spark `col > 0` is `NULL` where `col` is null, and
    `filter` drops nulls, so the naive `frame.filter(condition)` would silently lose exactly the
    rows this exists to keep. Every condition is therefore evaluated through `coalesce(..., false)`.
    """
    if not expectations:
        raise ValueError(
            f"{table} declares no expectations, so its quarantine could never be non-empty and "
            "the rule would be enforced by nothing. Declare one or route the table directly."
        )
    key = sf.concat_ws("|", *[sf.col(name).cast("string") for name in business_key])
    failure_name = sf.lit(None).cast("string")
    failure_note = sf.lit(None).cast("string")
    for expectation in reversed(expectations):
        holds = sf.coalesce(expectation.condition, sf.lit(False))
        failure_name = sf.when(holds, failure_name).otherwise(sf.lit(expectation.name))
        failure_note = sf.when(holds, failure_note).otherwise(sf.lit(expectation.note))
    marked = frame.withColumn("_expectation", failure_name).withColumn("_note", failure_note)
    kept = marked.filter(sf.col("_expectation").isNull()).drop("_expectation", "_note")
    quarantined = (
        marked.filter(sf.col("_expectation").isNotNull())
        .withColumn("source_table", sf.lit(table))
        .withColumn("business_key", key)
        .withColumnRenamed("_expectation", "expectation")
        .withColumnRenamed("_note", "note")
        .select(*QUARANTINE_COLUMNS)
    )
    return kept, quarantined
