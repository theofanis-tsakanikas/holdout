# The scenario

Who operates this system, what it decides, on what data, and what makes any of it hard.

`CLAUDE.md` carries the mental model, the seven claims and the doctrine. `PLAN.md` carries the
four phases. `docs/DECISIONS.md` carries what was decided and what would reverse it. This file
carries the thing all three assume and none of them states at length: **the shop.** It argues
for nothing — an argument that lives here rather than in `DECISIONS.md` is an argument that
cannot be reversed with its reasoning intact.

---

## The rule this file is written under

This is prose full of numbers, which is exactly the shape of the defect this repository has now
found eight times: **an assertion written against a table, or against a projection, instead of
against the measurement of what comes out when it runs.** `CLAUDE.md` boxes the rule — *an
assertion about what the system does, a sentence or a number in configuration, is written
against the function that would make it true, named, and against the measurement of what comes
out when it runs.* A background document is the easiest place in the repository to break it,
because nothing here compiles, no consumer is generated from it and no gate reads it.

So every number below carries one of exactly four kinds, and the kind names what is standing
behind it:

| | kind | what it is | what it carries beside it |
|---|---|---|---|
| **[M]** | measured | a command in **this** repository produced it | the command, the scale and the seed |
| **[D]** | declared | a contract value, `kind: scenario_assumption` | the contract file — and `make contracts` refuses a `value` with no `source` |
| **[C]** | cited | a fact about the world outside this repository | the instrument or the publisher, and the date somebody opened it |
| **[S]** | scenario | the chain this system is written *for* | the words **it has never run** |

**[D] and [C] do not merge, and keeping them apart is most of what the contract layer is for.**
A declared value is one this project invented — α, the holdout share, the ladder's depths — and
what holds it up is a gate that refuses it unless somebody wrote the argument down beside it. A
cited value is one somebody else measured, and what holds it up is a citation and a date on
which a person opened it. `docs/REGULATORY.md` exists because those two were once the same
field: a value carrying a real instrument, a real article and a resolving URL, asserting
something the instrument does not say. `make contracts` could not catch it and cannot — it
checks the *shape* of provenance, never its content.

**[S] never wears a number that reads as measured.** The largest estate this repository has
ever generated is **320 stores [M]**. `--scale` admits exactly four names, and `harness` is the
largest of them: **1,200 stores is the scenario, and no run of it exists.**

