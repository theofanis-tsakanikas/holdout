# **A Unity Catalog metastore is one per region per account, so this layer does not assume it owns
# one.** That is the `oidc.tf` lesson in a slower, more expensive resource: the GitHub OIDC
# provider is unique per issuer per account, another project had created it first, and declaring
# it as an unconditional `resource` failed the first apply with `EntityAlreadyExists`. A metastore
# fails the same way and takes longer to find out.
#
# `CLAUDE.md`'s row for this layer says **metastore attachment**, not creation, and the split
# below is what makes those two different acts rather than one word.

# ---------------------------------------------------------------- the branch that creates
resource "databricks_metastore" "this" {
  provider = databricks.account
  count    = var.create_metastore ? 1 : 0

  name   = "holdout-${var.region}"
  region = var.region

  # **No `storage_root`, deliberately.** A metastore-level root makes every catalog inherit one
  # location, which is the old shape; catalogs and external locations declare their own storage in
  # `lakehouse`, pointed at the four zones this layer creates. A root here would be a second place
  # storage is decided, and the zones are the first.
  #
  # **`force_destroy` because this branch means the project owns it.** `CLAUDE.md`'s survivor list
  # is exact — *the state bucket and its access-log bucket, the state KMS key, the SSM parameters
  # and the deploy role. Nothing else* — and a metastore this project created is not on it.
  force_destroy = true
}

# ---------------------------------------------------------------- the branch that reads
#
# **Both branches are written, because a switch with one branch is a switch that has never been
# off.** With `create_metastore = false` the account is expected to hold a metastore already —
# created by another project, or by an earlier apply of this one — and this layer attaches to it
# without claiming it.
#
# **What has actually been run, stated rather than implied.** Measured on 2026-09-05, this account
# holds **no metastore in any region**, no workspaces, no storage credentials and no external
# locations. So the first apply runs the branch above, and **the branch below has never executed
# against a real account.** It is written, it validates, and it is unexercised — which is a
# different claim from "it works", and this repository's own rule is that a line can be true of
# the code and false of the system.
data "databricks_metastore" "existing" {
  provider = databricks.account
  count    = var.create_metastore ? 0 : 1

  region = var.region

  lifecycle {
    postcondition {
      condition     = self.metastore_info[0].region == var.region
      error_message = <<-EOT
        The metastore this layer attached to is not in ${var.region}.

        A metastore is one per region per account, and a workspace attached to one in another
        region would work -- catalogs resolve, grants apply -- while every table it governs sat a
        region away from the S3 zones this layer created. Nothing would error and every byte would
        cross a region boundary on every read.
      EOT
    }
  }
}

locals {
  # The one id everything below uses, whichever branch produced it. **Written once**, because two
  # consumers each choosing a branch is doctrine rule 3's *interpreted by hand in two places*.
  metastore_id = var.create_metastore ? databricks_metastore.this[0].id : data.databricks_metastore.existing[0].id
}

# ---------------------------------------------------------------- the attachment
resource "databricks_metastore_assignment" "this" {
  provider     = databricks.account
  metastore_id = local.metastore_id
  workspace_id = databricks_mws_workspaces.this.workspace_id
}

# ═══════════════════════════════════════════════════════════════════════════════════════════════
# **The trap in this switch, written here because nothing else would catch it.**
#
# `create_metastore` is not a preference and it is not idempotent to change. It records **whether
# this project owns the metastore**, and it is set once.
#
# **Flipping it from `true` to `false` destroys the metastore.** The resource above goes to
# `count = 0`, Terraform plans a destroy, `force_destroy = true` means nothing refuses, and every
# catalog, schema, grant and external location in it goes with it. The plan says so — it is a
# visible `1 to destroy` line — which is exactly why `infra/bootstrap/README.md` instructs the
# author to **read the plan for `destroy` lines** rather than to trust that a variable change is
# small because the diff is one word.
#
# The reverse flip, `false` to `true`, is the failure that announces itself: the create fails
# because a metastore already exists in the region, which is the `EntityAlreadyExists` this whole
# file is shaped around.
#
# **So: set it `true` for the first apply of a region this project owns, and never change it.**
# There is no gate behind this paragraph. `terraform validate` cannot see a variable's history,
# and a `postcondition` cannot fire on a resource that is being destroyed.
# ═══════════════════════════════════════════════════════════════════════════════════════════════
