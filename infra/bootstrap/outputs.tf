# **Outputs are for the person at the terminal, and they are what the next layer's backend block
# has to be given.** The values are also in SSM, which is where a *workflow* reads them from;
# these exist so that the one manual step after `terraform apply` — writing the backend
# configuration for `infra/foundation` — does not require anybody to go and look them up.
#
# Nothing here is sensitive and nothing here is marked so. Marking an identifier `sensitive`
# would hide it from the applier who needs it, in exchange for nothing.

output "state_bucket" {
  description = "Backend `bucket` for every layer above this one."
  value       = aws_s3_bucket.state.id
}

output "state_kms_key_arn" {
  description = "Backend `kms_key_id`."
  value       = aws_kms_key.state.arn
}

output "deploy_role_arn" {
  description = "The role a dispatch workflow assumes. Goes in the workflow, not in a secret."
  value       = aws_iam_role.deploy.arn
}

output "region" {
  description = "Backend `region`, and the region every layer applies into."
  value       = var.region
}

output "backend_block" {
  description = <<-EOT
    The backend configuration to paste into the next layer, assembled here so that nobody has to
    reassemble it from four outputs. `use_lockfile` is what replaces the DynamoDB table AWS's own
    guides still describe, and it needs Terraform 1.10 or newer — the constraint `versions.tf`
    carries.
  EOT
  value       = <<-EOT
    terraform {
      backend "s3" {
        bucket       = "${aws_s3_bucket.state.id}"
        key          = "<layer>/terraform.tfstate"
        region       = "${var.region}"
        kms_key_id   = "${aws_kms_key.state.arn}"
        encrypt      = true
        use_lockfile = true
      }
    }
  EOT
}
