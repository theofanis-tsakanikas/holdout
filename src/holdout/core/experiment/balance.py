"""One statistic, one moment that decides — the standardised difference between arms.

Per covariate, a standardised difference:

* **numeric** — ``|x̄_T - x̄_C| / s_pooled``, with ``s_pooled = sqrt((s²_T + s²_C) / 2)``
* **categorical** — the same quantity per level, on that level's indicator:
  ``|p_T - p_C| / sqrt(p̄(1 - p̄))`` with ``p̄ = (p_T + p_C) / 2``, taking the **maximum** over
  levels

One statistic, one tolerance (`balance_tolerance_smd`), no per-type special case. A
categorical covariate is a set of indicators and an indicator's standard deviation is
`sqrt(p(1-p))`, so the second formula is the first one written out, not a different rule.

Nothing here takes a square root
--------------------------------
The comparison is ``smd ≤ tolerance``, which for non-negative quantities is exactly
``smd² ≤ tolerance²``. Both sides are exact in `Fraction`, so nothing ever leaves exact
rational arithmetic. `Decimal.sqrt()` appears once, when a figure is reported to a human.

Where the tolerance is judged, and where it is not
--------------------------------------------------
This module used to carry a `screen` as well — the rejection-sampling gate the old
re-randomisation draw ran candidates through. The stratified lottery has no screen: the
balance is built into the strata (`strata.py`), the design records the realised draw's
figures without judging them, and `balance_tolerance_smd` is applied at exactly **one**
moment — the readout's balance check. One moment, so an assignment cannot be accepted at
design and refused at readout under two tolerances nobody declared; the restatement is in
`contracts/design/inference.yaml`'s own notes.

The check is **not** vacuous, because the data is not the design's. The readout re-measures
the covariates from what actually arrived, over the units that actually reported. An
assignment re-checked against the matrix its strata were built from would pass by
construction almost always — a gate that can barely bite, which is the family of defect
this project has now found four times. Restated pre-period revenue, an attrited store, a
roster that moved: those are what `IMBALANCED_PRE_PERIOD` is for, and
`tests/core/test_balance.py` plants each of the three.

What a lottery could and could not have achieved
------------------------------------------------
`attainable` answers a different question from `standardised`, at a different moment. Given
the strata a lottery will draw within, **how good can a categorical covariate's balance
possibly get?** One control comes out of each stratum, so a stratum that is pure in a level
contributes a control to that level with certainty and one that contains no unit of the
level cannot contribute at all. The control count for a level is therefore pinned between
those two numbers whatever the seed is, and the best standardised difference over that
range is a fact about the *restriction* rather than about any draw.

It exists because a design that lands outside that range was, until T00D, accepted at
moment 1 and refused identically at every readout. On this repository's own corpus at 25
controls, `store_format=hypermarket` sat at a constant 0.1734 across two hundred draws:
an experiment that could never have reported anything, for a reason with nothing to do with
the lottery. `feasibility` turns it into `NO_ADMISSIBLE_ASSIGNMENT`.

**It is sound and it is incomplete, and both halves are deliberate.** Sound: the bound is
computed with `_standardised` itself — the same function the readout will run, not a second
implementation of it — so a design it refuses genuinely has no draw that passes. That is not
a guard agreeing with itself: the question here is *predictive*, and a prediction that used
different arithmetic from the thing it predicts would be worth nothing. Incomplete in two
named ways: the per-level optima need not be simultaneously attainable, so some accepted
designs still cannot pass; and **numeric covariates are not bounded here at all**, because
almost any numeric imbalance is attainable by some draw and the question about them is a
*rate* rather than a possibility. That rate is claim 2's to publish.

Zero spread is not a free pass
------------------------------
If a covariate has no within-arm spread at all and the two arms nonetheless sit at different
values, the standardised difference is not large — it is undefined, and treating it as zero
would wave through the most extreme imbalance the statistic can describe. It is reported as
`None`, which every comparison here reads as *exceeds any tolerance*. Where the arms are
also equal, the difference is zero and the covariate is perfectly balanced, which is the one
case where 0/0 has an obvious answer.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from fractions import Fraction
from types import MappingProxyType

from holdout.core.experiment.codes import Arm
from holdout.core.money import decimal_of

#: Two arms, so the pooled spread averages two variances. Named because it appears in the
#: arithmetic and a bare 2 in a formula is a number a reader has to reverse-engineer.
ARMS = 2


class BalanceError(ValueError):
    """The statistic was asked for something it cannot be computed over."""


class CovariateKind(StrEnum):
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"


#: One unit's value for one covariate. A `Fraction` for a numeric covariate, the level's own
#: name for a categorical one. Never a float: every comparison here is between exact
#: squares, and the first binary approximation would put a tolerance back into a
#: comparison built to avoid one.
CovariateValue = Fraction | str


@dataclass(frozen=True, slots=True)
class CovariateMatrix:
    """Pre-period covariates, per unit, in a fixed column order.

    Fixed order because everything downstream — the strata, the readout's check, the
    estimator's design matrix — has to agree about which column is which, and because the
    covariates are fixed by `contracts/design/balance_covariates.yaml` rather than chosen
    per experiment.

    `measured on the pre-period` is the contract's guarantee, not this type's: matching or
    checking on anything measured inside the comparison window uses the same data twice and
    biases the estimate toward zero. What this type enforces is that every unit has every
    column, because a missing covariate is a unit that would be silently balanced on less
    than the others.
    """

    ids: tuple[str, ...]
    kinds: tuple[CovariateKind, ...]
    rows: MappingProxyType[str, tuple[CovariateValue, ...]]

    @classmethod
    def of(
        cls,
        ids: tuple[str, ...],
        kinds: tuple[CovariateKind, ...],
        rows: Mapping[str, tuple[CovariateValue, ...]],
    ) -> CovariateMatrix:
        if not ids:
            raise BalanceError(
                "a balance matrix has at least one covariate. The list is fixed in "
                "contracts/design/balance_covariates.yaml and an empty one would make "
                "every stratification perfect and every balance check pass."
            )
        if len(kinds) != len(ids):
            raise BalanceError("every covariate declares its kind")
        if len(set(ids)) != len(ids):
            raise BalanceError(f"a covariate is named twice: {ids}")
        for unit, row in rows.items():
            if len(row) != len(ids):
                raise BalanceError(
                    f"unit {unit!r} carries {len(row)} value(s) for {len(ids)} covariate(s). "
                    "A unit balanced on fewer covariates than the others is a unit nobody "
                    "measured."
                )
            for index, value in enumerate(row):
                expected = kinds[index]
                if expected is CovariateKind.NUMERIC and not isinstance(value, Fraction):
                    raise BalanceError(
                        f"{ids[index]!r} is numeric and unit {unit!r} carries "
                        f"{type(value).__name__}. Numeric covariates arrive as Fraction so "
                        "the arithmetic stays exact."
                    )
                if expected is CovariateKind.CATEGORICAL and not isinstance(value, str):
                    raise BalanceError(
                        f"{ids[index]!r} is categorical and unit {unit!r} carries "
                        f"{type(value).__name__}. A level is named, never numbered."
                    )
        return cls(ids=ids, kinds=kinds, rows=MappingProxyType(dict(rows)))

    @property
    def units(self) -> tuple[str, ...]:
        """Every unit, sorted, so that iteration never depends on insertion order."""
        return tuple(sorted(self.rows))

    def column(self, covariate_id: str) -> tuple[CovariateValue, ...]:
        """One covariate's values, in `units` order."""
        index = self.ids.index(covariate_id)
        return tuple(self.rows[unit][index] for unit in self.units)

    def levels(self, covariate_id: str) -> tuple[str, ...]:
        """Every level a categorical covariate takes, sorted.

        Sorted rather than first-seen, so the reference level the estimator drops and the
        level a check reports are the same on every machine and in every process.
        """
        index = self.ids.index(covariate_id)
        if self.kinds[index] is not CovariateKind.CATEGORICAL:
            raise BalanceError(f"{covariate_id!r} is numeric and has no levels")
        return tuple(sorted({str(self.rows[unit][index]) for unit in self.units}))

    def restricted_to(self, units: frozenset[str]) -> CovariateMatrix:
        """The same matrix over a subset of units — what attrition leaves behind.

        Used at readout, where the units that reported are not necessarily the units that
        were assigned. It is a different matrix, and the balance check is meant to notice.
        """
        missing = units - set(self.rows)
        if missing:
            raise BalanceError(f"no covariates for {sorted(missing)}")
        return CovariateMatrix(
            ids=self.ids,
            kinds=self.kinds,
            rows=MappingProxyType({u: self.rows[u] for u in sorted(units)}),
        )


