"""Gold, built against local Delta by dbt, with the compiled consumers reached and not copied.

**This is `T011`'s `stop_at`** — *"when gold builds against local Delta and the compiled consumers
match byte-for-byte"* — and the two halves are asserted separately because they can fail
separately: a build that works while a second copy of a generated model drifts is exactly the
failure the second half is about.

**Rehearsal scale, and that is a measurement rather than a preference.** Silver's tests run at
`smoke`; gold's cannot, because at `smoke` **this corpus throws nothing away**:

    smoke      W6   shelf_days= 2,268   store-days with waste=     0   units=     0
    smoke      W1   shelf_days= 2,268   store-days with waste=     0   units=     0
    rehearsal  W6   shelf_days=26,880   store-days with waste= 1,329   units=16,370
    rehearsal  W1   shelf_days=26,880   store-days with waste= 1,329   units=18,009

`category_margin_per_store_week`'s third term is `sum(w.qty * w.unit_cost_as_of)`. Over a smoke
world that term is a sum over **nothing**, `waste_value_per_store_week` is a table with no rows,
and the metric quietly degenerates into revenue less cost of goods — **on a green run**. It is
the empty-population defect arriving in the primary metric of the project.

What rehearsal costs, measured on this machine, macOS arm64, warm:

    ingest 3.1s · silver 14.4s · gold 25.2s, plus two Spark sessions

**Every engine import is inside the function that needs it.** pytest collects every module before
it applies a mark expression, so a top-level `import pyspark` here would break `make test` on
every machine without the extra — see `tests/boundary/test_the_engine_is_never_skipped.py`, which
refuses it and refuses the two spellings that would turn an absent engine into a skip.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from pipelines.gold.build import Built
    from pipelines.gold.readout import Bound
    from pyspark.sql import SparkSession

    from holdout.core.experiment.assignment import SealedAssignment

pytestmark = pytest.mark.gold

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED = "gold"
DAY = "2025-09-02"
SCALE = "rehearsal"

#: The compiled readout this file reads. `{id}.v{version}` — the readout artefact keeps the dot
#: that the dbt model could not, because only dbt takes a file name as an identifier.
READOUT_STEM = "category_margin_per_store_week.v3"

#: The five models the project builds. Declared here **and** in `pipelines/gold/models.py`, and
#: the first test compares the two: a run that silently built fewer is the vacuous pass this
#: file exists to refuse, and a list kept in one place cannot notice it disagreeing with itself.
MODELS: tuple[str, ...] = (
    "decision_economics",
    "waste",
    "category_margin_per_store_week_v3",
    "units_sold_per_store_week_v1",
    "waste_value_per_store_week_v1",
)


@pytest.fixture(scope="module")
def spark(tmp_path_factory: pytest.TempPathFactory) -> Iterator[SparkSession]:
    """**One session for the file, and silver's build runs inside it too.**

    Not a saving. `SparkContext.stop()` stops the JVM-wide singleton, and a second session built
    afterwards comes back with `dagScheduler() == null` — every later statement then fails with
    `[INTERNAL_ERROR] Executed command failed. You hit a bug in Spark`, which names nothing that
    is true. The first version of this file built silver in its own session and stopped it, and
    eleven tests errored with that message before the cause was found in `Caused by:` nine lines
    down. So the file has exactly one session and nothing stops it early.
    """
    from pipelines.gold import session

    yield from session.sessions(tmp_path_factory.mktemp("warehouse"))


@pytest.fixture(scope="module")
def estate(spark: SparkSession, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One bronze, one silver, for the whole file. Built once because it is eighteen seconds."""
    from datetime import date

    from corpus.world import prepare
    from pipelines.ingest import bulk, erp
    from pipelines.silver.build import build as build_silver

    root = tmp_path_factory.mktemp("estate")
    run = prepare("W6", seed=SEED, scale=SCALE)
    erp.export(run, root / "landing", day=date.fromisoformat(DAY))
    erp.history(run, root / "landing")
    loaded = bulk.load(
        root / "landing",
        root / "bronze",
        arrived_at=datetime(2026, 9, 3, 9, 0),  # noqa: DTZ001 — the corpus is naive on purpose
    )
    assert loaded.files > 0, "the load moved nothing, so every assertion below would be vacuous"

    counts = build_silver(spark, root / "bronze", root / "silver")
    assert counts["sales"] > 0
    return root


