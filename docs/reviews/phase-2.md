# Phase 2 — integration review (oversight level 3)

**T016 · 2026-09-05 · branch `docs/phase-2-integration`**

Oversight level 3 reads the whole repository against `CLAUDE.md` and reports conceptual drift.
**It builds nothing.** Each proposed fix becomes its own branch with its own review.

**What was run to produce this report**, on a fourteen-core laptop, against `main` at `21c31f2`:

```
make check                    1540 passed, 55 deselected, exit 0
make eval-guardrail           green 10/10
make eval-assignment          green 10/10
make eval-censoring           green 12/12
make eval-oversight           green 12/12
make eval-uplift              green 13/13          8m33s wall, warm .worlds
make claim-5                  green  4/4 · 3/3 mutations     ) in an isolated venv with the
make silver                   16 passed                      ) dbt extra, outside the shared
make gold                     22 passed                      ) checkout's .venv
make gate-proof               green  9/9 · 53 mutations · 68 checks
make figures / findings / expiry / language / terraform      green
python -m ops.roster          at `scenario` and at `harness`
the GitHub API                the `main` ruleset, the repository's visibility, and the
                              step-level durations of four `ci` runs
```

**`eval-uplift` was run, and this line exists because the phase-1 report did not say whether it
had been.** `.claude/skills/integration-review/` names that silence as a hole in its own record;
it is closed here by measurement rather than by inheriting the omission. Claim 2 is 13/13 at
`harness` on this laptop.

**Two things this report contains that no reading produced.** Section 1's finding was found by
planting a mutation on the one mechanism claim 5 has none for, and section 2's by asking the
GitHub API for four runs' step timings. Everything measured is stated with the command that
produced it.

---

## 0 · What stands

**No claim's proof has collapsed, and phase 2's new claim bites where it says it does.** All six
claim targets are green. `make gate-proof` audits 53 mutations over 68 declared checks with no
orphan and none editing a detector. Both independence barriers hold **in the direction they were
built for**: no module under `corpus/` names `holdout` in an import, and no mutation edits `ops/`
or `corpus/`. §13 is the direction one of them was not built for, and it is the only finding here
that touches whether a claim is true.

`python -m ops.roster` reproduces exactly the table `CLAUDE.md` restated on 2026-08-29 —
`scenario` 100 → 18 → 17 → **83** → 16, W2 100 → 47 → 34 → **66** → 13, `harness` 320 → 59 → 51 →
**269** → 53, W2 320 → 148 → 98 → **222** → 44. The claim-4 figures `CLAUDE.md` restated on the
same day are reproduced too: 80,640 store-days, 21.0% emptied, −6.0% at the last trading hour and
−91.4% at the first. Doctrine rule 1's restatement holds: 716 of 26,600 ladder quotes refused by a
ceiling and 6,650 by a rule with no bound.

**The drift I found is in the instruments and in the documents, not in the estimators.** One
published number in a claim's own output is capped by a parameter; one barrier's runtime half
knows one of the two spellings its source half declares; four deferrals are closed in prose and
counted open; and two directories the map says do not exist have existed since 2026-09-04.

**And one thing is not drift at all.** §15 is the largest section of this report and it is not a
defect in anything: three joins on the path phase 3 is built to drive have no implementation and
no task id, each half already filed by the atom that found it and each correctly disowned. Read
that section before the list of corrections; it is the only one that changes what phase 3 can be.

---

## 1 · Does any claim's proof rest on something that has become a tautology?

**No. But claim 5's published disagreement count is capped at five, and the mechanism the eval
calls load-bearing owns no mutation.** Both were found by planting one.

### 1a · The count is capped at five and the docstring says *every*

`evals/definition/checks.py::_disagreements` takes `limit: int = 5` and **breaks out of the loop**
when it reaches it. `compare()` then publishes `len(broken)` as the check's figure:

```python
figure=f"{len(set(left) | set(right))} cell(s), {len(broken)} disagreeing"
```

Measured directly, with no pipeline involved — twenty cells, every one of them different:

```
20 cells all disagreeing -> 5 reported
docstring, first line:  "Every cell the two do not agree on, including cells one has and
                         the other does not."
```

**`passed` is unaffected and the claim does not become false**: any disagreement fails the check.
What is wrong is the number beside it, and it is wrong in the flattering direction — a one-cent
disagreement and a catastrophic one print the same figure. `evals/README.md`'s fifth rule is
*numbers, not a green tick*; this is the number, and it stops counting at five with nothing saying
so. Claim 1's `G6` is the contrast: it publishes `716` and `6,650` as counts and truncates nothing.

**Measured on a planted mutation** (section 1b): 349 cells present in both Python paths and absent
from the SQL, published as `481 cell(s), 5 disagreeing`.

**And the same numbers block hard-codes the constructed cell**:

```python
("cells", f"{len(sql):,} — {len(sql) - 1:,} from the corpus, 1 constructed"),
```

On the mutated run the SQL had dropped the constructed cell, and the line read *"132 — 131 from
the corpus, 1 constructed"* where the truth was 132 from the corpus and **0** constructed. The
breakdown is a subtraction against an assumption rather than a count, and it fails on exactly the
run where the eval's own constructed cell has gone missing.

*Branch:* `evals/claim-5-counts-what-it-found`

### 1b · The load-bearing third mechanism has no mutation — planted, and it bites

All three of claim 5's mutations edit `evals/definition/`'s two Python paths:

```
01 rounding-lands-on-every-row-instead-of-every-cell   evals/definition/combine_then_aggregate.py
02 a-float-where-the-contract-says-decimal             evals/definition/aggregate_then_combine.py
03 a-cell-only-one-source-has-is-dropped               evals/definition/aggregate_then_combine.py
```

None edits the compiled SQL, `metric_parts`, any compiler or `pipelines/gold/`. The eval's own
printed note calls that mechanism *"the load-bearing third … because it was compiled by a
different mechanism at a different time"*, and it is the one nothing has been shown to catch.

**Planted, in a copy of the tree, the same misreading mutation 03 plants on the Python side** —
`metric_parts`'s `left join` read as an inner join, which is `join: full_outer_on_grain` in the
contract read as an intersection:

