"""`gold.readout` — one row per experiment, and the two experiments that fill it.

**This module exists because the table `run` is accepted on was written by nothing.**
`PLAN.md` closes phase 3 on *at least one experiment producing a number and at least one refusing
for the right reason*, `ops/run_assertions.py` asserts exactly that against
`{catalog}.gold.readout`, and a `grep` for that table over the whole repository found the
constant in the assertion and no writer anywhere. `pipelines/gold/assignment.py` could create the
append-only assignment table, refuse an update and verify a seal — and nothing called it either.
Every piece of the experiment existed and none of them were joined up.

What this adds is the join, and nothing else
--------------------------------------------
Every decision here is `holdout.core`'s. `assess` decides whether an experiment may exist,
`close` decides whether a number may be stated, and both are pure functions over plain data that
this module hands them. It is an **adapter**, in exactly the sense `CLAUDE.md` means — the second
one over the same core, beside `evals/uplift/harness.py`, which assembles the same arguments from
the corpus in memory rather than from four Delta tables.

The two experiments, and why one of them refuses on purpose
-----------------------------------------------------------
`ops/run_assertions.py` requires both a number and a refusal, and says why: *a system that only
ever refuses passes every world and is worthless*, and *a run in which everything succeeded has
not demonstrated the thing this project is about.* So the pair is declared rather than hoped for:

    fresh-ladder            the whole estate, a single readout at the end     a number
    fresh-ladder-peeking    the same design with a group-sequential rule
                            and no spending function                         STOPPING_RULE_PERMITS_PEEKING

**The second is refused by a structural fact, not by an accident of the data.** A refusal that
depended on the roster being small enough or the variance being high enough would be a
demonstration that stops working the day the estate grows — and `feasibility.py` is explicit that
this one is decided over `StoppingRule`, a value the engine holds, and never over prose.

**And the first may still refuse.** If the estate's variance makes the declared MDE undetectable,
`assess` says so and `run` goes red on `--require-number`. That is the gate working: this module
does not get to choose the answer, only to ask the question honestly.

Dates are arguments, and `assigned_at` is the design moment rather than the clock
--------------------------------------------------------------------------------
`pipelines/gold/assignment.py` refuses a write at or after the period opens — *a lottery drawn
once the outcome has started arriving is a lottery whose drawer had something to look at.* A run
executed after eight months of history have landed is, by the clock, always too late. So the
design moment is derived from the data's own calendar: the last instant of the week before the
comparison window opens. That is the same convention every date in `holdout.core` follows, and it
is what makes a readout replayable a year later.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import TYPE_CHECKING, Any

from holdout.contracts.loader import load
from holdout.core.design import (
    DecisionRule,
    DesignForm,
    DesignRefusal,
    Feasible,
    FilledBy,
    FilledByKind,
    Intervention,
    MaxDuration,
    Mde,
    MdeDirection,
    MdeKind,
    Scope,
    StoppingKind,
    StoppingRule,
    Unit,
    assess,
)
from holdout.core.experiment import (
    CovariateKind,
    CovariateMatrix,
    Period,
    Readout,
    ReadoutRefusal,
    close,
    reference_set,
)
from pipelines import window as window_module
from pipelines.gold import assignment as assignment_table

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from pyspark.sql import SparkSession

#: Parts per million, for `waste_rate`; and the corpus records a store's size as an index around
#: 1.0 rather than as an area. Both are `evals/uplift/design.py`'s, for the same reason.
WASTE_RATE_SCALE = 1_000_000
SIZE_INDEX_TO_SQM = 1_000

#: The metric the experiment is read out on. Named rather than derived: `assess` refuses an id the
#: contract does not carry, which is the check that makes naming it safe.
PRIMARY_METRIC = "category_margin_per_store_week"


#: The two policy refs, read from the same source that delivers them rather than written here.
#:
#: **Written here they were wrong, and the run said so by refusing.** The first version declared
#: `policy:candidate` and `policy:incumbent`; what `silver.price_displayed` carries is
#: `ladder_policy@candidate` and `ladder_policy@v1`, so `contamination.check` compared a declared
#: arm against a delivered ref that could never match it and every experiment came back
#: `CONTAMINATED_ASSIGNMENT`. That is the check working — it is exactly the finding it exists to
#: report, arriving against the declaration rather than against the delivery.
#:
#: The control ref is the contract's: `ladder_policy@v{version}` from `contracts/policies/`. The
#: treatment ref is **not** a version in that directory — `evals/uplift/design.py` records the
#: same gap, deferred in `docs/DECISIONS.md` rather than papered over — so it is read off the
#: corpus's own candidate rather than invented a second time here.
def _policy_refs() -> tuple[str, str]:
    """`(treatment, control)`, from the policy module that generates what the shelf displays."""
    from corpus.world import policy

    ladder = policy.contract_ladder()
    return policy.candidate(ladder).policy_id, ladder.policy_id


#: The effect the design declares it is sized to detect, as a percentage of the pre-period mean.
#:
#: **Generous on purpose, and the direction of the generosity is the honest one.** A smaller MDE
#: is a stricter claim and needs more units; declaring one the estate cannot support would make
#: `assess` refuse both experiments and the run would demonstrate only that it can refuse. Ten
#: percent of a store's weekly category margin is a difference a chain would act on, which is the
#: test a declared MDE has to pass — it is not chosen to be reachable, it is chosen to be worth
#: reaching, and `UNDERPOWERED_FOR_CAPACITY` is what happens if the estate cannot reach it.
MDE_PCT = Decimal("10")

#: How many acknowledged labels a store needs before it counts as exposed, as a fraction of its
#: own acknowledgements. `contracts/design/inference.yaml` carries the estate-wide threshold the
#: readout is judged against; this is the per-unit rule that decides which side of it a store
#: falls, and it is the same one `evals/uplift/harness.py` applies.
UNIT_EXPOSED_MIN_ACK = Fraction(1, 2)


class ExperimentError(ValueError):
    """The estate cannot supply what an experiment has to be measured against."""


@dataclass(frozen=True, slots=True)
class Declared:
    """One experiment, declared before anything is measured."""

    experiment_id: str
    seed: str
    hypothesis: str
    stopping: StoppingRule

    def form(self, categories: Sequence[str]) -> DesignForm:
        """The nine fields. `evals/uplift/design.py::form` fills the same ones for the harness."""
        return DesignForm(
            hypothesis=self.hypothesis,
            intervention=Intervention(*_policy_refs()),
            scope=Scope(categories=tuple(categories), products=None, stores=None),
            primary_metric=PRIMARY_METRIC,
            unit=Unit.STORE,
            mde=Mde(kind=MdeKind.RELATIVE_PCT, value=MDE_PCT, direction=MdeDirection.EITHER),
            max_duration=MaxDuration(weeks=window_module.PERIOD_WEEKS),
            exclusions=(),
            decision_rule=DecisionRule(
                if_significant="Roll the candidate ladder out across the fresh estate.",
                if_not_significant="Keep the existing ladder and close the experiment.",
                if_refused="Publish the reason code and re-open the design against what it names.",
            ),
            filled_by=FilledBy(kind=FilledByKind.POLICY, name="estate_run"),
        )


#: The two, and the second is refused by construction. See the module docstring.
DECLARED: tuple[Declared, ...] = (
    Declared(
        experiment_id="fresh-ladder",
        seed="fresh-ladder/estate",
        hypothesis=(
            "A shallower fresh markdown ladder raises category margin per store-week, because "
            "the trade given away at the deeper rungs is worth more than the waste it avoids."
        ),
        stopping=StoppingRule(kind=StoppingKind.SINGLE_READOUT_AT_END),
    ),
    Declared(
        experiment_id="fresh-ladder-peeking",
        seed="fresh-ladder/estate-peeking",
        hypothesis=(
            "The same hypothesis, proposed with a rule that looks four times and stops when it "
            "likes what it sees."
        ),
        # **Constructible on purpose.** `StoppingRule`'s own docstring says so: a type that
        # raised here would turn a refusal into an error and make the refusal unreachable.
        stopping=StoppingRule(kind=StoppingKind.GROUP_SEQUENTIAL, spending_function=None, looks=4),
    ),
)


# ---------------------------------------------------------------- what the estate is asked for


def _monday(iso_week: str) -> datetime:
    """The Monday of an ISO week written `YYYY-Www`, which is how the metric models write it."""
    year, week = iso_week.split("-W")
    return datetime.strptime(f"{year}-{int(week)}-1", "%G-%V-%u").replace(tzinfo=UTC)


def _metric_table(metrics: Sequence[Any]) -> tuple[str, Any]:
    """The compiled table for `PRIMARY_METRIC`'s latest version, and the metric behind it."""
    family = [metric for metric in metrics if metric.id == PRIMARY_METRIC]
    if not family:
        raise ExperimentError(
            f"{PRIMARY_METRIC} is not in contracts/metrics/. `assess` would refuse the design "
            "with METRIC_NOT_IN_CONTRACT, which is the right answer to a different question: "
            "this module named a metric the contract does not have."
        )
    latest = max(family, key=lambda metric: metric.version)
    return f"{PRIMARY_METRIC}_v{latest.version}", latest


