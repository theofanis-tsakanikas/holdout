# Claim 1 — no price reaches a shelf without the guardrail set

> The actuation type cannot be constructed without a guardrail certificate. The envelope —
> floor, regulated basket, prior-price rule, max daily delta — is a versioned contract with
> effective dates.
>
> *Trap: a planter reading the same contract as the detector is one function agreeing with
> itself → the gates are attacked from an independent corpus of real price lists.*

```
make claim-1          the eval, and the sixteen mutations claim 1 owns
make eval-guardrail   the eval alone, about ten seconds
```

---

## 1 · What is attacked

**Real prices, real law, derived cost.** The quotes, the price endings, the dispersion, the
markdowns and the regulated list are published by people who have never seen this repository; the
unit cost the margins are measured against is derived from a sector median because no public source
carries a retailer's cost. Both halves are stated wherever the corpus is described, rather than
*real* standing alone with the cost in a footnote.

Every quote in `corpus/real/` is turned into a decision this system would have had to take,
and driven through `certify` against eight envelopes. Then one question, asked ten ways:
**does a price ever escape?**

| id | the question it would answer `false` |
|---|---|
| `G1.only-a-certificate-reaches-a-shelf` | is a certificate the only thing the actuator accepts, and is a refusal always rejected by it? |
| `G2.certified-price-inside-exact-bounds` | does every certified price satisfy this eval's **own** exact recomputation of every rule, with no tolerance? |
| `G3.refusal-supported-by-exact-arithmetic` | does every refusal have something to refuse — a price outside the bound this eval rounded, with no tolerance? |
| `G4.empty-range-is-really-empty` | when the answer is donation or disposal, is the admissible range really empty? |
| `G5.frozen-category-never-certified` | do the real cigarette, spirit, infant-formula and fish prices all refuse, naming the frozen category? |
| `G6.ladder-certifies-on-real-base-prices` | does the declared safe state ever produce a price refused by a bound it is built to satisfy? |
| `G7.closed-vocabulary-only` | is every reason a declared code carrying a detail, so the evidence is a count? |
| `G8.every-refusal-code-is-reached` | does this eval construct an input for **every** code, so no gate passes by never being tried? |
| `G9.no-tampered-certificate-reaches-a-shelf` | do the declared tampers still fail to dispatch, on certificates issued from real prices? |
| `G10.bounds-land-where-the-independent-arithmetic-puts-them` | is every bound the envelope placed on exactly the cent this eval's own arithmetic puts it on, compared as integers? |

`G2` is the one that carries the claim. The rest bound the ways it could be passing for the
wrong reason — and `G10` is there because `G2` and `G3` both go through a *price*, so both
see a misplaced bound only where a corpus price sits in the gap it opens. Measured, on an
absolute floor moved a cent loose: `G2` reports **3** violations in 28,485 certified prices,
`G10` reports **232,373** disagreements in 824,790 bounds. Three cases out of twenty-eight
thousand is a gate that holds until the corpus is reshuffled. And one break is caught by
`G10` alone — a bound at exactly the right amount wearing another rule's id, which moves no
arithmetic at all and destroys the record of which guardrail was checked.

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

**The boundary is computed twice — including the rounding.** Driving the gates from outside
answers *does it refuse*. It does not answer *at the right place*, and if the only thing that
knows where the boundary is were `evaluate`, the eval would be asking a function to mark its
own paper. `reference.py` is a second implementation, deliberately a different shape: exact
`Decimal` euros against integer cents, one predicate per rule against one pass appending
attributed bounds. The two share the rule *values* and nothing else.

That last sentence used to be false in one place, and it is the fourth instance of the defect
`CLAUDE.md` names: **a guard tested by its author is tested in the shape the guard already
handles.** The eval's own floor ended in `Money.as_lower_bound` — the core's rounding
primitive — under a docstring claiming the direction had been arrived at independently.

*What that cost, planted against the tree that had it rather than argued about:*

| | `main`, unmutated | `main`, `as_lower_bound` rounding half-to-even |
|---|---|---|
| `G2` | pass · 0 violations in 28,482 | **FAIL · 199 violations in 28,681** |
| `G3` · `G4` | pass | pass |
| `G6` | pass · 7,366 refused by a ceiling | pass · **7,365**, moved in silence |

