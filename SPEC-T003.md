# SPEC — T003 · the A/A harness, the reference implementation of truth, and `make claim-2`

> `evals/uplift/`, the claim-2 mutations, one new contract, one core optimisation and the CI
> restructure that pays for all of it. This document is the decision record for what `CLAUDE.md`,
> `PLAN.md` and `TASKS.md` left open, and the build order that follows. Branch `evals/aa-harness`.
>
> **T003 closes phase 1.**

---

## 0 · What this closes, and what it does not

`TASKS.md` T003. Closed when `make claim-2` is green and four numbers are **published, not ticked**:
the false-positive rate on A/A against the declared α as a one-sided binomial at a stated level; the
false-refusal rate on W6; estimator bias; and CI coverage over K runs of W6. Every draw runs the
whole system — assignment, exposure collection, the four validity checks, the readout — not just the
estimator. A deliberately slow Python reference implementation of truth-on-the-metric agrees with
the harness's grouped path **as integers, with no tolerance**.

**Out of scope, restated:** claims 3, 4 and 7 (T004, T005, T006); `make preview-audit`; any pipeline;
anything that needs an account.

**Also out of scope, and stated so the seam is deliberate:**

- **The decision path.** `CLAUDE.md` enumerates claim 2's "whole system" as *assignment, exposure
  collection, the four validity checks, the readout*. The guardrail envelope is not in that list and
  is not added here. The deferral **"the world's prices are not certified prices"**, which names
  T003 as where the question becomes concrete, is **restated rather than closed** — see §17.
- **The SQL/dbt leg of claim 5.** There is no dbt in phase 1. The reference implementation's
  counterpart is the harness's own grouped aggregation; the third and fourth mechanisms arrive with
  T011/T012. See §8 and §17.
- **A fifth validity check.** No new refusal code is added. The vocabulary is closed, and the reason
  W2 needed a restatement rather than a new check is §3.

---

## 1 · The four measured facts

Everything below is built on numbers measured in this repository on 2026-08-28, on the author's
laptop (Apple silicon, 14 cores, Python 3.12). **A GitHub `ubuntu-latest` runner is slower and the
factor is not known until it is measured** — the budget in §13 carries headroom and the build order
in §14 measures the runner before anything is tuned for it.

| | measured | how |
|---|---|---|
| **F1** | world generation: smoke **0.11 s**, rehearsal **1.32 s**, scenario **≈ 100 s** per world | streaming `corpus.world.events` to exhaustion |
| **F2** | one full readout, 100 units, B = 1000: **13.5 s** | `assess` → `reference_set` → `close` |
| **F3** | of those 13.5 s, **≈ 11.5 s is `estimator.interval`**, ≈ 1.4 s is `plan_for`, and **≈ 0.4 s is `permutation_p`** | `cProfile`, cumulative |
| **F4** | `SealedAssignment.__reduce__` raises | by design — a seal is not serialisable |

**F2 and F3 are the whole shape of this task.** K = 200 full readouts is ~45 CPU-minutes, and the
confidence interval is 85% of it while the p-value is 3%. **F4 says every worker process must
re-derive its own lottery from the seed** — nothing crosses a process boundary except a seed going
in and a small plain record coming back, which is a better shape anyway.

---

## 2 · The decisions

