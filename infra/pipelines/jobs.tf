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

  # The zone buckets, as arguments. A job takes paths rather than reading SSM itself: the layer
  # that knows the estate's shape is this one, and a pipeline that discovered its own inputs
  # would be a second place the estate is described.
  zone_url = { for z in local.zones : z => "s3://${data.aws_ssm_parameter.zone[z].value}" }
}

# ---------------------------------------------------------------- bronze, from files on S3
#
# **The ERP path, and it is a bulk load rather than a connector.** `CLAUDE.md` records the ruling:
# the master data arrives as files dropped several times during a run, and what that demonstrates
# is *incremental load of successive drops, not change capture against a live source* — the
# smaller claim, taken deliberately, because the connector that would have made the larger one
# runs a continuous classic-compute gateway.
resource "databricks_job" "bulk_load" {
  name        = "holdout — bulk load into bronze"
  description = "Files on S3 into bronze, in the source's shape. Nothing is transformed here."

  environment {
    environment_key = local.environment_key
    spec {
      client = "2"
    }
  }

  git_source {
    url      = var.repository_url
    provider = "gitHub"
    branch   = var.git_ref
  }

  task {
    task_key        = "bulk_load"
    environment_key = local.environment_key

    spark_python_task {
      python_file = "pipelines/ingest/__main__.py"
      source      = "GIT"
      parameters = [
        "--out", local.zone_url["bronze"],
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
    branch   = var.git_ref
  }

  task {
    task_key        = "silver"
    environment_key = local.environment_key

    spark_python_task {
      python_file = "pipelines/silver/__main__.py"
      source      = "GIT"
      parameters = [
        "--bronze", local.zone_url["bronze"],
        "--silver", local.zone_url["silver"],
      ]
    }
  }
}

# ---------------------------------------------------------------- gold, four families
#
# **Two tasks in one job, and the dependency is the point.** `dbt` builds the analytical models
# and the Python step builds what dbt does not — the assignment table written before the period
# opens, and the readout that pins a Delta version. Splitting them into two jobs would let the
# second run against a silver the first had not finished with.
resource "databricks_job" "gold" {
  name        = "holdout — silver into gold"
  description = "dbt for the analytical models, then the experiment tables dbt does not build."

  environment {
    environment_key = local.environment_key
    spec {
      client = "2"
    }
  }

  git_source {
    url      = var.repository_url
    provider = "gitHub"
    branch   = var.git_ref
  }

  task {
    task_key = "dbt"

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

  task {
    task_key        = "experiment_tables"
    environment_key = local.environment_key

    depends_on {
      task_key = "dbt"
    }

    spark_python_task {
      python_file = "pipelines/gold/__main__.py"
      source      = "GIT"
      parameters = [
        "--silver", local.zone_url["silver"],
        "--root", local.zone_url["gold"],
      ]
    }
  }
}
