# SPEC — T001 · the design engine and the experiment core

> `src/holdout/core/design/` and `src/holdout/core/experiment/`, as pure functions over plain data.
> This document is the decision record for the six things `CLAUDE.md`, `PLAN.md` and `TASKS.md`
> left open, and the build order that follows from them. Branch `core/design-experiment`.

## 0 · What this closes, and what it does not

`TASKS.md` T001. Closed when `src/holdout/core/design/` and `src/holdout/core/experiment/` exist as
pure functions over plain data, unit tests **and** a composition test are green, and the whole local
gate (`make check`) passes.

**Out of scope, restated:** the generator and the six worlds (T002), the A/A harness at K = 200 and
`make claim-2` (T003), any `claim-N` Makefile target, any `gate-proof` mutation, any directory under
`evals/`. A `claim-N` target added here with nothing planted against it makes `make gate-proof` red
by design — do not add one.

**Also out of scope, and stated so the seam is deliberate:** JSON Schema validation of a submitted
form. `core/` may not import `jsonschema`. A form arrives at the engine already parsed and already
shape-valid; the module that does that validation belongs in `src/holdout/adapters/`, which stays
empty in this branch with one line in its docstring saying so.

---

## 1 · The six decisions

| # | question | answer |
|---|---|---|
| 1 | permutation, or covariate-adjusted? | **Permutation under the restriction, with a covariate-adjusted statistic.** Validity from the lottery; precision from the adjustment. |
| 2 | which null? | **The weak (Neyman) null**, so the statistic is **studentized**. W5 is heavy tails and unequal arm variance, and a raw difference is only exact under the sharp null. |
| 3 | where does the interval come from? | **Inversion of the same test** over a grid of constant shifts, by bisection, reusing the same draws. Coverage is then correct by construction rather than by asymptotics. |
| 4 | exposure — adjust or refuse? | **ITT is the only number.** Below the declared threshold the readout refuses with `EXPOSURE_BELOW_THRESHOLD`. The realised exposure rate is published on every readout, pass or fail. No CACE, no exposure-adjusted estimate: the vocabulary is closed and there is no field for one. |
| 5 | where do α, power, the tolerance and the thresholds live? | **A new contract family, `contracts/design/inference.yaml`**, versioned with `effective_from`, every value carrying provenance. A `Decimal` constant in a `.py` file is precisely the "value without a source" the contract layer exists to refuse. |
| 6 | how many permutation draws? | **B = 1000, declared in the contract, drawn once per experiment and reused at every step of the interval's bisection.** The `(1 + hits) / (1 + B)` rule makes the level exact at any B — B buys resolution, not validity. |

And one that follows from the boundary rather than from taste:

| | | |
|---|---|---|
| 7 | the lottery, with `random` banned | **Keyed hashing.** `hashlib.blake2b(unit_id, key=…)` per unit, sorted. Deterministic, platform-stable, order-independent, and reproducible from the committed seed alone — strictly better than a PRNG for *"exactly reproducible"*, which is claim 3's whole sentence. |
| 8 | the sealed assignment | **The certificate pattern *and* a digest.** The unconstructible type protects the in-process path; the digest over `(seed, form, roster, arms)` is what survives the round trip through `gold.experiment_assignment` and back, which is the only way tampering will actually happen. |

---

## 2 · The contract that lands first

`contracts/design/inference.yaml` — new, and everything else depends on it.

