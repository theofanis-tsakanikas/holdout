# `infra/pipelines/` — the data flow, as jobs

**Applied by `deploy`, from `main`.** Three jobs, one per hop of `CLAUDE.md`'s flow:

```
files on S3  ──▶  bronze   holdout — bulk load into bronze
bronze       ──▶  silver   holdout — bronze into silver
silver       ──▶  gold     holdout — silver into gold   (dbt, then the experiment tables)
```

**None of the logic is here.** `pipelines/ingest`, `pipelines/silver` and `pipelines/gold` are
Python packages with `__main__.py` entry points, proved local against the corpus on every push by
`make test`. This layer schedules them; it re-implements nothing.

## Three decisions

**`git_source`, not a wheel.** The alternative puts three steps between the code and the run — a
build, an upload and a version pin — and each can drift from the tree. The repository is public,
so no git credential is needed.

**Serverless, no cluster block anywhere.** `CLAUDE.md`: *serverless only, no always-on cluster
anywhere in the design.*

**No schedule on any job.** `backfill` dispatches them over eight months of history and `run`
drives the live day. A cron here would be a fourth thing that can start compute, and `CLAUDE.md`
names exactly three ways the estate does work.

## What is deliberately not here

**Zerobus endpoints.** `CLAUDE.md` lists them among this layer's contents and **the Terraform
provider has no resource for them** — measured against `databricks/databricks 1.130.0`, whose
resource list carries no Zerobus type at all. Zerobus is written to by a client rather than
declared as infrastructure: `pipelines/ingest/driver.py` is that client, and `run` is what points
it at the workspace.

**So this layer creates no Zerobus object, and the layer's row in `CLAUDE.md` overstates it by
one item.** That is recorded here rather than quietly dropped, because a directory that does not
create what its description claims is the defect this repository catalogues most.

**And the pin is a branch, not a commit.** `var.git_ref` defaults to `main`, so two runs a day
apart can execute different code while reporting the same configuration — the shape the readout
refuses at its own layer. The argument for it, and the plan to pin the dispatched sha in
`backfill` and `run`, is in `variables.tf` beside the variable.