```
before regenerating   holdout-contracts check   FAILED 4 contract violation(s)  [stale_artefact]
after regenerating    holdout-contracts check   OK 15 artefact(s) · every byte matches
                      python -m evals.definition
                        FAIL D1.integer-equal  481 cell(s), 5 disagreeing
                        FAIL D2.integer-equal  481 cell(s), 5 disagreeing
                        pass D3, pass D4       RED 2/4
```

Two things follow, and the first is good news. **`make contracts` is green on a compiler that is
wrong**, because it compares bytes against a recompile and a wrong-but-consistent compiler agrees
with itself — which is precisely the gap claim 5 exists to fill, now demonstrated instead of
argued. **And claim 5 does bite there**, so arming it costs one YAML file and no new code.

*Branch:* `evals/claim-5-arms-the-sql-mechanism`

### 1c · Eight checks are unarmed and name no reason, and one of them arrived after the gate did

`make gate-proof` prints **37 armed · 23 declared un-armable · 8 unarmed**. `PLAN.md`'s landing
note for `evals/unarmed-checks` (2026-08-31) records **7**. The set differs by exactly one:
`D4.tool-definition-matches-the-contract`, from claim 5, landed 2026-09-04 — four days after
`evals/README.md`'s seventh rule gained a gate and says of it:

> *this is what applies it, and what stops the next one being written from prose.*

The next one was written from prose. The gate prints and does not refuse, deliberately and for a
stated reason; what is false is the clause claiming it stops anything. `D4` is armable — a
mutation to the compiled agent tool's rounding would break it — and it has no `unarmed_because`.

The other seven are `C5`, `C9`, `G4`, `G6`, `G8`, `U5` and `U9` — phase 1's eight, less `G7`,
which `evals/unarmed-checks` armed rather than excused. *(Phase 1's §1 said **8 of those name no
reason** and listed seven names; `C5` is the eighth, and the arithmetic only closes with it.)*

*Branch:* `evals/d4-is-armed-or-says-why`

---

## 2 · Has any gate stopped biting — and for what reason?

### 2a · `discover`'s floor is one below what exists, and the sentence that says a gate prevents this points the other way

```
uv run python -c "from ops import figures; print(figures.discover_floor(), figures.claim_targets_that_exist())"
8 9
```

`ci.yml`'s `discover` refuses below `FLOOR=8`. Nine targets exist: `claim-1 claim-2 claim-3
claim-4 claim-5 claim-7 gate-proof silver gold`. The floor moved 6 → 7 with `silver` and 7 → 8
with `gold`; **`claim-5` landed on 2026-09-04 and it did not move.** Its own comment says
*"FLOOR is what exists today"*, and today it is one less.

The same comment says:

> *`make figures` checks this number against the Makefile, so it cannot go stale downward.*

`ops/figures.floor_failures` refuses only `floor > exists`. Measured, by renaming one target at a
time in a copy of the Makefile and re-running both instruments:

```
claim-5  renamed away   discover finds 8   floor 8   discover refuses: no   figures refuses: no
gold     renamed away   discover finds 8   floor 8   discover refuses: no   figures refuses: no
silver   renamed away   discover finds 8   floor 8   discover refuses: no   figures refuses: no
gate-proof renamed away discover finds 8   floor 8   discover refuses: no   figures refuses: no
```

`claims-complete` aggregates only what `discover` emits, and `claims-complete` is one of the three
contexts the `main` ruleset requires. **The number that argues against this**: three of the four
are caught elsewhere — a renamed `gold` or `silver` is refused by `figures.unrun_target_failures`,
and a renamed `claim-N` by `tests/evals/test_ledger.py`, which requires every mutation's claim to
have a Makefile target. The floor is the backstop for the case those miss, and it is the one that
is one short.

*Branch:* `ops/the-floor-is-what-exists`

### 2b · Four deferrals are closed in the registry's own prose and counted open by the gate

`make expiry` reports **`36 entr(y/ies) in the section: 31 open, 5 closed`**. `ops/expiry.py`
reads one marker:

```python
_CLOSED = re.compile(r"\*Closed:\*[ \t]*(?:\n[ \t]*)?(?P<date>\d{4}-\d{2}-\d{2})", re.IGNORECASE)
```

Four entries record a full closure in bold prose instead, and are counted open:

```
docs/SCENARIO.md and docs/DAY-ONE.md                   "Closed 2026-09-02 by T015"
No threshold at which a reconstruction stops being usable   "Closed 2026-09-04 by T014"
The censoring correction has no consumer               "Closed 2026-09-04 by T014"
No source has declared what stocked_out_from_hour means     "Closed 2026-09-04"
```

So nine closures are written in the file and the gate reads five. **The true open count is 27, not
31**, and `oldest condition-only deferral is 8 day(s) old` is computed over a population four
entries too large.

**The gate is `ops/expiry-knows-what-closed`, written on 2026-08-31 for exactly this** — phase 1's
§2a, *"`make expiry` counts closed deferrals as open"*. It was correct, published, and every
closure written since has used the other spelling. That is `ops/expiry-knows-what-closed`'s own
lesson — *a new rule is not applied to what already exists unless somebody runs it there* —
pointing forwards instead of backwards.

**Two entries my scan flagged and that are correctly open**, stated because a coverage question
has two directions: *One pooled availability curve per world* says *"the entry stays open on its
own terms and that is the point of it"*, and *The regulated basket's benchmark* says *"half of this
closed"*. Neither is a defect, and a fix that read `**Closed` as a marker would close both wrongly.

**And this session's own entries instantiate the entry above it.** `make findings` prints
`as of 2026-09-04` and ages the sixteen entries filed today at **`-1d`**, because both registers
compute today as `datetime.now(UTC).date()` and this was written after midnight in the author's
day. `docs/FINDINGS.md` already carries *`make expiry` judges in UTC against dates written in the
author's local day* as `adrift`; it now has an instance produced by the register itself rather than
by a deferral, which is a cheaper thing to point at than an argument.

*Branch:* `ops/a-closure-is-read-however-it-is-written`

### 2c · `make language` reproduces the instance its own comment records

`ops/language.py::content_files` walks the working directory and excludes a hand-kept
`NOT_CONTENT`. Its comment counts three instances of what that costs — `.shards/`, *"a stray
worktree that reddened one laptop and no runner"*, and `.terraform/` — and names the fix without
taking it: *"the population it ought to be computed from is what git tracks."*

Measured, in this session, by putting a git worktree at `.claude/worktrees/phase-2-integration` —
a directory that exists on disk in this tree, untracked and not in `.gitignore`:

```
make language   → 304+ offences, all inside the worktree copy, exit 1
```

Every excepted path in `EXCEPTED_PATHS` is repo-relative, so the copy's
`.claude/worktrees/…/contracts/guardrails/prior_price.yaml` is a different path and the verbatim
Greek law inside it is read as a violation. **The worktree instance is already on the module's own
list and the list was never given an entry for it**, so the second worktree reproduces the first
exactly. `ops/figures._layout_population` asks git, one module along in the same package, for the
same reason.

The worktree was moved outside the repository and `make language` is green again.

*Branch:* `ops/language-asks-git-too`

---

## 3 · Does the code still say what `CLAUDE.md` says it says?

### 3a · Two directories the map says do not exist have existed since 2026-09-04

`CLAUDE.md`'s *Declared and not yet built — phase 2 and later* still lists `pipelines/ml/` and
`infra/`. `pipelines/ml/` landed with `T014` and holds nine modules; `infra/` landed with `T013`
and holds `infra/lakehouse/`. Only `experiments/` is still true.

**And `make figures` counts `infra` as *named* on the strength of that block.** Measured by
splitting the layout section at its own heading and asking which tracked top-level directory
appears in neither half:

```
infra    present block: False    future block: True
```

It is the only one. `layout 23 = 23` is green partly because a sentence says the directory does
not exist. `docs/FINDINGS.md` already carries *the layout block's third crossing* and *nothing
checks that a directory declared not yet built is still unbuilt*; this is the fourth and fifth
crossing, and the new half is that the coverage row is not merely silent — it is **counting the
false side as coverage**.

**The author's.** Named for his list, not fixed here.

### 3b · A package says it has four consumers and lists five

`src/holdout/contracts/compilers/__init__.py:9` — *"The four consumers of the metric contract:"* —
is followed by five bullets, the fifth being `generated/dashboards/`, added by `T013`.
`src/holdout/contracts/compilers/dashboard.py:7`, in the same package and the same commit, opens
*"A fifth consumer"*. The package contradicts itself one file apart.

`docs/FINDINGS.md` already carries *three consumers named in three files, four emitted*; its three
sites are `CLAUDE.md`, `PLAN.md` and `TASKS.md`, and it was filed before the fifth existed. This
site is in code and is new.

*Branch:* `contracts/the-count-matches-the-list`

### 3c · Claim 2 prints two disclaimers that have stopped being true, on every run

`evals/README.md`'s sixth rule: *"What this does not prove is printed on every run. Not kept in a
README where it can quietly stop being true."* Two of the five notes in
`evals/uplift/checks.py::report` have:

```
"claim 5, with two Python implementations. The dbt model and the SQL function are
 T011 and T012, and the deferral in docs/DECISIONS.md carries them as its unlock"