```yaml
# Fixed here, not chosen per experiment — for exactly the reason balance_covariates.yaml is.
# An alpha chosen per experiment is a degree of freedom, and anything that can be chosen after
# the fact will be chosen after the fact.

version:        1
effective_from: 2026-03-01

alpha:                    { value: 0.05,  source: { … } }
target_power:             { value: 0.80,  source: { … } }
balance_tolerance_smd:    { value: 0.10,  source: { … } }
exposure_min_pct:         { value: 95,    source: { … } }
holdout_share_pct:        { value: 20,    source: { … } }
permutation_draws:        { value: 1000,  source: { … } }
max_assignment_attempts:  { value: 10000, source: { … } }
neighbour_radius_m:       { value: 1000,  source: { … } }

quantiles:
  z_two_sided_alpha: { value: 1.959964, source: { … } }
  z_power:           { value: 0.841621, source: { … } }

# Two declared facts about grocery retail, and the mitigation that is NOT declared. The
# interference table is derived from these three lines — see §3. They are assumptions about
# the trade, with a source, and they are not observations of anything in this repository.
carryover:
  reference_price_memory:
    value: true
    source:
      kind: scenario_assumption
      note: >-
        A shopper's willingness to pay at a store carries the price they last saw at that
        store. Widely described in the pricing literature as reference-price behaviour; no
        chain's own measurement was obtained and none is claimed.
      verified_on: …
  cross_price_substitution:
    value: true
    source:
      kind: scenario_assumption
      note: >-
        Fresh categories in one store contain substitutes, so a price move in one shifts
        demand in another. Assumed of the trade; not measured here.
      verified_on: …
  washout_weeks:
    value: null
    source:
      kind: scenario_assumption
      note: >-
        No washout period is declared. Declaring one long enough to exhaust the reference
        price is what would make a within-store, across-time unit admissible.
      verified_on: …
```

Rules this file inherits and one it adds:

- **Every value carries a `source`.** All nine are `kind: scenario_assumption` — none of them is
  law, and saying so is the whole point of the split. `PROVENANCE_FAMILIES` in
  `holdout.contracts.provenance` currently covers `guardrails` and `policies`; **`design` is added
  to it**, so a number here with no argument is a build failure like any other.
- **The two quantiles are computed twice.** They are standard-normal quantiles, so their `note`
  names the quantile and how to reproduce it, and `tests/contracts/test_inference.py` recomputes
  both with `statistics.NormalDist().inv_cdf` — legal outside `core/` — and asserts agreement to
  six decimal places. `evals/`'s rule 5 ("a boundary that has to be known is computed twice")
  applied to a constant.
- **It compiles to nothing.** No consumer is generated from it, so `compile_all` is untouched. It is
  still validated, claimed and provenance-walked by `make contracts`.

Contract-layer work it implies, all of which `make contracts` will demand:

| where | what |
|---|---|
| `contracts/schemas/inference.schema.json` | the schema, `additionalProperties: false`, every value a `{value, source}` pair |
| `loader.CLAIMED_FILES["design"]` | gains `inference.yaml` — an unclaimed file under `contracts/` is a build failure |
| `contracts/model.py` | `InferenceSettings`, frozen + slots, `Decimal` and `int` only |
| `ContractSet.inference` | the accessor `core/` is handed |
| `contracts/cli.py` | one more line on the green summary |
| `provenance.PROVENANCE_FAMILIES` | `+ "design"` |

### One code added to the closed vocabulary

`at_design: NO_ADMISSIBLE_ASSIGNMENT` — *the re-randomisation screen accepted no candidate
assignment within the declared attempt budget, so no lottery satisfying the declared restriction
exists for this roster.* `what_would_fix_it`: a coarser unit, a wider tolerance (a contract change
with a restatement), or a roster whose covariates are less extreme.

Adding a code is a code change with a test, which is the design. Without it, a roster on which the
screen never accepts has no correct output: raising would make an infeasible design an error, and
the whole point of the design engine is that infeasibility is a *refusal that names what would fix
it*. Touches `contracts/schemas/reason_codes.schema.json`, `contracts/vocabularies/reason_codes.yaml`,
`core/design/codes.py`, and the three-way agreement test.

---

## 3 · `src/holdout/core/design/`

```
design/
  __init__.py      re-exports + __all__, in the shape guardrails/__init__.py sets
  codes.py         DesignRefusalCode (8) — the at_design vocabulary, written out by hand
  form.py          the nine fields as frozen dataclasses, plus Unit / MdeKind / MdeDirection
  feasibility.py   moment 1 — can this experiment exist?
  refusal.py       DesignRefusal — returned, never raised
```

### `form.py`

`DesignForm` and its nested types, mirroring `contracts/design/form.schema.yaml` exactly:
`Intervention(treatment, control)` · `Scope(categories, products, stores)` ·
`Mde(kind, value, direction)` · `MaxDuration(weeks)` · `Exclusion(store_id, reason)` ·
`DecisionRule(if_significant, if_not_significant, if_refused)`, plus `filled_by`.

- `Unit(StrEnum)` = `store | store_week | store_category | region`, `MdeKind` =
  `relative_pct | absolute`, `MdeDirection` = `increase | decrease | either`. These enums live
  inline in the form schema, so the mirror test asserts against the YAML rather than against a
  schema `$defs`.
