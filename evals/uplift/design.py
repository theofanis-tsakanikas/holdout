"""The one design form, and the facts moment 1 needs measured out of the pre-period.

**One form for every world.** Same hypothesis shape, same metric, `unit: store`, the same MDE
read out of the contract, the same `max_duration`, the same `decision_rule`, the same
`filled_by`. A per-world form would be a per-world degree of freedom, and the whole argument
of this eval is that the machinery does not know which world it is in.

Three things the engine cannot invent and this module therefore measures, all of them from the
**pre-period only** — the eight weeks before the comparison window opens, which is the lookback
`contracts/design/balance_covariates.yaml` declares:

- the **covariate matrix**, in the contract's own column order;
- `mean_per_unit_week`, which turns a relative MDE into an absolute one;
- `variance_per_unit_week`, which is what the power calculation sizes on.

The pre-period is read off the **all-control** generation, and that is the point rather than a
convenience: a pre-period precedes the experiment, so every store is on the existing policy in
it. Reading it off the draw's own world would make the covariates a function of the lottery,
which is the same data twice and the thing `balance_covariates.yaml` exists to forbid.

What `variance_per_unit_week` is, said plainly
----------------------------------------------
The design's power calculation is a normal approximation over `s² / W`, so `s²` has to be the
variance of a unit-week **around that unit's own level** — the part a longer window averages
away. This module supplies the mean within-unit week-to-week variance over the pre-period, and
that is a **modelling assumption**: it says the covariate adjustment removes the between-unit
level, which on this corpus it very nearly does, because `category_revenue_8w` is essentially
the store's size and the estimator adjusts on it.

It is declared here rather than hidden because it is exactly the assumption W5 exists to
break, and because the readout's power check is judged on the **realised** variance regardless
of what this supplied. A design sized on an assumption and read out on a measurement is the
honest arrangement; the two disagreeing is a refusal, not a wrong number.

The covariate values are integers, and that is arithmetic rather than taste
---------------------------------------------------------------------------
`waste_rate` is a ratio and would arrive as a `Fraction` with a seven-digit denominator, which
the estimator would then square and sum a thousand times per readout. It is expressed in parts
per million instead. Nothing downstream can see the difference: the standardised difference is
scale-invariant, the composite distance divides by the covariate's own variance, and a linear
adjustment is unchanged by scaling a column. What changes is that the arithmetic stays in small
integers, and that is worth minutes.

The same argument covers `store_size_sqm`: the corpus records a store's size as an **index**
rather than an area, so it is read as a size in metres by a declared scaling. Every use of it
is scale-invariant, so the constant cannot move a number — only the units the figure is printed
in, and it is not printed.
"""

from __future__ import annotations

import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from corpus.world import Run

from evals.uplift.outcomes import Week
from holdout.contracts.model import AaHarness, BalanceCovariates
from holdout.core.design import (
    DecisionRule,
    DesignForm,
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
)
from holdout.core.experiment import CovariateKind, CovariateMatrix

#: The comparison window the harness declares, in ISO weeks. It is `max_duration`, and the
#: `HARNESS` scale carries exactly twice it: eight weeks of pre-period for the covariates'
#: declared lookback, then eight of experiment. An **even** window is also what makes the unit
#: outcome's mean a place where the metric's rounding decides a cent rather than a place where
#: half_even and half_up cannot differ.
PERIOD_WEEKS = 8

#: The covariates' declared lookback. The same eight, and they are the same eight on purpose.
PRE_PERIOD_WEEKS = 8

#: Parts per million, for `waste_rate`. See the module docstring: scale-invariant everywhere it
#: is used, and worth minutes in the estimator's inner loop.
WASTE_RATE_SCALE = 1_000_000

#: The corpus records a store's size as an index around 1.0, not as an area.
SIZE_INDEX_TO_SQM = 1_000

STOPPING = StoppingRule(kind=StoppingKind.SINGLE_READOUT_AT_END)


class DesignError(ValueError):
    """The world cannot supply what a design form has to be measured against."""


@dataclass(frozen=True, slots=True)
class PrePeriod:
    """Everything moment 1 is handed, measured before the comparison window opens."""

    matrix: CovariateMatrix
    mean_per_unit_week: Decimal
    variance_per_unit_week: Decimal
    pre_weeks: tuple[Week, ...]
    period_weeks: tuple[Week, ...]