| # | question | answer |
|---|---|---|
| 1 | how does the CI job fit? | **Matrix job per claim target, *and* multiprocessing inside `claim-2`.** Neither alone is enough. `gate` returns to `timeout-minutes: 15`. |
| 2 | where do the 45–90 CPU-minutes go? | **Both levers: multiprocessing over seeds, and `estimator.interval` made cheap.** §9 shows the interval's statistic is affine in the shift, so each bisection step becomes O(B) instead of O(B·n·p). No answer changes. |
| 3 | what does "the same data, re-drawn" mean? | **Hybrid: few world seeds × many lotteries.** 5 world seeds × 40 lotteries = K = 200. The world seed stops being one choice somebody made, without paying for 200 generations. |
| 4 | at what scale? | **A new `HARNESS` scale** — 100 stores, because the roster is what the statistics see; fewer SKUs and fewer days, because the calendar is what the clock sees. §5. |
| 5 | what is "the truth on the metric"? | **The ATE over the roster, from two counterfactual worlds** — all-control and all-treatment under common random numbers — so every unit has both potential outcomes. §8. |
| 6 | what does the slow reference implementation agree with? | **The harness's grouped path**, integer-exact, no tolerance. The SQL leg is a declared deferral unlocked by T011/T012. §8. |
| 7 | what runs under a gate-proof mutation? | **Two entry points.** `evals.uplift` is the published harness; `evals.uplift.machinery` is the same checks at a small declared configuration, and it is the only module a mutation names. §11. |
| 8 | one run per world, or a rate? | **A rate over seeds, with a declared threshold, for every world.** W6's false-refusal rate is already a rate; measuring the other five differently would be two instruments. §10. |
| 9 | where do K, the binomial level and the per-world thresholds live? | **A new contract, `contracts/design/aa_harness.yaml`**, every value a `{value, source}` pair. §4. |
| 10 | how is the MDE declared without looking at the truth? | **As a percentage of the pre-period mean, declared once for every world**, written before any seal is opened. If W6 refuses under it, that **is** the published false-refusal rate and the number is not touched afterwards. |
| 11 | what does W2 publish? | **The pair** — the estimate with the neighbour pairs declared, and the bias that arrives when they are withheld. This required restating `CLAUDE.md`; see §3. |

---

## 3 · The restatement that landed first

**Found by reading `contamination.py`, not by reading the documents.** Three files —
`CLAUDE.md`'s six-worlds table, `corpus/world/README.md`, and the `correct_behaviour` field of `W2`
in `corpus/world/worlds.py`, which is **sealed into every `truth.sealed.json`** — all said some
version of *"detect and refuse, never estimate"*. That reads as a detector at readout.

There is none. `contamination.check` asks two questions: does the recomputed digest describe the
arms it carries, and did each unit receive its own arm's policy. Neither can see a neighbour's trade
crossing the road. The system's defence against interference is at **moment 1** —
`_neighbour_exclusions` drops the later-sorted member of every pair inside `neighbour_radius_m`
before the lottery is drawn — and the closed vocabulary's only interference code,
`UNIT_GUARANTEES_INTERFERENCE`, is filed under `at_design`. **The vocabulary was right and the prose
was wrong.**

All three sites are restated, prior wording kept, per doctrine rule 4, and `docs/DECISIONS.md`
records the delta and the rule that follows: *a sentence naming what the system does when something
goes wrong is written against the function that would do it — named — and not against the table it
came from.*

**And then all six rows were read against the function that would make them true**, because one bad
row is a row and two is a method. Two more did not stand:

- **W3** read *"exposure-adjust or refuse"*. There is nothing to adjust with, and `exposure.py`'s own
  docstring says so — *"no CACE, no instrumental-variable estimate and no exposure-adjusted
  alternative… the absence is deliberate rather than pending"*. **A row of the table contradicted a
  module in the same repository.** Restated to *"report ITT with the realised exposure rate printed,
  or refuse below the declared threshold — never silently dilute"*.
- **W4** read *"report the declared window's average"*, which reads as arithmetic the estimator
  performs. `close` takes `outcomes` as given and cannot verify they span the declared period; what
  is guaranteed is `may_read`. Restated to name that, and **`U8` in §10 is where the aggregation is
  checked rather than assumed.**

**W1, W5 and W6 stand** — against `Readout.is_significant`, `Statistic.detects` on the realised
variance, and `close` returning a `Readout` when all four checks passed.

The rule is now in `CLAUDE.md`'s **Before any change** checklist rather than only in
`docs/DECISIONS.md`, and beside it a section naming this as the sibling of *"a guard tested by its
author"*: a guard tested by its author fails in the shape its author imagined; a sentence written by
its author has no gate behind it at all.

---

## 4 · The new contract — `contracts/design/aa_harness.yaml`

`inference.yaml` is what the **core** consumes. This is what the **eval** consumes, and they are kept
apart so a number the estimator never reads cannot be mistaken for one it does. It lives in
`design/` rather than in a new family, because `CLAUDE.md` declares four families and a fifth would
be a structural change bought for one file.

