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
a cost decision and nothing else: **claim 2 does not get stronger with a larger estate**, it gets
stronger with 200 seeds and six adversarial worlds, which run local and cost nothing. Where a
figure depends on corpus size it is reported as such, never extrapolated to the full estate.

> **The size that decides whether anything is provable is the surviving roster, not the store
> count. Restated 2026-08-28.** This paragraph read *"claim 2 does not get stronger with 1,200
> stores"*, and treated the scale as purely a cost decision. It is not. **Two units of scale exist
> and only the second one is load-bearing**: the *nominal* estate, and the roster that survives the
> design engine's automatic exclusions — the units a lottery is actually drawn over. The first has
> never decided anything; the second decides whether an experiment can exist at all, because the
> control arm is a share of it and the balance tolerance is judged on that arm.
>
> Measured, on this repository's own corpus: **100 stores → 109 neighbour pairs → a surviving
> roster of 45 → a control arm of 9**, on which no lottery in two hundred passed the readout's
> balance check, and on which four of five world seeds were refused at design outright. Adding
> stores does not fix it — 1,200 leave a roster of 212 — because the towns are fixed and the estate
> gets denser rather than larger.
>
> Neither half was wrong on its own. `corpus/world/chain.py` clusters stores deliberately so W2
> always has interference to detect; `feasibility._neighbour_exclusions` removes one member of
> every pair deliberately so no store measures its neighbour. **They had never been run against
> each other**, and the sentence above is what let nobody look: it said the number was a cost
> decision, so nobody computed the other number. T00D and T00E in `TASKS.md` carry the fix, and
> the prior wording stays here per doctrine rule 4 — the delta *is* the finding.
>
> **So: a figure about scale names the surviving roster.** "100 stores" is a bill; "a roster of 45
> with a control arm of 9" is the thing a claim rests on, and only one of the two can be checked
> against a claim.

> **Restated again 2026-08-29, because the restatement above carried three unmeasured figures —
> and one of them was the very number it was written to insist on measuring.**
>
> The chain of the paragraph above — *100 → 109 pairs → roster 45 → control arm 9* — was measured
> before **T00E** moved the chain's placement rule, and nobody re-read it afterwards. Measured now,
> by `python -m ops.roster`, which is the one place that number lives:
>
> | scale | stores | pairs | excluded | roster | control arm |
> |---|---|---|---|---|---|
> | `scenario` | 100 | 18 | 17 | **83** | 16 |
> | `scenario` · W2 | 100 | 47 | 34 | **66** | 13 |
> | `harness` | 320 | 59 | 51 | **269** | 53 |
> | `harness` · W2 | 320 | 148 | 98 | **222** | 44 |
>
> Three things above are wrong, and they fail in three different ways.
>
> **The chain is stale.** 109 pairs and a roster of 45 belong to a placement rule the repository no
> longer has. The finding they carried was real — two files, each correct alone — and T00D and T00E
> are what closed it. The figures are what the closing made obsolete.
>
> **"1,200 leave a roster of 212" was never a measurement.** `--scale` accepts `smoke`,
> `rehearsal`, `harness` and `scenario`, and the largest is 320. No declared scale reaches 1,200,
> so that figure was a projection presented in a sentence whose whole argument is that projections
> are not measurements. It is withdrawn rather than corrected: **1,200 stores is the scenario the
> system is written for, not a scale this repository has ever run.**
>
> **And "the corpus is 100" names the wrong scale.** Claim 2 runs at `harness` — **320 stores, a
> surviving roster of 269** — and 100 is `scenario`, which proves nothing. The paragraph written to
> stop the nominal number standing in for the load-bearing one had the nominal number wrong too.
>
> *(`about 36M POS lines` is also stale; `corpus/world/README.md` restated it to **39.2M** under
> T00E and recorded the mismatch against this file. It stayed here for a day.)*
>
> **What survives is the argument, and it survives untouched**: the number a claim rests on is the
> roster a lottery is drawn over, and it is the only one of the two that can be checked. What did
> not survive is any figure in the paragraph that asserted it — which is the eighth form of the
> rule in `A guard tested by its author`, and the sharpest: **the statement of a rule is not exempt
> from it.**

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
| **7** | **A decision that targets a person is structurally impossible.** The decision key has no customer dimension, and a test goes red if one appears — on every type on the decision path and in the contracts, which compile into four consumers without a Python type moving. *Trap: a list of person-shaped words written by whoever also wrote the field names is one function agreeing with itself → the words come from two published vocabularies, and the guard is the **closed field set**, which reads no names at all.* **Measured: the hand-written list catches 35 of 317; the closed field set refuses 17,752 of 17,752.** | `evals/oversight/` |

