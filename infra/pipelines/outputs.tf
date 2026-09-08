# What `backfill` and `run` need in order to start these jobs, published as one map — the shape
# `infra/foundation/outputs.tf` argues for.
locals {
  published = {
    "job_bulk_load" = tostring(databricks_job.bulk_load.id)
    "job_silver"    = tostring(databricks_job.silver.id)
    "job_gold"      = tostring(databricks_job.gold.id)
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
