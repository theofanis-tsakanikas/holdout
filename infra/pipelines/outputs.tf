# What `backfill` and `run` need in order to start these jobs, published as one map — the shape
# `infra/foundation/outputs.tf` argues for.
locals {
  published = {
    "job_history_baseline"   = tostring(databricks_job.history["baseline"].id)
    "job_history_window"     = tostring(databricks_job.history["window"].id)
    "job_experiment_design"  = tostring(databricks_job.experiment["design"].id)
    "job_experiment_readout" = tostring(databricks_job.experiment["readout"].id)
    "job_silver"             = tostring(databricks_job.silver.id)
    "job_gold"               = tostring(databricks_job.gold.id)

    # **The corpus arguments, published so `run` drives the same world it was built from.**
    # A day driven under a different world from the history that trained the model is not a held
    # out day; it is a different experiment. `run.yml` carried these as literals and one of them
    # differed in case from the value here.
    "corpus_world" = var.corpus_world
    "corpus_scale" = var.corpus_scale
    "corpus_seed"  = var.corpus_seed
  }
}

resource "aws_ssm_parameter" "published" {
  for_each = local.published

  name  = "/holdout/pipelines/${each.key}"
  type  = "String"
  value = each.value
}

output "jobs" {
  value       = local.published
  description = "The three job ids. backfill and run start them by id rather than by name."
}