@pytest.fixture(scope="module")
def gold(spark: SparkSession, estate: Path, tmp_path_factory: pytest.TempPathFactory) -> Built:
    from pipelines.gold.build import build

    return build(spark, estate / "silver", root=tmp_path_factory.mktemp("gold"))


# ------------------------------------------------------------------ it builds


def test_gold_builds_five_models_against_local_delta(spark: SparkSession, gold: Built) -> None:
    """`stop_at`'s first half: every model exists, holds rows, and is a **Delta** table.

    **The provider is asserted, and that is not decoration.** `file_format` is a dbt *model*
    config; written in `profiles.yml`'s `outputs` block it is silently ignored, `dbt run` stays
    green, and every table comes out `Provider = parquet` with `version as of` raising
    `UNSUPPORTED_FEATURE.TIME_TRAVEL`. That happened on this branch before it was caught, on a
    green run — so what is checked is what came out, not what was asked for.
    """
    from pipelines.gold import session

    counts = {**gold.priced, **gold.tables}
    for name in MODELS:
        assert counts[name] > 0, f"{name} built no rows, so every assertion over it is vacuous"
        described = {
            row["col_name"]: row["data_type"]
            for row in spark.sql(f"describe table extended {session.SCHEMA}.{name}").collect()
        }
        assert described["Provider"] == "delta", f"{name} is {described['Provider']}, not Delta"


def test_a_run_that_built_fewer_models_is_refused_rather_than_reported_as_success() -> None:
    """`dbt run` over a selection that resolves nothing exits 0. That is the failure here.

    If `model-paths` stopped reaching `generated/dbt/models` — a moved directory, a renamed
    artefact — dbt would build the two local models, **report success**, and gold would contain
    no metric at all. `models.missing` is what turns that into a refusal, and it is a pure
    function precisely so this case costs nothing to reach: a check exercised only by the
    expensive path is a check nobody exercises.

    The two declarations are also compared against each other. `MODELS` here and
    `EXPECTED_MODELS` there are written twice on purpose — one of them is what the test believes
    the project builds and the other is what the code believes, and a single list could not
    notice them disagreeing.
    """
    from pipelines.gold import models

    assert set(models.EXPECTED_MODELS) == set(MODELS)
    assert models.missing(MODELS) == []
    assert models.missing(("decision_economics", "waste")) == [
        "category_margin_per_store_week_v3",
        "units_sold_per_store_week_v1",
        "waste_value_per_store_week_v1",
    ]
    assert models.missing(()) == list(models.EXPECTED_MODELS)


# ------------------------------------------- the compiled consumers, reached and not copied


def test_no_file_under_pipelines_is_a_copy_of_a_generated_artefact() -> None:
    """`stop_at`'s second half, and it is an **absence** rather than an equality.

    The dbt project reaches `generated/dbt/models` through `model-paths`, which dbt resolves
    outside its own directory. So there is no copy to go stale and `make contracts`' byte
    comparison is the only definition check gold needs.

    **A gate that maintained an equality would be weaker than an arrangement in which the
    equality cannot be broken**, and this is what keeps the arrangement: any file under
    `pipelines/` whose bytes match one under `generated/` is a copy that has just been made, and
    the day after it is made it is a second definition.
    """
    generated = {
        path.read_bytes() for path in (REPO_ROOT / "generated").rglob("*") if path.is_file()
    }
    assert generated, "generated/ is empty, so this walk would pass over nothing"
    copies = [
        path.relative_to(REPO_ROOT)
        for path in (REPO_ROOT / "pipelines").rglob("*")
        if path.is_file() and path.read_bytes() in generated
    ]
    assert not copies, (
        f"{copies} duplicate a compiled artefact. `make contracts` byte-compares `generated/` "
        "against the compilers and never looks at `pipelines/`, so a copy here is a second "
        "definition nothing checks. The dbt project reaches the originals through `model-paths`."
    )


