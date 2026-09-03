# `corpus/world/` — six worlds that break six different assumptions

Claim 2's trap, in `CLAUDE.md`'s words: *"a simulator generating data from the process the
estimator assumes is the estimator agreeing with itself."* This directory is the half of the
answer that produces the data.

The other half is that it does not matter very much what is in here. A difference of means
over randomly assigned units is unbiased **under any data-generating process** — that is a
theorem, not our opinion. So these worlds are not trying to be right about grocery retail.
They are trying to break the **machinery** around the subtraction: assignment, exposure
collection, the four validity checks, the readout. **The answer to "your simulator is rigged"
is that validity comes from the lottery, not from the simulator.**

**Nothing here imports `holdout`.** Not the estimator, not `Money`, not a refusal code, not
the ladder. `ops/isolation.py` is the one implementation of that rule;
`tests/boundary/test_corpus_imports_nothing.py` is the gate, and
`.claude/hooks/corpus_isolation.py` refuses the write before it lands. The reason is
mechanical rather than aesthetic: if the generator and the estimator shared a "compute margin"
function, a bug in it would cancel out and both would agree on a wrong number.

---

## The six worlds

| | the world | what it violates | the correct behaviour |
|---|---|---|---|
| **W1** | pure noise, true effect zero | nothing — this is the null | no significant uplift, at a rate ≤ α |
| **W2** | real effect + interference between neighbouring stores | SUTVA | **exclude the interfering units at design**, then estimate on what is left |
| **W3** | real effect + exposure fails on 30% of treated units | assignment ≠ exposure | report ITT with the realised rate printed, or refuse below the declared threshold — never silently dilute |
| **W4** | an effect that decays (novelty) | a constant effect over the window | no result before the declared end, then report what the declared window aggregated |
| **W5** | heavy-tailed **store-day** demand | the variance the power calculation assumed | the power check fails, or the interval is honestly wide |
| **W6** | everything works, a real effect is present | nothing — and that is the point | **produce the number.** No refusal |

**W6 matters as much as W1.** A system that refuses everything passes every other world and is
worthless, which is why the false-refusal rate is published beside the false-positive rate.

**W1 needs no ground truth at all.** Its treatment policy *is* its control policy, and
`tests/corpus/test_world_determinism.py` asserts the consequence byte for byte: under W1 the
assignment changes nothing in the whole stream except the arm label on the decision record.
Empty is empty, so nobody has to take the simulator's word for anything.

---

## The chain

At the declared `scenario` scale: 100 stores, three fresh categories, 40 SKUs each, 244 days —
2025-09-01 to 2026-05-02, eight months to the day. Every scale is the same chain at a different
size; the four are in **Four scales** below, and the one the A/A harness runs on is `harness`,
which has *more* stores and fewer SKUs for the reason that section gives. The three categories are `dairy`, `bakery` and `poultry`, which are the
three `contracts/guardrails/regulated_basket.yaml` calls "the synthetic scenario's own fresh
categories". The world does **not** read that contract for them — it would be reading a
guardrail to decide what a shop sells — so they are two lists, and
`tests/corpus/test_world_chain.py` fails the build when they disagree.

What the simulation actually does, per store, per day, per SKU:

- **baseline demand** by store, category, hour, weather and season;
- a **non-linear price response with reference-price memory** — a store that marks down all
  week teaches its shoppers a lower normal price, so the same absolute cut is a smaller cut on
  Friday than it was on Monday;
- **cross-price effects between substitutes** inside a category;
- **stock and per-item expiry**, replenished from a deliberately naive forecast — popularity,
  store size, day of week and season, which is what a planner has on the morning of the order,
  and *not* the weather or the markdown that has not happened yet;
- **sales censored by availability**: when the shelf empties the baskets stop, and nothing in
  the corpus records the ones that were never rung up;
- **ESL acknowledgements that sometimes fail**, in every world and not just W3.

Two of those exist to make later claims hard rather than to be realistic. Reference-price
memory is what makes a `store_week` unit interfere with itself; cross-price substitution is
what makes a `store_category` unit interfere with itself. Both are declared in
`contracts/design/inference.yaml`'s `carryover:` block as assumptions about the trade, and the
design engine refuses those two units on the strength of the **contract**, never on the
strength of anything measured here.

