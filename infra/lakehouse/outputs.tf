# What this layer publishes for `pipelines`, `ml` and `serving`, as one map — the shape
# `infra/foundation/outputs.tf` argues for: two lists would be two enumerations of one population.
locals {
  published = merge(
    {
      "catalog"       = databricks_catalog.holdout.name
      "warehouse_id"  = databricks_sql_endpoint.estate.id
      "lakebase_name" = databricks_database_instance.lakebase.name
    },
    { for z in local.zones : "location_${z}" => databricks_external_location.zone[z].name },
    # **The POSIX path each pipeline is given.** `volumes.tf` explains why a path rather than a
    # URI: every entry point declares `pathlib.Path`, and an `s3://` string becomes a local
    # directory named `s3:` rather than an error.
    { for z in local.zones : "volume_${z}" => "/Volumes/${databricks_catalog.holdout.name}/${z}/files" },
  )
}

resource "aws_ssm_parameter" "published" {
  for_each = local.published

  name  = "/holdout/lakehouse/${each.key}"
  type  = "String"
  value = each.value
}

output "catalog" {
  value       = databricks_catalog.holdout.name
  description = "The Unity Catalog catalog. Also published to /holdout/lakehouse/catalog."
}

output "warehouse_id" {
  value       = databricks_sql_endpoint.estate.id
  description = "The serverless SQL warehouse the dashboards run on."
}

output "dashboards" {
  value = {
    experiment_readout = databricks_dashboard.experiment_readout.id
    decision_monitor   = databricks_dashboard.decision_monitor.id
  }
  description = "The two AI/BI dashboards. T020's stop_at is that these render."
}
