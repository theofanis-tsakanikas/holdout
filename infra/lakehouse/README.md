# `infra/lakehouse/` — catalogs, external locations, the warehouse, Lakebase, the dashboards

**Applied by `deploy`, from `main`.** It reads what `infra/foundation` published to SSM and
governs it: one storage credential and one external location per zone, a catalog whose schemas
are the medallion, the grants, the serverless SQL warehouse the dashboards run on, and Lakebase.

> **This file opened with *the first Terraform layer, and it applies nothing* until 2026-09-06.**
> It read: *there is no `terraform apply` anywhere in this repository, no provider credential, no
> backend, no resource that exists, and nothing that costs a cent* — every clause of which was
> true when `T013` wrote it and none of which is true now. `T020` is this branch.
>
> **It is the fourth time in two days that an introduction survived the change beneath it** —
> after `deploy.yml`'s header, `oidc.tf`'s header and `TASKS.md`'s row for `T018`. The shape is
> recorded in `docs/FINDINGS.md` and it is the same every time: **a fix lands where the finding
> pointed, findings point at statements, and no statement's diff touches the paragraph that
> introduces it.** The prior wording stays per doctrine rule 4.

## What it costs

**Lakebase is the only thing here that bills at rest**, and it is why this layer is in `destroy`'s
reverse order rather than left standing between cycles. The warehouse bills per second of query
and stops after ten idle minutes; the catalog, the schemas, the credentials and the locations are
metadata and bill nothing.

## Why the dashboards land in this layer rather than beside the code that compiles them

`T020`'s branch is `infra/lakehouse`, it `depends_on T013`, and its `closes` names *"the two AI/BI
dashboards (T013) applied"*. So the resources are placed where the layer that applies them will
find them. That is a reading of the task graph, not a preference.

## What the resources actually contain, and what checks it

`serialized_dashboard` reads a **generated** file. Neither the SQL nor the check names nor the
guardrail list is written here: `holdout.contracts.compilers.dashboard` compiles both screens from
`contracts/`, the readout dataset **is** `compile_readout(metric)` — the same call
`generated/readout/` is written from — and `make contracts` byte-compares what lands on disk.

**That arrangement exists because `terraform validate` cannot check any of it.**
`serialized_dashboard` is a string, so a dashboard containing

    select nonsense from table_that_does_not_exist where 1=

validates clean. Measured against the real provider before this layer was written, and it is the
reason `T013`'s stopping condition needed a second gate: *a declared stopping condition that does
not test the declared closing condition* is the shape this repository keeps finding.

## The provider, pinned and locked

`.terraform.lock.hcl` is committed with the hashes for **every platform CI or a laptop might run
on**, so `terraform init` verifies rather than resolves. Two reasons, and the second is the one
that matters: a floating provider makes `terraform validate` a moving target, and **`gate` is a
required context** — the check everything else depends on. A registry fetch inside it means the
one job with the least tolerance for a new failure mode acquires one.

**What pinning does not remove is the fetch itself.** `terraform init` still downloads the
provider unless `TF_PLUGIN_CACHE_DIR` is populated, so CI caches that directory keyed on the lock
file. **If that cache misses, `gate` depends on the Terraform registry being reachable** — stated
here rather than absorbed, because it is a sentence somebody needs to be able to find when it
fires at three in the morning.

Measured on `darwin_arm64`, provider `databricks/databricks` **1.130.0**: **67 MB installed**,
`terraform init` **2.2s** cold. The Linux figure is whatever CI's own log says.
