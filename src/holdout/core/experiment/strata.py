"""Strata from matching on a composite distance — the restriction the lottery draws under.

Why strata at all
-----------------
Rejection sampling against a balance tolerance does not scale down: at the scenario's own
shape — 100 stores, a 20% holdout, five covariates — the standardised difference between
arms has a spread of about 0.25, so a screen at 0.10 accepts roughly one draw in a
thousand, the reference set inside any sane budget holds single figures, and the smallest
attainable p-value sits **above** the declared α. `docs/DECISIONS.md` records the
arithmetic. Stratified randomisation is the standard remedy: build the balance into the
*space* the lottery draws from, so that every draw is admissible and the reference set
fills to the declared B instead of starving.

The strata
----------
`control_count` strata, each contributing **exactly one control**, because the holdout
share fixes how many controls there are and one per stratum is the finest stratification
that number admits — the finest is the best-balanced, since a stratum is the set of units
the lottery treats as interchangeable.

Every stratum must hold **both** arms, so it must hold at least two units. Where
`floor(n / c) < 2` no such stratification exists and `strata_of` returns `None` — a fact
about the roster and the declared share, which the design engine turns into
`NO_ADMISSIBLE_ASSIGNMENT`, a refusal that names what would fix it. It is returned, not
raised, for the reason `assignment.draw` gives: a refusal is a correct output, and an
exception says the caller is wrong.

The composite distance
----------------------
Between two units, over the contract's declared balance covariates and nothing else:

* **numeric** — ``(x_u - x_v)² / var``, with ``var`` the population variance of the
  covariate over the whole roster. Scaling by the variance is what makes the sum
  *composite*: revenue in euros and waste as a rate become comparable, and a covariate
  with no spread contributes nothing because there is nothing to separate on.
* **categorical** — ``0`` where the levels agree, ``1`` where they differ.

Summed, exact in `Fraction`, and squared throughout — a distance compared but never
measured needs no square root, which keeps the whole construction in exact rational
arithmetic like everything else in this package.

The covariates are the ones `contracts/design/balance_covariates.yaml` fixes, pre-period
only, and the argument is the contract's own: matching on anything measured inside the
comparison window would use the same data twice, and a per-experiment choice of what to
match on would be a new way to fish.

Categorical levels are held by allocation, not by distance alone
----------------------------------------------------------------
A categorical covariate's balance is decided by *how many* strata sit inside each of its
levels, because a stratum pure in a level contributes its one control to that level with
certainty. So the units are first partitioned into **cells** — one per combination of
categorical levels — and the strata are allocated to cells in proportion to their size,
by largest remainder, capped at `floor(cell / 2)` so every stratum keeps both arms. That
pins each level's control share to within one stratum of its population share, which a
distance alone cannot do: with fixed stratum sizes the leftovers of each level must share
a stratum, and every draw then moves the level's control count. Cells too small to hold a
stratum give their units to the nearest formed stratum instead of forcing one; a cell
structure too fragmented to place every stratum — many one-unit cells — falls back to one
pool matched on the full composite distance, which is the same construction with the
allocation step degenerate.

Within a cell the matching is greedy, hardest first, then refined
-----------------------------------------------------------------
Each round anchors on the unmatched unit whose ``(size - 1)``-th nearest unmatched
neighbour is **furthest** — the unit hardest to match — and groups it with its
``size - 1`` nearest unmatched neighbours. Matching the hardest unit first is what stops
it being left for last, when only leftovers remain to pair it with. A bounded swap pass
then trades units between strata of the same cell while any swap lowers the summed
within-stratum distance — greedy grouping is order-sensitive at the margins, and the
refinement removes exactly that sensitivity's cost. Every comparison breaks ties on the
unit id, so the strata are a pure function of the matrix and depend on no iteration
order — the same property the lottery itself has, for the same reason: a stratification
that moved between runs would be an assignment that cannot be reproduced.

What stratification cannot do, said out loud
--------------------------------------------
With `c` controls a covariate's mean in the control arm is an average of `c` draws, one
per stratum, so its standardised difference keeps a sampling spread of roughly the
within-stratum spread over `sqrt(c)`. For a covariate the others carry no information
about — noise-like, unclustered — no matching shrinks the within-stratum spread much
below the roster's own, and at the scenario's shape that leaves the worst covariate near
the readout tolerance: some healthy stratified draws will be refused at readout as
`IMBALANCED_PRE_PERIOD`. That is the honest direction — a refusal, never a wrong number —
and the rate is measured in `tests/core/test_assignment.py` rather than asserted away.

What this module does not do
----------------------------
It never sees the seed and never draws: which unit in a stratum becomes control is the
lottery's decision (`assignment.candidate`), computed from the committed seed. Strata are
a function of the covariates alone, so they are fixed before any draw exists — the
restriction is committed first, and the randomness runs inside it.
"""

