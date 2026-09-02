"""The whole harness, run once, at whichever of two declared configurations it is given.

`python -m evals.uplift` is the published one, at the contract's K. `python -m
evals.uplift.machinery` is the **same code and the same check ids** at a small configuration,
and it is the only module a planted mutation names. One implementation, because two would be
two things to keep in step and only one of them would ever be run by a gate.

What differs between them is declared in `contracts/design/aa_harness.yaml` and nowhere else:
how many world seeds, how many lotteries. What does not differ is the scale — a mutation runs
against the published world, because several checks need a readout that **produces a number**
and that needs the roster and the signal the published scale supplies. It is affordable because
world generation is outside the mutation loop; `cache.py` says how, and what invalidates it.

The rate-shaped checks are the only ones the small configuration drops
----------------------------------------------------------------------
`U1`, `U2` and `U3` are rates over K draws and a rate over three draws is not a rate, so they
are **absent** from the machinery configuration rather than computed on three draws and printed
as though they meant the same thing. `U4` stays, and the reason it can is that it was restated
as a binomial: a fixed tolerance would have been a different check at the two draw counts, and
a test at a declared level is one instrument at any.

Ordering, and what it is a guarantee about
-------------------------------------------
Every draw is run and **written to disk** before a single seal is opened. `open_after_readout`
refuses without a readout it can hash, and records the opening in the seal's own ledger, so the
grading can be checked afterwards by somebody who was not in the room. What the seal holds is
the injected *behaviour*; the truth on the metric is computed from the two counterfactual
generations, and `coverage.py` is explicit that composing a draw puts it in the worker's memory
by construction and that no file could prevent it. What keeps it out of the estimate is
structural: `close()` never sees a potential outcome.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace
from fractions import Fraction
from pathlib import Path

from corpus.world.scale import scale_by_name
from corpus.world.worlds import WORLDS

from evals.report import Check, Report
from evals.uplift import aa, agreement, coverage, design, parallel, potential, worlds
from evals.uplift.harness import DrawRecord
from holdout.contracts.loader import load
from holdout.contracts.model import AaHarness, ContractSet

#: The worlds whose declared correct behaviour is a rate over draws, and the check each owns.
PATHOLOGIES = ("W3", "W4", "W5")


@dataclass(frozen=True, slots=True)
class Configuration:
    """What this run is: how much of it, and which checks that much can carry."""

    label: str
    scale: str
    world_seeds: int
    lotteries: int
    pathology_world_seeds: int
    pathology_lotteries: int
    interference_lotteries: int
    #: Whether the rate-shaped checks are computed. False at the machinery configuration, and
    #: the checks are then absent from the report rather than present and meaningless.
    rates: bool = True
    workers: int | None = None
    permutation_draws: int | None = None

    @property
    def draws(self) -> int:
        return self.world_seeds * self.lotteries


def published(harness: AaHarness) -> Configuration:
    seeds = harness.seeds
    return Configuration(
        label="published",
        scale="harness",
        world_seeds=seeds.world,
        lotteries=seeds.lotteries_per_world_seed,
        pathology_world_seeds=seeds.pathology_world_seeds,
        pathology_lotteries=seeds.pathology_lotteries_per_world_seed,
        interference_lotteries=seeds.interference_lotteries_per_world_seed,
        rates=True,
    )


def machinery(harness: AaHarness) -> Configuration:
    small = harness.machinery
    return Configuration(
        label="machinery",
        scale=small.scale,
        world_seeds=small.world_seeds,
        lotteries=small.lotteries,
        pathology_world_seeds=small.world_seeds,
        pathology_lotteries=small.lotteries,
        interference_lotteries=small.lotteries,
        rates=False,
    )


@dataclass(frozen=True, slots=True)
class Drawn:
    """Every record the run produced, by world, and the truths computed after they landed."""

    by_world: dict[str, list[DrawRecord]] = field(default_factory=dict)
    withheld: list[DrawRecord] = field(default_factory=list)


def _tasks(configuration: Configuration) -> list[parallel.Task]:
    tasks: list[parallel.Task] = []
    for world in ("W1", "W6"):
        for seed in parallel.world_seeds(configuration.world_seeds):
            tasks.append(
                parallel.Task(
                    world=world,
                    world_seed=seed,
                    scale=configuration.scale,
                    lottery_seeds=parallel.lottery_seeds(world, seed, configuration.lotteries),
                    permutation_draws=configuration.permutation_draws,
                )
            )
    for world in PATHOLOGIES:
        for seed in parallel.world_seeds(configuration.pathology_world_seeds):
            tasks.append(
                parallel.Task(
                    world=world,
                    world_seed=seed,
                    scale=configuration.scale,
                    lottery_seeds=parallel.lottery_seeds(
                        world, seed, configuration.pathology_lotteries
                    ),
                    permutation_draws=configuration.permutation_draws,
                )
            )
    # W2 twice over: the same lotteries with the neighbour pairs declared to the engine, and
    # with them withheld. The pair is what U6 publishes.
    for seed in parallel.world_seeds(configuration.pathology_world_seeds):
        for withheld in (False, True):
            tasks.append(
                parallel.Task(
                    world="W2",
                    world_seed=seed,
                    scale=configuration.scale,
                    lottery_seeds=parallel.lottery_seeds(
                        "W2", seed, configuration.interference_lotteries
                    ),
                    withhold_neighbour_pairs=withheld,
                    permutation_draws=configuration.permutation_draws,
                )
            )
    return tasks


def _truths(
    records: Sequence[DrawRecord],
    *,
    world: str,
    configuration: Configuration,
    contracts: ContractSet,
) -> tuple[dict[str, Fraction], dict[str, Fraction]]:
    """The window truth and the first-week truth, per world seed, from the counterfactuals.

    Computed **after** every record exists, from the two counterfactual generations, over the
    same roster and the same window the readout was taken over — an estimand measured on a
    different set of units is a different estimand.
    """
    metric = contracts.metric_versions("category_margin_per_store_week")[-1]
    scale = scale_by_name(configuration.scale)
    window: dict[str, Fraction] = {}
    first_week: dict[str, Fraction] = {}
    for seed in sorted({record.world_seed for record in records if record.world == world}):
        drawn = next(
            (r for r in records if r.world == world and r.world_seed == seed and r.unit_outcomes),
            None,
        )
        if drawn is None:
            # Every draw against this world seed refused at moment 1, so there is no roster to
            # take an average over. The refusal is the result and the checks below count it;
            # inventing a truth for it would be inventing the experiment it refused to run.
            continue
        control, treatment = potential.counterfactual_unit_weeks(
            world, world_seed=seed, scale=scale, rounding=metric.rounding
        )
        weeks = sorted({week for _unit, week in control})
        _pre, period = design.split_weeks(weeks)
        units = sorted(drawn.unit_outcomes)
        window[seed] = coverage.average_treatment_effect(
            control, treatment, units=units, weeks=period
        )
        first_week[seed] = coverage.average_treatment_effect(
            control, treatment, units=units, weeks=period[:1]
        )
    return window, first_week


@dataclass(frozen=True, slots=True)
class Shard:
    """One slice of the draws, and how many slices there are."""

    index: int
    count: int

    @classmethod
    def parse(cls, text: str) -> Shard:
        """`i/N`, one-based on the left so `1/8` is the first of eight and `0/8` is refused."""
        try:
            left, right = text.split("/", 1)
            index, count = int(left), int(right)
        except ValueError:
            raise ShardError(f"{text!r} is not a shard in the form i/N") from None
        if count < 1 or not 1 <= index <= count:
            raise ShardError(f"shard {index} of {count} does not exist")
        return cls(index - 1, count)


class ShardError(Exception):
    """A shard that cannot be run, or a set of shards that is not the whole."""


def _expanded(configuration: Configuration) -> list[tuple[int, str]]:
    """`(task index, lottery seed)` per draw, in the order `report` pairs records against.

    The list position **is** the draw's identity. Everything about sharding rests on it: a
    shard carries the positions it ran, and `gather` puts them back in this order before any
    check sees them.
    """
    return [
        (task_index, seed)
        for task_index, task in enumerate(_tasks(configuration))
        for seed in task.lottery_seeds
    ]


def shard_draws(configuration: Configuration, shard: Shard) -> list[tuple[int, DrawRecord]]:
    """The draws belonging to one shard, each carrying its position in the whole.

    **The slices are interleaved, not contiguous, and that is a measurement rather than a
    preference.** The expanded list is ordered by task, and per-draw cost varies about tenfold
    across tasks — W1's heaviest at 4.8s a draw against W2's lightest at 0.45s, measured on
    this repository's own corpus. A contiguous slice of a list ordered that way is the worst
    distribution available: one shard would take W1's 200 draws and another a handful of W2's.
    Wall clock is the slowest shard, so contiguous slicing would build the whole mechanism and
    keep most of the imbalance.

    Interleaving costs nothing, because `gather` restores order by position and the assignment
    order is therefore free. Cost-aware packing would be better still and needs a per-draw
    estimate for the machine that will run it, which nobody has.

    Draws are regrouped by task before running, so a task's world is built once per shard
    rather than once per draw.
    """
    tasks = _tasks(configuration)
    grouped: dict[int, list[tuple[int, str]]] = {}
    for position, (task_index, seed) in enumerate(_expanded(configuration)):
        if position % shard.count == shard.index:
            grouped.setdefault(task_index, []).append((position, seed))

    slices: list[parallel.Task] = []
    positions: list[int] = []
    for task_index in sorted(grouped):
        pairs = grouped[task_index]
        slices.append(replace(tasks[task_index], lottery_seeds=tuple(seed for _, seed in pairs)))
        positions.extend(position for position, _ in pairs)

    records = parallel.run(slices, workers=configuration.workers)
    return list(zip(positions, records, strict=True))


def gather(
    parts: Iterable[Iterable[tuple[int, DrawRecord]]], configuration: Configuration
) -> list[DrawRecord]:
    """Every shard's draws, back in the order `report` requires — or a refusal.

    **This is where completeness is guaranteed, because `report` cannot do it.** A missing
    shard would otherwise produce a smaller denominator and a plausible rate: `U1`'s
    `8/200` computed over 150 draws is still a number, and nothing downstream would know. So a
    position that appears twice, or a position that never appears, is refused by name rather
    than averaged over.
    """
    seen: dict[int, DrawRecord] = {}
    for part in parts:
        for position, record in part:
            if position in seen:
                raise ShardError(f"draw {position} was delivered by more than one shard")
            seen[position] = record
    expected = len(_expanded(configuration))
    missing = [position for position in range(expected) if position not in seen]
    if missing:
        raise ShardError(
            f"{len(missing)} of {expected} draw(s) were not delivered by any shard — first "
            f"missing is {missing[0]}. Every rate here has the number of draws as its "
            "denominator, so a partial set produces a plausible number rather than an error."
        )
    return [seen[position] for position in range(expected)]


def draws(configuration: Configuration) -> list[DrawRecord]:
    """Every draw the configuration declares, in the order `_tasks` produces them.

    Split out from `run` so that producing the draws and judging them are separate operations
    on separate machines. `parallel.run` already restores task order for a reason its own
    docstring gives — *a published list of draws that reshuffles itself between runs is one
    nobody can diff* — and everything downstream depends on that order holding, because
    `report` pairs records with tasks positionally.
    """
    return parallel.run(_tasks(configuration), workers=configuration.workers)


def report(
    records: Sequence[DrawRecord],
    configuration: Configuration,
    *,
    contracts: ContractSet | None = None,
) -> Report:
    """Every check, over draws that already exist.

    Takes the records rather than producing them, so the same judgment runs whether they came
    from one machine or were gathered from several. It **cannot** verify that it was handed
    every draw the configuration declares — the count is published in `numbers` and the caller
    is what guarantees completeness, which is the same obligation `close` carries about the
    window it is handed.
    """
    resolved = contracts if contracts is not None else load()
    harness = resolved.aa_harness
    alpha = Fraction(resolved.inference.alpha)
    level = Fraction(harness.binomial_level)
    metric = resolved.metric_versions("category_margin_per_store_week")[-1]
    scale = scale_by_name(configuration.scale)

    by_world: dict[str, list[DrawRecord]] = {world: [] for world in sorted(WORLDS)}
    withheld: list[DrawRecord] = []
    for task, record in zip(
        [t for t in _tasks(configuration) for _ in t.lottery_seeds], records, strict=True
    ):
        (withheld if task.withhold_neighbour_pairs else by_world[record.world]).append(record)

    with tempfile.TemporaryDirectory(prefix="holdout-uplift-") as scratch:
        readout = worlds.write_readout(records, Path(scratch) / "readout.json")
        w6_window, _ = _truths(
            by_world["W6"], world="W6", configuration=configuration, contracts=resolved
        )
        w4_window, w4_first = _truths(
            by_world["W4"], world="W4", configuration=configuration, contracts=resolved
        )
        w5_window, _ = _truths(
            by_world["W5"], world="W5", configuration=configuration, contracts=resolved
        )
        del readout

    checks: list[Check] = []
    numbers: list[tuple[str, str]] = []

    if configuration.rates:
        checks.append(aa.false_positive_rate(by_world["W1"], alpha=alpha, level=level))
        checks.append(aa.p_values_are_not_piled_at_one_end(by_world["W1"]))
        checks.append(
            worlds.false_refusal_rate(
                by_world["W6"], maximum_pct=Fraction(harness.false_refusal_max_pct)
            )
        )
        numbers.append(aa.refusal_share(by_world["W1"]))
        numbers.extend(worlds.imbalance_share(by_world["W6"]))

    checks.append(coverage.coverage(by_world["W6"], w6_window, alpha=alpha, level=level))
    if configuration.rates:
        # A mean over a handful of draws is not a bias estimate any more than a rate over a
        # handful is a rate — and it is worse, because the scale it is judged against is the
        # spread of those same few draws. Measured at the machinery configuration it reported
        # a bias of 1.8 standard errors as a failure on three draws whose spread happened to
        # be small. So it is absent there rather than present and unreliable.
        bias_check, bias_numbers = coverage.bias(by_world["W6"], w6_window)
        checks.append(bias_check)
        numbers.extend(bias_numbers)

    minimum = Fraction(harness.per_world_min_correct_pct)
    pair_check, pair_numbers = worlds.interference_pair(
        by_world["W2"], withheld, minimum_pct=minimum
    )
    checks.append(pair_check)
    numbers.extend(pair_numbers)
    checks.append(
        worlds.neighbour_pairs_are_excluded(
            [r for world, rs in by_world.items() if world != "W2" for r in rs] + by_world["W2"]
        )
    )
    checks.append(worlds.exposure_refuses(by_world["W3"], minimum_pct=minimum))
    window_check, window_numbers = worlds.window_not_first_week(
        by_world["W4"], window_truth=w4_window, first_week_truth=w4_first
    )
    checks.append(window_check)
    numbers.extend(window_numbers)
    checks.append(worlds.power_or_width(by_world["W5"], truth=w5_window, alpha=alpha, level=level))

    first_seed = parallel.world_seeds(1)[0]
    checks.append(
        agreement.implementations_agree("W6", world_seed=first_seed, scale=scale, metric=metric)
    )
    checks.append(
        agreement.composition_is_exact(
            ("W1", "W6", "W2"), world_seed=first_seed, scale=scale, metric=metric
        )
    )
    checks.append(agreement.interval_inverts_the_test(records, alpha=alpha))

    numbers = [
        ("configuration", f"{configuration.label} at the {configuration.scale} scale"),
        ("draws", f"{len(records)} across {len(by_world)} worlds"),
        ("K on W1 and W6", f"{configuration.world_seeds} x {configuration.lotteries}"),
        *numbers,
    ]
    return Report(
        claim=2,
        title="No uplift without a valid holdout",
        checks=tuple(checks),
        numbers=tuple(numbers),
        notes=(
            "that the six worlds are every failure mode — they are the six we thought of, and "
            "the estimator's validity does not come from passing them: a difference of means "
            "over randomly assigned units is unbiased under any data-generating process, which "
            "is a theorem. The worlds test the machinery around the subtraction, not the "
            "subtraction",
            "that interference is detected at readout — it is not, in any world. The defence "
            "is the design engine's exclusion, and U6 measures what happens without it, which "
            "is a measurement of a gap rather than the closing of one",
            "claim 5, with two Python implementations. The dbt model and the SQL function are "
            "T011 and T012, and the deferral in docs/DECISIONS.md carries them as its unlock",
            f"anything about an estate larger than this one: the roster is {scale.stores} "
            "stores before the design engine's automatic exclusions, and no figure here is "
            "extrapolated past it",
            "that the world's prices are certified prices — the guardrail envelope is not on "
            "this path, and the deferral that says so names phase 2 as its unlock",
        ),
    )


def run(configuration: Configuration, *, contracts: ContractSet | None = None) -> Report:
    """Every draw, then every check. The seals are opened between the two and nowhere else."""
    return report(draws(configuration), configuration, contracts=contracts)