def test_the_dbt_project_reaches_the_generated_models_rather_than_a_directory_of_its_own() -> None:
    """The other direction: the arrangement above only holds while the path actually resolves."""
    import yaml
    from pipelines.gold import models

    project = yaml.safe_load((models.PROJECT / "dbt_project.yml").read_text(encoding="utf-8"))
    resolved = [(models.PROJECT / path).resolve() for path in project["model-paths"]]
    assert (REPO_ROOT / "generated" / "dbt" / "models").resolve() in resolved, resolved
    assert project["models"]["holdout_gold"]["+file_format"] == "delta", (
        "`file_format` is a model config. In `profiles.yml` it is accepted, ignored, and every "
        "table comes out parquet on a green run."
    )


def test_the_contract_and_the_engine_agree_about_what_half_even_means() -> None:
    """The contract's rounding, the SQL it compiles to, and what that SQL actually does.

    Three links and the middle one is the one that has a name: `half_even` compiles to `bround`
    and not to `round`, because Spark's `round` is half-up and a one-cent disagreement is a
    failed claim 5 for a stupid reason. The third link is measured on a value chosen so the two
    modes differ — `3.485` is `3.48` under half_even and `3.49` under half_up — because a value
    where they agree proves nothing about which one ran.
    """
    from holdout.contracts import loader

    contracts = loader.load(REPO_ROOT / "contracts")
    margin = next(
        metric
        for metric in contracts.metrics
        if metric.id == "category_margin_per_store_week" and metric.version == 3
    )
    assert margin.rounding.mode == "half_even"
    assert margin.rounding.sql_function == "bround"
    compiled = (
        REPO_ROOT / "generated" / "dbt" / "models" / "metrics" / f"{margin.identifier}.sql"
    ).read_text(encoding="utf-8")
    assert "bround(" in compiled and "round(" not in compiled.replace("bround(", "")


def test_spark_bround_is_the_half_even_the_contract_means(spark: SparkSession) -> None:
    """The third link, on the engine rather than on a page about the engine."""
    row = spark.sql(
        "select bround(cast(3.485 as decimal(18,6)), 2) as even, "
        "round(cast(3.485 as decimal(18,6)), 2) as up"
    ).collect()[0]
    assert str(row["even"]) == "3.48", row["even"]
    assert str(row["up"]) == "3.49", row["up"]


# --------------------------------------------------- the waste term, which smoke cannot reach


def test_the_waste_term_of_the_primary_metric_is_not_computed_over_nothing(
    spark: SparkSession, gold: Built
) -> None:
    """The reason this file runs at rehearsal, asserted rather than left in a docstring.

    At smoke this corpus throws nothing away — measured, 0 store-days of 2,268 on both W1 and W6
    — so `sum(w.qty * w.unit_cost_as_of)` would be a sum over an empty table and the primary
    metric would silently be revenue less cost of goods. The assertion is that the third term is
    live: `waste` has rows, and at least one metric cell **differs** from the same cell computed
    without the waste term.
    """
    from pipelines.gold import session

    assert gold.tables["waste"] > 0, (
        "the corpus threw nothing away at this scale, so the primary metric's third term is a "
        "sum over nothing and this file is measuring two thirds of the metric it names"
    )
    differing = spark.sql(f"""
        select count(*) as n
        from {session.SCHEMA}.category_margin_per_store_week_v3 m
        join (
            select store_id, iso_week, category,
                   bround(sum(cast(qty * unit_cost_as_of as decimal(38, 6))), 2) as thrown
            from {session.SCHEMA}.waste
            group by store_id, iso_week, category
        ) w
          on w.store_id = m.store_id and w.iso_week = m.iso_week and w.category = m.category
        where w.thrown > 0
    """).collect()[0]["n"]
    assert differing > 0, (
        "no metric cell has any waste under it, so the third term contributes nothing and a "
        "compiler that dropped it would leave every number in this table unchanged"
    )


