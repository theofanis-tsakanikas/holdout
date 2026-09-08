locals {
  published = {
    "registered_model" = databricks_registered_model.demand.id
    "experiment"       = databricks_mlflow_experiment.training.id
    "job_train"        = tostring(databricks_job.train.id)
  }
}

resource "aws_ssm_parameter" "published" {
  for_each = local.published

  name  = "/holdout/ml/${each.key}"
  type  = "String"
  value = each.value
}

output "registered_model" {
  value       = databricks_registered_model.demand.id
  description = "The UC registered model. serving points at a version of this, once one exists."
}

output "job_train" {
  value       = databricks_job.train.id
  description = "The training job. backfill starts it and waits."
}
