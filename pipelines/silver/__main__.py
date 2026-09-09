"""`python -m pipelines.silver` — build silver from bronze and print what was quarantined.

    uv sync --extra spark
    python -m pipelines.ingest.bulk export  --scale smoke --day 2025-09-02 --landing .land
    python -m pipelines.ingest.bulk history --scale smoke --landing .land
    python -m pipelines.ingest.bulk load    --landing .land --bronze .bronze
    python -m pipelines.silver --bronze .bronze --silver .silver

Every number it prints is a count over one bronze directory, and the header says so: what a
quarantine holds is a fact about the data that arrived, never a property of the rules.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipelines import session as runtime
from pipelines.silver import session
from pipelines.silver.build import build


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipelines.silver", description=__doc__)
    parser.add_argument("--bronze", type=Path, required=True)
    parser.add_argument(
        "--silver", type=Path, help="Where silver goes on a machine with no catalog."
    )
    parser.add_argument(
        "--silver-schema",
        help="Where silver goes where there is a catalog. Exactly one of this and --silver.",
    )
    # **The catalog is named or it is the workspace's default.** `pipelines/session.py` carries
    # what that costs: a two-part table name resolves against whatever catalog is current, and
    # a run that wrote its tables into the wrong one reports success.
    parser.add_argument("--catalog")
    parser.add_argument("--cores", type=int, default=session.LOCAL_CORES)
    args = parser.parse_args(argv)

    with session.sessions(cores=args.cores) as spark:
        runtime.use_catalog(spark, args.catalog)
        counts = build(spark, args.bronze, args.silver, schema=args.silver_schema)

    destination = args.silver_schema or args.silver
    print(f"silver  {args.bronze} -> {destination}")
    print("        counts over this bronze directory, not properties of the rules\n")
    for name, rows in counts.items():
        marker = "  <- kept, not dropped" if name == "quarantine" else ""
        print(f"  {name:<18} {rows:>10,}{marker}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
