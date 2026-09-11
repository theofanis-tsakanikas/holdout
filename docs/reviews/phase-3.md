# Phase 3 — integration review (oversight level 3)

**T024 · 2026-09-11 · branch `docs/phase-3-integration`**

Oversight level 3 reads the whole repository against `CLAUDE.md` and reports conceptual drift.
**It builds nothing.** Each proposed fix becomes its own branch with its own review.

**It ran late, and that is the first finding about the process.** `CLAUDE.md`: *at every phase
boundary, without exception.* Phase 3's closing criterion was met on 2026-09-10 and phase 4's first
two tasks were built on 2026-09-11 before this session opened. Nothing in the tree refuses that
order — `TASKS.md` has `T025 depends_on T024` and nothing reads `depends_on`. The consequence is
visible below: two of this review's findings were produced *by* phase-4 work rather than found
here, which is the review arriving to a room somebody has already tidied.

**What was run to produce this report**, on a fourteen-core laptop, against `main` at `af5b850`
with `evals/design-under-violation` (#120) applied on top:

```
make check                    1881 passed, 1 skipped, 60 deselected, exit 0   2m20s
make eval-guardrail           green 10/10
make eval-assignment          green 10/10
make eval-censoring           green 12/12
make eval-oversight           green 12/12
make eval-design              green 11/11          the new one; K published three ways
make eval-uplift              green 13/13          warm .worlds; U1 = 8/200 = 4.0%
make gate-proof               green  9/9 · 56 mutations · 43 armed · 27 un-armable · 9 unarmed
make expiry                   38 entries: 32 open, 6 closed · 5 dated, 27 condition-only
python -m ops.roster          at `harness` and at `estate`
the GitHub API                the `main` ruleset, the three environments, the packed durations
                              of `claim-6`'s first three runs
the AWS account               what stands after `destroy`, asked service by service
```

`eval-uplift` was run, and the line says so because the phase-1 report did not and the phase-2
report had to say it was closing that gap. It is 13/13 at `harness` on this laptop.

---

## 0 · What stands

**No claim's proof has collapsed.** Six claims green on the laptop and on CI; claim 6 exists,
which it did not at the last boundary, and its three numbers are printed. Both independence
barriers hold: `tests/boundary/test_corpus_imports_nothing.py` is green, and the recording claim 6
grades carries the fingerprint of an agent that has never read `feasibility.py`. `ops.roster`
reproduces the table `CLAUDE.md` restated on 2026-08-29 exactly — 320 → 59 pairs → 269 roster →
53 control at `harness`; W2 222 and 44.

**Phase 3's criterion, as restated on 2026-09-09, is met in its first half.** `run` 34459339015
read out two experiments, both refused for declared reasons of two different kinds, and asked the
endpoint which version answered. The second half — *the account confirming afterwards that
nothing is left standing* — was met on 2026-09-10 for everything Terraform owns and not for the
network Databricks leaves behind, twice, for two different defects, each fixed on its own branch;
the dispatch that would exercise the second fix has no estate to run against, and the author moved
it to phase 4's cycle. So phase 3 is closed on its criterion **and `T023` is still open**, which is
the registry saying the true thing rather than the tidy one.

**And the estate is down.** Asked of the account service by service on 2026-09-10 evening: the two
state buckets, the state KMS key, four bootstrap parameters and the deploy role, which is
`CLAUDE.md`'s survivor list to the letter; five data keys `PendingDeletion`; no Lambda, no rule, no
topic, no log group, no zone bucket, no NAT gateway, no address. One empty VPC skeleton, costing
nothing, that the automation cannot reach because the parameter it needs was destroyed with the
layer that published it.

---

## 1 · Does any claim's proof rest on something that has become a tautology?

**No new tautology, and one that was avoided by measurement.** Claim 6's `D5` compares the engine's
answer to itself across three attributions, which is agreement — and it is a check only because
mutation `01` plants a branch on `filled_by` and `D5` refuses it. Its `D4` first compared the
engine's refusal codes against the engine's own enum, which is one function agreeing with itself;
it reads the contract's `at_design` list now, and that was changed on the branch before the eval
first ran, by reading the check rather than by a mutation surviving.

**What did survive, and what it found.** Mutation `03` — `store_category` admitted as a unit — bit
on the laptop and **SURVIVED on CI**, because the committed recording holds two interference
refusals and admitting one unit left the code reached by the other. `D7`'s population is the
recording's designs; the break lives in the contract's carryover table. `D9` derives that table a
second time and compares it over every unit, and the mutation is re-aimed there. *A gate can only be
shown to bite where it is the gate that refuses* — the rule from claim 1's history, arriving in
claim 6's first week.

**`gate-proof` reports 9 unarmed checks**, five of them claim 6's `D2`, `D3`, `D4`, `D6` and the
new `D10`/`D11` pair's siblings; each carries `unarmed_because`, so the ledger reads them as
declared rather than forgotten. The reasons are the narrow ones the seventh rule admits — a property
of the recording, a property of the inputs, a count against chance — and this review has no
objection to any of them.

*Disposition:* none — no finding.

---

## 2 · Has any gate stopped biting — and for what reason?

**Three, and the first is the most interesting because it is green.**

**2a · An anchor sees a sentence change and cannot see it stay wrong.** `docs/FINDINGS.md`'s
closing entry from 2026-09-05 restates its `*Now:*` anchor every time a layer lands — *Two* →
*Three* → *Four*, three restatements in three days, and the entry says so is *the anchor working*.
Six layers exist today. `CLAUDE.md`'s layout block still reads **`Four layers exist`**, the anchor
still matches it exactly once, and `make findings` is green. The mechanism can only notice a line
that moved; a line that stayed while the world moved is invisible to it, and the entry's own
argument — *the anchor is on the half that moves* — described the failure it would have and
called it a feature. **The count is a present-tense figure and belongs in `make figures`'s `PROSE`
list**, which re-runs a figure against the command that produces it and is the instrument built
for exactly this on 2026-08-31. It has never been given this sentence.

*Disposition:* branch `ops/the-layer-count-is-a-figure` — `PROSE` gains the layer count against
`ls infra/`, and the block is corrected in the same change so the new figure is green on arrival.

**2b · The forge guards `destroy` with nothing, and the workflow says otherwise.** Asked of the API:
the `deploy`, `destroy` and `plan` environments each have **zero** required reviewers.
`infra/bootstrap/github.tf` declares a reviewer on every environment but `plan`. `TASKS.md`'s T017
records the author relaxing `deploy` for the bring-up, in the account and not in the code, and says
*the next unrestricted apply restores it*. It does not record `destroy`, and `destroy.yml`'s own
header asserts the opposite of what the forge holds:

> *`environment: destroy` carries a required reviewer, and that is the asymmetry this project
> chose on purpose.*

Every `destroy` this phase dispatched — four of them — ran with no approval and no pause. That is
prose claiming a guard nobody has, in the file that removes the estate, which is the shape
`CLAUDE.md` catalogues under *the same defect one layer up*. It is not a defect in the code: the
code declares the reviewer. It is a fact that lives in the forge, and no reading of this tree can
find it — the second known member of the class §3 of the skill says has only one.

*Disposition:* the author's — restore both reviewers with a whole `terraform apply` of
`infra/bootstrap` once the bring-up is over, or restate the workflow's header and T017 to say
`destroy` was relaxed too. Filed in `docs/FINDINGS.md`.

**2c · The CI ceiling check abstains on a cold cache, and `claim-6` was cold on its first run.**
Run 34560323264 took 463s with its own world-cache key missing; the packed job compared nothing
against the ceiling, as designed, and the cost was declared from that run as a bound above it.
Not a finding in the mechanism — the abstention is argued at length in `ci.yml` — but the second
time in this repository that the first run of a new target was the one the ceiling could not judge.
Recorded so that a third instance is a pattern.

*Disposition:* none — recorded.

---

## 3 · Does the code still say what `CLAUDE.md` says it says?

**The map, again, in the direction `make figures` cannot see.** `CLAUDE.md`'s layout block:

| the sentence | the tree |
|---|---|
| `.github/  **ci.yml, and it is the only one.** The four that dispatch are phase 3` | five workflows, all built, and the restated table twenty lines below says so |
| `infra/  Terraform. **Four layers exist**` | six: `ml/` and `serving/` were applied on 2026-09-10 and destroyed the same day |
| `The other two (ml · serving) are phase 3` | phase 3 is over |
| `experiments/  one YAML per experiment, in git, with its full history` — *declared and not yet built* | still not built, and never will be in that form: the two experiments are `DECLARED` in `pipelines/gold/experiments.py`, as Python, with their stopping rules beside them |

The first three are the defect the block's own note names — *a directory that exists may not be
described as unbuilt* — for the third time, and the note was written after the second. `make
figures`'s layout row reads 24 = 24 because every tracked directory is *named*; it has nothing to
say about a name in the wrong sentence, which the note also says. What has not happened is anybody
turning the count into a figure (§2a).

**The fourth row is different.** `experiments/` is not stale; it is a design that was replaced
without the replacement being written down. An experiment declared in a Python module is an
experiment that changes when the module changes, with no restatement chain and no `git log` a
reviewer would think to read. Whether that is what the author wants — two experiments, fixed, in
code — or whether the estate's readout should be driven by files under `experiments/` as
`CLAUDE.md` still says, is a decision and not a correction.

**`src/holdout/adapters/` is a fourteen-line docstring** under the heading *thin cloud callers*.
Every cloud call the estate makes lives in `pipelines/` and, since 2026-09-11, in
`holdout/agent/client.py`. A package the map describes and nothing imports is the map describing
the plan.

**And three of these were already in the register, adrift.** `docs/FINDINGS.md` has carried
*the layout block's third crossing* since 2026-09-04, *nothing checks that a directory declared
not yet built is still unbuilt* and *the layout block cannot say declared and never to be built*
since 2026-09-02 — each with `*Disposition:* none`, each nine days adrift when this review opened
the block and found the fourth crossing. A finding filed three times with no owner is not a
finding anybody is going to fix by being told a fourth time; it is one whose mechanism is missing,
and §2a names it.

*Disposition:* rows one to three, branch `ops/the-layer-count-is-a-figure` (with §2a), which
closes the three adrift entries; row four, the existing entry restated as re-found with the
instance named — the author's; `adapters/`, a new entry, the author's.

---

## 4 · Is there code that serves no claim?

**`pricing/selection.py`, still, twelve days on.** `docs/FINDINGS.md` carries it as *adrift* —
`*Disposition:* none — to be scoped by whoever picks it up* — since 2026-08-31. It is reached by
`evals/oversight` only as a type whose fields claim 7 scans, which is not a functional reach, and
by no mutation. The phase-1 review found it and then lost it; the register was built so it could
not be lost again; it has not been lost, and it has not moved either. A finding that survives two
boundaries adrift is a finding whose owner is the author, and this review says so rather than
re-recording it.

**`src/holdout/adapters/`**, above.

**And the LLM judge that was not built.** `CLAUDE.md`'s claim-6 row permits a judge that *rules
only on design quality*. `evals/design/README.md` declines it in one paragraph — a second vendor
dependency for a number nothing checks — and this review concurs, which per §6 of the skill is not
closure. The row still permits it. Whether the permission should stay in the file is the author's.

*Disposition:* `selection.py` — unchanged, and named to the author a second time; the judge —
none, a permission unused is not drift.

---

## 5 · Has a claim landed on a preview surface?

**No.** `make preview-audit` exists now, runs in `make check`, and reads a declared inventory. The
serverless environment the estate runs on, `environment_version = "4"`, is GA; the model serving
endpoint is GA; Zerobus Ingest is GA and `CLAUDE.md` says so. The Lakeflow Connect connector that
was Public Preview was removed with the RDS it would have read. The question came back clean at
this boundary for the second time, and it is kept for the reason the phase-1 report gave.

*Disposition:* none — no finding.

---

## 6 · Is there still exactly one door with no key — not zero, not three?

**Phase 3 delivered the table and the door has an owner.** Doctrine rule 7's restatement of
2026-08-30 promised: *unopenability arrives in phase 3, with the read-only assignment table … where
the storage refuses the write that the type can only notice afterwards.* What arrived:

- `gold.experiment_assignment` is `delta.appendOnly`: update, delete and overwrite refused by the
  storage, **append permitted** — measured, three of four, and `pipelines/gold/assignment.py`
  says so and says `verify` is what catches the fourth.
- `infra/lakehouse/grants.tf` gives `account users` `SELECT` and `BROWSE` and nothing that writes.
  For a person, the door is shut.
- The pipelines run as the service principal that **owns** the objects, and an owner in Unity
  Catalog can append, can alter the table's properties, and can drop it. For the principal, the
  door is keyed, and it is the same identity that runs every job.

So the honest sentence today is a step past the last one and not at the destination: *one door,
shut to people, keyed for the automation, and reporting every hand laid on it.* The restatement
that promised more was written before the layer that would keep the promise existed, which is the
shape §3's `experiments/` row has too — a sentence that described a plan and became a description.

*Disposition:* branch `docs/the-door-has-an-owner` — a fourth restatement of rule 7 in
`CLAUDE.md`, per rule 4, saying what phase 3 delivered and what it did not. A sentence in the file
that governs every other branch, which is the phase-1 review's declared exception; it is proposed
as its own branch anyway, because this review builds nothing.

---

## 7 · What has the deferral registry become?

**Thirty-eight entries: 32 open, 6 closed; 5 carry a date, 27 a condition only; 0 name this
session.** The rule from 2026-08-30 — a condition names an event, never a session — held for the
whole of phases 2 and 3, which is the phase-1 review's largest output doing its job.

**And three conditions have been met without anybody noticing.** Read entry by entry against the
tree:

| entry | deferred | its unlock condition | the event |
|---|---|---|---|
| *`terraform validate` and `make preview-audit` in CI* | 2026-08-27 | *the first Terraform layer, and the first time a preview surface is considered* | `infra/bootstrap` landed 2026-09-05; both targets run in `ci.yml` and `make check` today |
| *The generated SQL has never been executed* | 2026-08-27 | *phase 2, when gold is built* | gold ran on the estate with five dbt models on 2026-09-10, run 34443755277 |
| *`evals/` and every `claim-N` target* | 2026-08-27 | *`corpus/real/` and the eval directories, each with the mutation that proves its gate bites* | six evals, 56 mutations, `make gate-proof` green |

`make expiry` cannot see any of the three: it checks that a condition is *present*, never that it
is *met*, which is its declared limit. This is the phase-1 review's §2 finding — *a budget whose
unlock condition had been met unnoticed* — three times over, and the reason level 3 reads the
registry as a population.

*Disposition:* branch `docs/deferrals-whose-conditions-were-met` — a `*Closed:*` with the date and
the event on each, and nothing else.

---

## 8 · Is the recurring rule complete?

**The phase's instances, counted.** Since the phase-2 review, every finding that reached the
register wears one of two shapes:

*A population defined by a property is blind to whatever lacks it* — nine times: `tests/infra/
tasks.py` blind to `parameters = concat(...)`; the survivor check enumerating by a tag Databricks'
VPC does not carry; the IAM condition on a tag only the VPC carries, inside the fix for the
previous one; `describe-addresses` region-wide inside a loop scoped to one VPC; `_declared_reason_
codes` reading strings where the contract holds dicts; the harness form skipping the schema the
agent could not; a mutation surviving because a second design reached the same code; seven designs
drawing one lottery from one seed; and §2a above, an anchor that watches a line.

*Two projections about one thing, never compared* — three times: the credential's duration in the
workflow and in the role; T023's `closes` and `out_of_scope` inside one block; the candidate policy
in `corpus/world/policy.py` and the policy list the form compiles from.

**The rule is not incomplete. What this phase adds is a limb about instruments rather than
populations**: an anchor, a count, a `verified_on` — each is a *representation* of a fact, and a
representation can be true of the thing at the moment it was made and stay green while the thing
moves. `docs/FINDINGS.md`'s own first paragraph already says this of itself. The phase-1 answer to
the rule was `make figures`, which re-runs a figure against its command; the phase-3 answer is that
`make figures` has to be *given* the figures, one by one, and the layer count was never given to
it. **A mechanism that must be fed by hand is a hand-kept list wearing a mechanism's clothes**,
and this repository's own §8 said that of `PROSE` on 2026-09-05 and kept it deliberately small.
Whether the list should now grow — the layer count, the workflow count, the family count — is
proposed in §2a's branch and left to the author.

**And the process finding.** `CLAUDE.md` schedules level 3 *at every phase boundary, without
exception*; `TASKS.md` has no integration task after phase 4, and phase 4 opened before this one
ran. Two documents, each defensible, no reconciliation written down — the skill found this while
being written and it is still true. Phase 4 closes the project, so the question is whether the
project closes with a review or with a merge.

*Disposition:* the phase-4 boundary — already in `docs/FINDINGS.md` since 2026-08-31, adrift
eleven days, restated as re-found with the second half; the author's, a `T029` or a sentence in
`PLAN.md` saying why not.

---

## The question no reading of this tree can answer

> **what does the `main` ruleset require, and does that list match the jobs `ci.yml` defines
> today?**

Asked of the API on 2026-09-11. Ruleset `21614140`, active, on the default branch, **no bypass
actors**, requiring three contexts: `gate`, `secrets`, `claims-complete`. `ci.yml` defines six
jobs: those three, and `discover`, `claims`, `combine`, which `claims-complete` aggregates with
`if: always()`. **The list matches.** The number read rather than the sentence: 3, and 3 is what
the design says.

What the same API said about the environments is §2b, and it is the second known member of the
class this question is the first of. The skill says there is no rule for finding the next one; two
instances are still not a rule, and this review adds the second to the record rather than the
rule.

---

## What this review proposes

The table records what was proposed on 2026-09-11 and is never updated afterwards; present-tense
status lives in `TASKS.md` and `docs/FINDINGS.md`.

| # | branch or decision | closes |
|---|---|---|
| 1 | `docs/deferrals-whose-conditions-were-met` | §7 — three `*Closed:*` lines with dates and events |
| 2 | `ops/the-layer-count-is-a-figure` | §2a, §3 rows 1–3 — the count into `PROSE`, the block corrected |
| 3 | `docs/the-door-has-an-owner` | §6 — rule 7 restated a fourth time |
| 4 | the author: restore the environment reviewers, or restate `destroy.yml` and T017 | §2b |
| 5 | the author: `experiments/` as files, or `CLAUDE.md` restated to say experiments are declared in code | §3 row 4 — an entry adrift since 2026-09-02, re-found |
| 6 | the author: `src/holdout/adapters/` deleted or filled, and `selection.py` scoped or deleted | §3, §4 — `selection.py` adrift since 2026-08-30 |
| 7 | the author: a `T029`, or a sentence saying the project closes without one | §8 — an entry adrift since 2026-08-31, re-found |

Ordered so that the first two are the ones that stop the class recurring and the rest are
corrections. Rows 4 to 7 are decisions and not branches, and each is in `docs/FINDINGS.md` with a
site — two of them were already there, adrift, and this review's contribution to those is the word
*re-found* and a date, which is the register doing what it was built for: **the register held
them, and holding is not the same as anybody picking them up.** Twenty-four of eighty-one open
findings are adrift today. That number is this review's last figure, and it is the one the author
should read first.
