# Holdout — project context

**Language rule: all repository content in English. Conversation with the author in Greek.**

## Read this first, every session

| file | what it settles |
|---|---|
| `CLAUDE.md` | this file — the mental model, the claims, the doctrine, the rules |
| `PLAN.md` | the four phases and what closes each |
| `docs/SCENARIO.md` | the operator, the decision paths, the data, what makes it hard |
| `docs/DECISIONS.md` | scope · technology · method · deliberately deferred |
| `docs/REGULATORY.md` | the legal posture, argued with citations and verification dates |
| `docs/DAY-ONE.md` | manual work with no API, recorded rather than silently done |

**Vocabulary — three words that must not blur.** "Offline" carries two unrelated meanings in this
domain and mixing them causes real bugs, so it is reserved here for exactly one of them.

| word | means |
|---|---|
| **local** | on a laptop or in CI, with no cloud account and no credentials |
| **on the estate** | against the deployed workspace |
| **offline / online** | **only** the batch-versus-serving sense: an offline feature store, an online feature store |

---

## What this system does (the mental model)

A supermarket chain of ~1,200 stores and ~40,000 SKUs takes roughly 2.4 million pricing
decisions a day. Holdout takes them. That is not the interesting part — others do that too.

**The interesting part is that it proves whether those decisions made money.** A share of the
estate is deliberately held back, locked from the start, and the comparison against it is the
only source of any claim about value. Where the comparison cannot be trusted, the system
produces **no number and a reason code**.

The problem it solves is not "make better decisions". It is the slide that says *"AI delivered
€4.2M"* that nobody in the room can check.

> **Holdout** — the experimental term (the control group, the holdout stores), and the plain
> English word: *to keep something back*. Both meanings are the project.

**The scenario is 1,200 stores. The corpus is 100.** Roughly 100 stores across three fresh
categories over eight months — about 36M POS lines, a few GB of Parquet. The scale of the corpus is
a cost decision and nothing else: **claim 2 does not get stronger with 1,200 stores**, it gets
stronger with 200 seeds and six adversarial worlds, which run local and cost nothing. Where a
figure depends on corpus size it is reported as such, never extrapolated to the full estate.

### The real envelope — what a supermarket may actually do

The system does **not** change prices wherever and whenever it likes. Encoding the envelope so it
cannot be violated **is** the engineering.

| action | allowed | reality |
|---|---|---|
| markdown on expiring fresh | **yes** | per store, per day, already automated in real chains |
| base price change | with conditions | central, weekly, by pricing zone — never per store per hour |
| margin cap on staple goods | **limit** | Greece: the state has imposed a gross-margin cap by emergency legislation three times since 2021, and between 2021 and 2022 it changed not its numbers but its **shape** — margin per unit against a past date, then margin per product code against a full-year average. **The list is a versioned contract with effective dates.** |
| announcing a reduction | **limit** | the "prior price" is bound by Directive 98/6/EC as amended |
| free dynamic pricing everywhere | **no** | ESL penetration is ~30% of large European retailers; display rules are tightening |
| personalised price per customer | **no** | structurally impossible: the decision key has no customer dimension |

### Three decisions, one stream — only one actuates itself

| decision | horizon | actuation | why |
|---|---|---|---|
| markdown on expiring fresh | minutes | **automatic — the primary path** | physical consequence; high frequency, so an experiment reaches power in days |
| base price by zone | weeks | **proposal to a human** | **no actuation path exists**; "anything with significant effect waits for a human" is architecture, not a policy statement |
| joint plan with a supplier | quarters | Clean Room | the alternative is exchanging commercially sensitive data |

### The boundary this system is built around

| Statistical models own | Deterministic code owns |
|---|---|
| Forecasting demand at each candidate price and time | Every price written to a shelf |
| Ranking which candidates are worth acting on | Whether an experiment design is valid |
| **Supplying the judgment fields of an experiment design** | Which arm a unit belongs to |
| Drafting the explanation for a human | The margin / waste / uplift arithmetic, and the decision to refuse |

The test, for every row: **is there exactly one correct answer here?** Choosing the unit of
randomisation has no single correct answer — model territory. Whether the resulting design has
the power it claims has exactly one — code.

**An uplift number produced without a valid holdout is a build failure.** That is the project,
in one sentence.

---

## The seven claims

Everything here exists to make one of these provable **local** — in CI or on a laptop, with no
workspace and no credentials. If a change does not serve one of them, question it.

