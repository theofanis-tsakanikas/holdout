# **One storage credential and one IAM role per zone, rather than one credential over all four.**
#
# The zones are separate buckets for a reason `infra/foundation/zones.tf` states — *a prefix
# shares a bucket policy, a lifecycle configuration and a blast radius with its neighbours; a
# bucket does not* — and a single credential spanning all four would put the blast radius back.
# **A credential is the thing Unity Catalog assumes in order to read a location**, so one per zone
# is the same isolation argument one layer up.
#
# It also removes a merge this repository has been bitten by: `databricks_aws_unity_catalog_policy`
# generates a document for **one** bucket, and combining four of them means
# `source_policy_documents`, which merges by `sid` and silently drops what collides. That is the
# mechanism that nearly made `oidc.tf`'s id conditions a disjunction. **Four documents, four
# roles, nothing merged.**

# The permission half: what Unity Catalog may do inside one zone.
data "databricks_aws_unity_catalog_policy" "zone" {
  for_each = toset(local.zones)
  provider = databricks.workspace

  aws_account_id = data.aws_caller_identity.current.account_id
  bucket_name    = data.aws_ssm_parameter.zone[each.key].value
  role_name      = "holdout-uc-${each.key}"
  kms_name       = data.aws_ssm_parameter.data_key_arn.value
}

# The trust half: who may assume it.
#
# **The external id is the Databricks account id**, which is what removes the chicken-and-egg this
# resource is famous for. The older pattern created the role with a placeholder, created the
# credential, read the credential's generated external id and went back to update the trust — two
# applies, with a window in between where the role trusts something that does not exist.
data "databricks_aws_unity_catalog_assume_role_policy" "zone" {
  for_each = toset(local.zones)
  provider = databricks.workspace

  aws_account_id = data.aws_caller_identity.current.account_id
  role_name      = "holdout-uc-${each.key}"
  external_id    = var.databricks_account_id
}

resource "aws_iam_role" "uc" {
  for_each = toset(local.zones)

  name               = "holdout-uc-${each.key}"
  assume_role_policy = data.databricks_aws_unity_catalog_assume_role_policy.zone[each.key].json
}

resource "aws_iam_role_policy" "uc" {
  for_each = toset(local.zones)

  name   = "holdout-uc-${each.key}"
  role   = aws_iam_role.uc[each.key].id
  policy = data.databricks_aws_unity_catalog_policy.zone[each.key].json
}

# **The same wait `infra/foundation/workspace.tf` needed, for the same reason — and it was one
# dependency short.**
#
# Unity Catalog validates a storage credential by assuming its role, and a role created
# milliseconds earlier is frequently not yet assumable. `depends_on` orders the calls; it does not
# make IAM's replicas agree. That failure reads as *"please use a valid cross account IAM role"*
# and is neither.
#
# **What the first version missed is that Unity Catalog validates the *location* too, by reading
# the bucket.** The second apply of this layer failed on exactly that, and on exactly one
# location:
#
#     cannot create external location: AWS IAM role does not have READ permissions on
#     url s3://holdout-catalog-…/  …  403 Forbidden
#
# **The four zones succeeded and the catalog did not, and the difference is age.** The zone
# buckets were created by `infra/foundation` in an earlier apply and had existed for hours; the
# catalog's bucket is created by *this* layer, seconds before Unity Catalog was asked to read it.
# The wait covered the role and not the thing the role reads.
#
# So the bucket's configuration is in the chain: the encryption rule and the public-access block,
# because a bucket whose SSE settings have not settled is a bucket a KMS-scoped role cannot read
# yet either. **The 30 seconds now start when the bucket is finished rather than when the policy
# is attached.**
resource "time_sleep" "uc_iam_propagation" {
  depends_on = [
    aws_iam_role_policy.uc,
    aws_iam_role_policy.uc_catalog,
    aws_s3_bucket_server_side_encryption_configuration.catalog,
    aws_s3_bucket_public_access_block.catalog,
  ]
  create_duration = "30s"
}

resource "databricks_storage_credential" "zone" {
  for_each = toset(local.zones)
  provider = databricks.workspace

  name    = "holdout-${each.key}"
  comment = "Unity Catalog's access to the ${each.key} zone. One credential per zone, one blast radius per zone."

  aws_iam_role {
    role_arn = aws_iam_role.uc[each.key].arn
  }

  depends_on = [time_sleep.uc_iam_propagation]
}

resource "databricks_external_location" "zone" {
  for_each = toset(local.zones)
  provider = databricks.workspace

  name            = "holdout-${each.key}"
  url             = "s3://${data.aws_ssm_parameter.zone[each.key].value}/"
  credential_name = databricks_storage_credential.zone[each.key].name
  comment         = "The ${each.key} zone, governed by Unity Catalog rather than by a bucket policy."

  # **`false`, and it is the whole point of the layer.** A destroy that refused to remove an
  # external location would leave Unity Catalog holding a pointer at a bucket `destroy` had
  # already taken, which is an estate reported as gone with a dangling grant.
  force_destroy = true
}