```
Both landed on 2026-09-04. Claim 5 exists, is green, and executes the compiled SQL.

```
"that the world's prices are certified prices — the guardrail envelope is not on this
 path, and the deferral that says so names phase 2 as its unlock"
```
The deferral names **T003** (*"T003 is the first eval to run a whole system over a world and is
where the question becomes concrete"*), which landed on 2026-08-28; its condition is *the decision
path being exercised end to end against a world*, which is phase 3's `run`. Three statements about
one deferral, and no two of them agree.

*Branch:* `evals/the-printed-disclaimer-is-re-read`

### 3d · A check id in prose that no check carries

`evals/definition/__init__.py:50` ends *"it is a property of the pipeline, established in `T010`
and `T011`, and it is `D5`."* `D5` occurs **exactly once in the repository** — in that sentence.
Claim 5 declares `D1`, `D2`, `D3`, `D4`; the drop it describes is published as a number
(`sales with no published cost  6,515 of 428,652`). `make figures`'s `armed-or-says-why` row
enumerates `Check(...)` ids, so a check named only in prose is outside every population.

*Branch:* folded into `evals/claim-5-counts-what-it-found`

---

## 4 · Is there code that serves no claim?

Phase 1's answer — `src/holdout/core/pricing/selection.py` — is still `adrift` in
`docs/FINDINGS.md` and is unchanged. Phase 2 added four packages, and `pipelines/ingest/`
established the standard for them in its own docstring:

> *A module that serves no claim and says so is a different object from one that serves no claim
> and does not — `docs/reviews/phase-1.md` §4 is open against the second kind.*

Measured against that standard, by asking which packages any eval imports:

```
pipelines/ingest/   no eval          says "It serves no claim"                     correct
pipelines/silver/   claim 5's eval   says "It serves no claim ... the layer they
                                     are eventually computed over"                 false since 2026-09-04
