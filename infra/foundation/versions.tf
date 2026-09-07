# The providers, pinned to exact versions rather than to ranges — the rule
# `infra/bootstrap/versions.tf` and `infra/lakehouse/versions.tf` both state, for the same
# reason: `~>` would let a patch release change what `terraform validate` accepts, which makes a
# required check a moving target.
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
    # Used once, by `reaper.tf`, to zip the handler. Pinned exactly for the same reason as the
    # two above: a patch release that changed the archive's bytes would change the Lambda's
    # source hash and plan a replacement for a file nobody edited.
    archive = {
      source  = "hashicorp/archive"
      version = "2.7.1"
    }
    # Used once, by `workspace.tf`, to let IAM propagate before Databricks validates the
    # cross-account role. Pinned exactly for the same reason as the others.
    time = {
      source  = "hashicorp/time"
      version = "0.12.1"
    }
  }

  # **A backend, because this layer applies from CI, and a partial one because the alternative
  # publishes an account-derived identifier.**
  #
  # `deploy.yml` refuses to apply a layer that declares no backend: a layer applied without one
  # writes its state to the runner and discards it, so the next apply plans against nothing and
  # proposes to create everything a second time. That check asserts applyability rather than
  # existence, and this block is what satisfies it.
  #
  # **The configuration is deliberately empty.** The bucket is
  # `holdout-tfstate-${substr(sha256(account_id), 0, 12)}` — not the account id, but a stable
  # value derived from it, and `CLAUDE.md` is unambiguous that every commit is a publication at
  # the moment it is made. So `bucket`, `key`, `region` and `kms_key_id` arrive at `init` time
  # through `-backend-config`, read from the parameters `infra/bootstrap` publishes at
  # `/holdout/bootstrap/*`. A backend block cannot interpolate a variable, which is why this is
  # the mechanism rather than a preference.
  #
  # `use_lockfile` is S3's native conditional-write lock and needs Terraform >= 1.10, which the
  # line above requires. There is no DynamoDB table anywhere in this project.
  backend "s3" {
    use_lockfile = true
    encrypt      = true
  }
}

# The AWS provider. Every resource this layer creates carries the estate tags, so the budget's
# `TagKeyValue` filter and the TTL reaper both see them without any resource repeating itself.
#
# **`holdout:*` rather than `Project`/`Layer`.** Activating a generic tag key for cost allocation
# is an account-level act in an account holding four other projects — the same ownership mistake
# `oidc.tf` records about the OIDC provider, and `infra/bootstrap/budget.tf` is where the
# namespaced keys are activated.
provider "aws" {
  region = var.region

  default_tags {
    tags = {
      "holdout:project" = "holdout"
      "holdout:layer"   = "foundation"
      "holdout:managed" = "terraform"
    }
  }
}

# The Databricks provider, at **account** level.
#
# A workspace does not exist yet, so there is no workspace host to authenticate against; this
# layer is the one that creates it. Account-level OAuth M2M (`auth_type = "oauth-m2m"`) is what
# the account API accepts, and the three values it needs are declared as variables with no
# defaults — an account id and a service-principal secret are credentials, and a default would
# put one in this file.
provider "databricks" {
  alias         = "account"
  host          = "https://accounts.cloud.databricks.com"
  account_id    = var.databricks_account_id
  client_id     = var.databricks_client_id
  client_secret = var.databricks_client_secret
  auth_type     = "oauth-m2m"
}