**Claim 2 is the one that separates this from a demo. Claim 6 is the one nobody builds.**

> **Claim 4's row restated 2026-08-29 (T005), because the corpus does not produce the shape it
> names.** The row says *a stock-out is never read as zero demand*, and the two functions that make
> it true are `censoring.read` — which returns a type with no `units` attribute at all — and
> `censoring.correct`, which answers with a lower bound and **no number** where the observed window
> is empty. Both hold. What the measurement says is that the literal zero is almost unreachable:
> across three worlds and 80,640 store-days, **no censored store-day sold nothing**, so the only
> route to a zero is a shelf that emptied before its first sale, which this corpus never produces
> and `evals/censoring/` therefore constructs.
>
> What the corpus *does* produce is the failure the row is really about: **21.0% of all store-days
> emptied**, every one of them a day whose sales understate its demand by an unknown amount. How
> much is not a corpus figure and is not stated as one — it is measured on held-out days censored
> **on purpose**, where the withheld total is known, and there reading the truncated number as the
> day's demand understates by **6.0% at the last trading hour and 91.4% at the first**. A day
> censored on purpose is not a stock-out, which is the eval's own first note, so the two halves of
> that sentence are kept apart. The claim's content is systematic understatement, and "zero" is its
> limiting case rather than its typical one.
>
> The prior wording stays, per doctrine rule 4, and it stays for a second reason: **the limiting
> case is where the arithmetic stops defending itself.** `DemandEstimate` refuses to be built
> claiming fewer units than the receipts show, so a zero written over a day that sold eleven is
> already impossible — and zero is not below zero, so the one day on which the claim can still be
> violated is the one the row names. The sentence is right about where to look and wrong about how
> often you find it there.

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
| W2 | real effect + interference between neighbouring stores | **the system does not detect interference.** At this spillover the variance it creates is enough for the power check to refuse — a refusal by luck, not by design |
| W3 | real effect + exposure fails on 30% of treated units | report ITT with the realised exposure rate printed, or refuse below the declared threshold — never silently dilute |
| W4 | an effect that decays (novelty) | no result before the declared end, then report what the declared window aggregated — the first week is never available to extrapolate from |
| W5 | **heavy-tailed store-day demand**, arriving after the history a power calculation is sized on — variance far above what it assumed | the power check fails, or the interval is honestly wide |
| W6 | **everything works, a real effect is present** | **produce the number.** No refusal |

**W6 matters as much as W1.** A system that refuses everything passes every other world and is
worthless. The **false-refusal rate is published beside the false-positive rate.**

> **W2's row restated 2026-08-28. It claimed more than the code supports.** It read *"detect and
> refuse, never estimate"*, which reads as a detector at readout. There is none, and there was
> never meant to be one: `contamination.check` compares the digest, the redraw and the delivered
> policy, and none of the three can see a neighbour's trade crossing the road. The system's whole
> defence against interference is **at design** — `_neighbour_exclusions` drops the later-sorted
> member of every pair inside `neighbour_radius_m` at moment 1, and the only interference code in
> the closed vocabulary, `UNIT_GUARANTEES_INTERFERENCE`, is `at_design`. So W2 is not a world the
> readout refuses; it is a world the **design** disarms, and the eval publishes the pair — the
> estimate with the neighbour pairs declared, and the bias that arrives when they are withheld.
> The prior wording stays here because doctrine rule 4 says a correction never erases what was
> previously stated, and because the delta *is* the finding: prose that claims a check nobody
> wrote is the same defect as a guard tested by its author, one layer up. It was found by reading
> `contamination.py`, not by reading this file — which is the only way it can be found.

