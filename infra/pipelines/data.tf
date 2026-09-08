# Everything this layer consumes, read from what the layers below published. Never a remote state
# read — `CLAUDE.md`'s rule and the reason the layers are separable at all.

data "aws_ssm_parameter" "workspace_url" { name = "/holdout/foundation/workspace_url" }
data "aws_ssm_parameter" "catalog" { name = "/holdout/lakehouse/catalog" }
data "aws_ssm_parameter" "warehouse_id" { name = "/holdout/lakehouse/warehouse_id" }

locals {
  zones = ["landing", "bronze", "silver", "gold"]
}

data "aws_ssm_parameter" "zone" {
  for_each = toset(local.zones)
  name     = "/holdout/foundation/zone_${each.key}"
}

data "aws_ssm_parameter" "region" {
  name = "/holdout/bootstrap/region"

  lifecycle {
    postcondition {
      condition     = self.value == var.region
      error_message = "infra/bootstrap applied in ${self.value} and this layer is configured for ${var.region}. A job would read buckets a region away from the workspace running it."
    }
  }
}