@dataclass(frozen=True, slots=True)
class Standardised:
    """One covariate's standardised difference between the arms.

    `squared` is `None` where the arms differ and neither has any within-arm spread: the
    statistic is undefined and reading it as zero would wave through the most extreme
    imbalance it can describe. Every comparison treats `None` as exceeding any tolerance.
    """

    covariate_id: str
    level: str | None
    squared: Fraction | None

    def exceeds(self, tolerance: Decimal) -> bool:
        if self.squared is None:
            return True
        limit = Fraction(tolerance)
        return self.squared > limit * limit

    @property
    def value(self) -> Decimal | None:
        """The figure a human reads. The only square root in the module."""
        if self.squared is None:
            return None
        return decimal_of(self.squared).sqrt()

    def __str__(self) -> str:
        where = self.covariate_id if self.level is None else f"{self.covariate_id}={self.level}"
        shown = "undefined (no within-arm spread)" if self.value is None else f"{self.value:.4f}"
        return f"{where} {shown}"


def _split(arms: Mapping[str, Arm], units: tuple[str, ...]) -> tuple[list[str], list[str]]:
    treated = [u for u in units if arms.get(u) is Arm.TREATMENT]
    control = [u for u in units if arms.get(u) is Arm.CONTROL]
    if not treated or not control:
        raise BalanceError(
            f"an arm is empty: {len(treated)} treated, {len(control)} control. A standardised "
            "difference between one arm and nothing is not a small number, it is no number."
        )
    unassigned = [u for u in units if u not in arms]
    if unassigned:
        raise BalanceError(
            f"{len(unassigned)} unit(s) carry covariates and no arm: {sorted(unassigned)[:5]}. "
            "A unit measured and not assigned would be balanced into neither arm."
        )
    return treated, control


