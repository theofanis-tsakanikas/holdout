# The budget posture, in `CLAUDE.md`'s own words: **1,000 USD, alerts at 50/80/100 % and no stop
# action; a stop action only at 150 %.**
#
# **Why the alerts do nothing.** *A budget that halts a run mid-way costs more than it saves* —
# `deploy`, `backfill` and `run` leave an estate standing whatever interrupts them, and an estate
# standing is an estate billing. A budget that stops the workflow at 80 % leaves everything it
# built running and removes the thing that would have torn it down. **Enforcement is the TTL
# reaper in `infra/foundation`, not this file**; what this file does is tell somebody.
#
# **And why there is one at 150 % anyway.** The reaper is a scheduled job inside the estate, so
# the failure it cannot cover is the estate being unable to run it — the case where spend keeps
# climbing and nothing in the account is answering. 150 % of a 1,000 USD budget is 1,500 USD
# against a modelled 100–600 for the whole phase, so the action fires only in a world where the
# model is wrong by more than a factor of two. **That is a fire alarm, not a thermostat.**

# **Activating the tag key, and without it the filter below matches nothing.**
#
# A `TagKeyValue` cost filter names a key AWS has been told to allocate costs by. Until that key
# is `Active`, the filter matches no resource that has ever existed, **the budget reports zero for
# ever, and the ceiling is a resource that exists and cannot fire** — `watermark` carries that
# sentence and learned it against a real account. The console is the usual place this is done,
# which is why it is usually forgotten and never noticed: **a budget at zero looks exactly like a
# project that is not spending.**
#
# **AWS lists a key here only once it has seen it on a billed resource**, which can take up to
# 24 hours after the first tagged thing is created. This layer's tag keys were namespaced on
# 2026-09-05, so `holdout:project` is new to the account and this resource may fail on the first
# apply after that. **The fix is to apply again the next day, never to reach for the console.**
resource "aws_ce_cost_allocation_tag" "project" {
  tag_key = "holdout:project"
  status  = "Active"
}

resource "aws_budgets_budget" "estate" {
  # `<project>-estate`, as every sibling names it. It was `holdout` for one hour.
  name         = "holdout-estate"
  budget_type  = "COST"
  limit_amount = var.budget_limit_usd
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  # **Only what this project tagged, and the first version of this file had no filter at all.**
  #
  # Measured an hour after the first apply, with holdout having spent nothing: **actual 0.638
  # USD, forecast 35.35 USD, `CostFilters: null`.** Every cent of that is another project in the
  # same account. `watermark`'s own comment states the consequence and it is sharper here than
  # there, because this is the only budget in the account carrying an **automatic** action: *a
  # ceiling that counts somebody else's spend disables this project's deploy role for a bill it
  # did not run up.*
  #
  # **And the window this opens is declared rather than discovered.** Between this applying and
  # AWS backfilling cost data for the newly activated key, the budget reads **zero** — which is
  # the failure mode two paragraphs up. It is harmless here and only because of a fact that is
  # true today and will not be true after `T018`: **nothing in this project is running.** The
  # first thing that spends is the estate, and the tag will have been active for days by then.
  cost_filter {
    name   = "TagKeyValue"
    values = ["user:holdout:project$holdout"]
  }

  depends_on = [aws_ce_cost_allocation_tag.project]

  # Actual spend, not forecast, at all three. A forecast alert on a workload that runs in bursts
  # of a few hours fires on the burst and says nothing about the month — and the number the
  # author needs to see is the one an invoice will agree with.
  dynamic "notification" {
    for_each = [50, 80, 100]
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "PERCENTAGE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = [var.budget_alert_email]
    }
  }
}

# The policy the action attaches. Deny everything: the point is that nothing further can be
# applied or started, not that some particular service stops.
data "aws_iam_policy_document" "halt" {
  statement {
    sid       = "DenyEverything"
    effect    = "Deny"
    actions   = ["*"]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "halt" {
  name        = "holdout-halt"
  description = "Attached to the deploy role by the 150% budget action. Detached by hand, on purpose."
  policy      = data.aws_iam_policy_document.halt.json
}

data "aws_iam_policy_document" "budget_action_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["budgets.amazonaws.com"]
    }
    # Without this, any AWS account whose budget names this role's arn could ask Budgets to
    # assume it. The confused-deputy condition is not optional on a service principal.
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_iam_role" "budget_action" {
  name               = "holdout-budget-action"
  description        = "Assumed by AWS Budgets to attach the halt policy at 150%."
  assume_role_policy = data.aws_iam_policy_document.budget_action_trust.json
}

data "aws_iam_policy_document" "budget_action" {
  statement {
    effect    = "Allow"
    actions   = ["iam:AttachRolePolicy", "iam:DetachRolePolicy"]
    resources = [aws_iam_role.deploy.arn]
    # It may attach exactly one policy, to exactly one role. A budget action whose execution role
    # can attach anything is a second path to administrator that nobody would think to look for.
    condition {
      test     = "ArnEquals"
      variable = "iam:PolicyARN"
      values   = [aws_iam_policy.halt.arn]
    }
  }
}

resource "aws_iam_role_policy" "budget_action" {
  name   = "attach-the-halt-policy"
  role   = aws_iam_role.budget_action.id
  policy = data.aws_iam_policy_document.budget_action.json
}

resource "aws_budgets_budget_action" "halt" {
  budget_name = aws_budgets_budget.estate.name
  action_type = "APPLY_IAM_POLICY"
  # **Automatic, and it is the one place in this repository where something acts without a human.**
  # An approval model that waits for somebody is a fire alarm that waits for somebody, and the
  # case this covers is precisely the one where nobody is answering.
  approval_model     = "AUTOMATIC"
  notification_type  = "ACTUAL"
  execution_role_arn = aws_iam_role.budget_action.arn

  action_threshold {
    action_threshold_type  = "PERCENTAGE"
    action_threshold_value = 150
  }

  definition {
    iam_action_definition {
      policy_arn = aws_iam_policy.halt.arn
      roles      = [aws_iam_role.deploy.name]
    }
  }

  subscriber {
    address           = var.budget_alert_email
    subscription_type = "EMAIL"
  }
}
