# Day one — the manual work with no API

**Nothing in this file has been verified.** There is no AWS account, no Databricks workspace and
no database to verify anything against. Phase 3 has not been authorised and nothing here has been
attempted.

So this is **a checklist to be run before phase 3 begins — not a record of a verification that
happened.** That distinction is the first thing in the file because a document of this shape is
read as evidence, and reading it as evidence is exactly how a paid run discovers on the day what
somebody believed had already been checked.

**Every external fact below carries the URL it came from and the date that URL was read.** Anything
that could not be established is in [Not verified](#not-verified), by name, with what was looked
for. That discipline is copied deliberately from `docs/REGULATORY.md`, and for the same reason: a
document about somebody else's product survives that product changing only if a reader can tell
which sentence was read where and when.

---

## SUPERSEDED 2026-09-02, IN SIX OF ITS SEVEN SECTIONS — read this before anything below it

**The author ruled that the ERP's master data arrives as files on S3, dropped several times
during `run`, rather than through Lakeflow Connect.** The connector is not used, so **§1, §3, §4,
§5, §6 and §7 describe work that will not be done**: the Public Preview enrolment, the
`rds.logical_replication` parameter and its reboot, the in-database SQL, the Unity Catalog
connection, the workspace-to-RDS network path, and the replication slot that outlives the
pipeline. There is no RDS: `T019` closed *not built* on the same ruling.

**They are kept rather than deleted**, per doctrine rule 4 — a correction never erases what was
previously stated. What each of them cost to establish is the argument for the ruling, and a
reader who wants to know why the estate does not use a managed connector will find the answer in
the six sections describing what using one would have required.

**§2 survives, and it survives untouched.** Its subject is the region, and its own text gives the
reason: *the binding constraint is Zerobus rather than the connector*, whose availability list was
the wider of the two. Removing the connector removes nothing from that intersection. **It is the
only section here that was never about the connector**, which is why it is the only one left.

> **Six of seven, not five.** `#43`'s finding said *five of its seven sections stop applying* —
> counted against the document it is six, and the miscount is recorded in `docs/FINDINGS.md`
> rather than silently corrected.

**What replaces them is not yet written.** The S3 bulk-load path has its own day-one work — a
bucket, a drop schedule, whatever `backfill` needs to read files it did not write — and none of it
has been established. It arrives with `pipelines/ingest-bulk-load`, and until then this document
is honest about describing a path the estate no longer takes.

---

## Why this file cannot be a record of verification, and what replaces it

`CLAUDE.md` requires one verification to happen before phase 3:

> **The network path from the workspace to RDS that Lakeflow Connect's database connectors need is
> verified before phase 3, not inside it** — see `docs/DAY-ONE.md`.

**That instruction is unachievable as written, by anybody, funded or not.** The workspace is created
by `infra/foundation` (T018) and the RDS by `infra/sources` (T019), and **both layers are phase 3.**
There is no workspace and no database for a path to exist between until phase 3 has started. The
sentence asks for a measurement between two endpoints that phase 3 is what creates.

It is not a careless sentence. It is protecting something real and expensive: **discovering on the
day that the gateway cannot reach the database means the estate is standing and billing while
somebody debugs networking**, and `backfill` is an hour and a half of it. What the sentence gets
wrong is only *when* the measurement can exist.

**So the instruction splits in two, and both halves are possible:**

| | when | what |
|---|---|---|
| **the design and the residue** | **now — this file** | what the path is, what has no API in it, what each item blocks, and what discovering it late costs |
| **the assertion** | **immediately after `sources` applies, before `backfill` spends anything** | the connection actually made, once for the first time both endpoints exist |

The second half is *inside* phase 3 by necessity, but at the **earliest moment it can exist** and
before the expensive half of the phase. That is a weaker guarantee than the sentence asked for and
it is the strongest one available.

> **`TASKS.md`'s T019 says the path is "verified in T015". It is not, and by T015's own `stop_at`
> it cannot be** — that line is restated there rather than left standing, per doctrine rule 4.

---

## The discriminator — what is in this file

T015: `out_of_scope  Anything that has an API (that is IaC).`

| kind | goes |
|---|---|
| has an API | **`infra/`, in Terraform.** Named in [What is deliberately not here](#what-is-deliberately-not-here-because-it-has-an-api) so nobody re-adds it |
| has no API at all | **here** |
| has an API, but not from where the applier stands | **here, and said in those words** — never as "no API", which would be a claim about the vendor rather than about our position |

The third row exists because of one item. The SQL that prepares the database for logical replication
runs *inside* PostgreSQL, and the RDS is in a private subnet by declared design. Whether any
infrastructure tool can execute it depends on a network path from whatever applies it into that
subnet, and CI has no such path. Calling that "no API" would be false about PostgreSQL and true
only about us — so it is written as the second thing rather than the first, and the part that is
genuinely unresolved is in [Not verified](#not-verified).

---

## The items, ordered by what discovering them late costs

**Not in the order they are performed.** A checklist read in performance order gets its expensive
items found last, which is the failure this ordering exists to prevent. The performance order is
the *Do it when* column.

### 1 · Enrol in the PostgreSQL connector's Public Preview — no API, lead time in days

> "The PostgreSQL connector for Lakeflow Connect is in Public Preview. **Reach out to your
> Databricks account team to enroll in the Public Preview.**"
> — [PostgreSQL connector limitations, docs.databricks.com](https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/postgresql-limits), read 2026-09-02

**No API, no Terraform resource, no console button.** It is a conversation with a human at a vendor,
and its lead time is whatever that person's reply time is.

*Do it when:* **first, and long before anything else here.** It is the only item whose lead time is
not under our control.

*Found on the day:* `backfill` cannot ingest ERP master data at all. The estate stands and bills
through `foundation`, `sources`, `lakehouse`, `pipelines` and `ml` while an email waits for an
answer — and the TTL reaper collects the estate before the reply arrives, so the cycle is repeated
from the beginning at full cost.

*And it has a second consequence that is not about day one at all:* `CLAUDE.md` lists this surface
as GA and forbids a claim resting on a non-GA one. That is a finding, filed as
[the PostgreSQL connector is Public Preview](FINDINGS.md), and it is the author's to settle.

### 2 · Choose a region that is in both availability lists — an API for the value, no API for the constraint

The region is a Terraform variable and therefore IaC. **The constraint on it is not**: it is a
vendor list that no code in this repository reads, and **no region is named anywhere in this
repository** — checked 2026-09-02 across all Markdown.

Read 2026-09-02 from
[Feature availability by region, docs.databricks.com](https://docs.databricks.com/aws/en/resources/feature-region-support#ingestion)
(the page states it was last updated 2026-08-31):

| | AWS regions |
|---|---|
| Zerobus Ingest | `ap-northeast-1` `ap-northeast-2` `ap-south-1` `ap-southeast-1` `ap-southeast-2` `ca-central-1` `eu-central-1` `eu-west-1` `eu-west-2` `sa-east-1` `us-east-1` `us-east-2` `us-west-1` `us-west-2` |
| Lakeflow Connect managed connectors | the same, **plus** `ap-southeast-3` `eu-west-3` |

**Zerobus is the narrower list, so the intersection is the Zerobus list** and the binding constraint
is Zerobus rather than the connector. `eu-central-1` and `eu-west-1` are both in it.

*Do it when:* before `bootstrap`, because the region is baked into the state bucket and every layer
above it.

*Found on the day:* the workspace exists in a region where one of the two ingestion paths does not.
There is no fix that is not `destroy all` and a full redeploy — the most expensive correction in
this document, and the one that looks least like a mistake until it fires.

### 3 · Set `rds.logical_replication = 1` and reboot — the parameter has an API, the reboot is an outage

> Required parameter: `rds.logical_replication`, value `1`. "Setting `rds.logical_replication`
> typically requires a database restart."
> — [PostgreSQL source setup, docs.databricks.com](https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/postgresql-source-setup), read 2026-09-02

The parameter group is a Terraform resource and belongs in `infra/sources`. **The reboot is not a
resource; it is a state transition that takes the database down**, and in this estate the database
is being driven by the `run` driver.

*Do it when:* inside `sources`, at creation, so the restart lands on an empty database that nothing
is reading. **Never after `backfill` has seeded eight months into it.**

*Found on the day:* minutes of clock, but the database goes down and whatever the driver had in
flight is gone. If it is discovered during `run`, the live day being driven is contaminated and the
run is not evidence of anything.

### 4 · Run the in-database SQL — an API PostgreSQL has and the applier may not be able to reach

Quoted from the same source-setup page, read 2026-09-02:

```sql
CREATE USER databricks_replication WITH PASSWORD 'your_secure_password';
GRANT CONNECT ON DATABASE your_database TO databricks_replication;
GRANT USAGE ON SCHEMA schema_name TO databricks_replication;
GRANT SELECT ON TABLE schema_name.table_name TO databricks_replication;
ALTER USER databricks_replication WITH REPLICATION;
GRANT rds_replication TO databricks_replication;
ALTER TABLE schema_name.table_name REPLICA IDENTITY DEFAULT;
CREATE PUBLICATION databricks_publication FOR TABLE schema_name.table1, schema_name.table2;
SET ROLE databricks_replication;
SELECT pg_create_logical_replication_slot('databricks_slot', 'pgoutput');
RESET ROLE;
```

Three things about this block are load-bearing rather than incidental:

- **`REPLICA IDENTITY`** is per table, and the page says to use `FULL` where a table has no primary
  key. Which of the ERP tables that describes is a question about `infra/sources`' schema, and it is
  not answerable from this file.
- **The publication names its tables explicitly.** The ERP is deliberately *driven* during `run`,
  and one of the declared changes is **an added column**. Whether a publication needs re-declaring
  when that happens is in [Not verified](#not-verified).
- **The password.** `CLAUDE.md` requires the RDS password to be generated into Secrets Manager.
  This is a *second* credential, for a different user, and nothing in the record says where it
  lives. Doctrine rule 3 applies to it: it is not invented at the prompt.

*Do it when:* after `sources` applies and before the Unity Catalog connection is created.

*Found on the day:* the connector refuses and the gateway cannot start. Recoverable in minutes
**if** something can reach the database; if nothing can, this becomes the network problem in
section 6 wearing a different error message.

### 5 · Create the Unity Catalog connection with the replication user's credentials

> "Create a Unity Catalog connection using the replication user's credentials after completing
> source setup." — same page, read 2026-09-02.
> Authentication: "Only username/password authentication is supported."
> — [PostgreSQL connector limitations](https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/postgresql-limits), read 2026-09-02

Username-and-password only means **no IAM role, no OIDC, no short-lived credential** on this path.
`CLAUDE.md`'s "no long-lived credentials" rule names OIDC for CI and service principals for
services; this is neither, and it is a standing exception rather than a day-one step. Named here
because a day-one document is where somebody looks for it, and settling it is the author's.

### 6 · The workspace-to-RDS network path — the item this task exists for

**What the vendor says the path may be**, read 2026-09-02 from
[Managed database connectors, docs.databricks.com](https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/cdc-overview):

> "Any network path that allows the gateway to reach the database is supported, including VPN,
> Azure ExpressRoute, AWS Direct Connect, VPC or VNet peering, and public endpoints."

**And the fact that decides which path this is:**

> "The gateway runs on classic compute, and it runs continuously to capture changes before change
> logs can be truncated in the source." — same page, read 2026-09-02

**That makes the problem smaller than it looks, and the reason is worth stating plainly.** Because
the gateway is classic compute in the workspace's own data plane — not serverless — the connection
is an **ordinary VPC-internal reachability question**: a security group, a route, a subnet. It is
not a serverless-egress problem and it needs no PrivateLink construction, provided the workspace's
VPC and the RDS's subnet are the same VPC or peered. `infra/foundation` creates the VPC and
`infra/sources` creates the RDS "in a private subnet", and **the record does not say whether that
subnet is inside the foundation VPC** — which is the single question this section turns on, and it
is in [Not verified](#not-verified).

*The classic compute itself is a separate and larger problem* — it contradicts `CLAUDE.md`'s
"no always-on cluster anywhere in the design", and it is filed as
[the ingestion gateway is classic compute](FINDINGS.md) with three ways out, one of which removes
this entire section. **If the author takes that route, sections 1 and 3–6 of this file stop
applying.**

**The assertion, and where it runs.** Immediately after `sources` applies and **before `backfill`
is dispatched**, in that order and not the other:

1. the Unity Catalog connection validates against the RDS endpoint over TLS on 5432;
2. the gateway pipeline starts and reports a live replication slot;
3. one row changes in the ERP and appears downstream.

Only (3) proves the path. (1) and (2) are named separately because each fails for a different
reason and knowing which one failed is the whole value of running them in order.

*Found on the day:* `backfill` fails after `deploy` has already applied five layers. The estate is
standing, billing, and holds nothing usable; the correct response is `destroy all` and a repeat.
**This is the specific expense `CLAUDE.md`'s "verified before phase 3" sentence was written to
prevent, and the reason the assertion is placed before `backfill` rather than inside it.**

### 7 · Teardown — the replication slot outlives the pipeline

> "replication slots require manual cleanup; failovers cause slot loss requiring full refresh"
> — [PostgreSQL connector limitations](https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/postgresql-limits), read 2026-09-02

A slot left behind on a database that still exists accumulates WAL indefinitely. In this estate
`destroy all` removes the database too, so the exposure is narrow — but **`destroy serving`
deliberately leaves the lakehouse standing**, and if the gateway is stopped while the RDS survives,
the slot is still there.

*Do it when:* before stopping the gateway, whenever the RDS outlives it.

*Found on the day:* storage growth on a database nobody is watching, which is a bill rather than a
failure — the kind that is noticed by the budget alert rather than by a red run.

---

## What is deliberately not here, because it has an API

Named rather than omitted, so that a later session does not helpfully re-add it and turn this file
into a runbook for work Terraform already owns:

VPCs, subnets, route tables, security groups · the RDS instance, its parameter group and its
subnet group · Secrets Manager and the generated password · the S3 zones and their policies · the
OIDC provider, the deploy role and the SSM parameters · the workspace and the metastore attachment
· catalogs, schemas, grants and external locations · Lakebase · the SDP pipelines, the dbt jobs and
the Zerobus endpoints · the AI/BI dashboards · the budget, its alerts and the TTL reaper.

**Every one of those is `infra/`, and a step for one of them appearing in this file is a defect in
this file.**

---

## Not verified

Listed by name with what was looked for, because a gap somebody can see is worth more than a
plausible sentence covering it.

- **Whether the RDS's private subnet is inside the VPC that `infra/foundation` creates.**
  `CLAUDE.md` gives `foundation` "VPC, keys, S3 zones, the workspace" and `sources` "RDS PostgreSQL
  playing the ERP + private networking", and never says whether the second is inside the first.
  Section 6 turns entirely on this. It is a question about a layer that has not been written, so it
  is answerable by T018/T019 and by nothing here.
- **Whether any IaC path can execute section 4's SQL from where the applier stands.** The database
  is in a private subnet and CI has no route into it. Not researched, because the answer changes
  with a networking decision that has not been taken.
- **Where the replication user's password lives.** Nothing in the record says, and doctrine rule 3
  forbids inventing one.
- **Whether the publication must be re-declared when the `run` driver adds a column.** The limits
  page says new columns auto-ingest with inline DDL enabled and that some DDL requires a full
  refresh; which side an added column falls on for a publication declared `FOR TABLE` was not
  established.
- **Zerobus Ingest's availability status is unresolved in one direction.** Its
  [overview page](https://docs.databricks.com/aws/en/ingestion/zerobus-overview), read 2026-09-02,
  carries **no** preview banner — only the Kafka-compatible APIs are marked Beta, and this project
  does not use them — which is consistent with `CLAUDE.md` calling it GA. A search result on the
  same date summarised some page as saying Zerobus Ingest is Public Preview requiring an account
  representative; **that page was not found and the claim is neither confirmed nor refuted.** It is
  recorded rather than dropped because the consequence, if true, is a second item in section 1 with
  the same lead time.
- **What the ingestion gateway costs.** It is classic compute at a stated minimum of 8 cores
  running continuously, and `CLAUDE.md`'s cost model has no line for it. Modelling it is part of
  the finding, not of this file.

---

## What this file does not settle

- **Whether the architecture changes because of what is in it.** Two findings here contradict
  `CLAUDE.md` and both are the author's — `docs/FINDINGS.md` carries them with their options.
- **How any of it is built.** That is `infra/`, and the discriminator above says why none of it is
  described here.
- **When phase 3 opens.** `PLAN.md` and `TASKS.md`.
