# The state backend every other layer uses: one KMS key, one bucket for state, one bucket for
# that bucket's access logs. All three are on `CLAUDE.md`'s survivor list.

# **A bucket name is globally unique across every AWS account**, so it cannot be a fixed string
# in a public repository without either colliding or telling the world what to look for. The
# suffix comes from the account id, hashed — so the name is stable for this account, different
# for any other, and does not carry the account id itself.
locals {
  account_suffix = substr(sha256(data.aws_caller_identity.current.account_id), 0, 12)
  state_bucket   = "holdout-tfstate-${local.account_suffix}"
  logs_bucket    = "holdout-tfstate-logs-${local.account_suffix}"
}

resource "aws_kms_key" "state" {
  description = "holdout — Terraform state at rest"
  # Rotation is annual and automatic. A key that survives every teardown is a key that outlives
  # the reasons anybody remembers for it, which is exactly the case rotation exists for.
  enable_key_rotation     = true
  deletion_window_in_days = 30

  # On the survivor list too, for the same reason as the two buckets above. A key destroyed
  # while the state it encrypts still exists leaves that state unreadable, which is worse than
  # losing the key alone.
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_kms_alias" "state" {
  name          = "alias/holdout-tfstate"
  target_key_id = aws_kms_key.state.key_id
}

resource "aws_s3_bucket" "logs" {
  bucket = local.logs_bucket

  # **`CLAUDE.md`'s survivor list is a policy and this is what makes it a mechanism.** *What
  # survives a teardown: the state bucket and its access-log bucket, the state KMS key, the SSM
  # parameters and the deploy role.* Nothing enforced that: a `terraform destroy` in this
  # directory took all of it, and the only things standing in the way were accidents —
  # `force_destroy` unset, so a non-empty bucket refuses; and KMS deletion being a scheduled
  # window rather than an act. **Neither is the guarantee the sentence claims.**
  #
  # Removing one of these on purpose means editing this block first, in a commit somebody
  # reviews. That is the point rather than the friction.
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket" "state" {
  bucket = local.state_bucket

  # **`CLAUDE.md`'s survivor list is a policy and this is what makes it a mechanism.** *What
  # survives a teardown: the state bucket and its access-log bucket, the state KMS key, the SSM
  # parameters and the deploy role.* Nothing enforced that: a `terraform destroy` in this
  # directory took all of it, and the only things standing in the way were accidents —
  # `force_destroy` unset, so a non-empty bucket refuses; and KMS deletion being a scheduled
  # window rather than an act. **Neither is the guarantee the sentence claims.**
  #
  # Removing one of these on purpose means editing this block first, in a commit somebody
  # reviews. That is the point rather than the friction.
  lifecycle {
    prevent_destroy = true
  }
}

# **Versioning on the state bucket is not a nicety.** A corrupted or truncated state written over
# a good one is unrecoverable without it, and the object being overwritten is the only record of
# what this estate consists of.
resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.state.arn
    }
    # Without this, every object read is a separate KMS call. It is a cost and latency setting
    # and it is here because state is read on every apply of every layer.
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  rule {
    apply_server_side_encryption_by_default {
      # **`AES256` rather than the KMS key, and it is not an inconsistency.** AWS states it
      # outright, read 2026-09-05 on the page cited below: *"Granting `s3:PutObject` to the
      # logging service principal is not sufficient if the destination bucket uses SSE-KMS
      # default encryption. The destination bucket must use Amazon S3 managed keys (SSE-S3)."*
      # So this is a requirement rather than a preference, and the failure it prevents is the
      # silent one — log objects delivered under a key nobody can read.
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket                  = aws_s3_bucket.logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# **`BucketOwnerEnforced` here too, and the sentence this replaces was wrong.**
#
# It read *"the log bucket keeps ACLs enabled on purpose: S3 log delivery writes with an ACL, and
# `BucketOwnerEnforced` would refuse it"* — which describes the **legacy** delivery path, the S3
# Log Delivery *group* as an ACL grantee. AWS's own documentation, read 2026-09-05
# (https://docs.aws.amazon.com/AmazonS3/latest/userguide/enable-server-access-logging.html):
# *"For access log delivery, you must grant the logging service principal
# (`logging.s3.amazonaws.com`) access to your destination bucket … we recommend that you use a
# bucket policy instead of ACLs"*, and with the bucket-owner-enforced setting *"you must update
# the bucket policy for the destination bucket to grant access to the logging service principal."*
#
# **The file was carrying both models at once and at most one can be operative.** The ACL
# accommodation above and the `logging.s3.amazonaws.com` exception in the policy below were two
# answers to the same question, written two passes apart, and reading either one alone made the
# other invisible. One model now: the service principal, granted by policy.
resource "aws_s3_bucket_ownership_controls" "logs" {
  bucket = aws_s3_bucket.logs.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_logging" "state" {
  bucket        = aws_s3_bucket.state.id
  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "tfstate/"

  # **Nothing else creates an edge to the grant, and `PutBucketLogging` is validated against the
  # destination's permissions** — `InvalidTargetBucketForLogging` is the documented refusal. This
  # resource references the two buckets and the policy references the two buckets, so Terraform
  # is free to order them either way and would be right to.
  #
  # **The failure this prevents is loud rather than silent, which is why it survived four passes
  # over this file**: an apply that errors is not an apply that quietly logs nothing, and a second
  # apply would succeed because the policy would exist by then. It costs one confusing error on a
  # first apply, and one line to not have it. Everything else in these twenty lines was hunting
  # silence, and this is the one thing here that shouts.
  depends_on = [aws_s3_bucket_policy.logs]
}

# Old state versions are kept for a quarter and then expire. Long enough that a mistake found a
# month later is still recoverable; short enough that the bucket is not an unbounded archive of
# every identifier this estate has ever had.
resource "aws_s3_bucket_lifecycle_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    id     = "expire-noncurrent-state"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration {
      noncurrent_days = 90
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# **The logs bucket is versioned too, as `manifest` and `watermark` version theirs.** It records
# who touched the state bucket; an object overwritten in it is a record of an access, and the one
# access worth overwriting is the one somebody wanted gone.
resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "expire-logs"
    status = "Enabled"
    filter {}
    expiration {
      days = 90
    }
  }
}