```yaml
version:        1
effective_from: 2026-08-28

seeds:
  world:            { value: 5,   source: {…} }   # world seeds
  lotteries_per_world_seed:
                    { value: 40,  source: {…} }   # 5 x 40 = K = 200
  interference_lotteries_per_world_seed:
                    { value: 8,   source: {…} }   # W2 only — see §6

binomial_level:     { value: 0.01,  source: {…} }  # the one-sided test on the FP rate
false_refusal_max_pct:
                    { value: 10,    source: {…} }  # W6
coverage_tolerance_pct:
                    { value: 5,     source: {…} }  # |realised - 95| on W6
per_world_min_correct_pct:
                    { value: 90,    source: {…} }  # W2-W5

mde_pct_of_pre_period_mean:
                    { value: 2.0,   source: {…} }  # declared before any seal opens

machinery_configuration:                            # what a gate-proof mutation runs
  world_seeds:      { value: 1,   source: {…} }
  lotteries:        { value: 3,   source: {…} }
```

Every entry is `kind: scenario_assumption` with a note and a `verified_on`, exactly as
`inference.yaml`'s are. **None of them is law and every source says so.** They are here rather than
as constants in `evals/uplift/` for `inference.yaml`'s own stated reason: doctrine rule 3 does not
care what extension the file has, and a threshold nobody justified is a dial that will eventually be
turned.

**What lands with it:** `contracts/schemas/aa_harness.schema.json`; the entry in
`loader.CLAIMED_FILES["design"]`; a model in `contracts/model.py`; and the file inside the
provenance walk, so `make contracts` refuses a value with no source here exactly as it does
everywhere else. `binomial_level` is deliberately **not** α: α is what the system declares about
itself, and this is the level at which we test whether the system kept that declaration. Two
numbers, two jobs, and collapsing them would be the estimator grading its own homework.

---

## 5 · The `HARNESS` scale

`corpus/world/scale.py` gains a fourth scale. The reasoning is that the two dimensions cost
different things:

- **stores** are what the statistics see — the roster, the 20% holdout, the strata, the standard
  error. **100, unchanged from `SCENARIO`.** A 20-store `REHEARSAL` gives a control arm of four, and
  a control arm of four cannot land inside a 0.10 SMD tolerance on a binary covariate: the
  proportions move in steps of ¼. `tests/core/conftest.py` already records that arithmetic.
- **SKUs and days** are what the clock sees. Eight pre-period weeks (the covariates' declared
  `lookback_weeks`) plus up to eight period weeks (`max_duration`) is **112 days**, and **12 SKUs per
  category** is enough for a fresh assortment to churn.

```
HARNESS = Scale(name="harness", stores=100, skus_per_category=12, days=112,
                start_date=date(2025, 9, 1))
```

Projected from F1 at ≈ 0.14 × scenario, so **≈ 14 s per world**. That is a projection; the build
measures it and `corpus/world/README.md` records the measured figure with its command, exactly as
the scenario figures are recorded.

**Fewer SKUs per store raises per-store variance relative to the mean.** That is honest and it is
stated: the power check is judged on the realised variance, so a thinner assortment makes the
harness's world *harder* to detect an effect in, not easier. If it turns out to make W6 refuse
outright, that appears as the published false-refusal rate and is reported, not tuned away — see
§15.

---

## 6 · The composition property, and why K = 200 is affordable at all

The naive reading of "run the whole system per draw" is 200 world generations per world: the data
depend on the assignment. It does not, in five of the six worlds, and this is a **fact about the
generator that can be checked rather than assumed**.

`generate.py` is store-major. The only place another store's arm enters a store's emission is
`_spillover`, and its first line is:

```python
if world.spillover_pct == 0:
    return 1.0
```

`spillover_pct` is non-zero in **W2 alone**. So in W1, W3, W4, W5 and W6 a store's whole event
stream is a function of its own arm and nothing else, and the two counterfactual generations — all
stores control, all stores treatment — give every unit **both potential outcomes exactly**. Any
lottery is then a lookup:

```
Y_observed[i] = Y_treatment[i] if arms[i] is TREATMENT else Y_control[i]
```

**Two generations buy forty lotteries.** That is the whole budget.

It is also a claim, so it is tested, and the test's case is not chosen by whoever wrote the
composition — it is whatever the lottery draws:

- **`test_composition_is_exact_where_there_is_no_interference`** — for each of W1, W3, W4, W5, W6,
  draw a mixed assignment, generate the world under it, and assert the per-unit metric equals the
  composed value **as integers**. Not close: equal.
- **`test_composition_is_wrong_under_interference`** — the same test on **W2 must fail**, and the
  test asserts that it does. A world built to break SUTVA whose outcomes could be composed
  unit-by-unit would not be breaking SUTVA at all, and this is the assertion that says so.

