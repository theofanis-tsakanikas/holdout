"""Which arms a slice of the world is generated under, and where they come from.

**Read by two callers and therefore not owned by either.** `pipelines/ingest/bulk.py` generates
the baseline and the comparison window; `pipelines/ingest/__main__.py` drives the live day after
the window has closed. All three have to be generated under the arms that were **committed**, or
they are three different experiments wearing one estate's name — so the resolution lives here and
each caller passes its own parsed arguments to it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

    from corpus.world import Run
    from corpus.world.assignment import Arm


def arms_for(args: Any, run: Run) -> Mapping[str, Arm] | None:
    """The assignment the history is generated under, or `None` for the package's default.

    Three answers and they are three different claims:

    * **`alternating`** — `None` here, so `prepare` applies its own convenience. It is not a
      lottery and the package says so; it is the right answer for a demonstration that is not
      going to be read out.
    * **`all-control`** — the baseline. Nothing is applied to anybody, which is what makes the
      pre-period covariates a measurement of the estate rather than of the treatment.
    * **`table`** — the arms `gold.experiment_assignment` holds, written by
      `pipelines/gold/experiments.py` from a lottery drawn against the baseline's covariates and
      sealed before this window opens. Read back through the table rather than passed along, so
      the window is generated under the arms that were **committed**, not under a mapping that
      travelled beside them.
    """
    from corpus.world.assignment import Arm, all_control

    choice = getattr(args, "arms", "alternating")
    if choice == "alternating":
        return None

    built = run.chain
    if choice == "all-control":
        return all_control(built)

    if not args.assignment_schema or not args.experiment_id:
        raise SystemExit(
            "--arms table needs --assignment-schema and --experiment-id: the window is "
            "generated under the arms that were committed, and this is how it finds them."
        )
    from pipelines import session as runtime_module
    from pipelines.gold import assignment as assignment_table
    from pipelines.gold import session as gold_session

    with gold_session.sessions() as spark:
        runtime_module.use_catalog(spark, getattr(args, "catalog", None))
        rows = assignment_table.read_rows(
            spark, schema=args.assignment_schema, experiment_id=args.experiment_id
        )
    if not rows:
        # **No rows is a refused design, and it is a state with an answer.**
        #
        # `pipelines/gold/experiments.py::design` creates this table whether or not it writes
        # into it, so an empty one means the designs were assessed and none may exist — not that
        # the design step was skipped. The window is then generated with nothing applied to
        # anybody, which is what an estate running no experiment looks like, and `gold.readout`
        # carries the reasons with their figures.
        #
        # **Printed rather than silent**, because a fallback nobody sees is the shape this
        # repository files findings about: the run says so here, and the readout says so in a
        # table.
        print(
            f"arms     {args.assignment_schema}.experiment_assignment holds no rows for "
            f"{args.experiment_id}: no design may exist, so this window runs all-control."
        )
        return all_control(built)
    committed = {store: Arm(arm) for store, arm in rows}
    # **A store outside the roster is simulated under control, and that is a decision.**
    # `assess` excludes stores automatically where a neighbour is treated — 80 of 320 on the
    # harness world — and those stores are not in the experiment. The world still has to
    # simulate them, and the only honest arm for a shop nobody randomised is the one where
    # nothing was applied. Treating them would put the intervention on shelves the readout does
    # not look at, and the estate would be running a bigger experiment than it declared.
    outside = [s.store_id for s in built.stores if s.store_id not in committed]
    print(f"arms     {len(committed)} committed, {len(outside)} outside the roster -> control")
    return {**dict.fromkeys(outside, Arm.CONTROL), **committed}
