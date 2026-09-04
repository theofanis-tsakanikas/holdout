"""`python -m pipelines.ml` — build a corpus, train on it, print what the gates said.

Prints the assessment whether it passed or refused, at the same size, for the reason the
experiment readout dashboard prints a refusal at the same size as an uplift: a run whose failure
is quieter than its success teaches everyone to read only the successes.

**Exit code 0 on a refusal.** A gate that refused did its job, and this entry point is a
demonstration rather than a gate — `make check` runs the tests, and those are what go red. An
exit code here that failed on a refused model would make the demonstration unrunnable on exactly
the corpus that shows it working.
"""

from __future__ import annotations

import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

SCALE = "rehearsal"
WORLD = "W1"
SEED = "training"
DAY = "2025-09-02"


def main() -> int:
    from corpus.world import prepare
    from corpus.world.scale import CLOSE_HOUR, OPEN_HOUR

    from holdout.contracts.loader import load
    from holdout.core.demand.censoring import TradingWindow
    from pipelines.gold import session as gold_session
    from pipelines.gold.build import register_silver
    from pipelines.ingest import bulk, erp
    from pipelines.ml.build import from_silver, train
    from pipelines.silver.build import build as build_silver

    settings = load().training
    # Read from the corpus that produced the rows rather than declared here, the same way
    # `evals/censoring/build.py` reads it. A trading window written down in two places is two
    # definitions of when a shop is open, and the one that is wrong is the one nobody re-reads.
    window = TradingWindow(open_hour=OPEN_HOUR, close_hour=CLOSE_HOUR)
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        run = prepare(WORLD, seed=SEED, scale=SCALE)
        erp.export(run, root / "landing", day=date.fromisoformat(DAY))
        erp.history(run, root / "landing")
        bulk.load(
            root / "landing",
            root / "bronze",
            arrived_at=datetime(2026, 9, 4, 9, 0),  # noqa: DTZ001 — the corpus is naive
        )
        spark = gold_session.build(root)
        try:
            build_silver(spark, root / "bronze", root / "silver")
            # **Reused rather than rewritten.** Mounting a silver Delta directory as a table is a
            # local-only step -- on the estate silver is a Unity Catalog schema and there is
            # nothing to mount -- and `pipelines/gold/build.py` already owns it. A second
            # implementation here would be two definitions of where silver lives.
            register_silver(spark, root / "silver", schema=gold_session.SCHEMA)
            days = from_silver(spark, gold_session.SCHEMA, window=window)
        finally:
            spark.stop()

    trained = train(days, settings, window=window)
    width = max(len(name) for name, _ in trained.summary)
    for name, value in trained.summary:
        print(f"{name:<{width}}  {value}")
    print()
    print(trained.assessment)
    return 0


if __name__ == "__main__":
    sys.exit(main())
