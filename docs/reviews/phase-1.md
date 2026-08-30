# Phase 1 — integration review (oversight level 3)

**T008 · 2026-08-30 · branch `docs/phase-1-integration`**

Oversight level 3 reads the whole repository against `CLAUDE.md` and reports conceptual drift.
**It builds nothing.** Each proposed fix becomes its own branch with its own review.

What was run to produce this report: `make check` (919 green), `make eval-guardrail`,
`make eval-assignment`, `make eval-censoring`, `make eval-oversight`, `make gate-proof`,
`python -m ops.roster` at two scales, and the durations of the 31 successful `claim-2` jobs
from the GitHub Actions API.

> **This report existed only in a terminal until it was written here.** That is the same defect
> it catalogues nine times over: an assertion with no place anybody but its author reads. Its
> place is the repository.

*Written in Greek in the session that produced it and translated on 2026-08-30 by
`docs/review-in-english`, because `CLAUDE.md`'s first line is that all repository content is in
English and only the conversation with the author is in Greek. Nothing in the content moved;
`make language` is what stops it happening again.*

---

## 0 · What stands

I found no claim whose proof has collapsed. The five closed claims are green and both
independence barriers hold: no module under `corpus/` sees `holdout`, no mutation touches `ops/`
or `corpus/`, and `ops.roster` reproduces exactly the table `CLAUDE.md` restated on 2026-08-29
(83·16 / 66·13 / 269·53 / 222·44). The `at_decision` codes are covered 12/12. The drift I found
is **in the casing around the proof, not in its core**.

---

## 1 · Does any claim's proof rest on something that has become a tautology?

**No — but 21 of the 57 checks own no mutation, and 8 of those name no reason either.**

Measured by matching the `targets:` of the 49 mutations against every check id:

```
claim 2   U1 aa-false-positive-rate      0 mutations
          U2 aa-p-values-are-uniform     0
          U3 w6-false-refusal-rate       0
          U5 w6-estimator-bias           0
          U9 w5-power-or-width           0
claim 1   G4, G6, G7, G8                 0
claim 4   C5, C7, C9, C11, C12           0
claim 3   A10                            0
claim 7   O4, O6, O7, O8, O11, O12       0
```

**Three of the four numbers claim 2 publishes — U1, U3, U5 — have no mutation.** Only U4
(coverage) does. The claim `CLAUDE.md` calls *the one that separates this from a demo* shows its
headline numbers without having shown that they bite.

For U1·U2·U3 the reason **does exist** — in the docstring of `evals/uplift/machinery.py`: they
are rate-shaped and are absent from the configuration a mutation runs. A10, C7/C11/C12 and the
six O checks also have a written reason. For **C9, G4, G6, G7, G8, U5, U9** there is none
anywhere — and two of those (`G8.every-refusal-code-is-reached`,
`C9.every-censoring-shape-is-reached`) are precisely the coverage checks that rule 4 of
`evals/README.md` says exist so that a gate is not forgotten in a footnote.

The rule that requires it — *"a check with no mutation names the reason it cannot have one, and
is broken deliberately somewhere"* — was written on **2026-08-29 by claim 7** and entered
`evals/README.md` as part of the shape. **It was never applied backwards.** It is a rule with one
conforming sample, in the file that declares itself the source of truth for the shape of every
claim.

**And 7 of the 24 closed codes are reached by no eval.** The whole of `at_design` —
`UNDERPOWERED_FOR_DURATION`, `UNDERPOWERED_FOR_CAPACITY`, `UNIT_GUARANTEES_INTERFERENCE`,
`STOPPING_RULE_PERMITS_PEEKING`, `EXCLUSIONS_DEFINED_POST_HOC`, `METRIC_NOT_IN_CONTRACT`,
`UNITS_ALREADY_COMMITTED` — exists only in `tests/core/test_refusal_codes.py`, that is, in cases
their own author wrote. `evals/design/` is phase 4. That is correctly deferred; **it is written
down nowhere**, and claim 6 is about to count N/M/K over exactly this vocabulary.

*Branch:* `evals/unarmed-checks` — for every check with no mutation, either a mutation or a line
saying why it cannot have one, and a statement of the `at_design` gap.

