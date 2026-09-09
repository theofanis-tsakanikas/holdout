"""The two experiments run end to end and `gold.readout` comes out with one of each.

**This is the acceptance `ops/run_assertions.py` performs on the estate, performed on a laptop.**
`PLAN.md` closes phase 3 on *at least one experiment producing a number and at least one refusing
for the right reason*, and until this branch the table that assertion queries — `gold.readout` —
was written by nothing at all. So the gate is the same shape as the acceptance: a run in which
everything succeeded has not demonstrated the thing this project is about, and neither has one in
which everything refused.

**It runs the whole path.** Corpus, ERP export, bulk load, silver, the priced tables, the five
dbt models, both design assessments, the assignment write, and both readouts. What it costs is
what `make gold` already costs plus the readouts, and the reason it is worth that is the reason
the finding existed: every piece passed its own test and nothing had ever joined them up.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pyspark.sql import SparkSession

pytestmark = pytest.mark.gold

SEED = "experiments"
DAY = "2025-09-02"
#: **`estate`, and the scale is the assertion.** `corpus/world/scale.py` declares it as the world
#: claim 2's harness is sized on plus the one week `run` drives, and this file builds the estate
#: the way `backfill` does — so running it on anything else would be testing a different world
#: from the one the workflow loads.
#:
#: **It was `harness`, and `pipelines/window.py` refused it the day the live week was reserved**:
#: *a world of 112 days cannot carry 8 weeks of pre-period and 8 weeks of comparison window.*
#: That is the guard working, on the test, before the estate paid for it — which is the whole
#: reason the window's arithmetic lives in one module instead of in each caller.
SCALE = "estate"


@pytest.fixture(scope="module")
def spark(tmp_path_factory: pytest.TempPathFactory) -> Iterator[SparkSession]:
    """One session for the file, for `tests/pipelines/test_gold.py`'s reason."""
    from pipelines.gold import session

    with session.sessions(tmp_path_factory.mktemp("warehouse")) as spark:
        yield spark