# **Every request to the state bucket must be encrypted in transit, and the bucket says so
# itself rather than trusting each caller.** A bucket policy is the only place this can be
# asserted once for every principal that will ever read it.
data "aws_iam_policy_document" "state_tls_only" {
  statement {
    sid       = "DenyUnencryptedTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.state.arn, "${aws_s3_bucket.state.arn}/*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "state" {
  bucket = aws_s3_bucket.state.id
  policy = data.aws_iam_policy_document.state_tls_only.json
}

# **The same denial on the logs bucket — and it carries an exception the state bucket does not
# need, because the writer here is not a caller anybody controls.**
#
# Its absence was the only state/logs difference in this file with no argument beside it. The
# other two are deliberate and say so: `AES256` because log delivery cannot use a
# customer-managed key, and `BucketOwnerPreferred` because delivery writes with an ACL. In a file
# where every difference carries its reason, an unexplained one reads as deliberate.
#
# **But a blanket `Deny s3:*` on a log *destination* is a documented way to make delivery stop
# silently**, and the AWS troubleshooting page for undelivered server access logs names this
# exact pattern — read 2026-09-05,
# https://docs.aws.amazon.com/AmazonS3/latest/userguide/troubleshooting-server-access-logging.html:
# check the destination bucket's policy for `Deny` statements and verify they do not prevent
# S3 from writing the logs. **A `Deny` cannot be allowed around** — it wins over every `Allow` —
# so the only way to keep the protection and the delivery is to except the one principal that
# performs it.
#
# **This is unverified and stays unverified until somebody applies it.** No account exists to
# test against, and the failure mode is silence: no error, no red gate, an empty prefix nobody
# looks at until they need it. **So the README's apply procedure ends with looking at the
# prefix** — the assertion runs at the earliest moment it can exist, which is the shape
# `docs/DAY-ONE.md` settled on for the path it could not verify in advance.
data "aws_iam_policy_document" "logs_tls_only" {
  # **The grant, which was absent altogether — and its absence would have stopped delivery
  # whatever the deny said.** With ACLs disabled, a bucket policy is the only way to permit the
  # logging service principal to write, and neither `aws_s3_bucket` nor `aws_s3_bucket_logging`
  # creates one: the console does it, and Terraform does not. **So the bucket had no ACL grant
  # and no policy grant, and two passes over these twenty lines argued about a `Deny` on a write
  # that was never permitted in the first place.**
  #
  # Shaped after AWS's own example on the page cited above: the two source conditions are what
  # stop any other account naming this bucket as its log destination.
  statement {
    sid       = "S3ServerAccessLogsPolicy"
    effect    = "Allow"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.logs.arn}/tfstate/*"]

    principals {
      type        = "Service"
      identifiers = ["logging.s3.amazonaws.com"]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = [aws_s3_bucket.state.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }

  statement {
    sid       = "DenyUnencryptedTransportExceptLogDelivery"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.logs.arn, "${aws_s3_bucket.logs.arn}/*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }

    # The exception, and it is as narrow as a condition can make it: **one service principal,
    # and only when the request is S3's own log delivery.** Every other caller — every role,
    # every user, every other service — is still denied over plain HTTP.
    condition {
      test     = "StringNotEquals"
      variable = "aws:PrincipalServiceName"
      values   = ["logging.s3.amazonaws.com"]
    }
  }
}

resource "aws_s3_bucket_policy" "logs" {
  bucket = aws_s3_bucket.logs.id
  policy = data.aws_iam_policy_document.logs_tls_only.json
}