pipelines/gold/     claim 5's eval   says nothing about claim standing             carries a mechanism
pipelines/ml/       no eval          says nothing about claim standing             the second kind
```

`evals/definition/build.py` imports `pipelines.silver.build` and `pipelines.gold.build` and runs
both on every `make claim-5`. **The two statements are the wrong way round**: the package that is
genuinely upstream of the comparison declares it serves no claim, and the package that materialises
claim 5's third mechanism declares nothing. `pipelines/ml/` is the second kind exactly as
`pipelines/ingest/` defines it.

*Branch:* `pipelines/each-package-says-what-it-serves`

---

## 5 · Has a claim landed on a preview surface?

**Undetermined, deliberately, and it is the author's** — but it has stopped being hypothetical, and
that is the change since phase 1, which answered *no* on the grounds that there was no `infra/`.

There is now `infra/lakehouse/`, holding two `databricks_dashboard` resources whose
`serialized_dashboard` is a compiled consumer of the metric contract. `make preview-audit` does not
exist; its deferral is correctly restated, with the remaining half's unlock condition naming an
event — *the declared inventory of preview surfaces exists* — and that inventory needs `T015`'s
Zerobus question answered. The population is no longer empty and no longer imaginary: it is the
`databricks_dashboard` resource, Zerobus, and the Unity Catalog metric view.

**No finding of mine.** Recorded so that `T017` is not entered believing phase 1's answer.

---

## 6 · Is there still exactly one door with no key?

**There are now four seals of identical construction, the fourth declares the same limit, and the
doctrine's restatement is what makes that correct rather than a drift.**

`pipelines/gold/assignment.py` joins `CertifiedPrice`, `SealedAssignment` and
`corpus/world/seal.py`. It measured what Delta gives and published it:

```
update / delete / insert overwrite   DELTA_CANNOT_MODIFY_APPEND_ONLY   refused
insert into                          allowed
```

and says in its own first paragraph *"today the guarantee is detection plus three of four storage
refusals; unopenability is phase 3."* That agrees with the restatement `T008` put in `CLAUDE.md`.
Nothing here widens the claim.

**One sentence in `CLAUDE.md` did not move with it.** The Gold section still reads *"The assignment
table is written before the period opens, from the committed seed, and is then **read-only**."* It
is append-only, and the module that built it says so. **The author's.**

---

## 7 · The deferral registry as a population

```
36 entries · 5 read as closed by the gate, 9 closed in the file (see §2b)
27 genuinely open: 4 carry a date, 23 carry an unlock condition only
14 unlock conditions name a task id · 2 name a session, and both are already restated
```

**The other register is not in the same shape, and the number is worth putting beside this
one.** `make findings`, before this review filed anything: **72 findings, 64 open, and 23 of the 64
`adrift`** — no branch, no task, a written reason. A third of the open register has nobody scoped
to it. `adrift` is a real state and deliberately does not turn the gate red, so this is not a
defect; it is the size of the thing nobody had asked the instrument for, and it is published here
because the review's own briefing put the register at *roughly thirty*.

**The deferral registry is in better shape than phase 1's, and the number that says so is one.** Of the
fourteen conditions naming a task, **thirteen name something that has happened**, and **twelve of
the thirteen carry a restatement or a closure written when it did** — *The generated SQL has never
been executed* (revised condition: the estate, where `${catalog}` resolves), *Claim 2's eval has no
three-question README* (restated by the task it named, which did not fire it, and re-anchored to
*the next change that edits any module under `evals/uplift/`*), *One pooled availability curve per
world* (fired, answered, and deliberately kept open on its own terms), both `terraform validate`
halves, and six closures. Phase 1 found **nine** entries pointing at one session; that shape is
gone.

**One of the thirteen is not.**

> **Claim 7 is proved over `holdout.core` and the contracts, and nothing else exists yet**
> *Unlock condition:* T011, which builds the gold layer.

`T011` landed on 2026-09-04. The entry is unchanged and `make expiry` cannot see it, because it
checks that a condition is present and never that it is true.

**Measured, so the exposure is a number rather than an alarm.** `evals/oversight/` scans
`src/holdout/` and `generated/`. `pipelines/` is 30 modules and is scanned by nothing in claim 7.
Running the eval's own reader and its own 317-name lexicon over `pipelines/`:

```
1,421 identifiers · 541 distinct names
collisions with the two published person-vocabularies: 1 — `parents`, at seven sites,
already on claim 7's explained list for the same reason it is there for src/holdout/
```

**The route is uncovered and it is clean today.** That is the moment to extend the scan, and it is
what the entry's own text asks for: *the silver tables' declared schemas and the Lakebase decision
record — the two places a customer column would arrive with a straight face.*

**And the fourteenth points at a task that did not meet it.** *The world's prices are not
certified prices* names T003 as *"where the question becomes concrete"*; T003 landed and its eval
prints, on every run, that the guardrail envelope is not on its path. The entry is correctly open;
what failed is the forecast beside its condition. The condition itself names an
event and is unmet; the sentence naming which task would meet it was a forecast, and
`docs/DECISIONS.md` already has the rule for that — *a prediction about what a task will touch is
not an event in the repository* — written on 2026-09-04 about a different entry and not swept over
this one.

*Branch:* `docs/the-condition-that-fired-at-T011`

---

## 8 · The recurring rule — is it complete?

**It is complete, it is armed in one place, and the arming reaches two numbers, both of which the
same module computes about itself.**

`ops/figures.PROSE` is the `[M]` half phase 1 §8 called *worth more than all the other corrections
together*. It holds two entries:

```
ops/language.py  "uses **<n>** distinct Greek tokens"        len(language.ALLOWED)
ops/language.py  "outside the <n> excepted paths"            len(language.EXCEPTED_PATHS)
```

Both recompute a constant from the module whose docstring asserts it. That is a real check and it
is not the class §8 was about: of the six incidents §8 said would have gone red — the 11/11, the
W5 counts, the 100→109→45 chain, *about 36M*, the cache hypothesis — **none is registered, and
neither is anything a claim publishes.** `docs/SCENARIO.md` carries eight `[M]` tags with the
command beside each and no command re-runs them; the docstring says so.

The list's own defence is written down and is good: doctrine rule 4 keeps superseded figures in
`PLAN.md` and `TASKS.md`, so only present-tense text can be registered and which text that is
remains a judgment. **What that defence does not reach is present-tense measured text that is not
in those two files** — `CLAUDE.md`'s claim rows, the evals' READMEs, the workflow comments. I
re-ran every present-tense measured figure in `CLAUDE.md` I could find a command for. **One is
stale** (§9), and I could only find that by running six evals.

**No new rule is proposed and that is deliberate.** `CLAUDE.md`'s own argument for waiting — that a
rule generalised at three instances is scoped to the forms those three wore — applies here too:
one measurement of one stale figure is not grounds to widen `PROSE`, and widening it by hand is
the same act as keeping `NOT_CONTENT` by hand (§2c). What is worth recording is the size of the
gap: **two registered figures, against every claim's published numbers.**

*Branch:* none — `docs/FINDINGS.md`, with the count and the argument for not acting yet.

---

## 9 · The author's list — `CLAUDE.md`

Five, and the first is a measured figure rather than a description.

| | what it says | measured |
|---|---|---|
| claim 7's row | *the closed field set refuses **17,752 of 17,752*** | `make eval-oversight` → **18,069 of 18,069**. The other half, *the hand-written list catches 35 of 317*, holds exactly |
| the layout block | `pipelines/ml/` and `infra/` under *Declared and not yet built* | both built 2026-09-04; `infra` is the only tracked top-level directory named nowhere else, so `make figures` reads `23 = 23` off that block (§3a) |
| Gold | *the assignment table … is then **read-only*** | `delta.appendOnly`: three of four refusals, append permitted, and `pipelines/gold/assignment.py` says so (§6) |
| the contract layer | *`contracts/` … **Four families*** | five — `contracts/ml/` landed with `T014`, and `TASKS.md` L26 calls it *a fifth contract family* |
| the visible surface | *the terminal carries the figures that matter most — `9/200 = 4.5%`* | the eval has never printed it; `U1` is **8/200 = 4.0%**, which is what `PLAN.md` and `TASKS.md` carry. Illustrative rather than asserted, and it reads as measured |

---

## 10 · The question no reading of this tree can answer

> **What does the `main` ruleset require, and does that list match the jobs `ci.yml` defines today?**

Asked of the API on 2026-09-05:

```
ruleset "main"  enforcement active  bypass_actors []  current_user_can_bypass never
  deletion · non_fast_forward
  pull_request  required_approving_review_count 0 · required_review_thread_resolution true
  required_status_checks  strict  →  gate · secrets · claims-complete
