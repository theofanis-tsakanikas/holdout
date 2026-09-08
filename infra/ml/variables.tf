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
