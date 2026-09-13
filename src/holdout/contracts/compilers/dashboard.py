"""The two AI/BI dashboards, compiled from the contracts rather than drawn in a console.

`CLAUDE.md`: *"No dashboard is built from a console. They are `databricks_dashboard` resources in
the `lakehouse` layer."* And: *"Both dashboards consume the metric contract, so they are part of
claim 5's evidence rather than decoration on top of it."*

**A fifth consumer, and the reason it has to be a compiled one is a measurement.** `T013`'s
stopping condition is *"when the definitions consume the metric contract and `terraform validate`
passes"*, and `terraform validate` cannot see the first half at all: `serialized_dashboard` is a
**string**, so a dashboard containing `select nonsense from table_that_does_not_exist where 1=`
validates clean — measured against the real provider before this file was written. So the
consumption is made structural instead: the readout dashboard's dataset SQL **is
`compile_readout(metric)`**, the same call the `generated/readout/` artefact is written from, and
`make contracts` byte-compares what lands on disk. Not a copy of the query — the query.

Where each number in these files comes from
-------------------------------------------
=========================  ==================================================================
the readout dataset SQL    `compile_readout(metric)` — the metric contract, one call
the four check tiles       `contracts/vocabularies/reason_codes.yaml`, `at_readout`, whose
                           every entry carries the `check` it belongs to
the refusal codes shown    the same four entries, by name
the guardrail breakdown    `at_decision`, all twelve, so the monitor's bar chart cannot
                           name a guardrail the envelope cannot fire
the metric's unit          the metric contract
=========================  ==================================================================

**Nothing here is typed by hand that a contract already declares**, which is the whole of rule 3
at this layer: a dashboard that re-expressed the metric would be a second definition wearing a
picture, and it is the definition consumers *cannot* be compared against that go wrong — the
screenshot is the one artefact nobody re-derives.

The columns of a table that does not exist
-------------------------------------------
The hero counter and the four check tiles read a readout **row**, and `gold.readout` does not
exist: `pipelines/gold/` builds two of family C's four tables and the rest are collected by a
running experiment, which is phase 3. So this file names columns for a table nobody has built.

**They are not invented.** `READOUT_COLUMNS` is the field list of
`holdout.core.experiment.readout.Readout` — the type the core already returns, which is what phase
3 will materialise — and `tests/contracts/test_dashboard.py` asserts the two agree in both
directions. That is the same arrangement `tests/core/test_refusal_codes.py` uses for the refusal
enums: three mechanisms, no imports between them, and a test that they say the same thing. This
module does not import `holdout.core`, because the contract layer never has.

**What is still missing is not a column, and it is filed rather than papered over**: nothing
*produces* such a row. `docs/FINDINGS.md` carries it — *the single most important screenshot in
the project has no data source, and the atom that names it that way cannot supply one.*
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from holdout.contracts.compilers.readout import compile_readout

if TYPE_CHECKING:
    from holdout.contracts.model import ContractSet, Metric

#: The columns of `gold.readout` **as the pipeline writes them** -- `pipelines/gold/experiments.py`'s
#: `SCHEMA`, in its order.
#:
#: **Until 2026-09-12 this was the field list of `holdout.core.experiment.readout.Readout`**, the
#: type, with a test that the two agreed in both directions -- and they did, while the table
#: nobody had built was built by `T022` in a different shape: the interval flattened to
#: `ci_low`/`ci_high`, the period to two dates, `alpha`, `statistic`, `balance` and `draw_index`
#: not carried, and `reason_code` added, because a refusal is a row too and the type has no field
#: for one. The screen's `verdict` dataset went on selecting `confidence_interval` and `alpha`
#: from a table with neither, and would have failed to draw on the first day anybody opened it.
#: Two projections of one thing -- the type and the table -- each compared with the compiler
#: and never with each other. **Found by `ops/inspect_estate.py`, written the day the author
#: asked whether the dashboards draw.**
#:
#: Written here rather than imported, because `holdout/contracts/` does not import
#: `pipelines/`; `tests/contracts/test_dashboard.py` compares this tuple with the pipeline's
#: `SCHEMA` in both directions, so a column the pipeline renames turns the build red here.
READOUT_COLUMNS: tuple[str, ...] = (
    "experiment_id",
    "moment",
    "metric_ref",
    "data_version",
    "period_opens_on",
    "period_ends_on",
    "seed",
    "uplift",
    "ci_low",
    "ci_high",
    "p_value",
    "draws",
    "reason_code",
    "reason_codes",
    "checks",
    "digest",
    "readout_at",
    "restates",
)

#: The metric the readout screen is built for. The primary metric of the experiments this project
#: defends, and the only one whose contract exercises two sources — the same choice
#: `evals/definition/` makes and for the same reason.
READOUT_METRIC = "category_margin_per_store_week"

#: Where the dashboards are compiled to. One file each, named the way the Lakeview format is.
READOUT_PATH = "generated/dashboards/experiment_readout.lvdash.json"
MONITOR_PATH = "generated/dashboards/decision_monitor.lvdash.json"

#: **The em dash is not cosmetic.** `tests/contracts/test_generated_artefacts.py` requires every
#: artefact under `generated/` to carry this exact string, so a hyphen here is a file that says it
#: is generated in a spelling nothing recognises. It went red on the first compile.
_BANNER = (
    "GENERATED FILE \u2014 DO NOT EDIT. Source: contracts/. Generator: "
    "holdout.contracts.compilers.dashboard. Regenerate: make contracts, which recompiles this "
    "file and fails the build if what is on disk differs."
)


class DashboardError(ValueError):
    """A dashboard that cannot be compiled without inventing something."""


def _dumps(document: dict[str, Any]) -> str:
    """One JSON shape for every dashboard artefact, so a diff is a change and never a reformat."""
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _readout_metric(contracts: ContractSet) -> Metric:
    from holdout.contracts.compilers import in_force_metrics

    for metric in in_force_metrics(contracts):
        if metric.id == READOUT_METRIC:
            return metric
    raise DashboardError(
        f"{READOUT_METRIC!r} is not an in-force metric, so the readout dashboard has no query. "
        "A screen compiled from a superseded definition would be a live artefact showing a "
        "retired number, which is what `in_force_metrics` exists to prevent."
    )


#: The parameters the compiled readout carries, each with the default a dashboard needs to run
#: at all. `data_version_*` are Delta versions and default to 0, the version every table has;
#: `experiment_id` defaults to the first experiment `pipelines/gold/experiments.py` declares;
#: the period bounds default to a window that matches nothing, so the screen opens empty rather
#: than on a slice nobody chose.
_PARAMETER_DEFAULTS: dict[str, tuple[str, str]] = {
    "experiment_id": ("STRING", "fresh-ladder"),
    "period_start": ("STRING", "1970-W01"),
    "period_end": ("STRING", "1970-W01"),
}


def _readout_parameters(query: str) -> list[dict[str, Any]]:
    """Every `:marker` in the compiled readout, declared the way Lakeview reads it."""
    import re

    markers = sorted(set(re.findall(r"(?<![:\w]):([A-Za-z_]\w*)", query)))
    declared: list[dict[str, Any]] = []
    for marker in markers:
        if marker.startswith("data_version_"):
            data_type, default = "INTEGER", "0"
        elif marker in _PARAMETER_DEFAULTS:
            data_type, default = _PARAMETER_DEFAULTS[marker]
        else:
            raise DashboardError(
                f"the compiled readout carries a parameter `:{marker}` this compiler has no "
                "default for, so the dashboard's dataset could not run. Declare it."
            )
        declared.append(
            {
                "displayName": marker,
                "keyword": marker,
                "dataType": data_type,
                "defaultSelection": {
                    "values": {"dataType": data_type, "values": [{"value": default}]}
                },
            }
        )
    return declared


def compile_readout_dashboard(contracts: ContractSet) -> str:
    """The experiment readout screen. Four check tiles, a hero counter, and the locked design.

    **The refusal is a first-class widget, not an error state.** `CLAUDE.md` calls the refused
    version *"the single most important screenshot in the project"*, and the hero counter is
    therefore declared over `coalesce(uplift, refusal)` rather than over the uplift with the
    refusal hidden behind a filter: a screen whose failure case is smaller than its success case
    teaches everyone to read only the successes.
    """
    metric = _readout_metric(contracts)
    checks = tuple(code for code in contracts.reason_codes.at_readout if code.check)
    if len(checks) != 4:
        raise DashboardError(
            f"{len(checks)} readout code(s) carry a `check`, and the screen has four tiles. "
            "The tiles are derived from the vocabulary rather than written here, so a fifth "
            "check is a contract change that must move this screen too."
        )

    document = {
        "_generated": _BANNER,
        "datasets": [
            {
                "name": "arm_metric",
                "displayName": f"{metric.ref} by arm",
                # **The compiled readout query itself.** Not a copy: the same call that writes
                # `generated/readout/`, so the screen and the readout cannot disagree about the
                # metric without `make contracts` going red.
                "queryLines": compile_readout(metric).splitlines(keepends=True),
                # **The compiled readout is parametrised, and a dashboard dataset that names a
                # parameter it does not declare cannot run at all** -- measured on 2026-09-12 by
                # `ops/inspect_estate.py`, which refuses to send such a query because the
                # warehouse's answer is the same sentence. So every marker the readout carries
                # is declared here, and the defaults are the one experiment and the tables'
                # first versions: a viewer types the pinned versions off the readout row, which
                # is the pin demonstrated rather than described.
                "parameters": _readout_parameters(compile_readout(metric)),
            },
            {
                "name": "verdict",
                "displayName": "The number, or the reason there is none",
                # Every readout row, every column the pipeline writes, and one derived column:
                # `verdict` is the uplift where there is one and the reason code where there is
                # not -- **one column for both cases**, which is what "at the same size" means
                # when it is a query rather than a sentence. No parameter: both experiments are
                # shown, because the screen exists to put the refusal beside the number.
                # **The newest row per experiment**, because the table appends and each row
                # names the one it restates (doctrine rule 4). The history is the table itself;
                # the verdict is its last word.
                "queryLines": [
                    "select\n",
                    "  coalesce(cast(uplift as string), reason_code) as verdict,\n",
                    *(f"  {column},\n" for column in READOUT_COLUMNS[:-1]),
                    f"  {READOUT_COLUMNS[-1]}\n",
                    "from (\n",
                    "  select *, row_number() over (partition by experiment_id order by "
                    "readout_at desc) as _rank\n",
                    "  from gold.readout\n",
                    ") where _rank = 1\n",
                    "order by experiment_id\n",
                ],
            },
        ],
        "pages": [
            {
                "name": "readout",
                "displayName": "Experiment readout",
                "layout": [
                    {
                        "widget": {
                            "name": f"check_{code.check}",
                            "textbox_spec": (
                                f"### {code.check}\n\n"
                                f"Refuses with **{code.code}**.\n\n{code.meaning}"
                            ),
                        },
                        "position": {"x": index * 3, "y": 0, "width": 3, "height": 3},
                    }
                    for index, code in enumerate(checks)
                ]
                + [
                    {
                        "widget": {
                            "name": "hero",
                            "textbox_spec": (
                                "## Uplift, or the refusal at the same size\n\n"
                                f"Metric **{metric.ref}**, unit **{metric.unit}**, rounded "
                                f"{metric.rounding.mode} to {metric.rounding.decimals} "
                                "decimals.\n\n"
                                "A refusal is a correct output. It is shown here at the size an "
                                "uplift would be, never as an empty chart."
                            ),
                        },
                        "position": {"x": 0, "y": 3, "width": 6, "height": 4},
                    },
                    {
                        "widget": {
                            "name": "verdicts",
                            "queries": [{"name": "main", "query": {"datasetName": "verdict"}}],
                            "spec": {
                                "version": 3,
                                "widgetType": "table",
                                "encodings": {
                                    "columns": [
                                        {"fieldName": column}
                                        for column in (
                                            "experiment_id",
                                            "verdict",
                                            "ci_low",
                                            "ci_high",
                                            "p_value",
                                            "reason_codes",
                                        )
                                    ]
                                },
                            },
                        },
                        "position": {"x": 0, "y": 7, "width": 12, "height": 3},
                    },
                    {
                        "widget": {
                            "name": "arms_by_week",
                            "queries": [{"name": "main", "query": {"datasetName": "arm_metric"}}],
                            "spec": {
                                "version": 3,
                                "widgetType": "line",
                                "encodings": {
                                    "x": {"fieldName": "iso_week", "scale": {"type": "temporal"}},
                                    "y": {
                                        "fieldName": "metric_value",
                                        "scale": {"type": "quantitative"},
                                    },
                                    "color": {"fieldName": "arm", "scale": {"type": "categorical"}},
                                },
                            },
                        },
                        "position": {"x": 6, "y": 3, "width": 6, "height": 4},
                    },
                    {
                        "widget": {
                            "name": "per_store_effect",
                            "queries": [{"name": "main", "query": {"datasetName": "arm_metric"}}],
                            "spec": {
                                "version": 3,
                                "widgetType": "histogram",
                                "encodings": {
                                    "x": {
                                        "fieldName": "metric_value",
                                        "scale": {"type": "quantitative"},
                                    }
                                },
                            },
                        },
                        "position": {"x": 0, "y": 10, "width": 6, "height": 4},
                    },
                    {
                        "widget": {
                            "name": "locked_design",
                            "queries": [{"name": "main", "query": {"datasetName": "verdict"}}],
                            "spec": {
                                "version": 3,
                                "widgetType": "table",
                                "encodings": {
                                    "columns": [
                                        {"fieldName": column}
                                        for column in (
                                            "experiment_id",
                                            "seed",
                                            "digest",
                                            "data_version",
                                            "period_opens_on",
                                            "period_ends_on",
                                        )
                                    ]
                                },
                            },
                        },
                        "position": {"x": 6, "y": 10, "width": 6, "height": 4},
                    },
                ],
            }
        ],
    }
    return _dumps(document)


def compile_decision_monitor(contracts: ContractSet) -> str:
    """The decision monitor. Required by doctrine rule 2, not optional.

    *"A fallback is visible to the actuator, the record **and the dashboard**. Without this
    screen, rule 2 is proved nowhere."* So the load-bearing widget is the stacked area of model /
    fallback / refusal over the day, and the guardrail breakdown names **every** decision-time
    code — all twelve, from the vocabulary — rather than the handful somebody remembered.
    """
    codes = contracts.reason_codes.at_decision
    if not codes:
        raise DashboardError(
            "the decision vocabulary is empty, so the monitor's refusal table would be a chart "
            "of nothing that renders green."
        )
    listed = "\n".join(f"- `{code.code}` — {code.guardrail or 'any'}" for code in codes)

    document = {
        "_generated": _BANNER,
        "datasets": [
            {
                "name": "decisions_today",
                "displayName": "Decisions, by outcome and hour",
                # **The day driven, not the calendar's today.** `where decided_at >=
                # current_date()` read as a live monitor and drew nothing: the live day `run`
                # drives is a day of the corpus, and the record's newest day is the one the
                # screen is about. Measured on run 34676694580, one layer above this -- the
                # table itself was not there -- and corrected with it.
                "queryLines": [
                    "select\n",
                    "  date_trunc('hour', decided_at) as hour,\n",
                    "  outcome,\n",
                    "  marker,\n",
                    "  reason_code,\n",
                    "  count(*) as decisions\n",
                    "from gold.decisions\n",
                    "where date(decided_at) = (select max(date(decided_at)) from gold.decisions)\n",
                    "group by 1, 2, 3, 4\n",
                ],
            }
        ],
        "pages": [
            {
                "name": "monitor",
                "displayName": "Decision monitor",
                "layout": [
                    {
                        "widget": {
                            "name": "outcome_over_the_day",
                            "queries": [
                                {"name": "main", "query": {"datasetName": "decisions_today"}}
                            ],
                            "spec": {
                                "version": 3,
                                "widgetType": "area",
                                "encodings": {
                                    "x": {"fieldName": "hour", "scale": {"type": "temporal"}},
                                    "y": {
                                        "fieldName": "decisions",
                                        "scale": {"type": "quantitative"},
                                    },
                                    "color": {
                                        "fieldName": "outcome",
                                        "scale": {"type": "categorical"},
                                    },
                                },
                            },
                        },
                        "position": {"x": 0, "y": 0, "width": 12, "height": 5},
                    },
                    {
                        "widget": {
                            "name": "which_guardrails_fired",
                            "queries": [
                                {"name": "main", "query": {"datasetName": "decisions_today"}}
                            ],
                            "spec": {
                                "version": 3,
                                "widgetType": "bar",
                                "encodings": {
                                    "x": {
                                        "fieldName": "reason_code",
                                        "scale": {"type": "categorical"},
                                    },
                                    "y": {
                                        "fieldName": "decisions",
                                        "scale": {"type": "quantitative"},
                                    },
                                },
                            },
                        },
                        "position": {"x": 0, "y": 5, "width": 6, "height": 5},
                    },
                    {
                        "widget": {
                            "name": "the_closed_vocabulary",
                            "textbox_spec": (
                                "### Every refusal a decision can carry\n\n"
                                "Compiled from `contracts/vocabularies/reason_codes.yaml`. A "
                                "code that is not here cannot be emitted, and a code emitted "
                                "that is not here is a contract change.\n\n" + listed
                            ),
                        },
                        "position": {"x": 6, "y": 5, "width": 6, "height": 5},
                    },
                ],
            }
        ],
    }
    return _dumps(document)