ci.yml defines: gate · discover · claims · combine · claims-complete · secrets
```

**The three required contexts cover all six jobs, and each uncovered path is refused by name.**
`discover` failing or emitting nothing leaves `claims` `skipped`, which `claims-complete` refuses
explicitly; `combine` is refused unless `any_combine` is false. The hole phase 1 found is closed
and has stayed closed.

**Two facts worth carrying forward.** `required_approving_review_count` is **0**, so `main` is
protected by checks and not by a reviewer — which is correct for a solo repository and is worth
knowing before another pair of hands touches it. And the ruleset was last updated **2026-08-30**;
**34 pull requests have merged since**, phase 2 entire, and none of them needed a change to it.
That is the `claims-complete` design working — a new claim target is covered on the day it is
written, by nobody remembering anything — and `claim-5` on 2026-09-04 is the case that proves it.

The standing limit is unchanged and cannot be closed from inside: **nothing in this tree checks the
ruleset.**

---

## 11 · The question `T011` routed here, answered by measurement

`docs/FINDINGS.md`, *The run is at its concurrency ceiling*:

> *Three tasks each want an engine job and all three want the same installation: silver has one,
> gold took a second, `pipelines/ml` will ask for a third — three slots for one dependency set. One
> job for every engine test would cost one slot instead of three. … it is to be answered by
> **measuring** what a combined job costs, not by projecting it.*

**The premise is false today, and two atoms that landed after it asked are why.**

**`pipelines/ml` asked for nothing.** `T014`'s tests carry no mark and need no engine; they run
inside `gate`'s `make check`, which passed here with neither extra installed.

**`silver` and `gold` hold no slots.** `T00M`'s packing put them in bins with claim targets. The
run is 17 jobs against a documented ceiling of 20:

```
python3 -m ops.ci_pack …  →  claim-5 gate-proof · claim-1 · claim-2-tests gold ·
                             claim-3 silver claim-4 · claim-7
```

**What an engine install actually costs**, from the GitHub API, step-level, four runs:

```
run          spark (claim-3 silver claim-4)   dbt (claim-2-tests gold)   dbt (claim-5 gate-proof)
33870971308            17s                              38s                       76s
33862276220            21s                              18s                       15s
33868753796            19s                              13s                       54s
33856881017            16s                              23s                       18s
```

54–131 s of runner time per run, spread over three jobs that run in parallel, against a critical
path of 736 s and 751 s on the two most recent `main` runs.

**So the combined job is refused by the measurement, in both directions.** It would save at most
~2 minutes of runner time and no wall clock, and it would cost wall clock: `silver` + `gold` +
`claim-5` is 165 + 225 + 750 = **1,140 s of declared cost against `CI_ENTRY_CEILING := 1032`**, and
~400 s above the critical path. The slot count does not move, because no engine target holds a slot.

**The limit of this answer**: four runs, all on `ubuntu-latest`, all with warm world caches; the
install figures are Linux and the extras' sizes in `pyproject.toml` are macOS. The conclusion rests
on the ratio (install ≤ 10% of its own job), which is robust to that spread; the point estimates
are not.

*Disposition:* the finding's structural question is answered here; the ceiling question underneath
it stays with the author, where `T011` left it.

---

## 12 · One open pull request, read hostilely because it was offered

`#59`, `ops/terraform-population`, at `f7dc6d4` — two defects found by review on `T013`'s merged
work, one fixed. The fix is right and the loop is now enumerated from the tree. Its run finished
while this was being written — seventeen contexts, all green, including all three the ruleset
requires.

**One thing in it should not merge as written.** The diff removes this clause:

```
-# ... a layer that exists and is never validated is the
-# coverage rule's own failure, and `make figures` compares this count against the tree.
```

and the replacement says *"the sentence above is the prior wording kept per doctrine rule 4."* The
sentence above is a rewrite, and the half that disappeared is the load-bearing one: **`make
figures` does not compare that count against anything.** `ops/figures.py` contains neither
`terraform` nor `infra` — there is no such row, and `make figures`'s eleven rows do not include one.

So a branch whose subject is a gate that reported on what it examined as though that were what
exists has **deleted an assertion about a check nobody wrote, rather than restating it.** Whether
`make figures` should gain a `terraform` row is a real question with a real answer either way — the
new target now enumerates its own population and refuses a non-layer by name, which is a decent
argument that a second enumeration would be one enumeration wearing two names. Either answer is
fine. Deleting the sentence is not.

> **Added after this section was written, and it is the better half of the finding.**
> `projects-d1` read the diff rather than this account of it and named a second defect: the
> replacement says *"the sentence above is the prior wording kept per doctrine rule 4"* **when the
> sentence above is a rewrite.** Not kept. **A rule-4 label on a sentence that was not preserved is
> worse than no label**, because it tells the next reader the original is there to compare against
> and it is not. Which makes the first defect sharper too: the target's own comment claimed a
> `figures` row that has never existed — **the branch's own subject, in the branch, uncounted.**
>
> Recorded here rather than folded in silently, for the same reason `docs/reviews/phase-1.md` §2d
> is dated and attributed: **this section reported one defect and there were two, and the second
> was found by somebody who was not me.**

*Disposition:* `projects-d1`, who owns the branch — it was rebased by that session after the one
that wrote it did not survive a restart — and who has said it does not merge as it stands. **Not a
wording call**, which is what this section said before the paragraph above was added.