**Anything that fits none of the four is not in this file.** Two things were excluded on that
rule rather than dropped quietly, and both are named in
[What is not in here](#what-is-not-in-here).

---

## The operator

A grocery chain in Greece. **[S] Roughly 1,200 stores and 40,000 SKUs, taking roughly 2.4
million pricing decisions a day. It has never run: no scale in this repository exceeds 320
stores.** That is the estate the architecture is written for, and it is the reason for the one
structural decision a reader is most likely to question: **no LLM is anywhere near the decision
path.** At that rate a language model is too slow, too expensive and non-deterministic, so the
demand model runs inside the pipeline from a registered artifact and the agent — which runs a
handful of times a week — never touches a price at all. The two never call each other.

The system is not built for the person who takes a pricing decision. It is built for the person
who has to **defend one afterwards** — the slide that says *"AI delivered €4.2M"* [S] that
nobody in the room can check. Three roles touch it and none of them is the model:

- **Whoever fills the design form.** `contracts/design/form.schema.yaml` declares nine fields
  and `filled_by: agent | human:<name> | policy:<name>`. The engine does not know and does not
  care which of the three it got; a test runs one identical design under all three attributions
  and asserts the three experiments are the same lottery. Two fields are never the agent's:
  `max_duration`, which is a business constraint, and `decision_rule`, which is what will be
  done with each outcome. **The agent proposes how we will find out, never what we will do once
  we know.**
- **A named human approves.** Both AI systems — the demand model and the agent — gate on a named
  human, and doctrine rule 5 is that nothing approves itself. No model, no pipeline and no agent
  may approve a promotion, grant an exception or classify its own design as valid.
- **Nobody moves a unit between arms.** Doctrine rule 7 — one door has no key. No unit changes
  arm after its first observation, and not by an approver either. The assignment table is
  written before the period opens, from a committed seed, and is then read-only.

What the operator gets back is deliberately asymmetric: **either an uplift with a confidence
interval and a pinned data version, or a refusal and its reason code at the same size on the
screen.** `contracts/vocabularies/reason_codes.yaml` closes the vocabulary at **12 `at_decision`,
8 `at_design` and 4 `at_readout` codes [D]** — closed, because a free-text reason cannot be
counted, tested or gated.

---

## Three decisions, one stream

The chain takes three kinds of pricing decision. They share a data path and share nothing else,
and only one of them actuates itself.

| decision | horizon | actuation | why |
|---|---|---|---|
| **markdown on expiring fresh** | minutes | **automatic — the primary path** | a physical consequence, at high enough frequency that an experiment reaches power in days |
| **base price by zone** | weeks | **a proposal to a human** | **no actuation path exists.** This is architecture, not a policy statement |
| **a joint plan with a supplier** | quarters | Clean Room | the alternative is exchanging commercially sensitive data |

### Why the fresh path is allowed to move on its own

Not because it was judged low-risk. Because of one provision, and the whole architecture rests
on it:

- **[C] Article 6a(1)–(2), Directive 98/6/EC** — an announced price reduction must state the
  *prior price*, the lowest the trader applied over not shorter than 30 days before. Verified
  2026-08-27.
- **[C] Article 6a(3)**, and Commission Notice **2021/C 526/02 §4.1** — Member States may set
  different rules for goods liable to deteriorate or expire rapidly, and those rules *"may even
  consist of completely exempting such goods"*. Verified 2026-08-27.
- **[C] άρθρο 9ι παρ. 2 ν. 2251/1994**, inserted by ν. 5111/2024 άρθρο 3 (ΦΕΚ Α΄ 76/24.05.2024)
  — Greece took the exemption. Verified 2026-08-27.

If that had gone the other way, every automatic markdown would be an announcement carrying a
30-day lowest price, the ladder would have to reason about its own price history at every step,
and *"markdown on expiring fresh actuates automatically"* would be false. `docs/REGULATORY.md`
carries the full chain, including the amendment that **moved the rule into a different statute
and repealed the old provision outright** — which is why a guardrail is a versioned contract
with effective windows and not a current value.

Two consequences the system encodes rather than remembers. Membership of the exemption is a
**product attribute** resolved from the product master as of the decision, never inferred from
an observed shelf life. And the exemption escapes Article 6a and nothing else: **[C] ΥΑ
91354/2017 άρθρο 78 παρ. 4** still requires the retailer to prove, on inspection, that the
original price on the label was really applied. That is the legal reason the **electronic shelf
label acknowledgement is a first-class source in this system rather than a log.**

### The safe state is asymmetric, and it is a type rather than a convention

Doctrine rule 1 says the safe state is declared per decision path and no path may inherit the
other's. For an expiring product silence is not safe — the product is thrown away — so the safe
state is the deterministic markdown ladder. For a price increase silence *is* safe, so the safe
state is no action.

`src/holdout/core/decision.py` makes the crossing impossible rather than discouraged:
`SafeState.LADDER` is unreachable on the base-price path and `safe_state_for` refuses to return
it there, because *falling back to a markdown schedule on a base-price decision would mark down
a product nobody asked to mark down.*

The ladder itself is `contracts/policies/ladder_policy@v1.yaml`: **[D] 20%, 35%, 50% and 70% off
the shelf base price at 24, 12, 6 and 3 hours to expiry**, each rung carrying a
`scenario_assumption` note saying that no chain's actual schedule was obtained and none is
claimed. It clamps to the floor and never produces a refusal itself — the guardrail set decides
whether any legal price sells the item, and a refusal there is a correct output (donation or
disposal) rather than an error.

And the ladder is also **the control arm**. The holdout does not mean *nothing*; it means the
*existing* policy. Comparing against abandonment would inflate every uplift ever measured.

### What a decision actually does, in seconds

```
trigger → freshness gate → which arm? → features → model → selection
   → guardrails → decision record → Lakebase → ESL → ack → bronze
```

Four things fire one: entering the decision window before expiry, a ladder step, an abrupt
inventory change, or a cost change in the ERP that moved the floor. The freshness gate runs
**before the model is called at all** — stale inputs go straight to the ladder, marked. The
model returns a *scenario table*, never a price; code picks the scenario by arithmetic. The
decision record is written **before** the price is dispatched. Three outcomes, and all three are
correct outputs: **normal** (model, certified), **fallback** (ladder, marked all the way to the
label, the P&L and the experiment — doctrine rule 2), and **refusal**.

A decision is idempotent per (SKU, store, ladder step), which is why `DecisionKey` carries an
integer `occasion` — the ladder rung on the markdown path, the pricing-week ordinal on the
base-price path, with the path itself in the key so the two numbering schemes cannot collide.
Four fields, closed by a test, and **no customer dimension anywhere in it.**

---

## The data, and where it comes from

Ten bronze tables, one per source, each in the source's own shape, each carrying **both** its
event time and its arrival time. Nothing is transformed at ingestion and no source is merged
with another there — merging at bronze destroys the ability to reprocess one independently.

| source | arrives by | why that mechanism |
|---|---|---|
| POS lines · scale labels · **ESL acknowledgements** | **Zerobus Ingest** | events from every store with no message bus to operate — **the live day only** |
| product master · cost ledger · supplier terms · regulated basket · store master · planogram · competitor prices | **bulk load from files on S3** | several drops during the day rather than one, so master data changes while the day runs — no connector, no gateway, no ingestion code to maintain |
| **eight months of transaction history** | **bulk load from files on S3** | streaming eight months through Zerobus would be slow and costly, and no real deployment does it — backfill from files, then stream |

The ERP's master data arrives as **files, dropped several times during the live day**: a cost
changes mid-day, a product enters the regulated basket, a supplier term changes retroactively, a
column is added. The argument is what forces the several drops rather than one — a single static
snapshot gives incremental ingestion nothing to do and proves nothing.

**What that demonstrates is incremental load of successive drops, not change capture against a
live source**, and the difference is stated here rather than glossed because this document is the
one an article would be written from. *Restated 2026-09-02.* It read *"The ERP is a **real
Postgres**, stood up by the `sources` layer, seeded with history and then driven during the live
day"*, and the prior wording stays per doctrine rule 4. **The larger claim was the better story**,
which is exactly why it is named: a managed connector to a live Postgres requires a gateway on
classic compute running continuously, which contradicts *serverless only*, and the author chose
the smaller claim over the contradiction.

Five silver tables — `sales · shelf_state · price_displayed · reference · quarantine` — one per
question rather than one per bronze table. Three rules there carry most of the weight:

- **As-of joins, never current.** A sale at 14:00 joins to the cost *as it was known at 14:00*.
  Joining to the current cost table silently rewrites every historical margin.
- **The displayed price comes from the ESL acknowledgement, never from the decision.**
  `price_decided` and `price_displayed` are separate columns and they differ.
- **Deduplication uses a business key, never a hash of the payload.** The same receipt line
  delivered twice is one event; two identical baskets in the same second at the same till are
  two. If the POS supplies no real `transaction_id`, that is declared as a known limit — it is
  not invented.

Gold is four families: business facts, features, the experiment tables, and the immutable
decision record written at decision time. The assignment table is written before the period
opens and is then read-only; the readout **pins a Delta version**, because without one,
re-running last month's readout returns a different number as late data arrives.

### The corpora that are not ours

Two claims are attacked from data published by people who have never seen this repository, and
`corpus/real/` holds it committed and digest-checked. **Real inputs, derived cost:** the three
sources below are observed, and the unit cost claim 1's margins rest on is derived from the third
because no public source carries a retailer's cost.

- **[C] 32,480 individual price quotes** collected by hand in shops by the UK Office for
  National Statistics and published under the Open Government Licence v3.0, retrieved
  2026-08-27. Real shelf prices, real price endings, real dispersion between outlets — none of
  which any generator this project could write would produce.
- **[C] The 63 categories of ΥΑ 21330/12.03.2026 (ΦΕΚ Β΄ 1411)** — the Greek margin cap's own
  list, which `contracts/guardrails/regulated_basket.yaml` deliberately does **not** name.
- **[C] Eurostat's gross margin on goods for resale over turnover for NACE 47.11 in Greece**,
  from which the corpus derives a unit cost. A retailer's cost is not public; the derivation and
  its inputs are written out in `corpus/real/MANIFEST.yaml` rather than a plausible number being
  chosen.
- **[C] 156 schema.org properties whose domain or range includes `Person` (release 30.0) and 99
  Presidio PII entity types (commit `eb93051b`)**, which together yield **317 names** — extracted
  mechanically, kept in the publishers' own spelling, retrieved 2026-08-29. Two publishers with
  nothing to do with each other and nothing to do with this project.

---

## What makes it hard

Six things, and none of them is the forecasting.

### 1 · The envelope is a moving contract, not a constant

The system does not change prices wherever and whenever it likes, and encoding the envelope so
it cannot be violated **is** the engineering. The hard part is that the envelope has a history.
Between 2021 and 2026 the Greek gross-margin cap changed not its numbers but its **shape**:

| in force | instrument | unit of comparison | benchmark |
|---|---|---|---|
| 18.07.2021 → | **[C]** ν. 4818/2021 άρθρο 58 | gross margin **per unit** | the seller's own margin before 01.09.2020 |
| 05.03.2022 → 30.06.2022 | **[C]** ν. 4903/2022 άρθρο 50 | gross margin **per unit** | the seller's own margin before 01.09.2021 |
| 11.03.2026 → 30.06.2026 | **[C]** ΠΝΠ 11.3.2026, ratified by ν. 5289/2026 άρθρο δεύτερο | gross margin **per product code** | the **2025 full-year average** |

All verified 2026-08-27. A decision taken in April 2022 is judged per unit against a point in
time; one taken in April 2026 is judged per SKU against an annual average. **There is no single
"current cap" field that could have held both**, and code that hard-coded either would keep
returning a plausible number computed the wrong way, with nothing red anywhere. So a guardrail
is a versioned contract with effective dates, and a decision taken in April is judged by April's
rule permanently — even after the law changes again.

And the answer is not portable. **[C] Commission report COM(2024) 258 final/2 §7** puts Member
States in four groups, not two: thirteen exempt perishables (Greece among them), four apply the
rule with a reduced reference period (Bulgaria 7 days, Romania 10, Denmark 14, Portugal 15), six
apply it in full, three took no derogation at all. A chain operating across the Union cannot
carry one prior-price rule, and cannot carry one *binary* either.

### 2 · The holdout is small, and its size is not the store count

This is the finding that decides whether anything is provable, and it was in no file: the corpus
clusters stores deliberately so that W2 always has interference to detect, and the design engine
excludes the later-sorted member of every pair inside the declared neighbour radius so that no
store measures its neighbour. Both deliberate, both documented, both tested — and their
**product** is that a large share of the estate disappears before a lottery is drawn.

**[M]** `python -m ops.roster --scale <name>`, seed `holdout-w-0001`, at the contract's **[D]**
`holdout_share_pct: 20`:

| scale | stores | pairs | excluded | **roster** | control arm |
|---|---:|---:|---:|---:|---:|
| `smoke` | 12 | 0 | 0 | **12** | 2 |
| `smoke` · W2 | 12 | 4 | 4 | **8** | 1 |
| `rehearsal` | 20 | 0 | 0 | **20** | 4 |
| `rehearsal` · W2 | 20 | 8 | 8 | **12** | 2 |
| `harness` | 320 | 59 | 51 | **269** | 53 |
| `harness` · W2 | 320 | 148 | 98 | **222** | 44 |
| `scenario` | 100 | 18 | 17 | **83** | 16 |
| `scenario` · W2 | 100 | 47 | 34 | **66** | 13 |

Three things follow, and the third is why this section exists.

**The number a claim rests on is the roster, not the store count.** Read the table by its last
column: a control arm of 53 and a control arm of 13 are different projects, and neither the store
count beside them nor the scale's name says which one you have. This is why `harness` — the scale
claim 2 is actually proved at — has **more** stores and fewer SKUs than `scenario`: it trades what
the clock sees for what the statistics see.

**`make roster` exists because two deliberate decisions met on a quantity nobody was computing.**
It lives in `ops/` rather than in `corpus/`, because the answer is a joint fact about the
geography the generator lays out and the exclusion rule `holdout.core.design.feasibility`
applies to it — and the corpus may not import the system, so a copy of the exclusion rule inside
`corpus/` would be the copy that goes stale.

**`CLAUDE.md`'s scale paragraph carries figures this command does not reproduce**, and the
reason is worth stating rather than leaving to be discovered. Its chain — *100 stores → 109
pairs → roster 45 → control arm 9* — was measured before T00E moved the chain's placement rule,
and is stale rather than wrong: at 100 stores today the roster is 83. Its *"1,200 leave a roster
of 212"* is a different thing again — `--scale` accepts four names and the largest is 320, so no
run of 1,200 stores has ever existed and that figure is a projection, in a paragraph whose whole
argument is that projections are not measurements. **`python -m ops.roster` is the one place this
number lives**, and the table above is what it printed.

### 3 · A stock-out is not zero demand

When a shelf empties the baskets stop and nothing records the ones that were never rung up. The
naive reading — *sales were low, so demand was low* — teaches a model to order less of the thing
that sold out, which empties the shelf sooner.

`holdout.core.demand.censoring` answers it as a **type** rather than a correction: a store-SKU-day
is either one the shelf held, which has `units`, or one the shelf emptied, which has `at_least`
and **no `units` attribute at all**. A caller who wants a number has to say what it did about the
censoring, because there is nothing to reach for. Where the observed window carries no evidence
to expand — the shelf was bare before the first sale, or it sold nothing before it emptied — the
answer is a lower bound and **no number**.

The rate and the size of the understatement are published by `make claim-4` and are not restated
here: they are that eval's evidence, and a figure copied into a background document is a figure
that goes stale where nothing runs.

### 4 · Exposure is not assignment

A price that was decided is not a price that reached a shelf. Labels fail, and they fail in every
world in the corpus rather than only in the one built to test it. This is why the ESL
acknowledgement is a source rather than a log, and why the readout refuses below **[D]**
`exposure_min_pct: 95` with `EXPOSURE_BELOW_THRESHOLD` instead of quietly diluting an estimate.

There is deliberately **nothing to adjust with**: no CACE, no instrumental-variable estimate, no
exposure-adjusted alternative, no field for one on a `Readout` and no code for one in the closed
vocabulary. An exposure-adjusted number carries an exclusion restriction, and this readout exists
to avoid assumptions of exactly that kind. Above the threshold the realised rate is printed
beside the estimate; below it, there is a reason code and no number.

### 5 · Interference, which the system does not detect

Two stores under a kilometre apart share shoppers, so a control store's outcome depends on its
neighbour's arm and SUTVA breaks. The system's entire defence is **at design**:
`feasibility` drops the later-sorted member of every pair inside **[D]**
`neighbour_radius_m: 1000`, and the closed vocabulary's only interference code,
`UNIT_GUARANTEES_INTERFERENCE`, is filed under `at_design`.

**There is no detector at readout, and there was never meant to be one.** The four validity
checks — balance, exposure, contamination, power — ask nothing about a neighbour's trade
crossing the road. `docs/DECISIONS.md` carries that as a deferral with the world that would
demonstrate it as the unlock, rather than as a limit somebody discovers later.

Two of the four units of randomisation are refused before any judgment is exercised, and the
refusal rests on a **paragraph in a contract rather than on a calculation** — said out loud
rather than presented as arithmetic. **[D]** `contracts/design/inference.yaml`'s `carryover:`
block declares `reference_price_memory: true`, `cross_price_substitution: true` and
`washout_weeks: null`, and `interference_of(unit, carryover)` derives the table from those three
entries. A contract that declared a washout long enough to exhaust the reference price would
admit `store_week` **with no code change**.

### 6 · The comparison has to survive being checked

Everything above is upstream of the one thing the project is actually about: an uplift number
produced without a valid holdout is a build failure. Every number that decides whether a result
may be stated is a contract value with an argument beside it rather than a constant in a module —
**[D]** `alpha: 0.05` and `target_power: 0.80`; the four thresholds `balance_tolerance_smd: 0.10`,
`exposure_min_pct: 95`, `holdout_share_pct: 20` and `neighbour_radius_m: 1000`; and two declared
budgets, `permutation_draws: 1000` and `max_assignment_attempts: 10000`. The alternative was a block of `Decimal`
constants in a `.py` file, which is precisely the *value without a source* the contract layer
exists to refuse: **doctrine rule 3 does not care what extension the file has.**

Anything that can be chosen after the fact will be chosen after the fact. An α chosen per
experiment is the most valuable dial in the building.

---

## The synthetic corpus — what it models, and what it does not

`corpus/world/` generates the chain the claims are proved against. It is a **stream**, not a
directory: a world is a pure function of `(world, seed, scale)`, so it is reproducible by anyone
who clones the repository and is regenerated rather than committed — the exact opposite of
`corpus/real/`, which is committed and digest-checked precisely because it *cannot* be
regenerated.

**Nothing under `corpus/` imports `holdout`**, enforced by `ops/isolation.py` with a test as the
gate and a harness hook that refuses the write before it lands. The reason is mechanical: if the
generator and the estimator shared a *compute margin* function, a bug in it would cancel out and
both would agree on a wrong number. The only thing they share is `ladder_policy@v1.yaml`, read
as **data** — because the control arm of a fresh-markdown experiment *is* the existing policy,
and a generator running some other schedule would be simulating a chain this system does not run.

### What it models

Baseline demand by store, category, hour, weather and season. A non-linear price response with
reference-price memory, so a store that marks down all week teaches its shoppers a lower normal
price. Cross-price effects between substitutes inside a category. Stock and per-item expiry,
replenished from a deliberately naive forecast — popularity, store size, day of week and season,
which is what a planner has on the morning of the order and *not* the weather or the markdown
that has not happened yet. Sales censored by availability. ESL acknowledgements that sometimes
fail, in every world.

It emits four event streams and the three reference tables the ERP drops would carry:
`pos_lines · esl_acks · shelf_days · price_decisions`, plus
`store_master · product_master · cost_ledger`. The cost ledger **moves inside the corpus**, so a
sale at 14:00 has a cost as it was known at 14:00 to join to; `Chain` has no `current_cost`
attribute at all, because the easier wrong answer should not be available to reach for.

### The four scales, and what they cost

**[M]** `python -m corpus.world count --world W1 --scale <name>`, seed `holdout-w-0001`:

| | stores | SKUs | days | POS lines · W1 | what it is for |
|---|---:|---:|---:|---:|---|
| `smoke` | 12 | 9 | 21 | — | the suite — every mechanism fires at least once, in well under a second |
| `rehearsal` | 20 | 24 | 56 | — | a laptop — enough to estimate something |
| `harness` | 320 | 12 | 112 | **5,263,284** | `evals/uplift/` — the A/A harness at K = 200 |
| `scenario` | 100 | 120 | 244 | **39,248,500** | the declared corpus |

`corpus/world/README.md` carries the same command's output for all six worlds at both scales,
with the seed that produced each. One property holds across every row of it: **a world's
acknowledgements match its decisions exactly**, because a label that refuses a price still
answers. `accepted` is a column rather than a missing row, so exposure is measurable by evidence
rather than by deletion — a world where a failed acknowledgement simply did not arrive would
have made it the other thing.

> **Two rows of that file did not reproduce, and writing this one is how it was found.**
> Recording a figure as `[M]` means running the command again, and W5's did not come back the
> same. At the same default seed, `python -m corpus.world count --world W5` prints
> **38,068,537 [M]** POS lines at `scenario` where the README records 33,582,648, and
> **5,028,772 [M]** at `harness` where it records 4,588,490; its acknowledgements and decisions
> come out **above** W1's rather than 40% below, which is the direction the prose beside the
> table asserts. W1 reproduces to the line at both scales, so this is not the seed.
>
> It is **T003 moving W5's pathology from the basket line to the store-day** — a change PLAN.md
> records, and one the README had not caught up with: its own six-worlds table still called W5
> *"heavy-tailed baskets"*, the pre-T003 wording, while `corpus/world/worlds.py` had said
> *"Heavy-tailed store-day demand"* since the move. The counts were taken before it. Both are
> restated in that file rather than overwritten, per doctrine rule 4, and the delta is the
> finding: **a measured table is only measured as of the last time somebody ran it**, which is
> the same rule as the one this file is written under, aimed one file along.

**A figure measured at one scale is reported at that scale.** `--only-stores` is a *window* onto
the same world, never a slice to be multiplied up, and the shelf-day count is the one figure in
the corpus tables that is arithmetic rather than a measurement.

**A world is a function of its seed**, so another seed is another hundred shops with another mix
of sizes and another total. Every figure above is reported with the seed that produced it for
that reason.

### What it does not model

Recorded rather than glossed, because each of these is a real gap and not merely a boundary:

- **It knows nothing about the guardrail envelope.** No floor, no ceiling, no regulated basket,
  no maximum daily delta — so it produces shelf prices `holdout.core.guardrails` would refuse,
  and the deepest rungs of the ladder sell below the cost the ledger records. That is what
  independence costs. A corpus that consulted the envelope would be a corpus that had met the
  gates it exists to be independent of.
- **No lateness and no duplicate delivery.** Event time equals arrival time here; those are
  `pipelines/ingest`'s to inject, and two places deciding how late a record is would eventually
  disagree.
- **No lottery, no estimator, no metric.** Assignment is an *input*. Nothing in the package
  computes a margin, an uplift or a confidence interval; the join between a world and the system
  lives in `evals/`.
- **No unserved demand.** `shelf_days` records that the shelf emptied and never what the
  stock-out hid, because a corpus that emitted it would be handing claim 4 the answer it exists
  to reconstruct.
- **No customer dimension anywhere.** Not a household, not a loyalty number, not a segment.
  Claim 7 is structural in `holdout.core.decision`, and it would be worth much less if the data
  underneath it had a person in it.
- **Six failure modes, not all of them.** The six worlds are the six somebody thought of. The
  estimator's validity does not come from passing them: a difference of means over randomly
  assigned units is unbiased under any data-generating process — a theorem, not an opinion. The
  worlds test whether the machinery *around* the subtraction preserves that validity. **The
  answer to "your simulator is rigged" is that validity comes from the lottery, not from the
  simulator.**
- **Its functional forms are the scenario's own assumptions.** A constant-elasticity price
  response, an exponentially weighted reference price, a sinusoidal season, the category
  elasticities. They are shaped to be plausible; **no chain's real figures were obtained and none
  is claimed.**

### The seal

The generator injects a known effect **on behaviour** — a schedule, an acknowledgement failure
rate, a decay — never on the metric. The effect on `category_margin_per_store_week` does not
exist anywhere until it is computed, and it is computed after the readout has been written, by a
separately written reference implementation that loops over every event.

The seal is an envelope rather than a lock and says so: the keystream is derived from a nonce
stored in the same file, so anyone who reads the module can decode it. What it guarantees is
narrower and is the half that matters — **the truth is never in the harness's process.** No
function returns it, no object a caller holds carries it, and the file yields nothing to `grep`.
The realistic failure it prevents is a number in scope at the moment an estimate is formed, and
a small unexamined decision made because of it.

---

## What is not in here

Two numbers were excluded by this file's own rule, and naming them is cheaper than letting
somebody rediscover the absence.

**"ESL penetration is ~30% of large European retailers."** `CLAUDE.md` carries it as the reason
free dynamic pricing everywhere is impossible. It is not **[M]** — no command here produces it.
It is not **[D]** — no contract holds it, so `make contracts` has never asked it for a source. It
is not **[S]** — it asserts a fact about the world rather than describing the scenario. And it is
not **[C]**, because there is no publisher, no URL and no verification date behind it anywhere in
the repository. It is a number about the outside world with nothing standing behind it, which is
the one shape `docs/REGULATORY.md` was written to make impossible for a guardrail — and the
argument it supports (that the *display* rules bind, and that a price cannot be changed on a
shelf that has no electronic label) does not need it. `docs/DECISIONS.md` carries it as a
deferral, with both an unlock condition and a date, rather than it being fixed here: this is a
documentation branch, and editing `CLAUDE.md`'s envelope table on it would be a change nobody
asked for, made in the file that governs every other branch and is least reviewed on this one.

**The corpus's own placement constants** — the per-world share of a town's stores opened inside
the exclusion radius, and the area the estate gives each store. Both carry a real argument where
they live, and both say in as many words that no chain's real footprint was obtained. But they
are not contract values, so they are not **[D]** as this file defines it, and `make contracts`
cannot reach them.

**And they should not become contract values, which is why this is structural rather than
sloppy.** The corpus reads exactly one contract — `ladder_policy@v1.yaml`, as data — and it reads
that one because the control arm of a fresh-markdown experiment *must* be the existing policy.
Everything else about the estate is deliberately the generator's own, and
`contracts/design/inference.yaml` states the reason about the two `carryover:` facts these
constants sit beside: they are **not** observations of anything in this repository, because
resting a refusal on what the generator does would be the generator and the engine agreeing with
each other. A placement constant promoted into `contracts/` would be exactly that, on the one
quantity claim 2 turns on.

So what goes into this file instead is **the roster they produce**, which is measured and which
is the quantity a claim actually rests on. The constants themselves are in
`corpus/world/worlds.py` and `corpus/world/chain.py`, with their arguments beside them.

---

## What this file does not settle

- **Which claims are proved, and how.** `CLAUDE.md` has the seven and their traps; `PLAN.md` has
  what has closed. This file deliberately republishes **no** claim's published figures: those are
  each eval's evidence, printed on every run, and a copy of them here would be a number in a
  place nothing executes.
- **Why any of this was decided.** `docs/DECISIONS.md`, with the reversals written underneath the
  originals.
- **The legal argument.** `docs/REGULATORY.md`, with the article, the quote and the date each
  URL was opened.
- **The manual work with no API.** `docs/DAY-ONE.md`, which does not exist yet and has nothing to
  record until there is an estate.