from __future__ import annotations

from collections.abc import Callable
from fractions import Fraction

from holdout.core.experiment.balance import CovariateKind, CovariateMatrix

_Distance = Callable[[str, str], Fraction]

#: How many times the swap refinement may sweep every pair of strata in a cell before it
#: stops even if an improving swap remains. Each sweep only ever lowers the summed
#: within-stratum distance, so the bound is about time, not correctness — in practice the
#: sweeps converge in two or three.
REFINEMENT_SWEEPS = 8


class StrataError(ValueError):
    """The matching was asked for something it cannot build. Not a refusal — a refusal is
    returned by `strata_of` as `None`, and this says the caller is wrong."""


def composite_distance(matrix: CovariateMatrix, left: str, right: str) -> Fraction:
    """The squared composite distance between two units. Exact, and symmetric by shape.

    Public because a test that could only observe distances through the finished strata
    could not check the arithmetic on its own — the same argument `candidate` makes for
    the lottery.
    """
    if left not in matrix.rows or right not in matrix.rows:
        missing = [u for u in (left, right) if u not in matrix.rows]
        raise StrataError(f"no covariates for {missing}")
    variances = _variances(matrix)
    return _distance(matrix, variances, left, right)


def strata_of(matrix: CovariateMatrix, control_count: int) -> tuple[tuple[str, ...], ...] | None:
    """`control_count` strata over the matrix's units, or `None` where none can hold both arms.

    Each stratum is sorted by unit id and the strata are sorted by their first member, so
    the answer is canonical: two calls over the same matrix are equal as values, not just
    equivalent as partitions.
    """
    units = matrix.units
    if control_count < 1:
        raise StrataError("a stratification holds at least one stratum")
    if control_count >= len(units):
        raise StrataError(
            f"{control_count} strata over {len(units)} unit(s) would leave strata with "
            "nobody in them. The control count comes from the holdout share and the "
            "roster is what would have to change."
        )
    if len(units) // control_count < 2:
        # The genuine "no admissible stratification": some stratum would hold one unit,
        # and a stratum of one is a unit whose arm nobody drew.
        return None

    variances = _variances(matrix)
    cache: dict[tuple[str, str], Fraction] = {}

    def between(left: str, right: str) -> Fraction:
        key = (left, right) if left < right else (right, left)
        if key not in cache:
            cache[key] = _distance(matrix, variances, key[0], key[1])
        return cache[key]

    cells = _cells(matrix)
    allocation = _allocate(cells, control_count, roster_size=len(units))
    if allocation is None:
        # Too fragmented to place every stratum inside a cell — one pool, full distance.
        matched = _refine(_greedy(list(units), control_count, between), between)
        return tuple(sorted(matched))

    strata: list[tuple[str, ...]] = []
    unplaced: list[str] = []
    for key in sorted(cells):
        members, count = cells[key], allocation[key]
        if count == 0:
            unplaced.extend(members)
            continue
        strata.extend(_refine(_greedy(members, count, between), between))
    for unit in sorted(unplaced):
        nearest = min(strata, key=lambda s: (min(between(unit, m) for m in s), s[0]))
        strata[strata.index(nearest)] = tuple(sorted((*nearest, unit)))
    return tuple(sorted(strata))


# ------------------------------------------------------------------ cells and allocation


def _cells(matrix: CovariateMatrix) -> dict[tuple[str, ...], list[str]]:
    """The units partitioned by their combination of categorical levels, sorted throughout."""
    categorical = [
        index for index, kind in enumerate(matrix.kinds) if kind is CovariateKind.CATEGORICAL
    ]
    out: dict[tuple[str, ...], list[str]] = {}
    for unit in matrix.units:
        key = tuple(str(matrix.rows[unit][index]) for index in categorical)
        out.setdefault(key, []).append(unit)
    return out


