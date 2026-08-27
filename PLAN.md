# Holdout — plan

Four phases. Each names what closes it. Nothing in a later phase starts before the earlier one
closes, because every later phase assumes the earlier one is true.

**Phase 1 is the core and the claims that need nothing else. Phase 3 is the claims that need an
estate.**

---

## Phase 1 — The core, the contracts, and the hardest claim

The phase that decides whether the project is worth building.

### Work

- `contracts/` first: the metric schema, the guardrail envelope with effective dates, the
  nine-field design schema, the closed reason-code vocabulary, `ladder_policy@v1`.
- `src/holdout/core/` as pure functions: guardrails and the certificate type, scenario selection,
  the ladder, the design feasibility engine, assignment from a committed seed, the four validity
  checks, the design-based estimator.
- `corpus/world/` — the generator and the six adversarial worlds at **100 stores across three
  fresh categories over eight months** (~36M POS lines), with **no import path** to `core/` and a
  test that enforces it. The truth lives in a sealed file the grader opens only
  after the estimate is produced.
- `evals/uplift/` — the A/A harness at K = 200 seeds with a one-sided binomial check against the
  declared α, and the six worlds including W6, the world where the correct answer is "yes, there
  was an effect". Every draw runs the whole system, not just the estimator.
- The reference implementation of truth: a deliberately slow Python loop over every event,
  written separately from the dbt path, so the two must agree. It doubles as a fourth independent
  check of claim 5.
- The re-randomisation screen on declared pre-period covariates, and the matching inference — a
  permutation test under the same restriction, or a covariate-adjusted estimate. CI coverage
  drifting above nominal in the A/A harness is the symptom of getting this wrong.
- `evals/assignment/`, `evals/guardrail/`, `evals/censoring/` and their `gate-proof` mutations.
- `evals/oversight/` — the decision key carries no customer dimension, and the test goes red if
  one appears. It costs minutes and needs nothing else, so it is proved here rather than left
  open for months.
- The Makefile: one target per claim, plus `make contracts` — recompiles every consumer and goes
  red on a stale artefact or on a guardrail `value` with no `source`.

### What closes this phase

**`make claim-2` green.** On an A/A split the system reports a significant effect no more often
than its declared α, across K = 200 seeds; and across the six worlds it refuses exactly where it
should and — equally important — **does not refuse in W6**. Four numbers are published, not a
tick: the false-positive rate against α, the false-refusal rate on W6, estimator bias, and CI
coverage.

**If the A/A test does not stand, nothing is built on top of it.** That is the whole point of
putting it first.

### Progress

| piece | branch | state |
|---|---|---|
| the repository skeleton, `contracts/`, the compilers, `make contracts`, `docs/REGULATORY.md` | `contracts/schemas` | **landed** |
| `src/holdout/core/` — guardrails and the certificate type, scenario selection, the ladder | `core/guardrails-pricing-ladder` | **landed** |
| `src/holdout/core/` — the design form, feasibility, assignment, the four checks, the estimator | `core/design-experiment` | open |
| the generator and the six adversarial worlds | `corpus/adversarial-worlds` | open |
| the A/A harness, the reference implementation of truth, the per-claim eval directories | `evals/aa-harness` | open |
| the `claim-N`, `gate-proof` and `preview-audit` targets | with the eval each proves | open |

**What the contract layer settled.** The four families are versioned with effective windows and
resolve as-of, so a decision taken in April is judged by April's rule permanently. Every numeric
`value` carries either a legal citation with a verification date or an explicit
`scenario_assumption` — 45 values, and `make contracts` prints the ratio of sourced to found so the
number can be less than 100%. The metric contract compiles into 13 artefacts that are byte-compared
on every run, so a hand-edited consumer is a build failure. A metric whose arithmetic or rounding
moved without a `restatement` is a build failure. `src/holdout/core/` is still empty by design; the
boundary test that keeps PyYAML and jsonschema out of it is placed and waiting.

**What it cost to get honest.** The review caught a `legal_instrument` asserting a basis its own
article never states — the per-unit framing belongs to 2022, not 2021 — and four more of the same
class, including a Directive cited as evidence about Greece. `make contracts` could not have caught
any of them: it checks the *shape* of provenance, never its *content*. That is the standing limit
of the mechanism, and it is why oversight level 2 reads the citations rather than trusting the
green tick. Separately, generation had been resolving paths against a fixed repository root, so
every negative test asserting only "exit code 1" had been passing for the wrong reason.

