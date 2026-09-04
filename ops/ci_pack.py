"""How many machines the run asks for, and which targets share one.

**The run was slot-bound, not time-bound, and nobody had measured it.** Twenty jobs against a
documented ceiling of twenty, holding work that fits in about six: ten unsharded entries carried
**2,375s** while the critical chain — the slowest shard leg plus the combine that waits on it —
was **1,032s**. Every one of those ten had slack, and `T012` could not start because it wanted
two more.

The first two answers considered both bought slots by tuning the **one** number that is on the
critical path. Shaving `CLAIM_2_SHARDS` from 7 to 5 buys two slots for 114 seconds of run;
packing buys them for nothing, because **a bin does not touch the run until it exceeds the
chain.**

Why this is a rule and not a grouping
-------------------------------------
A maintained list of which targets share a job is a list somebody has to re-open every time a
target arrives — and this repository has spent a day on the difference between a rule and a list
wearing a rule's clothes. Here nobody makes a packing decision when a target arrives:
**`packable_work / budget` is the whole arithmetic.** A new target adds *work*, falls into an
existing bin while the total stays under a multiple of the budget, and costs one more bin when it
does not. Never one slot each.

The two numbers, which are different questions
----------------------------------------------
`CI_ENTRY_BUDGET` is **where the packer stops adding**. `CI_ENTRY_CEILING` is **where a bin
starts costing the run**, and a packed job checks itself against that one.

They were nearly the same number, and that would have been a flake generator: packing to a budget
puts every bin *at* the budget by construction — the largest here is 777 of 800, three percent
under — so a self-check at the budget would fire on ordinary variance nearly every run, and
`claim-2-tests` moves 19% across four runs of unchanged work. The ceiling is the chain, 255s
above the largest bin, so only a genuinely stale cost trips it.

What this module does not know
------------------------------
**It cannot check a declared cost against reality.** No local gate can: the truth is in run
history, and a test that reached for it would be flaky and would need the network. What checks a
cost is the packed job itself, comparing its own elapsed time against the ceiling — so a stale
cost becomes a red run naming the exact bin rather than a slow run nobody attributes.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Where the budget and every cost are declared. The Makefile, because that is where the targets
#: are and where `discover` already reads `<TARGET>_SHARDS` from — so `ci.yml` still names no
#: claim and no number.
MAKEFILE = "Makefile"

BUDGET_NAME = "CI_ENTRY_BUDGET"
CEILING_NAME = "CI_ENTRY_CEILING"


class DeclarationMissingError(RuntimeError):
    """A number this module needs is not declared, and it will not be guessed at."""


def _declared(makefile: str, name: str) -> int | None:
    found = re.search(rf"^{re.escape(name)}[ \t]*:=[ \t]*([0-9]+)", makefile, re.MULTILINE)
    return int(found.group(1)) if found else None


def cost_variable(target: str) -> str:
    """`claim-2-tests` -> `CLAIM_2_TESTS_COST`, by the transform `discover` already uses.

    Derived rather than tabulated, for the reason the shard count is: a table mapping targets to
    variable names would be a second registry of the targets, kept by hand, in the layer that
    exists so nobody has to keep one.
    """
    return target.upper().replace("-", "_") + "_COST"


def budget(makefile: str) -> int:
    value = _declared(makefile, BUDGET_NAME)
    if value is None:
        raise DeclarationMissingError(
            f"the Makefile declares no {BUDGET_NAME}, so there is nothing to pack under. "
            "An unpacked matrix would still be correct and would silently ask for one machine "
            "per target, which is the arrangement this replaced — so this refuses instead."
        )
    return value


def ceiling(makefile: str) -> int:
    value = _declared(makefile, CEILING_NAME)
    if value is None:
        raise DeclarationMissingError(
            f"the Makefile declares no {CEILING_NAME}, so a packed job would have nothing to "
            "check its own duration against and a stale cost would show up as a slow run "
            "nobody attributes."
        )
    return value


def cost(makefile: str, target: str, *, default: int) -> int:
    """One target's declared cost, or the whole budget when it has none.

    **Unmeasured means unpacked**, and the direction matters: an unknown treated as *cheap*
    would pack a new target into a bin it might blow, and the failure would be a red run
    somebody has to diagnose. An unknown treated as the whole budget gives it its own machine,
    which costs one slot and nothing else, until somebody measures it.
    """
    value = _declared(makefile, cost_variable(target))
    return default if value is None else value


def pack(targets: list[str], makefile: str) -> list[list[str]]:
    """Place every target into a bin under the budget. First-fit over descending cost.

    **The ordering is the load-bearing part, not the packing quality.** Sorted by cost
    descending and then by name, so the result is a pure function of the declared numbers: a
    bin's slug is its contents, that slug is the world cache's namespace, and a packing that
    reshuffled between runs would leave every cache cold. That is measured rather than feared —
    it is exactly what changing `CLAIM_2_SHARDS` from 8 to 7 did to seven caches.

    First-fit-decreasing is not optimal and is not trying to be. It is deterministic, it is
    readable, and at this size the difference from optimal is under one bin.
    """
    limit = budget(makefile)
    ordered = sorted(targets, key=lambda t: (-cost(makefile, t, default=limit), t))
    bins: list[list[str]] = []
    for target in ordered:
        for existing in bins:
            if (
                sum(cost(makefile, t, default=limit) for t in existing)
                + cost(makefile, target, default=limit)
                <= limit
            ):
                existing.append(target)
                break
        else:
            # A target costing more than the budget lands here alone, and that is a signal
            # rather than an error: at a budget of 700, `claim-1` at 712 would be one.
            bins.append([target])
    return bins


def entries(targets: list[str], makefile: str) -> list[dict[str, str]]:
    """The matrix rows `discover` emits for the unsharded targets, packed.

    `target` carries the whole bin, space separated, because `ci.yml` runs
    `make ${{ matrix.target }}` unquoted and `make` takes several targets on one line. That is
    not a change to the run step; it is what the run step already did.
    """
    return [
        {"target": " ".join(one), "shard": "", "slug": "-".join(one), "name": " ".join(one)}
        for one in pack(targets, makefile)
    ]


def main(argv: list[str]) -> int:
    """`python3 -m ops.ci_pack <target>...` — the packed matrix rows, as JSON, on stdout."""
    makefile = (REPO_ROOT / MAKEFILE).read_text(encoding="utf-8")
    print(json.dumps(entries(argv, makefile)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
