# The provider, pinned to an exact version rather than to a range — the same rule
# `infra/lakehouse/versions.tf` states and for the same reason: `~>` would let a patch release
# change what `terraform validate` accepts, which makes a required check a moving target.
terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.63.0"
    }
    # Used once, by `github.tf`, to publish the deploy role's ARN into the repository that will
    # assume it. Pinned exactly for the same reason as the one above.
    github = {
      source  = "integrations/github"
      version = "6.6.0"
    }
  }
}