def test_a_sale_with_no_published_cost_produces_no_margin_row_and_is_counted(
    spark: SparkSession, gold: Built
) -> None:
    """Doctrine rule 3 in gold: revenue with a null cost would enter the metric as pure margin.

    `sum(s.qty * s.price_paid) - sum(s.qty * s.unit_cost_as_of)` skips the null in the second sum
    and not in the first. So the row is dropped — and the count is carried out of the build
    rather than left as a difference somebody could take for a rounding artefact.
    """
    from pipelines.gold import session

    unpriced = gold.unpriced_sales
    assert unpriced > 0, (
        "no sale on this corpus predates its product's first published cost, so this assertion "
        "would pass over an empty population"
    )
    priced = spark.table(f"{session.SCHEMA}.priced_sales").count()
    economics = spark.table(f"{session.SCHEMA}.decision_economics").count()
    assert priced - economics == unpriced
    assert (
        spark.sql(
            f"select count(*) as n from {session.SCHEMA}.decision_economics "
            "where unit_cost_as_of is null"
        ).collect()[0]["n"]
        == 0
    )


def test_no_gold_table_the_readout_reads_carries_an_arm(spark: SparkSession, gold: Built) -> None:
    """The arm is joined in from the assignment, never carried by a fact table.

    **`bronze.price_decisions` carries an `arm` column and that is correct**: it is the corpus's
    analogue of `gold.decisions`, the decision record written at decision time, and a decision
    record that did not know which arm it routed by would be a decision record of nothing. What
    would not be correct is a table on the **readout's** path taking the arm from there — the
    readout joins `gold.experiment_assignment`, which was written before the period opened from
    the committed seed, and a fact table with its own `arm` column would make that join
    decorative.

    So this asserts a property of the tables this branch creates, and it does not touch bronze.
    """
    from pipelines.gold import facts, session

    for name in (*facts.PRICED_TABLES, "decision_economics", "waste"):
        columns = {field.name for field in spark.table(f"{session.SCHEMA}.{name}").schema.fields}
        assert "arm" not in columns, (
            f"{name} carries an `arm` column. The readout's join to "
            "`gold.experiment_assignment` is what attributes a unit to an arm; a fact table "
            "that already knew would let the attribution come from somewhere the committed "
            "lottery never touched."
        )
    assert gold.tables["decision_economics"] > 0


# ------------------------------------ the assignment table: before the period, and then stuck


def _seal(experiment_id: str = "EXP-gold", units: int = 12) -> SealedAssignment:
    """One committed lottery over stores this corpus actually has, drawn rather than built.

    The unit ids are the corpus's own — `ST0001` upward — because the readout joins the
    assignment to `gold.decision_economics` on `store_id`, and a lottery over invented ids would
    return no rows and every assertion below it would be over nothing.

    The covariates are the contract's, in the contract's order, because the engine refuses a
    matrix whose columns are not exactly `contracts/design/balance_covariates.yaml`'s. Two
    blocks, so every stratum can hold both arms.
    """
    from decimal import Decimal
    from fractions import Fraction

    from holdout.contracts import loader
    from holdout.core.experiment import assignment as core
    from holdout.core.experiment.balance import CovariateKind, CovariateMatrix

    contracts = loader.load(REPO_ROOT / "contracts")
    kinds = tuple(CovariateKind(c.type) for c in contracts.balance_covariates.covariates)
    formats = ("hypermarket", "supermarket")
    zones = ("zone_north", "zone_south")
    rows: dict[str, tuple[Fraction | str, ...]] = {}
    for index in range(units):
        block = index % 2
        rows[f"ST{index + 1:04d}"] = (
            Fraction(10_000 + 500 * block),
            formats[block],
            Fraction(800 + 100 * block),
            Fraction(3 + block, 100),
            zones[block],
        )
    matrix = CovariateMatrix.of(contracts.balance_covariates.ids, kinds, rows)
    drawn = core.draw(
        experiment_id=experiment_id,
        roster=tuple(rows),
        seed="committed-seed-0001",
        form_digest="f" * 64,
        matrix=matrix,
        control_size=core.control_size_for(units, Decimal("50")),
    )
    assert drawn is not None, "no stratification gave every stratum both arms on this roster"
    return drawn[0]