- **`Mde.value` is a `Decimal`.** The schema says `number`; the adapter converts at the boundary,
  exactly as the contract layer already converts PyYAML floats. A float reaching `core/` is a lint
  failure and, one line later, a real one.
- `DesignFormError(ValueError)` for a form that is *malformed* — an empty category list, a
  non-positive MDE, `weeks` outside 1..52. Malformed is not refused: a refusal is a correct output
  about a design, an error is a statement that the caller is wrong. The same split
  `EnvelopeError` / `Refusal` already makes.
- `filled_by` is parsed into `FilledBy(kind, name)` and then **ignored by every decision**. A test
  runs the identical form under all three attributions and asserts the three results are equal —
  that is the engine not knowing and not caring who filled it, made checkable.

### `feasibility.py` — moment 1

```python
def assess(
    form: DesignForm,
    *,
    metric: Metric,                       # resolved as-of by holdout.contracts.windows
    covariates: BalanceCovariates,
    inference: InferenceSettings,
    metric_ids: tuple[str, ...],
    roster: tuple[str, ...],              # every store in scope, before exclusions
    variance_per_unit_week: Decimal,      # historical, pre-period, at metric scale
    mean_per_unit_week: Decimal,          # needed only for a relative_pct MDE
    committed_elsewhere: frozenset[str],
    neighbour_pairs: tuple[tuple[str, str], ...],
    stopping: StoppingRule,
    previously_locked: DesignForm | None,
) -> Feasible | DesignRefusal:
```

No `contracts_dir`, no filesystem, no clock — the signature discipline `core/__init__.py` states.
Every check below is arithmetic over what was handed in.

**The eight refusals, and what decides each:**

| code | decided by |
|---|---|
| `METRIC_NOT_IN_CONTRACT` | `form.primary_metric not in metric_ids` |
| `UNIT_GUARANTEES_INTERFERENCE` | a declared table over the four units — see below |
| `EXCLUSIONS_DEFINED_POST_HOC` | `previously_locked is not None and its exclusions differ` |
| `UNITS_ALREADY_COMMITTED` | roster ∩ `committed_elsewhere`, after automatic exclusions |
| `STOPPING_RULE_PERMITS_PEEKING` | `stopping` is not a single readout at the declared end, or is group-sequential with no pre-declared spending function |
| `UNDERPOWERED_FOR_CAPACITY` | required per-arm sample > the control arm the holdout share allows |
| `UNDERPOWERED_FOR_DURATION` | the smallest number of weeks that reaches power > `max_duration.weeks` |
| `NO_ADMISSIBLE_ASSIGNMENT` | raised by `assignment.draw` and returned through, when the screen accepts nothing inside the attempt budget |

**The interference table is derived from a declared assumption, and it must not be made to look
like arithmetic.**

Two of the four units are refused. The refusal does **not** rest on anything observed in this
repository, and in particular not on what `corpus/world/` generates: the generator was written to
have reference-price memory and cross-price effects, so grounding the refusal in them would be the
generator and the engine agreeing with each other, and `core/` may not know that `corpus/` exists at
all. It rests on `contracts/design/inference.yaml`'s `carryover:` block — two stated facts about
grocery retail, each `kind: scenario_assumption` with a note and a verification date, and one
mitigation that is declared absent.

The rule, applied to the dimension each unit splits arms along:

| unit | splits arms along | refused while |
|---|---|---|
| `store` | stores | never — a store is what a shopper visits, and nothing in `carryover` crosses it |
| `region` | regions | never — strictly coarser than a store |
| `store_week` | **time, inside one store** | `reference_price_memory` is declared and `washout_weeks` is null |
| `store_category` | **categories, inside one store** | `cross_price_substitution` is declared |

**The table is computed from the contract, never written out.** `interference_of(unit, carryover)`
is a pure function of the declared block, so a contract that declared no reference-price memory, or
declared a washout long enough to exhaust it, would admit `store_week` with no code change — and
`tests/core/test_design_engine.py` asserts exactly that, by handing the function an independently
built `carryover` with the flag cleared and requiring the refusal to disappear. A hard-coded table
would pass every test while quietly being a second definition of a contract value.