> **And then all six rows were read against the function that would make them true, 2026-08-28,
> because one defective row in a table is a defective row and two is a method.** Two more did not
> stand and are restated above; three did, and naming what holds them up is the point of the
> exercise.
>
> | row | the function that makes it true | verdict |
> |---|---|---|
> | W1 | `Readout.is_significant` — `p_value <= alpha`, where `permutation_p`'s `(1 + hits)/(1 + B)` rule is exact at any B | **stands** |
> | W2 | `feasibility._neighbour_exclusions`, at moment 1. Nothing at readout | restated above |
> | W3 | `exposure.measure` → `Exposure.meets` → `EXPOSURE_BELOW_THRESHOLD` | **restated.** It read *"exposure-adjust or refuse"*, and there is nothing to adjust with: `exposure.py`'s own docstring says *"There is no CACE, no instrumental-variable estimate and no exposure-adjusted alternative in this repository, and the absence is deliberate rather than pending"* — no code for it in the closed vocabulary, no field for it on a `Readout`, and it would carry an exclusion restriction this readout exists to avoid. **This row contradicted a module in the same repository.** |
> | W4 | `may_read`, raising `PeekError` before the declared end, and `STOPPING_RULE_PERMITS_PEEKING` at design | **restated.** It read *"report the declared window's average"*, which reads as arithmetic the estimator performs. It does not: `close` takes `outcomes` as given and **cannot verify that what it was handed spans the declared period**. What is guaranteed is that the result cannot be *asked for* early. The aggregation is the caller's obligation, and `evals/uplift/`'s `U8` is where it is checked rather than assumed. |
> | W5 | `Statistic.detects`, judged on the **realised** variance → `POWER_NOT_REACHED`; and `interval`, which widens by inversion rather than by an asymptotic formula | **stands** — the best-supported row in the table |
> | W6 | `close` returning a `Readout` when all four `CheckResult.passed` | **stands** |

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

> **Restated 2026-08-30 by T008, because *unopenable* is not what phase 1 delivers.** The rule
> above is the standing intent and does not change. What changes is the claim about *today*:
> the repository holds **three** seals of identical construction — `CertifiedPrice`,
> `SealedAssignment` and `corpus/world/seal.py` — each declaring the same limit, that a forger
> who rewrites every field together is not caught, and each with a test that performs that
> forgery and requires it to **succeed**. `contamination.py` calls itself *the one door with no
> key* while being the same shape as the other two.
>
> **So: today the guarantee is detection, not unopenability.** Every uncoordinated edit is
> refused by name — a reassigned unit, an erased one, a mis-delivered policy, a digest that no
> longer describes its arms. A coordinated rewrite of the arms, the seed, the strata and the
> digest agrees with itself, and the repository says so in three places rather than one.
>
> **Unopenability arrives in phase 3, with the read-only assignment table.** The door this rule
> names is not a Python type: it is `gold.experiment_assignment`, written before the period
> opens from the committed seed and then read-only, where the *storage* refuses the write that
> the type can only notice afterwards. Until that table exists, the honest sentence is *one
> door that reports every hand laid on it*, and the type is what makes the report trustworthy
> rather than what makes the door shut.
>
> The prior wording stays per rule 4, and the delta is the finding: **a door that detects every
> uncoordinated edit is not the same object as a door that does not open, and this repository
> had been calling the first by the second one's name.** Nothing in the code was wrong — the
> limit was declared in all three places from the day each was written. What was wrong was one
> sentence in the doctrine, which is the layer with no gate behind it.

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

**Balancing is stratification, and the analysis must account for it.** Units are matched into
strata on a composite distance over **pre-period covariates only** — category revenue over the
previous 8 weeks, store format and size, waste rate, pricing zone — and the lottery draws one
control per stratum from the committed seed. Matching on anything measured inside the comparison
window would be using the same data twice and would bias the estimate toward zero. Because the
space of admissible assignments is restricted, the ordinary confidence interval is wrong — it
assumes simple randomisation and comes out falsely wide. The inference is therefore a
**permutation test under the same restriction** — re-drawing within the same strata — or an
estimate adjusted for the covariates that were balanced on. The A/A harness catches a violation
here as CI coverage drifting above the nominal level, so the check exists in both places.

