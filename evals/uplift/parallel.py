"""The process pool, and the seed-in / record-out contract that shapes it.

`SealedAssignment.__reduce__` raises. That is not an obstacle this module works around — it is
the reason it has the shape it does. A seal that survived a round trip could be restored in a
process where no lottery ever ran, so nothing but **three strings goes in and a small frozen
record comes back**, and a worker re-derives its own lottery from the committed seed. A
parallel run and a single-process run of the same draw are then the same computation rather
than two arrangements of it, which is what makes `--serial` a debugging aid instead of a
second implementation.

**The unit of work is a world seed, not a draw**, and that is the whole budget. Building a
world seed's fixture costs one or two generations — about twenty-five seconds each — and every
lottery drawn against it then costs a readout. Handing single draws to the pool would rebuild
the fixture two hundred times.

Each worker loads the contracts itself. They are a few hundred kilobytes of frozen dataclasses
and pickling them per task would cost more than parsing them once per process; more to the
point, a worker that read its own contracts is a worker whose answer does not depend on what
the parent happened to be holding.
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

from corpus.world.scale import scale_by_name

from evals.uplift import harness
from holdout.contracts.loader import load


#: How many worker processes, when nobody says. `os.cpu_count()` on a laptop and four on a
#: GitHub runner, which is what the budget in the SPEC is priced against.
def default_workers() -> int:
    return max(1, os.cpu_count() or 1)


@dataclass(frozen=True, slots=True)
class Task:
    """One world seed's worth of work — the fixture, then every lottery against it."""

    world: str
    world_seed: str
    scale: str
    lottery_seeds: tuple[str, ...]
    #: W2's second arm: the same lotteries with the interfering pairs not declared to the
    #: engine, so the eval can publish what the exclusion is worth.
    withhold_neighbour_pairs: bool = False
    permutation_draws: int | None = None

    @property
    def label(self) -> str:
        suffix = "/withheld" if self.withhold_neighbour_pairs else ""
        return f"{self.world}@{self.world_seed}{suffix}"


def run_task(task: Task) -> tuple[harness.DrawRecord, ...]:
    """Everything one world seed produces. Runs in a worker, and reads its own contracts."""
    contracts = load()
    fixture = harness.build_fixture(
        task.world,
        world_seed=task.world_seed,
        scale=scale_by_name(task.scale),
        contracts=contracts,
    )
    return tuple(
        harness.run_one(
            fixture,
            lottery_seed=seed,
            contracts=contracts,
            harness=contracts.aa_harness,
            withhold_neighbour_pairs=task.withhold_neighbour_pairs,
            permutation_draws=task.permutation_draws,
        )
        for seed in task.lottery_seeds
    )


def run(tasks: Sequence[Task], *, workers: int | None = None) -> list[harness.DrawRecord]:
    """Every task, in parallel, with the records gathered in the order the tasks were given.

    Order is restored deliberately: a rate computed over records in completion order is the
    same rate, but a *published* list of draws that reshuffles itself between runs is one
    nobody can diff. Reproducibility here costs a sort.
    """
    if not tasks:
        return []
    size = workers if workers is not None else default_workers()
    if size <= 1:
        return [record for task in tasks for record in run_task(task)]
    gathered: list[list[harness.DrawRecord]] = [[] for _ in tasks]
    with ProcessPoolExecutor(max_workers=size) as pool:
        futures = {pool.submit(run_task, task): index for index, task in enumerate(tasks)}
        for future in futures:
            gathered[futures[future]] = list(future.result())
    return [record for batch in gathered for record in batch]


def lottery_seeds(world: str, world_seed: str, count: int) -> tuple[str, ...]:
    """The lottery seeds for one world seed. Spelled out, so a draw can be re-run by name."""
    return tuple(f"{world}/{world_seed}/lottery-{index:03d}" for index in range(count))


def world_seeds(count: int, *, prefix: str = "holdout-w") -> tuple[str, ...]:
    """The world seeds, spelled out for the same reason."""
    return tuple(f"{prefix}-{index:04d}" for index in range(1, count + 1))


def chunks(records: Sequence[harness.DrawRecord], world: str) -> Iterator[harness.DrawRecord]:
    return (record for record in records if record.world == world)
