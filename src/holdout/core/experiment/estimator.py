"""The number, and whether it may be stated. Everything here is exact.

**Outcomes arrive as integers at the metric's declared scale** — the `canonical_integer` the
metric contract's `Rounding` already produces — so every sum is an exact integer and the only
division is into a mean, taken in `Fraction`. There is no tolerance anywhere in this module,
for the same reason `Money` is integer cents: a tolerance is a place for a disagreement to
hide, and claim 5 compares consumers with none.

Four decisions, and each is here rather than in a comment because each changes the answer.

**The adjustment is Lin's estimator.** Covariates centred and interacted with the arm, which
is algebraically the same as fitting the covariates *within each arm* and comparing the two
fitted values at the grand mean — and that is how it is computed here, because two `k × k`
systems are cheaper than one `2k × 2k` and exactly as exact. The property that makes Lin's
worth the machinery: a misspecified adjustment cannot make the estimate *worse* than the
unadjusted difference in large samples, so adjusting is never a gamble on the model being
right. Categoricals are one-hot with a reference level, and the reference is the
lexicographically first, so it is the same level on every machine.

**The normal equations are solved by exact Gaussian elimination over `Fraction`.** Five
covariates is roughly eight columns over a hundred rows, and `fractions` is standard library.
No numpy, no floats, and the adjusted estimate is bit-identical everywhere. Where a column
turns out to be a linear combination of the ones before it — a categorical level that no unit
in one arm happens to take is the ordinary way — that column is **dropped and its coefficient
set to zero**, which is a genuine least-squares solution and not an approximation of one: a
dependent column adds nothing to the column space, so the fitted values and the residuals are
unchanged. Which columns get dropped is decided in column order, so it is deterministic.

**The statistic is studentized and compared as a square.** ``T² = τ̂² / (s²_T/n_T + s²_C/n_C)``
over the adjusted residuals, exact in `Fraction`, so the hot loop takes no square root at
all — `Decimal.sqrt()` appears once, for the `T` a human reads. The reason for studentizing
is the null being tested: the **weak (Neyman) null** of no *average* effect, not the sharp
null of no effect for any unit. A raw difference of means is exact only under the sharp null,
and W5 — heavy-tailed baskets, unequal arm variance — is precisely where that distinction
stops being pedantic.

**The p-value is** ``(1 + #{T²_b ≥ T²_obs}) / (1 + B)`` over draws taken under the same
restriction — the strata the realised assignment was drawn within. Exact at any B: B buys
resolution, not validity, and the readout prints B beside the p-value so nobody has to
guess which it was.

The interval inverts the same test
----------------------------------
Over ``y_i - τ·1{arm = T}``, by bisection on each side of the point estimate, with brackets
found by doubling and termination at **one canonical metric unit** — so both endpoints are
integers in the metric's own unit, with no tolerance and nothing to round. Coverage is then
correct by construction rather than by asymptotics.

The same draws are reused at every step, which is what keeps the cost at about B rather than
B × steps. They are handed around as a `ReferencePlan` rather than as a bare tuple, because
the expensive half of each draw — the arm split and the factorisation of its normal equations
— depends on the covariates and not on the outcomes, so it is computed once and reused at
every shift. That is the same reuse the SPEC asks for, made structural instead of hoped for.

**The interval is two-sided even where the MDE declared a direction.** A one-sided test
paired with a two-sided interval is not an inconsistency to apologise for: the test answers
the question the design asked, and the interval answers *what values of the effect are
consistent with the data*, which has no direction in it.

Two things this module assumes, said out loud
---------------------------------------------
**Bisection assumes the acceptance region is an interval.** ``{τ : p(τ) > α}`` is an interval
for every well-behaved statistic and is not guaranteed to be one in general. Where it is not,
bisection finds *an* endpoint of the region containing the point estimate rather than the
outermost one, which errs narrow. Nothing here detects that, and saying so is cheaper than
pretending a grid search over every integer would have been affordable.

**Validity comes from the lottery, not from this arithmetic.** A difference of means over
randomly assigned units is unbiased under any data-generating process — that is a theorem,
not an opinion held here. What the tests in this branch defend is the machinery around it.
Whether the machinery preserves that validity is claim 2, and claim 2 is measured at K = 200
seeds across six adversarial worlds, not asserted in a docstring.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from holdout.core.design.form import MdeDirection
from holdout.core.experiment.balance import CovariateKind, CovariateMatrix
from holdout.core.experiment.codes import Arm
from holdout.core.money import decimal_of

#: How far the doubling search may go past the spread of the outcomes before it concludes
#: that no shift is ever rejected. Generous, because the point is to fail loudly on an input
#: nobody expected rather than to run forever: as the shift grows the observed statistic
#: grows without bound while the permuted ones do not, so a real dataset always rejects.
BRACKET_SPANS = 64


class EstimatorError(ValueError):
    """The estimator was asked for a number it cannot compute. Never a refusal: a refusal is
    a correct output about an experiment, and this says the arithmetic was handed nonsense."""


# ------------------------------------------------------------------ the design matrix


@dataclass(frozen=True, slots=True)
class Design:
    """The covariates as a numeric matrix, one row per unit, in a fixed column order.

    Built once from a `CovariateMatrix`. Categoricals are expanded to one-hot indicators
    with the lexicographically first level dropped as the reference — dropped rather than
    kept, because keeping every level makes the intercept a linear combination of them and
    the normal equations rank-deficient by construction.
    """

    units: tuple[str, ...]
    columns: tuple[str, ...]
    rows: tuple[tuple[Fraction, ...], ...]

    @property
    def width(self) -> int:
        """Columns including the intercept — the size of one arm's normal equations."""
        return len(self.columns) + 1

    def index_of(self, unit: str) -> int:
        return self.units.index(unit)