### Geography is planar, and that is a declared assumption

Stores sit at integer metre offsets from their town centre, so "under 1 km" is an exact
integer comparison rather than a geodesic carrying an implicit datum. A real `store_master`
would carry latitude and longitude; this one does not, because the only question the scenario
ever asks of geography is the neighbour radius, and answering it exactly matters more than
looking like a GIS extract.

A share of each town's stores is opened within 700 m of one the chain already has there — a
**quota per town rather than a coin per store**, because W2 exists to be detected and every
scale has to contain the thing it detects, and a probabilistic cluster would have made the
smoke scale's pairs depend on the seed.

### How close the shops are is the size of the roster — restated 2026-08-28 (T00E)

This section read *"every second store a town gets is opened within 700 m of one the chain
already has there"*, as a fixed rule, and the town was a fixed 10 km across at every scale.
Both were deliberate and both were wrong in the same way: **nobody multiplied them by the
design engine's exclusion rule.** The engine drops the later-sorted member of every pair
inside the declared 1 km radius, so every clustered store is a store no experiment may use.

Measured before the change: 100 stores gave 109 neighbour pairs, 55 exclusions and a
**surviving roster of 45** — a control arm of nine, on which no lottery in two hundred passed
the readout's balance check. And it got worse rather than better with scale, because the towns
did not grow: **1,200 stores left a roster of 212**. The usable estate saturated.

> **Restated 2026-08-31 by `docs/layout-and-restatements`, completing a chain that stopped at
> `CLAUDE.md` on 2026-08-29.** `1,200 stores left a roster of 212` is written above as a
> measurement and it is not one. `--scale` admits exactly four names — `smoke`, `rehearsal`,
> `harness`, `scenario` — and the largest is **320 stores**. No declared scale reaches 1,200, so
> that figure was a projection appearing in a paragraph whose argument is that the load-bearing
> number is the surviving roster rather than the store count. It is **withdrawn rather than
> corrected**: 1,200 stores is the scenario the system is written for, not a scale this
> repository has ever run.
>
> The 100-store chain above it is also stale — it was measured before **T00E** moved the
> placement rule. `python -m ops.roster` is the one place the number lives, and `CLAUDE.md`
> carries the table it now prints.
>
> **What survives is the argument, untouched**: the number a claim rests on is the roster a
> lottery is drawn over. What did not survive is the figure that asserted it, which is the rule
> about a rule not being exempt from itself, for the second time on the same paragraph.

Two numbers are declared now, and neither is a constant somebody needed:

| | what it fixes | value |
|---|---|---|
| `worlds.World.clustered_pct` | the share of a town's stores opened inside the exclusion radius, **per world** | 15% in W1, W3, W4, W5, W6 · **30% in W2** |
| `chain.AREA_PER_STORE_M2` | the estate's density, so the town's placement square grows with the stores it holds | 64 km² per store — an 8 km square each |

**Per world, because only W2 needs interference to exist.** It is high there and realistic in
the other five — and it is 30% rather than higher because W2's declared correct behaviour is to
*estimate on what is left*, and an estate that excluded so much that nothing was left would
pass the interference half while making the estimate impossible. The choice is **nested**: the
stores clustered at 15% are a subset of those clustered at 30%, so W2's estate is the realistic
estate with more of the same rather than a different one, and everything else about a store —
its format, its size, its zone, its opening date — is identical in all six worlds.

Neither number is measured from a real chain and neither is claimed to be, which is the same
sentence this README's *Declared assumptions* section makes about the demand shapes.

### What survives, per world

`make roster` — or `python -m ops.roster --scale harness`. It lives in `ops/` because the
answer is a joint fact about this package's geography and
`holdout.core.design.feasibility.neighbour_exclusions`, and the corpus may not import the
system: a second copy of the exclusion rule in here would be the one that goes stale.

At the `harness` scale, seed `holdout-w-0001`, at the contract's 20% holdout share:

| world | clustering | stores | pairs | excluded | **surviving roster** | control arm |
|---|---:|---:|---:|---:|---:|---:|
| W1 · W3 · W4 · W5 · W6 | 15% | 320 | 59 | 51 | **269** | 53 |
| W2 | 30% | 320 | 148 | 98 | **222** | 44 |