def _by_unit_week(
    spark: SparkSession, table: str, weeks: Sequence[str]
) -> dict[tuple[str, str], int]:
    """The governed metric per store-week, in cents, summed across the categories in its grain.

    **Summed rather than averaged.** The metric's grain is `[store_id, iso_week, category]` and
    the experiment's unit is a store: a store-week's margin is the margin of everything it sold,
    which is the sum. `evals/uplift/grouped_metric.py` makes the same reduction for the harness.
    """
    quoted = ", ".join(f"'{week}'" for week in weeks)
    rows = spark.sql(
        f"select store_id, iso_week, sum(metric_value) as value from {table} "
        f"where iso_week in ({quoted}) group by store_id, iso_week"
    ).collect()
    return {(row["store_id"], row["iso_week"]): round(float(row["value"]) * 100) for row in rows}


def _pre_period_sums(
    spark: SparkSession, schema: str, weeks: Sequence[str]
) -> dict[str, dict[str, int]]:
    """Revenue, cost of goods and waste value per store over the pre-period, in cents.

    Read from the two dbt models rather than from the priced tables, so the covariate and the
    outcome are computed off the same rows: `decision_economics` is what the metric's first two
    terms are summed from and `waste` is its third.
    """
    quoted = ", ".join(f"'{week}'" for week in weeks)
    sales = spark.sql(
        f"select store_id, "
        f"sum(qty * price_paid) as revenue, sum(qty * unit_cost_as_of) as cogs "
        f"from {schema}.decision_economics where iso_week in ({quoted}) group by store_id"
    ).collect()
    waste = spark.sql(
        f"select store_id, sum(qty * unit_cost_as_of) as waste "
        f"from {schema}.waste where iso_week in ({quoted}) group by store_id"
    ).collect()
    out: dict[str, dict[str, int]] = {}
    for row in sales:
        out.setdefault(row["store_id"], {})["revenue"] = round(float(row["revenue"] or 0) * 100)
        out[row["store_id"]]["cogs"] = round(float(row["cogs"] or 0) * 100)
    for row in waste:
        out.setdefault(row["store_id"], {})["waste"] = round(float(row["waste"] or 0) * 100)
    return out