| # | Claim | Proved by |
|---|---|---|
| **1** | **No price reaches a shelf without the guardrail set.** The actuation type cannot be constructed without a guardrail certificate. The envelope — floor, regulated basket, prior-price rule, max daily delta — is a versioned contract with effective dates. *Trap: a planter reading the same contract as the detector is one function agreeing with itself → the gates are attacked from an independent corpus of real price lists.* | `evals/guardrail/` |
| **2** | **No uplift without a valid holdout — and on an A/A split the system reports a significant effect no more often than its declared α**, across K seeds and six adversarial worlds, including one where the correct answer is "yes, there was an effect". *Trap: a simulator generating data from the process the estimator assumes is the estimator agreeing with itself → the estimator is **design-based**, valid under any process, and the worlds violate every assumption a model-based estimator would have made.* **Not claimed: observational uplift where randomisation is impossible.** | `evals/uplift/` |
| **3** | **The holdout is neither erased nor chosen after the fact.** Assignment from a committed seed, exactly reproducible. *The one door with no key.* | `evals/assignment/` |
| **4** | **A stock-out is never read as zero demand.** *Trap: a simulator that generates censoring with the model that corrects it → validated on a held-out segment with full shelf availability.* | `evals/censoring/` |
| **5** | **One definition, three mechanisms, the same number.** The source of truth is the contract in this repository, compiled into a Delta view, the agent's tool definition and the experiment readout. Compared as integers, no tolerance. *Trap: two consumers calling the same function prove nothing → three genuinely different mechanisms, sharing only the definition.* | `evals/definition/` |
| **6** | **The design engine refuses an invalid design regardless of where the judgment came from** — human, declared policy, or model. When the source is a model: N designs proposed, M refused, and K of those would have produced a confidently wrong number. *Trap: an LLM judge in the same family is a correlated critic → **the judge never rules on validity**; code does. The judge rules only on design quality.* | `evals/design/` |
| **7** | **A decision that targets a person is structurally impossible.** The decision key has no customer dimension, and a test goes red if one appears. | `evals/oversight/` |

**Claim 2 is the one that separates this from a demo. Claim 6 is the one nobody builds.**

### How claim 2 is proved

Five artefacts, all provable local.

**The generator** (`corpus/world/`) produces a synthetic chain — baseline demand by store, category,
hour, weather and season; a non-linear price response with reference-price memory; cross-price
effects between substitutes; stock and per-item expiry; sales censored by availability; ESL
acknowledgements that sometimes fail. It **injects a known effect on behaviour**, not on the metric.

**Six adversarial worlds**, each violating a different assumption:

| | the world | the correct behaviour |
|---|---|---|
| W1 | pure noise, true effect zero | no significant uplift, at a rate ≤ α |
| W2 | real effect + interference between neighbouring stores | **detect and refuse**, never estimate |
| W3 | real effect + exposure fails on 30% of treated units | exposure-adjust or refuse — never silently dilute |
| W4 | an effect that decays (novelty) | report the declared window's average, not the first week extrapolated |
| W5 | heavy-tailed baskets — variance far above what the power calculation assumed | the power check fails, or the interval is honestly wide |
| W6 | **everything works, a real effect is present** | **produce the number.** No refusal |

**W6 matters as much as W1.** A system that refuses everything passes every other world and is
worthless. The **false-refusal rate is published beside the false-positive rate.**

**The A/A harness.** Both arms get the same policy — nothing is applied. The same data, re-drawn
under K = 200 seeds. Every draw runs the **whole system** — assignment, exposure collection, the
four validity checks, the readout — not just the estimator, because a formula is not a system.
The rate at which a "significant" uplift is reported must be ≤ the declared α, tested as a
one-sided binomial at a stated level rather than eyeballed. **It needs no ground truth at all:
empty is empty**, so no one can argue the simulation was rigged.

**Two barriers.** No module under `corpus/world/` imports anything from `src/holdout/`, enforced
by a test — if the generator and the estimator shared a "compute margin" function, a bug in it
would cancel out and both would agree on a wrong number. The only thing they share is the
*schema* from `contracts/`, never logic. And the injected truth lives in a sealed file the
harness opens **only after** the readout has been written.

