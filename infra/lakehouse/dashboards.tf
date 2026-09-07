# The two AI/BI dashboards, as `databricks_dashboard` resources.
#
# `CLAUDE.md`: *"No dashboard is built from a console. They are `databricks_dashboard` resources
# in the `lakehouse` layer. The IaC rule applies to everything that will be photographed."*
#
# **Neither resource contains a query.** Both read a generated artefact, compiled from
# `contracts/` by `holdout.contracts.compilers.dashboard` and byte-compared by `make contracts`.
# A query written here would be a second definition of the metric, in the one artefact nobody
# re-derives: a screenshot.

# **`warehouse_id` was a variable here and is now a reference.**
#
# It read: *supplied by `T020`, which creates it; declared with no default so that a layer
# applying these resources has to say which warehouse rather than inheriting one somebody typed
# here.* That was right while nothing in this layer created a warehouse. `T020` is this branch,
# `warehouse.tf` creates one, and the sentence's requirement — that the layer say which warehouse
# — is now met by the layer rather than by whoever runs the apply. **A variable with no default
# was the strongest available statement then; a reference is a stronger one now**, because it
# cannot be answered wrongly at all.
#
# The variable's own history is in `docs/FINDINGS.md`: it once carried `default = ""` two lines
# under a description asserting it had none, and an apply that forgot the input would have bound
# both dashboards to the warehouse named by the empty string.

variable "parent_path" {
  description = "The workspace folder the dashboards live in."
  type        = string
  default     = "/Shared/holdout"
}

# The project's central image. Four check tiles, then either the uplift with its interval or the
# refusal and its reason code **at the same size** — `CLAUDE.md` calls the refused version the
# single most important screenshot in the project.
resource "databricks_dashboard" "experiment_readout" {
  provider             = databricks.workspace
  display_name         = "Holdout — experiment readout"
  warehouse_id         = databricks_sql_endpoint.estate.id
  parent_path          = var.parent_path
  serialized_dashboard = file("${path.module}/../../generated/dashboards/experiment_readout.lvdash.json")
}

# Required by doctrine rule 2 rather than optional: *a fallback is visible to the actuator, the
# record and the dashboard. Without this screen, rule 2 is proved nowhere.*
resource "databricks_dashboard" "decision_monitor" {
  provider             = databricks.workspace
  display_name         = "Holdout — decision monitor"
  warehouse_id         = databricks_sql_endpoint.estate.id
  parent_path          = var.parent_path
  serialized_dashboard = file("${path.module}/../../generated/dashboards/decision_monitor.lvdash.json")
}