---

## 2 · Has any gate stopped biting?

### 2a · `make expiry` counts closed deferrals as open

```
35 deferred item(s): 5 carry a date, 30 carry an unlock condition only
next expiry 2026-09-30
```

`ops/expiry.py` reads **headers** (`_ENTRY`, `_MARKER`). It has no notion of closure. Three
entries carry an explicit `> **Closed**` / `> **Half closed**` and are counted regardless:

- *The contamination check cannot see a store erased* — closed 2026-08-29
- *`docs/SCENARIO.md` and `docs/DAY-ONE.md`* — half closed 2026-08-30
- *CI's gate job runs on a temporary 25-minute timeout* — **closed 2026-08-28**

And the third is the problem: **`next expiry 2026-09-30` points at an entry that closed two days
ago.** The only dated entry that ever armed the dated half of the gate — the one the registry
itself celebrates as *"This is the first entry that arms it"* — is closed. On 2026-09-30 CI will
go red for a finding that has already returned.

The deeper point: **"how many deferrals are open" has no answer that any command gives.** That is
exactly the defect `TASKS.md` declares on its first page that it exists to prevent — "two answers
to what is still open" — reproduced one file along.

*Branch:* `ops/expiry-knows-what-closed` — a closure marker the parser reads, with a planted entry
in `tests/ops/test_expiry.py` in both directions.

### 2b · CI's world cache saves nothing measurable

31 successful `claim-2` jobs:

```
min 32.2   median 51.4   max 77.1 minutes      (2.4x spread)
```

**The two fastest runs of all (32.2 and 32.7) are cache misses.** Run 33253331218 logged *Cache
not found* and finished in 44.8; run 33279086093 hit `worlds-Linux-1acc1402…` (6 MB restored) and
took 50.5. The mean of the warm runs is **above** the mean of the cold ones. There is no
measurement supporting *"about half the harness"* — and three places assert it:

- `.github/workflows/ci.yml:143-145` — *"The steady state is much lower… skips generation
  entirely"*
- `docs/DECISIONS.md:1291` — *"which is about half the harness"*
- `evals/README.md:132` — *"much lower once `.worlds/` is warm"* — and this one sits **inside the
  paragraph that has just declared every figure above it a cold measurement rather than a
  projection.**

