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
# **Three environments from one list**, so `oidc.tf`'s `local.environments` and these resources
# cannot drift: the trusted subjects and the objects that produce them are generated from the
# same source. `oidc.tf:117`'s argument for writing the names literally was that a knob silently
# breaks federation when turned — **one list turned by one hand is not that knob**; two lists that
# must agree is.
#
# **`plan` has no reviewer and that is the whole reason it exists.** An approval on a job that has
# not planned yet is an approval of a layer name; the plan job runs unattended, and the reviewer
# on `deploy` then approves a diff. **`protected_branches` is on all three**, because an
# environment reachable from any branch is a reviewer approving a branch nobody reviewed.
resource "github_repository_environment" "estate" {
  for_each    = toset(local.environments)
  repository  = local.repo
  environment = each.key

  dynamic "reviewers" {
    # No reviewer on `plan`. `for_each` over a one-or-zero list rather than a `count` on the
    # resource, because the environment must exist either way — it is half of the trust
    # condition, and an environment that does not exist refuses the token that names it.
    for_each = each.key == "plan" ? [] : [1]
    content {
      users = [var.github_owner_id]
    }
  }

  deployment_branch_policy {
    protected_branches     = true
    custom_branch_policies = false
  }
}



# **Two `moved` blocks, because this refactor changes an address that is already applied.**
#
# `github_repository_environment.deploy` and `.destroy` exist in the account and in this layer's
# state, applied 2026-09-05. Collapsing them into one `for_each` resource changes **both** the
# label and the address shape — `.deploy` becomes `.estate["deploy"]` — and Terraform matches
# state to configuration **by address**. Without these, the plan is *two destroys and three
# creates* for a change whose whole content is one addition.
#
# **Three reasons that is not merely noisy**, in order:
#
# **It asks for approval of a plan containing destroys, on the trust anchor, applied by hand.**
# `CLAUDE.md`'s posture is that a destroy is deliberate and never incidental; a surprise
# `- destroy` in a hand-applied plan is either rubber-stamped or aborted, and both are wrong for
# a change whose content is one addition.
#
# **It erases the environments' deployment history** — who approved which dispatch and when,
# which is the audit trail of the human gate. Doctrine rule 4 says a correction never erases what
# was previously stated, and this would erase it as a side effect of a rename.
#
# **And it opens a window where an environment named in the trust policy does not exist.**
# Terraform may destroy `deploy` before creating `estate["deploy"]`, and the comment above calls
# these objects half of that trust.
#
# **`moved` rather than `terraform state mv`**, for the reason this file already gives about the
# environments themselves: state surgery is a console-shaped act performed once by whoever
# happens to run it, and a `moved` block is configuration that goes through a pull request.
#
# **And the general lesson is worth more than the fix: `terraform validate` reads configuration
# and never reads state, so a rename is invisible to the check this branch is green on.**
# `infra/bootstrap` keeps its state locally — by design, for the chicken-and-egg reason `main.tf`
# gives — which makes *what will this plan do to what is already applied* answerable on this
# laptop, and this is the only layer in the estate where that is true.
moved {
  from = github_repository_environment.deploy
  to   = github_repository_environment.estate["deploy"]
}

moved {
  from = github_repository_environment.destroy
  to   = github_repository_environment.estate["destroy"]
}
