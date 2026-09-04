# `infra/lakehouse/` — the first Terraform layer, and it applies nothing

**This directory is not phase 3, and the sentence is here because *the first Terraform layer*
sounds like the estate.** There is no `terraform apply` anywhere in this repository, no provider
credential, no backend, no resource that exists, and nothing that costs a cent. What `T013`
delivers is **definitions and `terraform validate`**; applying them is `T020`'s, which is phase 3
and which `T013`'s own `out_of_scope` names.

`terraform init -backend=false` is what runs here. The backend is deliberately absent rather than
declared and unused: a backend block with no state to keep would be a configuration that reads as
though somebody had chosen where state lives, and nobody has.

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