@pytest.fixture(scope="module")
def built(spark: SparkSession, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The estate as `backfill` leaves it: a baseline, a sealed lottery, and a window under it.

    **Two generations, and the order is the experiment.** The baseline is `all_control` — nothing
    applied to anybody — which is what makes the pre-period covariates a measurement of the
    estate rather than of the treatment. `design` then draws the lottery against those covariates
    and writes it. Only then is the comparison window generated, under the arms that were
    committed. A single generation would carry `alternating` arms, which `corpus/world/` calls
    *a convenience and not a lottery*, and a readout over those is an uplift stated without a
    valid holdout.
    """
    from datetime import date

    from corpus.world import prepare
    from corpus.world.assignment import Arm, all_control
    from pipelines.gold import assignment as assignment_table
    from pipelines.gold import experiments
    from pipelines.gold.build import build as build_gold
    from pipelines.ingest import bulk, erp
    from pipelines.silver.build import build as build_silver

    from pipelines import window as window_module

    root = tmp_path_factory.mktemp("estate")
    baseline_opens, baseline_closes = window_module.baseline(SCALE)
    window_opens, window_closes = window_module.window(SCALE)

    chain = prepare("W6", seed=SEED, scale=SCALE)
    control = prepare("W6", seed=SEED, scale=SCALE, assignment=all_control(chain.chain))
    erp.export(control, root / "landing", day=date.fromisoformat(DAY))
    erp.history(control, root / "landing", since=baseline_opens, until=baseline_closes)

    def rebuild(arrived_at: datetime) -> None:
        bulk.load(root / "landing", root / "bronze", arrived_at=arrived_at)
        build_silver(spark, root / "bronze", root / "silver")
        build_gold(spark, root / "silver", root=root / "gold")

    rebuild(datetime(2026, 9, 3, 9, 0))  # noqa: DTZ001 — the corpus is naive on purpose
    experiments.design(spark, scale=SCALE)

    committed = assignment_table.read_rows(spark, schema="gold", experiment_id="fresh-ladder")
    assert committed, "design wrote no assignment, so the window has no arms to run under"
    # A store the design excluded is simulated under control: it is not in the experiment, and
    # the only honest arm for a shop nobody randomised is the one where nothing was applied.
    # `pipelines/ingest/bulk.py::_arms` makes the same choice for the estate.
    arms = {store.store_id: Arm.CONTROL for store in chain.chain.stores}
    arms.update({store: Arm(arm) for store, arm in committed})
    treated = prepare("W6", seed=SEED, scale=SCALE, assignment=arms)
    erp.history(treated, root / "landing", since=window_opens, until=window_closes, into="window")
    rebuild(datetime(2026, 9, 4, 9, 0))  # noqa: DTZ001 — the corpus is naive on purpose
    return root


@pytest.fixture(scope="module")
def rows(spark: SparkSession, built: Path) -> list[dict[str, object]]:
    """Both readouts, computed once.

    Each `readout` runs the permutation reference set the contract declares — B = 1000 draws over
    the roster — and three tests asking the same question three times is three times the cost for
    one answer. Measured on this laptop: the readout is the expensive half of this file.
    """
    from pipelines.gold import experiments

    return experiments.readout(spark, scale=SCALE)


def test_the_run_produces_a_number_and_a_refusal(rows: list[dict[str, object]]) -> None:
    from pipelines.gold import experiments

    assert len(rows) == len(experiments.DECLARED), (
        f"{len(experiments.DECLARED)} experiments were declared and {len(rows)} rows came back. "
        "Nothing is retried and no experiment is dropped: a run that quietly lost one would be "
        "the fishing this repository exists to make impossible."
    )

    numbers = [row for row in rows if row["uplift"] is not None]
    refusals = [row for row in rows if row["reason_code"] is not None]
    assert numbers, (
        "no experiment produced a number. A system that only ever refuses passes every world "
        f"and is worthless. What came back: {[(r['experiment_id'], r['reason_codes']) for r in rows]}"
    )
    assert refusals, (
        "no experiment refused. A run in which everything succeeded has not demonstrated the "
        "thing this project is about."
    )
    for row in rows:
        assert (row["uplift"] is None) != (row["reason_code"] is None), (
            f"{row['experiment_id']} carries both a number and a reason code, or neither. "
            "Exactly one of them is the row's answer."
        )


def test_the_peeking_design_is_refused_by_name(rows: list[dict[str, object]]) -> None:
    """The refusal is structural, so it is asserted by code rather than by count."""
    peeking = {row["experiment_id"]: row for row in rows}["fresh-ladder-peeking"]
    assert peeking["reason_code"] == "STOPPING_RULE_PERMITS_PEEKING", (
        f"the peeking design was answered with {peeking['reason_code']!r}. It declares a "
        "group-sequential rule with no spending function, which `feasibility.py` refuses over "
        "the structural value rather than over the prose — a different code here means the "
        "refusal this run demonstrates is an accident of the data."
    )
    assert peeking["moment"] == "design", (
        "the peeking design was refused at readout rather than at design. A design that may not "
        "exist must not reach a lottery, and this row says one did."
    )


def test_the_readout_table_is_written_in_the_shape_the_acceptance_reads(
    spark: SparkSession, rows: list[dict[str, object]]
) -> None:
    from pipelines.gold import experiments

    written = experiments.write(spark, rows, schema="gold")
    assert written == len(experiments.DECLARED)

    stored = spark.sql("select experiment_id, uplift, reason_code from gold.readout").collect()
    assert len(stored) == written, "gold.readout holds a different number of rows than were written"
    assert any(row["uplift"] is not None for row in stored)
    assert any(row["reason_code"] is not None for row in stored)


def test_the_window_agrees_with_the_harness() -> None:
    """Two hand-kept declarations of one window, compared rather than trusted."""
    from evals.uplift import design as harness_design
    from pipelines.gold import experiments

    from pipelines import window as window_module

    assert window_module.PERIOD_WEEKS == harness_design.PERIOD_WEEKS
    assert window_module.PRE_PERIOD_WEEKS == harness_design.PRE_PERIOD_WEEKS
    assert experiments.SIZE_INDEX_TO_SQM == harness_design.SIZE_INDEX_TO_SQM
    assert experiments.WASTE_RATE_SCALE == harness_design.WASTE_RATE_SCALE
