"""Three checks that are about the machinery itself rather than about a world.

`U10` two implementations of the metric agree · `U11` the composition is exact where there is
no interference and wrong where there is · `U12` the interval is the inversion of the test it
reports.

None of them is a rate over seeds, so each means the same thing at the published configuration
and at the small one a planted mutation runs. That is not a convenience: three of the eight
mutations name these ids, and a check whose meaning changed with the number of draws would be
a gate that proved something different in the two places it runs.
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

from corpus.world import Arm as WorldArm
from corpus.world import alternating, prepare
from corpus.world.scale import Scale

from evals.report import Check
from evals.uplift import outcomes, potential, reference
from evals.uplift.harness import DrawRecord
from holdout.contracts.model import Metric


def implementations_agree(world_id: str, *, world_seed: str, scale: Scale, metric: Metric) -> Check:
    """`U10` — the grouped path and the deliberately slow one produce the same integers.

    The grouped path bisects a sorted index and works in integer cents; the reference walks the
    cost ledger forward from its first entry and works in `Decimal` euros. They share no line,
    which `tests/evals/test_uplift_reference.py` asserts off both syntax trees, and they agree
    with **no tolerance** — a one-cent disagreement is a failed check with the offending cells
    named.

    That is the failure v3 of the metric contract exists to have made impossible: v2 rounded
    `half_up`, a SQL `round()` and a Python `Decimal` disagreed by a cent, and claim 5 compares
    consumers as integers. This is the first thing that would notice if it came back.
    """
    run = prepare(world_id, seed=world_seed, scale=scale)
    grouped = outcomes.cell_margins(outcomes.collect(run), metric.rounding)
    walked = reference.compute(run, metric=metric)
    missing = sorted(set(grouped) ^ set(walked))
    disagreeing = sorted(
        cell for cell in set(grouped) & set(walked) if grouped[cell] != walked[cell]
    )
    passed = not missing and not disagreeing
    return Check(
        id="U10.truth-implementations-agree",
        question=(
            "Do two independently written implementations of the metric contract — one "
            "grouped, one walking every event — produce the same integer for every cell?"
        ),
        passed=passed,
        figure=(
            f"{len(disagreeing)} disagreeing of {len(grouped)} cell(s) on {world_id}, no tolerance"
        ),
        detail=""
        if passed
        else (
            "the two implementations of one contract differ. Claim 5 compares consumers as "
            "integers with no tolerance, so a cent is a failure and not a rounding question."
        ),
        counterexamples=tuple(
            f"{cell}: grouped {grouped[cell]} against walked {walked[cell]}"
            for cell in disagreeing[:5]
        )
        + tuple(f"{cell}: present in only one implementation" for cell in missing[:5]),
    )


def composition_is_exact(
    world_ids: Sequence[str], *, world_seed: str, scale: Scale, metric: Metric
) -> Check:
    """`U11` — the property K = 200 rests on, checked against the generator both ways.

    Outside W2 a store's events are a function of its own arm, so two counterfactual
    generations buy every lottery — which is the whole reason two hundred draws are affordable.
    It is a claim about `corpus/world/generate.py`, so it is checked against it: a mixed
    assignment is generated for real and the per-unit metric it produces must equal the
    composed value **as integers**.

    And the same comparison on W2 must **disagree**. A world built to break the stable unit
    treatment value assumption whose outcomes composed unit by unit would not be breaking it,
    and every check downstream of it would be measuring a world with no interference in it.
    """
    exact: list[str] = []
    wrong: list[str] = []
    failures: list[str] = []
    for world_id in world_ids:
        run = prepare(world_id, seed=world_seed, scale=scale)
        mixed = alternating(run.chain)
        generated = outcomes.unit_weeks(
            outcomes.collect(prepare(world_id, seed=world_seed, scale=scale, assignment=mixed)),
            metric.rounding,
        )
        control, treatment = potential.counterfactual_unit_weeks(
            world_id, world_seed=world_seed, scale=scale, rounding=metric.rounding
        )
        composed = {
            key: (treatment if mixed[key[0]] is WorldArm.TREATMENT else control)[key]
            for key in control
        }
        differing = [key for key, value in composed.items() if generated.get(key) != value]
        interferes = bool(run.world.spillover_pct)
        if interferes and not differing:
            failures.append(
                f"{world_id} declares spillover_pct={run.world.spillover_pct} and composed "
                "exactly — it has stopped interfering"
            )
        elif not interferes and differing:
            failures.append(
                f"{world_id}: {len(differing)} of {len(composed)} unit-weeks differ between "
                f"generating and composing — {sorted(differing)[:2]}"
            )
        (wrong if interferes else exact).append(world_id)
    return Check(
        id="U11.composition-is-exact",
        question=(
            "Is a unit's outcome a function of its own arm where no interference is declared "
            "— exactly, as integers — and not a function of it where interference is?"
        ),
        passed=not failures,
        figure=(
            f"exact on {len(exact)} world(s) ({', '.join(exact) or 'none'}), "
            f"wrong on {len(wrong)} ({', '.join(wrong) or 'none'}), as it must be"
        ),
        detail=""
        if not failures
        else (
            "either the composition is not exact, and K draws cost K generations rather than "
            "two, or the interference world has stopped interfering and everything measured "
            "on it is measuring nothing."
        ),
        counterexamples=tuple(failures),
    )


def interval_inverts_the_test(records: Sequence[DrawRecord], *, alpha: Fraction) -> Check:
    """`U12` — the interval and the p-value are two readings of one test, so they must agree.

    The interval is the set of shifts the permutation test does not reject at the declared
    level. So zero lies outside it exactly when the test rejects zero, which is exactly when
    the readout calls the result significant. Two numbers, one test, and they cannot disagree
    unless one of them was computed some other way.

    **It holds because this harness declares a two-sided MDE**, and the condition is stated
    rather than assumed: `Readout.is_significant` follows the *declared direction* while the
    interval is always two-sided, so a one-sided design can honestly produce a rejection whose
    two-sided interval still contains zero. `evals/uplift/design.py` declares `EITHER`, and
    this check is about the arrangement in which the two must line up.

    What it catches that coverage does not: a wrong interval that happens to be about the right
    width still covers about as often as a right one. Only its relationship to the test it
    claims to invert gives it away.
    """
    scored = [r for r in records if r.interval_cents is not None and r.p_value is not None]
    disagreeing = [
        r
        for r in scored
        if r.interval_cents is not None
        and (r.interval_cents[0] <= 0 <= r.interval_cents[1]) is bool(r.significant)
    ]
    return Check(
        id="U12.interval-inverts-the-test",
        question=(
            "Is the confidence interval the inversion of the test the readout reports — does "
            "it exclude zero exactly when the p-value calls the result significant?"
        ),
        passed=not disagreeing and bool(scored),
        figure=(
            f"{len(scored) - len(disagreeing)}/{len(scored)} agree"
            if scored
            else "no draw produced both an interval and a p-value"
        ),
        detail=(
            "the interval and the p-value are two readings of one test and they disagree, so "
            "one of them was computed some other way. A wrong interval of about the right "
            "width still covers about as often as a right one; only this relationship gives "
            "it away."
            if disagreeing
            else ""
        ),
        counterexamples=tuple(
            f"{r.world}/{r.world_seed}/{r.lottery_seed}: interval {r.interval_cents} "
            f"{'contains' if r.interval_cents and r.interval_cents[0] <= 0 <= r.interval_cents[1] else 'excludes'} "
            f"zero while p={float(r.p_value or 0):.4f} against alpha={float(alpha)}"
            for r in disagreeing[:5]
        ),
    )
