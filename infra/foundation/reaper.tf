# **Level 1 of the three teardown guarantees, and the only one that depends on no workflow.**
#
# `CLAUDE.md` is explicit that a workflow step is a convenience: the runner can die, the network
# can drop, the job can be cancelled. This is a schedule in the account. What it does and what it
# deliberately does not touch is argued in `reaper/reap.py`'s docstring rather than here, because
# the decision belongs beside the code that acts on it.

data "archive_file" "reaper" {
  type        = "zip"
  source_dir  = "${path.module}/reaper"
  output_path = "${path.module}/.reaper.zip"
}

# ---------------------------------------------------------------- what the reaper may do
#
# **Read everywhere, delete nothing in AWS.** The reaper's deletions are all Databricks-side; in
# this account it only ever looks. That is not a narrowing of an intent — it is the intent, and
# writing the policy this way is what makes it checkable: a future change that gave the reaper
# `s3:DeleteObject` would be visible as a permission diff rather than as a behavioural one.
data "aws_iam_policy_document" "reaper_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "reaper" {
  statement {
    sid    = "EnumerateByTag"
    effect = "Allow"
    # The tagging API is account-wide and takes no resource ARN — `tag:GetResources` cannot be
    # scoped, which is why the reaper's *acting* population is filtered in code by the project tag
    # rather than by IAM. Stated here so the breadth is a known one.
    actions   = ["tag:GetResources"]
    resources = ["*"]
  }

  statement {
    sid       = "EnumerateByPublication"
    effect    = "Allow"
    actions   = ["ssm:DescribeParameters"]
    resources = ["*"]
  }

  statement {
    sid       = "ReadItsOwnCredentials"
    effect    = "Allow"
    actions   = ["ssm:GetParameters", "ssm:GetParameter"]
    resources = ["arn:${data.aws_partition.current.partition}:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter/holdout/foundation/reaper_*"]
  }

  statement {
    sid       = "DecryptThoseCredentials"
    effect    = "Allow"
    actions   = ["kms:Decrypt"]
    resources = [aws_kms_key.data.arn]
  }

  statement {
    sid    = "MeasureTheEstatesAge"
    effect = "Allow"
    # `s3:ListAllMyBuckets` is how a creation date is read, and it too takes no resource. The
    # reaper learns that buckets exist and when; it cannot read an object in any of them.
    actions   = ["s3:ListAllMyBuckets"]
    resources = ["*"]
  }

  statement {
    sid    = "ReportItsOwnFailure"
    effect = "Allow"
    # Lambda publishes to the dead-letter topic **as the function's role**, so without this the
    # raise in `reap.py` produces a failed invocation that reaches nobody -- which is the state
    # the raise was added to end.
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.reaper_failures.arn]
  }

  statement {
    sid    = "EncryptThatReport"
    effect = "Allow"
    # The topic is KMS-encrypted with the estate's data key, and publishing to an encrypted topic
    # needs a data key from it. `kms:Decrypt` is already granted above for the reaper's own
    # credentials; this is the other direction.
    actions   = ["kms:GenerateDataKey"]
    resources = [aws_kms_key.data.arn]
  }

  statement {
    sid    = "WriteItsOwnLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:${data.aws_partition.current.partition}:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/holdout-reaper:*"]
  }
}

resource "aws_iam_role" "reaper" {
  name               = "holdout-reaper"
  assume_role_policy = data.aws_iam_policy_document.reaper_trust.json
}

resource "aws_iam_role_policy" "reaper" {
  name   = "holdout-reaper"
  role   = aws_iam_role.reaper.id
  policy = data.aws_iam_policy_document.reaper.json
}

# ---------------------------------------------------------------- the credentials it reads
#
# **`SecureString`, and read at run time rather than carried in the function's environment.** A
# Lambda environment variable is stored in the function's configuration in plaintext and is
# readable by anything holding `lambda:GetFunction`, which is a wider set than this role.
#
# They are the *account* service principal's credentials, the same pair the provider uses. A
# dedicated reaper principal with a narrower scope is the better shape and is not taken here: it
# is an account-level Databricks object with its own lifecycle, and creating one from the layer
# that will be reaped by it is a circularity worth thinking about rather than typing.
resource "aws_ssm_parameter" "reaper_client_id" {
  name   = "/holdout/foundation/reaper_client_id"
  type   = "SecureString"
  key_id = aws_kms_key.data.arn
  value  = var.databricks_client_id
}