W2 therefore generates **per assignment**, at a smaller declared count
(`interference_lotteries_per_world_seed: 8`, so 5 × 8 = 40 generations). Its published quantity is
not a rejection rate anyway; it is the pair in §10.

W1 needs **one** generation, not two: `treats=False`, so `Y(1) ≡ Y(0)` and
`tests/corpus/test_world_determinism.py` already asserts the streams are byte-identical except for
the arm label. Empty is empty.

---

## 7 · `evals/uplift/`

Same shape as `evals/guardrail/`: a package, a `__main__.py` that delegates to `evals.report.main`,
named checks with stable ids, numbers published pass or fail.

```
evals/uplift/
  __init__.py
  __main__.py        python -m evals.uplift          — the published harness
  machinery.py       python -m evals.uplift.machinery — the same checks, small; §11
  outcomes.py        world events -> outcomes at the metric's grain (the grouped path)
  reference.py       the deliberately slow loop over every event (§8)
  potential.py       the two counterfactual generations, and the composition (§6)
  harness.py         one draw = one whole system run; the worker a process gets
  worlds.py          the six worlds' checks, and their declared correct behaviour
  aa.py              K draws, the rate, the one-sided binomial
  coverage.py        CI coverage and estimator bias on W6
  parallel.py        the process pool, and the seed-in / record-out contract (F4)
```

### One draw is one whole system run

`harness.run_one(world_id, world_seed, lottery_seed)` does, in a worker process, with nothing
inherited but three strings:

1. build the chain and the pre-period, derive `variance_per_unit_week`, `mean_per_unit_week` and the
   five balance covariates **from the pre-period only**;
2. `assess(...)` — the nine-field form, feasibility, automatic exclusions, the committed seed, the
   stratified draw, the sealed assignment;
3. compose or generate the period, and aggregate to `outcomes` (§8);
4. collect exposure from the `esl_acks` stream — the acknowledgement is the only evidence a price
   reached a shelf, so exposure is **read from the corpus**, never assumed from the assignment;
5. `reference_set(...)`, then `close(...)`;
6. return a plain frozen record: refusal codes or uplift, interval, p-value, the four check figures,
   the seed, the draw index and the digest.

A `DesignRefusal` at step 2 is a legitimate outcome and is recorded as one. Nothing is retried, and
**no draw is ever discarded** — a harness that drops the draws it does not like is the fishing this
whole repository is built to make impossible.

### The design form is written once

One form, in `evals/uplift/`, for every world: same hypothesis shape, same metric, `unit: store`,
`mde` from `mde_pct_of_pre_period_mean`, `max_duration: 8 weeks`, `decision_rule` declared,
`filled_by: policy:aa_harness`. **The same form everywhere is the point** — a per-world form would
be a per-world degree of freedom.

---

## 8 · The reference implementation of truth

### What the truth is

For each world and world seed, generate the two counterfactual worlds of §6 and compute, for **every
unit on the roster**, `Y(1)` and `Y(0)` at the metric's grain. Then

```
truth = mean over roster of Y(1)  -  mean over roster of Y(0)      # the ATE, in cents
```

This is the estimand the difference of means targets, so CI coverage is a question about the same
number the interval is an interval for. It also yields **per-unit truth**, which is what estimator
bias is measured against.

**The seal is opened only after the readout has been written.** `seal.open_after_readout(path,
readout)` already enforces that ordering and this harness uses it — the readout record lands on disk
first, then the truth is read, then they are compared. Never the other way round.

### Two implementations, and they may not share a line

- **`outcomes.py` — the grouped path.** Streams the world's events into a dictionary keyed by
  `(store_id, iso_week, category)`, accumulating the metric's three terms. This is the shape a
  `GROUP BY` has and it is what feeds `close()`.
- **`reference.py` — the slow path.** Loops over every event in order, one at a time, holding a
  running per-event ledger, resolving the as-of cost by walking the cost ledger forward rather than
  by indexing it. Deliberately slow. Written from `contracts/metrics/category_margin_per_store_week.v3.yaml`
  and the metric's own `rounding: {half_even, 2}`, and from nothing else.

They agree **as integers, with no tolerance**, per world and per unit. A one-cent disagreement is a
failed check with the offending units named — that is exactly the failure v3 of the metric contract
exists to have made impossible, and this is the first thing that would notice if it came back.

