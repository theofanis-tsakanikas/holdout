# The provider, pinned to an exact version rather than to a range.
#
# `~>` would let a patch release change what `terraform validate` accepts, which makes a required
# check a moving target: a green run and a red run could differ by a provider nobody chose. The
# lock file beside this pins the hashes; this pins the version a reader sees without opening it.
terraform {
  required_version = ">= 1.9"

  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "1.130.0"
    }
  }
}

# **No backend block, deliberately.** Nothing here is applied, so there is no state to keep, and a
# backend declared for a layer that never applies would read as though somebody had decided where
# state lives. `infra/bootstrap/` is where that decision belongs and it is phase 3.

# **A host with no credential, and it is not a placeholder for one.** `terraform validate` needs
# the provider to be configurable; it never contacts this address, because validation reads
# configuration and does not talk to anything. A real workspace URL would put an account
# identifier in a public repository for no gain — `CLAUDE.md`: every commit is a publication at
# the moment it is made.
provider "databricks" {
  host = "https://validate.invalid"
}
