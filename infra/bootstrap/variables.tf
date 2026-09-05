# Every value this layer needs from outside, and **no default that identifies anybody**.
#
# `CLAUDE.md`: *the repository is public and every commit is a publication at the moment it is
# made.* An account id, an email address or a workspace host written here would be published by
# the act of committing, and no `terraform destroy` takes it back. So the account is never named
# — `data.aws_caller_identity` reads it at apply time — and the two values that are personal are
# variables the applier supplies.
#
# The variables that must not carry a default say so **in their block**, which
# `tests/infra/test_variable_declarations.py` checks and which is why that guard landed before
# this layer was written rather than after it.

variable "region" {
  description = <<-EOT
    The AWS region the whole estate lives in. Defaulted here, deliberately: it is a decision
    already taken and published — `docs/DAY-ONE.md` §2 — rather than a value that varies by
    applier. `eu-west-1` is in Zerobus Ingest's availability list, which is the binding
    constraint on this estate; the managed-connector list is wider and no longer applies since
    the ERP path is files on S3.
  EOT
  type        = string
  default     = "eu-west-1"
}

variable "budget_alert_email" {
  description = <<-EOT
    Where the 50 / 80 / 100 % budget notifications go. Declared with no default because an email
    address is personal data, and a default here would publish one. The applier passes it; the
    value never enters the repository.
  EOT
  type        = string

  validation {
    condition     = can(regex("^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$", var.budget_alert_email))
    error_message = "budget_alert_email must be a single email address."
  }
}

variable "repository" {
  description = <<-EOT
    The GitHub repository whose workflows may assume the deploy role, as `owner/name`. This is
    already public — it is the repository you are reading — so it is not a secret, and it is a
    variable rather than a literal because the trust policy is the one place where getting it
    wrong grants somebody else's workflows access to this account.
  EOT
  type        = string
  default     = "theofanis-tsakanikas/holdout"
}

variable "budget_limit_usd" {
  description = <<-EOT
    The monthly budget. `CLAUDE.md`'s posture, in one number: **1,000 USD, alerts at 50/80/100 %
    and no stop action**; the stop action is at 150 % and is in `budget.tf` with its own argument.
  EOT
  type        = string
  default     = "1000"
}