**The restriction is constructive, not rejective, and that is a measured decision.** It was
re-randomisation: draw, screen against a balance tolerance, repeat. At the scenario's shape that
screen accepted about one draw in a thousand, so the permutation reference set starved and the
smallest attainable p-value sat **above** the declared α — no experiment could have reported a
significant effect, for a reason with nothing to do with the estimator. The three alternatives
were priced and refused (a budget of ~400 hours; a tolerance of ~0.41 SMD, which is no balancing
at all; a 50/50 holdout, which reaches only ~1/800), and `docs/DECISIONS.md` records each.
**The balance tolerance is therefore judged at exactly one moment — the readout's balance
check** — over the covariates as they actually arrived, and a stratified draw that lands outside
it is a refusal with a reason code rather than a design that was never allowed to exist.

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

`design/form.schema.yaml` (the nine fields, with closed lists), `design/balance_covariates.yaml`
and `design/inference.yaml`.

**`inference.yaml` is where α, the target power, the balance tolerance, the exposure threshold, the
holdout share and the two budgets live** — every one of them a `{value, source}` pair like any other
contract number. The alternative was a `Decimal` constant in a `.py` file, which is precisely the
"value without a source" this layer exists to refuse: doctrine rule 3 does not care what extension
the file has. Nothing in it is law and every source says so. It compiles to no consumer and is
still validated, claimed and provenance-walked, because a threshold nobody justified is a dial that
will eventually be turned.

It also carries a `carryover:` block — two declared facts about grocery retail and one mitigation
declared *absent*. **The interference table over the four units of randomisation is derived from
that block, never written out**, so a contract that declared a washout long enough to exhaust the
reference price would admit `store_week` with no code change. A hard-coded table would pass every
test while quietly being a second definition of a contract value.

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
             EXCLUSIONS_DEFINED_POST_HOC · METRIC_NOT_IN_CONTRACT ·
             UNITS_ALREADY_COMMITTED · NO_ADMISSIBLE_ASSIGNMENT
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
corpus/real/           what somebody else published, digest-checked — claim 1's prices, and
                       claim 7's two vocabularies of the names a person is known by
evals/                 one directory per claim · report.py is the shared shape
  gate_proof/          the planted mutations: green first, named target, STALE on a moved one
ops/                   the rules the product code is measured by — the corpus barrier and
                       the decision key's closed field set (one implementation, two callers
                       each: a test and an eval) and the deferral registry
.claude/               the AI layer that ships with the repository: the skills, the hooks,
                       and settings.json
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
| `ci` | every push | the suite, every eval, `gate-proof`, `make contracts`, `make expiry`, `make preview-audit`, `terraform validate` |
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

**And a condition names an event, never a session.** *Added 2026-08-30 by T008, which found nine
open deferrals pointing at itself.*

> **An unlock condition that names a session rather than an event is not a condition; it is a
> date without a calendar.**

*"The phase-1 integration session"* answers *when* and never *what has to become true*, so it
cannot be evaluated, cannot expire, and cannot be met by anything except a session being held.
Nine entries carrying it meant the review whose job was to **read** arrived owing eleven
**decisions**, and every one of them had been deferred on the strength of a name rather than a
fact. A condition names a thing that happens in the repository — a contract opening a new
window, a table existing, a target being written, a figure being published — and an integration
session is then the moment somebody *notices* it has happened, which is a different job.

Where the honest answer really is *"a human has to weigh this"*, that is said in those words with
a date beside it, because `make expiry` can act on a date and can never act on prose. It checks
that an unlock condition is **present**, never that it is right — the standing limit
`docs/DECISIONS.md` declares about itself, and the one this rule exists to keep small.

`PLAN.md` is updated at the end of every session: what closed, what is open.

---

## Where the AI layer lives

Three mechanisms, three jobs. Choosing the wrong one is why `.claude/` directories bloat.

