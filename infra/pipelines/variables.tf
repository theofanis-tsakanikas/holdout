variable "region" {
  type        = string
  default     = "eu-west-1"
  description = "The AWS region the estate runs in. Asserted against what bootstrap applied."
}

variable "databricks_client_id" {
  type        = string
  sensitive   = true
  description = "Account service principal's client id. No default: half of a credential."
}

variable "databricks_client_secret" {
  type        = string
  sensitive   = true
  description = "Account service principal's OAuth secret. No default: it is a credential."
}

variable "repository_url" {
  type    = string
  default = "https://github.com/theofanis-tsakanikas/holdout"
  # **The jobs run this repository's code, from this repository.** Not a wheel built somewhere and
  # uploaded, not a notebook pasted into the workspace: `git_source` below points Databricks at
  # the tree, and every task names a path in it. `CLAUDE.md`'s rule is *nothing is invented*, and
  # a job whose code arrives by a route nobody can retrace is the same defect one layer over.
  description = "The repository the jobs run from. Public, so no git credential is needed."
}

variable "git_ref" {
  type    = string
  default = "main"
  # **A branch rather than a commit, and it is a declared weakness.**
  #
  # A job pinned to `main` runs whatever `main` says at the moment it starts, so two runs a day
  # apart can execute different code while reporting the same configuration. That is exactly the
  # shape `CLAUDE.md` refuses at readout — *the readout pins a Delta version, because without it
  # re-running last month's readout returns a different number*.
  #
  # It is a branch anyway because the alternative is worse today: pinning a commit means this
  # layer is re-applied on every merge to `main`, which puts an `apply` in the path of every
  # routine edit — the thing `pipelines` was split from `lakehouse` to avoid. **`backfill` and
  # `run` are what will pin it**, by passing the dispatched sha, so the pin lands where a number
  # is actually produced rather than where code is stored.
  description = "The ref the jobs run. `main` by default; backfill and run pin the sha."
}
