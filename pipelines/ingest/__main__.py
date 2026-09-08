"""`python -m pipelines.ingest` — drive one world and print what arrived.

The numbers it prints are the ones T009's `stop_at` is about: *when the driver produces a
stream with the declared pathologies*. They are **measurements of one seed and one scale** and
say so on the line above them, because a share is a parameter and what a share produced is not.

    python -m pipelines.ingest --world W1 --scale smoke --seed t009 --out .ingest
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from corpus.world import Format, business_date_of, prepare, write
from corpus.world import events as world_events
from corpus.world.events import ShelfDay

from pipelines import window as window_module
from pipelines.ingest.arms import arms_for
from pipelines.ingest.driver import DECLARED, Outage, Pathologies, deliveries, out_of_order
from pipelines.ingest.sink import JsonlSink


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipelines.ingest", description=__doc__)
    parser.add_argument("--world", default="W1")
    parser.add_argument("--scale", default="smoke")
    parser.add_argument("--seed", default="t009")
    parser.add_argument("--out", type=Path, default=None, help="write JSONL here")
    parser.add_argument(
        "--day",
        default=None,
        help=(
            "the one business date to drive, or `after-window` for the day after the "
            "comparison window closes. Without it, every day the world has."
        ),
    )
    parser.add_argument(
        "--landing",
        type=Path,
        default=None,
        help="write the delivered stream as Parquet here, where the bulk load will find it",
    )
    parser.add_argument("--into", default="live", help="the subdirectory of --landing to write")
    parser.add_argument("--arms", choices=("alternating", "all-control", "table"), default="table")
    parser.add_argument("--assignment-schema")
    parser.add_argument("--experiment-id")
    parser.add_argument("--catalog")
    parser.add_argument("--outage-store", default=None)
    parser.add_argument("--outage-hours", type=int, default=2)
    args = parser.parse_args(argv)

    # **The arms are the committed ones, not the package's convenience.** The live day runs
    # after the comparison window has closed and the estate is still running the policy each
    # store was assigned; generating it under `alternating` would be a third experiment, and
    # `corpus/world/__init__.py` says in as many words that alternating is not a lottery.
    base = prepare(args.world, seed=args.seed, scale=args.scale)
    run = prepare(args.world, seed=args.seed, scale=args.scale, assignment=arms_for(args, base))
    records = list(world_events(run))
    # **One day, and it is filtered before the driver sees it.** `run.yml` calls this step
    # *driving one day* and it drove every day the world had — at the estate's scale, eight
    # months of events a second time. Filtering here rather than after `deliveries` keeps the
    # lateness and the duplicates being this day's: a record delivered twice is two copies of a
    # day that was driven, not of a day that was thrown away.
    if args.day:
        wanted = (
            window_module.live_day(args.scale)
            if args.day == window_module.AFTER_WINDOW
            else date.fromisoformat(args.day)
        )
        records = [record for record in records if business_date_of(record) == wanted]
        if not records:
            raise SystemExit(
                f"{wanted} is not a day this world has. The corpus runs from "
                f"{run.scale.start_date} for {run.scale.days} days."
            )
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
    print(f"ingest  {args.world} at {args.scale}, seed {args.seed}, day {args.day or 'every'}")
    print("        measurements of this seed and this scale, not properties of the driver\n")
    print(f"  produced by the corpus        {len(records)}")
    print(f"  delivered                     {len(delivered)}")
    print(f"  delivered twice               {len(delivered) - len(records)}")
    print(f"  arrived after their event     {late}")
    print(f"  behind a stream's high-water  {out_of_order(delivered)}")
    if args.outage_store:
        print(f"  held by the outage at {args.outage_store} for {args.outage_hours}h")

    if args.landing is not None:
        # **Parquet into the landing zone, because that is the only shape bronze can read.**
        # `bulk.load` takes `.csv.gz` and `.parquet` and nothing else, so the JSONL below —
        # which is what `run.yml` was producing, into a directory named `s3:` on a runner that
        # then went away — could not have become bronze even if it had landed.
        counts = write(
            run,
            args.landing / args.into,
            fmt=Format.PARQUET,
            records=[record for _stream, record in delivered],
        )
        print("")
        for stream, count in sorted(counts.items()):
            print(f"  {stream:<18} {count:>8} row(s) -> {args.landing / args.into}")

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
