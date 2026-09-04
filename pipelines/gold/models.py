"""Running dbt in this process, against the session this repository already started.

**In-process, not as a subprocess, and the reason is the session.** `method: session` drives
`SparkSession.builder.getOrCreate()`, which returns the *active* session — so dbt inherits the
one `pipelines/gold/session.py` built, with Delta's extension and catalog configured and its
warehouse under a caller-chosen root. A subprocess would build its own with none of that, and
`version as of` on the tables it wrote would fail.

Verified rather than assumed: the application id is identical before dbt runs and after it
finishes, and `select ... version as of 0` answers on a table dbt created.

What dbt is running
-------------------
Five models. Two are `pipelines/gold/dbt/models/` — the family A shaping, downstream of the
as-of join. Three are `generated/dbt/models/metrics/`, compiled from `contracts/metrics/*.yaml`
and reached through `model-paths` rather than copied, so **`make contracts`' byte comparison is
the only definition check this layer needs**: there is no second copy that could differ from it.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from pyspark.sql import SparkSession

#: The dbt project, beside this module. `dbt_project.yml`'s `model-paths` reaches out of it to
#: `generated/dbt/models`, which is the whole arrangement.
PROJECT = Path(__file__).resolve().parent / "dbt"

#: Every model the project builds, in dependency order. **Declared so a run that built fewer can
#: be refused**: `dbt run` exits 0 having built nothing at all if `model-paths` stops resolving,
#: and a green run over an empty selection is the vacuous pass this repository files against
#: itself most often. `build` compares this against what the run reported.
EXPECTED_MODELS: tuple[str, ...] = (
    "decision_economics",
    "waste",
    "category_margin_per_store_week_v3",
    "units_sold_per_store_week_v1",
    "waste_value_per_store_week_v1",
)


class DbtRunError(RuntimeError):
    """dbt reported a failure, or reported success over fewer models than the project has."""


def missing(built: Sequence[str]) -> list[str]:
    """Which declared models a run did not build. A pure function so it can be tested cheaply.

    Separated from `run` because the interesting case — dbt succeeding over a **short** model
    list — costs a full build to reach through `run` and costs nothing to reach here. A check
    that is only exercised by the expensive path is a check nobody exercises.
    """
    return [name for name in EXPECTED_MODELS if name not in set(built)]


def run(
    spark: SparkSession, *, target_root: Path, select: Sequence[str] | None = None
) -> tuple[str, ...]:
    """Build every model and return their names, or raise naming what went wrong.

    `spark` is taken as an argument and never used: it is here because **dbt reaching the right
    session is a precondition, not a coincidence**, and a signature that did not mention it would
    let a caller invoke this with no session active and get one dbt built for itself. The
    argument is the requirement, written down.
    """
    from dbt.cli.main import dbtRunner

    assert spark is not None
    invocation = dbtRunner().invoke(
        [
            "run",
            *(["--select", *select] if select else []),
            "--project-dir",
            str(PROJECT),
            "--profiles-dir",
            str(PROJECT),
            "--target-path",
            str(target_root / "dbt-target"),
            # **Both of dbt's output directories are caller-chosen**, for the reason
            # `pipelines/gold/session.py` gives about Spark's: left to their defaults they are
            # created *inside the project*, which here is a tracked package. `logs/` and
            # `target/` under `pipelines/gold/dbt/` are a build writing into the tree it is
            # built from.
            "--log-path",
            str(target_root / "dbt-logs"),
        ]
    )
    if not invocation.success:
        raise DbtRunError(f"dbt run failed: {invocation.exception or invocation.result}")

    # `invocation.result` is dbt's own `RunExecutionResult` for a `run`, and its type is a
    # union across every command the runner accepts — hence the cast rather than an assertion
    # about a library's internals. What is *not* trusted is its content: `missing` below is
    # what turns a short list into a refusal.
    built = tuple(str(result.node.name) for result in cast("Iterable[Any]", invocation.result))
    # **A selected run is not checked for completeness**, because it deliberately built fewer.
    # The check below exists so a run that resolved *nothing* cannot report success; a caller
    # naming its models has already said which it wants, and `claim-5`'s eval is the one caller
    # that does — it rebuilds only the metric models after appending a constructed cell, and a
    # full run would rebuild `decision_economics` from `priced_sales` and throw that cell away.
    if select:
        if not built:
            raise DbtRunError(
                f"dbt reported success having built nothing from --select {list(select)}. A "
                "selection that matches no model exits 0, which is the same silence as a run "
                "that resolved none."
            )
        return built

    absent = missing(built)
    if absent:
        raise DbtRunError(
            f"dbt reported success having built {list(built)}, which is missing {absent}. "
            "A run that resolves no models exits 0, so success alone says nothing about "
            "whether the generated metric models were found — `model-paths` reaching "
            "`generated/dbt/models` is what puts them in the project, and this is where that "
            "stops being assumed."
        )
    return built
