# The providers, pinned exactly — the rule `infra/bootstrap` and `infra/foundation` both state:
# `~>` would let a patch release change what `terraform validate` accepts, which makes a required
# check a moving target.
terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.63.0"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "1.130.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "0.12.1"
    }
  }

  # **A backend, and a partial one, for the reasons `infra/foundation/versions.tf` gives at
  # length.** This is also what `deploy`'s `ready` derivation reads: the absence of this block is
  # how a layer says *nothing here is applied*, and this layer said exactly that until now.
  backend "s3" {
    use_lockfile = true
    encrypt      = true
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      "holdout:project" = "holdout"
      "holdout:layer"   = "lakehouse"
      "holdout:managed" = "terraform"
    }
  }
}

# **Two Databricks providers, because this layer talks to both planes.**
#
# The account plane owns the metastore and its bindings; the workspace plane owns catalogs,
# schemas, grants, the warehouse and the dashboards. They authenticate the same way and against
# different hosts, and conflating them produces errors that name neither.
#
# **The workspace host is read from SSM rather than declared.** `infra/foundation` published it,
# `CLAUDE.md` says cross-layer references go `outputs` → SSM → `data`, and a workspace URL
# contains an account-derived identifier that may not be committed.
provider "databricks" {
  alias         = "account"
  host          = "https://accounts.cloud.databricks.com"
  account_id    = var.databricks_account_id
  client_id     = var.databricks_client_id
  client_secret = var.databricks_client_secret
  auth_type     = "oauth-m2m"
}

provider "databricks" {
  alias         = "workspace"
  host          = data.aws_ssm_parameter.workspace_url.value
  client_id     = var.databricks_client_id
  client_secret = var.databricks_client_secret
  auth_type     = "oauth-m2m"
}
