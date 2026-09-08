# `infra/foundation` — the estate everything above stands on

**Applied by `deploy`, from `main`, never from a laptop.** `CLAUDE.md`: *bootstrap is local,
everything else is CI. A layer that can be applied from a laptop drifts.*

## What it holds

| | |
|---|---|
| the data KMS key | encrypts the four zones; **not** the state key, and the difference is lifetime |
| four S3 zones | `landing · bronze · silver · gold` |
| the workspace | on a **Databricks-managed** network, plus its cross-account role and root bucket |
| the metastore | created **or** read, behind `owns_metastore`, then attached to the workspace |
| the TTL reaper | a Lambda on an hourly schedule — level 1 of the three teardown guarantees |

**There is no VPC and that is a decision with a date.** `CLAUDE.md`'s row for this layer said
`VPC` until 2026-09-06; the restatement beside it carries the argument and the measurement.
Serverless compute runs in Databricks' account, `network_id` is optional on
`databricks_mws_workspaces`, and the egress a customer-managed VPC needs is a NAT gateway billed
by the hour in a project whose cost posture opens by refusing always-on anything.

## The first apply, in order

**1 · `infra/bootstrap` is re-applied locally first.** It is where this layer's permissions live:
`aws_iam_role_policy.deploy_estate` is what makes the deploy role able to build any of the above,
and it did not exist until `T018`. **Skip this and the failure is `AccessDenied` mid-apply**,
after some resources exist and some do not.

**2 · `owns_metastore` is `true` for the first apply and never again.** Measured on 2026-09-05,
this account holds no metastore in any region. Flipping it back to `false` afterwards **plans a
destroy of the metastore and everything in it** — `metastore.tf` says so at length, and
`infra/bootstrap/README.md`'s instruction applies: read the plan for `destroy` lines.

**3 · The backend is configured at `init`, not in the file.** The state bucket's name is derived
from the account id and this repository is public, so:

    terraform -chdir=infra/foundation init \
      -backend-config="bucket=$(aws ssm get-parameter --name /holdout/bootstrap/state_bucket --query Parameter.Value --output text)" \
      -backend-config="key=foundation/terraform.tfstate" \
      -backend-config="region=$(aws ssm get-parameter --name /holdout/bootstrap/region --query Parameter.Value --output text)" \
      -backend-config="kms_key_id=$(aws ssm get-parameter --name /holdout/bootstrap/state_kms_key_arn --query Parameter.Value --output text)"

**4 · Three variables have no default and are credentials.** `databricks_account_id`,
`databricks_client_id`, `databricks_client_secret`. `terraform validate` never needs them;
`terraform plan` stops without them, which is the behaviour that makes their absence a protection.

## What it publishes

Everything under `/holdout/foundation/`, as one map in `outputs.tf` rather than as a list beside a
list. **Publishing is not a courtesy to the layers above**: `reaper/reap.py`'s second enumeration
is exactly this set, so a resource whose name never reaches SSM is one the reaper can report as
uncollectable and can never collect.

## What is written and has not run

**The metastore's read branch.** The account has no metastore, so the first apply takes the create
branch and the other one has never executed against a real account. It validates. That is a
different claim from *it works*, and this file says which one is being made.

**The reaper's deletions.** `collect_billing_surfaces` has never been pointed at a live workspace.
Its `DRY_RUN` environment variable exists for the first run after the first `deploy`, and the
honest sequence is one dry run read in the log before it is trusted with `false`.
