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
    # **The ERP exports on every day of the baseline, which is what the estate now exports.**
    #
    # It was `DAY` — the second day of the world — and then the last day inside the baseline,
    # and both were wrong in opposite directions, which the paragraph that stood here read
    # backwards. A drop two days in carries no later cost step, so every sale is priced at a
    # stale cost and the variance is too small. A drop on the last day carries every step and
    # silver knows all of them on that day, so every earlier sale has no cost at all, is
    # dropped, and the variance is the variance of seven empty weeks against one full one --
    # CV 3.57, the figure the estate refused on. `erp.export_days` carries the measurement.
    # Exported daily, no sale is unpriced and the design is sealed. A test that prices its
    # sales the way the estate does is the only test that can say what the estate will do.
    erp.export_days(
        control, root / "landing" / "baseline-drops", since=baseline_opens, until=baseline_closes
    )
    erp.history(control, root / "landing", since=baseline_opens, until=baseline_closes)

    def rebuild(arrived_at: datetime) -> None:
        bulk.load(root / "landing", root / "bronze", arrived_at=arrived_at)
        build_silver(spark, root / "bronze", root / "silver")
        build_gold(spark, root / "silver", root=root / "gold")

    rebuild(datetime(2026, 9, 3, 9, 0))  # noqa: DTZ001 — the corpus is naive on purpose
    experiments.design(spark, scale=SCALE)

    committed = assignment_table.read_rows(spark, schema="gold", experiment_id="fresh-ladder")
    # **No rows is a refused design, and the window then runs under all-control.**
    #
    # This asserted rows until 2026-09-09. What made it pass was an ERP drop two days into the
    # world, pricing eight weeks of sales at one cost and collapsing the variance the design is
    # sized against; with the estate's own drop day the design is refused, here and there, and
    # `pipelines/ingest/arms.py` makes the same choice for the estate: nothing applied to
    # anybody, said out loud, with the reasons in `gold.readout`.
    #
    # A store the design excluded is simulated under control for the same reason: it is not in
    # the experiment, and the only honest arm for a shop nobody randomised is the one where
    # nothing was applied.
    arms = {store.store_id: Arm.CONTROL for store in chain.chain.stores}
    arms.update({store: Arm(arm) for store, arm in committed})
    treated = prepare("W6", seed=SEED, scale=SCALE, assignment=arms)
    erp.export_days(
        treated, root / "landing" / "window-drops", since=window_opens, until=window_closes
    )
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


def test_every_declared_experiment_comes_back_with_an_answer(
    rows: list[dict[str, object]],
) -> None:
    """**This asserted a number until 2026-09-09, and the number was an artefact.**

    The fixture exported the ERP's master data on the second day of the world and then priced
    eight weeks of sales against it. A cost ledger that old resolves every sale to one cost, so
    the margin per store-week barely moves, the variance the design is sized against collapses,
    and a design the estate refuses passes here. Moving the drop to the last day inside the
    baseline — which is what `infra/pipelines/jobs.tf` exports — turned this red:

        366 unit(s) per arm are needed even over 52 weeks, and the binding arm holds 48

    So the assertion that at least one experiment produces a *number* is gone, because this corpus
    cannot support one at the declared MDE and asserting it would be asserting the artefact. What
    is left is the shape: every declared experiment comes back, each row answers with exactly one
    of an uplift or a reason code, and at least one refuses.

    **And the number is back, since 2026-09-13, because the refusal was the artefact.** Both
    drop days above were wrong in opposite directions: two days in, no later cost step is known
    and every sale is priced stale; the last day, every step is known and every earlier sale has
    no cost the ERP had published, is dropped by `decision_economics`, and the pre-period is
    seven empty weeks against one full one -- the CV of 3.57 the estate refused on. Exported on
    every day of the slice, as `erp.export_days` now does and the estate now does, no sale is
    unpriced, the CV is 0.12, `fresh-ladder` is sealed, and on W6 -- a world with a real effect
    -- its readout is a number with an interval. A corpus that could not carry the experiment
    was a ledger nobody had priced. Found by a fresh-context review on 2026-09-12.
    """
    from pipelines.gold import experiments

    assert len(rows) == len(experiments.DECLARED), (
        f"{len(experiments.DECLARED)} experiments were declared and {len(rows)} rows came back. "
        "Nothing is retried and no experiment is dropped: a run that quietly lost one would be "
        "the fishing this repository exists to make impossible."
    )

    refusals = [row for row in rows if row["reason_code"] is not None]
    assert refusals, (
        "no experiment refused. A run in which everything succeeded has not demonstrated the "
        "thing this project is about."
    )
    numbers = [row for row in rows if row["uplift"] is not None]
    assert numbers, (
        "no experiment produced a number. W6 carries a real effect and the ledger is priced on "
        "every day of the baseline; a readout that still refuses is a bug, not a demonstration."
    )
    for row in rows:
        assert (row["uplift"] is None) != (row["reason_code"] is None), (
            f"{row['experiment_id']} carries both a number and a reason code, or neither. "
            "Exactly one of them is the row's answer."
        )


