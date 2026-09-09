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

import argparse
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from pipelines import session as runtime

if TYPE_CHECKING:
    from holdout.core.demand.censoring import TradingWindow
    from pipelines.ml.features import ShelfDay

SCALE = "rehearsal"
WORLD = "W1"
SEED = "training"
DAY = "2025-09-02"


def _from_corpus(window: TradingWindow) -> list[ShelfDay]:
    """A world built here, loaded here, and thrown away here. The demonstration on a laptop.

    Every import is inside the function for the reason `tests/boundary/` polices: `corpus/` is
    not a dependency of anything that runs on the estate, and this branch is the only caller.
    """
    from corpus.world import prepare

    from pipelines.gold import session as gold_session
    from pipelines.gold.build import register_silver
    from pipelines.ingest import bulk, erp
    from pipelines.ml.build import from_silver
    from pipelines.silver.build import build as build_silver

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
        with gold_session.sessions(root) as spark:
            build_silver(spark, root / "bronze", root / "silver")
            # **Reused rather than rewritten.** Mounting a silver Delta directory as a table is a
            # local-only step -- on the estate silver is a Unity Catalog schema and there is
            # nothing to mount -- and `pipelines/gold/build.py` already owns it. A second
            # implementation here would be two definitions of where silver lives.
            register_silver(spark, root / "silver", schema=gold_session.SCHEMA)
            return list(from_silver(spark, gold_session.SCHEMA, window=window))


def _from_estate(schema: str, catalog: str | None, window: TradingWindow) -> list[ShelfDay]:
    """The silver the estate already holds, read through the session the runtime provided.

    **This branch is why the file changed.** The job in `infra/ml/training.tf` is described as
    *trains on the estate*, and what it ran was `_from_corpus`: eight months of history loaded by
    `backfill` were never opened, a fresh rehearsal world was generated inside the task, and the
    model that `serving` would answer from had been fitted on data that had nothing to do with
    the estate. It was green. `CLAUDE.md`'s whole thesis is that a number produced without a
    valid holdout is a build failure, and this was that failure one layer below the number.
    """
    from pipelines.gold import session as gold_session
    from pipelines.ml.build import from_silver

    with gold_session.sessions() as spark:
        runtime.use_catalog(spark, catalog)
        return list(from_silver(spark, schema, window=window))


def main(argv: list[str] | None = None) -> int:
    from corpus.world.scale import CLOSE_HOUR, OPEN_HOUR

    from holdout.contracts.loader import load
    from holdout.core.demand.censoring import TradingWindow as Window
    from pipelines.ml.build import train

    parser = argparse.ArgumentParser(prog="pipelines.ml", description=__doc__)
    parser.add_argument(
        "--silver-schema",
        help="Train on this catalog schema's silver. Without it, a corpus is built here.",
    )
    parser.add_argument("--catalog")
    parser.add_argument(
        "--model",
        help="The registered model a passing run creates a version of. Without it, nothing is registered.",
    )
    parser.add_argument("--experiment", help="The MLflow experiment the run is logged under.")
    args = parser.parse_args(argv)

    settings = load().training
    # Read from the corpus that produced the rows rather than declared here, the same way
    # `evals/censoring/build.py` reads it. A trading window written down in two places is two
    # definitions of when a shop is open, and the one that is wrong is the one nobody re-reads.
    window = Window(open_hour=OPEN_HOUR, close_hour=CLOSE_HOUR)

    if args.silver_schema:
        days = _from_estate(args.silver_schema, args.catalog, window)
    else:
        days = _from_corpus(window)

    trained = train(days, settings, window=window)
    width = max(len(name) for name, _ in trained.summary)
    for name, value in trained.summary:
        print(f"{name:<{width}}  {value}")
    print()
    print(trained.assessment)

    if not args.model:
        return 0

    # **With `--model`, a refusal is a failed run.** Without one this is a demonstration and a
    # refused model is the demonstration working, which is why the exit code above is zero. With
    # one, the caller is `backfill`, the next step reads the registry for a version, and a run
    # that refused and exited zero would send it looking for something nobody made.
    from pipelines.ml import registry

    try:
        version = registry.register(trained, model_name=args.model, experiment=args.experiment)
    except registry.RefusedError as refusal:
        print()
        print(f"REFUSED  {refusal}")
        return 1
    print()
    print(f"registered  {args.model}  version {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
