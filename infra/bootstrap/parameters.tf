# **What this layer built, published where the account can be asked rather than where a file has
# to be read.**
#
# Every later layer needs the state bucket's name, the key that encrypts it and the role that
# writes it — and every one of those is an account-identifying string that may not be committed.
# SSM is where they go: inside the account, readable by the deploy role, invisible to the
# repository. `CLAUDE.md` names *the SSM parameters* among what survives a teardown for exactly
# this reason, and `docs/DAY-ONE.md`'s discriminator is the same one — a value with an API is not
# manual work, and this is the API.
#
# **They are `String`, not `SecureString`, and that is a judgment rather than an oversight.** A
# bucket name, a key arn and a role arn are identifiers, not credentials: knowing them grants
# nothing, and `oidc.tf` is what decides who may use them. Encrypting an identifier with KMS
# would buy a KMS call per read and the appearance of a secret where there is none — and *the
# appearance of a protection that is not there* is the defect this repository keeps finding.

resource "aws_ssm_parameter" "state_bucket" {
  name        = "/holdout/bootstrap/state_bucket"
  description = "The Terraform state bucket. Every layer above bootstrap keeps its state here."
  type        = "String"
  value       = aws_s3_bucket.state.id
}

resource "aws_ssm_parameter" "state_kms_key_arn" {
  name        = "/holdout/bootstrap/state_kms_key_arn"
  description = "The key that encrypts Terraform state at rest."
  type        = "String"
  value       = aws_kms_key.state.arn
}

resource "aws_ssm_parameter" "deploy_role_arn" {
  name        = "/holdout/bootstrap/deploy_role_arn"
  description = "The role this repository's dispatch workflows assume through GitHub OIDC."
  type        = "String"
  value       = aws_iam_role.deploy.arn
}

resource "aws_ssm_parameter" "region" {
  name        = "/holdout/bootstrap/region"
  description = "The region the estate lives in. Baked into the state bucket, so it is not a preference."
  type        = "String"
  value       = var.region
}

# **The alert address, published once, encrypted, so the layers above can subscribe to their
# own failures without a second place to type it.** `infra/foundation/reaper.tf` declared its
# failure topic with no subscription because an email is personal data with no default in this
# repository -- true, and the consequence was a dead-letter topic nobody heard for a week. The
# address already exists here as `budget_alert_email`; publishing it as a SecureString under the
# state key is the same arrangement every other cross-layer value uses, and the value never
# enters a `.tf` file or a plan output.
resource "aws_ssm_parameter" "alert_email" {
  name        = "/holdout/bootstrap/alert_email"
  description = "Where a failure that a person has to hear about is sent. Encrypted; read by foundation."
  type        = "SecureString"
  key_id      = aws_kms_key.state.arn
  value       = var.budget_alert_email
}