**The honest limit:** two Python implementations are not the three genuinely different mechanisms
claim 5 needs. This is the fourth-consumer check's *first* leg, and `docs/DECISIONS.md` carries the
deferral with T011/T012 as its unlock. Stated in the eval's own `notes`, printed on every run.

---

## 9 · Making `estimator.interval` cheap without changing an answer

**The optimisation, stated as mathematics before it is stated as code.** `interval` inverts the
permutation test over constant shifts. For a candidate shift τ the outcomes become
`y(τ) = y − τ·T`, where `T` is the indicator of *treated under the observed arms* and does not
change between draws. For any fixed arm-labelling `a`:

- the covariate-adjusted difference is a **linear functional** of the outcome vector, so
  `numerator_a(τ) = n_a − τ·m_a` — affine in τ, and `(n_a, m_a)` depend only on the labels and the
  covariate design;
- each residual is affine in τ, so the pooled variance is
  `Q_a(τ) = A_a − 2·B_a·τ + C_a·τ²` — a quadratic with exactly three coefficients per draw.

So the studentized statistic is `(n_a − τ·m_a) / sqrt(Q_a(τ))`, and "is this draw at least as
extreme as the observed one" is a polynomial comparison in τ once both sides are squared — exact in
`Fraction`, with no re-fitting. **Precompute `(n, m, A, B, C)` once per draw; every bisection step is
then O(B) arithmetic instead of O(B·n·p) refits.** Projected ~100× on the 85% of the cost F3 found.

**The bisection stays.** Only the cost of `accepts(τ)` changes. This is deliberate: keeping the
search identical means the guard below can be an equality rather than an argument.

**The guard, and its case is not chosen by the author of the optimisation.** A test asserts the new
`interval` returns **bit-identical bounds** to the current one across (a) every case in
`tests/core/test_estimator.py` and `tests/core/test_experiment_composition.py`, and (b) a battery
of readouts drawn from the harness's own worlds — inputs nobody here picked. The old implementation
is kept in the test as the oracle for the length of this branch. `CLAUDE.md`'s checklist asks who
wrote the case a guard is tested on; the answer here is the lottery.

**If the algebra does not reproduce the bounds exactly, it is abandoned** and the budget falls back
to multiprocessing alone. §13 prices both.

---

## 10 · What is published

Numbers, in a monospace font, whether or not anything failed.

| id | the falsifiable sentence | figure |
|---|---|---|
| `U1.aa-false-positive-rate` | on an A/A split the system reports a significant effect no more often than α | `9/200 = 4.5%`, and the one-sided binomial p at `binomial_level` |
| `U2.aa-p-values-are-uniform` | the null p-values are not piled at one end | KS-style spread, published as a figure |
| `U3.w6-false-refusal-rate` | a world where everything works produces the number | `4/200 = 2.0%` against `false_refusal_max_pct` |
| `U4.w6-coverage` | a 95% interval contains the truth about 95% of the time | `191/200 = 95.5%` against `coverage_tolerance_pct` |
| `U5.w6-estimator-bias` | the estimate is unbiased for the truth | mean of `uplift − truth`, in cents, with its own spread |
| `U6.w2-exclusion-is-load-bearing` | declaring the neighbour pairs removes the interference the design engine exists to remove | the **pair**: bias with pairs declared, bias with pairs withheld |
| `U7.w3-exposure-refuses` | exposure below the threshold refuses and never silently dilutes | % of draws refusing `EXPOSURE_BELOW_THRESHOLD`, vs `per_world_min_correct_pct` |
| `U8.w4-window-average` | a decaying effect is reported as the window's average, not the first week | \|estimate − window truth\| vs \|estimate − first-week truth\| |
| `U9.w5-power-or-width` | heavy tails fail the power check, or the interval is honestly wide | % of draws doing one or the other |
| `U10.truth-implementations-agree` | two independently written implementations of the metric agree | `0` disagreeing units, out of N |
| `U11.composition-is-exact` | the potential-outcome composition is exact where there is no interference, and wrong where there is | integer equality on five worlds, inequality on W2 |

`U1` is claim 2's sentence. `U3` is published **beside** it, in the same block, because a system that
refuses everything passes `U1` and is worthless.

---

## 11 · The claim-2 mutations