def _mean_and_variance(values: list[Fraction]) -> tuple[Fraction, Fraction]:
    """The arm's mean and its population variance, exact.

    Population (divide by n) rather than sample (divide by n - 1). The standardised
    difference is a descriptive scale, not an inferential one — nothing here estimates a
    parameter — and the choice is written down because the two differ by a factor that
    matters at the sizes an experiment of a hundred stores actually runs at.
    """
    n = len(values)
    mean = sum(values, Fraction(0)) / n
    variance = sum(((v - mean) * (v - mean) for v in values), Fraction(0)) / n
    return mean, variance


def _standardised(
    treated: list[Fraction], control: list[Fraction], *, covariate_id: str, level: str | None
) -> Standardised:
    mean_t, var_t = _mean_and_variance(treated)
    mean_c, var_c = _mean_and_variance(control)
    difference = mean_t - mean_c
    pooled = (var_t + var_c) / ARMS
    if pooled == 0:
        squared = Fraction(0) if difference == 0 else None
    else:
        squared = (difference * difference) / pooled
    return Standardised(covariate_id=covariate_id, level=level, squared=squared)


def standardised(matrix: CovariateMatrix, arms: Mapping[str, Arm]) -> tuple[Standardised, ...]:
    """The standardised difference for every covariate, in the matrix's column order.

    One per numeric covariate; for a categorical one, the maximum over its levels, carrying
    the level that maximised it so a refusal can name it. Nothing is aggregated across
    covariates: the tolerance applies to each, because an assignment balanced on average and
    badly wrong on one covariate is badly wrong.
    """
    units = matrix.units
    treated, control = _split(arms, units)
    out: list[Standardised] = []
    for index, covariate_id in enumerate(matrix.ids):
        if matrix.kinds[index] is CovariateKind.NUMERIC:
            out.append(
                _standardised(
                    [_numeric(matrix, u, index) for u in treated],
                    [_numeric(matrix, u, index) for u in control],
                    covariate_id=covariate_id,
                    level=None,
                )
            )
            continue
        worst: Standardised | None = None
        for level in matrix.levels(covariate_id):
            here = _standardised(
                [_indicator(matrix, u, index, level) for u in treated],
                [_indicator(matrix, u, index, level) for u in control],
                covariate_id=covariate_id,
                level=level,
            )
            worst = here if worst is None or _worse(here, worst) else worst
        assert worst is not None  # levels() is non-empty for any populated column
        out.append(worst)
    return tuple(out)


def _worse(candidate: Standardised, incumbent: Standardised) -> bool:
    """`None` — an undefined statistic — is worse than any finite one, and ties go to the
    earlier level so the reported level does not depend on iteration order."""
    if candidate.squared is None:
        return incumbent.squared is not None
    if incumbent.squared is None:
        return False
    return candidate.squared > incumbent.squared


