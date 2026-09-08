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
      "holdout:layer"   = "serving"
      "holdout:managed" = "terraform"
    }
  }
}

provider "databricks" {
  host          = data.aws_ssm_parameter.workspace_url.value
  client_id     = var.databricks_client_id
  client_secret = var.databricks_client_secret
  auth_type     = "oauth-m2m"
}
