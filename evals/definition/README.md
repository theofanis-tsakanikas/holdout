# Claim 5 — one definition, three mechanisms, the same number

> The source of truth is the contract in this repository, compiled into a Delta view, the agent's
> tool definition and the experiment readout. Compared as integers, no tolerance.
>
> *Trap: two consumers calling the same function prove nothing → three genuinely different
> mechanisms, sharing only the definition.*

```
make claim-5          the eval, and the three mutations claim 5 owns
make eval-definition  the eval alone — it builds bronze, silver and gold first
```

---

## 1 · What is attacked

**The claim's own three consumers, first.** `CLAUDE.md` names a Delta view, an agent tool
definition and a readout query. Measured before anything was built:

| consumer | rendered by | verdict |
|---|---|---|
| `compile_dbt_model` | `metric_parts` | one mechanism |
| `compile_sql_function` | `metric_parts` | the same one |
| `compile_readout` | `metric_parts` | the same one |
| the agent tool definition | a JSON writer | **computes nothing** |

Normalising away relation names and the version clause, the first three are **byte-identical**:

```sql
sum(cast(qty * price_paid      as decimal(38, 6))) as term_0
sum(cast(qty * unit_cost_as_of as decimal(38, 6))) as term_1
sum(cast(qty * unit_cost_as_of as decimal(38, 6))) as term_2
bround(coalesce(s.term_0,0) - coalesce(s.term_1,0) - coalesce(w.term_2,0), 2)
```

A bug in the combination or in the `decimal(38, 6)` cast appears in all three and **cancels in
every comparison between them**. Comparing them proves Spark is deterministic. It is this claim's
own trap with a bigger number: *two consumers calling the same function prove nothing* becomes
three consumers calling the same **renderer**. The fourth cannot be a mechanism at all — it has no
number of its own — so `D4` holds it to the contract's *terms* instead, which is not an arithmetic
claim.

**So the eval builds the two mechanisms the repository did not have**, and the compiled SQL is the
third:

| | |
|---|---|
| the compiled SQL | executed by Spark over the gold tables `T011` builds |
| `aggregate_then_combine` | sum each term per cell, combine the sums, round once |
| `combine_then_aggregate` | combine each row, sum the contributions, round once |

Then one question, asked four ways:

| id | the question it would answer `false` |
|---|---|
| `D1` | does the compiled SQL agree with the aggregate-then-combine path, as an integer? |
| `D2` | does it agree with the combine-then-aggregate path? |
| `D3` | do the two Python paths agree with each other? |
| `D4` | does the agent's tool definition declare the contract's own id, version, grain, unit, rounding and canonical scale? |

Three pairwise checks rather than one aggregate, because **which two disagree is the diagnostic**:
a Python pair agreeing with each other and not with the SQL is a shared misconception; a Python
path disagreeing with both is an arithmetic slip in that path.

---

## 2 · Where the independence is

**In the order of operations, which is where the failures live.**

```
aggregate_then_combine    sum each term per cell   ->  subtract  ->  round once
combine_then_aggregate    subtract per row         ->  sum       ->  round once
```

In exact arithmetic those must agree. They stop agreeing the moment either rounds early, carries a
`float` where a `Decimal` belongs, or disagrees about a cell one side of the full outer join has
and the other does not — which is what the three mutations plant.

**`evals/uplift/`'s proven pair was the obvious candidate and was refused.** `grouped_metric` and
`walked_metric` both consume a `Ledger` whose three terms are *already aggregated*, so they
implement the combination and the rounding and nothing else. They are independent **in the wrong
half** — the half the SQL does differently — and reusing them would have bought agreement by
construction exactly where it is worth nothing.

`tests/evals/test_definition_independence.py` enforces non-sharing on the **import graph**: neither
module, nor any parent of either, may reach the other. Not on anybody's care.

**The population is held fixed, and the drop is its own number.** All three read the rows gold
materialised for `gold.decision_economics` and `gold.waste` — the contract's declared sources. The
`where unit_cost_as_of is not null` that shapes the first lives in the dbt model that *builds* it,
upstream of every mechanism, and arrives as rows rather than as logic. Feeding three mechanisms
three row sets would test the definition *and* the pipeline *and* the drop rule at once, and a
disagreement would name none of them, so the drop is published beside the comparison and never
inside it.

