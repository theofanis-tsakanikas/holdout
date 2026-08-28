"""How much of an estate an experiment may actually use — measured, per world.

`make roster`, and the figure `corpus/world/README.md` records.

**Why this lives in `ops/` and not in `corpus/`.** The number is a joint fact about two things
that may not see each other: the geography `corpus/world/chain.py` lays out, and the exclusion
rule `holdout.core.design.feasibility` applies to it. The corpus may not import the system —
`ops/isolation.py` is the barrier and it points one way — so a `corpus.world` subcommand could
only answer this by re-implementing the exclusion rule, which would be a second definition of
it and the one that goes stale. `ops/` is where the rules the product code is measured by
already live, and it is allowed to hold both.

**Why the number exists at all.** T00E. The design engine excludes the later-sorted member of
every pair inside the declared neighbour radius, so every clustered store the generator opens
is a store no experiment may use. Both halves were deliberate and documented; nobody had
multiplied them together. Measured on 2026-08-28, before T00E: 100 stores gave 109 pairs and a
**roster of 45**, and adding stores made it worse rather than better because the estate got
denser rather than larger. `CLAUDE.md` now says it in one line — the size that decides whether
anything is provable is the surviving roster, not the store count — and this is the command
that prints it.

It is a **measurement, not a gate.** It runs no assertion and returns 0 whatever it finds:
what the surviving roster has to be is declared in `TASKS.md` and checked by the eval that
depends on it, and a threshold here would be a third place that number lives.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from corpus.world.chain import build as build_chain
from corpus.world.scale import SCALES, Scale, scale_by_name
from corpus.world.worlds import WORLDS, World

from holdout.contracts.loader import load
from holdout.core.design import neighbour_exclusions

#: The seed the README's figures are taken at. A chain is a function of its seed, so another
#: seed is another hundred shops in another arrangement — the figure is reported with the seed
#: that produced it, exactly as the corpus's counts are.
DEFAULT_SEED = "holdout-w-0001"


def surviving(world: World, *, seed: str, scale: Scale, holdout_share_pct: int) -> dict[str, int]:
    """One world's estate, and what is left of it after the automatic exclusions.

    The exclusion rule is imported, never restated. A copy of it here would agree with the
    engine on the day it was written and drift afterwards, and the drift would show up as a
    roster that the harness could not reproduce.
    """
    chain = build_chain(seed, scale, clustered_pct=world.clustered_pct)
    roster = tuple(store.store_id for store in chain.stores)
    excluded = neighbour_exclusions(roster, chain.neighbour_pairs, frozenset())
    left = len(roster) - len(excluded)
    return {
        "stores": len(roster),
        "clustered_pct": world.clustered_pct,
        "pairs": len(chain.neighbour_pairs),
        "excluded": len(excluded),
        "roster": left,
        "controls": left * holdout_share_pct // 100,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ops.roster", description=__doc__)
    parser.add_argument("--scale", default="harness", choices=sorted(SCALES))
    parser.add_argument("--seed", default=DEFAULT_SEED)
    args = parser.parse_args(argv)

    scale = scale_by_name(args.scale)
    share = int(load().inference.holdout_share_pct)
    print(f"{scale}", file=sys.stderr)
    print(f"        seed {args.seed} · holdout share {share}%", file=sys.stderr)
    header = f"{'world':>6}  {'cluster':>8}  {'stores':>7}  {'pairs':>7}  {'excluded':>9}  "
    print(header + f"{'roster':>7}  {'controls':>9}")
    for world_id in sorted(WORLDS):
        row = surviving(WORLDS[world_id], seed=args.seed, scale=scale, holdout_share_pct=share)
        print(
            f"{world_id:>6}  {row['clustered_pct']:>7}%  {row['stores']:>7,}  "
            f"{row['pairs']:>7,}  {row['excluded']:>9,}  {row['roster']:>7,}  "
            f"{row['controls']:>9,}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
