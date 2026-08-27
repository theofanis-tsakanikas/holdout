"""Which arm a store is in — as an **input** to the world, never a decision of it.

The lottery belongs to `src/holdout/core/experiment/`: assignment from a committed seed,
exactly reproducible, written before the period opens and then read-only. That is claim 3, and
it is not this package's to make. The world is handed a mapping and simulates what a chain
would do under it.

Keeping the direction that way round is what lets the A/A harness re-draw K = 200 assignments
against **one** world and see what the system does with each — and it is what stops the
generator ever agreeing with the assignment engine, because it has never met it.

`alternating` exists for tests and for the command line. It is not a lottery and says so in
its own name: nothing about it is random, and no claim rests on it.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from corpus.world.chain import Chain


class Arm(StrEnum):
    """Two arms. `CONTROL` is the existing policy, never "nothing"."""

    CONTROL = "control"
    TREATMENT = "treatment"


#: Store id to arm. Every store in the chain must appear; `generate` refuses a partial one,
#: because a store with no arm would silently take the control path and quietly shrink the
#: experiment.
Assignment = Mapping[str, Arm]


def all_control(chain: Chain) -> dict[str, Arm]:
    """The counterfactual. Generating a world under this and under a real assignment gives
    the same numbers for every store whose policy did not change — see `rng`."""
    return {store.store_id: Arm.CONTROL for store in chain.stores}


def alternating(chain: Chain, treated_share: int = 50) -> dict[str, Arm]:
    """Every n-th store treated, by store ordinal. Deterministic, and not a lottery.

    A convenience for exercising the generator, and deliberately a bad experimental design:
    it is perfectly balanced on nothing in particular, it is trivially predictable, and it
    would fail a pre-period balance check as often as chance dictates. Nothing in `evals/`
    may use it to produce a number.
    """
    if not 0 <= treated_share <= 100:
        raise ValueError("treated_share is a percentage of stores")
    if treated_share == 0:
        return all_control(chain)
    every = max(1, round(100 / treated_share))
    return {
        store.store_id: (Arm.TREATMENT if index % every == 0 else Arm.CONTROL)
        for index, store in enumerate(chain.stores)
    }
