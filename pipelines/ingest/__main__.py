"""`python -m pipelines.ingest` — drive one world and print what arrived.

The numbers it prints are the ones T009's `stop_at` is about: *when the driver produces a
stream with the declared pathologies*. They are **measurements of one seed and one scale** and
say so on the line above them, because a share is a parameter and what a share produced is not.

    python -m pipelines.ingest --world W1 --scale smoke --seed t009 --out .ingest
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from corpus.world import events as world_events
from corpus.world import prepare
from corpus.world.events import ShelfDay

from pipelines.ingest.driver import DECLARED, Outage, Pathologies, deliveries, out_of_order
from pipelines.ingest.sink import JsonlSink


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipelines.ingest", description=__doc__)
    parser.add_argument("--world", default="W1")
    parser.add_argument("--scale", default="smoke")
    parser.add_argument("--seed", default="t009")
    parser.add_argument("--out", type=Path, default=None, help="write JSONL here")
    parser.add_argument("--outage-store", default=None)
    parser.add_argument("--outage-hours", type=int, default=2)
    args = parser.parse_args(argv)

    records = list(world_events(prepare(args.world, seed=args.seed, scale=args.scale)))
    pathologies = DECLARED
    if args.outage_store:
        timed = [r for r in records if not isinstance(r, ShelfDay)]
        opens = min(r.event_ts for r in timed)
        pathologies = Pathologies(
            outage=Outage(args.outage_store, opens, args.outage_hours),
        )

    delivered = deliveries(records, seed=args.seed, pathologies=pathologies)

    late = len(
        [
            record
            for _, record in delivered
            if not isinstance(record, ShelfDay) and record.arrival_ts > record.event_ts
        ]
    )
    print(f"ingest  {args.world} at {args.scale}, seed {args.seed}")
    print("        measurements of this seed and this scale, not properties of the driver\n")
    print(f"  produced by the corpus        {len(records)}")
    print(f"  delivered                     {len(delivered)}")
    print(f"  delivered twice               {len(delivered) - len(records)}")
    print(f"  arrived after their event     {late}")
    print(f"  behind a stream's high-water  {out_of_order(delivered)}")
    if args.outage_store:
        print(f"  held by the outage at {args.outage_store} for {args.outage_hours}h")

    if args.out is not None:
        sink = JsonlSink(args.out)
        for stream, record in delivered:
            sink.deliver(stream, record)
        sink.close()
        print("")
        for stream, count in sorted(sink.counts.items()):
            print(f"  {stream:<18} {count:>8} line(s) -> {args.out / f'{stream}.jsonl'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