def test_the_peeking_design_is_refused_by_name(rows: list[dict[str, object]]) -> None:
    """The refusal is structural, so it is asserted by code rather than by count."""
    peeking = {row["experiment_id"]: row for row in rows}["fresh-ladder-peeking"]
    # **The leading code, and it is the structural one.** `DesignRefusal` orders its reasons by a
    # declared precedence, so the peeking rule comes ahead of the power reasons this corpus also
    # raises — which is what makes this assertion about the design rather than about the data.
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
    assert any(row["reason_code"] is not None for row in stored), (
        "gold.readout carries no reason code. This corpus cannot power the declared experiment "
        "— 366 units an arm against 48 — so every row is a refusal, and a table of refusals "
        "with no reason in it is a table that says nothing."
    )
    assert all((row["uplift"] is None) != (row["reason_code"] is None) for row in stored), (
        "a row answers with a number or with a reason, never with both and never with neither"
    )


def test_a_second_readout_restates_the_first_and_erases_nothing(
    spark: SparkSession, rows: list[dict[str, object]]
) -> None:
    """Doctrine rule 4, on the table that is the system's last word.

    `write` used to overwrite. Written twice, the table holds both readouts; every second row
    names the `readout_at` of the first for its experiment; `latest` returns the second; and the
    first is still there with its number.
    """
    from pipelines.gold import experiments

    before = [r.asDict() for r in spark.sql("select * from gold.readout").collect()]
    again = [{**row, "readout_at": "2999-01-01T00:00:00+00:00"} for row in rows]
    experiments.write(spark, again, schema="gold")

    after = [r.asDict() for r in spark.sql("select * from gold.readout").collect()]
    assert len(after) == len(before) + len(again), "the second write erased rows"
    first_at = {row["experiment_id"]: row["readout_at"] for row in before}
    seconds = [row for row in after if row["readout_at"] == "2999-01-01T00:00:00+00:00"]
    assert seconds and all(row["restates"] == first_at[row["experiment_id"]] for row in seconds), (
        "a restating row does not name the readout it restates"
    )
    newest = experiments.latest(spark, schema="gold")
    assert {row["readout_at"] for row in newest} == {"2999-01-01T00:00:00+00:00"}
    assert len(newest) == len(experiments.DECLARED)


def test_the_window_agrees_with_the_harness() -> None:
    """Two hand-kept declarations of one window, compared rather than trusted."""
    from evals.uplift import design as harness_design
    from pipelines.gold import experiments

    from pipelines import window as window_module

    assert window_module.PERIOD_WEEKS == harness_design.PERIOD_WEEKS
    assert window_module.PRE_PERIOD_WEEKS == harness_design.PRE_PERIOD_WEEKS
    assert experiments.SIZE_INDEX_TO_SQM == harness_design.SIZE_INDEX_TO_SQM
    assert experiments.WASTE_RATE_SCALE == harness_design.WASTE_RATE_SCALE