`make gate-proof`'s ledger refuses a claim target with nothing planted against it, so claim 2 needs
mutations. Each mutation re-runs its `eval_module` as a subprocess under a **300 s cap**, which the
published harness cannot meet and should not try to.

**Two entry points.** `evals.uplift` is the published harness at the contract's K.
`evals.uplift.machinery` runs **the same named checks** at `machinery_configuration` — one world
seed, three lotteries, seconds — and is the only module a mutation names. Same ids, same questions,
smaller configuration; the rate-shaped checks (`U1`, `U3`, `U4`) are absent from it rather than
computed on three draws and called a rate, because a rate over three draws is not a rate.

Planted breaks, each written as a behaviour change in domain terms and each naming the check it must
trip in advance:

| | breaks | must trip |
|---|---|---|
| 01 | the balance check compares arms before the exclusions rather than after | `U6` |
| 02 | exposure counts assigned treated units instead of acknowledged ones | `U7` |
| 03 | the neighbour exclusion keeps both members of a pair | `U6` |
| 04 | the readout reads the first week and calls it the window | `U8` |
| 05 | the power check is judged on the design's assumed variance, not the realised one | `U9` |
| 06 | the interval is computed from the normal approximation instead of by inversion | `U4` |
| 07 | the grouped path rounds `half_up` where the contract says `half_even` | `U10` |
| 08 | the composition ignores the arm and always reads the treatment table | `U11` |

Mutations 01, 03, 04, 05 and 06 edit `src/holdout/`; 02, 07 and 08 edit `evals/uplift/`, which
`gate_proof.engine.COPIED` already copies. **A mutation that survives is reported, never adjusted.**

---

## 12 · The CI restructure

`TASKS.md`'s `stop_at` is binding: *"Do not raise `timeout-minutes` again. If the job does not fit,
the job is wrong."*

```yaml
jobs:
  gate:                       # make check · make contracts · make expiry
    timeout-minutes: 15       # back down from 25, in this change, as T000's deferral requires

  discover:                   # greps the Makefile, emits the claim targets as a JSON matrix
    outputs: { targets: … }

  claims:
    needs: [discover]
    strategy: { fail-fast: false, matrix: { target: ${{ fromJSON(…) }} } }
    timeout-minutes: 15
    steps: [ …, run: make ${{ matrix.target }} ]

  secrets:                    # unchanged
```

**The discovery property survives, and it had to.** The claim targets are still read out of the
Makefile and never listed in the workflow, so a claim target that exists but is never run stays
impossible by construction — the same property `claim-1` and `gate-proof` arrived under without this
file changing to admit them. It moves from a shell loop to a matrix, and `fail-fast: false` means a
red claim 2 does not hide the state of claim 1.

**The deferral in `docs/DECISIONS.md` that carries the 25 minutes is closed in this change**, with
the measured figure that replaced it.

---

## 13 · The budget

Per-readout cost after §9, projected from F2 and F3: `13.5 − 11.5 + 0.3 ≈ 2.3 s` on the laptop.

| | draws | readouts | generations | CPU-min |
|---|---|---|---|---|
| A/A (W1) | 5 × 40 | 200 | 5 | ~8 |
| W6 — coverage, bias, false refusal | 5 × 40 | 200 | 10 | ~9 |
| W3, W4, W5 | 5 × 40 each | 600 | 30 | ~25 |
| W2 — both arms of the pair | 5 × 8 × 2 | 80 | 80 | ~22 |
| **total** | | **1,080** | **125** | **~64** |

On four runner cores, ~16 minutes wall — **over a 15-minute job**, so headroom comes from the two
levers already declared rather than from the timeout: W3/W4/W5 share the A/A world seeds' generations
where the world permits, and `per_world_min_correct_pct` is measurable on 5 × 20 for the three
non-rate worlds. The build order measures the runner **before** the contract's counts are fixed, and
if the honest answer is that 200 draws for W3–W5 do not earn their minutes, the contract says 20 and
says why. **What does not happen is a third timeout increase.**

Without §9, the same table is ~370 CPU-minutes and nothing fits. That is why the optimisation is in
this branch and not a follow-up.

---

## 14 · Build order

Each step is a commit. The branch is squash-merged.

1. **The restatement.** ✅ *Landed.* `CLAUDE.md`, `corpus/world/worlds.py`, `corpus/world/README.md`,
   `docs/DECISIONS.md`. §3.
