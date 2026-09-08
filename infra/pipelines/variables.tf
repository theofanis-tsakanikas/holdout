variable "region" {
  type        = string
  default     = "eu-west-1"
  description = "The AWS region the estate runs in. Asserted against what bootstrap applied."
}

variable "databricks_client_id" {
  type        = string
  sensitive   = true
  description = "Account service principal's client id. No default: half of a credential."
}

variable "databricks_client_secret" {
  type        = string
  sensitive   = true
  description = "Account service principal's OAuth secret. No default: it is a credential."
}

variable "repository_url" {
  type    = string
  default = "https://github.com/theofanis-tsakanikas/holdout"
  # **The jobs run this repository's code, from this repository.** Not a wheel built somewhere and
  # uploaded, not a notebook pasted into the workspace: `git_source` below points Databricks at
  # the tree, and every task names a path in it. `CLAUDE.md`'s rule is *nothing is invented*, and
  # a job whose code arrives by a route nobody can retrace is the same defect one layer over.
  description = "The repository the jobs run from. Public, so no git credential is needed."
}

variable "git_ref" {
  type    = string
  default = "main"
  # **A branch rather than a commit, and it is a declared weakness.**
  #
  # A job pinned to `main` runs whatever `main` says at the moment it starts, so two runs a day
  # apart can execute different code while reporting the same configuration. That is exactly the
  # shape `CLAUDE.md` refuses at readout — *the readout pins a Delta version, because without it
  # re-running last month's readout returns a different number*.
  #
  # It is a branch anyway because the alternative is worse today: pinning a commit means this
  # layer is re-applied on every merge to `main`, which puts an `apply` in the path of every
  # routine edit — the thing `pipelines` was split from `lakehouse` to avoid. **`backfill` and
  # `run` are what will pin it**, by passing the dispatched sha, so the pin lands where a number
  # is actually produced rather than where code is stored.
  description = "The ref the jobs run. `main` by default; backfill and run pin the sha."
}

variable "corpus_scale" {
  type    = string
  default = "scenario"
  # **The defaults in `pipelines/ingest/__main__.py` are `smoke` and `W1`, and relying on them is
  # worse than a crash.**
  #
  # The bulk-load job passed only `--out`. Every other argument has a default, so the job would
  # have run **green** — and loaded a smoke-sized corpus of the wrong world where `backfill` is
  # supposed to load eight months of history. A missing argument that stops the job is a red run;
  # a missing argument that is quietly filled in is eight months of history that is not eight
  # months of anything.
  #
  # `scenario` is `CLAUDE.md`'s corpus: about 100 stores across three fresh categories over eight
  # months. `harness` is 320 and belongs to claim 2, which runs local and costs nothing.
  description = "The corpus scale backfill loads. `scenario` is the estate's; `harness` is claim 2's."
}

variable "corpus_world" {
  type    = string
  default = "W6"
  # **W6 rather than W1**, and the choice is the experiment rather than a preference. `CLAUDE.md`:
  # *W6 — everything works, a real effect is present — **produce the number**. No refusal.* A
  # `run` driving W1 would produce a correct refusal and prove only half the claim; the other
  # experiment in that run is what supplies the refusal, from a design the engine rejects.
  description = "The world backfill loads and run drives. W6 is the one that must produce a number."
}

variable "corpus_seed" {
  type    = string
  default = "estate"
  # A named seed rather than the package's `t009` default: the assignment is drawn from a
  # committed seed and *which* seed is part of what a readout has to be able to state.
  description = "The committed seed. Which seed drew the assignment is part of the readout."
}

variable "git_commit" {
  type    = string
  default = ""
  # **A branch and a commit are different fields, and the first apply proved it.**
  #
  # `git_source` accepts `branch`, `tag` **or** `commit`, and `backfill` was passing the
  # dispatched sha as `git_ref` — which lands in `branch`. Databricks then looked for
  # `refs/heads/<sha>` and refused:
  #
  #     GIT_UNKNOWN_REF: Commit ref refs/heads/3bd3c423… not found
  #
  # **The field name was right and the value was the wrong kind for it**, which is a shape no
  # amount of reading the two files against each other would have caught: both were internally
  # consistent, and only the API knew that a forty-character hex string is not a branch.
  #
  # Empty means *use the branch*. `backfill` and `run` set it to the sha they dispatched, so the
  # pin lands where a number is produced — which is the whole argument `git_ref` makes above.
  description = "Pin the jobs to a commit. Empty: use git_ref as a branch instead."
}