| | is | acts |
|---|---|---|
| **`CLAUDE.md`**, layered | a **rule** | passively, wherever you are working |
| **Skill** | a **procedure** | when you invoke it by name |
| **Hook** | a **guarantee** | the harness enforces it, wanted or not |

A rule that holds wherever you are → `CLAUDE.md`. A procedure that recurs and carries judgment →
a skill. Something that must never happen → a hook.

**And a hook has a second bar, because the first one is too easy to clear.** A hook exists only
where the gate that already covers the rule **cannot run at the moment the mistake is made**. A
hook that duplicates a check CI already makes green-or-red is a second, unversioned test suite
that nobody runs and nobody trusts. The two that clear it are the corpus barrier — whose gate is a
test that runs on every push and cannot run *now* — and `git commit` on `main`, whose gate is a
ruleset that refuses the *push* and cannot stop the commit being made. `.claude/README.md` names
what each does not catch.

### The criterion for where a skill lives

> **Does it shape the code in this repository → it lives in this repository.**
> **Does it produce something outside the repository → it lives at user level.**

| in `.claude/skills/` here | at `~/.claude/skills/` |
|---|---|
| `claim` — build a claim's eval, its `gate-proof`, its `make claim-N` | `banner`, `social-preview` |
| `contract-change` — restatement? new window? which consumers? which past results? | `readme-standard` |
| `integration-review` — bugs in the process, not the code | `linkedin-debut`, `linkedin-article`, `post-ideas` |
| `defect-to-rule` — root cause, then the rule that stops the class recurring | `promo-guide`, `storyboard`, `aws-mask` |

The right-hand column produces artefacts that live outside any repository. The left-hand column
writes code and rules inside this one.

`project-inception` and `project-architecture` stay at user level because they are needed *before*
the repository exists; their output — `CLAUDE.md`, `PLAN.md`, `infra/` — is what lands here.

### Why in the repository rather than shared

**A skill committed here is not a copy of a shared one. It is the record of the method that built
*this* project** — a lockfile for process. It is not supposed to match the next repository; it is
supposed to be accurate about what happened here. Divergence between projects stops being drift and
becomes history.

Three projects are also not proof of generality. Extracting a universal skill from three samples is
premature; extracting it from eight, once the shape has stopped moving, is not.

And a skill that lives here **goes through a pull request and CI like everything else**. A change to
the method is a commit with a reason, reviewed, and visible in `git log`. The method gets the same
standing as the code: **nothing changes silently.**

Anyone who clones this repository gets the whole thing — what was built *and* how.

---

## A guard tested by its author

The project's most frequent defect, five times over:

> **A guard tested by its author is tested in the shape the guard already handles.**

| | what happened |
|---|---|
| `_exact_floor` | called `Money.as_lower_bound` while claiming to be an independent second implementation |
| G3's tolerance | did not catch a bound that was *too strict* — the direction this project's own history says its bugs appear in |
| `main_guard` | refused `git add -A && git commit` on one line and allowed the same two commands on two lines. It bit the shape a reviewer writes in a test and missed the shape a session actually writes |
| the corpus barrier | missed `import src.holdout`, which works because `src/` is an implicit namespace package — the spelling that matches the file tree, and the one T00A's own description used. **The gate behind the hook had the same hole, and the branch that rewrote that gate did not close it** |
| claim 4's `C6` | offered `fit` a censored store-day **on its own** and demanded a refusal. A `fit` that skipped censored days instead of refusing them still went red on a pile of one, because the empty curve it then built was refused by a *different* guard. The check tested the shape its author pictured — one bad day — rather than the shape a caller hands over, which is a pile with a bad day in it |
| claim 7's word list | the guard against a customer dimension was a tuple of person-shaped substrings, written by whoever also wrote the field names it was checking. Measured against 156 schema.org properties and 99 Presidio entity types — 317 names, chosen by two publishers who have never read this repository — **it catches 35 of them, 11%**. It misses `family_name`, `nationality`, `job_title`, `spouse`, `buyer`, `owner`, `recipient` and 275 others |
| claim 7's own registry | and then, one row down, the same defect inside the fix. `unlisted()` exempted any type whose name begins with `_`, so the guard refused a planted `VisitContext` and waved through `_VisitContext` — while printing the question *"is **every** type written down"*. It was found by oversight level 2 renaming the class the mutation plants. **A guard tested by its author is tested in the shape the author's own naming convention produces** |