def split_weeks(weeks: Sequence[Week]) -> tuple[tuple[Week, ...], tuple[Week, ...]]:
    """The pre-period and the comparison window, from the world's own calendar.

    The last `PERIOD_WEEKS` are the window and the `PRE_PERIOD_WEEKS` before them are the
    lookback. A world too short to carry both is refused rather than silently given a shorter
    pre-period: a covariate declared over eight weeks and measured over three is a covariate
    that says something other than what the contract says it says.
    """
    needed = PRE_PERIOD_WEEKS + PERIOD_WEEKS
    if len(weeks) < needed:
        raise DesignError(
            f"the world spans {len(weeks)} ISO week(s) and the design needs {needed}: "
            f"{PRE_PERIOD_WEEKS} of pre-period for the covariates' declared lookback and "
            f"{PERIOD_WEEKS} of comparison window. A shorter pre-period would be a covariate "
            "measured over something other than what the contract declares."
        )
    ordered = tuple(sorted(weeks))
    period = ordered[-PERIOD_WEEKS:]
    return ordered[-needed:-PERIOD_WEEKS], period


def pre_period(
    run: Run,
    *,
    by_unit_week: Mapping[tuple[str, Week], int],
    revenue_by_unit: Mapping[str, int],
    cogs_by_unit: Mapping[str, int],
    waste_by_unit: Mapping[str, int],
    weeks: Sequence[Week],
    covariates: BalanceCovariates,
) -> PrePeriod:
    """Measure the five declared covariates and the two sizing figures over the pre-period."""
    pre, period = split_weeks(weeks)
    units = tuple(sorted({unit for unit, _week in by_unit_week}))
    stores = {store.store_id: store for store in run.chain.stores}
    rows: dict[str, tuple[Fraction | str, ...]] = {}
    for unit in units:
        store = stores[unit]
        cogs = cogs_by_unit.get(unit, 0)
        waste_rate = (
            Fraction(round(waste_by_unit.get(unit, 0) * WASTE_RATE_SCALE / cogs))
            if cogs
            else Fraction(0)
        )
        rows[unit] = (
            Fraction(revenue_by_unit.get(unit, 0)),
            store.store_format,
            Fraction(round(store.size_index * SIZE_INDEX_TO_SQM)),
            waste_rate,
            store.pricing_zone,
        )
    matrix = CovariateMatrix.of(
        covariates.ids,
        tuple(CovariateKind(c.type) for c in covariates.covariates),
        rows,
    )
    per_unit = {unit: [by_unit_week.get((unit, week), 0) for week in pre] for unit in units}
    mean = statistics.fmean(statistics.fmean(values) for values in per_unit.values())
    within = statistics.fmean(statistics.variance(values) for values in per_unit.values())
    if mean <= 0:
        raise DesignError(
            f"the pre-period mean per unit-week is {mean}. A relative MDE against a "
            "non-positive mean is not a difference anybody could detect."
        )
    return PrePeriod(
        matrix=matrix,
        mean_per_unit_week=Decimal(round(mean)),
        variance_per_unit_week=Decimal(round(within)),
        pre_weeks=pre,
        period_weeks=period,
    )


def form(
    *,
    harness: AaHarness,
    categories: Sequence[str],
    treatment_policy: str,
    control_policy: str,
) -> DesignForm:
    """The nine fields, filled once, for every world.

    `filled_by` is `policy:aa_harness` and the engine does not read it — one identical form
    under all three attributions gives three identical results, which `tests/core/` asserts.
    It is recorded because a design that could not say who filled it is a design nobody signed.

    **The intervention names the policies the corpus actually delivers**, so the contamination
    check compares a declared arm against a delivered one rather than against itself. The
    treatment arm's ref is `corpus/world/policy.candidate`'s, which is **not** a version in
    `contracts/policies/` — a gap recorded as a deferral in `docs/DECISIONS.md` rather than
    papered over, and one the engine does not currently look for.
    """
    return DesignForm(
        hypothesis=(
            "A shallower fresh markdown ladder raises category margin per store-week, because "
            "the trade given away at the deeper rungs is worth more than the waste it avoids."
        ),
        intervention=Intervention(treatment=treatment_policy, control=control_policy),
        scope=Scope(categories=tuple(categories), products=None, stores=None),
        primary_metric="category_margin_per_store_week",
        unit=Unit.STORE,
        mde=Mde(
            kind=MdeKind.RELATIVE_PCT,
            value=harness.mde_pct_of_pre_period_mean,
            direction=MdeDirection.EITHER,
        ),
        max_duration=MaxDuration(weeks=PERIOD_WEEKS),
        exclusions=(),
        decision_rule=DecisionRule(
            if_significant="Roll the candidate ladder out across the fresh estate.",
            if_not_significant="Keep the existing ladder and close the experiment.",
            if_refused="Publish the reason code and re-open the design against what it names.",
        ),
        filled_by=FilledBy(kind=FilledByKind.POLICY, name="aa_harness"),
    )
