# **Cross-layer references go `outputs` → SSM parameter → `data`, never a remote state read.**
# `CLAUDE.md` states the rule and the reason: a remote state read creates hidden coupling and
# destroys the isolation the layers exist for. A layer that reads another layer's state can be
# broken by a refactor in that state that changes nothing anybody published.

data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

data "aws_region" "current" {}

# The region `infra/bootstrap` actually applied with, read back rather than assumed.
#
# **`var.region` has a default and this parameter does not**, which is the whole point: the
# default is what a laptop uses when nobody says otherwise, and this is what the estate was built
# with. They are the same today. The precondition below is what says so on every plan instead of
# on the day they diverge — and they diverge silently, because every resource here would simply
# be created in the wrong region and nothing would error.
data "aws_ssm_parameter" "region" {
  name = "/holdout/bootstrap/region"

  lifecycle {
    postcondition {
      condition     = self.value == var.region
      error_message = <<-EOT
        infra/bootstrap applied in ${self.value} and this layer is configured for ${var.region}.

        Nothing would fail: every resource below would be created in ${var.region}, the state
        would be written to a bucket in ${self.value}, and the two halves of the estate would sit
        in different regions with no error anywhere. A Unity Catalog metastore is one per region
        per account, so the workspace would attach to a metastore this layer never looked at.

        Set -var=region= to match, or re-apply infra/bootstrap deliberately.
      EOT
    }
  }
}

# The deploy role's ARN, published by `infra/bootstrap`. Read here so the reaper's policy can be
# written against the identity that will actually run it rather than against a name typed twice.
data "aws_ssm_parameter" "deploy_role_arn" {
  name = "/holdout/bootstrap/deploy_role_arn"
}