Each of the first three was declared impossible by prose sitting beside the code. **The word
list had no prose at all and no gate behind it either** — claim 7's row in the table above was
the one row of seven with no *trap* written beside it, and that is exactly where it sat
unexamined. Six claims had somebody write down what agreeing with itself would look like here;
this one had a tuple of words and nobody had asked who wrote them. A missing trap is not a
formatting omission. It is the place the defect is.

**And the row after it is the one worth reading twice.** The branch that fixed the word list —
the branch whose entire subject was *who chose the case this guard is tested on* — shipped the
same defect one layer in, in its own replacement guard, and did not see it. Its author wrote the
mutation that plants a type the registry has not been told about, chose the name
`VisitContext`, watched it bite, and never tried the other spelling. **The rule does not stop
applying to the person who has just finished quoting it**, which is the argument for oversight
level 2 existing at all rather than being a formality: three of the four rows above were found
by a reviewer, and so was this one.

`gate-proof` catches this for gates, because a mutation is planted by something that is not the
detector. **Nothing catches it for hooks, barriers or tests**, and that is where it keeps happening.

> **Restated 2026-08-28 → 2026-08-29 (T005): it does catch it for an eval's checks, and the fifth
> row above is the proof.** The sentence read *"hooks, barriers, checks or tests"*, and `checks` was
> wrong to be in that list — an eval's check is a gate like any other, and a `claim-N` target owns
> mutations aimed at it by name. `the-curve-learns-from-the-days-the-shelf-emptied` reported
> `SURVIVED`, which is exactly the harness saying *this check does not bite where you claimed it
> does*, and the fix was to the check rather than to the assertion. **The condition is that a
> mutation is aimed at that check specifically** — a check with no mutation of its own is still
> outside the net, which is what `make gate-proof`'s "no claim target with nothing planted against
> it" makes structural at the target level and cannot make structural per check. Hooks, barriers and
> tests remain uncovered, and the prior wording stays per doctrine rule 4.

**So: the case a guard is tested on may not come from whoever built the guard's idea of the
failure.** It comes from a shape the guard did not anticipate — a command somebody actually ran, an
import somebody actually wrote, a price list nobody here drew. Where that is genuinely impossible,
the test says so in one line, and the guard's docstring states what it therefore does not cover.

**And when a guard is fixed, the gate behind it is re-read.** They usually share the assumption.

### The same defect one layer up — prose that claims a check nobody wrote

A guard tested by its author fails in the shape its author imagined. **A sentence written by its
author fails the same way, and there is no gate at all behind it.** The six-worlds table said W2 was
*"detect and refuse"* when the only interference code in the closed vocabulary is `at_design`, and
said W3 was *"exposure-adjust or refuse"* when `exposure.py`'s own docstring says in as many words
that there is no exposure-adjusted number and never will be. Three files agreed with each other
every time, because all three were written from the same sentence — so **no amount of reading the
documents could find it.** It was found by reading `contamination.py` and asking which of its two
questions would fire.

**So: a sentence naming what the system does when something goes wrong is written against the
function that would do it — named — and not against the table it came from.** Where no such function
exists, that is the finding, and the sentence says so instead. It applies hardest to text that
*ships*: `corpus/world/worlds.py`'s `correct_behaviour` is sealed into every `truth.sealed.json`, so
it is a promise the package makes about the system rather than a comment about it.

### And a third time on the same line — the limb the first two were missing

**W2's row was restated on 2026-08-28 and the restatement was wrong too.** The first wording said
*"detect and refuse, never estimate"*, which named a detector nobody wrote. It was corrected against
the code — `contamination.check` cannot see a neighbour's trade crossing the road, and the defence
is `feasibility.neighbour_exclusions` at moment 1 — and became *"exclude the interfering units at
design, then estimate on what is left"*. That sentence is **true about the code and false about the
system**: run on the corpus, W2 produces no number at all. Every draw in sixteen refused
`POWER_NOT_REACHED`, with the neighbour pairs declared and with them withheld alike, because the
spillover inflates the residual variance past what the power check will admit. There is nothing
left to estimate on.

