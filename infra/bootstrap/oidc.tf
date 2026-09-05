# GitHub Actions assumes a role here. **No access key exists anywhere in this estate**, which is
# the whole point: a long-lived credential in a repository's secrets is a credential that has to
# be rotated by somebody remembering to, and `docs/FINDINGS.md` is largely a record of what
# happens to things somebody has to remember.

# **No `thumbprint_list`, deliberately, and this is the one decision here that needed a source.**
#
# AWS IAM documentation, read 2026-09-05
# (https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html):
# *"AWS secures communication with OIDC identity providers (IdPs) using our library of trusted
# root certificate authorities (CAs) to verify the JSON Web Key Set (JWKS) endpoint's TLS
# certificate. If your OIDC IdP relies on a certificate that is not signed by one of these
# trusted CAs, only then we secure communication using the thumbprints set in the IdP's
# configuration."*
#
# The Terraform AWS provider's own documentation for this resource, read the same day, names
# GitHub among the providers AWS validates with its trusted-CA library — **and states the trap
# that makes this irreversible**: *"if a thumbprint list is initially configured and subsequently
# removed, Terraform continues using the original thumbprint list rather than prompting IAM to
# retrieve a new one."* So a thumbprint declared today is a thumbprint this estate carries
# forever, going stale on a certificate rotation nobody here will hear about, for a check AWS
# does not perform on this issuer. Declaring none is the reversible choice; declaring one is not.
#
# **The attribute is omitted rather than set to `[]`, and the difference is the trap itself.**
# Writing `thumbprint_list = []` *is* configuring one, and whether the provider treats an empty
# list as *configured-and-empty* or as *absent* is not something this repository can establish
# without an account to test against. Omitting it is the state the provider's own documentation
# describes — its example titled *"Create an IAM OIDC provider without a thumbprint"* declares no
# such attribute — so the code says what the paragraph above says, rather than saying it in a
# spelling that needs a footnote.
#
# ---
#
# **This layer usually reads the provider rather than creating it, and that is a correction made
# by an apply rather than by a reading.**
#
# An IAM OIDC provider is unique per issuer URL **per account**, not per project. The first
# `terraform apply` of this layer failed:
#
#     Error: creating IAM OIDC Provider: EntityAlreadyExists:
#     Provider with url https://token.actions.githubusercontent.com already exists.
#
# It was created on 2026-07-04 by another project in this portfolio. **So a per-project layer
# declaring `resource` here is a layer claiming to own an account-scoped object, and the second
# project to apply is the one that finds out.** Holdout was the second.
#
# The variable defaults to reading because that is true of the account this estate lives in. A
# fresh account sets it to `true` — the resource is kept rather than deleted precisely so the
# layer stays complete for an account that has none, which is what `IaC only` requires.
#
# **And what is read is asserted rather than assumed.** The audience is the other half of the
# trust condition below: a provider whose `client_id_list` does not carry `sts.amazonaws.com`
# would let every workflow fail at `AssumeRoleWithWebIdentity` with nothing here having noticed.
# Another project owns that list and could change it, so the postcondition below is this layer's
# only guard on a dependency it does not control.

variable "create_github_oidc_provider" {
  description = <<-EOT
    Whether this layer creates the GitHub OIDC provider or reads the one already in the account.
    An IAM OIDC provider is unique per issuer URL per **account**, so at most one project may own
    it. Defaults to reading, because this estate's account has had one since 2026-07-04. Set it
    to `true` in an account that has none.
  EOT
  type        = bool
  default     = false
}

