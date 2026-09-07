# **The warehouse the dashboards run on, created here rather than supplied.**
#
# `infra/lakehouse/dashboards.tf` declares `warehouse_id` with no default, and the block above it
# says why: *a layer applying these resources has to say which warehouse rather than inheriting
# one somebody typed here.* That was right when nothing in this layer created one. **It does
# now** — so the variable is answered by the layer instead of by whoever runs the apply, which is
# the same sentence with the ambiguity removed.
#
# `docs/FINDINGS.md` carries the entry: the default was `""`, the description asserted its
# absence, and an apply that forgot the input would have bound two dashboards to the warehouse
# named by the empty string. `tests/infra/test_variable_declarations.py` is what refuses that
# shape now.
resource "databricks_sql_endpoint" "estate" {
  provider = databricks.workspace

  name         = "holdout"
  cluster_size = var.warehouse_size

  # **Serverless, which is not a preference — it is `CLAUDE.md`'s cost posture.** *Serverless
  # only. No always-on cluster anywhere in the design.* A classic warehouse holds EC2 while it
  # runs and takes minutes to start; a serverless one bills per second of query and nothing at
  # rest.
  enable_serverless_compute = true

  # One cluster, no scaling. This estate has two dashboards and a person looking at them; a
  # minimum of two clusters would double the idle bill to serve a queue that never forms.
  max_num_clusters = 1

  auto_stop_mins = var.warehouse_auto_stop_minutes

  tags {
    custom_tags {
      key   = "holdout:project"
      value = "holdout"
    }
  }
}