def _store_attributes(
    spark: SparkSession, schema: str
) -> dict[str, tuple[str, float, str, int, int]]:
    """`silver.stores`, which exists because this is what asked for it."""
    rows = spark.sql(
        f"select store_id, store_format, size_index, pricing_zone, x_m, y_m from {schema}.stores"
    ).collect()
    if not rows:
        raise ExperimentError(
            f"{schema}.stores is empty, so three of the five declared balance covariates have no "
            "values. An assignment balanced on covariates nobody measured is a draw, not a "
            "stratified one."
        )
    return {
        row["store_id"]: (
            row["store_format"],
            float(row["size_index"]),
            row["pricing_zone"],
            int(row["x_m"]),
            int(row["y_m"]),
        )
        for row in rows
    }


def _matrix(
    units: Sequence[str],
    attributes: Mapping[str, tuple[str, float, str, int, int]],
    sums: Mapping[str, Mapping[str, int]],
    covariates: Any,
) -> CovariateMatrix:
    """The five declared covariates, in the contract's own order, for every unit on the roster."""
    rows: dict[str, tuple[Fraction | str, ...]] = {}
    for unit in units:
        store_format, size_index, pricing_zone, _x, _y = attributes[unit]
        cogs = sums.get(unit, {}).get("cogs", 0)
        waste = sums.get(unit, {}).get("waste", 0)
        waste_rate = Fraction(round(waste * WASTE_RATE_SCALE / cogs)) if cogs else Fraction(0)
        rows[unit] = (
            Fraction(sums.get(unit, {}).get("revenue", 0)),
            store_format,
            Fraction(round(size_index * SIZE_INDEX_TO_SQM)),
            waste_rate,
            pricing_zone,
        )
    return CovariateMatrix.of(
        covariates.ids,
        tuple(CovariateKind(covariate.type) for covariate in covariates.covariates),
        rows,
    )