The same measurement corrected W5 in the other direction. Its row said *"heavy-tailed baskets"* and
the tail was real — on the basket line, where `category_margin_per_store_week` aggregates sixteen
thousand of them and averages it away. Measured, W5's standard error at the readout came out
**below** W6's: the world whose declared pathology is variance had less of it than the world with
none.

**Three wrong sentences about one table, and the third is a signal that the rule was short a
limb rather than that somebody was careless.**

> **A sentence naming what the system does when something goes wrong is written against the
> function that would make it true — named — *and against the measurement of what comes out when
> it runs*. A line can be true of the code and false of the system on the corpus.**

The two are different questions and only the second one runs. `feasibility.neighbour_exclusions`
really does drop the later-sorted member of every neighbouring pair; what no reading of it could
have said is that the units it leaves behind carry a variance the readout will refuse. That is not
in any function. It is in a number, and the only way to have it is to run the thing.

### And a fourth time, in no sentence at all — the rule was scoped to the form, not the defect

The three above are prose. **The fourth was a number in a workflow file**, with no sentence
anywhere near it. `ci.yml`'s `claims` job was given `timeout-minutes: 45`, projected from a
measurement taken on the author's **fourteen-core** laptop onto a runner with **four**. The runner
cancelled the harness before it finished. No cold measurement of the thing that would actually run
had been taken, and one run would have produced it.

What makes it this defect rather than an estimate that came out wrong: it happened **inside the
same change whose deferral existed to prevent it**. `docs/DECISIONS.md` carried *"CI's gate job runs
on a temporary 25-minute timeout"*, whose entire argument is that a budget set from a projection
rather than from the spread between runners is a gate that reports which machine it drew, and whose
*what must not happen* names the next session's mistake in advance. That entry was **closed by this
change** — correctly, by splitting the jobs rather than raising anything — and in the same diff the
new job's budget was set the way the closed entry says not to. Nothing was careless. The rule simply
did not appear to apply, because it said *"a sentence"* and this was a YAML key.

**A timeout, a K, a tolerance, a threshold, a budget — each is an assertion about what the system
does, wearing a number instead of a verb.** `timeout-minutes: 45` says *this job finishes in
forty-five minutes*, which is as falsifiable as any row of the six-worlds table and was false in
exactly the same way: written against a projection instead of against the measurement of what comes
out when it runs. What a number lacks is the paragraph that would have made somebody ask which
function makes it true — so it is the form of the claim that hides it, which is precisely why the
rule may not be scoped to a form.

> **An assertion about what the system does — a sentence, or a number in configuration — is written
> against the function that would make it true, named, *and against the measurement of what comes
> out when it runs*. Where the number will be met on hardware that is not the author's, the
> measurement is taken there.**

This restates the boxed rule above, which said *a sentence*; the prior wording stays per doctrine
rule 4, and the delta is the finding. It was never only about sentences — the three instances that
produced it happened to be prose, and a rule generalised from the form the known defects wore is a
rule that cannot see the next one. **Three of these were found by reading code; the fourth was
found by a job being cancelled**, which is the same lesson the third one carried: only the
measurement runs.

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
- **If it is a guard, a barrier, a check or a hook: who wrote the case it is tested on?** See below.
- **If it is an assertion about what the system does — a sentence, *or a number in configuration*: which function makes it true, named, and what came out when it ran?** A sentence written against the table it came from rather than against the code is the same defect one layer up; one true of the code and false of the system on the corpus is that defect again. **A timeout, a K, a tolerance, a threshold or a budget is the same assertion wearing a number instead of a verb** — set it from a measurement of the thing that will run, on the hardware that will run it, never from a projection. See below.
- If it touches a contract: does the change imply a restatement?
- If it states a legal fact: which article, which instrument, verified when?
- If the pattern comes from another project in this portfolio: **what problem did it solve there,
  and do we actually have that problem?** A pattern copied with the solution to a problem you do
  not have is cost with no benefit — it has already happened twice here.
