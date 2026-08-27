# Claim 1 — no price reaches a shelf without the guardrail set

> The actuation type cannot be constructed without a guardrail certificate. The envelope —
> floor, regulated basket, prior-price rule, max daily delta — is a versioned contract with
> effective dates.
>
> *Trap: a planter reading the same contract as the detector is one function agreeing with
> itself → the gates are attacked from an independent corpus of real price lists.*

```
make claim-1          the eval and the fourteen planted mutations
make eval-guardrail   the eval alone, about ten seconds
```

---

## 1 · What is attacked

Every quote in `corpus/real/` is turned into a decision this system would have had to take,
and driven through `certify` against eight envelopes. Then one question, asked nine ways:
**does a price ever escape?**

| id | the question it would answer `false` |
|---|---|
| `G1.only-a-certificate-reaches-a-shelf` | is a certificate the only thing the actuator accepts, and is a refusal always rejected by it? |
| `G2.certified-price-inside-exact-bounds` | does every certified price satisfy this eval's **own** exact recomputation of every rule, with no tolerance? |
| `G3.refusal-supported-by-exact-arithmetic` | does every refusal have something to refuse — or lie within the one cent the core's conservative rounding may claim? |
| `G4.empty-range-is-really-empty` | when the answer is donation or disposal, is the admissible range really empty? |
| `G5.frozen-category-never-certified` | do the real cigarette, spirit, infant-formula and fish prices all refuse, naming the frozen category? |
| `G6.ladder-certifies-on-real-base-prices` | does the declared safe state ever produce a price refused by a bound it is built to satisfy? |
| `G7.closed-vocabulary-only` | is every reason a declared code carrying a detail, so the evidence is a count? |
| `G8.every-refusal-code-is-reached` | does this eval construct an input for **every** code, so no gate passes by never being tried? |
| `G9.no-tampered-certificate-reaches-a-shelf` | do the declared tampers still fail to dispatch, on certificates issued from real prices? |

`G2` is the one that carries the claim. The rest bound the ways it could be passing for the
wrong reason.

---

## 2 · Where the independence is

Four separations, strongest last.

**The prices are not ours.** Every price, base price, prior price and week-opening price is
an individual price quote the UK Office for National Statistics collected by hand in a shop
and published under the Open Government Licence. Nobody who chose those numbers has read
`contracts/guardrails/`. The corpus covers real dispersion across 811 outlet strata, real
price endings — `.00`, `.50`, `.95`, `.99` — and 1,577 real markdowns taken by real
retailers.

**The regulated list is not ours, and it disagrees with our contract.**
`contracts/guardrails/regulated_basket.yaml` names three categories and declares them a
`scenario_assumption`, because when it was written the ministerial decision had not been
obtained. It has been now: ΥΑ 21330/12.03.2026, ΦΕΚ Β΄ 1411, άρθρο 6, sixty-three categories.
The eval decides what is regulated from **that table**. An independent corpus that agreed
with the contract in every particular would not be independent.

**`corpus/real/` cannot see the system.** It imports nothing from `holdout` — no refusal
code, no `Money`, no opinion about whether a price is admissible — and
`tests/boundary/test_corpus_imports_nothing.py` fails the build if that ever changes. The
join between the two lives in `build.py`, in this directory, where it can be read as one
thing.

**The boundary is computed twice.** Driving the gates from outside answers *does it refuse*.
It does not answer *at the right place*, and if the only thing that knows where the boundary
is were `evaluate`, the eval would be asking a function to mark its own paper. `reference.py`
is a second implementation, deliberately a different shape: exact `Decimal` euros against
integer cents, one predicate per rule against one pass appending attributed bounds, and no
rounding at all against the core's declared conservative rounding. The two share the rule
*values* and nothing else.

---

## 3 · Observed, derived, swept

The distinction is kept sharp because doctrine rule 3 is the easiest rule in this repository
to break by accident.

| | |
|---|---|
| **observed** | prices, base prices, prior prices, week-opening prices, the 63 regulated categories, the industry gross margin |
| **derived**, with the arithmetic written out | the unit cost, and the benchmark margin the cap needs |
| **swept**, not claimed | how old the cost is, how many changes have been dispatched today, whether a decision announces a reduction |

**A retailer's unit cost is not public and never will be** — it is what a buyer negotiates.
Rather than write a plausible number, the corpus takes Eurostat's published gross margin on
goods for resale for Greek supermarkets (NACE 47.11) — a median of 16.81% of turnover across
thirteen years — and derives `unit_cost = price × (1 − 0.1681)`.

It is derived from the item's **median price across the whole corpus**, not from each row's
own price, and that choice does the work. A cost derived from the row's own price would make
the margin identical on every row and the floor would answer the same question thirty
thousand times. Deriving it from the item lets the real dispersion between outlets drive the
margin: about a fifth of the rows sit below their item's derived cost, which is what makes
the floor bite at all.

