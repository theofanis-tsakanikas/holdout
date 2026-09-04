"""`python -m pipelines.gold` — build gold from silver and print what came out.

    uv sync --extra dbt
    python -m pipelines.ingest.bulk export  --scale smoke --day 2025-09-02 --landing .land
    python -m pipelines.ingest.bulk history --scale smoke --landing .land
    python -m pipelines.ingest.bulk load    --landing .land --bronze .bronze
    python -m pipelines.silver --bronze .bronze --silver .silver
    python -m pipelines.gold   --silver .silver --root .gold

`--root` is where Spark's warehouse and its Derby metastore go, and it has no default: a session
that fell back to the working directory would write `spark-warehouse/`, `metastore_db/` and
`derby.log` into whatever it was run from, which for a run from the repository root is the
repository. That is doctrine rule 3 with a directory instead of a value — the same argument
`pipelines/silver/pipeline.py` makes about its bronze root.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipelines.gold import session
from pipelines.gold.build import build


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipelines.gold", description=__doc__)
    parser.add_argument("--silver", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--cores", type=int, default=session.LOCAL_CORES)
    args = parser.parse_args(argv)

    args.root.mkdir(parents=True, exist_ok=True)
    spark = session.build(args.root, cores=args.cores)
    try:
        built = build(spark, args.silver, root=args.root)
    finally:
        spark.stop()

    print(f"gold    {args.silver} -> {args.root}/warehouse")
    print("        counts over this silver directory, not properties of the models\n")
    for name, rows in built.priced.items():
        print(f"  {name:<34} {rows:>10,}")
    print()
    for name, rows in built.tables.items():
        marker = "  <- compiled from a contract" if name.endswith(("_v1", "_v3")) else ""
        print(f"  {name:<34} {rows:>10,}{marker}")
    print(
        f"\n  {'sales with no published cost':<34} {built.unpriced_sales:>10,}"
        "  <- no margin row: revenue with a null cost would enter the metric as pure margin"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
