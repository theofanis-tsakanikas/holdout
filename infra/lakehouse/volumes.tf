# **Four volumes, because the pipelines take filesystem paths and not URIs.**
#
# Every entry point under `pipelines/` declares its inputs as `pathlib.Path` — `--landing`,
# `--bronze`, `--silver`, `--root`. Handing one of them `s3://holdout-bronze-…` does not fail: it
# creates a **local directory named `s3:`** on the worker and writes into it. The job exits zero,
# the bucket stays empty, and the failure surfaces three jobs later as an empty readout.
#
# **A Unity Catalog volume is the POSIX path over that bucket.** `/Volumes/<catalog>/<schema>/
# <volume>/` is a real filesystem path on Databricks compute and is governed by the same grants as
# everything else here — which is why this is the answer rather than teaching four Python modules
# about S3. The modules stay pure and provable local, which is the property `CLAUDE.md` protects.
#
# **`files/` rather than the bucket root**, because the schema already claims the root as its
# managed storage and a volume may not overlap it. The split is also honest: managed tables at the
# root, the files those tables were built from under `files/`.
resource "databricks_volume" "zone" {
  for_each = toset(local.zones)
  provider = databricks.workspace

  name             = "files"
  catalog_name     = databricks_catalog.holdout.name
  schema_name      = each.key == "landing" ? databricks_schema.landing.name : databricks_schema.zone[each.key].name
  volume_type      = "EXTERNAL"
  storage_location = "${databricks_external_location.zone[each.key].url}files/"
  comment          = "The ${each.key} zone as a filesystem path. The pipelines take paths, not URIs."
}
