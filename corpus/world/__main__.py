"""`python -m corpus.world` — build a world, count one, or look inside a seal.

Three subcommands, and the split between them is the point:

``count``   how many records of each kind, keeping none of them. This is what produced the
            scenario figure in `README.md`, and it is a command anybody can re-run.
``write``   materialise a world to a directory: four event streams, three reference tables,
            the run's manifest and the seal.
``seal``    the seal's header and its ledger of openings. Never the payload — opening it
            takes a readout, and a readout is not something a command line hands over by
            accident.

Nothing here is committed. A world is a pure function of `(world, seed, scale)`, so the corpus
is regenerated rather than stored — which is the opposite of `corpus/real/`, where the data is
committed and digest-checked precisely because it *cannot* be regenerated: it was collected by
hand in shops by people who have never seen this repository.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from corpus.world import count, prepare, write
from corpus.world.scale import SCALES
from corpus.world.seal import SEAL_FILENAME, header
from corpus.world.worlds import WORLDS

DEFAULT_SEED = "holdout-w-0001"


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--world", default="W6", choices=sorted(WORLDS), help="which world")
    parser.add_argument("--seed", default=DEFAULT_SEED, help="the world seed")
    parser.add_argument("--scale", default="smoke", choices=sorted(SCALES), help="how big")
    parser.add_argument(
        "--only-stores",
        default=None,
        help=(
            "comma-separated store ids. A window onto the same world, not a smaller one — "
            "a count over a restriction is reported as such and is never multiplied up."
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="corpus.world", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    counter = sub.add_parser("count", help="count the records, keep none of them")
    _common(counter)

    writer = sub.add_parser("write", help="materialise a world into a directory")
    _common(writer)
    writer.add_argument("--out", required=True, type=Path, help="where to write it")

    reader = sub.add_parser("seal", help="a seal's header and its ledger — never its payload")
    reader.add_argument(
        "path", type=Path, help=f"the seal, or the directory holding {SEAL_FILENAME}"
    )

    args = parser.parse_args(argv)

    if args.command == "seal":
        path = args.path / SEAL_FILENAME if args.path.is_dir() else args.path
        print(json.dumps(header(path), indent=2))
        return 0

    only = tuple(args.only_stores.split(",")) if args.only_stores else None
    run = prepare(args.world, seed=args.seed, scale=args.scale)
    print(f"{run.world.id} · {run.world.title}", file=sys.stderr)
    print(f"        {run.scale}", file=sys.stderr)
    print(
        f"        control {run.control.policy_id} · treatment {run.treatment.policy_id}",
        file=sys.stderr,
    )
    print(
        f"        {len(run.treated)} of {len(run.chain.stores)} stores treated · "
        f"{len(run.chain.neighbour_pairs)} neighbour pairs inside the radius",
        file=sys.stderr,
    )
    if only:
        print(f"        restricted to {len(only)} stores — a window, not a total", file=sys.stderr)

    counts = (
        write(run, args.out, only_stores=only)
        if args.command == "write"
        else count(run, only_stores=only)
    )
    for stream, number in counts.items():
        print(f"{stream:>16}  {number:>12,}")
    print(f"{'total':>16}  {sum(counts.values()):>12,}")
    if args.command == "write":
        print(f"\nwritten to {args.out} · truth sealed in {args.out / SEAL_FILENAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
