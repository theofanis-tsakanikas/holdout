# `infra/bootstrap/` — the layer that applies from a laptop, once, and is never applied again

**This is the first thing in this repository that spends money, and it spends almost none.** An
S3 bucket, a second bucket for its access logs, a KMS key, an OIDC provider, two IAM roles, four
SSM parameters and a budget. Together they are a few cents a month. **The money is in `T018` and
after it** — `CLAUDE.md` models a full cycle at 20–60 USD and the whole phase at 100–600.

**Nothing here has been applied.** No `terraform apply` has run, no account has been touched, and
what follows describes a configuration rather than an estate. `terraform validate` is what CI
runs, and the next section is about how little that proves.

## What `terraform validate` does not tell you, said first

`make terraform` runs `terraform init -backend=false && terraform validate` over every directory
under `infra/` that carries a `.tf` file. **Validate reads configuration. It does not talk to
AWS, and it agrees with almost anything.**

Measured on this layer, before it was written: `infra/lakehouse/dashboards.tf` declared a variable
whose description said it had *no default* two lines above a `default = ""`, and `validate`
passed. It passed with the default and it passes without it. **A whole class of defect in a
Terraform file is invisible to the only gate this repository has**, which is why
`tests/infra/test_variable_declarations.py` exists and why it landed before this directory did.

So the honest statement of what is proven here is: **the configuration parses, its references
resolve, and its provider is pinned.** Whether a bucket policy denies what it means to deny is
not knowable until somebody applies it, and that is `T017`'s stopping condition rather than this
file's claim.

## The chicken-and-egg, which is this layer's whole shape

Every other layer keeps its state in a bucket. **This layer creates that bucket**, so it cannot.
Its state is local, and `.gitignore` refuses `terraform.tfstate`, `*.tfplan` and `*.tfvars` —
planted and checked rather than assumed, because a state file in a public repository carries
every identifier the rest of this directory is written to keep out of the tree.

**What that costs.** Local state lives on one machine and is not backed up. Lose it and the
resources still exist, unmanaged. That is recoverable — they are all importable, and
`parameters.tf` publishes their identifiers into SSM precisely so the account can be asked rather
than the state file read — but it is work, and it is the price of the ordering rather than an
oversight.

**Locking is the S3 lock file, not a DynamoDB table.** Terraform 1.10 and newer put the lock
beside the state object; `versions.tf` requires `>= 1.10` for that reason and not for a language
feature. One resource fewer to create, pay for and tear down than every AWS guide still
describes.

## The four decisions worth arguing about

**0 · The OIDC provider is read, not created — and an apply is what said so.** An IAM OIDC
provider is unique per issuer URL **per account**, and this account has had one since 2026-07-04,
created by another project. The first apply of this layer failed with `EntityAlreadyExists`.
**A per-project layer declaring it as a `resource` claims to own an account-scoped object, and
the second project to apply is the one that finds out.** The resource is kept behind
`create_github_oidc_provider`, defaulting to reading, so the layer is still complete for an
account that has none — and what is read carries a postcondition asserting the audience, because
another project owns that list and a workflow would otherwise fail at `AssumeRoleWithWebIdentity`
with nothing here having noticed.

**1 · No thumbprint on the OIDC provider.** AWS validates GitHub's JWKS endpoint against its own
library of trusted CAs, so a thumbprint is not consulted — and the Terraform provider documents
that a thumbprint list, once declared, **keeps being used even after it is removed**. Declaring
none is reversible; declaring one is not. Both sources are quoted with their dates in `oidc.tf`.

**2 · The trust condition pins `ref:refs/heads/main`, not the repository.** `repo:owner/name:*`
also matches `repo:owner/name:pull_request`, and **this repository is public**: anybody may open
a pull request, and a workflow running on one receives an OIDC token with exactly that subject.
`ci.yml` never assumes this role; the four dispatch workflows run from `main`.

**And the coupling that comes with it, which is written in `oidc.tf` because the person who hits
it will be reading a stack trace rather than Terraform.** A job that declares an `environment:`
gets the subject `repo:OWNER/NAME:environment:NAME` — GitHub **replaces** the `ref:` form rather
than adding to it. **A protected environment with required reviewers is the ordinary way to make
a workflow wait for a human before it spends money**, and adding one without changing this
condition stops `deploy` assuming the role at all.

