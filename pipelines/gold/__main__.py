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

from pipelines import session as runtime
from pipelines.gold import session
from pipelines.gold.build import build, priced


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipelines.gold", description=__doc__)
    parser.add_argument(
        "--silver", type=Path, help="Silver as directories, where there is no catalog."
    )
    parser.add_argument(
        "--silver-schema", help="Silver as a catalog schema. Exactly one of the two."
    )
    parser.add_argument("--catalog")
    parser.add_argument("--root", type=Path, help="Where a local session puts its warehouse.")
    # **`priced` and `all` are two callers, not two moods.** On the estate the analytical models
    # are built by the job's `dbt` task against a warehouse, so the Python step must write the
    # priced tables and stop; running dbt a second time in this process would build the same
    # models twice, from a session that on serverless cannot exist. Locally there is no dbt task
    # and `all` is the whole build.
    parser.add_argument("--only", choices=("all", "priced"), default="all")
    args = parser.parse_args(argv)

    if args.only == "all" and args.root is None:
        parser.error("--root is required for --only all: dbt writes its warehouse there.")
    if args.root is not None:
        args.root.mkdir(parents=True, exist_ok=True)

    spark = session.build(args.root)
    try:
        runtime.use_catalog(spark, args.catalog)
        if args.only == "priced":
            counts, unpriced = priced(spark, args.silver, silver_schema=args.silver_schema)
            _report_priced(counts, unpriced)
            return 0
        if args.silver is None:
            parser.error("--only all reads silver from directories: pass --silver.")
        built = build(spark, args.silver, root=args.root, silver_schema=args.silver_schema)
    finally:
        runtime.release(spark)

    print(f"gold    {args.silver or args.silver_schema} -> {args.root}/warehouse")
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


def _report_priced(counts: dict[str, int], unpriced: int) -> None:
    """What the estate's first gold task produced, in the shape the full build prints it."""
    print("gold    priced tables only; the models are dbt's task\n")
    for name, rows in counts.items():
        print(f"  {name:<34} {rows:>10,}")
    print(
        f"\n  {'sales with no published cost':<34} {unpriced:>10,}"
        "  <- no margin row: revenue with a null cost would enter the metric as pure margin"
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