Across eight world seeds the worst world never drops below 218 at this scale. And the number
that actually decides whether an experiment can report anything — how often a stratified draw
lands inside the 0.10 balance tolerance — moves with it:

| roster | control arm | draws inside the tolerance |
|---|---:|---|
| 45 (100 stores, before T00E) | 9 | **0 of 200** |
| 100 (no exclusions at all, for reference) | 20 | 30 of 100 |
| 265–269 (W1, W3–W6) | 53 | **145–192 of 200**, over three world seeds |
| 218–222 (W2) | 43–44 | **121–172 of 200**, over three world seeds |

The remaining refusals are sampling spread on the numeric covariates, not structure: with a
finite control arm a covariate the others carry no information about keeps a spread near the
tolerance, and `strata.py` owns that limit. **The rate is a number claim 2 publishes, not one
this package asserts away.**

---

## What it emits

Four event streams, in the source's shape, plus the three reference tables the ERP's file
drops carry:

```
pos_lines · esl_acks · shelf_days · price_decisions
store_master · product_master · cost_ledger
```

- **`price_decided` and `price_displayed` are two columns and they differ.** The displayed
  price comes from the acknowledgement, never from the decision. A world in which they never
  differed would let a reader take either one and be right, and exposure would be a column
  nobody ever had to look at.
- **`transaction_id` is a business key, not a hash of the payload.** The world injects the
  case that distinction exists for, at a declared rate: two receipts, same till, same second,
  identical contents, two different ids. A payload hash would collapse them into one and
  quietly delete a sale.
- **The cost ledger moves inside the corpus**, so a sale at 14:00 has a cost as it was known
  at 14:00 to join to. `Chain` has no `current_cost` attribute at all — the easier, wrong
  answer is not available to reach for.
- **`shelf_days` records that the shelf emptied and never what the stock-out hid.** A corpus
  that emitted the unserved demand would be handing claim 4 the answer it exists to
  reconstruct.
- **There is no customer dimension anywhere.** Not a household, not a loyalty number, not a
  segment. Claim 7 is structural in `holdout.core.decision`, and it would be worth much less
  if the data underneath it had a person in it.

Event time equals arrival time here. A generator that invented lateness would be inventing the
pathology `pipelines/ingest` exists to inject, and two places deciding how late a record is
would eventually disagree.

---

## Four scales

| | stores | SKUs | days | surviving roster | what it is for |
|---|---|---|---|---|---|
| `smoke` | 12 | 9 | 21 | — | the suite — every mechanism fires at least once, in well under a second |
| `rehearsal` | 20 | 24 | 56 | — | a laptop — enough to estimate something |
| `harness` | 320 | 12 | 112 | **269 · 222 (W2)** | `evals/uplift/` — the A/A harness, K = 200 |
| `scenario` | 100 | 120 | 244 | 83 · 66 (W2) | the declared corpus |

**The fourth column is the one that decides whether anything is provable**, and it is why
`harness` has more stores than `scenario` rather than fewer. `CLAUDE.md` says it in a line: the
size a claim rests on is the roster that survives the design engine's automatic exclusions, not
the store count. `harness` trades SKUs and days — what the clock sees — for stores, which is
what the statistics see, and lands at about 21 s per world either way. Measured, per world,
with `python -m corpus.world count --scale harness`:

| | POS lines | ESL acks | shelf days | price decisions | seconds |
|---|---:|---:|---:|---:|---:|
| **W1** | 5,263,284 | 358,040 | 430,080 | 358,040 | 21.2 |
| **W2** | 5,282,580 | 370,036 | 430,080 | 370,036 | 21.2 |
| **W3** | 5,400,461 | 352,332 | 430,080 | 352,332 | 21.6 |
| **W4** | 5,388,111 | 349,616 | 430,080 | 349,616 | 21.7 |
| **W5** | **5,028,772** | **367,376** | 430,080 | **367,376** | 18.6 |
| **W6** | 5,364,336 | 354,096 | 430,080 | 354,096 | 21.9 |

At the scenario scale, with the default seed `holdout-w-0001`, from
`python -m corpus.world count --world Wn --scale scenario` — about 150 seconds per world:

