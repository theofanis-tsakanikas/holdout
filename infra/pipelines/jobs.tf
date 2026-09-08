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
}

# ------------------------------------------------- landing, then bronze, from files on S3
#
# **The ERP path, and it is a bulk load rather than a connector.** `CLAUDE.md` records the ruling:
# the master data arrives as files dropped several times during a run, and what that demonstrates
# is *incremental load of successive drops, not change capture against a live source* — the
# smaller claim, taken deliberately, because the connector that would have made the larger one
# runs a continuous classic-compute gateway.
resource "databricks_job" "bulk_load" {
  name        = "holdout — history into landing, landing into bronze"
  description = "Eight months of history into landing, then into bronze once each. Nothing is transformed here."

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
    task_key        = "history"
    environment_key = local.environment_key

    # **The module this job is named after, which is not the one it was running.**
    #
    # It ran `pipelines/ingest/__main__.py` — which *generates a corpus and writes JSONL*. The
    # bulk load is `pipelines/ingest/bulk.py`, whose own docstring says so: *the S3 bulk load:
    # files that landed become bronze, once each.* It takes subcommands, and the two `backfill`
    # needs are `history` — eight months into landing — and `load` — landing into bronze.
    #
    # **Every argument is passed and none left to a default.** The package's defaults are `smoke`
    # and `W6`; a task given only some of them runs green over the wrong corpus, and a crash is a
    # red run where this is eight months of history that is not eight months of anything.
    spark_python_task {
      python_file = "pipelines/entrypoint.py"
      source      = "GIT"
      parameters = [
        "pipelines.ingest.bulk",
        "history",
        "--world", var.corpus_world,
        "--scale", var.corpus_scale,
        "--seed", var.corpus_seed,
        "--landing", local.zone_path["landing"],
      ]
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

  # **No schedule.** `backfill` dispatches this once over eight months of history, and `run`
  # drives the live day through Zerobus instead. A cron here would be a fourth thing that can
  # start an apply's worth of compute, and `CLAUDE.md` names exactly three.
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
    environment_key = local.environment_key

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
