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

from pipelines.silver import session
from pipelines.silver.build import build


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipelines.silver", description=__doc__)
    parser.add_argument("--bronze", type=Path, required=True)
    parser.add_argument("--silver", type=Path, required=True)
    parser.add_argument("--cores", type=int, default=session.LOCAL_CORES)
    args = parser.parse_args(argv)

    spark = session.build(cores=args.cores)
    try:
        counts = build(spark, args.bronze, args.silver)
    finally:
        spark.stop()

    print(f"silver  {args.bronze} -> {args.silver}")
    print("        counts over this bronze directory, not properties of the rules\n")
    for name, rows in counts.items():
        marker = "  <- kept, not dropped" if name == "quarantine" else ""
        print(f"  {name:<18} {rows:>10,}{marker}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
