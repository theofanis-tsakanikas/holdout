# **The model serving endpoint — the most expensive object in the estate, applied last and
# destroyed first.**
#
# `CLAUDE.md` names it as the only layer that bills while idle, and everything about this file is
# shaped by that: it is applied by `backfill` rather than `deploy`, it scales to zero by default,
# and `destroy serving` exists as its own target so the expensive half can be taken in two minutes
# while the lakehouse stays browsable.

resource "databricks_model_serving" "demand" {
  name = "holdout-demand"

  config {
    served_entities {
      name           = "demand"
      entity_name    = data.aws_ssm_parameter.registered_model.value
      entity_version = var.model_version

      # **The smallest CPU size.** `CLAUDE.md` models the endpoint at 1–5 USD a cycle and this is
      # the assumption behind that figure. The interactive path is one question answered live; the
      # 2.4M decisions a day happen **inside the pipeline** from the same pinned version, and
      # never through this endpoint — *no LLM is anywhere near the decision path*, and neither is
      # an HTTP hop.
      workload_size = "Small"
      workload_type = "CPU"

      scale_to_zero_enabled = var.scale_to_zero
    }

    traffic_config {
      routes {
        served_model_name  = "demand"
        traffic_percentage = 100
      }
    }
  }

  # **`holdout_project`, and the underscore is the finding rather than a preference.**
  #
  #     cannot create model serving: Endpoint tag key holdout:project is either not between
  #     1-255 characters long or contains one or more of the reserved characters: . , = / or :
  #
  # Every other object in this estate carries `holdout:project` — it is what the budget filters
  # on, what the reaper enumerates, and what `destroy`'s survivor check reads. **Model serving
  # refuses a colon in a tag key**, so this one object cannot carry the estate's own key, and the
  # thing that reached the estate first was the whole `backfill`: baseline, window, silver, gold,
  # training, a registered version, and then this.
  #
  # **What that costs is stated rather than absorbed.** A serving endpoint is a Databricks object
  # and was never in the AWS tag population — `tag:GetResources` has never returned one — so
  # nothing that reads `holdout:project` loses sight of anything it could see before. What would
  # be wrong is to leave it untagged: `infra/foundation/reaper.py` enumerates billing surfaces by
  # tag on the workspace side, and an endpoint with no key at all is the shape of the finding this
  # register already holds about the network Databricks leaves behind.
  tags {
    key   = "holdout_project"
    value = "holdout"
  }
}
