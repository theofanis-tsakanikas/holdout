# Pinned exactly, the rule every layer here states: `~>` would let a patch release change what
# `terraform validate` accepts, which makes a required check a moving target.
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
  }

  # Partial, for the reason `infra/foundation/versions.tf` gives: the state bucket's name is
  # derived from the account id and this repository is public. `deploy` supplies the coordinates
  # at `init`, and this block's presence is what tells `deploy` the layer is ready to apply.
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
      "holdout:layer"   = "pipelines"
      "holdout:managed" = "terraform"
    }
  }
}

# **Workspace plane only.** This layer creates no account-level object: jobs, and nothing that a
# second project could collide with. `lakehouse` needed both planes because a metastore is
# account-level; nothing here is.
provider "databricks" {
  host          = data.aws_ssm_parameter.workspace_url.value
  client_id     = var.databricks_client_id
  client_secret = var.databricks_client_secret
  auth_type     = "oauth-m2m"
}