2. **`HARNESS` scale** + the measured generation figure in `corpus/world/README.md`. §5.
3. **The composition property** — `potential.py`, and the two tests, including the one that must
   fail on W2. §6. *Nothing downstream is affordable until this holds.*
4. **`contracts/design/aa_harness.yaml`** + schema + loader + provenance walk + `make contracts`. §4.
5. **`outcomes.py` and `reference.py`**, and `U10`. §8. Two implementations before either is trusted.
6. **`estimator.interval`**, with the bit-identical-bounds oracle. §9. **Measured on the runner
   before the counts in §4 are fixed.**
7. **`harness.py` + `parallel.py`** — one draw, then many. F4's seed-in/record-out contract.
8. **`aa.py`** — K = 200, the rate, the binomial. **This is the stop point of §15.**
9. **`coverage.py` and `worlds.py`** — U3 through U9.
10. **`machinery.py`, the eight mutations, `make claim-2`.** §11.
11. **The CI restructure**, and the 25-minute deferral closed. §12.
12. `PLAN.md` and `TASKS.md`: T003 closed, phase 1 closed.

---

## 15 · The stop condition, restated because it is binding

> **If the A/A test does not stand against α — STOP and notify the author. Nothing is built on top
> of it.**

Concretely: at step 8, if `U1` reports a false-positive rate whose one-sided binomial p at
`binomial_level` rejects `rate ≤ α`, the branch stops there. **No threshold is loosened, no seed is
re-drawn, no world is regenerated, and `binomial_level` is not moved.** The finding is the deliverable
and steps 9 to 12 do not happen. That is the entire reason the A/A harness is built before the six
worlds rather than after them.

The same discipline, one notch weaker, at step 6: if the optimised `interval` does not reproduce the
current bounds exactly, it is abandoned rather than argued with.

---

## 16 · What this does not prove, printed rather than filed

Every run prints these, in `Report.notes`:

- **The six worlds are the six failure modes we thought of.** A curated set is not a proof of
  coverage. The estimator's validity does not come from passing them: a difference of means over
  randomly assigned units is unbiased under any data-generating process. That is a theorem. **The
  worlds do not test the subtraction; they test whether the machinery around it preserves it.**
- **There is no interference detector at readout, in any world.** §3. The defence is the design
  engine's exclusion, and W2's `U6` measures what happens without it — which is a measurement of a
  gap, not the closing of one.
- **Two Python implementations are not three mechanisms.** §8. Claim 5's SQL leg is T012.
- **The corpus is 100 stores.** Nothing here is extrapolated to 1,200, and no figure in this eval is
  reported without the scale it was measured at.
- **The world's prices are not certified prices.** The guardrail envelope is not in this path. §17.

---

## 17 · Deferrals this branch creates, closes and restates

| | |
|---|---|
| **closed** | *"CI's gate job carries a temporary timeout of 25 minutes"* — §12, with the measured figure |
| **closed** | *"the scenario scale is measured by hand, not by a gate"*, in part — `HARNESS` is measured **and** run by CI every push; the scenario scale stays a hand-measured README figure, and the entry is narrowed to say only that |
| **restated** | *"the world's prices are not certified prices"* — T003 was named as where this becomes concrete, and the answer is that it does not: `CLAUDE.md` enumerates claim 2's whole system without the decision path. **New unlock condition: phase 2, when a decision path exists to run a world through.** |
| **new** | *"the metric has one Python consumer checked against another, and no SQL consumer"* — §8. **Unlock: T011's dbt models and T012's `make claim-5`.** |
| **new** | *"W2's interference is measured, not detected"* — the eval publishes the cost of withholding the neighbour pairs; nothing in the four checks would notice interference the design engine did not exclude. **Unlock: a declared interference check would need a fifth validity check and a new `at_readout` code, which is a contract change with a restatement chain — the phase-1 integration session decides whether it is worth one.** |
| **new** | *"`close` cannot verify that the outcomes it is handed span the declared period"* — surfaced by W4's restatement, §3. `may_read` stops an early *read*; nothing stops a late read of an early *aggregation*. **Unlock: `U8` measures it for the harness's own caller; a check inside `core/` would need the period and the outcomes' own coverage to be comparable, which is a signature change and belongs to whoever adds the gold `outcomes` table in T011.** |
