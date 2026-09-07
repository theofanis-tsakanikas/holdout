# **One catalog, and the schemas are the medallion.**
#
# `CLAUDE.md`'s data flow is `sources → bronze (10) → silver (5) → gold (4 families)`, and the
# schemas below are that sentence in Unity Catalog. A catalog per layer was the alternative and it
# buys nothing here: a catalog is a governance boundary and the boundary this project needs is
# between *this estate* and the four other projects in the account, which one catalog already is.
resource "databricks_catalog" "holdout" {
  provider = databricks.workspace

  name          = "holdout"
  metastore_id  = data.aws_ssm_parameter.metastore_id.value
  comment       = "The holdout estate. Storage is per-schema, on the zone this schema belongs to."
  force_destroy = true

  # **No `storage_root` on the catalog.** A catalog-level root makes every schema inherit one
  # location, and this estate's whole shape is one bucket per zone with its own blast radius. The
  # storage decision belongs to the schema, where the zone is known.
}

resource "databricks_schema" "zone" {
  for_each = toset(["bronze", "silver", "gold"])
  provider = databricks.workspace

  catalog_name  = databricks_catalog.holdout.name
  name          = each.key
  storage_root  = databricks_external_location.zone[each.key].url
  comment       = "The ${each.key} layer, stored on its own zone."
  force_destroy = true
}

# **`landing` is a schema too, and it is the one worth explaining.**
#
# It holds no tables that anybody queries: it is where the ERP's file drops and the eight months
# of transaction history arrive, and `pipelines` reads them from there into bronze. Registering it
# in Unity Catalog rather than leaving it as a raw bucket is what puts the *arrival* of data under
# the same governance as everything downstream — lineage starts at the file, not at the first
# table somebody made.
resource "databricks_schema" "landing" {
  provider = databricks.workspace

  catalog_name  = databricks_catalog.holdout.name
  name          = "landing"
  storage_root  = databricks_external_location.zone["landing"].url
  comment       = "Where files arrive. Governed here so lineage starts at the file."
  force_destroy = true
}
