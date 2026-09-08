# **State moves, kept in their own file so that a rename is legible as a rename.**
#
# A `moved` block is a statement about history rather than about the estate: it says that the
# object Terraform is holding under a new address is the same object it created under an old one.
# Deleting one is not a tidy-up — it is an instruction to destroy and recreate whatever it names,
# and for a Databricks job that is a new id, a stale SSM parameter and a workflow pointing at
# nothing. They stay until the estate they describe has been destroyed and rebuilt.

# **One job became two slices, and the baseline is the one that kept its work.**
#
# `bulk_load` generated the whole history in one pass, under the arms `prepare` applies by
# default — which `corpus/world/__init__.py` calls *a convenience and not a lottery*. The
# baseline instance runs the same two tasks over the days before the comparison window opens,
# so it is the same job doing less rather than a different job; the window instance is new.
moved {
  from = databricks_job.bulk_load
  to   = databricks_job.history["baseline"]
}