> **Closed 2026-09-05, and this section is now history rather than a state.** `#59` merged as
> `e113ff9` with both defects fixed. The original sentence is back **verbatim** as the first three
> lines of the comment, and the restatement under it names both corrections — that the earlier
> version *"rewrote that sentence, deleted its last clause, and then labelled the rewrite as prior
> wording"*, and that *"the deleted clause was itself a claim about a check nobody wrote.
> `ops/figures.py` contains no occurrence of `terraform` or `infra` — there is no such row among
> its eleven, and there never was."*
>
> **Left as written above rather than rewritten**, for the reason the closing table carries: a
> review's sections are what the method produced before anyone knew which of them survived, and a
> present-tense section in a historical document reads as current only when nothing says it is
> not. This says it.

---

## 13 · The corpus barrier's runtime half knows one of the two spellings its source half declares

Its own section, because it is the one attack that survived and the only finding here that
touches whether a claim is true.

`ops/isolation.py` declares both spellings and says why:

```python
FORBIDDEN_ROOTS = (FORBIDDEN, f"src.{FORBIDDEN}")   # "A barrier that misses the spelling its
                                                    #  own task description used is not a barrier."
```

The runtime half — `test_every_corpus_module_imports_with_the_system_absent`, the test written to
close the dynamic hole reading cannot see — passes one:

```python
block_imports(FORBIDDEN, evict=(POLICED,))
```

Measured:

```
_Refuse(("holdout",))._blocks("holdout.core.money")       True
_Refuse(("holdout",))._blocks("src.holdout.core.money")   False

with that finder installed, exactly as the test installs it:
  importlib.import_module("holdout.core.money")      ModuleNotFoundError: blocked for this test
  importlib.import_module("src.holdout.core.money")  <class 'src.holdout.core.money.Money'>
```

So a **module-level** `importlib.import_module("src.holdout…")` in a corpus module is invisible to
both halves of the barrier: to `offences`, because there is no `Import` node, and to the runtime
test, because the finder was never told the second spelling.

**And the prose says otherwise.** `tests/boundary/conftest.py`:

> *`tests/boundary/test_blocking.py` plants **both spellings** against this fixture and requires
> each to raise.*

`src.holdout` occurs nowhere in `test_blocking.py`. All six of its tests block and plant
`holdout`. This is the file that exists **because** the previous technique's prose looked right,
and it carries the same defect one layer along.

**What this is not.** It is not the declared hole. `.claude/README.md` and the boundary test both
state that a dynamic import is invisible to the source scan, and the runtime test closes the
module-level half deliberately. What is undeclared is that it closes it for one spelling out of
two, in a repository whose own history records the first spelling costing a barrier.

**Not planted in `corpus/`**, and that is the one step not taken: the two halves were measured
directly rather than by writing a file into a shared checkout other sessions are working in. Each
half is a direct measurement; the composite is inference from them.

*Branch:* `ops/the-barrier-blocks-both-spellings` — and the fix is `block_imports(*FORBIDDEN_ROOTS)`
with `test_blocking.py` planting the second spelling, which is what its own conftest already claims.

---

## 14 · One more, in the layer that costs money

`infra/lakehouse/dashboards.tf`:

```hcl
variable "warehouse_id" {
  description = <<-EOT
    ... declared with no default so that a layer applying these resources has to say which
    warehouse rather than inheriting one somebody typed here.
  EOT
  type        = string
  default     = "" # validate-only: T020 supplies the real one
}
```

**The description asserts the absence of the thing declared two lines below it**, and the default is
exactly what removes the protection the description claims: a `terraform apply` that forgets
`warehouse_id` will not stop, it will bind two dashboards to warehouse `""`.

**The stated reason does not hold.** Measured, on a copy of the layer with the default removed:

```
terraform init -backend=false && terraform validate   →   Success! The configuration is valid.
```

`terraform validate` does not need it. The fix is to delete the default, and the description
becomes true.

This is in the first layer of the estate, in the phase whose whole cost is that mistakes there are
paid for in dollars and in forty-minute applies. It is why it is on the list rather than in a note.

---

## 15 · The three findings routed to this session, and they are one finding

`docs/FINDINGS.md` routes three entries to `T016` by name. Read together and measured against
`TASKS.md`, they are not three questions. They are one, and it is the largest thing in this report.

**Each was filed by the atom that found it, and each was correct to say it was not theirs.**

| filed by | the half it named |
|---|---|
| `T013` | *The single most important screenshot in the project has no data source* — `gold.readout` is read by the compiled dashboard and written by nothing |
| `T014` | *the adapter between the model and the decision path has no owner* — and, on this corpus at every declared scale, one discount level per `(hours, arm)` |
| the reviewer | *The explained-collision pair key degrades to the bare identifier* — a design question, deliberately unfixed |

### What is measured, not inferred

```
Scenario(...) is constructed in     tests/core/test_pricing.py, tests/core/test_composition.py
                                    and nowhere else in the repository
holdout.core.experiment.close() is  evals/assignment/checks.py:852, evals/uplift/harness.py:387
called from                         and nowhere else. holdout.core.experiment.readout is
                                    imported by no module under pipelines/ — gold imports
                                    assignment and codes, and neither reaches close
gold.readout is written by          nothing; generated/dashboards/experiment_readout.lvdash.json
                                    reads `from gold.readout` at line 110
the decision path is composed in    tests/core/test_composition.py and evals/guardrail/build.py;
                                    there is no pipelines/ module that takes a trigger and
                                    produces a certified price or a decision record
```

**So three joins on the path `PLAN.md`'s `run` describes have no implementation**: model → scenario
table, decision path → a decision, readout → `gold.readout`. Every piece on either side of each one
exists, is tested, and is proved local. What does not exist is the wire.

### And no task owns any of them

`TASKS.md`'s phase 3 is `T017` bootstrap, `T018` foundation, `T019` (closed, not built), `T020`
lakehouse, `T021` pipelines, `T022` ml, `T023` the five workflows plus serving, `T024` this review's
successor. **Six infrastructure layers, five workflows, and a review.** Phase 4 is the agent and
claim 6. No `closes` in the file names a scenario producer, a decision-path driver or a readout
writer.

`T023`'s `closes` requires the **output** of two of them:

> *A run whose every figure is asserted by a step that fails when it is not true — at least one
> experiment producing a number and at least one refusing for the right reason.*

**A gap with no owner is the one kind that survives every atom, because every atom can correctly
say it is not theirs.** `T013`'s entry says exactly that about itself, one half at a time. What
nobody did — and what this session exists for — is put the halves beside the task registry and ask
which atom owns the wire. The answer is none, and it has been none since the registry was written.

### What this does and does not mean

**It does not mean a claim is untrue.** Claims 1–5 and 7 are proved local and every one is green;
none of them asserts that the system runs end to end. `CLAUDE.md` is careful about this and always
has been — *claim 4 today is a proof that the arithmetic and the refusals are right, not a proof
that the system uses them* is the same sentence, written a fortnight ago about a different module.

**It does mean phase 3's closing condition is not reachable by phase 3's task list**, and that this
is knowable now, for nothing, rather than after `deploy` and `backfill` have applied five layers.

**And it means the demonstration would be a different one than the project describes.** `T014`
measured that this corpus offers one discount level per `(hours, arm)` at every declared scale, so
`run` exercises the deterministic ladder and never the model path. A coherent, honest system doing
exactly what doctrine rule 1 says — and not the system on the shot list, whose rows for claims 1
and 2 are *the decision monitor, the guardrails that fired* and *the readout showing a REFUSAL*.

### The disposition, which is not this session's to take

**Three tasks, or one paragraph.** Either the joins become atoms with ids, sized and placed before
`T021` — because a pipeline layer that deploys jobs should know what job writes the readout — or
phase 3's scope is restated to what it can actually demonstrate, and the shot list moves with it.
**Both are the author's**, because both change what the project shows rather than how it is built,
and one of them changes what `T023` closes.

**What this session can say is that the choice cannot be deferred past `T018`.** `T017` spends
almost nothing and depends on none of this; `T020` and `T021` apply layers whose contents depend on
which answer is taken.

### The third entry, disposed of separately because it is genuinely separate

`EXPLAINED`'s key is a pair, and for a same-name collision the pair **is** the bare identifier.
Re-measured today, after `height` was added:

```
12 entries · 5 same-name (agent · candidate · height · members · parents) · 7 differing
```

The finding predicted `height` would be the fifth and it is. **The pair protects seven entries and
protects nothing on five**, and the ratio is getting worse rather than better.

**No fix is proposed and the finding's own reason is why**: an explanation keyed to a module, a
type or a line goes stale on a move or an edit, and the pair was chosen because it is stable. What
is available for nothing is to **publish the split** — `O12` already re-checks every explanation,
and printing *5 of 12 explanations are same-name and pre-approve any future collision on that
name* costs one line and makes the partiality visible on every run instead of in a register.
That is smaller than a fix and it is the shape this repository uses everywhere else: publish the
number that argues against you.

*Disposition:* the two joins go to the author, in the words above. The `EXPLAINED` split is a
branch: `evals/the-explanation-publishes-what-it-does-not-cover`.

> **Answered 2026-09-05, and it went the way that costs more.** Relayed by `projects-d1`, which
> put it to the author as the question underneath the two options rather than as the options —
> *does the corpus gain price randomisation* — on the grounds that `CLAUDE.md` declares it as
> design, in bold, with its reason, and a corpus without it models a system nobody designed.
>
> **He chose it.** So `T023` is **not** restated: two of the three joins become **phase-2** atoms
> and the third becomes buildable once the corpus changes, with the corpus work batched against
> the sub-cent finding — in phase 2, before any money.
>
> **That changes this report's closing answer and the closing answer is left as written.** It says
> *phase 2 closes*; phase 2 now has two atoms it did not have when the sentence was written. The
> sentence was true of the tree it was written against and is superseded rather than wrong, which
> is the distinction doctrine rule 4 exists for.
>
> **Recorded as relayed, and deliberately not recorded as closed.** This session did not hear the
> ruling; it heard a session that heard it. The register's own line is that two agents agreeing is
> two representations agreeing — so the finding in `docs/FINDINGS.md` stays **open**, and what
> closes it is the atoms existing with ids, written by whoever writes them. **Not by this review**,
> whose `out_of_scope` is building any product code and whose scoping of somebody else's work
> would be the review deciding the thing it exists to put in front of him.

---

## Verified correct

What was actually checked and held, so this report's coverage is known and not only its complaints.

- **Claim 2 at `harness`, run rather than inherited**: 13/13, A/A 8/200 = 4.0% against α = 5% at a
  one-sided binomial p = 0.7867, coverage 163/170 = 95.9%, W6 false-refusal 0/200, U10 0 of 15,360
  cells disagreeing.
- **The roster table** in `CLAUDE.md`, both scales, all four rows, exact.
- **Claim 4's restated figures** in `CLAUDE.md`: 80,640 store-days, 21.0%, −6.0% and −91.4%. All
  exact. And `C2`: 0 of 176,266 censored corrections returned zero demand.
- **Doctrine rule 1's restatement**: 716 of 26,600 and 6,650 of 26,600, exact.
- **Claim 7's other half**: 35 of 317, exact.
- **`make contracts` bites on a hand-edited consumer**: a rounding change planted in
  `generated/dashboards/experiment_readout.lvdash.json` was refused as `stale_artefact` by name.
- **The corpus barrier's source scan** attacked with eleven shapes. It refuses `import holdout`,
  `from src.holdout…`, `from src import holdout` and aliased submodules; it passes
  `importlib.import_module`, `__import__`, `exec`, `runpy` and `sys.modules` — **and that hole is
  declared** in `.claude/README.md` and in the boundary test's own docstring, with the module-level
  half closed by a `sys.meta_path` finder. Section 13 is what is left after that.
- **The hooks** are wired in `.claude/settings.json` for `Write|Edit|MultiEdit` and `Bash`, and
  `tests/hooks/test_settings.py` checks the wiring, that each command runs, and that it runs
  without the project's virtualenv.
- **The sealed `correct_behaviour` strings** in `corpus/world/worlds.py` match `CLAUDE.md`'s
  restated six-worlds table, W2 and W3 and W4 included.
- **`pipelines/gold/`'s absent families** are named with reasons rather than built empty, and
  `tests/pipelines/test_gold.py` asserts that nothing under `pipelines/` duplicates a path under
  `generated/`.