def design_of(matrix: CovariateMatrix) -> Design:
    """Expand a covariate matrix into the numeric design the estimator adjusts on."""
    units = matrix.units
    columns: list[str] = []
    getters: list[list[Fraction]] = []
    for index, covariate_id in enumerate(matrix.ids):
        if matrix.kinds[index] is CovariateKind.NUMERIC:
            columns.append(covariate_id)
            getters.append([_numeric(matrix, unit, index) for unit in units])
            continue
        levels = matrix.levels(covariate_id)
        for level in levels[1:]:
            columns.append(f"{covariate_id}={level}")
            getters.append(
                [
                    Fraction(1) if matrix.rows[unit][index] == level else Fraction(0)
                    for unit in units
                ]
            )
    rows = tuple(tuple(column[row] for column in getters) for row in range(len(units)))
    return Design(units=units, columns=tuple(columns), rows=rows)


def _numeric(matrix: CovariateMatrix, unit: str, index: int) -> Fraction:
    value = matrix.rows[unit][index]
    assert isinstance(value, Fraction)  # enforced by CovariateMatrix.of
    return value


def _grand_mean(design: Design) -> tuple[Fraction, ...]:
    n = len(design.units)
    if n == 0:
        raise EstimatorError("a design over no units")
    return tuple(
        sum((row[j] for row in design.rows), Fraction(0)) / n for j in range(len(design.columns))
    )


# ------------------------------------------------------------------ the statistic


@dataclass(frozen=True, slots=True)
class Statistic:
    """The adjusted difference and its studentized square.

    `squared` is `None` where the arms differ and the adjusted residuals have no spread at
    all: `T` is unbounded, not large, and every comparison here reads `None` as exceeding
    any finite value. The SPEC's `tuple[Fraction, int]` had nowhere to put that case, and it
    is a real one — a small arm whose covariates fit it exactly is not exotic.
    """

    difference: Fraction
    variance: Fraction
    squared: Fraction | None
    sign: int

    @property
    def standard_error(self) -> Decimal:
        """`sqrt(s²_T/n_T + s²_C/n_C)` — what the realised power is judged against.

        The design's power calculation believed a variance somebody supplied from history.
        This is the one the world actually supplied, and W5 is the world where the two are
        not the same number.
        """
        return decimal_of(self.variance).sqrt()

    def detects(self, mde_absolute: Fraction, z_sum: Fraction) -> bool:
        """Whether the realised standard error is small enough to detect the declared MDE.

        `d >= (z_alpha + z_beta) * se`, compared as squares so no square root is taken and
        no tolerance is introduced. It is the design's own sizing arithmetic, run again on
        the variance that actually arrived instead of the one that was assumed.
        """
        return mde_absolute * mde_absolute >= z_sum * z_sum * self.variance

    @property
    def value(self) -> Decimal | None:
        """`T` itself, signed — the only square root in the module."""
        if self.squared is None:
            return None
        magnitude = decimal_of(self.squared).sqrt()
        return magnitude if self.sign >= 0 else -magnitude


@dataclass(frozen=True, slots=True)
class _ArmPlan:
    """One arm of one draw: which rows, and the solved normal equations for them.

    Everything in it depends on the covariates and the arm split and **not** on the
    outcomes, so it survives every shift of the interval's bisection unchanged. That is
    where the cost of inverting the interval actually goes.
    """

    rows: tuple[int, ...]
    solve: tuple[tuple[Fraction, ...], ...]
    rank: int


