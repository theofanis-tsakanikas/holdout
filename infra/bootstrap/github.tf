# **The trust anchor writes its own trust, so nothing is copied by hand.**
#
# A workflow authenticates by assuming `aws_iam_role.deploy`, and to assume it the workflow has
# to name its ARN. That ARN carries the account id, so it may not be a literal in a workflow file
# in a public repository — it is a repository secret. **And a secret set in a browser is a console
# action**, which `CLAUDE.md` forbids in the same words it forbids one in AWS: *IaC only. No
# console actions, ever.*
#
# So the layer that creates the role also publishes it. `terraform apply` here leaves GitHub able
# to authenticate; there is no step afterwards where somebody pastes a string, and no window in
# which the role exists and the repository does not know it.
#
# **The pattern is taken from `fintelliguard`, which learned it the hard way.** Its bootstrap
# workflow carries the record: an earlier version assumed `secrets.AWS_DEPLOY_ROLE_ARN` in order
# to run the layer whose whole purpose is to create that role — *"the trust anchor cannot be
# derived from the trust it anchors."* Publishing from inside the local apply is what closes that
# loop rather than describing it.
#
# **The token is not a variable and is not stored.** The provider reads `GITHUB_TOKEN` from the
# environment of whoever runs the apply — `gh auth token` on a laptop — so no credential enters
# this repository, this state file or this configuration. An apply without it fails at plan time
# with the provider naming what is missing, which is the correct failure: the layer's job is only
# finished when GitHub can authenticate, and an apply that skipped this silently would report
# success for a bootstrap that is not one.

provider "github" {
  owner = split("/", var.repository)[0]
}

resource "github_actions_secret" "deploy_role_arn" {
  repository      = split("/", var.repository)[1]
  secret_name     = "AWS_DEPLOY_ROLE_ARN"
  plaintext_value = aws_iam_role.deploy.arn
}

# The region is not a secret and is already a default in `variables.tf` with its argument beside
# it. It is published as a **variable** rather than a secret for exactly that reason: a value in
# `secrets` that is not secret teaches a reader that everything in there is arbitrary, and the
# one thing in there that matters is the account id inside the role ARN.
resource "github_actions_variable" "aws_region" {
  repository    = split("/", var.repository)[1]
  variable_name = "AWS_REGION"
  value         = var.region
}
