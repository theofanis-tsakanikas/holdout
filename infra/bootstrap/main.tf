# `infra/bootstrap/` — the layer that creates what every other layer's backend needs, and
# therefore the one layer that cannot use it.
#
# **No `backend` block, and the reason is the opposite of `infra/lakehouse`'s.** That layer has
# none because it applies nothing. This one has none because it *creates* the bucket and the key
# the others keep state in, and a layer cannot store its state in a bucket it has not made yet.
# Its state is **local**, on the machine that applied it, and `.gitignore` refuses it — a
# `terraform.tfstate` in a public repository is the largest single publication risk in this task,
# because it carries every id, arn and account number this file works so hard not to write down.
#
# **What that costs, stated rather than discovered.** Local state lives on one laptop and is not
# backed up. If it is lost, the resources below still exist and are simply unmanaged. That is
# recoverable — every one of them is importable, and their identifiers are published to SSM by
# `parameters.tf` precisely so that the account can be asked rather than the state file read —
# but it is recovery work, and it is the price of the chicken-and-egg rather than an oversight.
#
# **Locking is the S3 lock file, not DynamoDB.** `required_version >= 1.10` is what buys that:
# from 1.10 the S3 backend takes `use_lockfile = true` and keeps the lock beside the state, so
# the table AWS's own guides still describe is one resource this estate does not create, does not
# pay for and does not have to tear down. That constraint is in `versions.tf` for this reason and
# not for a language feature.

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project = "holdout"
      Layer   = "bootstrap"
      # **`Lifetime = permanent` is load-bearing rather than decorative.** `CLAUDE.md` names what
      # survives a teardown — the state bucket and its access-log bucket, the state KMS key, the
      # SSM parameters and the deploy role — and `infra/foundation`'s TTL reaper destroys what is
      # tagged and older than N hours. Everything in this layer is on the survivor list, so the
      # reaper must be able to tell it apart from an estate that is meant to die.
      Lifetime = "permanent"
    }
  }
}

# The account, read at apply time rather than written down. Used by the KMS key policy and by
# nothing else — `aws_iam_policy_document` needs the account principal spelled out, and this is
# the only way to spell it without publishing it.
data "aws_caller_identity" "current" {}