What is code and what is not: *which* unit to randomise on has no single correct answer, so a model
may propose it. Whether a declared carryover fact crosses the dimension a given unit splits has
exactly one answer, so code decides it. The **assumption** is the load-bearing part and it is in the
contract; the code is only the derivation.

`docs/DECISIONS.md` gains the entry, under **Deliberately deferred**, with the condition that would
unlock it: a **declared washout period** at least as long as the reference price persists makes
`store_week` admissible, and a declared assortment separation would do the same for
`store_category`. Until one is declared and sourced, two of the four units the form admits are
refused — by a paragraph in a contract, not by a calculation.

**And a consequence for claim 6, recorded here because this is where it is created.**

Two of the four units are refused *by construction*, before any judgment has been exercised on
anything. So claim 6's headline — *N designs proposed, M refused, K of those would have produced a
confidently wrong number* — must be **broken down by reason code, and never reported as a single
aggregate M**. A `UNIT_GUARANTEES_INTERFERENCE` refusal is not the agent's judgment failing; it is a
design falling outside a declared envelope, in exactly the way `CATEGORY_FROZEN` is not a pricing
model failing. Adding the two kinds together flatters the engine — it counts as "caught" a design
whose judgment nothing ever inspected — and it defames the proposer, by charging it with an error it
did not make.

**Consequence for T026:** `evals/design/` publishes M per code, and says which codes are *scope*
refusals and which are *judgment* refusals, before it publishes any total. The same split governs
K: only a judgment refusal can be a design that would have produced a confidently wrong number, and
a scope refusal that was counted into K would be evidence of a catch that never happened.

**Automatic exclusions**, applied before every count: every `Exclusion.store_id` in the form; the
later-sorted member of each `neighbour_pair` (deterministic, so the same roster always yields the
same survivors); and every unit in `committed_elsewhere`.

**Power, and the arithmetic that is written down rather than approximated by a library.**

The MDE is converted to an absolute difference on the metric first — `relative_pct` against
`mean_per_unit_week`, `absolute` as given. Then, for `W` weeks and a per-unit-week variance `s²`,
the variance of a unit's mean over the window is `s² / W`, and

```
n per arm  =  ceil( 2 · (z_α + z_β)² · s² / (W · d²) )
```

with `z_α` two-sided from the contract (one-sided when `mde.direction` is not `either`), `z_β` from
the contract, `d` the absolute MDE. Every quantity is a `Decimal`; the one square root the whole
module needs is `Decimal.sqrt()` under a `localcontext()` with the precision `money.py` already
declares. `math` is never imported, and no float is ever produced.

- **capacity** — the control arm is `floor(available × holdout_share_pct / 100)`; the binding arm is
  the smaller one. `required > control_capacity` → `UNDERPOWERED_FOR_CAPACITY`.
- **duration** — the smallest `W` for which `required ≤ control_capacity`. `W > max_duration.weeks`
  → `UNDERPOWERED_FOR_DURATION`. If capacity fails at every `W ≤ 52`, the capacity code leads;
  `PRECEDENCE` over the design codes is written out exactly as `guardrails/codes.py` writes it, and
  **every fired code is carried**, not only the leading one.

`Feasible` carries the resolved metric version, the surviving roster, the required sample, the
planned arm sizes, the chosen `W`, and the exclusions that were applied automatically with the
reason for each. A `DesignRefusal` carries every fired code with its `what_would_fix_it`, in the
shape `Refusal` already has — sorted by a declared precedence, derived properties rather than stored
ones, and returned rather than raised.

### One limit, declared in the module docstring rather than papered over

**`decision_rule` is free text and code does not adjudicate free text.** The schema guarantees three
non-empty sentences and nothing more. `STOPPING_RULE_PERMITS_PEEKING` is therefore decided over a
structural value the engine itself holds — `StoppingRule`, which is either
`SINGLE_READOUT_AT_END` or `GROUP_SEQUENTIAL(spending_function, looks)` — and never over the prose.
It has no default: doctrine rule 3, a default here would be a lie with a plausible shape.

The guarantee that actually stops peeking is moment 2 (§4, `may_read`), which refuses to compute a
readout before the declared end whatever anybody declared. The design-time check is the announcement;
the readout-time block is the lock.

---

## 4 · `src/holdout/core/experiment/`

