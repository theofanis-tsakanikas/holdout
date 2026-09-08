data "aws_ssm_parameter" "workspace_url" { name = "/holdout/foundation/workspace_url" }
data "aws_ssm_parameter" "registered_model" { name = "/holdout/ml/registered_model" }

data "aws_ssm_parameter" "region" {
  name = "/holdout/bootstrap/region"

  lifecycle {
    postcondition {
      condition     = self.value == var.region
      error_message = "infra/bootstrap applied in ${self.value} and this layer is configured for ${var.region}."
    }
  }
}
