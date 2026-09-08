# **Every variable here that has no default has none on purpose, and says so in those words.**
# `tests/infra/test_variable_declarations.py` refuses a block that says it has no default and
# declares one — a description asserting the absence of the thing declared below it is worse than
# a description that says nothing, because it tells the next reader a protection is in place.

variable "region" {
  type = string
  # The one region the estate runs in. It carries a default because it is not a secret and
  # because the argument for it is a fact about a product rather than about this account:
  # `eu-west-1` is in Zerobus Ingest's availability list, and Zerobus is the binding constraint
  # on this estate. `infra/bootstrap` publishes the applied value to `/holdout/bootstrap/region`,
  # and `data.tf` reads it back rather than trusting this default to have been the one used.
  default     = "eu-west-1"
  description = "The AWS region the estate runs in. Zerobus Ingest availability is what picks it."
}

variable "vpc_cidr" {
  type        = string
  default     = "10.42.0.0/16"
  description = <<-EOT
    The VPC's address range.

    It is a private range with no peering, no transit gateway and no on-premises counterpart, so
    it can be anything that does not collide with itself. It is a variable rather than a literal
    because a second estate in the same account would need a different one, and discovering that
    by reading a hard-coded string mid-apply is the discovery this variable exists to prevent.
  EOT
}

variable "ttl_hours" {
  type    = number
  default = 48
  # **This is the number the whole cost posture rests on**, and `CLAUDE.md` ranks the reaper as
  # level 1 of three: *the real net. Depends on no workflow's control flow.* The budget is level
  # 2 and tells you the model was wrong; `destroy` is level 3 and is a convenience.
  #
  # 48 hours rather than 6: one full cycle is modelled at ~6 hours of estate, and `destroy` is
  # deliberately never automatic — on success the standing estate is what screen recordings and
  # console screenshots need, and that is the one thing a rerun cannot regenerate. A reaper that
  # collects while the evidence is being captured costs a whole cycle to get back.
  description = "Hours after which the reaper destroys tagged estate, whatever else happened."
}

variable "owns_metastore" {
  type    = bool
  default = true
  # **It was called `create_metastore`, and the name is what made it dangerous.**
  #
  # *Create* describes the first apply. The variable does not: it records **whether this project
  # owns the metastore**, which is a relationship that holds on every apply after the first as
  # well. A reader reaching for `false` on the second dispatch — *the metastore already exists, so
  # do not create it* — is reading the name correctly and getting the opposite of what they want,
  # because `count = 0` plans a **destroy** of what the first apply created, and `force_destroy`
  # means nothing refuses.
  #
  # **That is not hypothetical: it happened on 2026-09-08**, by the session that had written the
  # warning three times. The dispatch was cancelled before Terraform reached the resource and
  # nothing was lost, and the lesson is not *read the comment more carefully* — the comment was
  # there and was read. **The name is the thing a person acts on under time pressure**, and a
  # name describing an event cannot express a state.
  #
  # **The default moved from `false` to `true` in the same change, and that is the larger half.**
  #
  # `false` was argued as the safe direction: *the dangerous direction is creating a second
  # metastore, not failing to create the first.* **That was wrong about which failure is worse.**
  # A second metastore is impossible — the account refuses it, loudly, at the first apply that
  # tries. Destroying the one that exists is not impossible, is silent until the plan is read, and
  # takes every catalog, schema, grant and external location with it.
  #
  # So the two failure modes are:
  #
  #     default true,  forgotten  ->  a create that the account refuses. A red run.
  #     default false, forgotten  ->  a destroy of the metastore and everything in it.
  #
  # `watermark`'s rule, which this repository has already borrowed once for the reaper's dry run:
  # **forgetting the variable should under-delete, which costs money, rather than over-delete,
  # which costs data.** Under that rule the safe default is `true`, and the first argument had the
  # asymmetry backwards.
  # **A Unity Catalog metastore is one per region per account, so it is not this project's to
  # own by default.** That is the `oidc.tf` lesson in a more expensive resource: the GitHub OIDC
  # provider is unique per issuer per account, another project had created it first, and
  # declaring it as an unconditional `resource` failed the first apply with
  # `EntityAlreadyExists`. A metastore fails the same way and takes longer to find out.
  #
  # Measured on 2026-09-05: this account has **no metastore in any region**, no workspaces, no
  # storage credentials and no external locations — so the switch is `true` for the first apply
  # and `false` for ever afterwards. It defaults to `false` because the dangerous direction is
  # creating a second one, not failing to create the first: a missing metastore is a `plan` that
  # says so, and a duplicate is an account-level object two projects both believe they own.
  #
  # **Both branches exist.** With the switch off, `data.databricks_metastore` reads the account's
  # metastore and a `postcondition` asserts it is in this region; with it on, the resource is
  # created and the same assertion holds by construction. A switch with only one branch written
  # is a switch that has never been off.
  description = "Create the account's Unity Catalog metastore, rather than reading the one that exists."
}

variable "databricks_account_id" {
  type      = string
  sensitive = true
  # **Declared with no default.** It identifies the Databricks account and belongs in no
  # committed file; `deploy.yml` supplies it from a repository secret, and a laptop supplies it
  # from the environment. `terraform validate` never needs a value — validation reads
  # configuration and contacts nothing — and `terraform plan` stops with *"is not set, and has no
  # default value"*, which is the behaviour that makes the absence a protection rather than an
  # inconvenience.
  description = "Databricks account id. No default: it is an identifier, supplied at apply time."
}

variable "databricks_client_id" {
  type      = string
  sensitive = true
  # No default, for the reason above: this is the account-level service principal's id, half of
  # an OAuth M2M credential.
  description = "Account service principal's client id. No default: half of a credential."
}

variable "databricks_client_secret" {
  type      = string
  sensitive = true
  # No default. The other half, and the half that is a secret in the ordinary sense.
  description = "Account service principal's OAuth secret. No default: it is a credential."
}

variable "reaper_dry_run" {
  type    = bool
  default = true
  # **The default is `true` and that is the safe direction rather than the common one.**
  #
  # `watermark` inverted the same switch deliberately, and its argument transfers whole: a
  # deployment that forgets the variable then **under-deletes, which costs money, rather than
  # over-deletes, which costs data.** Here the asymmetry is sharper still, because
  # `collect_billing_surfaces` has never been pointed at a live workspace -- a first apply that
  # defaulted to deleting would exercise an unrun code path against real compute.
  #
  # `infra/foundation/README.md` says the honest first-run sequence is one dry run read in the log
  # before it is trusted with `false`. **This variable is what makes that sequence followable**;
  # it was a string literal `"false"` in the function's environment, so following the stated
  # procedure meant editing Terraform, applying, reading, editing back and applying again.
  description = "Report what the reaper would delete instead of deleting it. Default: report."
}