```
experiment/
  __init__.py        re-exports + __all__
  codes.py           ReadoutRefusalCode (4) · ValidityCheck (4) · the 1:1 map between them
  assignment.py      the keyed-hash lottery, the re-randomisation screen, SealedAssignment
  balance.py         the standardised difference — one function, used as screen and as check
  exposure.py        the ITT threshold
  contamination.py   redraw-and-compare, and the delivered-policy comparison
  estimator.py       difference of means · Lin adjustment · studentization · permutation · inversion
  readout.py         moment 2 and moment 3 — may this be read, and may this be stated
```

### `assignment.py` — the lottery, and the one door with no key

**The draw.** For a candidate index `d` and a unit id `u`:

```
key    = blake2b(seed_bytes || d.to_bytes(8, "big"), digest_size=32).digest()
rank_u = int.from_bytes(blake2b(u.encode("utf-8"), key=key, digest_size=16).digest(), "big")
```

Units are sorted by `(rank_u, u)` — the id breaks a tie, so the order is total and never depends on
the order the roster arrived in — and the first `control_size` become the control arm.

Properties this buys and a PRNG does not: reproducible from the committed seed alone with no
interpreter or platform dependency; independent of iteration order; and computable per unit, so the
readout can re-derive one unit's arm without replaying a sequence. `random` and `secrets` are banned
in `core/` anyway, but this is the better mechanism regardless.

**Re-randomisation.** Candidates `d = 0, 1, 2, …` are drawn and screened on the pre-period
covariates only, until one is accepted or `max_assignment_attempts` is reached. The accepted `d` is
recorded on the seal: **the reference set at readout is exactly the set of candidates the same screen
accepts**, which is what makes the inference match the restriction rather than assume simple
randomisation.

**`SealedAssignment`.** The `CertifiedPrice` pattern, one module along: `__slots__`, a constructor
that raises, `__init_subclass__` that raises, no `__setattr__`, no `__reduce__`, every field read
through a guarded accessor, and the filler held in a closure beside a witness with no importable
name. `draw()` and `sealed()` come out of one `_build()`. It carries `experiment_id`, `seed`,
`draw_index`, the arm per unit, a digest of the covariate matrix it was screened on, and

```
digest = blake2b(canonical_bytes(experiment_id, seed, form_digest, roster, arms)).hexdigest()
```

**Why both the type and the digest.** The type makes the mistake impossible inside the process. The
digest is what survives being written to `gold.experiment_assignment` and read back by a readout in
another process a month later — which is the only way an assignment will actually be altered. The
contamination check recomputes the digest from the seed and the roster and compares.

**The honest limit, in the docstring, in the shape `certificate.py` already sets:** a forger who
rewrites the arms, the seed and the digest in one coordinated edit is not caught, because a seal
never held independent evidence of its own provenance. A test asserts that limit rather than hiding
it. What *is* caught is every edit that is not coordinated — which is every edit that happens by
accident, and most that do not.

### `balance.py` — one statistic, two moments, and it is not vacuous

Per covariate, a standardised difference between arms:

- **numeric** — `|x̄_T − x̄_C| / s_pooled`
- **categorical** — the same quantity per level on the level's indicator,
  `|p_T − p_C| / sqrt(p̄(1 − p̄))`, taking the maximum over levels

One statistic, one tolerance (`balance_tolerance_smd`), no per-type special case. Exact in
`Fraction` up to the single `Decimal.sqrt()` at the end.

**The readout's balance check is not the screen re-run on the screen's own numbers.** It re-measures
the covariates from the data that actually arrived, over the units that actually reported. A screened
assignment re-checked against its own screening matrix would pass by construction — a gate that
cannot bite. Restated pre-period revenue, an attrited store, a roster that moved: those are what
`IMBALANCED_PRE_PERIOD` is for, and a test plants each of them and asserts the check goes red.

### `exposure.py`

`exposed_treated / assigned_treated` against `exposure_min_pct`. Below it,
`EXPOSURE_BELOW_THRESHOLD` and no number. Above it, ITT and the realised rate printed beside it.
There is no exposure-adjusted estimator in this repository and the docstring says why: the readout
vocabulary is closed, there is no code and no field for one, and an exposure-adjusted number carries
an exclusion restriction — an assumption, in a readout built to avoid them.