def _numeric(matrix: CovariateMatrix, unit: str, index: int) -> Fraction:
    value = matrix.rows[unit][index]
    assert isinstance(value, Fraction)  # enforced by CovariateMatrix.of
    return value


def _indicator(matrix: CovariateMatrix, unit: str, index: int, level: str) -> Fraction:
    return Fraction(1) if matrix.rows[unit][index] == level else Fraction(0)


def attainable(
    matrix: CovariateMatrix, strata: Sequence[Sequence[str]]
) -> tuple[Standardised, ...]:
    """The best standardised difference any draw within `strata` could reach, per
    categorical covariate — a fact about the restriction, not about a seed.

    One control per stratum, so for a level the control count is pinned between the number
    of strata that are **pure** in it and the number that **contain** it at all. Every
    integer in that range is the count some draw produces, so the minimum standardised
    difference over the range is attainable and nothing below it is. Per covariate the
    **maximum** over its levels is returned, exactly as `standardised` does, because a draw
    passes only when every level does.

    Numeric covariates are absent from the answer by design — see the module docstring.
    An empty tuple means the matrix declares no categorical covariate, which is a matrix a
    lottery cannot be constrained by in this way rather than one that is perfectly balanced.
    """
    units = [unit for stratum in strata for unit in stratum]
    if not units:
        raise BalanceError("a stratification with no units has no attainable balance")
    if len(set(units)) != len(units):
        raise BalanceError("a unit appears in two strata; each is assigned once")
    missing = sorted(set(units) - set(matrix.rows))
    if missing:
        raise BalanceError(f"no covariates for {missing[:5]}")
    control_size = len(strata)
    treatment_size = len(units) - control_size
    if treatment_size < 1:
        raise BalanceError(
            f"{control_size} strata over {len(units)} unit(s) leave no treatment arm, so "
            "there is no difference for any draw to make"
        )
    out: list[Standardised] = []
    for index, covariate_id in enumerate(matrix.ids):
        if matrix.kinds[index] is not CovariateKind.CATEGORICAL:
            continue
        worst: Standardised | None = None
        for level in matrix.levels(covariate_id):
            here = _best_for_level(
                matrix,
                strata,
                index=index,
                covariate_id=covariate_id,
                level=level,
                control_size=control_size,
                treatment_size=treatment_size,
            )
            worst = here if worst is None or _worse(here, worst) else worst
        if worst is not None:
            out.append(worst)
    return tuple(out)


def _best_for_level(
    matrix: CovariateMatrix,
    strata: Sequence[Sequence[str]],
    *,
    index: int,
    covariate_id: str,
    level: str,
    control_size: int,
    treatment_size: int,
) -> Standardised:
    """The least imbalance any draw can reach on one level, over the counts it can produce."""
    holding = [
        sum(1 for unit in stratum if matrix.rows[unit][index] == level) for stratum in strata
    ]
    lowest = sum(1 for stratum, count in zip(strata, holding, strict=True) if count == len(stratum))
    highest = sum(1 for count in holding if count)
    total = sum(holding)
    best: Standardised | None = None
    for controls in range(lowest, highest + 1):
        treated = total - controls
        if not 0 <= treated <= treatment_size:
            continue  # a count the arms cannot hold; no draw produces it
        here = _standardised(
            _indicators(treated, treatment_size),
            _indicators(controls, control_size),
            covariate_id=covariate_id,
            level=level,
        )
        best = here if best is None or _worse(best, here) else best
    if best is None:  # pragma: no cover - lowest <= highest always yields one admissible count
        raise BalanceError(
            f"no control count between {lowest} and {highest} fits the arms for "
            f"{covariate_id}={level}"
        )
    return best


def _indicators(ones: int, size: int) -> list[Fraction]:
    """One arm's indicator column for a level, as the readout would see it."""
    return [Fraction(1)] * ones + [Fraction(0)] * (size - ones)


def worst_of(differences: tuple[Standardised, ...]) -> Standardised:
    """The covariate furthest out of balance. What a readout reports as its balance figure."""
    if not differences:
        raise BalanceError("no covariates were compared, so there is no worst one")
    worst = differences[0]
    for candidate in differences[1:]:
        if _worse(candidate, worst):
            worst = candidate
    return worst