**An independent measurement of truth.** The generator injects behaviour ("three more units per
store"), so the true effect *on the metric* must be computed — by a deliberately slow, separately
written reference implementation that loops over every event in Python, while the production path
is SQL through dbt. Two genuinely different implementations must agree. **That reference
implementation doubles as a fourth, independent check of claim 5.**

**What is published** — numbers, not a green tick: the false-positive rate on A/A against the
declared α; per-world correctness; the false-refusal rate on W6; estimator bias; and **CI
coverage** — over K runs of W6 a 95% interval must contain the truth about 95% of the time.

**What stays uncovered, honestly.** The six worlds are the six failure modes we thought of. But
the estimator's validity does not come from passing them: a difference of means over randomly
assigned units is unbiased **under any data-generating process** — that is a theorem, not our
opinion. The worlds do not test the subtraction; they test whether the machinery around it —
assignment, exposure, the checks — preserves that validity. **The answer to "your simulator is
rigged" is that validity comes from the lottery, not from the simulator.**

---

## The doctrine — what happens when it goes wrong

1. **The safe state is asymmetric, and declared per decision path.** For an expiring product,
   silence is not safe — the product is thrown away — so the safe state is the **deterministic
   markdown ladder**. For a price increase, silence *is* safe, so the safe state is no action.
   No path may inherit the other's answer.
2. **A fallback is visible all the way to the end.** A price produced by the ladder carries that
   marker to the label, the P&L and the experiment. A fallback that looks like a model decision
   is worse than an outage, because it is silent and it teaches someone to trust it.
3. **Nothing is invented.** Not an expiry date derived from a rule, not a cost that is stale, not
   a transaction id hashed from the payload. A default is a lie with a plausible shape.
4. **A correction never erases what was previously stated.** Late data restates; it does not
   overwrite. The prior value, the reason and the delta are recoverable.
5. **Nothing approves itself.** No model, no pipeline, no agent may approve a promotion, grant an
   exception, or classify its own design as valid.
6. **Exceptions expire.** On expiry the finding returns and CI goes red again.
7. **One door has no key.** No unit changes arm after its first observation — not by anyone,
   including an approver. From the moment it can, every number the system produces becomes
   unfalsifiable. Having exactly one unopenable door is what keeps the other six honest.

---

## Non-negotiable engineering rules

**Framework-free core.** All domain logic in `src/holdout/core/` as pure functions over plain
data, importing no cloud SDK and no engine. Adapters are thin. This is the only way the claims
are provable local.

**No claim depends on a non-GA surface.** A preview surface may only add a second, independent
proof of something already proved on GA. `make preview-audit` reads the declared inventory of
preview surfaces and fails when any claim's proof path touches one.

**Local is the default.** Full suite, every eval, every gate, `terraform validate`, with no
account. Cloud is where proof is captured, not where logic is validated — which is a statement
about *logic*, not about *runs*: the training code is proved local, the training run that produces
the deployed model happens on the estate, where a real one would.

**IaC only.** No console actions, ever. Day-one manual work with no API goes in `docs/DAY-ONE.md`.

**Bootstrap is local, everything else is CI.** A layer that can be applied from a laptop drifts.

**No long-lived credentials.** OIDC for CI, service principals for services, `gitleaks` on push.

---

## The data flow

```
sources → bronze (10) → silver (5) → gold (4 families) → decision → experiment
```

### Sources and ingestion

| source | via | why |
|---|---|---|
| POS lines, scale labels, **ESL acknowledgements** | **Zerobus Ingest** (GA) | events from every store, no message bus to operate — **the live day only** |
| ERP tables, competitor prices | **Lakeflow Connect** (GA) | pull from a database; no custom ingestion code to maintain |
| **eight months of transaction history** | **bulk load from files on S3** | streaming eight months through Zerobus would be slow and costly, and no real deployment does it: backfill from files, then stream |

The **ESL acknowledgement is a first-class source, not a log.** It is the only evidence that a
price reached the shelf. Without it every experiment measures intentions instead of actions.

The ERP is a **real Postgres** stood up by the `sources` layer, seeded with eight months of
history in `backfill` and then **driven** during `run` — costs change mid-day, a product enters the
regulated basket, a supplier term changes retroactively, a column is added. A seeded-and-static
database gives incremental ingestion nothing to do and proves nothing.

### Bronze — one table per source, in the source's shape

```
Zerobus:            pos_lines · scale_labels · esl_acks
Lakeflow Connect:   product_master · cost_ledger · supplier_terms ·
                    regulated_basket · store_master · planogram · competitor_prices
```

Nothing is transformed at ingestion. Every record carries **both** its event time and its
arrival time. No source is merged with another here — merging at bronze destroys the ability to
reprocess one independently.

### Silver — one table per question

```
sales · shelf_state · price_displayed · reference · quarantine
```

Not one-to-one with bronze: `reference` collapses six bronze tables into one **as-of queryable**
dimension; `pos_lines` feeds two silver tables, because a sale is both revenue and an inventory
movement.

- **As-of joins, never current.** A sale at 14:00 joins to the cost *as it was known at 14:00*.
  Joining to the current cost table silently rewrites every historical margin.
- **The displayed price comes from the ESL ack, never from the decision.** `price_decided` and
  `price_displayed` are separate columns and they differ.
- **Deduplication uses a business key, never a hash of the payload.** The same receipt line
  delivered twice is one event; two identical baskets in the same second at the same till are
  two. That needs a real `transaction_id` from the source. **If the POS does not supply one, it
  is declared as a known limit — it is not invented.**
- **Quarantine, not drop.** The size of the quarantine table is a health metric.
- **Stock-out marking happens here**, because only here are the inventory movements available.

### Gold — four families

```
A · business facts          decision_economics · waste · store_day
B · features                demand_features   (point-in-time correct)
C · experiment              experiment_assignment · exposure · outcomes · readout
D · the decision record     decisions          (immutable, written at decision time)
```

- **Point-in-time correctness is mandatory and deliberately not claimed.** A feature used in
  training must equal the value that was available at decision time; computing it against today's
  tables leaks the future into training. `watermark` already proves this as a claim, and
  re-claiming it in a second repository is padding. It is implemented correctly, tested, and
  stated in one line.
- **Features and metrics never mix.** A metric is governed and stable; a feature is
  point-in-time correct and free to change. Training on a business metric means that the day the
  metric is redefined, the model has learned something that no longer exists.
- **The assignment table is written before the period opens**, from the committed seed, and is
  then read-only.
- **The readout pins a Delta version.** Without it, re-running last month's readout returns a
  different number as late data arrives.

### Engines

| layer | engine | why |
|---|---|---|
| bronze → silver | **Spark Declarative Pipelines** | streaming, out-of-order, expectations and quarantine are native |
| silver → gold | **dbt** | many analytical models, tests, docs, per-model ownership; the metric contract compiles into exactly dbt's shape |

Two tools, split at a declared boundary — chosen per problem, not per preference.

### Lakebase vs the lakehouse — two stores, two jobs

| | Lakebase (Postgres) | Lakehouse (Delta) |
|---|---|---|
| answers | "what do I do now" | "what happened and what did I learn" |
| holds | only the current operational state | everything, forever |
| needs | ms point reads, a `UNIQUE` constraint, real transactions | large scans, versions, time travel |

Two flows, in opposite directions: **decisions** go Lakebase → lakehouse; **features** go
lakehouse → Lakebase. It is not a mirror.

---

## The decision path (seconds)

```
trigger → freshness gate → which arm? → features → model → selection
   → guardrails → decision record → Lakebase → ESL → ack → bronze
```

- **Four things fire a decision**: entering the decision window before expiry, a ladder step, an
  abrupt inventory change, or a cost change in the ERP that moved the floor. **A decision is
  idempotent per (SKU, store, ladder step)** — re-running never produces a second price change.
- The **freshness gate runs before the model is called at all**. Stale inputs go straight to the
  ladder, marked.
- **Holdout does not mean "nothing"** — it means the *existing* policy. Comparing against
  abandonment would inflate every uplift.
- The model returns a **scenario table**, never a price. Code picks the scenario by arithmetic.
- The model is applied **inside the pipeline** from a registered MLflow artifact. The endpoint in
  the `serving` layer exists only for the interactive path; both load the same pinned version and
  a test compares them.
- **The guardrail set is a type, not a check**: `ProposedPrice → CertifiedPrice | Refusal`, and
  the function that pushes to the ESL accepts only `CertifiedPrice`.
- The decision record is written **before** the price is dispatched.

Three outcomes: **normal** (model, certified) · **fallback** (ladder, marked) · **refusal** (no
legal price sells the item — donation or disposal, which is a correct output, not an error).

---

## The two AI systems

| | demand model | agent |
|---|---|---|
| ours? | yes, we train it | no, never trained |
| runs | ~2.4M times/day, inside the pipeline | a handful of times a week |
| input / output | numbers → numbers | text + context → the judgment fields of a design |
| versioned artifact | weights | prompt + tools + context |
| gate | calibration, per-segment regression, model card | the design evals |
| approver | a named human | a named human |

They never call each other. **No LLM is anywhere near the decision path** — too slow, too
expensive at 2.4M calls a day, and non-deterministic.

### Training — the code is proved local, the run happens on the estate

The training *logic* — the time split, the censoring correction, the calibration gate, the
promotion gates — is pure code and is proved local against a small corpus. **The run that produces
the model actually used is executed on the estate, during `backfill`, on eight months of loaded
history**, because that is what a real deployment does and because the data is there.

Training on history that ends before the day that is then driven live means **the driven day is
naturally held out** — it is the future relative to training. The time split falls out of the
sequence instead of being imposed.

Time-based split, never random. **Deliberate price randomisation** on a small share of decisions,
because the history was generated by our own policy and contains almost no evidence about prices
we never chose. Censoring corrected (claim 4). **Calibration is gated above RMSE**: a model that
is systematically optimistic by 20% sets systematically low prices, and every individual price
still passes every guardrail. Shadow runs on a Lakebase branch catch breakage, **not value** —
value is only ever measured by the holdout experiment.

---

## The design engine — one form, three sources

The nine fields a human, a declared policy, or the agent may fill:

```yaml
hypothesis:      one precise sentence — what changes, on what, measured by what
intervention:    { treatment: policy@vN, control: policy@vM }
scope:           which categories, products, stores
primary_metric:  from the metric contract — a closed list, never free text
unit:            store | store_week | store_category | region
mde:             the smallest difference worth detecting, declared in advance
max_duration:    business constraint          # the agent never fills this
exclusions:      store ids with reasons
decision_rule:   what we will do with each outcome  # the agent never fills this
filled_by:       agent | human:<name> | policy:<name>
```

**The agent proposes how we will find out. Never what we will do once we know.**

The engine does not know and does not care who filled the form. Same checks, same refusals, same
experiment. All three sources are first-class.

### The core's three moments

**1 · On receiving the form — *can this experiment exist?***
Computes historical variance, required sample, automatic exclusions (neighbours under 1 km,
holidays, units already committed elsewhere), then feasibility against `max_duration` and holdout
capacity. Either a **refusal that names what would fix it**, or: generate the committed seed,
write the assignment, check pre-period balance, lock the table read-only.

**Balancing is re-randomisation, and the analysis must account for it.** Candidate assignments
are drawn from the committed seed and screened on **pre-period covariates only** — category
revenue over the previous 8 weeks, store format and size, waste rate, pricing zone. Selecting on
anything measured inside the comparison window would be using the same data twice and would bias
the estimate toward zero. Because the space of admissible assignments is restricted, the ordinary
confidence interval is wrong — it assumes simple randomisation and comes out falsely wide. The
inference is therefore a **permutation test under the same restriction**, or an estimate adjusted
for the covariates that were balanced on. The A/A harness catches a violation here as CI coverage
drifting above the nominal level, so the check exists in both places.

**2 · While it runs — *is it running as declared?***
Routes each decision by arm. **Blocks any reading of results before the declared end.** Blocks any
change to the assignment, by anyone. Collects exposure.

**3 · On close — *may the result be stated?***
Four checks, all mandatory: balance · exposure · contamination · power. All pass → uplift as a
difference of means, with a confidence interval and a pinned data version. Any fail → a reason
code and no number. Then the `decision_rule` declared at the start is applied.

The core never chooses what to test and never decides what to do about the answer. It decides
only **what may be claimed**.

---

## The contract layer

`contracts/` is the source of truth, versioned in this repository, and it is what claims 1, 5 and
6 rest on. Four families, none of which is a vendor feature.

### `metrics/` — one definition, four consumers

```yaml
id:             category_margin_per_store_week
version:        3
effective_from: 2026-03-01
grain:          [store_id, iso_week, category]
unit:           EUR
rounding:       { mode: half_even, decimals: 2 }
expression: |
  sum(s.qty * s.price_paid)
  - sum(s.qty * r.unit_cost_as_of)
  - sum(w.qty * r.unit_cost_as_of)
sources: [gold.decision_economics, gold.waste]
```

Compiles into a dbt model, a SQL function, **the agent's tool definition** (the agent never
writes SQL) and the readout query.

