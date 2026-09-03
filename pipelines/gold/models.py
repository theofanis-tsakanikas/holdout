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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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


def run(spark: SparkSession, *, target_root: Path) -> tuple[str, ...]:
    """Build every model and return their names, or raise naming what went wrong.

    `spark` is taken as an argument and never used: it is here because **dbt reaching the right
    session is a precondition, not a coincidence**, and a signature that did not mention it would
    let a caller invoke this with no session active and get one dbt built for itself. The
    argument is the requirement, written down.
    """
    from dbt.cli.main import dbtRunner

    assert spark is not None  # noqa: S101 — the precondition above, not a test assertion
    invocation = dbtRunner().invoke(
        [
            "run",
            "--project-dir",
            str(PROJECT),
            "--profiles-dir",
            str(PROJECT),
            "--target-path",
            str(target_root / "dbt-target"),
        ]
    )
    if not invocation.success:
        raise DbtRunError(f"dbt run failed: {invocation.exception or invocation.result}")

    built = tuple(
        result.node.name
        for result in invocation.result  # type: ignore[union-attr]
    )
    missing = [name for name in EXPECTED_MODELS if name not in built]
    if missing:
        raise DbtRunError(
            f"dbt reported success having built {list(built)}, which is missing {missing}. "
            "A run that resolves no models exits 0, so success alone says nothing about "
            "whether the generated metric models were found — `model-paths` reaching "
            "`generated/dbt/models` is what puts them in the project, and this is where that "
            "stops being assumed."
        )
    return built
