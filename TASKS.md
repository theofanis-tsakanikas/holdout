# Holdout — tasks

The third layer of one thing. **What** the system is, and why → `CLAUDE.md`. **How** it is built
and **in which phases** → `PLAN.md`. **The atoms** — the individual pieces of work, with their exact
closing condition and their status → this file.

This is the single source of truth for what is open. `PLAN.md` no longer carries a progress table,
because two answers to "what is still open" is exactly the thing this file exists to prevent.

## The schema

| field | means |
|---|---|
| `id` | `T001`, `T002`, … · ops/method tasks that gate the phases are `T000`, `T00A`, `T00C` |
| `title` | what it is |
| `branch` | the exact branch name (one branch per closed piece — one per session, not per commit) |
| `depends_on` | ids that must have closed first |
| `blocks` | ids that cannot start until this closes (the inverse of another task's `depends_on`, named here only where the ordering is the point) |
| `closes` | the checkable condition — which `make` target, which file, which number |
| `out_of_scope` | stated, so scope does not creep |
| `stop_at` | where the session stops and notifies the author |
| `review` | oversight level 2 in fresh context: yes / no |
| `status` | open · in progress · closed |

`status: closed` tasks stay in the file. The record of what each closed piece settled, and what the
reviews cost, stays in `PLAN.md`'s prose — doctrine rule 4: a correction never erases what was
previously stated.

---

## Ops / method — these gate the phases

These are not phase work. They fix the instruments and enforce the rules the phase work is measured
by, so they land first.

```
id            T000
title         Fix the measuring instrument — the eval schema's blind spot
branch        evals/instrument-fix
depends_on    —
blocks        T003, T004, T005, T006
closes        The claim-1 eval no longer computes a "known twice" boundary by calling the
              core's own primitive. Specifically:
              (1) the misattribution is corrected — 6,650 of the "7,366 ladder quotes
                  refused by a ceiling" are MARGIN_CAP_BASIS_UNEVALUABLE (a predicate with no
                  bound); the supportable figure is 716 of 26,600, from one envelope. Fixed in
                  the eval and in DECISIONS.md.
              (2) _exact_floor stops calling Money.as_lower_bound (the core's own rounding)
                  while its docstring claims independence; the "computed twice" boundary is
                  genuinely second-implementation, and G3's tolerance can catch a bound that is
                  one cent TOO STRICT — the exact shape of the ladder bug it cites as motivation.
              (3) benchmark_margin_pct declares which denominator it is in (selling price vs
                  cost), so a caller cannot apply 16.81% where 20.21% was meant.
out_of_scope  The floor.yaml rule-id rename and the ladder-ceiling restatement — those stay in
              T008, because they are contract changes with a restatement chain, not instrument
              defects.
stop_at       When the three fixes land with tests that fail on the un-fixed instrument, and
              before any new eval (T003–T006) is written on the corrected shape.
review        yes
status        open
```

Finding 2 is a defect in the measuring instrument itself: every eval built on the `evals/` shared
shape inherits the blind spot. It is fixed **before** it is copied four times (into the claim-2, -3,
-4 and -7 evals), not after — which is why it precedes T003–T006 instead of sitting inside the
integration session that depends on them.

```
id            T00A
title         Hooks that make the barriers structural, and make expiry
branch        ops/hooks
depends_on    —
blocks        T002
closes        .claude/hooks/corpus_isolation.py — blocks any write under corpus/world/ that
                imports from src/holdout/ (the no-import-path barrier, enforced by the harness
                rather than by a test that runs after the fact).
              .claude/hooks/main_guard.py — blocks git commit on main.
              .claude/settings.json — committed, so the hooks travel with the repository and go
                through a pull request like everything else.
              make expiry — deferred items in DECISIONS.md carry an unlock condition or a date;
                on expiry the target goes red. Doctrine rule 6 ("exceptions expire") is enforced
                nowhere today.
out_of_scope  Any hook that duplicates a check CI already makes green-or-red.
stop_at       When the two hooks fire on a deliberate violation, settings.json is committed, and
              make expiry goes red on a planted expired deferral.
review        yes
status        closed
```

The import barrier must exist **before** `corpus/world/` is written — otherwise T002 can land a
violation that only a later test catches. That is why T00A blocks T002.

**What it landed, and where it went wider than the line above.** The barrier is policed over the
whole of `corpus/`, not `corpus/world/` alone, because that is what
`tests/boundary/test_corpus_imports_nothing.py` has always policed and a hook that policed *less*
than its own gate would wave through the violation it was added to catch early. The rule now has
**one** implementation, `ops/isolation.py`, with the test and the hook as its two callers — a hook
carrying its own copy of the AST walk would have been the copy nobody reads. And the hook is
registered on `PostToolUse` for `Bash` as well: a heredoc or a `sed -i` reaches no `PreToolUse`
hook with a `file_path` at all, so a Pre-only hook would have been blind to the route this session
itself writes files by. That half cannot un-write the file and is not the guarantee; the test is.

`make expiry` runs inside `make check` and is named as its own step in `ci`. Its limit is written
into `docs/DECISIONS.md` rather than left implied: an unlock **condition** is prose and can never
expire, so a condition-only deferral is checked for existence and never for truth. What the target
does about that is print every deferral's age in days.

**Oversight level 2 found ten things, two of them fatal to this task's own `closes` line** — the
guard allowed the ordinary two-line `git commit` on `main`, and the barrier missed `src.holdout`,
which is the spelling this task description itself used and which imports and runs. Both were
fixed by correcting the code, each with a test that fails on the un-fixed version; the record is
in `PLAN.md` and `docs/DECISIONS.md`.

```
id            T00C
title         Skill — defect-to-rule
branch        skills/defect-to-rule
depends_on    —
closes        .claude/skills/defect-to-rule/ — root cause, then the rule that stops the class
              recurring. It lives in this repository because it shapes the code here (CLAUDE.md's
              criterion).
out_of_scope  The integration-review skill (T008) and any user-level skill.
stop_at       When the skill exists and has been run once against a real phase-1 defect to
              produce a rule.
review        no
status        open
```

Three phase-1 defects were already fixed — the empty `PriceBounds()`, the ladder/guardrail rounding
split, the `legal_instrument` asserting a basis its article never states — and not one of them became
a rule. The skill is what turns the next one into a rule instead of a memory.

---

## Phase 1 — the core, the contracts, and the hardest claim

Remaining atoms. Everything below has an ancestor that has already landed (see `PLAN.md`).

```
id            T001
title         core/ — design form, feasibility, assignment, four checks, estimator
branch        core/design-experiment
depends_on    —
closes        src/holdout/core/design/ and experiment/ as pure functions over plain data,
              importing no SDK, no engine, and not PyYAML or jsonschema. The design-based
              estimator is a difference of means; the inference is a permutation test under the
              same re-randomisation restriction, or a covariate-adjusted estimate. Unit tests
              AND a composition test green — no core module is tested only alone.
out_of_scope  The generator, the A/A harness, any claim-N target.
stop_at       After the core modules and the composition test; before any eval is wired.
review        yes
status        closed
```

**What it landed.** `src/holdout/core/design/` (the nine-field form, the eight refusals, the
sizing arithmetic) and `src/holdout/core/experiment/` (the keyed-hash lottery and its seal, the
standardised difference, exposure, contamination, Lin's adjustment with a studentized permutation
test and an interval that inverts it, and the two readout moments). Plus a new contract family,
`contracts/design/inference.yaml`, and one new code in the closed vocabulary,
`NO_ADMISSIBLE_ASSIGNMENT`. 510 tests to 747; `make check` green; `make claim-1` still 9/9 with
13/13 mutations biting. What each piece settled is in `PLAN.md`'s prose.

**Three corrections to the SPEC, made in the code rather than worked around**, and a fourth that
was an internal contradiction. The seed is supplied, not generated — `core/` reads no random
source, and a seed the engine invented is a seed nobody committed to in advance. The covariate
*values* had to join the signature, because the screen cannot run on a contract that only names
the columns. A one-sided quantile was used and never declared, so it joined the contract with its
own source. And `UNITS_ALREADY_COMMITTED` was listed both as an automatic exclusion and as a
refusal; it is the refusal, because the contract's own remedy says *exclude the committed units*,
in the imperative.

**The finding T003 has to act on before it starts.** At the scenario's shape — 100 stores, the
declared 20% holdout, the declared 0.10 tolerance over five covariates — the re-randomisation
screen accepts roughly **one draw in a thousand**, so a reference set inside the declared attempt
budget holds single figures and the smallest attainable p-value sits above the declared α. **No
experiment at that shape could ever report a significant effect**, which would make W6's
false-refusal rate 100% for a reason unrelated to the estimator. Recorded as a deferral in
`docs/DECISIONS.md` and measured by
`tests/core/test_assignment.py::test_the_screen_accepts_about_one_draw_in_a_thousand_at_the_scenario_s_shape`,
so it is a number in the suite rather than a paragraph. Choosing the remedy — a much larger
budget, a wider tolerance, a larger holdout share, or stratified randomisation instead of
rejection sampling — is a contract or design change and belongs to T003, not to a session whose
scope was the core.

```
id            T002
title         The generator and the six adversarial worlds (W1–W6)
branch        corpus/adversarial-worlds
depends_on    T00A
closes        corpus/world/ at 100 stores x 3 fresh categories x 8 months (~36M POS lines), with
              NO import path to src/holdout/ (now enforced by the T00A hook). Injected truth in a
              sealed file the grader opens only after the readout. W6 (a real effect is present)
              exists as a first-class world beside W1.
out_of_scope  The estimator; the independent measurement of truth on the metric (T003).
stop_at       When the six worlds produce data and the no-core-import barrier holds.
review        yes
status        closed
```

**What it landed, and the two places it went beyond the line above.** The generator is a **stream**
rather than a directory of files: a world is a pure function of `(world, seed, scale)`, generated
store-major with every draw keyed on what it is a draw *about*, so nothing is committed, a
restriction to three stores is a genuine window onto the same world, and — the property T003 needs
— **no key contains the arm**, which makes the all-control counterfactual differ from the observed
world by the treatment effect and by nothing else. `write` materialises gzipped CSV rather than
Parquet, recorded as a deferral with the S3 bulk load as its unlock.

The seal is `corpus/world/seal.py`. It holds **behaviour** — the two schedules, the exposure that
failed, the decay — and explicitly not a number about money, because the effect on the metric does
not exist anywhere until it is computed. It opens only against a readout that is already on disk and
records the opening in an append-only ledger. Its limit is asserted by a test that performs the
coordinated forgery and requires it to *succeed*, rather than described in prose beside the code.

**Two things were found by measuring rather than by reasoning, and both would have passed a green
suite.** Store placement was probabilistic, and at the smoke scale it produced **zero** neighbour
pairs — so W2 was structurally unable to interfere and every test about it would have passed
vacuously. And W2's direction was hard-coded as *control loses trade to treatment*, from the
assumption that a candidate markdown policy cuts deeper; the candidate cuts **shallower**, because
an aggressive ladder measured against its own counterfactual destroyed 5–25% of category margin
through reference-price habituation. A world whose interference points the wrong way still breaks
SUTVA and would still have been detected downstream, which is exactly why nothing would have caught
it. The test now hands the neighbour a shallower ladder and then a deeper one, both built inside the
test, and requires the watched store to move both ways.

**Deliberately not done here:** the world knows nothing about the guardrail envelope, so it produces
shelf prices the system would refuse. That is what independence costs and it is recorded as a
deferral rather than quietly fixed.

```
id            T003          <- closes Phase 1
title         A/A harness (K=200), reference implementation of truth, make claim-2
branch        evals/aa-harness
depends_on    T000, T001, T002
closes        make claim-2 green. Four numbers published, not a tick: the false-positive rate on
              A/A against the declared alpha (one-sided binomial at a stated level); the
              false-refusal rate on W6; estimator bias; and CI coverage (~95% over K runs of W6).
              Every draw runs the WHOLE system, not just the estimator. A deliberately slow Python
              reference implementation of truth-on-the-metric agrees with the dbt/SQL path with no
              tolerance, and doubles as a fourth independent check of claim 5.
out_of_scope  Claims 3/4/7 (their own tasks); preview-audit.
stop_at       If the A/A test does not stand against alpha — STOP and notify the author. Nothing
              is built on top of it. That is the whole point of putting it first.
review        yes
status        open
```

```
id            T004
title         evals/assignment/ + gate-proof — make claim-3
branch        evals/assignment
depends_on    T000, T001
closes        make claim-3 green. Assignment from a committed seed, exactly reproducible. The one
              door with no key — a test that no unit changes arm after its first observation, by
              anyone including an approver. The gate-proof mutation this claim owns bites by name.
out_of_scope  The other claims.
stop_at       After claim-3 and its mutation refuse the planted break by name.
review        yes
status        open
```

```
id            T005
title         evals/censoring/ + gate-proof — make claim-4
branch        evals/censoring
depends_on    T000, T001, T002
closes        make claim-4 green. A stock-out is never read as zero demand; the correction is
              validated on a held-out segment with full shelf availability. The simulator that
              generates censoring does NOT share the model that corrects it. The gate-proof
              mutation this claim owns bites by name.
out_of_scope  The full training pipeline (Phase 2, T014).
stop_at       After claim-4 and its mutation.
review        yes
status        open
```

```
id            T006
title         evals/oversight/ — make claim-7
branch        evals/oversight
depends_on    T000, T001
closes        make claim-7 green. The decision key carries no customer dimension, and a test goes
              red if one appears — on every type on the decision path, over the key's exact field
              set. Proved here because it costs minutes and needs nothing else.
out_of_scope  —
stop_at       When the test covers the whole field set on every decision-path type.
review        yes
status        open
```

```
id            T007
title         docs/SCENARIO.md
branch        docs/scenario
depends_on    —
closes        The file exists — the operator, the decision paths, the data, what makes it hard.
              It is in the "read this first" table and is currently missing. A writing task, not a
              blocked one.
out_of_scope  docs/DAY-ONE.md (T015, before Phase 3).
stop_at       Before Phase 2 opens — the pipelines assume it.
review        no
status        open
```

```
id            T008          <- Phase-1 integration session (oversight level 3)
title         Phase-1 integration -> the skill integration-review
branch        skills/integration-review
depends_on    T000, T003, T004, T005, T006
closes        Reads the whole repository against CLAUDE.md and reports conceptual drift — it builds
              no product code. Two deferred items it is expressly empowered to act on:
              (1) floor.yaml's rule id refuse_when_no_legal_price_sells still carries the overreach
                  the refusal code shed; the session may propose the restatement.
              (2) the ladder-ceiling gap (doctrine rule 1 is incomplete — the declared safe state
                  produces prices the envelope refuses); the session may propose a restatement.
              The method is written as the .claude/skills/integration-review skill, not as ad hoc
              instructions — so the review that runs at every phase boundary is a versioned
              procedure that goes through a pull request like everything else.
out_of_scope  The three instrument findings — they are T000, and they land before the evals, not
              after. Building any product code.
stop_at       When the drift report is written and each proposed fix is opened as its own branch
              with its own review.
review        n/a — this task IS the review.
status        open
```

The integration-review skill is extracted **after** T000, not before: a review skill extracted while
the measuring instrument still has its blind spot would encode that blind spot into a reusable
procedure and then propagate it deliberately.

---

## Phase 2 — pipelines, the metric contract's three consumers, the model (local)

```
id            T009
title         pipelines/ingest — Zerobus driver + Lakeflow Connect definitions
branch        pipelines/ingest
depends_on    T008
closes        A driver that writes as the corpus's 100 stores would: correct distribution over
              time, late arrivals, duplicates, a store that drops for two hours and then sends
              everything at once. The Lakeflow Connect definitions.
out_of_scope  Any apply to a workspace (Phase 3).
stop_at       When the driver produces a stream with the declared pathologies.
review        yes
status        open
```

```
id            T010
title         pipelines/silver — Spark Declarative Pipelines
branch        pipelines/silver
depends_on    T009
closes        Expectations routing to quarantine, the as-of reference dimension, stock-out marking
              (the one place inventory movements are available).
out_of_scope  —
stop_at       When silver builds against local Delta with quarantine non-empty on planted bad data.
review        yes
status        open
```

```
id            T011
title         pipelines/gold — dbt, the metric contract's Delta view + agent tool def + readout
branch        pipelines/gold
depends_on    T010
closes        The metric contract compiles into a Delta view, the agent tool definition and the
              readout query. The assignment table is written before the period opens and is
              read-only; the readout pins a Delta version.
out_of_scope  Executing the generated SQL on a real engine (deferred to Phase 3 — see DECISIONS.md).
stop_at       When gold builds against local Delta and the compiled consumers match byte-for-byte.
review        yes
status        open
```

```
id            T012
title         evals/definition/ — make claim-5 + make preview-audit
branch        evals/definition
depends_on    T011
closes        make claim-5 green — one definition, three genuinely different mechanisms, compared
              as integers with no tolerance (the reference implementation from T003 is a fourth).
              make preview-audit — reads the declared inventory of preview surfaces and fails when
              any claim's proof path touches one. This is where preview-audit first has something
              to act on; DECISIONS.md defers it to exactly here.
out_of_scope  The Unity Catalog metric view as a consumer (a preview/GA fourth consumer, added on
              the estate).
stop_at       When claim-5 is integer-equal across three mechanisms and preview-audit is green.
review        yes
status        open
```

```
id            T013
title         The two AI/BI dashboards as databricks_dashboard resources (definitions)
branch        lakehouse/dashboards
depends_on    T011
closes        The experiment readout and the decision monitor as databricks_dashboard resources,
              both consuming the metric contract (so both are claim-5 evidence). The refused
              version of the readout screen is the single most important screenshot in the project.
out_of_scope  Applying them to a workspace — that happens in T020 (lakehouse layer).
stop_at       When the definitions consume the metric contract and terraform validate passes.
review        yes
status        open
```

```
id            T014
title         pipelines/ml — training code, proved local
branch        pipelines/ml
depends_on    T005, T011
closes        Time-based split, censoring correction (claim 4), calibration gating above RMSE, the
              promotion gates and a named approver — pure code, proved local against a small corpus.
              A gate that has never refused anything has not been tested.
out_of_scope  The run that produces the deployed model (Phase 3, on the estate).
stop_at       When the promotion gate refuses a planted bad model for a stated reason.
review        yes
status        open
```

```
id            T015
title         docs/DAY-ONE.md — the workspace-to-RDS network path
branch        docs/day-one
depends_on    —
closes        The manual, no-API work recorded rather than silently done — in particular the
              network path from the Databricks workspace to RDS that Lakeflow Connect's database
              connectors require, verified BEFORE Phase 3, not inside it.
out_of_scope  Anything that has an API (that is IaC).
stop_at       Before Phase 3 begins, and specifically before the network path is attempted.
review        no
status        open
```

```
id            T016          <- Phase-2 integration session (oversight level 3)
title         Phase-2 integration — read the repo against CLAUDE.md, report drift
branch        —  (dedicated session, runs the integration-review skill from T008)
depends_on    T012, T014
closes        A drift report. Builds nothing.
out_of_scope  Building any product code.
stop_at       When the report is written and each proposed fix is its own branch.
review        n/a — this task IS the review.
status        open
```

---

## Phase 3 — the estate (the only phase that costs money)

Entered with every locally provable claim already green. Layers apply bottom-up; `destroy` is never
automatic.

```
id            T017
title         infra/bootstrap — applied locally, once
branch        infra/bootstrap
depends_on    T016
closes        State backend + KMS, OIDC provider, the deploy role, published parameters, and the
              budget posture — 1,000 USD with alerts at 50/80/100% and NO stop action; a stop
              action only at 150%. Enforcement is the TTL reaper in foundation, not the budget.
out_of_scope  Anything a workflow applies (foundation and up).
stop_at       When bootstrap applies from a laptop and the budget + alerts exist.
review        yes
status        open
```

```
id            T018
title         infra/foundation — VPC, keys, S3 zones, workspace, metastore, TTL reaper
branch        infra/foundation
depends_on    T017
closes        The foundation layer, including the TTL reaper — the scheduled job that destroys
              anything tagged and older than N hours whatever happened. The real net; depends on no
              workflow's control flow.
out_of_scope  Sources, lakehouse, pipelines, ml.
stop_at       When foundation applies via deploy and the reaper is scheduled.
review        yes
status        open
```

```
id            T019
title         infra/sources — RDS PostgreSQL playing the ERP
branch        infra/sources
depends_on    T018
closes        The smallest RDS instance that works, Single-AZ (a declared cost decision), in a
              private subnet, password generated into Secrets Manager.
out_of_scope  Seeding it (that is backfill) and driving it (that is run).
stop_at       When sources applies and the workspace-to-RDS path (verified in T015) holds.
review        yes
status        open
```

```
id            T020
title         infra/lakehouse — catalogs, schemas, grants, Lakebase, the dashboards
branch        infra/lakehouse
depends_on    T019, T013
closes        Catalogs, schemas, grants, external locations, Lakebase, and the two AI/BI dashboards
              (T013) applied.
out_of_scope  Pipelines and ml (separate layers, edited constantly).
stop_at       When lakehouse applies and the dashboards render.
review        yes
status        open
```

```
id            T021
title         infra/pipelines — SDP, dbt jobs, Lakeflow Jobs, Zerobus endpoints, bulk-load
branch        infra/pipelines
depends_on    T020
closes        The pipeline layer as jobs and endpoints. Split from lakehouse because pipelines are
              edited constantly and no routine edit should put an apply near catalogs and grants.
out_of_scope  Training (ml) and serving.
stop_at       When pipelines applies.
review        yes
status        open
```

```
id            T022
title         infra/ml — training job, evaluation, promotion gates, MLflow — NO endpoint
branch        infra/ml
depends_on    T021
closes        The ml layer. No serving endpoint — an endpoint cannot point at a model version that
              does not exist yet, and a version exists only after backfill has trained one.
out_of_scope  The serving endpoint and the agent runtime (T023, applied by backfill).
stop_at       When ml applies with no endpoint.
review        yes
status        open
```

```
id            T023          <- closes Phase 3
title         The five workflows + infra/serving (applied by backfill)
branch        infra/serving-workflows
depends_on    T022
closes        ci, deploy, backfill, run, destroy — each dispatching from main only. infra/serving
              (the endpoint, the agent runtime, the AI Gateway and its tool registry) applied by
              backfill once a model version exists. A run whose every figure is asserted by a step
              that fails when it is not true — at least one experiment producing a number and at
              least one refusing for the right reason — with the account confirming afterwards that
              nothing is left standing. destroy takes a target (serving | all) and is never
              automatic, on success or failure.
out_of_scope  The agent surface and claim 6 (Phase 4).
stop_at       When run's assertions pass and destroy leaves the account clean (asked, not assumed).
review        yes
status        open
```

```
id            T024          <- Phase-3 integration session (oversight level 3)
title         Phase-3 integration — read the repo against CLAUDE.md, report drift
branch        —  (dedicated session, runs the integration-review skill from T008)
depends_on    T023
closes        A drift report. Builds nothing.
out_of_scope  Building any product code.
stop_at       When the report is written and each proposed fix is its own branch.
review        n/a — this task IS the review.
status        open
```

---

## Phase 4 — the agent, and the number that matters

```
id            T025
title         The agent surface — context, tool registry, structured output, budget caps, traces
branch        agent/runtime
depends_on    T024
closes        What context the agent reads, the tool registry it is confined to, the structured
              nine-field design output, budget caps, traces. No LLM anywhere near the decision path.
out_of_scope  claim-6 (T026); the human/policy paths (T027).
stop_at       When the agent produces a structured design and is confined to its tool registry.
review        yes
status        open
```

```
id            T026          <- closes Phase 4, closes the project
title         evals/design/ — make claim-6
branch        evals/design
depends_on    T025
closes        make claim-6 green with three numbers printed: N designs proposed against a bank of
              business questions with known answers, M refused, and K of the refused that would
              have produced a confidently wrong number. The judge never rules on validity — code
              does; the judge rules only on design quality. gate-proof refuses every planted
              violation by name.
out_of_scope  README/banner/article/post/promo (T028).
stop_at       When claim-6 is green with the three numbers and its mutations bite by name.
review        yes
status        open
```

```
id            T027
title         The human path and the declared-policy path through the same engine
branch        design/three-sources
depends_on    T025
closes        The human path and the declared-policy path exercised by the SAME engine, proving the
              engine does not know and does not care who filled the form — same checks, same
              refusals, same experiment.
out_of_scope  —
stop_at       When all three sources (agent, human, policy) are first-class through one engine.
review        yes
status        open
```

```
id            T028
title         Publication — README, banner, article, debut post, promo
branch        docs/publication
depends_on    T026
closes        The publication checklist runs: README to the portfolio standard, banner, long-form
              article, debut post, promo. Every Greek citation re-opened through search.et.gr and
              updated; every console screenshot through aws-mask. The repository is public but
              unannounced until this closes.
out_of_scope  Any product claim.
stop_at       When the checklist is complete and the citations are re-verified.
review        no
status        open
```

---

## Closed — the atoms that have landed

Kept so this file is the complete registry, not just the open half. What each one settled lives in
`PLAN.md`'s prose.

```
L1  contracts/ — the metric schema, the guardrail envelope with effective windows, the nine-field
    design schema, the closed reason-code vocabulary, ladder_policy@v1, the compilers, make
    contracts, docs/REGULATORY.md.        branch contracts/schemas              status closed
L2  src/holdout/core/ — the guardrails and the certificate type (ProposedPrice ->
    CertifiedPrice | Refusal), scenario selection, the ladder. Money as integer cents with three
    roundings.                            branch core/guardrails-pricing-ladder status closed
L3  corpus/real/, evals/guardrail/, evals/gate_proof/, make claim-1, make gate-proof — claim 1
    closed; thirteen mutations, each refused by the check named in advance.
                                          branch evals/guardrail-and-gate-proof status closed
L4  Mutation ownership — a mutation belongs to exactly one claim and runs under that claim's
    target; gate-proof audits rather than executes (the orphan/duplicate ledger).
                                          branch evals/mutation-ownership       status closed
L5  CI, the protected main (a ruleset with no bypass actors), docs/DECISIONS.md.
                                          branch ops/gate-and-decisions         status closed
L6  src/holdout/core/design/ and experiment/ — the nine-field form, the eight design
    refusals, the committed lottery and its seal, the four validity checks and the
    design-based estimator. contracts/design/inference.yaml as a fourth contract family.
                                          branch core/design-experiment         status closed
```

---

## The critical path

```
T00A ─▶ T002 ─┐        (both closed)
              ├─▶ T003 (claim-2, closes Phase 1) ─▶ T008 ─▶ Phase 2 ─▶ Phase 3 ─▶ Phase 4
T001 ─────────┤        ▲     (T001 closed)
T000 ─────────┴────────┘  (also blocks T004, T005, T006)
```

T000 and T00A gate the phase-1 evals and corpus respectively, and both had no upstream. **T00A,
T002 and T001 have closed.** T003 — the A/A harness and `make claim-2`, which closes phase 1 — now
waits on T000 alone, as does T005 (claim 4) on its corpus side.

**T003 carries one inherited condition.** The screen's acceptance rate at the scenario's shape
leaves the reference set too small for the declared α — see T001's record above and the deferral
in `docs/DECISIONS.md`. T003 cannot produce a meaningful false-refusal rate on W6 until that is
settled, so settling it is the first thing in it rather than a surprise in the middle.
