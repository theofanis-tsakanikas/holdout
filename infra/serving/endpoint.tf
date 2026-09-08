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

  tags {
    key   = "holdout:project"
    value = "holdout"
  }
}