@dataclass(frozen=True, slots=True)
class ReferencePlan:
    """The reference set, with everything that does not depend on the outcomes precomputed.

    `draws` is what `assignment.reference_set` returned; `plans` is one `(treatment,
    control)` pair per draw. Built once per experiment and reused at every step of the
    interval's bisection.
    """

    design: Design
    grand_mean: tuple[Fraction, ...]
    plans: tuple[tuple[_ArmPlan, _ArmPlan], ...]

    @property
    def size(self) -> int:
        """B, as actually accepted. The p-value divides by this and the readout prints it,
        so a reference set that came up short of the declared draws is a number on the
        report rather than a footnote."""
        return len(self.plans)


# ------------------------------------------------------------------ exact linear algebra


def _solve_matrix(a: list[list[Fraction]]) -> tuple[tuple[tuple[Fraction, ...], ...], int]:
    """`S` such that `β = S·b` solves `Aβ = b`, with dependent columns set to zero.

    Gauss-Jordan on `[A | I]` in column order. A column whose pivot is zero after
    elimination is a linear combination of the ones before it; its coefficient is set to
    zero, which leaves the fitted values and the residuals exactly where they were because
    it adds nothing to the column space. Column order rather than magnitude order, so which
    column gets dropped is decided by the design's declared layout and not by the data.
    """
    size = len(a)
    work = [
        [*row, *(Fraction(1) if i == j else Fraction(0) for j in range(size))]
        for i, row in enumerate(a)
    ]
    retained: list[tuple[int, int]] = []
    row = 0
    for column in range(size):
        pivot = next((r for r in range(row, size) if work[r][column] != 0), None)
        if pivot is None:
            continue
        work[row], work[pivot] = work[pivot], work[row]
        scale = 1 / work[row][column]
        work[row] = [value * scale for value in work[row]]
        for other in range(size):
            if other != row and work[other][column] != 0:
                factor = work[other][column]
                work[other] = [
                    value - factor * head
                    for value, head in zip(work[other], work[row], strict=True)
                ]
        retained.append((column, row))
        row += 1
    solve = [[Fraction(0)] * size for _ in range(size)]
    for column, at in retained:
        solve[column] = work[at][size:]
    return tuple(tuple(line) for line in solve), len(retained)


def _arm_plan(design: Design, rows: tuple[int, ...]) -> _ArmPlan:
    size = design.width
    normal = [[Fraction(0)] * size for _ in range(size)]
    for index in rows:
        row = (Fraction(1), *design.rows[index])
        for i in range(size):
            if row[i] == 0:
                continue
            for j in range(i, size):
                normal[i][j] += row[i] * row[j]
    for i in range(size):
        for j in range(i):
            normal[i][j] = normal[j][i]
    solve, rank = _solve_matrix(normal)
    return _ArmPlan(rows=rows, solve=solve, rank=rank)


def _fit(
    plan: _ArmPlan, design: Design, grand_mean: tuple[Fraction, ...], outcomes: Sequence[Fraction]
) -> tuple[Fraction, Fraction, int]:
    """`(the arm's fitted value at the grand mean, its residual sum of squares, its rank)`."""
    size = design.width
    right = [Fraction(0)] * size
    total_square = Fraction(0)
    for index in plan.rows:
        y = outcomes[index]
        total_square += y * y
        right[0] += y
        for j, value in enumerate(design.rows[index], start=1):
            if value != 0:
                right[j] += value * y
    beta = [sum((row[j] * right[j] for j in range(size)), Fraction(0)) for row in plan.solve]
    fitted = beta[0] + sum(
        (beta[j + 1] * grand_mean[j] for j in range(len(grand_mean))), Fraction(0)
    )
    residual = total_square - sum((beta[j] * right[j] for j in range(size)), Fraction(0))
    return fitted, residual, plan.rank


def _statistic(
    treatment: _ArmPlan,
    control: _ArmPlan,
    design: Design,
    grand_mean: tuple[Fraction, ...],
    outcomes: Sequence[Fraction],
) -> Statistic:
    fitted_t, rss_t, rank_t = _fit(treatment, design, grand_mean, outcomes)
    fitted_c, rss_c, rank_c = _fit(control, design, grand_mean, outcomes)
    difference = fitted_t - fitted_c
    n_t, n_c = len(treatment.rows), len(control.rows)
    if n_t <= rank_t or n_c <= rank_c:
        raise EstimatorError(
            f"an arm has {min(n_t, n_c)} unit(s) and its adjusted model uses "
            f"{max(rank_t, rank_c)} degree(s) of freedom, so there is nothing left to "
            "estimate a variance from. Adjusting on more covariates than an arm has units "
            "does not produce a wide interval; it produces no interval at all."
        )
    variance = rss_t / (n_t * (n_t - rank_t)) + rss_c / (n_c * (n_c - rank_c))
    sign = (difference > 0) - (difference < 0)
    if variance == 0:
        squared = Fraction(0) if difference == 0 else None
    else:
        squared = (difference * difference) / variance
    return Statistic(difference=difference, variance=variance, squared=squared, sign=sign)