def _allocate(
    cells: dict[tuple[str, ...], list[str]], control_count: int, *, roster_size: int
) -> dict[tuple[str, ...], int] | None:
    """Strata per cell, in proportion to the cell's share of the roster.

    Largest remainder, capped at `floor(cell / 2)` so every stratum keeps both arms, ties
    broken toward the larger cell and then the earlier key. `None` where the caps cannot
    place every stratum — the fragmented case the caller answers with one pool.
    """
    order = sorted(cells, key=lambda key: (-len(cells[key]), key))
    quota = {key: Fraction(len(cells[key]) * control_count, roster_size) for key in cells}
    cap = {key: len(cells[key]) // 2 for key in cells}
    allocation = {key: min(int(quota[key]), cap[key]) for key in cells}
    remaining = control_count - sum(allocation.values())
    while remaining > 0:
        eligible = [key for key in order if allocation[key] < cap[key]]
        if not eligible:
            return None
        chosen = max(eligible, key=lambda key: quota[key] - allocation[key])
        allocation[chosen] += 1
        remaining -= 1
    return allocation


# ------------------------------------------------------------------ matching


def _greedy(units: list[str], count: int, between: _Distance) -> list[tuple[str, ...]]:
    """`count` strata over `units`, sizes as even as possible, hardest matched first."""
    ordered = sorted(units)
    quotient, remainder = divmod(len(ordered), count)
    sizes = [quotient + 1] * remainder + [quotient] * (count - remainder)
    unmatched = set(ordered)
    out: list[tuple[str, ...]] = []
    for size in sizes:
        anchor = _hardest_to_match(unmatched, size, between)
        others = sorted(
            (u for u in unmatched if u != anchor), key=lambda u: (between(anchor, u), u)
        )
        stratum = (anchor, *others[: size - 1])
        unmatched.difference_update(stratum)
        out.append(tuple(sorted(stratum)))
    assert not unmatched  # the sizes sum to the units by construction
    return out


def _hardest_to_match(unmatched: set[str], size: int, between: _Distance) -> str:
    """The unit whose `size - 1`-th nearest unmatched neighbour is furthest away.

    Anchoring on it now, while its nearest neighbours are still free, is the greedy
    version of not leaving the outlier for last. Ties go to the smaller id, so the
    matching never depends on set-iteration order.
    """
    worst_id = ""
    worst_reach: Fraction | None = None
    for unit in sorted(unmatched):
        reach = sorted(between(unit, other) for other in unmatched if other != unit)[size - 2]
        if worst_reach is None or reach > worst_reach:
            worst_id, worst_reach = unit, reach
    return worst_id


def _spread(stratum: tuple[str, ...], between: _Distance) -> Fraction:
    """The summed pairwise distance inside one stratum — what the refinement minimises."""
    return sum(
        (between(a, b) for i, a in enumerate(stratum) for b in stratum[i + 1 :]),
        Fraction(0),
    )


def _refine(strata: list[tuple[str, ...]], between: _Distance) -> list[tuple[str, ...]]:
    """Trade units between strata while any swap lowers the summed within-stratum spread.

    Greedy grouping is order-sensitive at the margins — the last strata formed choose from
    leftovers — and this removes that sensitivity's cost. Deterministic: pairs are visited
    in sorted order, the best strict improvement per pair is taken, and each sweep only
    lowers a non-negative total, so the process cannot cycle; `REFINEMENT_SWEEPS` bounds
    the time regardless.
    """
    working = [tuple(s) for s in strata]
    for _ in range(REFINEMENT_SWEEPS):
        improved = False
        for i in range(len(working)):
            for j in range(i + 1, len(working)):
                first, second = working[i], working[j]
                base = _spread(first, between) + _spread(second, between)
                best: tuple[Fraction, str, str] | None = None
                for x in first:
                    for y in second:
                        swapped_first = tuple(sorted([u for u in first if u != x] + [y]))
                        swapped_second = tuple(sorted([u for u in second if u != y] + [x]))
                        cost = _spread(swapped_first, between) + _spread(swapped_second, between)
                        if cost < base and (best is None or cost < best[0]):
                            best = (cost, x, y)
                if best is not None:
                    _, x, y = best
                    working[i] = tuple(sorted([u for u in first if u != x] + [y]))
                    working[j] = tuple(sorted([u for u in second if u != y] + [x]))
                    improved = True
        if not improved:
            break
    return working


# ------------------------------------------------------------------ the arithmetic


def _variances(matrix: CovariateMatrix) -> tuple[Fraction | None, ...]:
    """Per column: the population variance for a numeric covariate, `None` for a categorical."""
    out: list[Fraction | None] = []
    for index in range(len(matrix.ids)):
        if matrix.kinds[index] is not CovariateKind.NUMERIC:
            out.append(None)
            continue
        values = [_numeric(matrix, unit, index) for unit in matrix.units]
        mean = sum(values, Fraction(0)) / len(values)
        out.append(sum(((v - mean) * (v - mean) for v in values), Fraction(0)) / len(values))
    return tuple(out)


def _distance(
    matrix: CovariateMatrix,
    variances: tuple[Fraction | None, ...],
    left: str,
    right: str,
) -> Fraction:
    total = Fraction(0)
    for index in range(len(matrix.ids)):
        variance = variances[index]
        if variance is None:
            if matrix.rows[left][index] != matrix.rows[right][index]:
                total += 1
            continue
        if variance == 0:
            continue  # no spread means every unit agrees; there is nothing to separate on
        gap = _numeric(matrix, left, index) - _numeric(matrix, right, index)
        total += (gap * gap) / variance
    return total


def _numeric(matrix: CovariateMatrix, unit: str, index: int) -> Fraction:
    value = matrix.rows[unit][index]
    assert isinstance(value, Fraction)  # enforced by CovariateMatrix.of
    return value