| | POS lines | ESL acks | shelf days | price decisions |
|---|---:|---:|---:|---:|
| **W1** | 39,248,500 | 1,869,441 | 2,928,000 | 1,869,441 |
| **W2** | 39,264,442 | 1,922,012 | 2,928,000 | 1,922,012 |
| **W3** | 40,228,156 | 1,818,638 | 2,928,000 | 1,818,638 |
| **W4** | 40,041,576 | 1,820,154 | 2,928,000 | 1,820,154 |
| **W5** | **38,068,537** | **1,945,238** | 2,928,000 | **1,945,238** |
| **W6** | 39,976,813 | 1,830,229 | 2,928,000 | 1,830,229 |

> **Restated 2026-08-28 (T00E), because the chain moved.** The table read 36.7M POS lines on
> W1 and 36.3M on W2, taken before the placement rule changed. It is restated rather than
> overwritten, per doctrine rule 4, and the delta is worth reading: **the counts rose by about
> 7% and W2's fell relative to W1's rather than rising.** Both follow from the same edit. A
> store's coordinates are now drawn from its own stream in *both* branches and overridden when
> it is clustered, where before the clustered branch consumed a different number of draws — so
> every previously-clustered store's size, zone and opening date shifted, and a chain with a
> different mix of store sizes sells a different number of lines. And W2 now has fewer stores
> pulling trade from a neighbour, because 30% of a town is clustered where every second store
> used to be.
>
> `demand.BASE_LINES_PER_SKU_DAY` is **left where it was.** It was calibrated once so the
> scenario lands near the corpus `CLAUDE.md` declares, and 39.2M against *"about 36M"* still
> does. Re-tuning it to land back on the old figure would be fitting the corpus to a sentence,
> which is the opposite of what a measured constant is for.

**39.2M POS lines** on the null world, against the *"about 36M"* `CLAUDE.md` declares. The shelf
day count is identical everywhere and is the only figure in the table that is arithmetic rather
than a measurement: 100 stores × 120 SKUs × 244 days, one row each, whatever happened on them.

One of the rows says something. **W3's acknowledgements match its decisions** exactly, as
they do in every world: a label that refuses the new price still answers, and `accepted` is a
column rather than a missing row. A world where a failed acknowledgement simply did not arrive
would make exposure unmeasurable by deletion instead of by evidence.

> **Restated 2026-08-30 (T007), because W5's four counts did not reproduce.** Both tables above
> carried W5 at **4,588,490** POS lines and **202,080** acknowledgements at `harness`, and
> **33,582,648** and **1,119,581** at `scenario`. Re-run at the same default seed while
> `docs/SCENARIO.md` was being written, the command prints **5,028,772 / 367,376** and
> **38,068,537 / 1,945,238**. W1 reproduces to the line at both scales, so it is not the seed.
>
> The prose that sat here said **"W5 is over 6M lines short of the others"** and **"its price
> decisions are down by 40%"**, and explained both by a heavy-tailed *basket* emptying a shelf
> in fewer transactions. Neither half survives: W5 is about 1.2M lines short at `scenario`, and
> its decisions come out **above** W1's rather than 40% below. Both sentences are withdrawn
> rather than corrected, because the mechanism they described is not the one the world has.
>
> **The cause is in this file's own first table, one screen up.** T003 moved W5's pathology off
> the basket line and onto the store-day — a heavy tail on a basket is averaged away by the
> sixteen thousand of them the metric aggregates, which is why the world with the declared
> variance pathology had measured a standard error *below* the world with none. The counts here
> were taken before that move, and the six-worlds table still read *"heavy-tailed baskets"*
> while `worlds.py` had read *"Heavy-tailed store-day demand"* since the day it changed. That
> row is corrected above.
>
> The prior figures stay per doctrine rule 4, and the delta is the finding: **a measured table
> is measured only as of the last time somebody ran it.** Nothing in the repository re-runs
> these — `docs/DECISIONS.md` already carries *"the scenario scale is measured by hand, not by a
> gate"* as a deferral, and this is the first time that deferral cost something. It is a figure
> in a README rather than a figure in a claim, which is the reason it cost only this much.

Every one of those figures comes from the command above, not from arithmetic on a smaller run. `CLAUDE.md` forbids extrapolating a corpus-size figure to the full estate, and the same
rule applies one level down: `--only-stores` is a **window** onto the same world and a count
over it is reported as a count over it.

