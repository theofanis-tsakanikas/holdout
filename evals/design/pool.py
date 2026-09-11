"""The process pool the eval's expensive phases share, and why it is seed-in, record-out.

Two phases of `evals.design` are embarrassingly parallel and dominate its cost: the guards-off
number for every refused design (`grade.anyway`, one exact-arithmetic permutation test per
design) and the violations (`violate.peeking` and `violate.post_hoc`, several per design per
lottery). Both run through here.

**A worker is handed an index and a seed and hands back a record.** It rebuilds the contracts,
the world and the recording itself on first use rather than receiving them pickled, because
the world is a few hundred megabytes of ledgers and the recording is read off disk in
milliseconds. What crosses the process boundary is a task of three strings and a frozen
result -- which is what makes a parallel run and a serial run the same computation: the
tasks are enumerated in order and collected in that order whatever the pool did with them.

`workers=1` runs in-process. It is the debugging aid and not a second implementation.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from concurrent.futures import ProcessPoolExecutor

from evals.design import build

_WORKER: dict[str, object] = {}


def worker_state() -> tuple[build.ContractSet, build.World, build.Recording]:
    """The contracts, the world and the recording, built once per process."""
    if not _WORKER:
        contracts = build.contracts()
        _WORKER["contracts"] = contracts
        _WORKER["world"] = build.world(contracts)
        _WORKER["recording"] = build.recording()
    return (
        _WORKER["contracts"],  # type: ignore[return-value]
        _WORKER["world"],
        _WORKER["recording"],
    )


def run[T, R](task: Callable[[T], R], tasks: Iterable[T], *, workers: int | None = None) -> list[R]:
    """Every task, in order, across the pool -- or in-process when `workers` is 1."""
    ordered = list(tasks)
    size = workers if workers is not None else max(1, os.cpu_count() or 1)
    if size == 1:
        return [task(t) for t in ordered]
    with ProcessPoolExecutor(max_workers=size) as pool:
        return list(pool.map(task, ordered))