def _exposure(
    spark: SparkSession, schema: str, weeks: Sequence[str]
) -> tuple[frozenset[str], dict[str, str], dict[str, int]]:
    """Which stores were exposed, what each was delivered, and how many refs each saw.

    **Read from the acknowledgement and never from the decision.** `CLAUDE.md`: *the ESL
    acknowledgement … is the only evidence that a price reached the shelf. Without it every
    experiment measures intentions instead of actions.* `silver.price_displayed` is built from
    `esl_acks`; `bronze.price_decisions` — which carries the arm — is read by nothing, and this
    module is one of the places where that has to stay true.
    """
    quoted = ", ".join(f"'{week}'" for week in weeks)
    rows = spark.sql(
        "select store_id, accepted, policy_id, count(*) as n from "
        f"{schema}.price_displayed where concat(lpad(cast(extract(YEAROFWEEK from event_ts) as "
        "string), 4, '0'), '-W', lpad(cast(weekofyear(event_ts) as string), 2, '0')) "
        f"in ({quoted}) group by store_id, accepted, policy_id"
    ).collect()

    total: dict[str, int] = {}
    accepted: dict[str, int] = {}
    refs: dict[str, dict[str, int]] = {}
    for row in rows:
        store = row["store_id"]
        total[store] = total.get(store, 0) + int(row["n"])
        if row["accepted"]:
            accepted[store] = accepted.get(store, 0) + int(row["n"])
            refs.setdefault(store, {})
            refs[store][row["policy_id"]] = refs[store].get(row["policy_id"], 0) + int(row["n"])

    exposed = frozenset(
        store
        for store, seen in total.items()
        if seen and Fraction(accepted.get(store, 0), seen) >= UNIT_EXPOSED_MIN_ACK
    )
    # **The modal ref, and the count of distinct ones beside it.** A store delivered two policies
    # during one window is contamination evidence rather than a tie to break quietly, so the
    # number that says so travels with the answer.
    delivered = {
        store: max(seen.items(), key=lambda pair: pair[1])[0] for store, seen in refs.items()
    }
    distinct = {store: len(seen) for store, seen in refs.items()}
    return exposed, delivered, distinct


def _data_version(spark: SparkSession, table: str) -> str:
    """The table and the Delta version it was read at.

    `CLAUDE.md`: *the readout pins a Delta version. Without it, re-running last month's readout
    returns a different number as late data arrives.*
    """
    version = spark.sql(f"describe history {table} limit 1").collect()[0]["version"]
    return f"{table}@{version}"