@pytest.fixture
def assigned(spark: SparkSession, tmp_path: Path) -> tuple[SealedAssignment, str]:
    """A fresh schema per test, because the table is append-only and cannot be rewritten."""
    from pipelines.gold import assignment

    # A schema **and** an experiment id per test. The schema because the table is append-only
    # and cannot be rewritten between tests; the experiment id because the two readout tests
    # copy their rows into the one `gold.experiment_assignment` the compiled query names by
    # hand, and a second copy under the same id would fan the join out rather than fail.
    schema = f"gold_{tmp_path.name.replace('-', '_')}"
    seal = _seal(experiment_id=f"EXP-{tmp_path.name.replace('-', '_')}")
    assignment.write(
        spark,
        seal,
        schema=schema,
        assigned_at=datetime(2026, 2, 20, 9, 0),  # noqa: DTZ001
        period_start="2026-W10",
    )
    return seal, schema


def test_the_assignment_is_refused_once_its_own_period_has_opened(
    spark: SparkSession, tmp_path: Path
) -> None:
    """*Written before the period opens* is a property of the moment, so the **write** refuses.

    A table cannot check afterwards when it was written; nothing in Delta records intent. So the
    declared `period_start` is an argument and an assignment stamped at or after it is refused by
    name. A lottery drawn once the outcome has started arriving is a lottery whose drawer had
    something to look at, which is `EXCLUSIONS_DEFINED_POST_HOC` wearing different clothes.
    """
    from pipelines.gold import assignment

    schema = f"late_{tmp_path.name.replace('-', '_')}"
    with pytest.raises(assignment.AssignmentWriteError, match="in or after its own comparison"):
        assignment.write(
            spark,
            _seal(),
            schema=schema,
            assigned_at=datetime(2026, 3, 4, 9, 0),  # noqa: DTZ001 — inside 2026-W10
            period_start="2026-W10",
        )


def test_a_second_assignment_for_the_same_experiment_is_refused(
    spark: SparkSession, assigned: tuple[SealedAssignment, str]
) -> None:
    """The table is append-only, so a second write adds a lottery rather than replacing one."""
    from pipelines.gold import assignment

    seal, schema = assigned
    with pytest.raises(assignment.AssignmentWriteError, match="already has"):
        assignment.write(
            spark,
            seal,
            schema=schema,
            assigned_at=datetime(2026, 2, 21, 9, 0),  # noqa: DTZ001
            period_start="2026-W10",
        )


def test_the_storage_refuses_three_of_the_four_ways_to_change_an_arm(
    spark: SparkSession, assigned: tuple[SealedAssignment, str]
) -> None:
    """**Measured, and the fourth is named rather than left out of the list.**

    `delta.appendOnly` is a table property the open-source engine enforces. Three of the four
    statements that could move a unit between arms are refused by the storage; the fourth, an
    append, is not — and it is the one `verify` exists for. `CLAUDE.md`'s doctrine 7 restatement
    says unopenability arrives in phase 3 with Unity Catalog grants, and nothing here claims it
    early: what is claimed is three refusals and a detection.

    **This is the half of a pair that asserts the guard is on**, and it is independent of
    `test_a_unit_erased_from_the_table_is_caught_as_well`, which turns the guard off in order to
    reach the layer behind it. Neither test is enough alone: without this one, `appendOnly`
    appears in the suite only where it is disabled.
    """
    from pipelines.gold import assignment

    _, schema = assigned
    table = f"{schema}.{assignment.TABLE}"
    assert assignment.is_append_only(spark, schema=schema)

    for statement in (
        f"update {table} set arm = 'control' where arm = 'treatment'",
        f"delete from {table} where arm = 'treatment'",
        f"insert overwrite {table} select * from {table}",
    ):
        with pytest.raises(Exception, match="APPEND_ONLY"):
            spark.sql(statement)

    before = spark.table(table).count()
    spark.sql(f"insert into {table} select * from {table} limit 1")
    assert spark.table(table).count() == before + 1, (
        "the append was refused too, which would make the sentence above wrong in the other "
        "direction: this test asserts what the storage does, not what it ought to do"
    )