**`rounding` is part of the contract, not a detail.** If two consumers round differently, claim 5
fails over a one-cent difference for a stupid reason.

### `guardrails/` — the envelope, with effective windows

```
floor.yaml · regulated_basket.yaml · prior_price.yaml · max_delta.yaml · frozen_categories.yaml
```

The regulated basket carries **windows**, because the Greek cap changed shape between 2021 and
2022 and no single "current cap" field could ever have expressed both regimes. A decision taken in
April is judged by April's rule, permanently, even after the law changes again. The verified
history, with citations, is in `docs/REGULATORY.md`.

**Doctrine rule 3 bites hardest here.** A numeric `value` in a guardrail contract requires a
`source` and a verification date. **`value` without `source` is a build failure.**

### `policies/` — what treatment and control actually are

`ladder_policy@vN` and **every predecessor**. No policy version is ever deleted: the meaning of
last year's experiment depends on exactly what its control was. Delete v3 and the result of the
experiment that used it becomes retroactively uninterpretable.

### `design/` — the form, and `vocabularies/` — the refusal codes

`design/form.schema.yaml` (the nine fields, with closed lists) and `design/balance_covariates.yaml`.

**`vocabularies/reason_codes.yaml` is deliberately not in `design/`**, because the system refuses at
three moments and only one of them is a design. One file, three sections, and a test that no code
appears in two of them: a refusal that could be counted under two moments could be counted twice.