`G2` compares against `reference.py`'s **exact** `Decimal` bound, which never went through
`Money`'s rounding, so `G2` was never blind to this. The check that shared the primitive was
`G6`, and `G6` stayed green while the number it publishes moved. An earlier version of this
section claimed all three stayed green — an order of magnitude too large, and written without
being run, which is the same defect one level up in the layer that is supposed to be the
evidence.

`rounding.py` now re-decides the direction and carries it out on the value's exact integer
ratio: no precision, no context, no quantisation, so a defect in any of those cannot cancel
out between the two. `make gate-proof` plants that exact break and demands a named check
refuse it.

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

Neither is fully fixed here — the second is half closed and half deferred, and both are
recorded in `docs/DECISIONS.md` with the condition that unlocks what remains. An eval that quietly widened an assertion to swallow what it found would be
worse than no eval.

**The first figure below was wrong when this file first carried it, and by an order of
magnitude.** It said 7,366; the supportable number is 716. What follows is the corrected
account, and the original sentence is not deleted — doctrine rule 4 — it is restated, with
what it got wrong named.

### The ladder knows about a floor and not about a ceiling

`ladder.quote()` takes a `floor` and clamps to it. It takes no ceiling and knows of none. So
where the margin cap binds below the base price, the shallow rungs of the declared safe state
produce prices the envelope refuses — **716 of 26,600 ladder quotes** in this run, on one
envelope.

**What the earlier figure of 7,366 was.** It was every ladder quote the envelope refused for
any reason outside the three bounds the ladder models, counted as though all of them were
ceilings. **6,650 of them are `MARGIN_CAP_BASIS_UNEVALUABLE`** — a cap whose basis states
nothing computable, which refuses every price at every rung in either direction. It is not a
ceiling, and a ladder that took ceilings would not move one of those quotes. The two counts
are now separated by `reference`, from the `side` it already computes per rule rather than
from a list of codes kept here, and both are published:

    716 refused by a ceiling · 6,650 refused by a rule with no bound

The guardrail set behaved perfectly in both cases: it refused, by name, for a true reason.
What is incomplete is doctrine rule 1, and only for the 716. For an expiring product the safe
state is the ladder, and there the ladder's answer is itself refused — so there is nowhere
left to fall. It is the same *class* as the finding a review made by composing two modules
that had only ever been tested alone, and it was found the same way: by composing them over
inputs nobody chose.

`G6` therefore asserts only the three bounds the ladder is built to satisfy — the max depth,
the absolute floor, the margin floor — and publishes both counts beside it as numbers. The
frequency depends on the derived cost, which is why this is a finding to investigate rather
than a defect to assert. `tests/evals/test_guardrail_instrument.py` pins 716 and 6,650, so a
change that merges them again is red in the suite rather than wrong in a paragraph.

### The benchmark's denominator — half closed, half deferred

ΥΑ 21330/2026 άρθρο 4 παρ. 4 defines the capped margin as
`(selling price − average cost of goods sold) ÷ selling price` — a fraction of the **price**.
`evaluate` bounds the price at `cost + cost × markup`, a mark-up on **cost**. The two are the
same constraint in different denominators and `m / (1 − m)` converts exactly. Feeding the
first straight into the second applies 16.81% where 20.21% was meant: a stricter cap, so it
fails **safe**, and still a wrong number arrived at silently.

**The half that is now closed** is the field. `ProposedPrice.benchmark_markup_on_cost` takes a
`MarkupOnCost` and refuses anything else at runtime as well as in the annotation, and
`MarginOnPrice.as_markup_on_cost()` is the only route between the two — a named call in a diff
somebody reads. `build.py` holds the published figure as a `MarginOnPrice`, in the denominator
its source publishes it in, and converts once.

**The half that is deferred** is the contract. `contracts/guardrails/regulated_basket.yaml`
still names its benchmark `average_gross_margin_2025` and says nothing about what it is a
fraction of. Naming the denominator there opens a window on a live guardrail and pulls a
restatement chain with it, so it waits for the next change to that file — `docs/DECISIONS.md`
carries the entry and the unlock condition.