def _neighbour_pairs(
    attributes: Mapping[str, tuple[str, float, str, int, int]], *, radius_m: int
) -> tuple[tuple[str, str], ...]:
    """Every ordered pair of stores closer together than the declared radius.

    Euclidean over the coordinates `store_master` publishes, which is what the corpus's own
    chain uses to place them. The radius is `contracts/design/inference.yaml`'s, not this
    module's: a distance at which two stores stop being independent is a claim about shoppers.
    """
    units = sorted(attributes)
    pairs: list[tuple[str, str]] = []
    for index, left in enumerate(units):
        _f, _s, _z, left_x, left_y = attributes[left]
        for right in units[index + 1 :]:
            _f2, _s2, _z2, right_x, right_y = attributes[right]
            if (left_x - right_x) ** 2 + (left_y - right_y) ** 2 <= radius_m**2:
                pairs.append((left, right))
    return tuple(pairs)


def _row(
    declared: Declared,
    *,
    outcome: Readout | ReadoutRefusal | DesignRefusal,
    moment: str,
    data_version: str,
    period: tuple[str, str],
) -> dict[str, Any]:
    """One `gold.readout` row, in the shape `ops/run_assertions.py` reads.

    **`uplift` and `reason_code` are the two columns the acceptance queries, and exactly one of
    them is null.** A row with both would be a number stated beside the reason it may not be, and
    a row with neither would be an experiment that did not happen.
    """
    row: dict[str, Any] = {
        "experiment_id": declared.experiment_id,
        "moment": moment,
        "metric_ref": None,
        "data_version": data_version,
        "period_opens_on": period[0],
        "period_ends_on": period[1],
        "seed": declared.seed,
        "uplift": None,
        "ci_low": None,
        "ci_high": None,
        "p_value": None,
        "draws": None,
        "reason_code": None,
        "reason_codes": None,
        "checks": None,
        "digest": None,
    }
    if isinstance(outcome, DesignRefusal):
        row["reason_code"] = outcome.reasons[0].code.value
        row["reason_codes"] = ",".join(reason.code.value for reason in outcome.reasons)
        return row

    row["metric_ref"] = outcome.metric_ref
    row["digest"] = outcome.digest
    row["checks"] = "; ".join(str(check) for check in outcome.checks)
    if isinstance(outcome, ReadoutRefusal):
        row["reason_code"] = outcome.code.value
        row["reason_codes"] = ",".join(code.value for code in outcome.codes)
        return row

    low, high = outcome.confidence_interval
    row["uplift"] = float(outcome.uplift)
    row["ci_low"] = low
    row["ci_high"] = high
    row["p_value"] = float(outcome.p_value)
    row["draws"] = outcome.draws
    return row


#: The readout table's shape, declared here because `spark.createDataFrame` over dictionaries
#: would infer it from whichever row came first — and the first row of a run in which every
#: experiment refused carries a null in every column a number would have filled.
SCHEMA = (
    "experiment_id string, moment string, metric_ref string, data_version string, "
    "period_opens_on string, period_ends_on string, seed string, uplift double, "
    "ci_low int, ci_high int, p_value double, draws int, reason_code string, "
    "reason_codes string, checks string, digest string"
)
TABLE = "readout"


@dataclass(frozen=True, slots=True)
class Measured:
    """Everything both moments need, measured once from the estate's own tables."""

    metric: Any
    metric_ids: tuple[str, ...]
    table: str
    data_version: str
    roster: tuple[str, ...]
    matrix: CovariateMatrix
    mean_per_unit_week: Decimal
    variance_per_unit_week: Decimal
    categories: tuple[str, ...]
    neighbours: tuple[tuple[str, str], ...]
    pre_weeks: tuple[str, ...]
    period_weeks: tuple[str, ...]
    period: Period
    assigned_at: datetime
    contracts: Any