**The balance covariates are fixed here, not chosen per experiment.** If each experiment could
pick which characteristics to balance on, that would be a new way to fish — try combinations until
a draw comes out flattering. Fixing the list removes the degree of freedom, exactly as the closed
reason codes and the pre-declared `decision_rule` do. **Anything that can be chosen after the fact
will be chosen after the fact.**

The refusal vocabulary:

```
at_decision: CATEGORY_FROZEN · COST_STALE · BELOW_ABSOLUTE_FLOOR · BELOW_MARGIN_FLOOR ·
             NO_PRICE_SATISFIES_EVERY_GUARDRAIL · MARKDOWN_EXCEEDS_MAX_DEPTH ·
             DAILY_CHANGE_BUDGET_EXHAUSTED · BASE_PRICE_MOVE_EXCEEDS_WEEKLY_LIMIT ·
             MARGIN_CAP_EXCEEDED · MARGIN_CAP_BASIS_UNEVALUABLE ·
             PRIOR_PRICE_NOT_ESTABLISHED · INPUT_NOT_AVAILABLE
at_design:   UNDERPOWERED_FOR_DURATION · UNDERPOWERED_FOR_CAPACITY ·
             UNIT_GUARANTEES_INTERFERENCE · STOPPING_RULE_PERMITS_PEEKING ·
             EXCLUSIONS_DEFINED_POST_HOC · METRIC_NOT_IN_CONTRACT · UNITS_ALREADY_COMMITTED
at_readout:  IMBALANCED_PRE_PERIOD · EXPOSURE_BELOW_THRESHOLD ·
             CONTAMINATED_ASSIGNMENT · POWER_NOT_REACHED
```

**`at_decision` names which guardrail refused a price**, and it is what claim 1 counts. A refusal is
a correct output, not an error: when no legal price sells the item the answer is donation or
disposal. `NO_PRICE_SATISFIES_EVERY_GUARDRAIL` is arithmetic — the legal range is empty — and says
nothing about demand, which is the model's territory and not the envelope's.

**Closed, because a free-text reason cannot be counted, tested or gated.** Claim 6's "N proposed,
M refused, K would have been wrong" exists only because the reasons are enumerable. Adding a code
is a code change with a test.

