data "aws_ssm_parameter" "workspace_url" { name = "/holdout/foundation/workspace_url" }
data "aws_ssm_parameter" "catalog" { name = "/holdout/lakehouse/catalog" }

locals {
  zones = ["silver", "gold"]
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
      error_message = "infra/bootstrap applied in ${self.value} and this layer is configured for ${var.region}."
    }
  }
}