**What the core settled.** `ProposedPrice → CertifiedPrice | Refusal`, and `CertifiedPrice` is a
type rather than a convention: not a dataclass, filled by a function held in a closure and stamped
with a witness that has no importable name. Direct construction, subclassing, `dataclasses.replace`,
pickling, copying and duck-typing all refuse. The actuator re-derives the certificate's checks from
its own recorded bounds, so a tampered price contradicts what the certificate claims was checked.
Money is integer cents with three roundings, because a bound that rounds toward what it forbids is
not a bound. The ladder, the envelope and scenario selection are pure functions over plain data;
`core/` imports no SDK, no engine, and not PyYAML or jsonschema either.

**The limit, stated rather than papered over.** A forger who rewrites the price, the bounds, the
checks and the source in one coordinated edit is not caught by any check inside a certificate,
because the certificate never held independent evidence of its own provenance. A test asserts that
limit rather than hiding it. **The type makes the mistake impossible and leaves the forgery visible.**

**What the review cost, again.** Two lines of public API defeated claim 1's central sentence: an
empty `PriceBounds()` satisfied both halves of the actuator's re-check, turning a certified €2.00
into €0.01 on a shelf. And the ladder's deepest rung — the declared safe state of the primary
decision path — was refused by the envelope for roughly one base price in five, at the rung three
hours from expiry that matters most, because the ladder rounded its quote as a price and the
guardrail rounded the same number as a bound. Neither was visible to a green suite, for one reason:
**the branch delivered two modules and never composed them.** From here on, no core module is
tested only alone.

**Deliberately not built yet:** no `claim-N` target exists, because nothing here proves a claim. A
green target that proves nothing is a gate disarmed before it was ever armed. Claim 1 is not proved
by the core — it is made provable; the eval that attacks the gates from an independent corpus of
real price lists is still open, and the seam it needs is built and verified.

**Still missing from the "read this first" table:** `docs/SCENARIO.md`, `docs/DECISIONS.md`,
`docs/DAY-ONE.md`. And there is no `.github/` — oversight level 1 is a Makefile someone remembers
to type until a remote and a `ci` workflow exist.

### Closed in this phase

Claims 1, 2, 3, 4 and 7 — all provable local, with no account.

**Then an integration session**, before the next phase opens: read the whole repository against
`CLAUDE.md` and report conceptual drift. It builds nothing.

### Open

Everything that needs data at scale, an engine, or a workspace.

---

## Phase 2 — The pipelines, the metric contract's three consumers, and the model

### Work

- `pipelines/ingest/` — the Zerobus driver that writes as the corpus's 100 stores would: correct
  distribution over time, late arrivals, duplicates, a store that drops for two hours and then
  sends everything at once. The Lakeflow Connect definitions.
- `pipelines/silver/` — Spark Declarative Pipelines, with expectations routing to quarantine and
  the as-of reference dimension.
- `pipelines/gold/` — dbt. The metric contract compiles into a Delta view, the agent tool
  definition and the readout query.
- The two AI/BI dashboards as `databricks_dashboard` resources — experiment readout and decision
  monitor. The second is required by doctrine rule 2: without it, a fallback is not visible to the
  end. Both consume the metric contract, so both are claim 5 evidence.
- `evals/definition/` — the three mechanisms compared as integers, no tolerance.
- `pipelines/ml/` — the training code: time-based split, censoring correction, calibration gating,
  the promotion gates and a named approver. Proved **local** against a small corpus. The run that
  produces the deployed model happens on the estate in phase 3, where the data is.
- `make preview-audit` — the declared inventory of preview surfaces, and the check that no
  claim's proof path touches one.

### What closes this phase

`make claim-5` green against local Delta tables, and a trained model that the promotion gate
either accepts for a stated reason or refuses for a stated reason. **A gate that has never
refused anything has not been tested.**

### Closed in this phase

Claim 5. The pipelines and the training code, proved local.

**Then an integration session**, before the next phase opens: read the whole repository against
`CLAUDE.md` and report conceptual drift. It builds nothing.

### Open

Everything requiring a real workspace and a real bill.

---

## Phase 3 — The estate

The only phase that costs money. It is entered with every locally provable claim already green.

### Work