### `estimator.py` — the number, and whether it may be stated

Everything here is exact. **Outcomes arrive as integers at the metric's declared scale** — the
`canonical_integer` the metric contract's `Rounding` already produces — so every sum is an exact
integer and the only division is into a mean, taken in `Fraction`. There is no tolerance anywhere in
the estimator, which is the same reason `Money` is integer cents.

```python
def difference_in_means(outcomes, arms)                    -> Fraction
def adjusted_difference(outcomes, arms, covariates)        -> Fraction
def studentized_square(outcomes, arms, covariates)         -> tuple[Fraction, int]   # (T², sign)
def permutation_p(observed, draws, outcomes, covariates, *, direction) -> Fraction
def interval(outcomes, arms, covariates, draws, *, alpha)  -> tuple[int, int]
```

- **The adjustment is Lin's estimator** — covariates centred and interacted with the arm, so a
  misspecified adjustment cannot make the estimate *worse* than the unadjusted difference in large
  samples. Categoricals are one-hot with a reference level. The normal equations are solved by exact
  Gaussian elimination over `Fraction`: five covariates is roughly eight columns over a hundred
  rows, and `fractions` is stdlib and not on the ban list. No numpy, no floats, and the adjusted
  estimate is bit-identical on every machine.
- **The statistic is studentized and compared as a square.** `T² = adj_diff² / (s²_T/n_T + s²_C/n_C)`
  over the adjusted residuals, exact in `Fraction`, so the hot loop takes no square root at all.
  `Decimal.sqrt()` appears once, for the reported `T`. For a one-sided `mde.direction` the signed
  statistic is compared instead.
- **The p-value** is `(1 + #{T²_b ≥ T²_obs}) / (1 + B_accepted)`, over the draws the same screen
  accepted. Exact at any B — B buys resolution, not validity, and the report prints B beside the
  p-value so nobody has to guess which it was.
- **The interval inverts the same test.** Over `y_i − τ·1{arm = T}`, bisection on each side of the
  point estimate, brackets found by doubling, **terminating at one canonical metric unit** — so both
  endpoints are integers in the metric's own unit, with no tolerance and nothing to round. The same
  1000 draws are reused at every step, which is what keeps the cost at ~B rather than B × steps and
  what makes the endpoints deterministic.

### `readout.py` — moments 2 and 3

```python
def may_read(*, asked_on: date, period_ends_on: date) -> bool
def close(seal, outcomes, exposure, covariates_at_close, *, inference, metric,
          data_version: str, period) -> Readout | ReadoutRefusal
```

`close` runs the four checks in the declared order — balance · exposure · contamination · power —
**all four, always**, so the report carries four figures whether or not one of them failed. Any
failure returns a `ReadoutRefusal` carrying every fired code and no number. All four passing returns
a `Readout` carrying the uplift, the interval, the p-value, B, the four check figures, the pinned
`data_version`, the seed, the accepted draw index and the digest.

`POWER_NOT_REACHED` is decided on **realised** variance and realised sample against the declared
MDE, not on the pre-experiment approximation — that is the honest half of W5, where the design
believed a variance the world did not supply.

The engine never chooses what to test and never decides what to do about the answer. It decides only
what may be claimed.

---

## 5 · Tests

Under `tests/core/`, flat, as `guardrails/` and `ladder/` already are.

| file | what it defends |
|---|---|
| `test_design_engine.py` | each of the eight design refusals, each fired alone; the interference table over all four units; the power arithmetic against hand-worked numbers; the three `filled_by` sources producing identical results |
| `test_assignment.py` | the same seed twice is byte-identical; a one-character change to one unit id moves that unit and no other; the roster's arrival order does not matter; the accepted draw index is recorded and reproducible |
| `test_assignment_forgery.py` | the `SealedAssignment` walked the way `test_certificate_forgery.py` walks the certificate — construction, subclassing, `replace`, `copy`, `deepcopy`, `pickle`, `object.__new__`, a look-alike; and the declared limit asserted rather than hidden |
| `test_balance.py` | the statistic against hand-worked numbers on both types; the screen and the check are the same function; **and each of restated covariates, attrition and a moved roster turning the check red** |
| `test_estimator.py` | the difference of means on a table small enough to check by eye; Lin's adjustment against a hand-solved 2-covariate system; `p = (1+h)/(1+B)` exactly; the interval's endpoints as integers, and that they bracket the point estimate |
| `test_readout.py` | each of the four refusals fired alone; all four figures present on a refusal; `may_read` refusing before the end |
| `test_experiment_composition.py` | **the closing condition** — see below |
| `tests/contracts/test_inference.py` | the new contract: schema, provenance, and the two quantiles recomputed with `statistics.NormalDist` |

