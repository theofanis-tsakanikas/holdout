# **A bucket for the catalog's own managed storage, and it belongs to this layer.**
#
# The first apply of `infra/lakehouse` failed with:
#
#     cannot create catalog: Metastore storage root URL does not exist. Default Storage is
#     enabled in your account… please provide a storage root
#
# **Unity Catalog requires a managed location at one of three levels** — metastore, catalog or
# schema — and `infra/foundation/metastore.tf` deliberately declares none, for a reason that
# still holds: *a metastore-level root makes every catalog inherit one location, which is the old
# shape*. What that argument missed is that a catalog needs a root **even when every schema
# overrides it**, because the root is what a `CREATE TABLE` falls back to before any schema is
# named.
#
# **It is created here rather than in `foundation`, and that is a decision.** The four zones are
# the medallion — `landing`, `bronze`, `silver`, `gold` — and each is a place data *arrives* or is
# *written to* by a pipeline. This bucket holds nothing anybody writes on purpose: it is Unity
# Catalog's fallback, and a fallback that is never used is exactly the kind of thing that should
# live next to the object requiring it rather than in the layer below. `foundation` would have to
# grow a fifth "zone" that is not a zone.
locals {
  # The suffix rule `infra/bootstrap/state.tf` and `infra/foundation/zones.tf` both use: a bucket
  # name is globally unique, so it needs something account-specific, and the account id may not
  # appear in a public repository.
  account_suffix = substr(sha256(data.aws_caller_identity.current.account_id), 0, 12)
}

resource "aws_s3_bucket" "catalog" {
  bucket = "holdout-catalog-${local.account_suffix}"

  # Same argument as the zones: not on `CLAUDE.md`'s survivor list, and a destroy that stops on a
  # non-empty bucket leaves the estate half-standing.
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "catalog" {
  bucket                  = aws_s3_bucket.catalog.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "catalog" {
  bucket = aws_s3_bucket.catalog.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "catalog" {
  bucket = aws_s3_bucket.catalog.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = data.aws_ssm_parameter.data_key_arn.value
    }
    bucket_key_enabled = true
  }
}

# Its own credential and location, for the reason every zone has its own: a credential is what
# Unity Catalog assumes in order to read a location, and one credential across five locations is
# one blast radius across five buckets.
data "databricks_aws_unity_catalog_policy" "catalog" {
  provider = databricks.workspace

  aws_account_id = data.aws_caller_identity.current.account_id
  bucket_name    = aws_s3_bucket.catalog.bucket
  role_name      = "holdout-uc-catalog"
  kms_name       = data.aws_ssm_parameter.data_key_arn.value
}

data "databricks_aws_unity_catalog_assume_role_policy" "catalog" {
  provider = databricks.workspace

  aws_account_id = data.aws_caller_identity.current.account_id
  role_name      = "holdout-uc-catalog"
  external_id    = var.databricks_account_id
}

resource "aws_iam_role" "uc_catalog" {
  name               = "holdout-uc-catalog"
  assume_role_policy = data.databricks_aws_unity_catalog_assume_role_policy.catalog.json
}

resource "aws_iam_role_policy" "uc_catalog" {
  name   = "holdout-uc-catalog"
  role   = aws_iam_role.uc_catalog.id
  policy = data.databricks_aws_unity_catalog_policy.catalog.json
}

resource "databricks_storage_credential" "catalog" {
  provider = databricks.workspace

  name    = "holdout-catalog"
  comment = "Unity Catalog's own managed storage. Holds what no schema claimed."

  aws_iam_role {
    role_arn = aws_iam_role.uc_catalog.arn
  }

  depends_on = [time_sleep.uc_iam_propagation]
}

resource "databricks_external_location" "catalog" {
  provider = databricks.workspace

  name            = "holdout-catalog"
  url             = "s3://${aws_s3_bucket.catalog.bucket}/"
  credential_name = databricks_storage_credential.catalog.name
  comment         = "The catalog's managed root. Every schema overrides it; it exists because a catalog cannot have none."
  force_destroy   = true
}