**And the key over-covers.** `DEPENDS_ON = ("corpus", …)` scans all of `corpus/`, so it includes
`corpus/real/__init__.py`, `fetch.py` and `reader.py` — the files of claim 1's and claim 7's
corpus, which produce not one byte of a world. Verified: the digest moved `ad6b6e27 → 1acc1402`
with the merge of **T006 (claim 7)**, and all 40 harness-scale ledgers of 540 KB were invalidated
by a change that could not touch a world. `cache.py`'s own docstring warns explicitly about the
opposite way to make a cache useless (*"A digest over the whole repository would move on every
mutation… which is the other way to make a cache useless"*) — and the key has it, one directory
in.

### 2c · The 90-minute budget

Maximum measured **77.1 minutes — 86% of the budget**, two runs above 76. The same shape that has
cost twice already (15→25, 45→90), with the difference that this time the number was set from a
cold measurement and was right; what was not measured is the **spread between runners under
contention**, which is 2.4x rather than the ~40% this repository has recorded.

The deferral says: *"Unlock condition: the first CI run with a warm world cache, which is the
steady state this number should be set from."* That condition **has been satisfied 21 times since
2026-08-29 01:47** and nobody noticed. It is the first time in the registry that an unlock
condition was met silently — that is, the declared limit of `make expiry` (*"checks that an unlock
condition is present, never that it is right"*) biting for the first time.

*Branch:* `evals/world-cache-measured` — `DEPENDS_ON` narrowed to `corpus/world` plus the two
modules, a restatement of the deferral with the 31 runs, and a budget from the new measurement.

### 2d · The ruleset required `gate`, and the claims had left it

*Added 2026-08-30, by the author, **after** this report was merged. The review did not find it,
and the cause is the finding itself.*

The `main` ruleset required two contexts: **`gate` and `secrets`**. The claim targets ran inside
`gate` until T003, which moved them — correctly — into the `claims` matrix. **The ruleset stayed
pointing at `gate`.** From that commit until today, **a pull request with a red `claim-2`
merged.**

This is not a gate that stopped biting. It is **oversight level 1** — `CLAUDE.md`'s line *"a
session cannot merge something that breaks a claim, because the gate is structural rather than
advisory"* — false for two days, at the level everything else leans on.

**Why the review missed it, and why no review will catch it by reading.** What the ruleset
requires is a **fact about the forge, not about this tree**. No file carries it: `ci.yml` declares
which jobs *exist* and never which are *required*, `make check` cannot see it, no test touches it.
§2 of this report read `ci.yml` line by line and measured 31 of its runs; the missing question was
answered by nothing in there. It was found by asking the API.

**And its fingerprint had been sitting in the registry since 2026-08-27.** The deferral *Branch
protection covers `main` only* quotes its own verification: *"2 of 2 required status checks are
expected"*. The **2** was the finding. Nobody read the number, because the sentence beside it
already said which two and they agreed. It is exactly the shape §8 names: the assertion checked
against the sentence it came from.

**The fix, and why it is not a list of names.** A `claims-complete` job with `needs: [claims]` and
`if: always()` fails on anything that is not `success` — and the case that matters is
**`skipped`**, because skipping is how a matrix job passes silently: a skipped required check
reports as neutral rather than red. The ruleset requires **that one context** and never the claim
names: an enumeration there would be a second registry of which claims exist, kept by hand, in a
place no session reads — and the day `claim-5` lands somebody would have to remember it.
`discover` already reads the targets out of the `Makefile`.

**Verified by attacking, not by reading**, the way claim 1's gates are — and it took **three**
attacks, because the first two did not prove what they looked like proving:

| | attack | matrix | `claims-complete` | `gate` | merge |
|---|---|---|---|---|---|
| **A** | every `claim-N:` hidden from `discover` | `skipping` | fail in 2s | *also red* | `BLOCKED` |
| **B** | a `DecisionKey` that learns who is buying (claim 7's planted break 01) | `failure` | fail | *also red* | `BLOCKED` |
| **C** | the margin cap's bound carries another rule's name | `failure` | fail | **green, 919** | `BLOCKED` |

**The `gate` column is why C exists.** A and B were already caught by the suite —
`tests/evals/test_ledger.py` parses the real `Makefile`, so renamed targets turn it red, and the
`DecisionKey` has a test of its own. They showed the job fires on both values of `result`, and
that the ruleset refuses; **they did not show the context is necessary**, which is exactly the
rule this repository applies to its own gates: *a gate can only be shown to bite where it is the
gate that refuses.* On A the `gate` column was empty because `concurrency` had cancelled it — and
the empty column was the finding.

**And no committed mutation can serve as the isolated attack.** Number 16 was tried and `gate`
went red: `ledger.every-anchor-is-aimed-at-one-place` requires each anchor to occur exactly once,
and applying the mutation removes it. The repository defending itself correctly; the consequence
is that the isolated attack had to be written from scratch.

**C is that one.** `cap_benchmark`'s bound is attributed to `markdown_max_depth_pct`: right
amount, wrong rule name — that is, a certificate asserting a check that never ran. `make check`
**green at 919**; `G10` red with **156,294 disagreements in 746,643 bounds**. It is the break
`G10` was written for, and now also the one `claims-complete` exists for: **before this branch,
that exact tree would have merged.**

The refusal names itself, and the three wordings are themselves the evidence that the ruleset
moved — the last one names a single context:

```
A   2 of 3 required status checks have not succeeded: 1 failing.   (HTTP 405)
B   2 of 3 required status checks are failing.                     (HTTP 405)
C   Required status check "claims-complete" is failing.            (HTTP 405)
```

**What this does not catch: the ruleset itself.** If the required context is removed tomorrow, the
job goes on reporting and nothing turns red — the same hole one layer out. There is no way to
close it from inside, because anything living in this tree can only be checked by something that
runs after the forge has already decided to run it. So it closes as a **question in a procedure**:
*"what does the ruleset require, and does it match the jobs that exist today?"* goes explicitly
into the `integration-review` skill when it is written, and is in T008's `closes` so that it is
not a sentence in a conversation.

*Branch:* `ops/claims-are-required` — done.

---

## 3 · Does the code still say what `CLAUDE.md` says it says?

### 3a · The repository map omits two packages — and one is exactly the blind spot that cost claim 7

`CLAUDE.md`'s `Repository layout` lists `core/{guardrails,pricing,design,experiment,ladder}` and
`adapters/`. Missing:

- `src/holdout/core/demand/` — claim 4
- `src/holdout/contracts/` — **fifteen modules**, an 820-line loader and the compilers

The second is the same blind spot that produced a blocking finding in T006's oversight level 2:
`reference.CORE` stopped at `core/`'s boundary, so a `customer` parameter on `compile_agent_tool`
was outside the scan. The eval was fixed (820 → 1,181 identifiers). **The map in the file every
session reads first was not.** `ops/` is likewise described without `roster.py`.

### 3b · Claim 4 is 12/12, not 11/11

The eval prints `green 12/12 checks` and `evals/censoring/README.md` lists C1…C12. The `11/11`
survives in five places: `PLAN.md:42`, `PLAN.md:737`, `TASKS.md:802`, `TASKS.md:1422` (L9),
`TASKS.md:1457`. `C12` arrived in the **same commit** that closed the claim (`86fe136`), so the
published number never agreed with the eval — and it passed oversight level 2.

### 3c · Two restatement chains stopped at `CLAUDE.md`

`CLAUDE.md` withdrew two things on 2026-08-29. Neither withdrawal reached anywhere else:

| withdrawn | still live |
|---|---|
| *"1,200 leave a roster of 212" — projection, never a measurement* | `docs/DECISIONS.md:380`, `corpus/world/README.md:100` — both as measurement |
| *"about 36M POS lines" / "a cost decision and nothing else" / "does not get stronger with 1,200 stores"* | `docs/DECISIONS.md:14-19` — the Scope entry, **with no restatement underneath** |

The second is the worse one, because `docs/DECISIONS.md` opens with its own sentence: *"Where a
decision has been reversed, the original stays and the reversal is written underneath it."* The
one reversed decision in the file does not have its reversal underneath it.

### 3d · T008's own task note names the wrong function for `floor.yaml`

`TASKS.md:1069-1074` instructs the session: *"the core's `Bound.rule_id` strings are written down
a second time in `evals/guardrail/reference.py`… A rename turns G10 red on both directions at
once; move the two in one change."*

`refuse_when_no_legal_price_sells` is **never a `Bound.rule_id`.** `envelope.py` attributes six
rule ids and it is not among them — it is a boolean field on `FloorRule`, a predicate with no
edge. `reference.py` does not model it. **The rename does not turn `G10` red.** What actually
moves is `envelope.py`, `evals/guardrail/build.py:213`, `tests/core/conftest.py` ×2 and the
registry at `ops/personhood.py:186` — and the last of those means **`O2` will go red**, correctly,
as a change to the system the registry has not been told about.

> **And the author acknowledges it as his own mistake, which makes this line the tenth form of the
> rule rather than merely an inaccuracy.** The note was written by the same person who wrote `G10`
> and the independence `G10` carries, and it was written **against `G10`'s argument** — *the six
> strings are written down a second time, so a rename separates them* — rather than against the
> list of six. It is exactly the same shape as the nine before it: the assertion checked against
> the artefact it came from rather than against the thing that would falsify it. The nine prior
> forms were a sentence, `timeout-minutes`, a deferral, a cost estimate, a measurement that went
> stale, a minuted figure, a cache hypothesis, and the rule's own statement. **The tenth is an
> instruction to the next session** — that is, the form with the longest reach of all, because it
> does not describe the system: it aims the hand that will change it. No gate found it; it was
> found by reading the six `rule_id=` lines in `envelope.py`.

### 3e · Smaller, all verified

- `CLAUDE.md`, *How claim 2 is proved*: *"a deliberately slow reference implementation… while the
  production path is SQL through dbt. Two genuinely different implementations must agree."* `U10`
  compares **two Python paths inside `evals/uplift/`**. dbt is phase 2. It is the only one of the
  paragraph's five artefacts that does not exist, stated in the present tense.
- `docs/REGULATORY.md:398`: *"Every `verified_on` in this repository reads 2026-08-27."* — 66 read
  2026-08-27 and **15 read 2026-08-28**.
- `CLAUDE.md`, the skills table: presents four skills as living "in this repository". There is
  **one** (`claim`). `.claude/README.md` says so correctly. And `contract-change` **has no task id
  anywhere in `TASKS.md`** — it is not deferred, it is forgotten, in the doctrine's own words.
- `TASKS.md`, *Closed — the atoms that have landed*, declared as "the complete registry": stops at
  **L9 (T005)**. Missing are **T004 (claim 3), T006 (claim 7), T007 (SCENARIO.md)** — three of the
  last four. The critical-path diagram shows T004 and T006 without ✅ while the paragraph below it
  says "all three closed".

*Branches:* `docs/layout-and-restatements` (3a, 3c, 3e) · `docs/claim-4-counts` (3b) · 3d is fixed
inside the branch that does the rename.

---

## 4 · Is there code that serves no claim?

One module: **`src/holdout/core/pricing/selection.py`**. Only `tests/core/test_pricing.py` and
`tests/core/test_composition.py` touch it. No eval imports it — claim 1 builds `ProposedPrice`
directly — and none of the 49 mutations targets it. It is on `CLAUDE.md`'s declared decision path
("the model returns a scenario table, code picks the row by arithmetic"), so I do not propose
deleting it; I propose **naming** it: either claim 1 brings it into its sweep, or it is written
down that scenario selection is proved by the suite and not by a claim.

`ops/` is correctly outside the claims and says so. `adapters/` is empty with a declared seam.

---

## 5 · Has a claim landed on a preview surface?

**No.** There is no `infra/`, no declared inventory, `make preview-audit` is deliberately absent
and the `Makefile` says so. All five claims are proved locally with no account — confirmed by
running them.

---

## 6 · Is there still **exactly one** door with no key?

The repository holds **three** seals of identical construction and identical declared limit:
`CertifiedPrice`, `SealedAssignment`, `corpus/world/seal.py`. All three are tamper-**evident**,
all three declare explicitly that a coordinated forgery passes, and all three have a test that
requires the forgery to **succeed**. `contamination.py` calls itself "the one door with no key".

The question: if the door opens under a coordinated rewrite, is it "with no key" or "with a key
that shows"? The doctrine says *"Having exactly one unopenable door is what keeps the other six
honest"*. The implementation delivers *one detectable* door, not *one that does not open*. The
difference is not verbal: `assignment table is written before the period opens and then read-only`
is infrastructure that will exist in phase 3, and until then unopenability rests on a type whose
limit is written down.

> **Accepted, 2026-08-30.** The doctrine line is restated to say that **today the guarantee is
> detection**, and that **unopenability arrives with the read-only assignment table in phase 3**.
> The prior wording stays, per doctrine rule 4, and the delta is the finding: a door that detects
> every uncoordinated edit is not the same object as a door that does not open, and the repository
> had been calling the first by the second one's name. The change is in `CLAUDE.md` and is on this
> branch.

---

## 7 · The deferral registry became T008's parking space

**Nine of the open entries point at this session** as their unlock condition: claim 3 covariates,
the `floor.yaml` rule id, the scenario-scale measurement, the ladder ceiling, the regulated basket
3-vs-63, W2 luck, W6's `IMBALANCED_PRE_PERIOD` threshold, the C7/C11/C12 mutations, and ESL
penetration. Plus two more reading "T012 or T008".

None of them is wrong. Together, though, they mean the "phase-1 integration session" became a
synonym for "later" — and the session whose job was to *read* now arrives owing eleven
*decisions*. The rule that follows, and which is now in `CLAUDE.md`:

> **An unlock condition that names a session rather than an event is not a condition; it is a
> date without a calendar.**

The two T008 is explicitly empowered to move:

- **`floor.yaml`** — the rename stands, with §3d's correction: the gate that will go red is `O2`,
  not `G10`. A new window; the closed one keeps the old id.
- **The ladder ceiling** — the **716/26,600** was confirmed by `make eval-guardrail`. Doctrine
  rule 1 is incomplete only for those, and `G6` publishes both numbers without widening an
  assertion. What is proposed is a restatement of doctrine rule 1, not a ceiling on the ladder:
  "the safe state may be empty, and then the correct output is a refusal" is true of the system
  and false only of the sentence.

---

## 8 · The rule "a guard tested by its author" — is it complete?

Nine times in one phase: a sentence, `timeout-minutes: 45`, a deferral, a cost estimate, a
measurement that went stale (W5), a minuted figure (11/11), the cache hypothesis, the rule's own
statement (the scale paragraph that insisted on measuring carried three unmeasured figures) — and
now, tenth, a task note that names the wrong gate (§3d).

**The answer: the rule is not incomplete. It is unarmed.**

Every restatement widened the **form** — a sentence → a number in configuration → a deferral → the
rule's own statement → an instruction to the next session. The form was never the variable. The
invariant across all ten is the same: *the assertion was checked against the artefact it came from
rather than against the thing that would falsify it.* That is precisely the sentence already in
the box. An eleventh widening will add one more noun and will not see the twelfth case.

What is missing is elsewhere. **And all ten were found by a human or by a run — none by a
command.** The rule is the repository's only first-order rule with no gate behind it, in a
repository whose entire argument is that *a rule that is a paragraph is advice and a rule that is
a Makefile target is structural*.

And the mechanism that would arm it **already exists, in one file**. `docs/SCENARIO.md`'s
four-kinds rule — `[M]` measured with the command, `[D]` declared with a contract, `[C]` cited
with a date, `[S]` scenario carrying the words *it has never run* — paid for itself inside the
branch that wrote it: it forced a re-run and W5's counts did not come back the same. It is the
first mechanism in this repository that **caught this defect by construction rather than by
reading**.

Hence the one proposal held to be worth more than all the other corrections together:

> **The four-kinds rule extends from `SCENARIO.md` to every published number — `CLAUDE.md`,
> `PLAN.md`, `TASKS.md`, the evals' READMEs, the workflow comments — and a `make figures` re-runs
> the commands behind the `[M]`s and goes red when they do not return the same.**

At least six of the ten incidents would have gone red: the 11/11, the W5 counts, the 100→109→45
chain, the "1,200 → 212" (no command, so not `[M]`, so it does not go in), the "about 36M", and
the cache hypothesis (no command). The rest — the timeouts and §3d's note — are not numbers a
command produces, and for those the rule already says what to do; what is missing is for it to say
so somewhere a gate reads.

*Branch:* `ops/every-number-carries-its-kind` — and it is the one piece of this report that must
precede the others, because the rest are corrections of numbers and this is the thing that stops
them recurring.

---

## Proposed branches, in order

| # | branch | what it closes |
|---|---|---|
| 1 | `ops/every-number-carries-its-kind` | §8 — the only rule with no gate |
| 2 | `ops/expiry-knows-what-closed` | §2a — the gate that will bite wrongly on 2026-09-30 |
| 3 | `evals/world-cache-measured` | §2b, §2c — restatement + a budget from measurement |
| 4 | `evals/unarmed-checks` | §1 — 21 checks, 8 with no reason, the `at_design` gap |
| 5 | `docs/layout-and-restatements` | §3a, §3c, §3e — the map, the two chains, the smaller ones |
| 6 | `docs/claim-4-counts` | §3b — 11/11 → 12/12 in five places |
| 7 | `contracts/floor-rule-id` | §7 — with §3d's correction inside it |
| 8 | `docs/doctrine-rule-1-ceiling` | §7 — a restatement, not a ceiling |
| 9 | `skills/integration-review` | T008 itself: the method as a skill |

\#9 is T008's `closes` and was deliberately not written here — a skill extracted from one session
is a copy of that session, and `TASKS.md` itself carries the argument for T00B. It is written
**after** 1–8 have run, so that it has two things to record: what the review asked, and which of
the questions produced a finding.