# ------------------------------------------------------------------ the public estimates


def _ordered(design: Design, outcomes: Mapping[str, int]) -> list[Fraction]:
    missing = [u for u in design.units if u not in outcomes]
    if missing:
        raise EstimatorError(
            f"{len(missing)} unit(s) in the design report no outcome: {missing[:8]}. A unit "
            "silently dropped here is attrition treated as if it never happened."
        )
    return [Fraction(outcomes[unit]) for unit in design.units]


def _split(design: Design, arms: Mapping[str, Arm]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    treatment = tuple(i for i, u in enumerate(design.units) if arms.get(u) is Arm.TREATMENT)
    control = tuple(i for i, u in enumerate(design.units) if arms.get(u) is Arm.CONTROL)
    if not treatment or not control:
        raise EstimatorError(
            f"an arm is empty: {len(treatment)} treated, {len(control)} control. There is "
            "nothing to take a difference of."
        )
    return treatment, control


def difference_in_means(outcomes: Mapping[str, int], arms: Mapping[str, Arm]) -> Fraction:
    """The unadjusted difference of means. Unbiased under any data-generating process."""
    treated = [Fraction(v) for u, v in sorted(outcomes.items()) if arms.get(u) is Arm.TREATMENT]
    control = [Fraction(v) for u, v in sorted(outcomes.items()) if arms.get(u) is Arm.CONTROL]
    if not treated or not control:
        raise EstimatorError("an arm is empty; there is nothing to take a difference of")
    return sum(treated, Fraction(0)) / len(treated) - sum(control, Fraction(0)) / len(control)


def adjusted_difference(
    outcomes: Mapping[str, int], arms: Mapping[str, Arm], design: Design
) -> Fraction:
    """Lin's estimator. With no covariate columns it is exactly the difference of means."""
    return studentized(outcomes, arms, design).difference


def studentized(outcomes: Mapping[str, int], arms: Mapping[str, Arm], design: Design) -> Statistic:
    """The adjusted difference and its studentized square, over the observed assignment."""
    treatment, control = _split(design, arms)
    grand_mean = _grand_mean(design)
    return _statistic(
        _arm_plan(design, treatment),
        _arm_plan(design, control),
        design,
        grand_mean,
        _ordered(design, outcomes),
    )


# ------------------------------------------------------------------ the permutation test


def plan_for(design: Design, draws: Sequence[Mapping[str, Arm]]) -> ReferencePlan:
    """Precompute the half of every draw that does not depend on the outcomes.

    Built once per experiment. `interval` shifts the outcomes dozens of times and every one
    of those shifts reuses this, which is what makes inverting the test cost about B rather
    than B times the number of steps.
    """
    if not draws:
        raise EstimatorError(
            "an empty reference set. The permutation test has nothing to compare against, "
            "and (1 + hits) / (1 + 0) is not a p-value, it is the number 1."
        )
    grand_mean = _grand_mean(design)
    plans: list[tuple[_ArmPlan, _ArmPlan]] = []
    for arms in draws:
        treatment, control = _split(design, arms)
        plans.append((_arm_plan(design, treatment), _arm_plan(design, control)))
    return ReferencePlan(design=design, grand_mean=grand_mean, plans=tuple(plans))


def _at_least(candidate: Fraction | None, incumbent: Fraction | None) -> bool:
    """`None` is unbounded, so it is at least anything and nothing is at least it."""
    if candidate is None:
        return True
    if incumbent is None:
        return False
    return candidate >= incumbent


def _as_extreme(draw: Statistic, observed: Statistic, direction: MdeDirection) -> bool:
    """Whether a permuted statistic is at least as extreme as the observed one.

    Two-sided compares magnitudes; a declared direction compares the signed `T`, which is
    what makes a one-sided design's p-value the one its own hypothesis asked for rather than
    half of a two-sided one.
    """
    if direction is MdeDirection.EITHER:
        return _at_least(draw.squared, observed.squared)
    if direction is MdeDirection.INCREASE:
        return _signed_at_least(draw, observed)
    return _signed_at_least(observed, draw)


def _signed_at_least(left: Statistic, right: Statistic) -> bool:
    if left.sign != right.sign:
        return left.sign > right.sign
    if left.sign >= 0:
        return _at_least(left.squared, right.squared)
    return _at_least(right.squared, left.squared)


def permutation_p(
    observed: Statistic,
    plan: ReferencePlan,
    outcomes: Mapping[str, int],
    *,
    direction: MdeDirection,
) -> Fraction:
    """`(1 + #{as extreme as observed}) / (1 + B)`, over draws under the same restriction.

    Exact at any B — B buys resolution, not validity — and the `+1` on both sides is what
    makes it exact: it counts the realised assignment, which `reference_set` deliberately
    leaves out of the draws for exactly this reason.
    """
    values = _ordered(plan.design, outcomes)
    hits = 0
    for treatment, control in plan.plans:
        drawn = _statistic(treatment, control, plan.design, plan.grand_mean, values)
        if _as_extreme(drawn, observed, direction):
            hits += 1
    return Fraction(1 + hits, 1 + plan.size)


def interval(
    outcomes: Mapping[str, int],
    arms: Mapping[str, Arm],
    plan: ReferencePlan,
    *,
    alpha: Decimal,
) -> tuple[int, int]:
    """The set of shifts the same test does not reject, as integers in the metric's own unit.

    Inversion, not asymptotics: for each candidate `τ` the outcomes are shifted by `τ` on
    the units that were actually treated and the permutation test is re-run. The endpoints
    are the outermost integers that survive, found by doubling out to a bracket and then
    bisecting, terminating at one canonical unit — so there is nothing to round.
    """
    level = Fraction(alpha)
    treatment, control = _split(plan.design, arms)
    treated = frozenset(plan.design.units[i] for i in treatment)
    values = [Fraction(outcomes[u]) for u in plan.design.units]
    point = _statistic(
        _arm_plan(plan.design, treatment),
        _arm_plan(plan.design, control),
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
        observed = _statistic(
            _arm_plan(plan.design, treatment),
            _arm_plan(plan.design, control),
            plan.design,
            plan.grand_mean,
            shifted,
        )
        hits = sum(
            1
            for t, c in plan.plans
            if _as_extreme(
                _statistic(t, c, plan.design, plan.grand_mean, shifted),
                observed,
                MdeDirection.EITHER,
            )
        )
        return Fraction(1 + hits, 1 + plan.size) > level

    centre = _nearest_integer(point)
    if not accepts(centre):
        raise EstimatorError(
            f"the test rejects its own point estimate ({centre} canonical unit(s)), so the "
            "acceptance region does not contain it and there is no interval to bisect "
            "outward from. That is a statistic behaving unlike any this module was written "
            "for, and returning a plausible pair of endpoints would be inventing one."
        )
    spread = max(values) - min(values) if values else Fraction(0)
    reach = _nearest_integer(spread * BRACKET_SPANS) + BRACKET_SPANS
    return (
        _edge(accepts, centre, step=-1, reach=reach),
        _edge(accepts, centre, step=1, reach=reach),
    )


def _edge(accepts: Callable[[int], bool], centre: int, *, step: int, reach: int) -> int:
    """The outermost integer in one direction that the test still accepts.

    Doubling out to a bracket, then bisecting it. Both halves terminate at one canonical
    unit, which is why the answer is an integer with nothing left to round.
    """
    inside = centre
    span = 1
    while span <= reach:
        candidate = centre + step * span
        if not accepts(candidate):
            break
        inside = candidate
        span *= 2
    else:
        raise EstimatorError(
            f"no shift within {reach} canonical unit(s) of the point estimate is rejected, "
            "so the interval is unbounded on one side. With B draws the smallest attainable "
            "p-value is 1/(1+B), which is below any usable level, so an unbounded interval "
            "means the statistic is not growing with the shift — an input this module was "
            "not written for."
        )
    outside = centre + step * span
    # Bisect the bracket `(inside accepted, outside rejected)` down to a single unit.
    while abs(outside - inside) > 1:
        middle = (inside + outside) // 2
        if accepts(middle):
            inside = middle
        else:
            outside = middle
    return inside


def _nearest_integer(value: Fraction) -> int:
    """Round half away from zero, so the centre of the search is never biased toward zero.

    Not `round()`, which is half-to-even: the metric contract's rounding governs *money*,
    and this is the midpoint of a search rather than an amount anybody is charged.
    """
    whole = abs(value.numerator) // value.denominator
    remainder = abs(value) - whole
    if remainder * 2 >= 1:
        whole += 1
    return whole if value >= 0 else -whole
