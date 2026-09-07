# **What this layer publishes, and it is published rather than output.**
#
# `CLAUDE.md`: *cross-layer references go `outputs` → SSM parameter → `data`. Never a remote state
# read.* The outputs at the bottom of this file exist for a human reading a plan; the parameters
# above them are the interface. `lakehouse`, `pipelines`, `ml` and `serving` read these names and
# never this layer's state.
#
# **And publishing is not a courtesy to the layers above — it is what makes the reaper correct.**
# `reap.py`'s second enumeration is exactly this set: a resource whose name never reached SSM is
# one it can report as uncollectable but can never collect. Every parameter below is therefore
# both an interface and a declaration that something exists.

locals {
  # One map, so a resource added here cannot be published under a name that disagrees with the
  # one it is stored under. Two lists would be two enumerations of one population, which is the
  # defect this repository catalogues most.
  published = merge(
    {
      "workspace_url"  = databricks_mws_workspaces.this.workspace_url
      "workspace_id"   = tostring(databricks_mws_workspaces.this.workspace_id)
      "metastore_id"   = local.metastore_id
      "data_key_arn"   = aws_kms_key.data.arn
      "reaper_lambda"  = aws_lambda_function.reaper.function_name
      "cross_account"  = aws_iam_role.cross_account.arn
      "workspace_root" = aws_s3_bucket.root.bucket
    },
    { for zone, bucket in aws_s3_bucket.zone : "zone_${zone}" => bucket.bucket },
  )
}

resource "aws_ssm_parameter" "published" {
  for_each = local.published

  name  = "/holdout/foundation/${each.key}"
  type  = "String"
  value = each.value

  # **`String` and not `SecureString`, deliberately, and the two credentials in `reaper.tf` are
  # the exception rather than the rule.** None of these is a secret: a bucket name, a workspace
  # URL and a role ARN are identifiers that the layers above need and that appear in every plan.
  # Encrypting them would buy nothing and would cost the reaper a `kms:Decrypt` on its widest
  # enumeration.
}

output "workspace_url" {
  value       = databricks_mws_workspaces.this.workspace_url
  description = "The workspace's URL. Also published to /holdout/foundation/workspace_url."
}

output "metastore_id" {
  value       = local.metastore_id
  description = "Whichever branch of create_metastore produced it. Also published to SSM."
}

output "zones" {
  value       = { for zone, bucket in aws_s3_bucket.zone : zone => bucket.bucket }
  description = "The four zone buckets by name. lakehouse turns these into external locations."
}
