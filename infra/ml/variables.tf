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
  type        = string
  default     = "https://github.com/theofanis-tsakanikas/holdout"
  description = "The repository the training job runs from. Public, so no git credential."
}

variable "git_ref" {
  type    = string
  default = "main"
  # The same declared weakness `infra/pipelines/variables.tf` argues at length: a branch means two
  # runs can execute different code while reporting the same configuration, and `backfill` is what
  # pins the dispatched sha. **It matters more here**, because the artefact this job produces is a
  # model version that a serving endpoint will later point at — and *which code trained it* is
  # part of what a model card has to be able to say.
  description = "The ref the training job runs. backfill pins the sha."
}

variable "git_commit" {
  type    = string
  default = ""
  # **A branch and a commit are different fields, and the first apply proved it.**
  #
  # `git_source` accepts `branch`, `tag` **or** `commit`, and `backfill` was passing the
  # dispatched sha as `git_ref` — which lands in `branch`. Databricks then looked for
  # `refs/heads/<sha>` and refused:
  #
  #     GIT_UNKNOWN_REF: Commit ref refs/heads/3bd3c423… not found
  #
  # **The field name was right and the value was the wrong kind for it**, which is a shape no
  # amount of reading the two files against each other would have caught: both were internally
  # consistent, and only the API knew that a forty-character hex string is not a branch.
  #
  # Empty means *use the branch*. `backfill` and `run` set it to the sha they dispatched, so the
  # pin lands where a number is produced — which is the whole argument `git_ref` makes above.
  description = "Pin the jobs to a commit. Empty: use git_ref as a branch instead."
}