def test_the_digest_catches_the_edit_the_storage_allows(
    spark: SparkSession, assigned: tuple[SealedAssignment, str]
) -> None:
    """The append the storage permits is the one the committed digest refuses.

    A unit with two rows has a roster the committed digest does not describe, so recomputing the
    digest over what the table holds — using the seal's own strata and form digest, which no
    table edit can reach — no longer matches.
    """
    from pipelines.gold import assignment

    seal, schema = assigned
    assignment.verify(spark, seal, schema=schema)

    table = f"{schema}.{assignment.TABLE}"
    victim = spark.sql(f"select store_id, arm from {table} limit 1").collect()[0]
    flipped = "control" if victim["arm"] == "treatment" else "treatment"
    spark.sql(
        f"insert into {table} select experiment_id, store_id, '{flipped}', assigned_at, seed, "
        f"draw_index, form_digest, digest from {table} where store_id = '{victim['store_id']}'"
    )
    with pytest.raises(assignment.AssignmentTamperedError, match="more than one row"):
        assignment.verify(spark, seal, schema=schema)


def test_a_unit_erased_from_the_table_is_caught_as_well(
    spark: SparkSession, assigned: tuple[SealedAssignment, str]
) -> None:
    """The other direction, and it is a different sentence from a unit holding the wrong arm.

    **This test disarms `appendOnly` on purpose, and it is one half of a pair.** The other half
    is `test_the_storage_refuses_three_of_the_four_ways_to_change_an_arm`, which asserts the
    property is **on** in ordinary operation and that the storage refuses `update`, `delete` and
    `insert overwrite`. Read alone, this file would eventually teach somebody that `appendOnly`
    is not load-bearing, because the only place they saw it named was where it was switched off.

    **The disarm exists *because* the outer layer works.** `delete` is refused by the storage, so
    an erasure cannot be produced any other way — and the digest's erasure case is the inner
    layer. An inner layer nobody has seen fire is a declared thing that never runs, which is the
    defect this repository files most; defence in depth is untestable without reaching past the
    outer layer, and untested depth is decoration.

    **It is not the `importorskip` shape.** That one makes a test silently *not run*. This one
    runs, against a configuration it weakened in the open and restores at the end — the last two
    assertions are that the guard is back on and biting, because a test that turns something off
    is a test that can leave it off.

    What survives the coordinated route — the one `CLAUDE.md` says is **not** closed — is the
    digest, because it is recomputed over the committed strata rather than over the rows.
    """
    from pipelines.gold import assignment

    seal, schema = assigned
    table = f"{schema}.{assignment.TABLE}"
    assert assignment.is_append_only(spark, schema=schema), (
        "the guard was already off before this test disarmed it, so what follows would prove "
        "nothing about the layer behind it"
    )

    spark.sql(f"alter table {table} set tblproperties ({assignment.APPEND_ONLY} = false)")
    erased = spark.sql(f"select store_id from {table} limit 1").collect()[0]["store_id"]
    spark.sql(f"delete from {table} where store_id = '{erased}'")
    with pytest.raises(assignment.AssignmentTamperedError, match="drawn and absent"):
        assignment.verify(spark, seal, schema=schema)

    spark.sql(f"alter table {table} set tblproperties ({assignment.APPEND_ONLY} = true)")
    assert assignment.is_append_only(spark, schema=schema)
    with pytest.raises(Exception, match="APPEND_ONLY"):
        spark.sql(f"delete from {table} where store_id = '{erased}'")


# ------------------------------------------------------ the readout, and the pin it carries


def test_the_executed_text_differs_from_the_artefact_only_at_parameter_positions() -> None:
    """The narrow claim, checked rather than asserted.

    What runs is the compiled file with `:name` replaced by literals and **nothing else changed**.
    `Bound` builds both texts from the same spans, so rebuilding the original from what was
    executed and comparing it to the file on disk fails if a single character outside a marker
    moved.
    """
    from pipelines.gold import readout

    path = readout.artefact("category_margin_per_store_week.v3")
    original = path.read_text(encoding="utf-8")
    pinned = readout.pins(original)
    assert set(pinned) == {"gold.decision_economics", "gold.waste", "gold.experiment_assignment"}
    parameters: dict[str, object] = {
        "experiment_id": "EXP-gold",
        "period_start": "2025-W36",
        "period_end": "2025-W40",
    }
    parameters.update(dict.fromkeys(pinned.values(), 3))
    bound = readout.bind(original, parameters)
    assert bound.original == original
    assert bound.executed != original
    assert ":data_version" not in bound.executed
    assert bound.executed.count("version as of 3") == 3
    assert "'EXP-gold'" in bound.executed