**The chain is a function of the seed**, so another seed is another hundred shops with another
mix of sizes and popularity, and another total. The figure above is reported with the seed
that produced it for that reason.

---

## The seal

`CLAUDE.md`: *"the injected truth lives in a sealed file the harness opens **only after** the
readout has been written."*

What is sealed is **behaviour** — which schedule the treated arm was given, how many labels
never took the price, how fast the novelty decayed. What is *not* sealed, because it does not
exist anywhere, is the effect on the metric: the generator injects three more units per store,
not four thousand euros per week. The true effect on `category_margin_per_store_week` has to
be **computed**, by re-running the world under all-control with the same seed and looping over
every event. That is T003's reference implementation, and it happens after the readout for the
same reason the file is shut.

**It is not encryption and it is not trying to be.** The keystream is derived from a nonce
stored in the same file. Calling it a lock would be the kind of sentence this repository
exists to refuse. What it is:

- **The accident is impossible.** The truth is never in the harness's process. `events()`
  filters the exposure records out of the stream, no object a caller holds has them as an
  attribute, and the file yields nothing to `cat`, `grep`, a diff or an editor. The realistic
  failure — a number in scope at the moment an estimate is formed, and a small unexamined
  decision made because of it — has nowhere to happen.
- **The legitimate opening is recorded.** `open_after_readout` refuses without a readout that
  exists and appends its digest to an append-only ledger inside the seal, so an eval can
  assert exactly one opening against exactly the readout that was published.
- **A quiet edit is caught**, by a SHA-256 commitment over the plaintext.
- **A window's truth says it is a window.** A run restricted with `--only-stores` seals the
  exposure of those stores and records the restriction, because a rate over three stores
  wearing the whole world's name is exactly the kind of number this repository refuses to let
  anyone quote.

**The limit, stated rather than papered over.** A coordinated rewrite — decode, change,
re-seal with a fresh commitment, forge the ledger — is not caught, because a seal never held
independent evidence of its own provenance. `tests/corpus/test_world_seal.py` performs that
forgery and asserts that it succeeds, rather than describing the limit in prose beside the
code. It is the same shape as the certificate type's limit in `holdout.core.guardrails`, and
it is worth stating in the same words: **it makes the mistake impossible and leaves the
forgery visible.**

---

## Running it

```
make world                                    all six, at smoke scale, counted
make roster                                   how much of the estate survives the exclusions
python -m corpus.world count --world W6 --scale scenario
python -m corpus.world write --world W2 --scale rehearsal --out .worlds/W2
python -m corpus.world write --world W2 --scale smoke --out .worlds/pq --format parquet
python -m corpus.world seal .worlds/W2        the header and the ledger — never the payload
```

`make roster` is the odd one out and deliberately so: it is the only command here that is not
in this package, because the answer is a joint fact about this geography and the design
engine's exclusion rule, and this package may not import that engine. `ops/roster.py` says why
at more length.

**Nothing here is committed.** A world is a pure function of `(world, seed, scale)`, so the
corpus is regenerated rather than stored — which is the exact opposite of `corpus/real/`,
where the data is committed and digest-checked precisely because it *cannot* be regenerated:
those prices were written down by hand in shops by people who have never seen this repository.
Two corpora, two opposite rules, one reason each.

`write` produces gzipped CSV by default and Parquet on request. The deferral that kept it to
one target — *"adding a Parquet engine to `corpus/` … to write files nothing in this phase
reads would be a dependency bought for a screenshot"* — named the moment it ends: **the S3
bulk load in T009, the first thing that needs files on disk in the format the lakehouse
reads.** `corpus/world/parquet.py` is that engine, written out of the standard library, and
the file that says why the check on it comes from pyarrow in the dev group rather than from a
reader written here.

**What the second target costs, measured on W6 at smoke scale rather than assumed.** Parquet
is not a size win here and the numbers say so plainly:

| table | rows | `.csv.gz` | `.parquet` | |
|---|---:|---:|---:|---|
| `pos_lines` | 32,858 | 366,231 | 361,262 | 0.99x |
| `shelf_days` | 2,268 | 16,406 | 11,199 | 0.68x |
| `esl_acks` | 916 | 4,616 | 3,421 | 0.74x |
| `price_decisions` | 916 | 4,740 | 3,399 | 0.72x |
| `store_master` | 12 | 484 | 1,449 | **2.99x** |
| `product_master` | 9 | 244 | 838 | **3.43x** |
| `cost_ledger` | 35 | 349 | 675 | **1.93x** |

