# **Grants, and the smallest set that lets the estate work.**
#
# There is one human and one service principal on this estate, so a role hierarchy would be
# ceremony. What is not ceremony is that the grants are **declared here rather than inherited from
# ownership** — an object's creator owns it, and ownership is not a grant anybody can read back
# from a repository. `CLAUDE.md`'s governance story is Unity Catalog, and a governance story whose
# permissions exist only as a side effect of who ran `apply` is not one.
resource "databricks_grants" "catalog" {
  provider = databricks.workspace
  catalog  = databricks_catalog.holdout.name

  grant {
    principal = "account users"
    # **Read, and nothing that writes.** The pipelines write as the service principal that owns
    # the objects; a human browsing the lakehouse — which is what the dashboards and Genie do —
    # needs to select and to see the shape, and needs nothing else.
    privileges = ["USE_CATALOG", "USE_SCHEMA", "SELECT", "BROWSE"]
  }
}

# **The external locations are granted separately from the catalog, and that is the interesting
# half.** A grant on a catalog governs tables; a grant on an external location governs the
# *files*. `READ_FILES` without `WRITE_FILES` is what lets somebody inspect a drop that failed to
# parse without being able to change it — which is the difference between debugging an ingestion
# and altering the evidence.
resource "databricks_grants" "location" {
  for_each          = toset(local.zones)
  provider          = databricks.workspace
  external_location = databricks_external_location.zone[each.key].id

  grant {
    principal  = "account users"
    privileges = ["READ_FILES", "BROWSE"]
  }
}
