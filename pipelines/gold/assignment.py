"""`gold.experiment_assignment` — written before the period opens, and then refusing to move.

This is the table `CLAUDE.md`'s doctrine rule 7 is about, and the honest sentence about it is
narrower than the rule. **Today the guarantee is detection plus three of four storage refusals;
unopenability is phase 3.** `CLAUDE.md` says so itself, in the restatement `T008` added, and this
module does not widen it.

What refuses what, measured rather than described
-------------------------------------------------
Delta's `delta.appendOnly` is a **table property the storage layer enforces**, and it is in the
open-source engine rather than only in Databricks. Measured on delta-spark 4.4.0 / Spark 4.2.0
against a local table:

    update gold.experiment_assignment set arm = …   [DELTA_CANNOT_MODIFY_APPEND_ONLY]  refused
    delete from gold.experiment_assignment …        [DELTA_CANNOT_MODIFY_APPEND_ONLY]  refused
    insert overwrite gold.experiment_assignment …   [DELTA_CANNOT_MODIFY_APPEND_ONLY]  refused
    insert into gold.experiment_assignment …        allowed

**So three of the four ways to change a unit's arm are refused by the storage, and the fourth is
not.** An append can add a second row for a unit that already has one. Nothing in Delta stops it;
what stops it is `verify`, which re-reads the table and recomputes the digest over what it found.
A unit with two rows has a roster the committed digest does not describe.

And the limit under **that**: `SealedAssignment`, `CertifiedPrice` and `corpus/world/seal.py` all
declare the same one, and this table inherits it. **A forger who rewrites every row and the digest
together agrees with itself.** What is refused is every *uncoordinated* edit. The door that does
not open is `gold.experiment_assignment` under Unity Catalog grants, in phase 3, where the write
is refused by something that is not this repository.

Why the write is refused rather than the read
---------------------------------------------
*"Written before the period opens"* is a property of the moment, and a table cannot check it
afterwards. So `write` takes the declared `period_start` and refuses an assignment stamped at or
after it, by name. An assignment written on the second day of its own comparison window is
`EXCLUSIONS_DEFINED_POST_HOC` wearing different clothes: whatever produced it saw some of the
outcome before it drew.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from holdout.core.experiment.assignment import digest_for
from holdout.core.experiment.codes import Arm

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime

    from holdout.core.experiment.assignment import SealedAssignment
    from pyspark.sql import SparkSession

#: The table `generated/readout/*.sql` names. Not a preference: the compiled query reads
#: `gold.experiment_assignment` by hand, so a different name here makes the artefact unrunnable.
TABLE = "experiment_assignment"

#: Delta's own property, and the only storage-level refusal available locally.
APPEND_ONLY = "delta.appendOnly"


class AssignmentWriteError(RuntimeError):
    """The assignment may not be written: too late, or already there."""


class AssignmentTamperedError(RuntimeError):
    """What came back out of the table is not what the committed lottery drew."""


def _qualified(schema: str) -> str:
    return f"{schema}.{TABLE}"


def create(spark: SparkSession, *, schema: str) -> None:
    """Create the table if it is absent, append-only from its first version.

    **The property is set at creation and never afterwards.** Setting it on a populated table
    would leave the window between the two writable, and a guarantee with a window in it is a
    guarantee about the window.
    """
    spark.sql(f"create schema if not exists {schema}")
    spark.sql(
        f"create table if not exists {_qualified(schema)} ("
        "  experiment_id string,"
        "  store_id string,"
        "  arm string,"
        "  assigned_at timestamp,"
        "  seed string,"
        "  draw_index int,"
        "  form_digest string,"
        "  digest string"
        f") using delta tblproperties ({APPEND_ONLY} = true)"
    )


def write(
    spark: SparkSession,
    seal: SealedAssignment,
    *,
    schema: str,
    assigned_at: datetime,
    period_start: str,
) -> int:
    """Write one experiment's lottery, or refuse and say which rule refused.

    Two refusals, and they are different sentences:

    * **the period has opened** — `assigned_at` is at or after `period_start`, so whatever drew
      this could have seen part of the outcome first;
    * **the experiment already has an assignment** — the table is append-only, so a second write
      does not replace the first, it adds to it, and the roster the digest describes stops being
      the roster the table holds.
    """
    if str(period_start) <= _iso_week_of(assigned_at):
        raise AssignmentWriteError(
            f"{seal.experiment_id} would be assigned at {assigned_at.isoformat()}, which is in "
            f"or after its own comparison window opening at {period_start}. The assignment is "
            "written before the period opens or it is not written: a lottery drawn once the "
            "outcome has started arriving is a lottery whose drawer had something to look at."
        )
    create(spark, schema=schema)
    existing = spark.sql(
        f"select count(*) as n from {_qualified(schema)} where experiment_id = '{seal.experiment_id}'"  # noqa: E501
    ).collect()[0]["n"]
    if existing:
        raise AssignmentWriteError(
            f"{seal.experiment_id} already has {existing} assignment row(s). This table is "
            f"append-only ({APPEND_ONLY}), so a second write would not replace the first — it "
            "would leave the experiment with two lotteries and a digest that describes neither."
        )
    rows = [
        (
            seal.experiment_id,
            unit,
            seal.arms[unit].value,
            assigned_at,
            seal.seed,
            seal.draw_index,
            seal.form_digest,
            seal.digest,
        )
        for unit in seal.roster
    ]
    frame = spark.createDataFrame(
        rows,
        "experiment_id string, store_id string, arm string, assigned_at timestamp, "
        "seed string, draw_index int, form_digest string, digest string",
    )
    frame.write.format("delta").mode("append").saveAsTable(_qualified(schema))
    return len(rows)


def _iso_week_of(moment: datetime) -> str:
    """The ISO week the readout would window this moment into.

    The comparison window is declared in ISO weeks — `generated/readout/*.sql` filters on
    `iso_week` — so *"before the period opens"* is a comparison in the same units the period is
    declared in. Comparing a timestamp against a week string would be comparing two things that
    are not the same kind, which is how a bound stops meaning anything.
    """
    year, week, _ = moment.isocalendar()
    return f"{year:04d}-W{week:02d}"


def read_arms(spark: SparkSession, *, schema: str, experiment_id: str) -> dict[str, str]:
    """Every (store, arm) the table holds for one experiment, as it comes back out."""
    rows = spark.sql(
        f"select store_id, arm from {_qualified(schema)} where experiment_id = '{experiment_id}'"
    ).collect()
    return {row["store_id"]: row["arm"] for row in rows}


def verify(spark: SparkSession, seal: SealedAssignment, *, schema: str) -> None:
    """Read the table back and refuse if it no longer describes the committed lottery.

    **This is the half `delta.appendOnly` cannot do.** Storage refuses an update, a delete and an
    overwrite; it permits an append, and an appended row is how a unit acquires a second arm.
    So the arms are read back and the digest is recomputed over **what the table holds**, using
    the seal's own committed strata and form digest — the two things a table edit cannot reach.

    A digest recomputed over an edited roster does not match the recorded one, whichever
    direction the edit went: a unit added, a unit removed, or a unit's arm changed.
    """
    from_table = read_arms(spark, schema=schema, experiment_id=seal.experiment_id)
    arms: dict[str, Arm] = {unit: Arm(value) for unit, value in from_table.items()}
    recomputed = digest_for(
        experiment_id=seal.experiment_id,
        seed=seal.seed,
        form_digest=seal.form_digest,
        strata=seal.strata,
        arms=arms,
    )
    if recomputed != seal.digest:
        drawn = frozenset(seal.roster)
        held = frozenset(arms)
        raise AssignmentTamperedError(
            f"{seal.experiment_id}: the assignment table no longer describes the committed "
            f"lottery. digest {recomputed[:12]}… against {seal.digest[:12]}…; "
            f"{len(drawn - held)} unit(s) drawn and absent, {len(held - drawn)} present and "
            f"never drawn, "
            f"{sum(1 for u in drawn & held if arms[u] is not seal.arms[u])} holding another arm."
        )


def is_append_only(spark: SparkSession, *, schema: str) -> bool:
    """Whether the storage is the thing refusing, rather than a comment saying it would."""
    properties = spark.sql(f"show tblproperties {_qualified(schema)}").collect()
    return any(
        row["key"] == APPEND_ONLY and row["value"].lower() == "true" for row in properties
    )


def arms_of(seal: SealedAssignment) -> Mapping[str, Arm]:
    """The committed arms, for a caller that wants to compare without reaching into the seal."""
    return seal.arms
