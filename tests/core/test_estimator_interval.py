"""The optimised interval against the one it replaced — bit-identical bounds, or abandoned.

`estimator.interval` used to re-fit two normal systems per draw per candidate shift. It now
precomputes each draw's statistic as a polynomial in the shift, which is exact algebra and
seventeen times faster on the harness's own inputs. The search is deliberately unchanged, so
the guard can be an **equality** rather than an argument: the same brackets, the same
bisection, the same termination — only the cost of asking changes.

**The refitting implementation is kept here, in full, as the oracle**, for the length of the
branch that replaced it. It is not a paraphrase and it is not the new code with a flag: it is
the function as it stood, so that a difference between the two is a difference between
refitting and algebra rather than between two readings of the same code.

**Whose cases are these.** `CLAUDE.md`'s checklist asks who wrote the case a guard is tested
on, because a guard tested by its author is tested in the shape the author already handles.
The answer here is the lottery and the corpus: the outcomes come from a world this repository
generates and the assignments from the committed-seed draw, so neither the arm split nor the
spread of the outcomes was chosen by whoever wrote the algebra. The hand-built cases beside
them exist for the shapes a corpus does not reliably produce — a degenerate arm, a covariate
with no spread, an outcome vector with no variation at all.

**If the bounds ever differ, the optimisation is abandoned rather than argued with.** That is
the SPEC's own instruction and it is repeated here because this file is where it would be
noticed.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from fractions import Fraction

import pytest
from corpus.world import alternating, prepare
from corpus.world.scale import REHEARSAL
from evals.uplift import outcomes as grouped

from holdout.contracts.model import ContractSet
from holdout.core.experiment import (
    Arm,
    CovariateKind,
    CovariateMatrix,
    ReferencePlan,
    design_of,
    draw,
    interval,
    plan_for,
    reference_set,
)
from holdout.core.experiment import estimator as estimator_module

#: Small enough that the refitting oracle is affordable in the suite, large enough that the
#: bisection takes real steps. B buys resolution and not validity, so the comparison is as
#: sharp at 99 draws as at the contract's thousand — and the oracle costs B x steps refits.
ORACLE_DRAWS = 99

ALPHA = Decimal("0.05")


# ------------------------------------------------------------------ the oracle, verbatim


def interval_by_refitting(
    outcomes: Mapping[str, int],
    arms: Mapping[str, Arm],
    plan: ReferencePlan,
    *,
    alpha: Decimal,
) -> tuple[int, int]:
    """`estimator.interval` as it stood before the algebra — two refits per draw per shift."""
    level = Fraction(alpha)
    treatment, control = estimator_module._split(plan.design, arms)
    treated = frozenset(plan.design.units[i] for i in treatment)
    values = [Fraction(outcomes[u]) for u in plan.design.units]
    point = estimator_module._statistic(
        estimator_module._arm_plan(plan.design, treatment),
        estimator_module._arm_plan(plan.design, control),
        plan.design,
        plan.grand_mean,
        values,
    ).difference

    def accepts(tau: int) -> bool:
        shift = Fraction(tau)
        shifted = [
            value - (shift if unit in treated else Fraction(0))
            for unit, value in zip(plan.design.units, values, strict=True)
        ]
        observed = estimator_module._statistic(
            estimator_module._arm_plan(plan.design, treatment),
            estimator_module._arm_plan(plan.design, control),
            plan.design,
            plan.grand_mean,
            shifted,
        )
        hits = sum(
            1
            for t, c in plan.plans
            if estimator_module._as_extreme(
                estimator_module._statistic(t, c, plan.design, plan.grand_mean, shifted),
                observed,
                estimator_module.MdeDirection.EITHER,
            )
        )
        return Fraction(1 + hits, 1 + plan.size) > level

    centre = estimator_module._nearest_integer(point)
    if not accepts(centre):
        raise estimator_module.EstimatorError("the test rejects its own point estimate")
    spread = max(values) - min(values) if values else Fraction(0)
    reach = (
        estimator_module._nearest_integer(spread * estimator_module.BRACKET_SPANS)
        + estimator_module.BRACKET_SPANS
    )
    return (
        estimator_module._edge(accepts, centre, step=-1, reach=reach),
        estimator_module._edge(accepts, centre, step=1, reach=reach),
    )


# ------------------------------------------------------------------ the cases


Case = tuple[str, CovariateMatrix, dict[str, int]]


def _matrix(rows: Mapping[str, tuple[Fraction | str, ...]]) -> CovariateMatrix:
    return CovariateMatrix.of(
        ("revenue", "format", "size"),
        (CovariateKind.NUMERIC, CovariateKind.CATEGORICAL, CovariateKind.NUMERIC),
        rows,
    )


def _corpus_case(contracts: ContractSet) -> Case:
    """A world, aggregated to unit outcomes — inputs nobody in this repository picked.

    The rehearsal scale, because the oracle is quadratic in what it is handed and this is a
    test of an algebraic identity rather than of a scale. What matters is that the numbers are
    a chain's takings rather than a sequence somebody typed: their spread, their skew and the
    ratio between the arms are all the corpus's.
    """
    metric = contracts.metric_versions("category_margin_per_store_week")[-1]
    run = prepare("W6", seed="oracle", scale=REHEARSAL, assignment=None)
    ledger = grouped.collect(
        prepare("W6", seed="oracle", scale=REHEARSAL, assignment=alternating(run.chain))
    )
    weeks = ledger.weeks
    units = ledger.units
    values = grouped.window_mean(
        grouped.unit_weeks(ledger, metric.rounding),
        units=units,
        weeks=weeks,
        rounding=metric.rounding,
    )
    rows: Mapping[str, tuple[Fraction | str, ...]] = {
        store.store_id: (
            Fraction(round(store.size_index * 100_000)),
            store.store_format,
            Fraction(round(store.size_index * 1_000)),
        )
        for store in run.chain.stores
    }
    return "corpus/W6@rehearsal", _matrix(rows), values


def _hand_built() -> list[Case]:
    """The shapes a corpus does not reliably produce, built here and said to be built here."""
    formats = ("hypermarket", "supermarket", "convenience")
    plain: Mapping[str, tuple[Fraction | str, ...]] = {
        f"unit-{i:02d}": (Fraction(1_000 + 37 * i), formats[i % 3], Fraction(200 + 11 * (i % 5)))
        for i in range(40)
    }
    flat: Mapping[str, tuple[Fraction | str, ...]] = {
        f"unit-{i:02d}": (Fraction(500), formats[i % 3], Fraction(80)) for i in range(40)
    }
    return [
        ("spread outcomes", _matrix(plain), {u: 1_000 + 91 * i for i, u in enumerate(plain)}),
        (
            "one big outlier",
            _matrix(plain),
            {u: (900_000 if i == 3 else 400) for i, u in enumerate(plain)},
        ),
        ("negative outcomes", _matrix(plain), {u: -5_000 + 211 * i for i, u in enumerate(plain)}),
        ("covariates with no spread", _matrix(flat), {u: 700 + 13 * i for i, u in enumerate(flat)}),
        (
            "ties everywhere",
            _matrix(plain),
            {u: (100 if i % 2 else 140) for i, u in enumerate(plain)},
        ),
    ]


def _bounds(
    matrix: CovariateMatrix, values: dict[str, int]
) -> tuple[tuple[int, int], tuple[int, int]]:
    drawn = draw(
        experiment_id="oracle",
        roster=matrix.units,
        seed="oracle-seed",
        form_digest="oracle-form",
        matrix=matrix,
        # Wide enough that the smaller arm has degrees of freedom left after the
        # adjustment: the design here is five columns including the intercept, and an arm
        # of five would leave `_statistic` nothing to estimate a variance from.
        control_size=max(8, len(matrix.units) // 4),
    )
    assert drawn is not None
    seal, _balance = drawn
    draws = reference_set(seal, draws=ORACLE_DRAWS, max_attempts=ORACLE_DRAWS * 20)
    plan = plan_for(design_of(matrix), draws)
    optimised = interval(values, seal.arms, plan, alpha=ALPHA)
    refitted = interval_by_refitting(values, seal.arms, plan, alpha=ALPHA)
    return optimised, refitted


@pytest.mark.parametrize("case", _hand_built(), ids=lambda c: c[0])
def test_the_algebra_reproduces_the_refits_bit_for_bit(case: Case) -> None:
    _name, matrix, values = case
    optimised, refitted = _bounds(matrix, values)
    assert optimised == refitted, (
        f"the optimised interval returned {optimised} and refitting returns {refitted}. The "
        "algebra does not reproduce the search it replaced, so it is abandoned rather than "
        "argued with — that is the SPEC's instruction and this is the test that would notice"
    )


def test_the_algebra_reproduces_the_refits_on_a_world_nobody_chose(
    contracts: ContractSet,
) -> None:
    """The same equality on outcomes drawn from the corpus rather than written here."""
    _name, matrix, values = _corpus_case(contracts)
    optimised, refitted = _bounds(matrix, values)
    assert optimised == refitted, (
        f"{optimised} against {refitted} on a world this repository generated. See above"
    )


def test_a_draw_that_covers_less_than_the_design_takes_the_other_path() -> None:
    """The complement identity's condition, exercised rather than assumed.

    `XᵀX` over one arm is the whole minus the other arm **only where the two partition the
    design**. Nothing in this package produces a draw that covers less than the design today —
    `close` builds both over the units that reported — but `plan_for` is public, and a design
    row belonging to neither arm would otherwise be attributed to the larger one in silence.
    So the fallback is driven here, by a draw with a unit deliberately left out, and it has to
    give the same bounds as refitting like every other case.
    """
    _name, matrix, values = _hand_built()[0]
    drawn = draw(
        experiment_id="oracle",
        roster=matrix.units,
        seed="oracle-seed",
        form_digest="oracle-form",
        matrix=matrix,
        control_size=max(8, len(matrix.units) // 4),
    )
    assert drawn is not None
    seal, _balance = drawn
    full = reference_set(seal, draws=ORACLE_DRAWS, max_attempts=ORACLE_DRAWS * 20)
    absent = seal.roster[-1]
    partial = [{u: a for u, a in candidate.items() if u != absent} for candidate in full]
    assert any(absent not in candidate for candidate in partial)
    plan = plan_for(design_of(matrix), partial)
    optimised = interval(values, seal.arms, plan, alpha=ALPHA)
    refitted = interval_by_refitting(values, seal.arms, plan, alpha=ALPHA)
    assert optimised == refitted, (
        f"{optimised} against {refitted} on draws that do not partition the design — the "
        "complement identity was applied where its condition does not hold"
    )


def test_the_oracle_is_not_the_thing_it_is_testing() -> None:
    """A guard that called the code under test would agree with it for free.

    Cheap and worth writing down: the oracle's own body must not reach `interval`. It is
    the one way this file could pass while proving nothing at all.
    """
    import inspect

    body = inspect.getsource(interval_by_refitting)
    assert "interval(" not in body
    assert "_shifted" not in body
