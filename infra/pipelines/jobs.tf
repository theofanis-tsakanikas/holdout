# **Three jobs, one per hop of the data flow, and each runs this repository's own entry point.**
#
# `CLAUDE.md`'s flow is `sources → bronze (10) → silver (5) → gold (4 families)`, and
# `pipelines/ingest`, `pipelines/silver` and `pipelines/gold` are the three packages that make it.
# Each already has a `__main__.py` with the arguments it needs — proved local against the corpus,
# on every push, by `make test`. **This layer does not re-implement any of it**; it schedules it.
#
# **`git_source` rather than a wheel.** The alternative is building an artefact, uploading it, and
# pinning a version — three steps between the code and the run, each of which can drift from the
# tree. `CLAUDE.md`'s rule is *nothing is invented*, and a job whose code arrives by a route
# nobody can retrace is that defect one layer over. The repository is public, so this needs no git
# credential; a private one would need `databricks_git_credential`, and that is a decision this
# repository does not have to make.
#
# **Serverless, with no cluster block anywhere.** *Serverless only. No always-on cluster anywhere
# in the design.* A job with a `new_cluster` would hold EC2 for its whole run and take minutes to
# start; a serverless task bills per second of execution.

locals {
  # The environment every task runs in. One spec, referenced by key, rather than repeated per
  # task — two copies of a runtime are two things to keep equal.
  environment_key = "holdout"

  # **A second environment, for the one task that needs a package.**
  #
  #     + dbt deps
  #     /bin/bash: line 4: dbt: command not found
  #
  # A serverless `dbt_task` runs dbt in the environment it names, and the base image has no dbt
  # in it. The dependency is declared here rather than added to `environment_key` above because
  # every other task would then pay the install — eight tasks resolving an adapter that only one
  # of them runs — and because a runtime is a claim about what a task needs, not a shared bag.
  #
  # **`dbt-databricks`, not the `dbt-spark[session]` the local extra installs.** They are two
  # adapters for two engines: locally dbt drives the SparkSession this repository started, and
  # on the estate it issues SQL to the warehouse `lakehouse` created. `pyproject.toml` carries
  # the local half and says why; this is the other half, and the lower bound is the same shape
  # the extra uses.
  dbt_environment_key = "holdout-dbt"

  # **The volume path, not the bucket URI.** A job takes paths rather than reading SSM itself:
  # the layer that knows the estate's shape is this one, and a pipeline that discovered its own
  # inputs would be a second place the estate is described.
  #
  # These were `s3://…`, and every entry point under `pipelines/` declares `pathlib.Path`. An
  # `s3://` string handed to one does not fail — it becomes a **local directory named `s3:`** on
  # the worker. The job exits zero, the bucket stays empty, and the failure surfaces three jobs
  # later as an empty readout. `infra/lakehouse/volumes.tf` is what makes a real path available.
  zone_path = { for z in local.zones : z => data.aws_ssm_parameter.volume[z].value }

  # **The catalog is named on every task that writes a table.** A two-part name resolves against
  # whatever catalog the workspace defaults to: the tables would be created, the run would report
  # success, and every grant, dashboard and readout would point at an empty schema.
  # `tests/infra/test_tasks_name_the_catalog.py` is what keeps a new task from omitting it.
  catalog = data.aws_ssm_parameter.catalog.value

  # Silver and gold as catalog schemas rather than paths. The zone names are the schema names:
  # `infra/lakehouse/catalog.tf` creates one schema per zone.
  silver_schema = "silver"
  gold_schema   = "gold"

  # The experiment whose committed arms the comparison window is generated under. One id, named
  # here because two layers use it: the window's ingest reads the assignment by it, and the
  # readout writes its row under it. `pipelines/gold/experiments.py` declares it.
  experiment_id = "fresh-ladder"
}