def measure(spark: SparkSession, *, scale: str, gold_schema: str, silver_schema: str) -> Measured:
    """What the estate says, before anything is decided about it.

    **Measured over the baseline and never over the window.** `pipelines/window.py` owns the
    split; the covariates and the two sizing figures come from the last
    `PRE_PERIOD_WEEKS` weeks before the window opens, because a covariate measured inside the
    comparison window uses the same data twice and biases the estimate it is supposed to protect.

    Called by both moments, and that is the point: the lottery `design` seals is a deterministic
    function of these numbers, so `readout` re-deriving them arrives at the same seal and can
    check the table against it rather than trusting it.
    """
    contracts = load()
    table, metric = _metric_table(contracts.metrics)
    qualified = f"{gold_schema}.{table}"

    opens, closes = window_module.window(scale)
    period_weeks = window_module.iso_weeks(opens, closes)
    baseline_opens, baseline_closes = window_module.baseline(scale)
    pre_weeks = window_module.iso_weeks(baseline_opens, baseline_closes)[
        -window_module.PRE_PERIOD_WEEKS :
    ]

    by_unit_week = _by_unit_week(spark, qualified, pre_weeks)
    if not by_unit_week:
        raise ExperimentError(
            f"{qualified} holds nothing for the pre-period weeks {pre_weeks[0]}..{pre_weeks[-1]}, "
            "so there are no covariates to balance on. The gold job builds that table: run it "
            "over the baseline before this."
        )

    attributes = _store_attributes(spark, silver_schema)
    roster = tuple(sorted({unit for unit, _week in by_unit_week} & set(attributes)))
    if not roster:
        raise ExperimentError(
            f"no store appears in both {qualified} and {silver_schema}.stores. The outcome and "
            "the covariates describe different estates, and an experiment cannot be balanced "
            "across the gap."
        )

    sums = _pre_period_sums(spark, gold_schema, pre_weeks)
    matrix = _matrix(roster, attributes, sums, contracts.balance_covariates)

    per_unit = {unit: [by_unit_week.get((unit, week), 0) for week in pre_weeks] for unit in roster}
    mean = statistics.fmean(statistics.fmean(values) for values in per_unit.values())
    within = statistics.fmean(statistics.variance(values) for values in per_unit.values())
    if mean <= 0:
        raise ExperimentError(
            f"the pre-period mean per store-week is {mean}. A relative MDE against a "
            "non-positive mean is not a difference anybody could detect."
        )

    categories = tuple(
        sorted(
            row["category"]
            for row in spark.sql(f"select distinct category from {qualified}").collect()
        )
    )
    return Measured(
        metric=metric,
        metric_ids=tuple(sorted({each.id for each in contracts.metrics})),
        table=qualified,
        data_version=_data_version(spark, qualified),
        roster=roster,
        matrix=matrix,
        mean_per_unit_week=Decimal(round(mean)),
        variance_per_unit_week=Decimal(round(within)),
        categories=categories,
        neighbours=_neighbour_pairs(attributes, radius_m=contracts.inference.neighbour_radius_m),
        pre_weeks=pre_weeks,
        period_weeks=period_weeks,
        period=Period(opens_on=opens, ends_on=closes),
        # The last instant before the window opens. `pipelines/gold/assignment.py` refuses a
        # write at or after it, and by the clock a run over loaded history is always too late —
        # so the design moment is the data's, like every other date in this repository.
        assigned_at=datetime.combine(opens, datetime.min.time()) - timedelta(seconds=1),
        contracts=contracts,
    )


def _verdicts(measured: Measured) -> list[tuple[Declared, Feasible | DesignRefusal]]:
    """Moment 1 for every declared experiment, in declaration order.

    `committed_elsewhere` is empty and stated rather than defaulted: both designs are proposed
    at the same moment against the same estate and neither has been run, which is the only
    reading under which that argument is honest. The estate keeps no register of open
    experiments — `gold.experiment_assignment` records which units were assigned and carries no
    period, so *already committed* is not a question it can answer.
    """
    return [
        (
            declared,
            assess(
                declared.form(measured.categories),
                experiment_id=declared.experiment_id,
                seed=declared.seed,
                metric=measured.metric,
                metric_ids=measured.metric_ids,
                covariates=measured.contracts.balance_covariates,
                inference=measured.contracts.inference,
                roster=measured.roster,
                matrix=measured.matrix,
                variance_per_unit_week=measured.variance_per_unit_week,
                mean_per_unit_week=measured.mean_per_unit_week,
                committed_elsewhere=frozenset(),
                neighbour_pairs=measured.neighbours,
                stopping=declared.stopping,
                previously_locked=None,
            ),
        )
        for declared in DECLARED
    ]


