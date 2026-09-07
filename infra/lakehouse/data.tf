# **Everything this layer consumes, read from what `infra/foundation` published.**
#
# `CLAUDE.md`: cross-layer references go `outputs` → SSM parameter → `data`. Never a remote state
# read — that creates hidden coupling and destroys the isolation the layers exist for.

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

data "aws_ssm_parameter" "workspace_url" {
  name = "/holdout/foundation/workspace_url"
}

data "aws_ssm_parameter" "metastore_id" {
  name = "/holdout/foundation/metastore_id"
}

data "aws_ssm_parameter" "data_key_arn" {
  name = "/holdout/foundation/data_key_arn"
}

# The region bootstrap applied with, asserted rather than assumed — the same postcondition
# `infra/foundation/data.tf` carries, and for the same silent failure: every resource created in
# one region, state written to a bucket in another, and no error anywhere.
data "aws_ssm_parameter" "region" {
  name = "/holdout/bootstrap/region"

  lifecycle {
    postcondition {
      condition     = self.value == var.region
      error_message = <<-EOT
        infra/bootstrap applied in ${self.value} and this layer is configured for ${var.region}.

        A Unity Catalog metastore is one per region per account, so a catalog created here would
        attach to a metastore this layer never looked at, over buckets a region away.
      EOT
    }
  }
}

locals {
  # **The four zones, read one by one rather than listed once.** The names live in
  # `infra/foundation`; this layer knows only that they were published under these keys, which is
  # what makes the coupling an interface rather than a copy.
  zones = ["landing", "bronze", "silver", "gold"]
}

data "aws_ssm_parameter" "zone" {
  for_each = toset(local.zones)
  name     = "/holdout/foundation/zone_${each.key}"
}
