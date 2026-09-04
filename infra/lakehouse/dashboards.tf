# The two AI/BI dashboards, as `databricks_dashboard` resources.
#
# `CLAUDE.md`: *"No dashboard is built from a console. They are `databricks_dashboard` resources
# in the `lakehouse` layer. The IaC rule applies to everything that will be photographed."*
#
# **Neither resource contains a query.** Both read a generated artefact, compiled from
# `contracts/` by `holdout.contracts.compilers.dashboard` and byte-compared by `make contracts`.
# A query written here would be a second definition of the metric, in the one artefact nobody
# re-derives: a screenshot.

variable "warehouse_id" {
  description = <<-EOT
    The serverless SQL warehouse the dashboards query through. Supplied by `T020`, which creates
    it; declared with no default so that a layer applying these resources has to say which
    warehouse rather than inheriting one somebody typed here.
  EOT
  type        = string
  default     = "" # validate-only: T020 supplies the real one
}

variable "parent_path" {
  description = "The workspace folder the dashboards live in."
  type        = string
  default     = "/Shared/holdout"
}

# The project's central image. Four check tiles, then either the uplift with its interval or the
# refusal and its reason code **at the same size** — `CLAUDE.md` calls the refused version the
# single most important screenshot in the project.
resource "databricks_dashboard" "experiment_readout" {
  display_name         = "Holdout — experiment readout"
  warehouse_id         = var.warehouse_id
  parent_path          = var.parent_path
  serialized_dashboard = file("${path.module}/../../generated/dashboards/experiment_readout.lvdash.json")
}

# Required by doctrine rule 2 rather than optional: *a fallback is visible to the actuator, the
# record and the dashboard. Without this screen, rule 2 is proved nowhere.*
resource "databricks_dashboard" "decision_monitor" {
  display_name         = "Holdout — decision monitor"
  warehouse_id         = var.warehouse_id
  parent_path          = var.parent_path
  serialized_dashboard = file("${path.module}/../../generated/dashboards/decision_monitor.lvdash.json")
}