def test_a_parameter_bound_that_the_artefact_does_not_name_is_refused() -> None:
    """The direction that fails **silently** if it is not refused.

    A marker with no value raises at the engine — loudly, but naming Delta's parser rather than
    the caller. A value with no marker is a caller who believes they have restricted something
    they have not: the query runs, over more rows than intended, and returns a number.
    """
    from pipelines.gold import readout

    text = "select 1 from t where a = :experiment_id"
    with pytest.raises(readout.ParameterError, match="nothing bound it"):
        readout.bind(text, {})
    with pytest.raises(readout.ParameterError, match="no such parameter"):
        readout.bind(text, {"experiment_id": "E", "store_id": "ST0001"})
    with pytest.raises(readout.ParameterError, match="a readout parameter is an int"):
        readout.bind(text, {"experiment_id": None})


#: The compiled readouts, enumerated once so the count can be asserted before anything is
#: parametrised over it. **A parametrised test with no cases does not run at all**, and pytest
#: reports that as a green suite rather than as an empty one.
COMPILED_READOUTS: tuple[Path, ...] = tuple(
    sorted((REPO_ROOT / "generated" / "readout").glob("*.sql"))
)


def test_there_are_compiled_readouts_to_bind() -> None:
    """The population, before the parametrisation that walks it.

    **The guard inside each case cannot fire when there are no cases.** If `generated/readout/`
    were empty, or the glob stopped matching what the compilers write, the test below would
    collect zero parameters, run nothing, and the suite would be green over an absence — which is
    the fourth instance of this shape in four days and the first one caught before it happened.

    The count is derived rather than frozen: one readout per metric in force, which is what
    `compile_all` emits and what `make contracts` byte-compares.
    """
    from holdout.contracts import loader
    from holdout.contracts.compilers import in_force_metrics

    in_force = in_force_metrics(loader.load(REPO_ROOT / "contracts"))
    assert COMPILED_READOUTS, (
        "generated/readout/ holds no .sql, so every test parametrised over it would collect "
        "zero cases and pass. That is an instrument that could not answer, not an answer."
    )
    assert len(COMPILED_READOUTS) == len(in_force), (
        f"{len(COMPILED_READOUTS)} compiled readout(s) against {len(in_force)} metric(s) in "
        "force. One of the two moved without the other, and `make contracts` is where that is "
        "supposed to be caught."
    )


@pytest.mark.parametrize("path", COMPILED_READOUTS, ids=lambda p: p.name)
def test_every_compiled_readout_binds_in_both_directions(path: Path) -> None:
    """The binder is a small parser of the artefact, and small parsers drift from what they parse.

    **Over the real files, all of them, rather than over a string written here.** The refusals
    are tested on a synthetic text one test up, which proves the mechanism; this proves the
    mechanism is pointed at what actually runs, and it re-parametrises itself when a fourth
    metric contract comes into force.

    Both directions, because they fail differently:

    * **a parameter the compiler emits and the binder does not bind** would reach Spark, which
      raises about an unbound parameter — under `delta-spark` it does not even do that, it
      silently leaves the marker in the plan. Either way the message names the engine rather
      than the compiler that added it;
    * **a binding for a parameter the compiler no longer emits** fails **silently**: the query
      runs, the stale value goes nowhere, and nothing says the caller is pinning something that
      is not there any more.
    """
    from pipelines.gold import readout

    text = path.read_text(encoding="utf-8")
    named = {match.group("name") for match in readout.PARAMETER.finditer(text)}
    assert named, f"{path.name} names no parameter, so neither direction below means anything"

    complete: dict[str, object] = {
        name: 1 if name.startswith("data_version") else "x" for name in named
    }
    assert readout.bind(text, complete).original == text

    for withheld in sorted(named):
        short = {name: value for name, value in complete.items() if name != withheld}
        with pytest.raises(readout.ParameterError, match="nothing bound it"):
            readout.bind(text, short)

    with pytest.raises(readout.ParameterError, match="no such parameter"):
        readout.bind(text, {**complete, "data_version_gold_a_table_nobody_reads": 1})

    # The parser and the parameters agree: every relation `pins` finds is pinned by a parameter
    # the file names, and every `data_version_*` parameter belongs to a relation it found.
    pinned = readout.pins(text)
    assert set(pinned.values()) == {name for name in named if name.startswith("data_version")}