### The six rules

1. Every contract is versioned and **never deleted**.
2. Every number that comes from outside carries a citation and a verification date.
3. A contract **compiles**; it is never interpreted by hand-written code in two places.
4. A change that affects past values implies a **restatement** (doctrine 4).
5. **No vendor feature is a source of truth.** Unity Catalog metric views are a *fourth consumer*
   of the metric contract — provable when available, removable when the API churns.
6. The closed vocabularies are closed.

### `make contracts`

Validates every contract against its schema, recompiles every consumer, and **goes red** when a
generated artefact is stale or when a `value` has no `source`. It is not enough that the
definition exists — it must be provable that everyone is using it, now.

---

## Repository layout

```
src/holdout/core/      pure functions — no SDK, no engine
  guardrails/          the envelope and the certificate type
  pricing/             scenario selection arithmetic
  design/              the nine-field form, feasibility, refusal
  experiment/          assignment, the four validity checks, the estimator
  ladder/              the deterministic fallback
src/holdout/adapters/  thin cloud callers
contracts/             the source of truth (above)
corpus/world/          the six adversarial worlds — NO import path to core/
corpus/real/           a public retail dataset, distribution realism only
evals/                 one directory per claim
pipelines/ingest/      Zerobus driver · Lakeflow Connect · the S3 bulk load
pipelines/silver/      Spark Declarative Pipelines
pipelines/gold/        dbt
pipelines/ml/          training, evaluation, promotion
infra/                 bootstrap · foundation · sources · lakehouse · pipelines · ml · serving
experiments/           one YAML per experiment, in git, with its full history
docs/
```

---

## The visible surface

**Databricks AI/BI dashboards, not Grafana.** AI/BI is native and GA, queries Unity Catalog
directly so governance continues inside the dashboard, is backed by a serverless SQL warehouse
with auto-stop, and has a Terraform resource. Grafana would need hosting, a JDBC data source, its
own auth and its own bill, **for no additional proof**. It wins where you need sub-minute refresh
with alerting; the decision monitor does not. Declining a service that does not earn its place is
itself a signal.

**No dashboard is built from a console.** They are `databricks_dashboard` resources in the
`lakehouse` layer. The IaC rule applies to everything that will be photographed.

### Dashboard 1 — experiment readout

The project's central image. Four check tiles across the top (balance · exposure · contamination ·
power), each green or red with its figure beneath. Then the hero counter: either the uplift with
its confidence interval, or **the refusal and its reason code, at the same size**. A line chart of
treatment against control by week with the intervention start marked, so the two arms are visibly
together before and apart after. A histogram of the per-store effect, so it is clear that one store
is not dragging the mean. A table of the locked design — the nine fields, `filled_by`, the seed,
the pinned data version.

**The refused version of this screen is the single most important screenshot in the project.**

### Dashboard 2 — decision monitor

**Required by doctrine rule 2**, not optional: a fallback is visible to the actuator, the record
*and the dashboard*. Without this screen, rule 2 is proved nowhere.

A counter row — decisions today, % model, **% fallback**, % refused. Then the load-bearing chart: a
**stacked area over the day of model / fallback / refusal**, so when a store drops offline the
amber band visibly swells. A bar chart of which guardrails fired. A line with a drawn ±5% band for
seven-day calibration drift, where leaving the band is what asks for retraining. A heatmap of hour
against category by markdown depth, showing the ladder working. A table of recent refusals with
their reason codes.

**Both dashboards consume the metric contract**, so they are part of claim 5's evidence rather than
decoration on top of it.

### Surfaces that cost nothing

Unity Catalog **lineage** already draws the graph from `esl_acks` to `experiment_readout` — free,
native, and the best governance shot available. A **notebook** carries the live question and the
what-if, which is how a data scientist actually works. And the **terminal** carries the figures
that matter most — `9/200 = 4.5%`, `gate-proof`, `200 / 47 / 12`. Numbers that hurt read better in
a monospace font, which is why `manifest` shows `34/34` in a terminal and not in a chart.

**Genie** over the same tables comes free and answers the backward-looking questions — the
commodity half, deliberately not where the work went.

---

## The estate — cloud, layers, order

**Databricks on AWS.** The account, the OIDC pattern, SSM for cross-layer publishing and the
Terraform muscle memory already exist across three projects. A second cloud would divide attention
without proving anything more about Databricks.

Seven layers. Each earns its place by passing at least two of: **different lifetime · its own
blast radius · consumes only from below · expensive or slow to apply.**

| layer | applied | holds |
|---|---|---|
| `bootstrap` | **locally, once** | state bucket + KMS, OIDC provider, deploy role, **the budget and its alerts**, published parameters |
| `foundation` | `deploy` | VPC, keys, S3 zones, the workspace, metastore attachment, **TTL reaper** |
| `sources` | `deploy` | **RDS PostgreSQL playing the ERP** + private networking |
| `lakehouse` | `deploy` | catalogs, schemas, grants, external locations, Lakebase, the two AI/BI dashboards |
| `pipelines` | `deploy` | SDP pipelines, dbt jobs, Lakeflow Jobs, Zerobus endpoints, bulk-load jobs |
| `ml` | `deploy` | training job, evaluation, promotion gates, MLflow — **no endpoint** |
| `serving` | **`backfill`, at the end** | the model serving endpoint, the agent runtime, the AI Gateway and its tool registry |