- `infra/bootstrap/` applied locally, once: state backend, OIDC, the deploy principal, and the
  budget posture — **1,000 USD with alerts at 50/80/100% and no stop action**, a stop action only
  at 150%. A budget that halts a run mid-way costs more than it saves. Enforcement is the TTL
  reaper in `foundation`, not the budget.
- `infra/foundation/`, `sources/`, `lakehouse/`, `pipelines/`, `ml/` applied by `deploy`;
  `infra/serving/` applied by `backfill`, once a model version exists. CI only. Layer boundaries follow lifetime, blast radius, dependency direction and apply cost.
- **Before this phase begins**, not inside it: verify the network path from the Databricks
  workspace to RDS that Lakeflow Connect's database connectors require, and record whatever has
  no API in `docs/DAY-ONE.md`. Discovering this during a paid run is the expensive way.
- `sources/` stands up the real Postgres playing the ERP. `backfill` seeds it with eight months;
  the **driver** changes it during `run`: a mid-day cost change, a product entering the regulated
  basket, a retroactive supplier term, an added column, a deactivated SKU.
- Five workflows: `ci`, `deploy`, `backfill`, `run`, `destroy`.
- **`backfill`** — eight months of history: ERP master data through Lakeflow Connect from RDS,
  transaction history bulk-loaded from files on S3 (streaming eight months through Zerobus is slow,
  costly and nobody does it). Then silver, gold, training on the estate, the gates, a registered
  version — and only then the `serving` apply, because an endpoint cannot point at a version that
  does not exist.
- **`run`** — one live day through Zerobus with lateness and duplicates, decisions routed by arm,
  two experiments (one produces a number, one must refuse), a live question answered at the
  endpoint, and the account asked whether it behaved. The driven day is **after** the trained
  history, so it is held out by construction.
- **`destroy`** — **never automatic**, on success or failure. It takes a target: `serving` kills
  the expensive layer in two minutes and leaves the lakehouse browsable; `all` takes everything.
  On failure the evidence survives; on success the estate is what the console recordings need. The
  TTL reaper in `foundation` is the guarantee, not the workflow.

### What closes this phase

A `run` whose every figure is asserted by a step that fails when it is not true — including at
least one experiment that produces a number and at least one that **refuses** for the right reason
— with the account confirming afterwards that nothing is left standing.

### Closed in this phase

The live evidence for claims 1 to 5. The cost model — 20–60 USD a cycle, 100–600 USD across the
five to ten cycles it realistically takes — replaced by a real bill.

**Then an integration session**, before the next phase opens: read the whole repository against
`CLAUDE.md` and report conceptual drift. It builds nothing.

### Open

The agent surface and claim 6.

---

## Phase 4 — The agent, and the number that matters

### Work

- The agent surface: what context it reads, the tool registry it is confined to, the structured
  design output, budget caps, traces.
- `evals/design/` — N designs proposed against a bank of business questions with known answers,
  M refused, and **K of the refused that would have produced a confidently wrong number**.
- The human path and the declared-policy path, exercised by the same engine to prove the engine
  does not care about the source.
- README, banner, article, debut post, promo.

### The shot list

| claim | where it is visible |
|---|---|
| 1 · guardrails | decision monitor, the guardrails that fired · `gate-proof` in a terminal |
| 2 · no false uplift | **the readout showing a REFUSAL** · the A/A rate in a terminal |
| 3 · locked holdout | the assignment table, read-only, with its seed |
| 4 · stock-out | a notebook: the same hour, with and without the correction |
| 5 · one definition | three windows side by side showing the **same** number |
| 6 · the engine refuses | the agent's design → the refusal and its reason code |
| 7 · no person | the decision key schema · the test that goes red |

### What closes this phase

`make claim-6` green with the three numbers printed, and `make gate-proof` refusing every planted
violation by name.

### Closed in this phase

Claim 6. The project.

---

## What this plan will not do

- **It will not claim causal identification outside the randomised design.** Observational
  elasticity ranks candidates. It never reports money.
- **It will not claim the feedback loop is solved.** The model trains on data its own decisions
  produced. Deliberate price randomisation limits this; it does not remove it.
- **It will not put a claim on a preview surface.** Real-Time Mode, metric views, domains,
  contextual policies and Genie Ontology are additive and removable throughout.
- **It will not claim optimality.** The claim is not that the decisions are the best available.
  It is that every number reported survives being checked.
- **It will not build a Genie replacement.** Backward-looking question answering is a commodity
  and is not where the value is.
