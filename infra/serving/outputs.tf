locals {
  published = {
    "endpoint_name" = databricks_model_serving.demand.name
    "model_version" = var.model_version
  }
}

resource "aws_ssm_parameter" "published" {
  for_each = local.published

  name  = "/holdout/serving/${each.key}"
  type  = "String"
  value = each.value
}

output "endpoint_name" {
  value       = databricks_model_serving.demand.name
  description = "The endpoint. `run` asks it a live question; `destroy serving` removes it in about two minutes."
}

# **The version is published as well as consumed, and that is not redundant.**
#
# `run` has to be able to say *which* version answered the live question, and the only place that
# is written down after the fact is here. A readout that named an endpoint without naming a
# version would be the same defect as a number without a pinned Delta version, one layer over.
output "model_version" {
  value       = var.model_version
  description = "The served version. What answered a question is part of the answer."
}
