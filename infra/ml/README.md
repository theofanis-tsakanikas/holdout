# `infra/ml/` — trains, gates, registers. **No endpoint.**

**Applied by `deploy`, from `main`.** Three objects and one absence.

| | |
|---|---|
| `databricks_registered_model` | `<catalog>.gold.demand` — where versions land |
| `databricks_mlflow_experiment` | `/Shared/holdout/training` — where runs land |
| `databricks_job` | *train, gate, register* — one task, no schedule |
| **no** `databricks_model_serving` | see below |

## Why there is no endpoint here

`T022`'s `closes` says it: *an endpoint cannot point at a model version that does not exist yet,
and a version exists only after `backfill` has trained one.* `CLAUDE.md` splits `serving` from
`ml` for that reason and calls it **a difference of moment rather than of kind** — the two would
otherwise be one layer wearing two names, since they share a lifetime, a blast radius and a
billing shape.

**`serving` is applied by `backfill`, at the end**, and is `T023`'s.

## Why the gates are inside the task

`pipelines/ml/promotion.py` decides whether a version may be registered. Splitting the gates into
a second job task would put a workflow's control flow between a model and the decision about it —
and doctrine 5 is that **nothing approves itself**. A gate has to be code the training run cannot
skip, not a step somebody can re-run until it is green.

## Why the experiment is declared

MLflow creates one implicitly when a run logs to a path that has none, and **an implicitly created
object belongs to no layer**: `destroy` leaves it, and the next `deploy` adopts it silently. That
argument was learned at `infra/foundation/reaper.tf`'s log group and it is the same one.

## Why there is no schedule

`CLAUDE.md`: *the run that produces the model actually used is executed on the estate, during
`backfill`, on eight months of loaded history.* A cron would produce versions nobody asked for,
against data whose end date nobody declared — and **the time split that makes the driven day
held-out by construction depends on exactly when this runs.**
