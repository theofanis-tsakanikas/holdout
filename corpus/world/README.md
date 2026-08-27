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
| **W2** | real effect + interference between neighbouring stores | SUTVA | **detect and refuse**, never estimate |
| **W3** | real effect + exposure fails on 30% of treated units | assignment ≠ exposure | refuse below the threshold — never silently dilute |
| **W4** | an effect that decays (novelty) | a constant effect over the window | report the window's average, not the first week extrapolated |
| **W5** | heavy-tailed baskets | the variance the power calculation assumed | the power check fails, or the interval is honestly wide |
| **W6** | everything works, a real effect is present | nothing — and that is the point | **produce the number.** No refusal |

**W6 matters as much as W1.** A system that refuses everything passes every other world and is
worthless, which is why the false-refusal rate is published beside the false-positive rate.

**W1 needs no ground truth at all.** Its treatment policy *is* its control policy, and
`tests/corpus/test_world_determinism.py` asserts the consequence byte for byte: under W1 the
assignment changes nothing in the whole stream except the arm label on the decision record.
Empty is empty, so nobody has to take the simulator's word for anything.

---

## The chain

100 stores, three fresh categories, 40 SKUs each, 244 days — 2025-09-01 to 2026-05-02, eight
months to the day. The three categories are `dairy`, `bakery` and `poultry`, which are the
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

Every second store a town gets is opened within 700 m of one the chain already has there —
stated as a rule rather than a probability, because **W2 exists to be detected and every scale
has to contain the thing it detects**. Scattering stores uniformly gave zero neighbour pairs
at 20 stores and a handful at 100.

---

## What it emits

Four event streams, in the source's shape, plus the three reference tables Lakeflow Connect
would pull from the ERP:

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

## Three scales

| | stores | SKUs | days | what it is for |
|---|---|---|---|---|
| `smoke` | 12 | 9 | 21 | the suite — every mechanism fires at least once, in well under a second |
| `rehearsal` | 20 | 24 | 56 | a laptop — enough to estimate something |
| `scenario` | 100 | 120 | 244 | the declared corpus |

At the scenario scale, with the default seed `holdout-w-0001`, from
`python -m corpus.world count --world Wn --scale scenario` — about 150 seconds per world:

| | POS lines | ESL acks | shelf days | price decisions |
|---|---:|---:|---:|---:|
| **W1** | 36,676,068 | 1,876,392 | 2,928,000 | 1,876,392 |
| **W2** | 36,266,964 | 1,997,911 | 2,928,000 | 1,997,911 |
| **W3** | 37,510,813 | 1,825,055 | 2,928,000 | 1,825,055 |
| **W4** | 37,349,168 | 1,827,013 | 2,928,000 | 1,827,013 |
| **W5** | 31,465,861 | 1,132,484 | 2,928,000 | 1,132,484 |
| **W6** | 37,292,793 | 1,837,333 | 2,928,000 | 1,837,333 |

**36.7M POS lines** on the null world, against the *"about 36M"* `CLAUDE.md` declares. The shelf
day count is identical everywhere and is the only figure in the table that is arithmetic rather
than a measurement: 100 stores × 120 SKUs × 244 days, one row each, whatever happened on them.

Two of the rows say something. **W5 is nearly 6M lines short of the others**, because a
heavy-tailed basket empties a shelf in fewer transactions and a shelf that is empty sells
nothing else that day — and its price decisions are down by 38% for the same reason: stock that
has already gone never reaches a markdown rung. **W3's acknowledgements match its decisions** exactly, as
they do in every world: a label that refuses the new price still answers, and `accepted` is a
column rather than a missing row. A world where a failed acknowledgement simply did not arrive
would make exposure unmeasurable by deletion instead of by evidence.

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
python -m corpus.world count --world W6 --scale scenario
python -m corpus.world write --world W2 --scale rehearsal --out .worlds/W2
python -m corpus.world seal .worlds/W2        the header and the ledger — never the payload
```

**Nothing here is committed.** A world is a pure function of `(world, seed, scale)`, so the
corpus is regenerated rather than stored — which is the exact opposite of `corpus/real/`,
where the data is committed and digest-checked precisely because it *cannot* be regenerated:
those prices were written down by hand in shops by people who have never seen this repository.
Two corpora, two opposite rules, one reason each.

`write` produces gzipped CSV. `CLAUDE.md` describes the scenario corpus as *"a few GB of
Parquet"*, and on the estate it will be — the S3 bulk load in phase 3 is what writes those
files. Here the product is a **stream**, consumed in process by the A/A harness, and adding a
Parquet engine to `corpus/` to write files nothing in phase 1 reads would be a dependency
bought for a screenshot. `docs/DECISIONS.md` records it with the condition that unlocks it.

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