# ------------------------------------------------- landing, then bronze, from files on S3
#
# **The ERP path, and it is a bulk load rather than a connector.** `CLAUDE.md` records the ruling:
# the master data arrives as files dropped several times during a run, and what that demonstrates
# is *incremental load of successive drops, not change capture against a live source* — the
# smaller claim, taken deliberately, because the connector that would have made the larger one
# runs a continuous classic-compute gateway.
# **Two slices of history, and the split is what makes an experiment possible.**
#
# `corpus/world/__init__.py` says of the default assignment that it is *a convenience and not a
# lottery*. A history generated in one pass therefore carries arms nobody drew, and an uplift
# read out over those is exactly the failure this repository exists to make impossible. So the
# estate loads the baseline first, under `all_control`; `experiment_design` draws the lottery
# against the baseline's covariates and seals it; and only then is the comparison window
# generated, under the arms that were committed.
#
# One resource with two instances rather than two resources: the runtime, the git source and the
# load step are identical, and two copies of them are two things to keep equal.
locals {
  slices = {
    baseline = {
      arms  = "all-control"
      after = null
    }
    window = {
      arms  = "table"
      after = local.experiment_id
    }
  }
}

resource "databricks_job" "history" {
  for_each = local.slices

  name        = "holdout — ${each.key} history into landing, landing into bronze"
  description = "The ${each.key} slice, generated under ${each.value.arms} arms, then loaded once each."

  environment {
    environment_key = local.environment_key
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

  # **The ERP's own drop, and without it silver refuses.**
  #
  # A history slice's Parquet carries the three reference tables beside the four event streams —
  # and `bulk.load` deliberately does not read them: `corpus/world/`'s `store_master` carries the
  # `arm` column, which is the experiment's answer, and the loader reads each `run.json`'s stream
  # counts rather than globbing so that it cannot enter bronze by that route.
  #
  # So the master data has to arrive the way `CLAUDE.md` says it does — *ERP master data → files
  # on S3, dropped again during a run* — and nothing dispatched it. Measured: `silver` refused
  # with *`/Volumes/holdout/bronze/files/cost_ledger` holds no Parquet, so silver would build an
  # empty cost_ledger and report a clean run*, which is that guard doing exactly its job.
  #
  # One export per slice, into its own directory, on the last day **inside** it: a drop publishes
  # every reference row effective at or before the day it names, so the baseline's drop carries
  # the ledger as the ERP knew it when the window opened and the window's carries what became
  # effective during it.
  task {
    task_key        = "export"
    environment_key = local.environment_key

    spark_python_task {
      python_file = "pipelines/entrypoint.py"
      source      = "GIT"
      parameters = [
        "pipelines.ingest.bulk",
        "export",
        "--world", var.corpus_world,
        "--scale", var.corpus_scale,
        "--seed", var.corpus_seed,
        "--landing", local.zone_path["landing"],
        "--slice", each.key,
        "--into", "${each.key}-drops",
      ]
    }
  }

  task {
    task_key        = "history"
    environment_key = local.environment_key

    depends_on {
      task_key = "export"
    }

    # **The module this job is named after, which is not the one it was running.**
    #
    # It ran `pipelines/ingest/__main__.py` — which *generates a corpus and writes JSONL*. The
    # bulk load is `pipelines/ingest/bulk.py`, whose own docstring says so: *the S3 bulk load:
    # files that landed become bronze, once each.* It takes subcommands, and the two `backfill`
    # needs are `history` — the slice into landing — and `load` — landing into bronze.
    #
    # **Every argument is passed and none left to a default.** The package's defaults are `smoke`
    # and `W6`; a task given only some of them runs green over the wrong corpus, and a crash is a
    # red run where this is months of history that is not months of anything.
    spark_python_task {
      python_file = "pipelines/entrypoint.py"
      source      = "GIT"
      parameters = concat(
        [
          "pipelines.ingest.bulk",
          "history",
          "--world", var.corpus_world,
          "--scale", var.corpus_scale,
          "--seed", var.corpus_seed,
          "--landing", local.zone_path["landing"],
          # The days this slice writes, named rather than dated: `pipelines/window.py` owns
          # where one ends and the other begins, because three steps have to agree about it.
          "--slice", each.key,
          "--into", each.key,
          "--arms", each.value.arms,
        ],
        each.value.after == null ? [] : [
          "--assignment-schema", local.gold_schema,
          "--experiment-id", each.value.after,
          "--catalog", local.catalog,
        ],
      )
    }
  }

  # **Landing into bronze, once each.** The checkpoint that makes *once each* true lives in
  # `bulk.py`; this task's job is only to run it after the files exist.
  task {
    task_key        = "load"
    environment_key = local.environment_key

    depends_on {
      task_key = "history"
    }

    spark_python_task {
      python_file = "pipelines/entrypoint.py"
      source      = "GIT"
      parameters = [
        "pipelines.ingest.bulk",
        "load",
        "--landing", local.zone_path["landing"],
        "--bronze", local.zone_path["bronze"],
      ]
    }
  }

  # **No schedule.** `backfill` dispatches these once, and `run` drives the live day through
  # Zerobus instead. A cron here would be a fourth thing that can start an apply's worth of
  # compute, and `CLAUDE.md` names exactly three.
}

# ---------------------------------------------------------------- silver, one table per question
resource "databricks_job" "silver" {
  name        = "holdout — bronze into silver"
  description = "As-of joins, the derived stock-out, and the quarantine the OSS framework does not provide."

  environment {
    environment_key = local.environment_key
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
    task_key        = "silver"
    environment_key = local.environment_key

    spark_python_task {
      python_file = "pipelines/entrypoint.py"
      source      = "GIT"
      parameters = [
        "pipelines.silver",
        "--bronze", local.zone_path["bronze"],
        # **A schema, not the volume path.** `pipelines/silver/build.py` carries the argument:
        # gold's dbt models and the training job both read silver through the catalog, and Unity
        # Catalog refuses a table created inside a volume — so silver as five directories under
        # `/Volumes/.../silver/files` is a place nothing downstream can name.
        "--silver-schema", local.silver_schema,
        "--catalog", local.catalog,
      ]
    }
  }
}

# ---------------------------------------------------------------- gold, four families
#
# **Two tasks in one job, and the dependency runs the other way from the first version.** The
# Python step writes `gold.priced_sales` and `gold.priced_waste`; `pipelines/gold/dbt/models/
# sources.yml` declares exactly those two as dbt's sources. So dbt cannot go first, and it did:
# `depends_on` named `dbt` from the Python task, which would have started dbt against sources
# nothing had written. `tests/infra/test_dbt_sources_are_written_first.py` reads the two files
# against each other, which is the only way to see it — each is correct alone.
resource "databricks_job" "gold" {
  name        = "holdout — silver into gold"
  description = "The priced tables, then dbt over them for the analytical models."

  environment {
    environment_key = local.environment_key
    spec {
      client = "2"
    }
  }

  environment {
    environment_key = local.dbt_environment_key
    spec {
      client       = "2"
      dependencies = ["dbt-databricks>=1.11.0"]
    }
  }

  git_source {
    url      = var.repository_url
    provider = "gitHub"
    # Exactly one of the two, never both: `variables.tf` explains which and why.
    branch = var.git_commit == "" ? var.git_ref : null
    commit = var.git_commit == "" ? null : var.git_commit
  }

  # **The sources, before the thing that reads them.**
  task {
    task_key        = "priced"
    environment_key = local.environment_key

    spark_python_task {
      python_file = "pipelines/entrypoint.py"
      source      = "GIT"
      parameters = [
        "pipelines.gold",
        # `priced` rather than the whole build: the analytical models are the `dbt` task's work,
        # and running them here as well would build the same four families twice — in a process
        # that on serverless cannot start a session of its own to do it in.
        "--only", "priced",
        "--silver-schema", local.silver_schema,
        "--catalog", local.catalog,
      ]
    }
  }

  task {
    task_key = "dbt"

    depends_on {
      task_key = "priced"
    }

    # **A serverless `dbt_task` needs an environment as well as a warehouse, and the first apply
    # said so:** *an environment is required for serverless task dbt.*
    #
    # The two are not alternatives, which is what the omission assumed. The **warehouse** is where
    # dbt's SQL runs — the object `lakehouse` created for exactly this. The **environment** is
    # where dbt itself runs: the Python process that resolves `dbt deps` and issues the
    # statements. Giving one and not the other reads as complete, because each is sufficient for
    # the half a reader happens to be thinking about.
    #
    # **And the environment has to contain dbt**, which the first two applies took for granted:
    # `dbt deps` came back `command not found`. See `local.dbt_environment_key`.
    environment_key = local.dbt_environment_key

    dbt_task {
      project_directory = "pipelines/gold/dbt"
      commands          = ["dbt deps", "dbt build"]
      catalog           = data.aws_ssm_parameter.catalog.value
      schema            = "gold"
      # **A warehouse rather than a cluster**, because dbt issues SQL and the warehouse is what
      # `lakehouse` created for exactly this. It stops after ten idle minutes on its own.
      warehouse_id = data.aws_ssm_parameter.warehouse_id.value
    }
  }

}

# ---------------------------------------------------------------- the experiment, in two moments
#
# **Two jobs because they run at two different times and one of them must run before data
# exists.** `design` assesses both declared experiments against the baseline's covariates and
# writes the lottery for every one that may exist; the comparison window is then generated under
# those arms. `readout` runs after the window has been loaded and built, verifies the table
# against the seal it re-derives, and writes `gold.readout` — the table `ops/run_assertions.py`
# accepts phase 3 on, and which until this branch was written by nothing at all.
#
# A single job with two tasks would put the window's generation in the middle of it, which is
# not something a job can wait for.
resource "databricks_job" "experiment" {
  for_each = toset(["design", "readout"])

  name        = "holdout — experiment ${each.key}"
  description = each.key == "design" ? "Moment 1: assess both designs and seal the lottery, before the window exists." : "Moment 3: verify the seal, close, and write one row per experiment into gold.readout."

  environment {
    environment_key = local.environment_key
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
    task_key        = each.key
    environment_key = local.environment_key

    spark_python_task {
      python_file = "pipelines/entrypoint.py"
      source      = "GIT"
      parameters = [
        "pipelines.gold.experiments",
        each.key,
        # The scale, because `pipelines/window.py` derives the window from it rather than from
        # three dates threaded through a workflow.
        "--scale", var.corpus_scale,
        "--catalog", local.catalog,
        "--gold-schema", local.gold_schema,
        "--silver-schema", local.silver_schema,
      ]
    }
  }
}

# ---------------------------------------------------------------- the live day
#
# **A job rather than a step on the runner, and the reason is where the files have to land.**
#
# `run.yml` drove this from the workflow with `--out s3://<bucket>`. `--out` is a `pathlib.Path`:
# the driver wrote its stream into a local directory literally named `s3:` on the runner, printed
# its line counts, exited zero, and the runner went away. It is the same trap `local.zone_path`
# above was written to close, one layer up — and the format could not have been loaded anyway,
# since `bulk.load` reads `.csv.gz` and `.parquet` and the driver wrote JSONL.
#
# Here it writes Parquet into the landing volume, under its own subdirectory, and the load task
# after it takes the rows once each — duplicates included, because a receipt line delivered twice
# is one event and proving that is what a live day is for.
resource "databricks_job" "live_day" {
  name        = "holdout — one live day, arriving wrong"
  description = "The day after the comparison window closes, with lateness and duplicates, into bronze."

  environment {
    environment_key = local.environment_key
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
    task_key        = "drive"
    environment_key = local.environment_key

    spark_python_task {
      python_file = "pipelines/entrypoint.py"
      source      = "GIT"
      parameters = [
        "pipelines.ingest",
        "--world", var.corpus_world,
        "--scale", var.corpus_scale,
        "--seed", var.corpus_seed,
        # **`after-window`, not a date.** `pipelines/window.py` owns where the window closes and
        # therefore which day is held out by construction; a date written here would be a second
        # definition of the split, and the one that is wrong is the one nobody re-reads.
        "--day", "after-window",
        "--landing", local.zone_path["landing"],
        "--into", "live",
        # The committed arms: the estate is still running the policy each store was assigned.
        "--arms", "table",
        "--assignment-schema", local.gold_schema,
        "--experiment-id", local.experiment_id,
        "--catalog", local.catalog,
      ]
    }
  }

  task {
    task_key        = "load"
    environment_key = local.environment_key

    depends_on {
      task_key = "drive"
    }

    spark_python_task {
      python_file = "pipelines/entrypoint.py"
      source      = "GIT"
      parameters = [
        "pipelines.ingest.bulk",
        "load",
        "--landing", local.zone_path["landing"],
        "--bronze", local.zone_path["bronze"],
      ]
    }
  }
}
