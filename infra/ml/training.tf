# **The training job, the registered model it writes into, and no endpoint.**
#
# `T022`'s `closes` says it in one line and the line is the whole design: *no serving endpoint —
# an endpoint cannot point at a model version that does not exist yet, and a version exists only
# after `backfill` has trained one.* `CLAUDE.md` splits `serving` from `ml` for the same reason,
# and calls it a difference of *moment* rather than of kind.

# ---------------------------------------------------------------- where the model is registered
#
# **Unity Catalog rather than the workspace registry.** A registered model in UC is a governed
# object like a table: it lives in the catalog, it carries grants, and its lineage joins the
# lineage of the data that trained it. The workspace registry is the older shape and keeps models
# in a namespace nothing else in this estate uses.
resource "databricks_registered_model" "demand" {
  name         = "demand"
  catalog_name = data.aws_ssm_parameter.catalog.value
  schema_name  = "gold"
  comment      = "The demand model. Versions are created by the training job, never by hand."
}

# **An experiment, declared rather than created by the first run that needs one.**
#
# MLflow creates an experiment implicitly when a run logs to a path that has none, and an
# implicitly created object belongs to no layer: `destroy` would leave it, and the next `deploy`
# would adopt it silently. That is the same argument `infra/foundation/reaper.tf` makes about its
# log group, and it was learned there.
#
# **No `description`: the provider deprecates it.** `terraform validate` says so — *remove the
# description attribute as it no longer is used and will be removed in a future version* — and a
# field the provider has stopped reading is a comment that costs a warning on every plan. What it
# would have said is the paragraph above.
resource "databricks_mlflow_experiment" "training" {
  name = "/Shared/holdout/training"
}

# ---------------------------------------------------------------- the job
#
# **One task, and the gates are inside it rather than beside it.**
#
# `pipelines/ml/` is the time split, claim 4's censoring correction, the calibration gate and the
# five promotion gates — and `promotion.py` is what decides whether a version may be registered.
# Splitting the gates into a second task would put a job's control flow between a model and the
# decision about it, and `CLAUDE.md`'s doctrine 5 is that **nothing approves itself**: the gate
# has to be code the training run cannot skip, not a step somebody can re-run green.
resource "databricks_job" "train" {
  name        = "holdout — train, gate, register"
  description = "Trains on the estate, runs the five promotion gates, registers a version only if they pass."

  environment {
    environment_key = "holdout"
    spec {
      client = "2"
    }
  }

  git_source {
    url      = var.repository_url
    provider = "gitHub"
    # Exactly one of the two, never both: `variables.tf` explains which and why.
    branch = var.git_commit == "" ? var.git_ref : null
    commit = var.git_commit == "" ? null : var.git_commit
  }

  task {
    task_key        = "train"
    environment_key = "holdout"

    spark_python_task {
      python_file = "pipelines/entrypoint.py"
      source      = "GIT"
      parameters  = ["pipelines.ml"]
    }
  }

  # **No schedule, and here the absence carries more than convenience.** `CLAUDE.md`: *the run
  # that produces the model actually used is executed on the estate, during `backfill`, on eight
  # months of loaded history.* A cron would produce versions nobody asked for, against data whose
  # end date nobody declared — and the time split that makes the driven day held-out by
  # construction depends on exactly when this runs.
}
