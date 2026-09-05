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
  repository      = local.repo
  secret_name     = "AWS_DEPLOY_ROLE_ARN"
  plaintext_value = aws_iam_role.deploy.arn
}

# The region is not a secret and is already a default in `variables.tf` with its argument beside
# it. It is published as a **variable** rather than a secret for exactly that reason: a value in
# `secrets` that is not secret teaches a reader that everything in there is arbitrary, and the
# one thing in there that matters is the account id inside the role ARN.
resource "github_actions_variable" "aws_region" {
  repository    = local.repo
  variable_name = "AWS_REGION"
  value         = var.region
}

# **The two environments the trust condition names, created here rather than in a browser.**
#
# `oidc.tf` trusts `environment:deploy` and `environment:destroy` and nothing else, so **these
# two objects are half of that trust**: without them no workflow can present a subject the role
# accepts, and with them wrong — no reviewer, or an unprotected branch policy — the human gate
# the environment exists for is not there while the federation still works.
#
# **Every sibling project creates these by hand.** That is the one place this layer deliberately
# does not follow them: `CLAUDE.md` says *IaC only. No console actions, ever*, and a required
# reviewer configured by clicking is a protection whose existence nobody can prove from the
# repository. It is also the protection most worth proving.
#
# `required_reviewers` is what makes a dispatch wait. `protected_branches` is the second half:
# without it an environment can be targeted from any branch, and a reviewer who approves a
# deployment is approving a branch nobody reviewed.
resource "github_repository_environment" "deploy" {
  repository  = local.repo
  environment = "deploy"

  reviewers {
    users = [var.github_owner_id]
  }

  deployment_branch_policy {
    protected_branches     = true
    custom_branch_policies = false
  }
}

# **`destroy` is protected too, and the reason is not symmetry.** A teardown is not a safe
# operation to leave unguarded because it is cheap: `CLAUDE.md` is explicit that on a failure
# tearing down destroys the evidence, and that `destroy` is *always a deliberate dispatch, never
# automatic*. An environment with a reviewer is what makes "deliberate" a property of the system
# rather than of somebody's intention.
resource "github_repository_environment" "destroy" {
  repository  = local.repo
  environment = "destroy"

  reviewers {
    users = [var.github_owner_id]
  }

  deployment_branch_policy {
    protected_branches     = true
    custom_branch_policies = false
  }
}