The **swept** inputs are walked over a declared, deterministic grid — never drawn at random,
so a red run reproduces exactly. The grid contains `4` dispatched changes for one reason: two
envelopes carry a budget of 4, and the only input that can tell `>=` from `>` is the one that
lands on the bound. `gate-proof`'s off-by-one mutation would survive without it.

`corpus/real/MANIFEST.yaml` argues each derivation, states which way it errs, and carries a
digest for every file so that none of this can be quietly adjusted.

---

## 4 · The envelopes

Eight. Three resolved from this repository's own `contracts/guardrails/` — the markdown path
with the 2026 margin cap in force, the same path after it lapsed on 30.06.2026, and the
base-price path. Those are what the production path would use, and attacking them is the test
that matters.

The other five are a **declared sweep**. Their numbers are not claims about any retailer; they
exist because an arithmetic that happens to be right at a 0% margin floor and wrong at 25% is
wrong, and only a sweep finds that. One of them carries
`cap_basis: unspecified_in_the_instrument` — the shape of ν. 4818/2021, which imposes a cap
and never says what the margin is measured on. `docs/DECISIONS.md` records that this window is
unreachable through `envelope_as_of`, so the branch that refuses rather than borrowing a
neighbouring regime's arithmetic is live code nothing drives. Here it is driven, by real
prices.

---

## 5 · What this does not prove

* **That the numbers in `contracts/guardrails/` are the right numbers.** No test can, and
  `make contracts` cannot either — it checks the *shape* of provenance, never its content.
  This eval shows the machinery honours whatever envelope it is handed. Whether the envelope
  is the right one is oversight level 2's job, and level 2 has already caught five citations
  that were wrong in exactly that way.
* **Anything about real retailers' costs.** The cost is derived and one industry-wide ratio
  is applied to every item, so it carries no information about which products earn more. It
  cannot manufacture a pass for the *system* — the eval's own exact recomputation uses the
  same derived cost, so a wrong cost moves both sides together — but the refusal counts are a
  property of that derivation and are reported as such.
* **That the guardrails hold against every possible input.** Thirty-two thousand real quotes
  is a large sample of real prices, not a proof over all prices.
* **That the corpus is Greek.** The ONS collects in pounds; the numeric value is used as an
  amount of euros, unconverted. It is a stated modelling choice: four of the five guardrails
  are percentages and therefore scale-free, and the fifth sits an order of magnitude below
  the cheapest quote. A conversion would add a daily-changing rate and buy no proof.

---

## 6 · Two findings

Neither is fixed on this branch, and both are recorded in `docs/DECISIONS.md` with the
condition that unlocks them. An eval that quietly widened an assertion to swallow what it
found would be worse than no eval.

### The ladder knows about a floor and not about a ceiling

`ladder.quote()` takes a `floor` and clamps to it. It takes no ceiling and knows of none. So
where the margin cap binds below the base price, the shallow rungs of the declared safe state
produce prices the envelope refuses — **7,366 of 26,600 ladder quotes** in this run, on the
repository's own contract envelope among others.

The guardrail set behaved perfectly: it refused, by name, for a true reason. What is
incomplete is doctrine rule 1. For an expiring product the safe state is the ladder, and here
the ladder's answer is itself refused — so there is nowhere left to fall. It is the same
*class* as the finding a review made by composing two modules that had only ever been tested
alone, and it was found the same way: by composing them over inputs nobody chose.

`G6` therefore asserts only the three bounds the ladder is built to satisfy — the max depth,
the absolute floor, the margin floor — and publishes the ceiling count beside it as a number.
The frequency depends on the derived cost, which is why this is a finding to investigate
rather than a defect to assert.

### `benchmark_margin_pct` does not say which denominator it is in

ΥΑ 21330/2026 άρθρο 4 παρ. 4 defines the capped margin as
`(selling price − average cost of goods sold) ÷ selling price` — a fraction of the **price**.
`evaluate` bounds the price at `cost + cost × benchmark_margin_pct`, a mark-up on **cost**.
The two are the same constraint in different denominators and `m / (1 − m)` converts exactly,
which is what `build.py` does.

But `contracts/guardrails/regulated_basket.yaml` names its benchmark `average_gross_margin_2025`,
and the instrument that defines that quantity defines it over the price. Feeding it straight
in would apply 16.81% where 20.21% was meant. That fails **safe** — it is a stricter cap — but
it is an ambiguity in a load-bearing field, and it was found by reading the instrument the
corpus cites rather than by reading the contract. A denominator is a contract question with a
restatement attached, so it is reported here and not changed on an eval branch.