---

## 3 · Observed, derived, constructed

**Observed** — 422,139 economics rows and 676 waste rows, from `W6` at `rehearsal`, built by
`pipelines/`'s own code so a defect in the pipeline shows up as a claim-5 failure rather than
hiding behind a private path.

`rehearsal` rather than `smoke` for a measured reason: **at smoke this corpus throws nothing
away.** `gold.waste` is empty, the metric's third term is a sum over no rows, and the full outer
join — the one place a one-sided cell can be lost — never has a one-sided cell. A claim 5 proved at
smoke would agree on two thirds of its own definition.

**Derived** — 480 cells at the contract's grain, and 6,515 sales of 428,652 that gold could not
price.

**Constructed** — **one cell, and every number in it is chosen rather than found.**

    row A   qty 1 · price 0.1000 · cost 0.0050   ->  0.0950
    row B   qty 1 · price 0.2000 · cost 0.1700   ->  0.0300
    exact                                            0.1250
    half_even 0.12   ·   half_up 0.13                the modes disagree

**The corpus cannot exercise the contract's `rounding` block at all.** Gold builds `price_paid` and
`unit_cost_as_of` as `cents / 100` and `qty` is an integer, so every corpus cell is an exact number
of cents: `bround(x, 2)` is the identity and the two modes differ only on an exact half at the
third decimal this data never has. That is not an argument, it is a controlled comparison — the
same mutation, unchanged, **SURVIVED** over 480 corpus cells and **BIT** over the same run plus
this one. The only thing that changed is the data.

It is appended to `gold.decision_economics` rather than upstream because sub-cent content cannot
enter through `priced_sales`, whose cost is a bigint of cents. `decision_economics` is
`decimal(18,4)` and is the contract's own declared source, so **all three** mechanisms see it and
none sees a row the others do not. There is deliberately no waste row: a cell that traded and threw
nothing away is a real shape.

One cell rather than a scattering, because the smaller the construction the smaller the part of the
claim it weakens — and it is sufficient: both surviving plants bite on it and it is the only value
that makes them. **This is claim 4's practice**, including the form: each check's question names
both populations — *over every cell the corpus produced and the one the eval constructed* — so a
reader sees which half the eval wrote.

---

## 4 · What came out

```
481 cells — 480 from the corpus, 1 constructed
D1 · D2 · D3   integer-equal, 0 disagreeing
D4             7 terms compared, 0 disagreeing
mutations      3 planted, 3 bit
```

---

## 5 · What this does not prove

**Non-sharing prevents shared code. It does not prevent a shared misconception.** The two Python
paths were written by one session in one sitting and could both misread the contract the same way
— every mutation would pass and the integers would agree.

**Which is why the SQL is the load-bearing third**, and why that is said here rather than left for
a reader to assume. It was compiled from the same contract by a different mechanism, at a different
time, for a different purpose. The Python pair mostly guards the arithmetic; **the SQL guards the
reading.** A reader who sees three mechanisms should not assume all three are equally independent
— one of them is carrying more than the others.

**It does not prove the corpus should produce sub-cent content.** The constructed cell proves three
mechanisms round alike on a value the corpus never produces. Whether a corpus that cannot reach the
contract's own `rounding` is the right corpus is a question for the author, filed rather than
answered.

**And it says nothing about the Unity Catalog metric view**, which is a fourth consumer on the
estate and is `T012`'s declared `out_of_scope`.

---

## 6 · One finding

### The contract's `rounding` block is inert on this corpus, and v3's justification with it

Filed in `docs/FINDINGS.md` against `contracts/metrics/category_margin_per_store_week.v3.yaml` and
the corpus, **not against this eval** — this is where it was found, not where it lives. The
distinction metric v3 exists for is now demonstrably **real**, because the constructed cell exhibits
it, and demonstrably **unreachable from the corpus**. Both halves measured; neither the contract nor
the corpus is changed here, because which of the two should move is the author's call.
