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

variable "model_version" {
  type = string
  # **Declared with no default, and the absence is the layer's whole precondition.**
  #
  # `CLAUDE.md`: *an endpoint cannot point at a model version that does not exist yet, and a
  # version exists only after `backfill` has trained one.* A default here — `"1"`, or `"latest"` —
  # would let this layer apply before any training run had happened, and the endpoint would come
  # up pointing at nothing while reporting success.
  #
  # `backfill` supplies it, from the version its own training task registered. That is why this
  # layer is applied by `backfill` and not by `deploy`: the value does not exist at `deploy` time.
  description = "The registered model version to serve. No default: it does not exist until backfill has trained one."
}

variable "scale_to_zero" {
  type    = bool
  default = true
  # **The most expensive layer's only cost control, and it defaults to on.**
  #
  # `CLAUDE.md`: *`serving` is the most expensive layer and the only one that bills while idle. It
  # is applied last and destroyed first.* An endpoint that scales to zero bills nothing between
  # requests and takes a few seconds to wake — which is the right trade for a demonstration, and
  # the wrong one for 2.4M decisions a day. **The scenario is not this estate**, and this variable
  # is where that difference is written down rather than assumed.
  description = "Scale the endpoint to zero between requests. True: this estate is not the scenario."
}