### The composition test is the closing condition, not an extra

`docs/DECISIONS.md` records why: a branch delivered `ladder/` and `guardrails/` and never ran one
into the other, and the declared safe state produced a price the envelope refused for one base price
in five. **This branch delivers two packages.** So the test that matters runs the whole path:

> a form → feasibility → the committed seed → the screened draw → a sealed assignment → delivered
> outcomes and exposure → the four checks → a number with an interval

and, beside it, the shape T003 will scale up: **the same policy in both arms**, over a handful of
seeds, asserting that the reported p-values are not concentrated where an A/A split says they cannot
be. That is a smoke test here and a claim at K = 200 in T003 — but a branch that delivers an
estimator and never runs an A/A through it is the same mistake, one module along.

### Two things that will go red the moment the packages exist

- `tests/core/test_decision_key.py` walks every module under `holdout.core` and fails on any frozen
  or slotted class absent from its hand-written `EXACT_FIELDS` map. **Every new dataclass in both
  packages is added to it**, which is claim 7 doing its job on new code.
- The same file scans field names against `PERSON_SHAPED`, which includes `segment`, `cohort`,
  `basket`, `subject` and `profile` — all plausible words in an experiment module. The vocabulary
  here is `arm`, `unit`, `stratum`, `roster`. Never `cohort`, never `segment`.

---

## 6 · Build order

1. `contracts/design/inference.yaml` — including the `carryover:` block — plus its schema, the
   loader entry, `model.InferenceSettings`, `PROVENANCE_FAMILIES` and
   `tests/contracts/test_inference.py`. `make contracts` green.
2. `NO_ADMISSIBLE_ASSIGNMENT` into the schema, the vocabulary and the three-way agreement test.
3. `docs/DECISIONS.md` — two entries, written before the code that depends on them: the inference
   settings under **Method** (why they are a contract and not constants), and the interference
   refusal under **Deliberately deferred**, with the declared washout period as its unlock
   condition. An item with no unlock condition is not deferred, it is forgotten.
4. `core/design/codes.py` and `form.py`, with the mirror tests.
5. `core/experiment/assignment.py` and `balance.py` — the lottery before the engine that calls it,
   because feasibility returns the screen's refusal.
6. `core/design/feasibility.py` and `refusal.py`.
7. `core/experiment/estimator.py`, then `exposure.py` and `contamination.py`, then `readout.py`.
8. The composition test.
9. `src/holdout/core/__init__.py` — replace the "still to come" paragraph with the two rows the
   table now earns. `src/holdout/adapters/__init__.py` — one line naming where form validation goes.
10. `make check` green: `lint · typecheck · contracts · test`.

---

## 7 · What this does not prove, printed rather than filed

- **The estimator is not validated by these tests.** A difference of means over randomly assigned
  units is unbiased under any data-generating process — that is a theorem. What the tests defend is
  the machinery around it. Whether the machinery preserves that validity is claim 2, and claim 2 is
  T003.
- **The power calculation is a normal approximation**, declared as such. It decides feasibility
  before the experiment; it decides nothing at readout, where the realised variance does.
- **`decision_rule` is free text and is not adjudicated.** Code judges the structural stopping rule
  and nothing else. What stops peeking is the readout's refusal to compute before the end.
- **The seal is tamper-evident, not tamper-proof.** A coordinated rewrite of the arms, the seed and
  the digest is not caught. Every uncoordinated one is.
- **Two of the four units are refused before any judgment is exercised**, so nothing here shows
  that the engine catches a *bad* design — only that it refuses one outside the declared envelope.
  A single "M refused" would conflate the two. Claim 6's numbers are per reason code, split into
  scope refusals and judgment refusals — see §3.
- **No world has run through this yet.** Every number in these tests comes from a table its author
  chose. The inputs its author did not choose arrive with T002 and T003 — which is the difference
  between a suite and an eval, and the reason this branch stops before `evals/`.