def design(
    spark: SparkSession, *, scale: str, gold_schema: str = "gold", silver_schema: str = "silver"
) -> int:
    """Moment 1: assess both designs and write the lottery for every one that may exist.

    **This runs before the comparison window's data exists, and that is the whole guarantee.**
    `backfill` generates the baseline, builds it into gold, calls this, and only then generates
    the window under the arms this wrote. A design step that ran afterwards would be drawing a
    lottery with the outcome already on disk, which `pipelines/gold/assignment.py` refuses by
    date and which no amount of good faith would make into an experiment.
    """
    measured = measure(spark, scale=scale, gold_schema=gold_schema, silver_schema=silver_schema)
    written = 0
    print(f"design   roster {len(measured.roster)}  window opens {measured.period.opens_on}\n")
    for declared, verdict in _verdicts(measured):
        if isinstance(verdict, DesignRefusal):
            codes = ", ".join(reason.code.value for reason in verdict.reasons)
            print(f"  {declared.experiment_id:<26} REFUSED  {codes}")
            continue
        rows = assignment_table.write(
            spark,
            verdict.assignment,
            schema=gold_schema,
            assigned_at=measured.assigned_at,
            period_start=measured.period_weeks[0],
        )
        written += rows
        print(
            f"  {declared.experiment_id:<26} sealed   {verdict.treatment_size} treated, "
            f"{verdict.control_size} control, {len(verdict.automatic_exclusions)} excluded"
        )
    if not written:
        raise ExperimentError(
            "every declared design was refused, so no assignment was written and the comparison "
            "window has no arms to be generated under. A run with nothing to read out is not a "
            "run that refuses; it is one that never started."
        )
    return written


def readout(
    spark: SparkSession, *, scale: str, gold_schema: str = "gold", silver_schema: str = "silver"
) -> list[dict[str, Any]]:
    """Moment 3: one row per declared experiment, whichever moment answered it.

    Nothing is retried and no experiment is dropped. A design that refused produces a row saying
    so, at the same size as a row carrying a number — `evals/uplift/harness.py` refuses to
    discard a draw for the same reason, and the readout dashboard prints a refusal at the same
    size as an uplift.
    """
    measured = measure(spark, scale=scale, gold_schema=gold_schema, silver_schema=silver_schema)
    treatment_policy, control_policy = _policy_refs()
    outcomes = _outcomes(spark, measured)
    exposed, delivered, distinct_refs = _exposure(spark, silver_schema, measured.period_weeks)

    rows: list[dict[str, Any]] = []
    for declared, verdict in _verdicts(measured):
        if isinstance(verdict, DesignRefusal):
            rows.append(
                _row(
                    declared,
                    outcome=verdict,
                    moment="design",
                    data_version=measured.data_version,
                    period=(measured.period_weeks[0], measured.period_weeks[-1]),
                )
            )
            continue
        seal = verdict.assignment
        # **The table is checked against the seal rather than trusted.** `measure` is
        # deterministic, so re-deriving it here reproduces the lottery `design` drew; `verify`
        # is what says the rows on disk are that lottery and not something that replaced it.
        assignment_table.verify(spark, seal, schema=gold_schema)
        on_roster = frozenset(seal.roster)
        rows.append(
            _row(
                declared,
                outcome=close(
                    seal,
                    outcomes={u: v for u, v in outcomes.items() if u in on_roster},
                    exposed=frozenset(exposed & frozenset(seal.treatment)),
                    delivered={u: r for u, r in delivered.items() if u in on_roster},
                    treatment_policy=treatment_policy,
                    control_policy=control_policy,
                    covariates_at_close=measured.matrix.restricted_to(on_roster),
                    draws=reference_set(
                        seal,
                        draws=measured.contracts.inference.permutation_draws,
                        max_attempts=measured.contracts.inference.max_assignment_attempts,
                    ),
                    inference=measured.contracts.inference,
                    metric=measured.metric,
                    mde_absolute=verdict.mde_absolute,
                    direction=MdeDirection.EITHER,
                    form_digest=verdict.form_digest,
                    data_version=measured.data_version,
                    period=measured.period,
                    asked_on=measured.period.ends_on,
                ),
                moment="readout",
                data_version=measured.data_version,
                period=(measured.period_weeks[0], measured.period_weeks[-1]),
            )
        )
    _report(rows, distinct_refs)
    return rows