**At rehearsal scale, once, the four streams look better and the writing is faster**: 430,649
records, six row groups on `pos_lines`, 4,420,531 bytes against 4,483,401 as gzipped CSV
(0.99x) and 0.23x to 0.62x on the other three — written in **4.1s against 5.8s** for the CSV
target. One run, on one machine, on one world; the three reference tables at that scale are the
same nine and twenty rows they are at smoke, so their penalty does not move.

The three reference tables are **larger**, by up to 3.4x, because a footer describing ten
columns costs more than ten rows of data — and `pos_lines` barely wins because this writer has
no dictionary encoding, so a store id repeated thirty thousand times is written out thirty
thousand times and only gzip notices. **The reason to write Parquet here is that it carries a
schema and a type, not that it is smaller**: a `date` is a date and an absent substitute is a
null rather than an empty cell, which is what the loader in `pipelines/ingest/` is handed
instead of a guess. Measured at one scale, on one world, and reported as such.

---

## The one thing it shares with the system

`contracts/policies/ladder_policy@v1.yaml`, read as **data** by `policy.contract_ladder` —
`yaml.safe_load` and a dictionary lookup, not `holdout.contracts.loader`. The control arm of a
fresh-markdown experiment *is* the existing policy (*"the holdout does not mean nothing, it
means the existing policy"*), so a generator running some other schedule would be simulating a
chain this system does not run, and every uplift ever measured against it would be an uplift
against a fiction.

No code crosses. The world rounds a markdown **half-up on the cent**, which is deliberately
not `holdout.core.money`'s rounding — the core rounds a price half-even and a bound away from
what it forbids, for reasons that belong to the guardrail set, and a till does not know about
any of that. If the two ever have to agree on a number they must agree by computing it
separately and matching.

---

## Declared assumptions, and what was calibrated

The functional forms — a constant-elasticity price response, an exponentially weighted
reference price, a sinusoidal season, the category elasticities, the ladder's effect on
demand — are the scenario's own assumptions about grocery retail. They are shaped to be
plausible. **No chain's real figures were obtained and none is claimed here**, which is the
same sentence `contracts/policies/ladder_policy@v1.yaml` uses about its own rungs.

Three constants were **calibrated by measurement** rather than chosen, and each says so where
it lives: `demand.BASE_LINES_PER_SKU_DAY`, so the scenario scale lands near the corpus
`CLAUDE.md` declares; `generate.SERVICE_FACTOR` and `generate.EXPIRING_TODAY_CREDIT`, which
between them decide how much fresh is thrown away and how often a shelf empties. A world with
no waste would have deleted the markdown ladder's whole reason to exist.

**What calibration deliberately did not record.** The treatment policy in `policy.candidate`
was chosen by running it against its own counterfactual, so the sign of its effect is known
and is disclosed there: it is real and it is positive, which is what W6 requires of it — a
world where nothing happens is W1 and already exists. The *magnitude* is written down nowhere,
including here, because it moved by a factor of four between seeds and by more than that
between scales. There is no such number as "the effect of this policy": there is only the
effect in a given world, computed after the readout. That is not a limitation of the corpus.
It is the thing the project is about.

---

## What is deliberately not in here

- **No estimator, and no metric.** Nothing in this package computes a margin, an uplift or a
  confidence interval. The join between a world and the system lives in `evals/`.
- **No lottery.** Assignment is an *input*. The lottery belongs to
  `src/holdout/core/experiment/`, and a generator that drew its own arms would have met the
  engine it is supposed to be independent of.
- **No lateness and no duplicate delivery.** Those are `pipelines/ingest`'s to inject.
- **No day window.** `--only-stores` exists; there is no `--only-days`, because stock,
  reference prices and the replenishment forecast all carry across days. Day 200 exists only
  after days 0 to 199 have happened, and a day window would be a different world wearing the
  same name.
- **Six failure modes, not all of them.** These are the six we thought of. The worlds do not
  test the subtraction; they test whether the machinery around it preserves a validity the
  subtraction already had.