def test_the_readout_pins_a_delta_version_and_the_pin_is_what_holds_the_number(
    spark: SparkSession, gold: Built, assigned: tuple[SealedAssignment, str]
) -> None:
    """`CLAUDE.md`: *"Without it, re-running last month's readout returns a different number as
    late data arrives."*

    **Two-sided on purpose.** The pinned number must survive an append, and the unpinned number
    must not. An assertion with only the first half would pass over a table nobody had appended
    to — which is the empty-population defect wearing a different hat.
    """
    from pipelines.gold import assignment, session

    seal, schema = assigned
    del gold  # the fixture is the dependency; the tables it built are read through the session

    # The readout names `gold.experiment_assignment` by hand, so the rows have to be there
    # under that name rather than under the per-test schema the seal was written into.
    assignment.create(spark, schema=session.SCHEMA)
    spark.sql(
        f"insert into {session.SCHEMA}.{assignment.TABLE} select * from {schema}.{assignment.TABLE}"
    )
    pinned = readout_pins(spark)
    assert len(pinned) == 3, pinned

    before, bound = readout_rows(spark, pinned, seal)
    assert before, "the readout returned nothing, so neither half of this test means anything"
    assert "version as of" in bound.executed

    spark.sql(f"""
        insert into {session.SCHEMA}.decision_economics
        select store_id, iso_week, category, qty * 1000, price_paid * 10, unit_cost_as_of
        from {session.SCHEMA}.decision_economics limit 200
    """)

    after, _ = readout_rows(spark, pinned, seal)
    assert after == before, "the pin did not hold: late data changed a number that was pinned"

    unpinned, _ = readout_rows(spark, readout_pins(spark), seal)
    assert unpinned != before, (
        "reading the latest version returned the same numbers as the pinned one, so this "
        "corpus's late data changed nothing and the pin was never actually load-bearing here"
    )


def readout_text() -> str:
    from pipelines.gold import readout

    return readout.artefact(READOUT_STEM).read_text(encoding="utf-8")


def readout_pins(spark: SparkSession) -> dict[str, int]:
    """Every relation the compiled readout pins, at its current version."""
    from pipelines.gold import readout

    return readout.pin_now(spark, readout_text())


def readout_rows(
    spark: SparkSession, versions: Mapping[str, int], seal: SealedAssignment
) -> tuple[dict[tuple[str, str, str], str], Bound]:
    """One readout, as a comparable mapping, beside the `Bound` that produced it."""
    from pipelines.gold import readout

    frame, bound = readout.run(
        spark,
        READOUT_STEM,
        experiment_id=seal.experiment_id,
        versions=versions,
        period_start="2025-W01",
        period_end="2025-W52",
    )
    rows = {
        (row["store_id"], row["iso_week"], row["category"]): str(row["metric_value"])
        for row in frame.collect()
    }
    return rows, bound


def test_the_readout_splits_by_arm_from_the_assignment_and_from_nowhere_else(
    spark: SparkSession, gold: Built, assigned: tuple[SealedAssignment, str]
) -> None:
    """Every row the readout returns carries the arm the committed lottery drew for its store."""
    from pipelines.gold import assignment, session

    from holdout.core.experiment.codes import Arm

    seal, schema = assigned
    del gold

    assignment.create(spark, schema=session.SCHEMA)
    spark.sql(
        f"insert into {session.SCHEMA}.{assignment.TABLE} select * from {schema}.{assignment.TABLE}"
    )
    from pipelines.gold import readout

    frame, _ = readout.run(
        spark,
        READOUT_STEM,
        experiment_id=seal.experiment_id,
        versions=readout_pins(spark),
        period_start="2025-W01",
        period_end="2025-W52",
    )
    rows = frame.collect()
    assert rows, "the readout returned nothing, so the arms it did not return prove nothing"
    for row in rows:
        assert Arm(row["arm"]) is seal.arms[row["store_id"]]