def _outcomes(spark: SparkSession, measured: Measured) -> dict[str, int]:
    """The unit outcome: the mean store-week over the comparison window, in cents."""
    over_window = _by_unit_week(spark, measured.table, measured.period_weeks)
    if not over_window:
        raise ExperimentError(
            f"{measured.table} holds nothing for the comparison window "
            f"{measured.period_weeks[0]}..{measured.period_weeks[-1]}. The window's days are "
            "generated under the committed assignment and loaded after `design` has run: if "
            "this is empty, that step has not happened."
        )
    return {
        unit: round(
            statistics.fmean([over_window.get((unit, week), 0) for week in measured.period_weeks])
        )
        for unit in measured.roster
    }


def _report(rows: Sequence[Mapping[str, Any]], distinct_refs: Mapping[str, int]) -> None:
    """What came out, printed at the same size whether it is a number or a refusal."""
    print(f"readout  {len(rows)} experiment(s)\n")
    for row in rows:
        if row["uplift"] is None:
            print(f"  {row['experiment_id']:<26} REFUSED  {row['reason_codes']}")
        else:
            print(
                f"  {row['experiment_id']:<26} uplift {row['uplift']:+.2f} cents "
                f"[{row['ci_low']:+d}, {row['ci_high']:+d}] p={row['p_value']:.4f}"
            )
    many = sorted(store for store, seen in distinct_refs.items() if seen > 1)
    if many:
        print(f"\n  {len(many)} store(s) saw more than one policy in the window: {many[:8]}")


def write(spark: SparkSession, rows: Sequence[Mapping[str, Any]], *, schema: str) -> int:
    """Replace `gold.readout` with this run's rows, and return how many were written."""
    spark.sql(f"create schema if not exists {schema}")
    frame = spark.createDataFrame([dict(row) for row in rows], SCHEMA)
    frame.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
        f"{schema}.{TABLE}"
    )
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    """`python -m pipelines.gold.experiments {design,readout} --scale …`"""
    import argparse

    from pipelines import session as runtime
    from pipelines.gold import session as gold_session

    parser = argparse.ArgumentParser(prog="pipelines.gold.experiments", description=__doc__)
    parser.add_argument("moment", choices=("design", "readout"))
    parser.add_argument("--scale", required=True, help="the corpus scale the estate loaded")
    parser.add_argument("--catalog")
    parser.add_argument("--gold-schema", default="gold")
    parser.add_argument("--silver-schema", default="silver")
    parser.add_argument("--root", type=Path, help="where a local session puts its warehouse")
    args = parser.parse_args(argv)

    spark = gold_session.build(args.root)
    try:
        runtime.use_catalog(spark, args.catalog)
        if args.moment == "design":
            design(
                spark,
                scale=args.scale,
                gold_schema=args.gold_schema,
                silver_schema=args.silver_schema,
            )
            return 0
        rows = readout(
            spark,
            scale=args.scale,
            gold_schema=args.gold_schema,
            silver_schema=args.silver_schema,
        )
        write(spark, rows, schema=args.gold_schema)
    finally:
        runtime.release(spark)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