- **`silver`'s dedup** is on `("transaction_id", "line_no")`, with an expectation refusing a line
  with no transaction id and quoting the doctrine rule that refuses to invent one.
- **The repository is public** (`visibility: public`), which is what `CLAUDE.md` asserts.
- **`TASKS.md`'s closed registry** is current through `L27` / `T013`, which is `main`'s head.

---

## Proposed branches, in order

> **This table records what was proposed on 2026-09-05 and is not updated.** Phase 1's table
> carries the same note and the reason: rewriting rows to match what has since landed would
> overwrite history, and destroy the record of what the method produced before anyone knew which
> rows survived. Present-tense status lives in `TASKS.md` and `docs/FINDINGS.md`.

| # | branch | what it closes |
|---|---|---|
| 1 | `ops/the-barrier-blocks-both-spellings` | §13 — an independence barrier, one spelling short, with prose saying otherwise |
| 2 | `evals/claim-5-counts-what-it-found` | §1a, §3d — the cap of five, the hard-coded constructed cell, `D5` |
| 3 | `evals/claim-5-arms-the-sql-mechanism` | §1b — a mutation on the mechanism the eval calls load-bearing |
| 4 | `ops/a-closure-is-read-however-it-is-written` | §2b — four closures the gate cannot see |
| 5 | `ops/the-floor-is-what-exists` | §2a — `FLOOR=8` against nine, and the check that runs the other way |
| 6 | `docs/the-condition-that-fired-at-T011` | §7 — claim 7's population, and the pointer that named the wrong task |
| 7 | `evals/the-printed-disclaimer-is-re-read` | §3c — two notes printed on every claim-2 run |
| 8 | `pipelines/each-package-says-what-it-serves` | §4 — silver, gold and ml |
| 9 | `contracts/the-count-matches-the-list` | §3b — four consumers, five bullets |
| 10 | `ops/language-asks-git-too` | §2c — the hand-kept population, fourth instance |
| 11 | `infra/the-warehouse-has-no-default` | §14 — a default that contradicts its own description, in the layer that costs money |
| 12 | `evals/the-explanation-publishes-what-it-does-not-cover` | §15 — 5 of 12 explanations pre-approve any future collision on the name |

**Row 1 is first because it is the only one that touches whether a claim is true**, and rows 2 and 3
follow because they touch what a claim publishes. The rest are documents and instruments.

### And the twelve exhaust the ops id scheme, which is a consequence of this review rather than a finding about the tree

`TASKS.md`'s schema declares ops ids as *"`T000`, `T00A`, `T00B`, `T00C`"*. Measured against the
file after these twelve land:

```
26 ops ids in use   T000 · T00A–T00N · T00P–T00Z
letters used        25 of 26 — the only free one is O
```

**And the free one is the one nobody should take.** `T00O` beside `T000` is a letter that reads as
the digit next to it, which is why it was skipped here rather than used.

**The file already contains that hazard once**, and nobody has recorded it: `T00I` and `T001` both
exist today. So the skip was a judgment applied on one letter and not the other, by different
sessions, with nothing written down either time — which is what makes this worth one paragraph
rather than none.

**Not a defect and not routed anywhere.** The two joins and the corpus work `§15` produced are
**product** atoms in phase 2, where the file's precedent for an insertion is `T002B` and the ops
alphabet does not apply. What has no answer is the *next ops atom*, and the scheme is one line in
a schema the author owns. It is named here because it became true in this review's own diff, and a
scheme that runs out inside the change that fills it is the kind of thing nobody goes looking for.

---

## What this report does not cover

- **`make preview-audit`**, because it does not exist and its remaining unlock is the author's.
- **Anything about the estate.** No layer has been applied, no bill exists, and every figure here
  was produced with no cloud account.
- **Whether the eight questions are the right eight.** This is the second sample. §5 produced no
  finding for the second time and is kept for the reason phase 1 kept it.
- **The ruleset itself**, which nothing in this tree can check (§10).
- **`corpus/world/`'s generated data**, which was read through the evals that consume it and not
  audited on its own.
- **`docs/DAY-ONE.md`**, read for its phase-3 assertions and not line-checked against the vendor;
  its own six declared holes are unchanged.

---

## Is phase 2 ready to close, and may `T017` open?

**Phase 2 closes. `T017` may open. `T023` cannot close as written, and that is the sentence the
author needs before a layer is applied rather than after.**

**Phase 2 closes.** Every claim target is green, both independence barriers hold in the direction
they were built for, the seven phase-2 atoms — `T009` to `T015` — delivered what their `closes` named, and nothing on the
list above makes a claim untrue. The corrections are corrections.

**`T017` may open.** The bootstrap is a state bucket, a KMS key, an OIDC provider, a deploy role
and a budget posture. It depends on none of the findings here, it spends almost nothing, and every
later layer depends on it. Blocking it would buy nothing.

**Two rows should land before the estate starts producing evidence, and neither blocks the
bootstrap.** Row 1, `ops/the-barrier-blocks-both-spellings`, because claim 2's whole answer to
*your simulator is rigged* is that the generator cannot see the estimator, and today that is
enforced for one of the two spellings that reach it — a small fix with a test that fails on the
un-fixed version. Row 11, `infra/the-warehouse-has-no-default`, because `T017` is the next thing to
touch `infra/` and a default that contradicts its own description is cheapest to remove before a
second layer copies the pattern.

**What is not ready is `T023`.** Its `closes` requires *at least one experiment producing a number
and at least one refusing for the right reason*, and §15 measures that nothing in this repository
writes a readout row, converts a model into a scenario table, or drives the decision path outside a
test. Three joins, no task, and the closing condition of phase 3 sits on top of two of them.

**The decision is the author's and it is one decision.** Either the three joins become atoms with
ids, sized and placed before `T021` — a pipeline layer that deploys jobs ought to know which job
writes the readout — or phase 3's scope is restated to the demonstration this corpus and this code
can actually give, and the shot list moves with it. It does not have to be taken today. It has to
be taken before `T018`, because `T020` and `T021` apply layers whose contents depend on the answer.

**What this session did not do**, so the coverage is not overstated: it built nothing, it took no
decision reserved to the author, it merged nothing, and the one attack it could not complete — a
planted file under `corpus/` — is named in §13 rather than counted as run.