`pipelines` is split from `lakehouse` because pipelines are edited constantly and no routine edit
should put an `apply` near catalogs and grants. **`serving` is split from `ml` because it is
applied at a different moment**: an endpoint cannot point at a model version that does not exist
yet, and a version exists only after `backfill` has trained one. The agent runtime lives there too
— it is the same lifetime, the same blast radius and the same billing shape, and two layers that
always deploy together and never independently are one layer wearing two names.

**The RDS is the smallest instance that works, Single-AZ, in a private subnet, with its password
generated into Secrets Manager.** Single-AZ is a declared cost decision for an estate that lives
one day, not an oversight. **The network path from the workspace to RDS that Lakeflow Connect's
database connectors need is verified before phase 3, not inside it** — see `docs/DAY-ONE.md`.

**Cross-layer references go `outputs` → SSM parameter → `data`. Never a remote state read** — that
creates hidden coupling and destroys the isolation the layers exist for.

### The order the estate comes up in

```
deploy     apply foundation · sources · lakehouse · pipelines · ml
           no model, no endpoint

backfill   eight months of history:
             ERP master data  → Lakeflow Connect from RDS
             transaction history → files on S3, bulk-loaded into bronze
               (streaming eight months through Zerobus would be slow, costly,
                and nobody does it; real deployments backfill then stream)
           → silver → gold
           → train on the estate → gates → register a version
           → apply serving          <- only now can an endpoint exist

run        one live day through Zerobus, with lateness and duplicates
           decisions routed by arm · exposure collected
           experiment A produces a number · experiment B must refuse
           a live question answered at the endpoint
           then ask the account whether it behaved

destroy    reverse order, then ask the account what is left
```

This is infrastructure → data and model → serving: the order every real system comes up in, not a
workaround. The day driven in `run` is **after** the history trained on, so it is held out by
construction.

**What survives a teardown**: the state bucket and its access-log bucket, the state KMS key, the
SSM parameters and the deploy role. Nothing else — verified by asking the account, never by
reading a workflow's exit code.

### Five workflows

| | runs | does |
|---|---|---|
| `ci` | every push | the suite, every eval, `gate-proof`, `make contracts`, `make preview-audit`, `terraform validate` |
| `deploy` | dispatch | the whole suite **first**, then apply five layers |
| `backfill` | dispatch | load history, build silver and gold, train, gate, register, apply `serving` |
| `run` | dispatch | drive the day, run both experiments, answer a live question, assert against the account |
| `destroy` | dispatch | takes a target: `serving` (the expensive layer, ~2 min) or `all` (reverse order), then asks the account |

**The suite runs upstream of every apply.** Nothing reaches AWS until all of it is green.

---

## Cost controls — always active

- Serverless only. **No always-on cluster anywhere in the design.**
- `serving` is the most expensive layer and the only one that bills while idle. It is applied
  **last** and destroyed **first**.
- Cost is a **model** until a bill exists, and is said that way every time it is reported.

### What a cycle costs, modelled

Serverless everywhere, so there is **no separate EC2 line** — infrastructure is bundled into the
serverless DBU rate. The "you pay Databricks and you pay AWS" trap applies to classic compute,
which this design does not use.

One full cycle is roughly six hours of estate: `deploy` ~40 min, `backfill` ~1.5 h, `run` ~2 h,
console time, `destroy` ~15 min.

| | modelled |
|---|---|
| jobs compute — silver, gold, training | 10 – 30 USD |
| serverless SQL for dbt and queries | 5 – 15 USD |
| model serving, small CPU endpoint | 1 – 5 USD |
| Lakebase | 2 – 8 USD |
| RDS `db.t4g.small`, six hours | ~0.20 USD |
| S3 and transfer | 1 – 3 USD |
| **one cycle** | **~20 – 60 USD** |

**The real number is not one cycle.** It will not come out clean the first time — budget for **five
to ten cycles**, so **100 – 600 USD** in total. These are list-price estimates, not a verified
bill; the figure that reaches the README comes from an actual invoice.

### The budget posture — a guardrail, not a brake

**1,000 USD**, with **alerts at 50 / 80 / 100%** and **no stop action at any of them**. A budget
that halts a run mid-way costs more than it saves: the estate is left half-standing, the evidence
is unreadable and the cycle must be repeated. A stop action exists **only at 150%** — at 1,500 USD
against a 600 USD model, something has genuinely gone wrong and stopping is the correct response.

**Enforcement lives in the TTL reaper, not in the budget.** The budget's job is to tell you, early
and loudly, that the model was wrong.

### The teardown guarantee does not live in a workflow

A workflow step is a convenience, not a guarantee: the runner can die, the network can drop, the
job can be cancelled. Three independent levels, in order of trust:

| | what | why |
|---|---|---|
| **1** | **TTL reaper** in `foundation` — a scheduled job that destroys anything tagged and older than N hours, whatever happened | the real net. Depends on no workflow's control flow |
| **2** | **Budget policy** in `bootstrap`, applied before anything can bill | catches what escapes level 1 |
| **3** | `destroy` — **always a deliberate dispatch**, never automatic | convenience |

**`destroy` is never automatic, on success or on failure.** On failure, tearing down destroys the
evidence — the Lakebase rows, the Delta state, the endpoint's configuration — and re-deploying to
debug costs forty minutes and real money. On success, the estate is exactly what console
screenshots and video need, and this project's promo material is screen recordings of a live
workspace. An automatic teardown adds **no guarantee that level 1 does not already provide**, and
costs the one thing that cannot be regenerated: time at the keyboard with a live system.

**`destroy` takes a target.** `destroy serving` removes only the expensive layer — the endpoint and
the agent runtime — in about two minutes, leaving the lakehouse standing to browse at almost no
cost. `destroy all` takes everything in reverse order. `run` ends by printing what is standing,
when the reaper will collect it, and what to dispatch.

---

## Git workflow

**Never commit to `main`.** One branch per closed piece of work — which means **one branch per
session, not one per commit**. Inside a session, commit freely and often: those are restore points.
At the end, **squash-merge**, so `main`'s history is one commit per closed piece.

This is not ceremony for a solo repository. Three reasons, and all of them are real here:

- **The repository will be public and `main`'s log is read.** It should say
  `contracts: the metric schema and the guardrail envelope`, not `wip` three hundred times. The
  history is part of the portfolio.
- **It makes the gate structural.** On a branch, the suite runs *before* anything lands. Pushed
  straight to `main` it runs afterwards, and a check that runs afterwards is a notification, not a
  gate.
- **The fresh-context reviewer needs an object to review.** A pull request diff is exactly that.

**`main` is protected and CI must be green to merge.** A repository with a protected default
branch and required checks says something on its own.

**No exceptions for small fixes.** "It's just a typo" is how `main` breaks.

**Branch names name the work, not the ticket**: `contracts/metric-schema`,
`core/design-engine`, `corpus/adversarial-worlds`, `evals/aa-harness`.

**The workflows that spend money dispatch from `main` only.** `deploy`, `backfill`, `run` and
`destroy` never run from an unreviewed branch.

**This repository is public. Every commit is a publication — at the moment of the commit, not at
the moment of the announcement.** The protection is `gitleaks` as a required check, not the
visibility setting, and it is already in place.

**Evidence is scrubbed before it is committed.** Logs, assertion output and screenshots from `run`
are never committed raw: screenshots go through `aws-mask`, and logs are filtered of workspace
URLs and account identifiers first. This rule would be needed regardless of repository
visibility — that evidence ends up in the README and the article, which are public either way.

**Deferring is not forgetting.** Anything deliberately deferred names, in `docs/DECISIONS.md`, the
condition that will unlock it. An item with no unlock condition is not deferred; it is forgotten.

`PLAN.md` is updated at the end of every session: what closed, what is open.

---

## Oversight — four levels

Many small sessions carry one real risk: **conceptual drift**. Each session is locally correct,
its tests pass, its piece closes — and after five of them the project has lost its spine with
nothing red anywhere. The estimator quietly becomes model-based because it "gave better results".
The generator starts sharing assumptions with `core/`, so the import test still passes while the
independence is gone. A gate is "fixed" so it stops firing so often. Code appears that serves no
claim.

| | when | catches | who |
|---|---|---|---|
| **1 · CI** | every PR | mechanical drift — `make claim-N`, `make contracts`, `make preview-audit`, `gate-proof` | automatic |
| **2 · Reviewer** | every PR | the diff against `PLAN.md` and the claims | a subagent in **fresh context** |
| **3 · Integration** | **at every phase boundary** | conceptual drift | a dedicated session |
| **4 · The author** | always | is this still worth building? | a human, and never an agent |

Level 1 is why the claims are Makefile targets: a session cannot merge something that breaks a
claim, because the gate is structural rather than advisory.

**Level 3 builds nothing.** It reads the whole repository against this file and asks what CI
cannot:

- Does any claim's proof rest on something that has quietly become a tautology?
- Has any gate stopped biting — and for what reason?
- Does the code still say what `CLAUDE.md` says it says?
- Is there code that serves no claim?
- Has a claim landed on a preview surface?
- Is there still **exactly one** door with no key — not zero, not three?

It is scheduled, not remembered: at the end of every phase, without exception.

---

## Before any change — checklist

- Which of the seven claims does this serve?
- Is there exactly one correct answer here? Then it is code, not a model.
- Can it be validated with no cloud account? If not, why not?
- Does it put a claim on a non-GA surface?
- If it is a gate: is there a `gate-proof` mutation that proves it bites?
- If it touches a contract: does the change imply a restatement?
- If it states a legal fact: which article, which instrument, verified when?
- If the pattern comes from another project in this portfolio: **what problem did it solve there,
  and do we actually have that problem?** A pattern copied with the solution to a problem you do
  not have is cost with no benefit — it has already happened twice here.