**3 · The deploy role can hold state and apply nothing.** The layers it will apply do not exist,
and a permission set written for undeclared resources is either `AdministratorAccess` — which
would leave the trust condition as the only thing between a public repository and this account —
or a guess wrong in both directions. **Each layer's task adds what that layer needs, reviewed
with that layer's resources on the page.**

**4 · The budget alerts do nothing and the 150 % action does.** *A budget that halts a run
mid-way costs more than it saves*: stopping the workflow at 80 % leaves everything it built
standing and billing, and removes the thing that would have torn it down. Enforcement is the TTL
reaper in `infra/foundation`. The action at 150 % covers the case the reaper cannot — the estate
unable to run it and nobody answering — and 1,500 USD against a modelled 100–600 for the whole
phase is a fire alarm rather than a thermostat.

## What survives a teardown

`CLAUDE.md`: *the state bucket and its access-log bucket, the state KMS key, the SSM parameters
and the deploy role.* **That list is this directory.**

**It is a policy, and `lifecycle { prevent_destroy = true }` on the two buckets and the key is
what makes it a mechanism.** Without it a `terraform destroy` here took all of it, and the only
things in the way were accidents: `force_destroy` unset, so a non-empty bucket refuses; and KMS
deletion being a scheduled window rather than an act. Removing one on purpose means editing that
block first, in a commit somebody reviews.

Everything here is also tagged `Lifetime = permanent`, which is not decoration: `infra/foundation`'s TTL reaper destroys what is
tagged and older than N hours, and it has to be able to tell the survivors apart from an estate
that is meant to die.

## Applying it, when the author decides to

```
cd infra/bootstrap
export GITHUB_TOKEN=$(gh auth token)   # publishes the deploy role's ARN; never stored
terraform init                         # no backend; state is local
terraform plan  -var budget_alert_email=<address> -out bootstrap.tfplan
terraform apply bootstrap.tfplan
```

**`GITHUB_TOKEN` is required and its absence fails at plan time**, which is the correct failure.
The layer creates the role a workflow assumes and **publishes its ARN into the repository's
secrets from inside the apply** — the ARN carries the account id, so it cannot be a literal in a
public workflow file, and setting it in a browser is a console action. An apply that skipped it
would report success for a bootstrap after which GitHub still cannot authenticate.

**`budget_alert_email` has no default and the plan stops without it** — which is the guard from
`tests/infra/test_variable_declarations.py` doing what a description says it does, rather than
saying it.

The outputs include a `backend_block` to paste into the next layer. Nothing else in this
repository needs them: a workflow reads SSM.

## The one thing to check after applying, and why it is a step rather than a gate

**Server access logging can stop silently, and three passes over twenty lines were needed to
find that it would have.** The delivery model is now one rather than two: `BucketOwnerEnforced`
on the logs bucket, and a bucket policy granting `s3:PutObject` to `logging.s3.amazonaws.com`
with the two source conditions AWS's own example carries. **That grant was missing entirely** —
neither `aws_s3_bucket` nor `aws_s3_bucket_logging` writes one, the console does it and Terraform
does not — so delivery would have failed whatever the rest of the policy said, and two of the
three passes argued about a `Deny` on a write nothing had permitted.

**What remains unverified is the deny's exception**, not the grant. The bucket denies plain-HTTP
requests and excepts the logging service principal, and whether that condition matches a delivery
request is not knowable without an account. The failure produces no error, no red gate and an
empty prefix nobody looks at until they need it.

So, once state has been written a few times by the next layer:

```
aws s3 ls s3://$(terraform output -raw state_bucket | sed 's/tfstate/tfstate-logs/')/tfstate/
```

**Empty after a day of activity means the exception did not work**, and the fix is to drop the
`Deny` statement — **not the whole policy**, which now carries the grant delivery depends on. The
protection is worth less than the record it would be suppressing; the grant is not.

**This is a step and not a gate deliberately.** Nothing in this repository can assert it: the
assertion needs an account, and `make terraform` runs `validate`, which does not talk to AWS.
`docs/DAY-ONE.md` settled the shape for a check that cannot exist before the thing it checks —
**the design is recorded now, the assertion runs at the earliest moment it can exist.**