resource "aws_iam_openid_connect_provider" "github" {
  count          = var.create_github_oidc_provider ? 1 : 0
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

data "aws_iam_openid_connect_provider" "github" {
  count = var.create_github_oidc_provider ? 0 : 1
  url   = "https://token.actions.githubusercontent.com"

  lifecycle {
    postcondition {
      condition     = contains(self.client_id_list, "sts.amazonaws.com")
      error_message = <<-EOT
        The account's GitHub OIDC provider does not accept `sts.amazonaws.com` as an audience,
        and the deploy role's trust condition requires it. Another project owns that provider;
        adding the audience is an account-level change and not this layer's to make silently.
      EOT
    }
  }
}

locals {
  github_oidc_arn = (
    var.create_github_oidc_provider
    ? one(aws_iam_openid_connect_provider.github[*].arn)
    : one(data.aws_iam_openid_connect_provider.github[*].arn)
  )
}

# **Every trusted subject names this repository and exactly one environment**, spelled out as a
# list rather than reached with a wildcard: `repo:owner/repo:*` trusts every branch and every
# pull request, **including one a stranger opens** — this repository is public — and it reads as
# a small convenience right up until it is the whole of the breach.
#
# **An environment rather than a branch, and that is the human gate.** GitHub environment
# protection is what makes a workflow wait for a named reviewer before it spends anything, and
# it is the property the author reserved to himself in words. `ref:refs/heads/main` is not that:
# it trusts every push that reaches `main`, with no moment at which a person decides.
#
# **Two forms of the same claim, because the account decides which it sends and not this file.**
# GitHub's OIDC reference, read 2026-09-05
# (https://docs.github.com/en/actions/reference/security/oidc): the subject is
# `repo:OWNER/NAME:environment:NAME` when a job declares an environment, and the branch form
# appears *"only if the job doesn't reference an environment"*. Accepting the name form and the
# id form widens nothing — both name one repository and one environment — and **the id form is
# the one that cannot be taken over, because a released account name can be re-registered by
# somebody else and an id cannot.**
#
# `deploy` and `destroy` are written here rather than taken from a variable: they must equal the
# `environment:` lines in `deploy.yml` and `destroy.yml` exactly, so a knob is one that silently
# breaks federation when turned — and the failure is an `AssumeRoleWithWebIdentity` denial that
# names nothing.
#
# **`ci.yml` runs on pull requests and never assumes this role**, and none of the four dispatch
# workflows exists yet — each is written by the task that first needs one, and each will declare
# its environment here by name.
#
# **This layer trusted `ref:refs/heads/main` until 2026-09-05.** Every sibling project in this
# portfolio — `manifest`, `watermark`, `attestor` — was already on the environment-and-id form,
# and `watermark`'s own comment carries the argument this paragraph is built from. **The pattern
# was copied from them and this half of it was not**, which is the second time in one day that
# sentence has been true of this layer.
locals {
  trusted_subjects = [
    "repo:${var.repository}:environment:deploy",
    "repo:${var.repository}:environment:destroy",
    "repo:${local.owner}@${var.github_owner_id}/${local.repo}@${var.github_repository_id}:environment:deploy",
    "repo:${local.owner}@${var.github_owner_id}/${local.repo}@${var.github_repository_id}:environment:destroy",
  ]
  owner = split("/", var.repository)[0]
  repo  = split("/", var.repository)[1]
}
data "aws_iam_policy_document" "deploy_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [local.github_oidc_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = local.trusted_subjects
    }
  }
}

resource "aws_iam_role" "deploy" {
  name               = "holdout-deploy"
  description        = "Assumed by this repository's dispatch workflows through GitHub OIDC. Phase 3."
  assume_role_policy = data.aws_iam_policy_document.deploy_trust.json
  # One hour. Long enough for `backfill`, which `CLAUDE.md` models at about an hour and a half —
  # so this will need raising, by the task that measures it rather than by a guess made here.
  max_session_duration = 3600
}

# **What this role can do today is the state backend and nothing else, and that is the
# deliberate part.**
#
# The layers it will apply — `foundation`, `lakehouse`, `pipelines`, `ml`, `serving` — do not
# exist. A permission set written now for resources nobody has declared is a permission set
# nobody can review: it would be either `AdministratorAccess`, which makes the trust condition
# above the only thing standing between a public repository and this account, or a guess that is
# wrong in both directions at once. **Each layer's task adds what that layer needs, with the
# resources it actually declares in front of whoever writes it.**
#
# So `T017` closes with a role that can hold state and apply nothing. `T018` is what makes it
# able to build a VPC, and the review of that permission set happens with the VPC on the page.
data "aws_iam_policy_document" "deploy_state" {
  statement {
    sid       = "ListTheStateBucket"
    effect    = "Allow"
    actions   = ["s3:ListBucket", "s3:GetBucketVersioning"]
    resources = [aws_s3_bucket.state.arn]
  }

  statement {
    sid    = "ReadWriteStateObjects"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    # **Objects, not the bucket resource** — which is what this statement and the one above it
    # actually split on, and it is all they split on. `arn/*` is **every object in the bucket**:
    # there is no key prefix here and `state.tf` declares none, so nothing is narrowed by it.
    # The effect today is nil, because the bucket holds state and nothing else. The reason the
    # sentence is corrected rather than left is that a comment asserting a restriction the line
    # below does not express is `T00Y`'s finding, one commit after `T00Y` — and `T00Y`'s guard
    # cannot see this one, because it reads `variable` blocks and this is a policy document.
    resources = ["${aws_s3_bucket.state.arn}/*"]
  }

  statement {
    sid    = "UseTheStateKey"
    effect = "Allow"
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:DescribeKey",
    ]
    resources = [aws_kms_key.state.arn]
  }

  statement {
    sid       = "ReadThePublishedParameters"
    effect    = "Allow"
    actions   = ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath"]
    resources = ["arn:${data.aws_partition.current.partition}:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter/holdout/*"]
  }
}

data "aws_partition" "current" {}

resource "aws_iam_policy" "deploy_state" {
  name        = "holdout-deploy-state"
  description = "Terraform state and the published parameters. Nothing else — see oidc.tf."
  policy      = data.aws_iam_policy_document.deploy_state.json
}

resource "aws_iam_role_policy_attachment" "deploy_state" {
  role       = aws_iam_role.deploy.name
  policy_arn = aws_iam_policy.deploy_state.arn
}