resource "aws_ssm_parameter" "reaper_client_secret" {
  name   = "/holdout/foundation/reaper_client_secret"
  type   = "SecureString"
  key_id = aws_kms_key.data.arn
  value  = var.databricks_client_secret
}

# ---------------------------------------------------------------- the function
resource "aws_lambda_function" "reaper" {
  function_name    = "holdout-reaper"
  role             = aws_iam_role.reaper.arn
  handler          = "reap.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.reaper.output_path
  source_code_hash = data.archive_file.reaper.output_base64sha256

  # 60 seconds. The reaper makes a handful of list calls and at most a few deletes; a function
  # that has not finished in a minute has hit something it does not understand, and the right
  # outcome then is a timeout in the log rather than a long silent run.
  timeout = 60

  environment {
    variables = {
      TTL_HOURS             = tostring(var.ttl_hours)
      LANDING_BUCKET        = aws_s3_bucket.zone["landing"].bucket
      DATABRICKS_HOST       = databricks_mws_workspaces.this.workspace_url
      DATABRICKS_ACCOUNT_ID = var.databricks_account_id
      DRY_RUN               = tostring(var.reaper_dry_run)
    }
  }

  # **The dead-letter topic is what makes a failed run visible**, and it is the half of this
  # pattern that was copied from `watermark` without its loud end. `reap.py` raises after the
  # sweep; without a destination for that failure the Lambda would simply be marked failed in a
  # console nobody opens, and *a reaper that silently fails to delete is indistinguishable from
  # one that had nothing to do.*
  dead_letter_config {
    target_arn = aws_sns_topic.reaper_failures.arn
  }

  depends_on = [aws_iam_role_policy.reaper]
}

# **A topic rather than an alarm, and no subscription declared here.**
#
# A subscription carries an email address, which is personal data and has no default anywhere in
# this repository -- `infra/bootstrap/variables.tf` makes the same argument about
# `budget_alert_email`. The topic is the durable half and it is what the function's failures land
# on; who hears about them is a decision with a person in it.
#
# **It is deliberately not the budget's topic.** The budget says *the model was wrong*; this says
# *the net did not hold*, and `CLAUDE.md` ranks them as different levels of the same guarantee.
resource "aws_sns_topic" "reaper_failures" {
  name              = "holdout-reaper-failures"
  kms_master_key_id = aws_kms_key.data.id
}

# **And a subscription, since 2026-09-13, because a topic nobody hears is a log line.** The
# paragraph above was right that the address is personal data with no default here; what it did
# not do was read the address from where it already lives. `bootstrap` publishes it encrypted
# under the state key, and this layer subscribes to its own failures the way it reads every other
# published value. Email subscriptions are confirmed by the recipient once; until then the
# subscription is pending and the topic is, as before, unheard -- the confirmation is in
# `docs/DAY-ONE.md`.
data "aws_ssm_parameter" "alert_email" {
  name            = "/holdout/bootstrap/alert_email"
  with_decryption = true
}

resource "aws_sns_topic_subscription" "reaper_failures" {
  topic_arn = aws_sns_topic.reaper_failures.arn
  protocol  = "email"
  endpoint  = data.aws_ssm_parameter.alert_email.value
}

# ---------------------------------------------------------------- the schedule
#
# **Hourly, against a TTL measured in tens of hours.** The interval is not the TTL: it is how long
# an over-age estate can stand before somebody notices, and an hour is a rounding error against a
# 48-hour life. Running more often would cost nothing and prove nothing; running daily would make
# the effective TTL `ttl_hours + 24`, which is a different number from the one declared.
resource "aws_cloudwatch_event_rule" "reaper" {
  name                = "holdout-reaper"
  description         = "Hourly TTL check over the holdout estate"
  schedule_expression = "rate(1 hour)"
}

resource "aws_cloudwatch_event_target" "reaper" {
  rule = aws_cloudwatch_event_rule.reaper.name
  arn  = aws_lambda_function.reaper.arn
}

resource "aws_lambda_permission" "reaper" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.reaper.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.reaper.arn
}

# The log group, declared rather than left to be created implicitly on first invocation.
#
# **An implicitly created log group has no retention and keeps everything for ever**, which is a
# small permanent cost and, more to the point, an object no layer owns: `destroy` would leave it
# behind and the next `deploy` would adopt it silently.
resource "aws_cloudwatch_log_group" "reaper" {
  name              = "/aws/lambda/${aws_lambda_function.reaper.function_name}"
  retention_in_days = 14
}
