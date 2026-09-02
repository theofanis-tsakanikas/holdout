# Holdout — tasks

The third layer of one thing. **What** the system is, and why → `CLAUDE.md`. **How** it is built
and **in which phases** → `PLAN.md`. **The atoms** — the individual pieces of work, with their exact
closing condition and their status → this file.

This is the single source of truth for what is open. `PLAN.md` no longer carries a progress table,
because two answers to "what is still open" is exactly the thing this file exists to prevent.

## The schema

| field | means |
|---|---|
| `id` | `T001`, `T002`, … · ops/method tasks that gate the phases are `T000`, `T00A`, `T00B`, `T00C` |
| `title` | what it is |
| `branch` | the exact branch name (one branch per closed piece — one per session, not per commit) |
| `depends_on` | ids that must have closed first |
| `blocks` | ids that cannot start until this closes (the inverse of another task's `depends_on`, named here only where the ordering is the point) |
| `closes` | the checkable condition — which `make` target, which file, which number |
| `out_of_scope` | stated, so scope does not creep |
| `stop_at` | where the session stops and notifies the author |
| `review` | oversight level 2 in fresh context: yes / no |
| `status` | open · in progress · closed |

`status: closed` tasks stay in the file. The record of what each closed piece settled, and what the
reviews cost, stays in `PLAN.md`'s prose — doctrine rule 4: a correction never erases what was
previously stated.

---

## Ops / method — these gate the phases

These are not phase work. They fix the instruments and enforce the rules the phase work is measured
by, so they land first.

```
id            T000
title         Fix the measuring instrument — the eval schema's blind spot
branch        evals/instrument-fix
depends_on    —
blocks        T003, T004, T005, T006
closes        The claim-1 eval no longer computes a "known twice" boundary by calling the
              core's own primitive. Specifically:
              (1) the misattribution is corrected — 6,650 of the "7,366 ladder quotes
                  refused by a ceiling" are MARGIN_CAP_BASIS_UNEVALUABLE (a predicate with no
                  bound); the supportable figure is 716 of 26,600, from one envelope. Fixed in
                  the eval and in DECISIONS.md.
              (2) _exact_floor stops calling Money.as_lower_bound (the core's own rounding)
                  while its docstring claims independence; the "computed twice" boundary is
                  genuinely second-implementation, and G3's tolerance can catch a bound that is
                  one cent TOO STRICT — the exact shape of the ladder bug it cites as motivation.
              (3) benchmark_margin_pct declares which denominator it is in (selling price vs
                  cost), so a caller cannot apply 16.81% where 20.21% was meant.
out_of_scope  The floor.yaml rule-id rename and the ladder-ceiling restatement — those stay in
              T008, because they are contract changes with a restatement chain, not instrument
              defects.
stop_at       When the three fixes land with tests that fail on the un-fixed instrument, and
              before any new eval (T003–T006) is written on the corrected shape.
review        yes
status        closed
```

Finding 2 is a defect in the measuring instrument itself: every eval built on the `evals/` shared
shape inherits the blind spot. It is fixed **before** it is copied four times (into the claim-2, -3,
-4 and -7 evals), not after — which is why it precedes T003–T006 instead of sitting inside the
integration session that depends on them.

**What it landed.** All three, each with a test that fails on the un-fixed instrument, and one thing
the `closes` line did not ask for.

*(1) The misattribution.* `G6` no longer counts every refusal outside the ladder's three bounds as a
ceiling. Which bucket a refusal falls in is decided by `reference`, from the `side` it already
computes per rule — not from a list of codes, which would have to be remembered every time a rule is
added. **716 refused by a ceiling · 6,650 refused by a rule with no bound**, both published, both
pinned in `tests/evals/test_guardrail_instrument.py`. `evals/guardrail/README.md`,
`docs/DECISIONS.md` and `corpus/real/MANIFEST.yaml` restate rather than overwrite.

*(2) The rounding, and the tolerance behind it.* `_exact_floor` is gone; `evals/guardrail/rounding.py`
re-decides the direction and carries it out on the value's exact integer ratio — no precision, no
context, no quantisation shared with `Decimal`, so a defect in any of those cannot cancel out. A
test scans **every** module under `evals/guardrail/` bar a declared exclusion list, refusing any
reach for `Money`'s three rounding constructors or any import of a rounding name out of
`holdout.core.money`. Verified against `main`, where it reports `checks.py:400`; a rule scoped to
the file the fix landed in would have passed on the tree that had the bug. It states the three
routes it does **not** cover, which `CLAUDE.md` requires and the first version of it omitted. `G3`'s one-cent tolerance is gone with it — under
a correctly rounded core it was unreachable, so it was an exemption for exactly one bug, the bound a
cent too strict. `G4` lost the same tolerance for the same reason.

*(3) The denominator.* `ProposedPrice.benchmark_markup_on_cost` takes a `MarkupOnCost` and refuses a
bare number at runtime, not only where mypy runs; `MarginOnPrice.as_markup_on_cost()` is the only
route between the two. The case the guard is tested on is the figure the instrument publishes —
16.81% — not one this session invented. The contract half stays deferred.

**Beyond the line above: `G10`.** `G2` and `G3` both reach a bound *through a price*, so both see a
misplaced bound only where a corpus price lands in the one-cent gap it opens — measured, an absolute
floor a cent loose gives `G2` **3** violations in 28,485 certified prices against `G10`'s **232,373**
disagreements in 824,790 bounds. `G10` compares the bounds themselves, as integer cents with no
tolerance: **0 disagreements**. Three mutations are planted against it, and the third is the one
that earns it — **a bound at the right amount wearing another rule's id**, which moves no arithmetic
at all and is refused by `G10` and by nothing else in the eval.

**What oversight level 2 sent back, and what it cost.** Two blocking findings, both in the prose
rather than the code, and both the project's own most frequent defect. The claim that patching
`Money.as_lower_bound` left every check green was **false and had not been run**: `G2` fails on it
with 199 violations, and what actually stayed green was `G6` — the one check that shared the
primitive — while its published figure moved 7,366 → 7,365 in silence. Corrected in all six places
that carried it, with the mutation output quoted. And `G3` was still *publishing* the one-cent
tolerance this task removed, so the eval's own terminal output contradicted its README. Four latent
findings were fixed with it: the AST rule was a hard-coded tuple that could not see the module this
branch itself added; `BASE_PRICE_MOVE_EXCEEDS_WEEKLY_LIMIT` bounds on **both** sides and collapsed
to one in a dict keyed by code; `reference` gated on `proposal.unit_cost` while reading
`case.unit_cost`; and `MarkupOnCost(Decimal("Infinity"))` was accepted, becoming an
`InvalidOperation` crash three modules later where the contract is a refusal.

**And CI's timeout was wrong rather than the run.** The first PR run was cancelled at 15m16s
while an identical run on the same commit passed at 11m00s, four minutes apart, on a different
runner. Two things moved: 13 mutations became 15, and the eval got ~15% slower because `G10`
makes a full independent pass over every bound — about 30% more work against a budget the *fast*
runner was already using two thirds of. `reference.constraints` is now computed once per decision
instead of once per check (`G3` was recomputing it per *reason*, a quarter of a million times),
and `rounding` works on the value's exact integer ratio rather than building a `Fraction` per
bound: **16.5s → 12.1s**, against 10.5s on `main`. The job's `timeout-minutes` went 15 → 25,
with the arithmetic in the workflow: a timeout is a guard against a hang, not a performance
budget.

`make check` green at 768 tests · `make claim-1` **10/10 with 16/16 mutations biting**.

```
id            T00A
title         Hooks that make the barriers structural, and make expiry
branch        ops/hooks
depends_on    —
blocks        T002
closes        .claude/hooks/corpus_isolation.py — blocks any write under corpus/world/ that
                imports from src/holdout/ (the no-import-path barrier, enforced by the harness
                rather than by a test that runs after the fact).
              .claude/hooks/main_guard.py — blocks git commit on main.
              .claude/settings.json — committed, so the hooks travel with the repository and go
                through a pull request like everything else.
              make expiry — deferred items in DECISIONS.md carry an unlock condition or a date;
                on expiry the target goes red. Doctrine rule 6 ("exceptions expire") is enforced
                nowhere today.
out_of_scope  Any hook that duplicates a check CI already makes green-or-red.
stop_at       When the two hooks fire on a deliberate violation, settings.json is committed, and
              make expiry goes red on a planted expired deferral.
review        yes
status        closed
```

The import barrier must exist **before** `corpus/world/` is written — otherwise T002 can land a
violation that only a later test catches. That is why T00A blocks T002.

**What it landed, and where it went wider than the line above.** The barrier is policed over the
whole of `corpus/`, not `corpus/world/` alone, because that is what
`tests/boundary/test_corpus_imports_nothing.py` has always policed and a hook that policed *less*
than its own gate would wave through the violation it was added to catch early. The rule now has
**one** implementation, `ops/isolation.py`, with the test and the hook as its two callers — a hook
carrying its own copy of the AST walk would have been the copy nobody reads. And the hook is
registered on `PostToolUse` for `Bash` as well: a heredoc or a `sed -i` reaches no `PreToolUse`
hook with a `file_path` at all, so a Pre-only hook would have been blind to the route this session
itself writes files by. That half cannot un-write the file and is not the guarantee; the test is.

`make expiry` runs inside `make check` and is named as its own step in `ci`. Its limit is written
into `docs/DECISIONS.md` rather than left implied: an unlock **condition** is prose and can never
expire, so a condition-only deferral is checked for existence and never for truth. What the target
does about that is print every deferral's age in days.

**Oversight level 2 found ten things, two of them fatal to this task's own `closes` line** — the
guard allowed the ordinary two-line `git commit` on `main`, and the barrier missed `src.holdout`,
which is the spelling this task description itself used and which imports and runs. Both were
fixed by correcting the code, each with a test that fails on the un-fixed version; the record is
in `PLAN.md` and `docs/DECISIONS.md`.

```
id            T00B
title         Skill — claim, extracted from the two claims that have closed
branch        ops/claim-skill
depends_on    T000, T003
blocks        T004, T005, T006
closes        .claude/skills/claim/ — the procedure for building one of the seven claims end to
              end: the eval that attacks it from a source its author did not choose, the
              gate-proof mutations with the three rules, the make claim-N target and mutation
              ownership, and the statement of where the independence is and what is not proved.
              It lives in this repository because it shapes the code here (CLAUDE.md's
              criterion), and it is extracted from TWO closed claims rather than one.
              Also: CLAUDE.md's rule about a sentence is generalised to an ASSERTION — a number
              in configuration is one too. `ci.yml`'s claims job was set to 45 minutes from a
              projection onto fourteen cores while a measurement of the four-core run was
              available, inside the same change whose deferral existed to prevent exactly that.
out_of_scope  Writing any claim's eval. The defect-to-rule skill (T00C) and integration-review
              (T008). Product code of any kind.
stop_at       When the skill exists, CLAUDE.md's rule covers numbers as well as sentences, and
              the divergence the extraction found between the two samples is recorded rather
              than papered over.
review        yes
status        closed
```

**Why it blocks T004, T005 and T006 rather than running beside them.** Those three are mutually
independent and are meant to run in parallel; they are also the first three evals that will be
written by copying the shape of an existing one. A method extracted **after** they land is a
method extracted from five samples of a habit rather than two samples of a rule, and three of
those five would have inherited whatever the copying got wrong. T000 makes the same argument one
layer down and is the reason it precedes the evals rather than sitting inside T008: *a defect in
the measuring instrument is fixed before it is copied four times, not after.*

**What it landed.** The skill is a **procedure and not a second copy of the shape**: it points at
`evals/README.md`, `evals/report.py` and `evals/gate_proof/README.md` rather than restating them,
because a procedure that carries its own copy of the rules is the copy that goes stale. What it
adds is what only two samples can give — a table of every place claims 1 and 2 diverge, with the
column that says what actually governs the choice: an outside-the-repository corpus against a
generator behind an enforced barrier; a single question against a rate tested as a binomial; ten
seconds a mutation against a small configuration declared in a contract; nothing cached against a
world cache keyed on a digest of every file it was produced by.

**And the extraction produced a finding, which is the argument for extracting from two.**
`evals/README.md` declares `<claim>/README.md` as part of the shape. Claim 1 has one; **claim 2
does not** — its three answers are real but spread across module docstrings, with only the third
enforceable half printed on every run through `Report.notes`. It was invisible while there was one
claim, because with one sample the shape *is* whatever that sample does. `docs/DECISIONS.md`
carries it as a deferral with T012 as its unlock and a date behind that, rather than the skill
declaring a shape half its own sample violates — and rather than this branch writing claim 2's
evidence, which is how a document comes to assert more than the code supports.

**The rule about sentences was short a limb, for the fourth time.** `ci.yml`'s `claims` job was
given `timeout-minutes: 45`, projected from the author's fourteen-core laptop onto a four-core
runner, which cancelled the harness before it finished. It happened **inside the same change that
closed the deferral written to prevent it** — the 25-minute gate entry, whose whole argument is
that a budget set from a projection is a gate reporting which machine it drew. Nothing was
careless; the rule said *"a sentence"* and this was a YAML key. It now reads **an assertion — a
sentence, or a number in configuration** — with the measurement taken on the hardware that will
meet it. `CLAUDE.md`'s checklist carries the same widening, and the skill has a section on it:
a timeout, a K, a tolerance, a threshold and a budget are each an assertion wearing a number
instead of a verb.

**One test, and it is armed by a planted fixture.** `tests/skills/test_skills.py` checks the
wiring only — frontmatter parses, `name` is the directory, the description says *when*, no bundled
file is unreferenced, every relative link resolves — and states in its docstring that it cannot
check whether the skill is right or whether it is followed. The last two checks would be vacuously
green on the real tree, since no skill here bundles a second file yet, so they are driven by a
skill directory built inside the test that is wrong in each direction. That is the shape
`tests/ops/test_expiry.py` already uses, and it is the answer to the text fallback whose twelve
parametrised sources all took the other branch. The suite is **828**.

```
id            T00C
title         Skill — defect-to-rule
branch        skills/defect-to-rule
depends_on    —
closes        .claude/skills/defect-to-rule/ — root cause, then the rule that stops the class
              recurring. It lives in this repository because it shapes the code here (CLAUDE.md's
              criterion).
out_of_scope  The integration-review skill (T008) and any user-level skill.
stop_at       When the skill exists and has been run once against a real phase-1 defect to
              produce a rule.
review        no
status        open
```

Three phase-1 defects were already fixed — the empty `PriceBounds()`, the ladder/guardrail rounding
split, the `legal_instrument` asserting a basis its article never states — and not one of them became
a rule. The skill is what turns the next one into a rule instead of a memory.

### The two atoms T003 stopped on — 2026-08-28

T003 built the A/A harness far enough to run the whole system once on the corpus, and stopped at the
first measurement. **End to end, on this repository's own corpus, the system produces no number.**
Two independent causes, neither of them in a file that is wrong on its own, and both invisible until
the corpus and the design engine were run against each other for the first time:

| | measured |
|---|---|
| the estate | 100 stores → **109 neighbour pairs** → 55 automatic exclusions → **roster 45**, control arm 9 |
| the design | **4 of 5 world seeds refuse** at moment 1 with `UNDERPOWERED_FOR_DURATION` on a roster of 45 |
| the readout | on the one seed that survives, **0 of 200 lotteries** pass the balance check; on the full 100-store roster with no exclusions, 30 of 100 |
| and it does not scale out | 400 stores leave a roster of 130; **1,200 stores leave 212**. The surviving roster saturates |

`corpus/world/chain.py` opens *every second* store within 990 m of one the chain already has, so
that W2 always has interference to detect. `feasibility._neighbour_exclusions` removes one member of
every pair inside the declared 1 km radius, so that no store measures its neighbour. Both are
deliberate, both are documented, and together they delete half the estate — and what is left cannot
carry a 20% holdout at a 0.10 standardised difference.

The second cause is smaller and sharper. At 25 controls on the same roster,
`store_format=hypermarket` sits at a **constant 0.1734** and `pricing_zone=zone_c` at a constant
0.1122, for every draw: a categorical covariate's balance is fixed by how the strata are allocated
to cells, not by the lottery. So there are rosters on which **no admissible assignment can ever pass
the readout's balance check**, and `assess` returns `Feasible` for them without a word. That is the
same shape as the deferral T002B closed — an experiment that could never have reported anything, for
a reason with nothing to do with the estimator — one moment earlier.

They are two tasks rather than one because they are independent: T00D is arithmetic inside
`holdout.core` and needs no corpus, T00E is the corpus's geography and needs no contract.

```
id            T00D          <- do this one first
title         A design that can never pass its own balance check is refused at moment 1
branch        core/attainable-balance
depends_on    T001, T002B
blocks        T003
closes        assess() refuses NO_ADMISSIBLE_ASSIGNMENT when no draw within the strata it
              built could satisfy balance_tolerance_smd on a categorical covariate. The
              bound is exact and computed with the readout's own arithmetic: for each level,
              the control count is between the number of strata that are pure in that level
              and the number that contain it at all, and the best standardised difference
              attainable over that range is a number, not an estimate.
              It is SOUND and INCOMPLETE, and says so: it never refuses a design some draw
              could have saved, and it does not catch a roster that fails on the numeric
              covariates by sampling spread — that one is a rate, and it is T003's to publish.
              The vocabulary does not grow: NO_ADMISSIBLE_ASSIGNMENT already says exactly
              this sentence, and its meaning in contracts/vocabularies/reason_codes.yaml is
              restated rather than replaced.
out_of_scope  The neighbour exclusion and the corpus's geography (T00E). Any change to
              balance_tolerance_smd or holdout_share_pct — a threshold that moves because it
              bound is the shape oversight level 3 exists to catch.
stop_at       When the refusal fires on a control count found by SEARCH rather than chosen —
              the case comes from the lottery, not from whoever wrote the guard — and when a
              brute-force draw over every control count it accepts confirms it refused
              nothing that could have passed.
review        yes
status        closed
```

**What it landed.** `balance.attainable` — the best standardised difference any lottery within a
given stratification could reach, per categorical covariate — and a `NO_ADMISSIBLE_ASSIGNMENT`
refusal in `assess` when it already exceeds `balance_tolerance_smd`. The vocabulary entry was
restated rather than replaced, and it now carries both readings with the date.

The bound is computed with `_standardised` itself — the readout's own function, not a second
implementation of it — because the question is *predictive*: a prediction that used different
arithmetic from the thing it predicts would be worth nothing. It is sound and incomplete, and both
files say which: the per-level optima need not be simultaneously attainable, and numeric covariates
are not bounded at all, because almost any numeric imbalance is attainable by *some* draw and the
question about them is a rate rather than a possibility. That rate is claim 2's to publish.

**The case came from the corpus and the breaking size from a loop.** The test roster's composition is
laid out by `corpus.world.chain`'s own keyed hashing, and the control counts are scanned rather than
named. On a 100-store roster the scan reproduces the defect exactly as it was found in the field:

```
 20 controls  reachable      best attainable store_format=hypermarket 0.0792
 21 controls  OUT OF REACH   best attainable pricing_zone=zone_b      0.1356
 25 controls  OUT OF REACH   best attainable store_format=hypermarket 0.1734   <- the finding
 26 controls  reachable      best attainable pricing_zone=zone_b      0.0463
```

Three tests hold it, and none of them takes the arithmetic's word for anything: every control count
the bound refuses is checked against 200 real draws and none may pass; every count it accepts is
checked so that no draw comes in *under* the floor; and the scan must come back mixed, because a
guard that refused everything would pass the first test and destroy the engine.

`CLAUDE.md`'s checklist asks whether a `gate-proof` mutation proves the gate bites. **There is none
and there cannot be yet** — design-engine mutations belong to claim 6, which has no Makefile target,
and the ledger refuses a mutation no claim target would run. The gap is written into
`feasibility.py`'s own docstring rather than left for someone to notice.

```
id            T00E
title         The corpus's clustering becomes a declared per-world parameter, and HARNESS is
              chosen on the surviving roster
branch        corpus/declared-clustering
depends_on    T00A, T00D
blocks        T003
closes        corpus/world/chain.py stops opening every second store inside the exclusion
              radius as a hidden constant. Two declared assumptions, each with the argument
              beside it in the corpus's own voice:
              (1) clustered_pct, per world — realistic in W1/W3/W4/W5/W6, HIGH in W2, which
                  is the only world that needs interference to exist. W2 is still required to
                  ESTIMATE ON WHAT IS LEFT, so its surviving roster must work too;
              (2) the placement radius scales with the stores a town holds, so the density of
                  the estate — and therefore the number of chance pairs — does not change
                  with the scale. Today it does, which is why the surviving roster saturates
                  at 212 however many stores are added. That is a pathology of the generator,
                  not a fact about retail.
              Then HARNESS is chosen so the SURVIVING roster is >= 200 in EVERY world,
              measured per world and recorded in corpus/world/README.md with the command.
              The scenario-scale figures in that README are restated, not overwritten
              (doctrine rule 4): the chain moved, so the counts moved.
out_of_scope  The balance tolerance, the holdout share, the neighbour radius. The A/A harness
              itself (T003).
stop_at       When every world's surviving roster is measured and >= 200, and when the
              balance pass rate at that roster is measured and recorded — so T003 starts from
              a number rather than from a hope.
review        yes
status        closed
```

**What it landed, and the numbers it closes on.** `clustered_pct` is a field on `World` — 15% in
the five that need no interference, **30% in W2** — and `chain.AREA_PER_STORE_M2` fixes the estate's
density so the town's placement square grows with the stores it holds. `HARNESS` is
**320 x 12 SKUs x 112 days**, and it has *more* stores than `scenario` rather than fewer, which is
the whole restatement in one line: the roster is what the lottery draws over.

```
make roster --scale harness            seed holdout-w-0001, 20% holdout share
 world   cluster   stores    pairs   excluded   roster   controls
    W2       30%      320      148         98      222         44      <- the binding world
 others      15%      320       59         51      269         53
```

Across eight world seeds the worst world never falls below 218. The figure that decides whether an
experiment can report anything moved with it:

| roster | control arm | draws inside the 0.10 tolerance |
|---|---:|---|
| 45 — 100 stores, before T00E | 9 | **0 of 200** |
| 265–269 — W1, W3–W6 | 53 | **145–192 of 200**, three world seeds |
| 218–222 — W2 | 43–44 | **121–172 of 200**, three world seeds |

Three properties are held by tests rather than by the docstring that claims them: the clustering is
**nested**, so W2's estate is the realistic estate with more of the same; **only the geography moves
between worlds** — same shops, same formats, same sizes, same zones, same products — which the
generator gets only because the coordinates are drawn in both branches and overridden rather than
skipped; and the estate's **density does not move with the scale**, which is the half that had no
test at all before and is what capped the usable roster at 212 however many stores were added.

`corpus/world/README.md`'s scenario figures are **restated, not overwritten**: 36.7M POS lines
became 39.2M, because the chain moved. `demand.BASE_LINES_PER_SKU_DAY` was left where it was —
re-tuning a measured constant to land back on a prose figure is fitting the corpus to a sentence.

**What T003 inherits, and the one decision it does not have to take.** A refusal rate on balance
alone of roughly 4% to 40% depending on the world seed and the roster. `false_refusal_max_pct`
**stays at 10 and is not touched** — it was written before anything was measured — and what it binds
is settled instead: the refusals the machinery produces, every `at_readout` code but
`IMBALANCED_PRE_PERIOD`. The imbalance rate is published beside it as a number with **no threshold**
in this phase, because the only evidence for a bigger threshold would be the measurement that raised
the question. `docs/DECISIONS.md` carries the deferral with what the rate is a function of and what
would give grounds to set one; its unlock is T008.

**Phase 2 opens with CI rather than with Terraform, and the order is measured rather than felt.**
`docs/FINDINGS.md` carries the disposition — *its own branch, before the first Terraform layer* —
because phase 2 is where the push rate multiplies and CI is what every later phase is judged by.
Rebuilding the instrument mid-phase risks the defect it protects against. Four atoms, and the
first is not the one that was on the list: it was found by pairing the Actions run list on
`headSha` while scoping the other three.

```
id            T00F          <- do this one first, of the four that open phase 2
title         One tree, one run — ci.yml is entered twice for every branch push
branch        ops/ci-runs-once-per-tree
depends_on    —
blocks        T00H
closes        `on: push:` carries a branch filter, so a push to a branch with an open pull
              request no longer fires BOTH the push and the pull_request event. Measured over
              200 runs, 2026-08-27 to 08-31: 118 distinct head shas, 81 under both events,
              ~58 h of redundant runner time in five days, 34.9 h of it claim-2 — 36% of all
              successful claim-2 compute, and roughly 8x the cache over-coverage in T00G.
              A guard that judges the trigger's EFFECT rather than its spelling: given the
              parsed `on:` block, does a push to a non-main branch start this workflow? Four
              filters that filter nothing are driven as attacks — no filter, `['**']`,
              `[main, 'ops/*']`, and `branches-ignore` — because a guard keyed to the literal
              line `branches: [main]` passes on three of them. Verified against `main`, where
              the block parses as `{'push': None, …}` and the guard goes red.
out_of_scope  The cache key (T00G), sharding (T00H) and the merge queue (T00I). The 90-minute
              budget is NOT lowered: it is a ceiling against the slowest cold draw, and this
              change does not move a cold draw.
stop_at       When the fix and its guard land. What this SAVES is a prediction until a week of
              runs exists on the other side of it — the 58 h is what was spent, not what comes
              back, and no figure in the branch may say otherwise.
review        yes
status        open
```

**The second effect, and it is written down at the weaker strength the data supports.** Every
context existed twice on every pull-request head sha — 36 of 36 merged pull requests — including
all three the `main` ruleset requires. That is a live hazard and it was **never realised**: in zero
of those 36 did a required context disagree with itself. Three self-disagreements exist in the
sample and all three sit on superseded commits, so the ambiguity decided nothing. Whether the forge
takes the latest check run or either one is **not established**, and the fix dissolves the question
rather than answering it — after the filter, a head carries one run of each context. A first draft
of this entry claimed *a gate whose verdict depends on which run the forge happens to read*; it was
withdrawn against the merge heads before the branch was written, which is the register's rule
arriving in time for once.

```
id            T00G
title         The world cache key over-covers, and narrowing it is the dangerous direction
branch        evals/cache-key-covers-the-world
depends_on    —
closes        `evals/uplift/cache.py`'s DEPENDS_ON stops taking all of `corpus/`. `corpus/real/`
              is claim 1's and claim 7's corpus and cannot produce a byte of a world, yet a
              commit touching it threw away every world ledger: 11 spurious invalidations over
              71 claim-2 jobs at +18.4 min each (95% CI +13.5 to +23.2), ~3.4 h already spent.
              The test DEMONSTRATES that the key still MOVES when world sources genuinely
              change, against two commits that differ, rather than asserting it.
out_of_scope  Lowering the 90-minute budget. The ceiling exists for the cold draw and the key
              will still move — less often, which is the point.
stop_at       When the key is narrowed and the both-directions test drives real files.
review        yes
status        open
```

**What it landed, and one thing the `closes` line did not ask for.** `DEPENDS_ON` becomes
`("corpus/world", "corpus/__init__.py", "evals/uplift/outcomes.py", "evals/uplift/reference.py")` —
15 files where it read 18. `corpus/__init__.py` is kept **by name**: it executes on any import of
`corpus.world`, so narrowing to the subdirectory alone would have dropped it, and it holds only a
docstring today, which is precisely why that looks safe and is not. The question is what *can*
produce a world, not what happens to today.

*The coverage is computed rather than declared.* `test_every_module_a_cached_artefact_is_produced_by_is_in_the_digest`
walks the **import closure** of the three roots and requires every repository-local module in it to
be a file the digest reads. It reaches **13 modules** and reports **11 missing** when `corpus/world`
is dropped from the list, so it bites. That is a second implementation of *what produces a world*,
in the sense `evals/README.md`'s rule 5 uses the words — not a list somebody keeps in step.

*And a `DEPENDS_ON` entry that names nothing now raises.* It used to be skipped silently, which is
this narrowing's own failure mode wearing the shape of a typo: `corpus/wolrd` would have digested
the two `evals/uplift` modules alone, every world would have read back unchanged forever, and a
mutation to the generator would have reported `SURVIVED`. **An instrument that cannot answer raises
rather than returning a smaller number** — `ops/figures.py`'s rule, at the one site where the
smaller number is silently wrong rather than merely wrong.

*What the closure test cannot see, and what asking about it found.* A value reaching the
world-producing path **as data rather than as an import** is invisible to an import walk by
construction. Two exist, they fail in opposite directions, and the split between them is on the
direction rather than on convenience:

*(1) The ladder contract — closed here, because it is silent.* `prepare()` calls
`policy.contract_ladder()`, which reads `contracts/policies/ladder_policy@v1.yaml` at run time:
the control arm of every fresh-markdown world, and so the markdown behaviour the whole ledger is a
summary of. Moving one rung changed the policy and left the digest where it was. Nothing recomputes
anything that would disagree, so every consumer reads the same stale ledger and the run reports a
world with the old ladder **in silence** — a gate disarmed. `DEPENDS_ON` gains **one file**, not
`contracts/`, and the test takes the path from `policy.LADDER_CONTRACT` rather than repeating it,
so a generator pointed elsewhere cannot leave the list behind.

*(2) The metric rounding — filed, because it fails safe.* `agreement/walked` caches a value whose
rounding arrives from the metric contract as an argument. The half it is compared against is
computed fresh, so a stale entry produces a **red** `U10` rather than a silent pass. **The fix is a
genuine widening with two candidate shapes and T00G is a narrowing**; shipping both would move the
key in two directions at once and no measurement could say which did what.

**A proven silent hole may not be declared as a limit by the branch claiming its coverage is
computed.** That is what separated the two, and it is why (1) did not wait for its own branch.

**The warning travels with this one and is the load-bearing half.** Over-covering costs time.
**Under-covering serves a stale world and nothing goes red** — the mutation reports `SURVIVED`
while the thing it broke never ran, which is a gate silently disarmed and the failure this
repository has already paid for four times. `cache.py`'s own docstring names the opposite hazard
and has the defect one directory in.

```
id            T00H
title         Shard claim-2 across its six worlds
branch        evals/claim-2-sharded
depends_on    T00F
closes        The six worlds run on six runners instead of one, with a combine step, because
              the eval prints aggregates ACROSS worlds. Both CI invariants survive: `discover`
              still finds targets by grep over the Makefile and the workflow still never lists
              one, and `claims-complete` still sees every shard — a shard that silently does
              not run is refused exactly as a skipped matrix is. Correctness is exact rather
              than statistical: the sharded output equals the unsharded output BYTE FOR BYTE,
              same sha256, no tolerance. Two runners in different regions 1.69x apart in wall
              clock already produce byte-identical result lines, which is what makes that test
              available.
out_of_scope  Path filtering, refused by name in docs/FINDINGS.md: skipping claim-2 when only
              documents change reintroduces a claim that silently does not run.
stop_at       When the sharded and unsharded outputs are compared and equal.
review        yes
```

**Why it depends on T00F rather than merely following it.** Concurrency, measured: queue delay
median 3 s, peak **16 jobs simultaneous against a documented ceiling of 20**, and the 16 is what it
is *because jobs double*. Six shards on top of the doubling exceed the ceiling, past which the wall
clock stops improving and only the flight count grows. Removing the duplication is what makes the
headroom exist.

```
id            T00I
title         A merge queue — prepared, verified, and NOT applied
branch        ops/merge-queue-prepared
depends_on    T00F, T00H
closes        The expensive matrix runs once on the merged result rather than on every push.
              Two halves, and only the first is this repository's to make:
              (1) `ci.yml` gains `on: merge_group`, without which the required contexts never
                  run in the queue and every merge blocks forever;
              (2) the `main` ruleset gains a `merge_queue` rule and LOSES
                  `strict_required_status_checks_policy: true` — and THE TWO MOVE TOGETHER OR
                  NEITHER MOVES. Strict mode is not only a cost. It is what guarantees a branch
                  is tested against the `main` it will land on: a branch green against an older
                  `main` can break `main` when merged, and strict mode is what stops that
                  today. A queue provides the same guarantee by a different route, because it
                  tests the MERGED RESULT. Clearing strict mode alone would trade a real
                  guarantee for one re-run in five days, which is the worst available outcome
                  and the one this atom could reach while looking like a simplification.
out_of_scope  Applying (2). The ruleset IS oversight level 1 — required contexts `gate`,
              `secrets`, `claims-complete`, zero bypass actors — and editing it is a change to
              the forge rather than to this tree. No session applies it.
stop_at       When (1) is in the tree and (2) is written up with the exact API call and its
              verification, and PUT TO THE AUTHOR. A peer session cannot authorise it and this
              session does not ask one to.
review        yes
```

**And the cost case is measured now, because it did not survive being asked.** The disposition in
`docs/FINDINGS.md` justified a queue on `#30`'s *two superseded runs*. **Those two were the push
run and the pull_request run of one sha** — the duplication T00F removes — so that measurement is
already spent and cannot be spent twice.

*What is left was counted rather than argued.* Over the 200-run window, every branch's head shas
ordered by first run, classified by the branch's own commit subjects and its merge-base:

| transition | count |
|---|---|
| **forced update** — same work, new base | **1** |
| the author changed the work | 49 |
| amend or retry on the same base | 0 |

**A merge queue removes the first row and nothing else.** One full matrix in five days.

*The instrument is recorded because the first one was wrong.* `git patch-id` was tried first, on
the reasoning that a rebase preserves patch-ids. It does not when the rebase overlaps what landed:
it classified `contracts/floor-rule-id`'s second matrix as a content change, and
`docs/FINDINGS.md` records that one as *forced by `bec0e7f` landing on main*. **A documented event
is what caught it.** The subject-plus-base discriminator reproduces that branch exactly — 1 forced,
2 content — which is why it is the one reported. The earlier timing signal gave *at most 17*; that
was a ceiling over coincidence and is superseded by a count.

*So T00I is not justified on measured cost today, and the honest ask says so.* Its case is that it
removes a **class** of wasted run rather than a quantity of them, and that the quantity is a
function of the merge rate — which phase 2 raises and which nothing has yet measured at that rate.
**That is a forward-looking argument and must be put to the author as one**, not as a saving. The
saving was 58 hours and T00F already took it.


**What it landed, and the number is measured rather than projected.** Eight interleaved shards of
the expanded draw list, a combine step that runs the checks **once over every draw**, and both
wired into `ci` without the workflow naming a claim or a shard count — `discover` derives
`CLAIM_2_SHARDS` from the target name and reads it out of the `Makefile`, the way it already reads
the target names.

*The split is not by world, and the measurement is why.* Six worlds is the obvious unit and the
wrong one: the harness decomposes into **18 tasks** carrying **456 draws**, and eight of those
tasks hold the 400 K-draws. The heaviest task **alone** is 240.3s against 270s for the whole
parallel harness — 89% of the wall clock is one task — so no arrangement of whole tasks beats it.
The unit is the draw.

*And the slices are interleaved rather than contiguous.* Per-draw cost varies about tenfold across
tasks — W1's heaviest at 4.8s, W2's lightest at 0.45s — and the expanded list is ordered by task,
so a contiguous slice is the **worst** distribution available. Measured over eight interleaved
shards: **38 43 39 42 37 40 43 41 seconds, max over min 1.16**.

*The guarantee is exact rather than statistical.* The combined output equals the unsharded output
**byte for byte**, driven at 1, 3 and 8 shards, and end to end through the real `Makefile` targets:
eight `claim-2-shard` runs then `claim-2-combine`, green at 13/13 checks and 8/8 mutations.

*Completeness is guaranteed where `report()` cannot do it.* Every rate has a count of draws as its
denominator, so a missing shard produces a plausible number rather than an error — `U1`'s `8/200`
over 150 draws still prints. `gather` refuses a position that never arrives or arrives twice;
`shards.parts` checks the files as a **set** — different trees by digest, disagreeing counts, and a
set that is not all of them, which is the shape a CI matrix produces when one leg fails.

*What the mutation ledger caught, and it was right to.* `claim-2-combine` runs claim 2's mutations
and so does `claim-2`, which counted by name is the duplicate the accountant exists to refuse. The
answer was not to widen the assertion: `claim-2-combine` **is** claim 2's target in the sharded
arrangement, so ownership is now counted over a **closed** list of arrangement suffixes, and
`tests/evals/test_ledger.py` drives both halves — a shard and a combine are one owner, and a
*different* claim's target running them is still two.

*What is cached rather than removed, said plainly because the atom would otherwise read as
finished.* A cold combine is **596s** — `_truths` 411, `U11` 195, `U10` 51 — because the
counterfactual generations it needs are produced by no shard. Two key families with one writer each
and the same digest make it a bounded penalty paid once per world-source change rather than a
partial cache silently regenerating. `docs/FINDINGS.md` carries the removal and the reason it is
safe.

```
id            T00J
title         The counterfactual generations move into the shards
branch        evals/truths-in-the-shards
depends_on    T00H
closes        The combine job stops generating counterfactual worlds. `_truths`'s expensive
              half — `counterfactual_unit_weeks` — runs in the shards, which already have
              every world warm because the slices are interleaved. The combine keeps choosing
              the units over the WHOLE set, so the byte-identical comparison is unchanged and
              is what proves the move.
              Measured before: a cold combine is 596s, of which _truths is 411s. A cold run is
              cold BECAUSE the corpus or the generator changed, which is the run where every
              shard is cold too and the parallel phase is worth the most — so this removes a
              serial tail from exactly the runs the 90-minute ceiling exists for.
out_of_scope  The agreement checks (U10, U11), which take no records at all and want their own
              shard rather than a shard's leftovers. 246s of the 596.
stop_at       When a cold combine is seconds and the output is still byte-identical.
review        yes
status        open
```

**Why it is safe, recorded here because it is not obvious and was nearly the reason not to do it.**
`_truths` takes its units from the **globally-first** record with outcomes, so a shard computing
truths from its own interleaved subset would pick a different record, different units, a different
truth, and the comparison would be gone. **But the expensive half takes no units:**
`counterfactual_unit_weeks` returns the full control and treatment maps and
`average_treatment_effect` filters them afterwards. The generation moves; the choice of units does
not.

```
id            T00L
title         The world cache's digest hashes a file; the dependency is a function
branch        evals/the-digest-cannot-tell-collect-from-window-mean
depends_on    T00G
blocks        T00K
closes        Every cached artefact is produced by outcomes.collect or reference.compute, and
              source_digest() hashes those two files WHOLE -- so editing a function that
              produces nothing cached throws away six families of artefact. Measured: 11
              function definitions across the two files, 6 producers and 5 consumers, no
              function on both sides. The consumers move to grouped_metric.py and
              walked_metric.py, after which hashing outcomes.py and reference.py whole is
              correct. DEPENDS_ON, key() and source_digest() are untouched -- the fix makes the
              files honest rather than the instrument cleverer.
out_of_scope  Widening DEPENDS_ON, and TIMEOUT_SECONDS. T00G filed a widening as out of scope
              because a narrowing and a widening in one diff cannot be separated by
              measurement; the same argument applies here. The budget is re-set AFTER this
              lands, from a re-measurement, because every observation of it today is of a form
              this task removes.
stop_at       When mutation 07 runs in its siblings' band on CI, published as a measurement
              beside the five observations of its expensive form: 528 / 747 / 779 / 806 / 826
              and one killed at 900.
review        yes
status        open   <- the measurement below is in; the branch is not merged
```

**The measurement, on run 33621267184.** `07` ran in **58s**, `bit`, against the five observations
of its expensive form -- `528 / 747 / 779 / 806 / 826` and one killed at `900`.

**It is the median of its siblings, not merely nearer them.** The eight now read
`34 / 55 / 58 / 58 / 60 / 66 / 70 / 93`, and `07` is no longer the slowest mutation in claim 2 --
that is `the-power-check-is-judged-on-the-variance-the-design-assumed` at **93s, 10% of the 900s
budget**. *Nearer* would have been consistent with the fix merely helping; the median is consistent
with the anomaly being gone.

**Two observations, and two is not a spread.** Run 33621267184 gave **58s** and run 33627230673 --
the follow-up commits on this branch -- gave **59s**. They are **1.02x apart**, against the
expensive form's **1.56x across five** completed runs plus a kill.

**That is suggestive and is not evidence.** It is consistent with the variance having lived in the
regeneration rather than in the mutation's own work, which is what the diagnosis predicts -- and
**two points cannot establish a distribution**, which is the day's whole lesson arriving on the
number that closes it. `the-power-check-is-judged-on-the-variance-the-design-assumed` was the
slowest mutation at **93s in both runs**, which is a second thing that did not move.

Anything stronger needs `workflow_dispatch` re-runs on one sha, and none were taken.

**The job-level figure is deliberately not the measurement**: `claim-2 combine` went 47m04s ->
37m19s across two runs on two runners with different cache states, a difference of ~585s where the
mutation alone accounts for 748s. That is spread in everything else. The clean number is the
per-mutation one, taken by the same instrument on both sides.

**And one property worth recording because it is the first of its kind today.** The two follow-up
commits on this branch -- the attribution correction and the parent finding -- cost it **one** CI
run rather than the ~1.25 every other branch has paid, because the coin toss they would have faced
is the thing this branch removed. **It is the first change today that made the next change cheaper
rather than more expensive.**

```
id            T00K
title         Shard claim 2's mutations
branch        evals/mutations-sharded
depends_on    T00H
closes        `evals/gate_proof`'s nine runs — one baseline and eight mutations — stop being
              strictly serial. They are the other half of `make claim-2` and, measured on the
              runner from the timestamped log of job 99702683729, they are 22m01s of its
              50m44s: harness 01:18:52 -> 01:47:34, mutations 01:47:34 -> 02:09:36.
              The units are NOT near-equal and the balance interleaving buys is not free:
              measured on run 33600284036 they span 32-87s against 806s, a spread of 25x, so
              one unit alone floors the phase. After T00L the spread is 32-87s, about 2.7x --
              better, and still not near-equal.
depends_on    T00H, T00L
out_of_scope  Anything about the ledger's ownership rule, which T00H already answered.
stop_at       When the sharded mutation report equals the unsharded one exactly.
review        yes
status        open
```

> **`closes` restated 2026-09-02 by T00L.** It read *"Nine near-equal units, so the balance
> interleaving had to buy for the draws is free here"*, and the near-equality was never measured.
> It is 25x. The prior wording stays per doctrine rule 4 and the delta is the finding: **a
> scheduling argument was made from an equality nobody had checked**, in a task about scheduling.
>
> **And `T00L` is now a dependency rather than a sibling**, because sharding's floor is the unit
> `T00L` fixes. Stated as seconds rather than as a ratio, because the ratio misleads here and did:
> serial the phase is ~1213s and perfectly sharded it is ~806s, so sharding saves **~407s today**
> and **~373s after T00L** -- the *ratio* improves 1.5x to 5.3x while the *wall clock saved falls*,
> and CI bills minutes.
>
> **Which leaves a question this entry now carries openly, and T00L's own run sharpened it from
> a projection into a measurement.** On run 33621267184, with T00L landed:
>
> ```
> make claim-2-combine                    2229s   37m09s
>   the eval, --combine                   1432s   23m52s   64%
>   gate-proof --claim 2                   797s   13m17s   36%
>     of which the eight mutations         494s    8m14s   22% of the job
>   T00K saves at most                     401s    6m41s   18% of the job
> ```
>
> **So: is `T00K` worth its own review for a measured 6m41s, against an unmeasured 23m52s
> sitting beside it?** Nothing has been done to the `--combine` phase and nobody has measured
> what is inside it. Sharding the mutations now optimises the smaller half -- **which is the
> error this entry's own `closes` records the laptop nearly making about which half to shard**,
> arriving a second time because the two halves swapped places when T00L landed. Nobody has
> decided it, and a task whose value is now the smaller of two numbers should say so before
> somebody builds it from momentum.

**And the reason this is a separate atom rather than part of T00H.** The two halves have different
mechanisms and different failure modes, and folding them together would mean one branch in which
two measurements cannot be separated — the same argument this repository has already made twice
about a widening and a narrowing in one diff. **T00H delivers a number and so will this.**

*One thing the laptop would have got wrong, recorded because it nearly did.* Measured warm on a
fourteen-core laptop the mutations are **59%** of the target and the harness 41%; measured on the
four-core runner the harness is **57%** and the mutations 43%. **The ratio inverts**, so a session
choosing which half to shard from its own machine would have chosen the wrong one. It is
`CLAUDE.md`'s hardware rule arriving in a decision about which work to move rather than about a
number.

**And the standing limit, which is the reason this atom is shaped as two halves.** What the ruleset
requires is a fact about the forge that no file in this tree carries, `make check` cannot read, and
no amount of reading `ci.yml` reveals. `docs/reviews/phase-1.md` §2d is what it costs to assume
otherwise: the ruleset required `gate`, the claims left `gate` for their own matrix, and **a pull
request with a red `claim-2` merged** for two days with nothing able to say so. A merge queue
configured wrong fails in the same direction — a required context satisfied by a run that did not
test the merged result — so (2) is verified against the API and never against a memory of it.


---

## Phase 1 — the core, the contracts, and the hardest claim

Remaining atoms. Everything below has an ancestor that has already landed (see `PLAN.md`).

```
id            T001
title         core/ — design form, feasibility, assignment, four checks, estimator
branch        core/design-experiment
depends_on    —
closes        src/holdout/core/design/ and experiment/ as pure functions over plain data,
              importing no SDK, no engine, and not PyYAML or jsonschema. The design-based
              estimator is a difference of means; the inference is a permutation test under the
              same re-randomisation restriction, or a covariate-adjusted estimate. Unit tests
              AND a composition test green — no core module is tested only alone.
out_of_scope  The generator, the A/A harness, any claim-N target.
stop_at       After the core modules and the composition test; before any eval is wired.
review        yes
status        closed
```

**What it landed.** `src/holdout/core/design/` (the nine-field form, the eight refusals, the
sizing arithmetic) and `src/holdout/core/experiment/` (the keyed-hash lottery and its seal, the
standardised difference, exposure, contamination, Lin's adjustment with a studentized permutation
test and an interval that inverts it, and the two readout moments). Plus a new contract family,
`contracts/design/inference.yaml`, and one new code in the closed vocabulary,
`NO_ADMISSIBLE_ASSIGNMENT`. 510 tests to 747; `make check` green; `make claim-1` still 9/9 with
13/13 mutations biting. What each piece settled is in `PLAN.md`'s prose.

**Three corrections to the SPEC, made in the code rather than worked around**, and a fourth that
was an internal contradiction. The seed is supplied, not generated — `core/` reads no random
source, and a seed the engine invented is a seed nobody committed to in advance. The covariate
*values* had to join the signature, because the screen cannot run on a contract that only names
the columns. A one-sided quantile was used and never declared, so it joined the contract with its
own source. And `UNITS_ALREADY_COMMITTED` was listed both as an automatic exclusion and as a
refusal; it is the refusal, because the contract's own remedy says *exclude the committed units*,
in the imperative.

**The finding T003 has to act on before it starts.** At the scenario's shape — 100 stores, the
declared 20% holdout, the declared 0.10 tolerance over five covariates — the re-randomisation
screen accepts roughly **one draw in a thousand**, so a reference set inside the declared attempt
budget holds single figures and the smallest attainable p-value sits above the declared α. **No
experiment at that shape could ever report a significant effect**, which would make W6's
false-refusal rate 100% for a reason unrelated to the estimator. Recorded as a deferral in
`docs/DECISIONS.md` and measured by
`tests/core/test_assignment.py::test_the_screen_accepts_about_one_draw_in_a_thousand_at_the_scenario_s_shape`,
so it is a number in the suite rather than a paragraph. Choosing the remedy — a much larger
budget, a wider tolerance, a larger holdout share, or stratified randomisation instead of
rejection sampling — is a contract or design change and belongs to T003, not to a session whose
scope was the core.

```
id            T002
title         The generator and the six adversarial worlds (W1–W6)
branch        corpus/adversarial-worlds
depends_on    T00A
closes        corpus/world/ at 100 stores x 3 fresh categories x 8 months (~36M POS lines), with
              NO import path to src/holdout/ (now enforced by the T00A hook). Injected truth in a
              sealed file the grader opens only after the readout. W6 (a real effect is present)
              exists as a first-class world beside W1.
out_of_scope  The estimator; the independent measurement of truth on the metric (T003).
stop_at       When the six worlds produce data and the no-core-import barrier holds.
review        yes
status        closed
```

**What it landed, and the two places it went beyond the line above.** The generator is a **stream**
rather than a directory of files: a world is a pure function of `(world, seed, scale)`, generated
store-major with every draw keyed on what it is a draw *about*, so nothing is committed, a
restriction to three stores is a genuine window onto the same world, and — the property T003 needs
— **no key contains the arm**, which makes the all-control counterfactual differ from the observed
world by the treatment effect and by nothing else. `write` materialises gzipped CSV rather than
Parquet, recorded as a deferral with the S3 bulk load as its unlock.

The seal is `corpus/world/seal.py`. It holds **behaviour** — the two schedules, the exposure that
failed, the decay — and explicitly not a number about money, because the effect on the metric does
not exist anywhere until it is computed. It opens only against a readout that is already on disk and
records the opening in an append-only ledger. Its limit is asserted by a test that performs the
coordinated forgery and requires it to *succeed*, rather than described in prose beside the code.

**Two things were found by measuring rather than by reasoning, and both would have passed a green
suite.** Store placement was probabilistic, and at the smoke scale it produced **zero** neighbour
pairs — so W2 was structurally unable to interfere and every test about it would have passed
vacuously. And W2's direction was hard-coded as *control loses trade to treatment*, from the
assumption that a candidate markdown policy cuts deeper; the candidate cuts **shallower**, because
an aggressive ladder measured against its own counterfactual destroyed 5–25% of category margin
through reference-price habituation. A world whose interference points the wrong way still breaks
SUTVA and would still have been detected downstream, which is exactly why nothing would have caught
it. The test now hands the neighbour a shallower ladder and then a deeper one, both built inside the
test, and requires the watched store to move both ways.

**Deliberately not done here:** the world knows nothing about the guardrail envelope, so it produces
shelf prices the system would refuse. That is what independence costs and it is recorded as a
deferral rather than quietly fixed.

```
id            T002B         <- unblocks T003
title         Stratified randomisation — the restriction the lottery draws under
branch        experiment/stratified-randomisation
depends_on    T001
blocks        T003
closes        The inherited condition below is settled, and settled by the mechanism rather
              than by a number: assignment draws WITHIN strata, so every candidate is
              admissible and the reference set fills to the contract's B instead of starving.
              Specifically:
              (1) src/holdout/core/experiment/strata.py — strata matched on a composite
                  distance over the declared balance covariates, one control per stratum,
                  with categorical levels held by proportional allocation to cells. A pure
                  function of the matrix; it never sees the seed.
              (2) assignment.py draws within them from the committed seed and returns None —
                  a refusal, not an exception — where no stratification gives every stratum
                  both arms. The strata are on the seal and inside its digest.
              (3) balance_tolerance_smd becomes a readout check and stops being a design
                  screen. That is a RESTATEMENT of contracts/design/inference.yaml, not an
                  edit: v2, with the prior meaning recoverable in the file (doctrine rule 4).
                  max_assignment_attempts is restated the same way — it budgeted the screen's
                  rejections and now budgets the reference-set scan.
              (4) The reference set does NOT change: stratification is a restriction, and a
                  permutation within strata is "under the same restriction" exactly as the
                  screened reference set was under the screen's.
              The number that closes it: at the scenario's shape — 100 stores, the declared
              20% holdout — the reference set reaches the contract's B = 1000, so the
              p-value floor 2/(1+B) sits two orders of magnitude under alpha = 0.05.
out_of_scope  The A/A harness, the six worlds, any claim-N target — all T003. The three
              rejected remedies: a larger attempt budget (~400 hours of screening), a wider
              tolerance (~0.41 SMD, which is no balancing at all), and a 50/50 holdout
              (acceptance only reaches ~1/800). Each is recorded as rejected rather than
              silently passed over.
stop_at       When make check and make claim-1 are green and the reference set fills at the
              scenario's shape, measured in the suite.
review        yes
status        closed
```

**Why a task of its own rather than the first hour of T003.** The remedy is a design change
to `assignment.py` and a restatement of a contract — two things whose review question is
*did the restriction move honestly*, which has nothing to do with whether an A/A harness
measures a rate correctly. Folding it into T003 would have put a contract restatement inside
a branch whose closing condition is a number, and the number would have been the thing
reviewed.

**What the measurement says, in both directions.** The reference set now fills, which is what
the deferral asked for. What stratification does *not* buy is a draw that always passes the
readout's balance check: with 20 controls a covariate the others carry no information about
keeps a sampling spread near the tolerance, so a minority of healthy stratified draws are
refused as `IMBALANCED_PRE_PERIOD`. On a roster whose covariates hang together the way a
chain's do, a clear majority pass; on a deliberately orthogonal roster most do not, and
`tests/core/test_assignment.py` measures both rather than asserting the comfortable one. The
direction is the honest one — a refusal, never a wrong number — and the published rate is
T003's to produce.

```
id            T003          <- closes Phase 1
title         A/A harness (K=200), reference implementation of truth, make claim-2
branch        evals/aa-harness
depends_on    T000, T001, T002, T002B, T00D, T00E
closes        make claim-2 green. Four numbers published, not a tick: the false-positive rate on
              A/A against the declared alpha (one-sided binomial at a stated level); the
              false-refusal rate on W6; estimator bias; and CI coverage (~95% over K runs of W6).
              Every draw runs the WHOLE system, not just the estimator. A deliberately slow Python
              reference implementation of truth-on-the-metric agrees with the dbt/SQL path with no
              tolerance, and doubles as a fourth independent check of claim 5.
              Also: CI's gate job carries a temporary timeout of 25 minutes, raised from 15 by
              T000 on measured runner variance. Claim 2 adds K=200 seeds and six worlds to the
              same job, so the answer is parallelising the mutations or splitting the claim
              targets into their own jobs — NOT a third increase — and the limit comes back
              down in the same change. See the deferral in docs/DECISIONS.md, which expires
              2026-09-30.
out_of_scope  Claims 3/4/7 (their own tasks); preview-audit.
stop_at       If the A/A test does not stand against alpha — STOP and notify the author. Nothing
              is built on top of it. That is the whole point of putting it first.
              Do not raise timeout-minutes again. If the job does not fit, the job is wrong.
review        yes
status        closed
```

**What it landed, and the numbers it closes on.** `make claim-2` is green: **13 checks, 456 draws
across six worlds, eight planted mutations and eight that bit.**

```
U1  aa-false-positive-rate     8/200 = 4.0% significant against alpha=5%
                               one-sided binomial p=0.7867 at level 0.01
U3  w6-false-refusal-rate      0/200 refused by the machinery, ceiling 10%
U4  w6-coverage                163/170 = 95.9% against a nominal 95%
U5  w6-estimator-bias          +0.59 EUR against a standard error of 1.02, over 170 draws
```

Published beside them, with no threshold on it in this phase: **W6 refused
`IMBALANCED_PRE_PERIOD` on 30/200 = 15%** of draws. `docs/DECISIONS.md` says what that rate is a
function of and what would give grounds to gate on it.

**Every draw runs the whole system** — the pre-period, the nine-field form, the eight design
refusals, the automatic exclusions, the committed seed, the stratified draw, exposure read from the
corpus's acknowledgements, the four validity checks and the readout. Two hundred draws are
affordable because a store's events are a function of its own arm outside W2, so two counterfactual
generations buy every lottery; `U11` checks that against the generator both ways and W2 must
disagree.

**Three worlds' declared behaviour changed, and each was a measurement rather than an argument.**

- **W5's tail was on the wrong thing.** `quantity_tail_alpha` was a Pareto index on a basket line,
  and the metric aggregates about sixteen thousand of them: W5's standard error at the readout came
  out *below* W6's — 8.08 EUR against 11.51 — so the world whose declared pathology is variance had
  less of it than the world with none. The tail moved to the **store-day** and to the **second half
  of the calendar**, because a pathology present in the history a design is sized on is variance the
  calculation *assumed*. Pre-period sd is now identical to W6's and the period's is 4.4x it.
- **W2 states no number, and it is luck.** Every draw refuses `POWER_NOT_REACHED` with the neighbour
  pairs declared and withheld alike: the spillover inflates the residual variance past what the
  power check will admit. There is no interference detector anywhere in the system, so at a lower
  spillover it would report a contaminated number in silence. `U6` publishes the pair of refusal
  rates and `docs/DECISIONS.md` carries the limit with the world that would demonstrate it.
- **`CLAUDE.md`'s rule about sentences gained a third limb**, because W2's line was wrong twice: once
  against the code and once against what the world produces when it runs. *A sentence is written
  against the function that would make it true — and against the measurement of what comes out.*

**One core optimisation, guarded by equality.** A readout on a roster of 269 at B = 1000 went from
32 s to 5.3 s: the permutation statistic is a polynomial in the shift, and an arm's `XtX` is the
whole minus the other arm's where the two partition the design. Both are algebra over `Fraction`, so
`tests/core/test_estimator_interval.py` keeps the refitting implementation verbatim as an oracle and
asserts **bit-identical** bounds on cases the corpus drew.

**The CI restructure, and the gate is back to 15.** Four jobs where there were two: `gate` runs
`make check`, the contracts and the expiry check; `discover` reads the claim targets out of the
Makefile; `claims` runs one per runner with `fail-fast: false`. The discovery property is untouched
— the targets are still never listed in the workflow. The 25-minute deferral is closed and the new
job's budget is a dated one.

**And world generation left the mutation loop.** A world is a pure function of `(world, seed, scale)`
and a mutation changes eval code, so the ten runs of `make claim-2` generate the worlds once. What
invalidates that is a digest of every file the artefact was produced by, not a list somebody
maintains — `tests/evals/test_uplift_cache.py` drives both directions by editing real files.

**Two mutations were re-aimed on measurement and one gate-proof constant moved.** The half_up
mutation on a grain cell could not bite — every term of the metric is an exact integer number of
cents, so the two rounding modes are the same function there; it moved to the window mean, which is
the only division either implementation performs, and `U10` now compares both. And
`gate_proof.engine.TIMEOUT_SECONDS` went from 300 to 900: a mutation that changes the corpus
*legitimately* regenerates every world, which is the cache working rather than failing, and under
300 that was recorded as `CRASHED`.

**And the rule-id map.** `evals/guardrail/reference.py` now writes the core's six `Bound.rule_id`
strings down a second time, which is what makes `G10` able to disagree. T008's `floor.yaml` rule-id
rename will therefore turn `G10` red on **both** directions at once until `reference.py` follows;
that is the gate working, and T008 must move the two together in one change.

```
id            T004
title         evals/assignment/ + gate-proof — make claim-3
branch        evals/assignment
depends_on    T000, T001, T002B
closes        make claim-3 green. Assignment from a committed seed, exactly reproducible. The one
              door with no key — a test that no unit changes arm after its first observation, by
              anyone including an approver. The gate-proof mutation this claim owns bites by name.
out_of_scope  The other claims.
stop_at       After claim-3 and its mutation refuse the planted break by name.
review        yes
status        closed
```

**What it landed, and the numbers it closes on.** `make claim-3` is green: **10 checks over 36
declared configurations, and nine planted mutations of which nine bit.**

```
A1   4129/4129 units agree with an independently implemented lottery, over 30 configurations
A5   3/3 interpreters agree on one fingerprint of every stratum and every arm
A6   273/273 attempts refused · 12 declared in-process routes, 9 of them per seal
A7   30/30 forgeries refused, over the 15 designs of 30 where a better-balanced candidate
     exists inside a 24-candidate scan — careless and careful each
A8   72/72 caught by the contamination check · 72/72 named by the readout
A9   24/24 clean readouts pass · 9/9 substituted readouts refuse CONTAMINATED_ASSIGNMENT
A10  RFC 7693 Appendix A reproduced · 176/176 of a declared sweep against hashlib
```

**The trap was named before any code was written, and it is not the one the other claims carry.**
Verifying that a draw is reproducible by running the draw again is a deterministic function
repeated: `draw` reads no clock, no environment and no random source, so it agrees with itself —
and would agree just as loudly on a lottery that ignored the committed seed, or one that handed the
holdout to the lowest-numbered store in each stratum. So the independence arrives by three other
doors, each named on the check that uses it:

- **a second implementation** — `evals/assignment/blake2b.py` is BLAKE2b written out from RFC 7693
  in Python, and `reference.py` recomputes the draw and the digest over it with its own framing, its
  own rank arithmetic and its own selection. `A10` drives that hash against the vector **RFC 7693
  Appendix A** publishes, which is the only expected answer in this eval chosen by somebody who has
  never seen the repository;
- **the per-unit path** — `A3` re-derives a store's arm the way a readout a month later has to, from
  the seed, the candidate index and that store's own stratum, never touching the seal;
- **another interpreter** — `A5` recomputes the whole grid in subprocesses under three declared
  `PYTHONHASHSEED` values, which is the only way to see a tie broken by set-iteration order. The
  mutation that makes `strata._hardest_to_match` scan its unmatched set unsorted is invisible to
  every in-process repetition and bites here.

**The incentive to fish is measured, not asserted.** Anyone holding the committed seed can generate
every candidate and see which one flatters the design. In this grid a better-balanced candidate
exists for **15 of 30** designs, improving the worst standardised difference by **0.2422** on
average against a declared tolerance of 0.10. `A7` substitutes it — including as the careful forger
who recomputes the digest so the seal agrees with itself — and `A9` drives the substitution through
the whole of moment 3 and reads `CONTAMINATED_ASSIGNMENT` off the refusal.

**The finding, and it closed in the same branch.** As first measured, `contamination.check` did
not see a store erased from the assignment table: it derives the roster it walks **from the arms
it is checking**, so a control store deleted with the digest recomputed to match left nothing to
compare — it reported the assignment intact and `sealed()` agreed. 24 of 72 erasure routes, and
what refused them was `readout.close`'s stray-outcome guard one function later, holding only
while the erased store still reports an outcome. The eval published the split as
`48/72 = 66.67%` and `docs/DECISIONS.md` carried the rest as a deferral.

**Oversight level 2 found the deferral wrong rather than the measurement.** `check` already
computes `redraw(seal)` and then walks `seal.roster`, one line apart — and `redraw`'s key set
*is* the roster the lottery was drawn over, taken from the committed **strata**, which
`digest_for` commits as their own section. `frozenset(drawn) - frozenset(seal.roster)` names the
erased store. The deferral's argument — that closing it needed a contract and signature change —
was written against an imagined fix rather than against the function that would make it true.
No argument was added and no signature moved: `Contamination` gained a `dropped` field and
`is_clean` a clause. The strata are a **sound** witness rather than a handy one, because deleting
the unit from them as well changes which unit holds the smallest rank in that stratum and
`reassigned` fires instead.

`A8` now asserts **both** layers, per route, against a phrase each route declares in advance —
either alone would have hidden this, and a readout that declined `POWER_NOT_REACHED` on an
emptied assignment has caught nothing. Two mutations hold the pair open, and the ninth
(`the-contamination-check-trusts-the-roster-it-is-handed`) reverts the line that closed the gap
so it cannot be removed in silence. `docs/DECISIONS.md` keeps the deferral **and** its
restatement: the delta is the finding, because a deferral is an assertion about what the system
does wearing a cost estimate instead of a verb, and `make expiry` checks only that an unlock
condition is present, never that it is the right one.

**One mutation survived and the eval was fixed, not the assertion.** The break that walks the
covariate matrix in arrival order reported `SURVIVED` against `A4`, and correctly: `strata_of` is
order-independent at every point by its own sorting, not because `CovariateMatrix.units` is sorted.
What the break does move is `covariate_digest`, so `A4` now compares the whole record the seal
commits to — strata, arms, covariate digest and the standardised differences — and it bites.
`evals/assignment/README.md` §6 keeps the account.

**Two shapes reached from the corpus that the contract's own values cannot.** At the declared 20%
holdout share no roster this corpus produces can reach the `None` the design engine turns into
`NO_ADMISSIBLE_ASSIGNMENT` — a 20% control arm always leaves five units to a stratum — so the grid
sweeps the share and six configurations reach it at 70%. And the rosters are the ones that survive
`feasibility.neighbour_exclusions`, not the store counts. Over the eval's own two chain seeds:
100 stores leave a roster of **65 to 83** depending on how clustered the world is, and 320 leave
**218 to 269**.

**Cost.** `make eval-assignment` is about 17 s; `make claim-3` is 3 min 14 s cold, which is
ten runs of the eval — one baseline and nine mutations. A chain is placement arithmetic rather than a
simulation, so there is no world cache and no smaller mutation configuration to keep in step.

**What T002B changed about what claim 3 has to prove.** "Exactly reproducible" now takes **two**
committed things, not one: the seed, and the **strata** the lottery drew within. The strata are a
pure function of the covariate matrix, so they are recomputable by anyone — but only from the
matrix as it stood at design, and a restatement moves that matrix. Both are on the seal and both
are inside its digest, so the eval has to reproduce the assignment from the seal's own record and
not from `strata_of` re-run on today's covariates: the second would pass on a day the first should
have gone red. That is the same shape as the readout's balance check re-measuring rather than
re-reading, one moment earlier.

```
id            T005
title         evals/censoring/ + gate-proof — make claim-4
branch        evals/censoring
depends_on    T000, T001, T002
closes        make claim-4 green. A stock-out is never read as zero demand; the correction is
              validated on a held-out segment with full shelf availability. The simulator that
              generates censoring does NOT share the model that corrects it. The gate-proof
              mutation this claim owns bites by name.
out_of_scope  The full training pipeline (Phase 2, T014).
stop_at       After claim-4 and its mutation.
review        yes
status        closed
```

**What it landed.** `src/holdout/core/demand/censoring.py` — the reading, the availability curve and
the correction — plus `evals/censoring/`, nine mutations and `make claim-4`. Green at **12/12 checks
and 9/9 mutations biting**, about 58 s end to end on a fourteen-core laptop; the eval alone is 5 s,
so it needs no world cache and does not have one.

*Where the independence is.* The curve is fitted on store-days in the first 60% of the calendar on
which the shelf **held**, and graded on store-days in the last 40% on which the shelf held —
censored on purpose at a declared grid of hours, with the hours after withheld. **The truth is a
receipt total the corpus emitted**, never a latent intensity the generator knows, so the grader
never opens the process that produced the data. The corpus's stock-outs come out of the
simulation's replenishment arithmetic, written for claim 2 before this claim had a line of code, and
W5 is in the set of three worlds because its heavy-tailed store-days are the hardest input
available. `tests/evals/test_censoring_instrument.py` refuses any import of `corpus.world.demand`
from the eval and any import of `corpus` from the correction, in both directions.

*The figures it closes on.* 16,942 of 80,640 store-days emptied (21.0%) — the one corpus figure;
the rest are measured on held-out days censored **on purpose**, where the withheld total is known.
There, reading the truncated number as the day's demand understates by **6.0% at the last trading
hour and 91.4% at the first**; the reconstruction lands within **0.1% at a share of 0.94** and comes
out **36–40% high at 0.06**, which is selection — the same expansion conditioning on nothing lands
at −1.5% to −0.6%, and the pair is published. 176,266 reconstructions and 48 hourly boundaries
compared against a second implementation as integers with no tolerance: **0 disagreements**. 51,883
censored days answered with a lower bound and no number.

*Two things the measurement corrected, and neither was visible in the code.* First, `checks.py`
declared two censoring shapes unreachable from the corpus and one of them is reachable — W5 empties
a shelf inside the first trading hour three times in 26,880, having sold up to three units. Found by
`gate-proof` reporting `CRASHED`, because `DemandEstimate` refused to be built with zero units over
the two that day had sold. Which shapes come from the corpus is now measured and published rather
than reasoned. Second, `C6` offered `fit` a censored day **on its own** and the mutation aimed at it
reported `SURVIVED` — a `fit` that skipped censored days still went red, but by a different guard.
*A gate can only be shown to bite where it is the gate that refuses.* The eval was fixed, not the
assertion, and `CLAUDE.md`'s guard table has a fifth row.

*What it also moved.* `CLAUDE.md`'s claim-4 row is restated: the corpus produces no censored
store-day that sold nothing, so the literal zero is the limiting case rather than the typical one —
the typical one is understatement on a fifth of all store-days. And the sentence *"nothing catches
this for hooks, barriers, checks or tests"* is restated: `gate-proof` does catch it for an eval's
checks, where a mutation is aimed at that check by name.

*What is deferred, with unlock conditions in `docs/DECISIONS.md`.* No threshold at which a
reconstruction stops being usable — that number would have to come from real stock-outs and this
eval constructs its own; the endogeneity of a real stock-out, stated rather than measured; one
pooled curve per world; and the correction having no consumer until T014's training pipeline and
T010's silver layer compose it.

*One number left to read off CI.* `claim-4` joins the `claims` matrix, which runs on the temporary
90-minute timeout `docs/DECISIONS.md` already carries with a date. Measured at **58 s, serial, at
99% CPU** — so core count is not the variable and the local figure is close to what a runner will
see; it is two orders of magnitude under the budget either way, and nothing is changed here. The
cold figure from CI is what that deferral's next measurement should record beside claim 2's,
because a measurement taken on the hardware that will meet the number is the only kind this
repository accepts.

*Read off the runner, 2026-08-29:* `claim-4` is **1m51s and 2m31s** cold on `ubuntu-latest`, over
two runs of the same commit — a 36% spread between runners, which is the same order as the ~40%
this repository has already measured and is why a budget is never set from a single run. Against
the matrix's 90-minute timeout that is a factor of 36, so `claim-4` puts no pressure on it. The
deferral itself stays claim 2's to close: `claim-2` is what the 90 was sized on, at 50m26s and
51m24s on the same two runs.

```
id            T006
title         evals/oversight/ — make claim-7
branch        evals/oversight
depends_on    T000, T001
closes        make claim-7 green. The decision key carries no customer dimension, and a test goes
              red if one appears — on every type on the decision path, over the key's exact field
              set. Proved here because it costs minutes and needs nothing else.
out_of_scope  —
stop_at       When the test covers the whole field set on every decision-path type.
review        yes
status        closed
```

**What it landed, and the number it closes on.** `make claim-7` — twelve checks, seven mutations,
all seven bit — and one measurement that is the whole reason the task was worth doing.

The task line said *a test goes red if one appears*. That test existed and was good: an exact field
set for every type on the decision path, plus a tuple of person-shaped substrings as a net under it.
What nobody had asked was **who wrote the words in the net**. They were written by whoever also
wrote the field names they were checking, which is `CLAUDE.md`'s most frequent defect exactly — *a
guard tested by its author is tested in the shape the guard already handles* — with no prose beside
it to be wrong and no gate behind it. **Claim 7's row in the seven-claim table was the one row with
no trap written beside it**, and that is where it sat.

So the words came from outside. `corpus/real/` now carries a second corpus under the same four
rules as the prices: **156 schema.org properties** whose domain or range includes `Person` (release
30.0, pinned — *latest* is not a provenance) and **99 Presidio PII entity types** (pinned at commit
`eb93051b`). Both extractions mechanical and total, both in the publisher's own spelling, nothing
curated — `DATE_TIME`, `brand`, `award`, `height` and `weight` stay on the lists, because the moment
this repository decides which of somebody else's names count, the inputs are being chosen here
again. Between them they yield **317 names**, planted one at a time on each of the 56 types:

```
attacks planted                          17,752
  refused by the closed field set        17,752
  refused by the hand-written word list   1,960   (35/317 = 11.0% of the names)
```

The list misses `family_name`, `given_name`, `nationality`, `job_title`, `spouse`, `buyer`, `owner`,
`recipient` and 274 others. `O7` turns that into a gate rather than an anecdote: **no attack may
ever be refused by the word list alone.**

**Where the task went wider than its `closes` line, and why each was necessary rather than tempting.**
*`O5`* — a person does not have to arrive as a *field*. A `customer` parameter on `dispatch_to_shelf`
is invisible to every field-set comparison ever written, so the eval parses the package's source
text and reads every identifier it defines: 1,181 of them. *`O10`* — nor does one have to arrive in Python.
`ladder_policy@v1.yaml` becoming idempotent per customer says, in as many words, that a decision is
taken per customer, and it compiles into a dbt model, a SQL function, the agent's tool definition and
the readout query with **no type moving at all**. Those two are the mutations that earn their checks.
*`O9`* asks the question at runtime instead of by reading — 951 attempts to construct, assign and
`replace` a person onto a key, all refused. *`O11`* is the second implementation the shape requires:
field sets parsed from the text against field sets read off the live objects, sharing only `tokens`.

**Two rules were restated by being run against.** `gate-proof`'s independence argument said *the
planter edits `src/holdout/`*; claim 7's most valuable mutation edits a contract, and a planter
confined to `src/` could not have written it. What matters is not which directory the planter may
touch but which one it may **not** — `ops/` and `corpus/real/` are the detector and are never
targets, and `engine.py` and the README now say so. And `evals/README.md` gained the half of the
shape that had been true since `tests/evals/test_ledger.py` and never written down: **a check with
no mutation names the reason it cannot have one, and is broken deliberately somewhere.** Six of the
twelve are in that position, all six armed by `tests/evals/test_oversight_instrument.py`.

`ops/personhood.py` now holds the registry and the word list, with `tests/core/test_decision_key.py`
and the eval as its two callers — the arrangement `ops/isolation.py` already had for the corpus
barrier. `ops/` joined `gate_proof`'s copied workspace for the same reason.

**Two deferrals, both real.** Claim 7 is proved over `holdout.core` and the contracts and nothing
else exists yet — a scan against a `pipelines/` that does not exist is a check with nothing to
check, so it unlocks at T011. And the vocabularies are pinned, so nothing notices a name published
after 2026-08-29; that ages the *net* and never the *guard* — `O2` reads no names at all — and it
expires 2027-02-28.

**No new number in configuration.** `make claim-7` is 37s on the author's laptop and **under two
minutes on the four-core runner, on every CI run so far**, in a matrix job whose 90-minute budget
was measured for claim 2. The measurements span **1m7s to 1m45s** — and how many of them there are
is deliberately not written down, because that count grows with every push and stating it would
guarantee this sentence is stale again by the next one.

It is a bound rather than a point because the point was wrong three times, each for a different
reason, and the third is the instructive one. 1m8s was measured before the seventh mutation existed
and left standing after it landed. "1m33s and 1m41s" stopped being true when merging claims 3 and 4
grew the registry — every type added to it adds 317 attacks. And "1m32s to 1m45s" was falsified by
the very next run coming in **faster**, at 1m7s: a 40% spread on work that had not changed, which is
the same runner variance T000 measured at 11m00s against 15m16s on an identical commit.

So the quantity has two independent reasons to move — the eval grows, and the runner varies — and a
tight range around it is a point estimate wearing a wider hat. **What is load-bearing is the distance
to the budget.** The span is published as evidence for the bound, not as a second assertion. A target two
orders of magnitude under a timeout asserts nothing about that timeout, and the runner figure is the
measurement taken on the hardware that meets it rather than a projection from the laptop.

**What oversight level 2 sent back, and what it cost.** Four blocking findings, and the review did
the one thing this branch could not do for itself: it re-downloaded both vocabularies, wrote its own
extractor without touching `corpus/real/fetch.py`, and reproduced both committed CSVs **byte for
byte** — 156 and 99, all six MANIFEST digests recomputed, 317 derived independently, and every
ALL_CAPS token in the Presidio source that is *not* in the corpus accounted for (67 acronyms in
prose; `PH_MOBILE_NUMBER` and `TR_PHONE_NUMBER`, both inside a description cell as configuration
examples). **The extraction is mechanical. Nobody filtered.** That is the finding the whole claim
rests on and it could only be established by somebody who had not written the extractor.

Then the four:

*(1) The prose named two names the word list actually catches.* Four documents said the list misses
`telephone` and `personnummer`. `PERSON_SHAPED` contains `phone` and `person` and matches by
substring, so it catches both — and both are among the 35 the eval reports as caught. **The
aggregates were right the whole time; the illustrations were picked by reading the lexicon rather
than by asking `ops.personhood.person_shaped`, which is the function that would make the sentence
true.** It is this branch's own subject, one layer up, in the branch about it. The exemplars are now
pinned in `tests/evals/test_oversight_instrument.py` in both directions, the way
`test_guardrail_instrument.py` pins claim 1's 716 and 6,650.

*(2) `O3` printed "every type" and exempted every type whose name begins with `_`.* Inherited from
the version of the rule that lived in the test, where it read as hygiene. What it did was leave one
spelling that walks past the guard: the reviewer renamed the class mutation 03 plants and watched it
survive. The exemption is gone, the estimator's three private types are written down like everything
else (registry 46 → **49**, and **56** after merging claims 3 and 4), and `07-the-second-key-arrives-with-a-private-name.yaml` plants the
underscored break so nothing but the code decides whether the hole is shut. **This is a guard tested
by its author, inside the branch whose subject is guards tested by their authors** — `CLAUDE.md`'s
table carries it as its own row.

*(3) The deferral said the scan covered the whole system, and `src/holdout/contracts/` — fifteen
modules — was outside it.* `reference.CORE` stopped at `core/`'s boundary, so a `customer` parameter
on `compile_agent_tool`, the exact shape mutation 05 proves `O5` catches inside `core/`, would not
have been seen. `identifiers()` now reads all of `src/holdout/` (820 → **1,181**), and the three
collisions that surfaced — `parents`, `url`, `compile_agent_tool` — are published with their reasons
rather than filtered. The deferral is restated rather than overwritten.

*(4) The restated independence rule was false of the repository it sits in.* It enumerated what the
planter may edit — "`src/` and `contracts/`" — and three of the thirty committed mutations edit
`evals/uplift/`, because claim 2's machinery is partly what claim 2 is proving. It now names what it
**forbids**, and `ledger.no-mutation-edits-the-detector` is the function behind it: a mutation whose
`file:` is under `ops/` or `corpus/` is refused. Until this branch that separation — the one
`engine.py` says carries its whole argument — was prose with nothing behind it, and this branch made
it reachable by adding `ops` to `COPIED`.

Two latent findings fixed with them: `EXPLAINED` is keyed on the **pair** `(name here, name there)`
rather than on the bare identifier, so an entry for `members` no longer pre-approves any future
`members` anywhere in the package; and three figures in prose were corrected against what the eval
prints.

`make check` green at **919 tests** · `make claim-7` **12/12 with 7/7 mutations biting**.

**Restated after merging `main`.** Claims 3 and 4 landed first and brought seven types and twenty
fields with them, so every product in this note moved: 49 → **56** types, 222 → **242** fields,
15,533 → **17,752** attacks, 1,715 → **1,960** refused by the word list. **35 of 317 and 11.0% did
not move**, because they are properties of the two published vocabularies rather than of this
estate — which is the distinction the whole claim turns on. The merge also carried claim 4's seven
demand types and claim 3's `Contamination.dropped` into `ops/personhood.py`, and the guard named
them itself: `unlisted()` and `misdeclared()` printed exactly the seven and the one.

```
id            T007
title         docs/SCENARIO.md
branch        docs/scenario
depends_on    —
closes        The file exists — the operator, the decision paths, the data, what makes it hard.
              It is in the "read this first" table and is currently missing. A writing task, not a
              blocked one.
out_of_scope  docs/DAY-ONE.md (T015, before Phase 3).
stop_at       Before Phase 2 opens — the pipelines assume it.
review        no
status        closed
```

**Closed 2026-08-30.** `docs/SCENARIO.md` exists: the operator and the three roles that touch the
design form, the three decisions with their horizons and the one legal provision that lets the
fresh path actuate itself, the ten bronze sources and the two committed corpora that are not ours,
six things that make the problem hard, and what the synthetic corpus does and does not model.

**The file is written under a rule rather than a word count, and the rule is the point.** It is
prose full of numbers, which is the exact shape of the defect this repository has found eight
times — an assertion written against a table or a projection instead of against the measurement of
what comes out when it runs. So **every number carries one of four kinds**: `[M]` measured, with
the command, the scale and the seed; `[D]` declared, a contract value `make contracts` refuses
without a `source`; `[C]` cited, an instrument or a publisher with a verification date; `[S]`
scenario, the chain the system is written *for*, carrying the words *it has never run*. `[D]` and
`[C]` are deliberately not one kind: one this project invented and a gate holds up, the other
somebody else measured and a citation holds up, and `docs/REGULATORY.md` exists because they were
once the same field. Anything that fits none of the four is **not in the file**.

**Applying the rule excluded two numbers, and both are named in the file rather than dropped.**
`CLAUDE.md`'s *"ESL penetration is ~30% of large European retailers"* is a fact asserted about the
outside world with no publisher, no URL and no verification date anywhere in the repository — not
`[M]`, not `[D]`, not `[S]`, and not `[C]` either. It is now a deferral in `docs/DECISIONS.md`
rather than an edit made on a documentation branch. And the corpus's own placement constants carry
a real argument where they live but are not contract values, because `corpus/` may not read a
contract at all — structural rather than sloppy, so what the file states instead is **the roster
they produce**, which is measured.

**Two figures in `CLAUDE.md`'s scale paragraph do not reproduce, and the file says which is which.**
Its *100 stores → 109 pairs → roster 45* was measured before T00E moved the chain's placement rule
and is stale — `python -m ops.roster --scale scenario` prints a roster of **83** today. Its
*"1,200 leave a roster of 212"* is a different failure: `--scale` accepts four names and the
largest is `harness` at 320 stores, so no run of 1,200 has ever existed and that figure is a
projection, sitting in a paragraph whose whole argument is that projections are not measurements.
`CLAUDE.md` is not edited here — that restatement is its own branch's work, and rewriting the
project's own context file inside a documentation task is a change made in the place it is least
reviewed.

```
id            T008          <- Phase-1 integration session (oversight level 3)
title         Phase-1 integration -> the skill integration-review
branch        skills/integration-review
depends_on    T000, T003, T004, T005, T006
closes        Reads the whole repository against CLAUDE.md and reports conceptual drift — it builds
              no product code. Two deferred items it is expressly empowered to act on:
              (1) DONE 2026-08-31 by contracts/floor-rule-id (#31). The rename landed and this
                  instruction is kept, corrected, per doctrine rule 4.
                  IT NAMED THE WRONG GATE. It read: "the core's Bound.rule_id strings are
                  written down a second time in evals/guardrail/reference.py, which is what
                  lets G10 disagree rather than agree with itself. A rename turns G10 red on
                  both directions at once; move the two in one change."
                  refuse_when_no_legal_price_sells appears ZERO times in reference.py and is
                  never a Bound.rule_id, so the rename cannot turn G10 red in either direction.
                  What goes red is O2 — the id is a field name in ops/personhood.py's closed
                  field set — confirmed by putting the registry back and running the eval:
                  FAIL O2 · 55/56 types agree.
                  It is the tenth form of the rule and the form with the longest reach: an
                  instruction to the next session, which does not describe the system but aims
                  the hand that changes it. Corrected here on 2026-08-31 by
                  evals/world-cache-measured — #31 fixed the PR body, PLAN.md and the deferral
                  and LEFT THIS LINE, which is a correction that stopped at one document inside
                  the branch that was correcting two of those.
              (2) the ladder-ceiling gap (doctrine rule 1 is incomplete — the declared safe state
                  produces prices the envelope refuses); the session may propose a restatement.
              The method is written as the .claude/skills/integration-review skill, not as ad hoc
              instructions — so the review that runs at every phase boundary is a versioned
              procedure that goes through a pull request like everything else.
              The skill MUST ask, in these words: "what does the `main` ruleset require, and
              does that list match the jobs ci.yml defines today?" It is the one question in
              this review that cannot be answered by reading the repository — what the forge
              requires is a fact about the forge, carried in no file here — and it is in the
              skill because it was missed once. T003 moved the claim targets out of `gate` and
              into the `claims` matrix while the ruleset went on requiring `gate`, so for two
              days a pull request with a red claim-2 merged and oversight level 1 was false.
              ops/claims-are-required closed it with one summary context, `claims-complete`;
              nothing inside this tree can check that the ruleset still names it.
out_of_scope  The three instrument findings — they are T000, and they land before the evals, not
              after. Building any product code.
stop_at       When the drift report is written and each proposed fix is opened as its own branch
              with its own review.
review        n/a — this task IS the review.
status        closed
```

**What it landed.** The review itself, `docs/reviews/phase-1.md`, and the eight branches it
proposed — all eight merged, in six commits, since rows 5, 6 and 8 turned out to be one piece
written down as three. Then this skill, `.claude/skills/integration-review/`, which is the atom's
`closes` and the reason it could not be written on the review's own branch.

**Written from the record rather than from memory, and that is the whole of why it is a separate
session.** The two sessions that conducted the review are disqualified from writing the method
down for exactly the reason they are best placed to: a procedure extracted from memory by the
people who executed it is a copy of them and not a method, and nothing afterwards can measure the
difference. So the skill was written by a session told where to look and nothing else — the report,
`PLAN.md`'s landing notes, `docs/FINDINGS.md`, `TASKS.md`, `docs/DECISIONS.md` and the log of
`main` — under one rule: **an instruction that cannot be pointed at does not go in, however
obviously a review ought to do it.**

**Its load-bearing section is the one where the method failed.** Not the eight questions, which any
reader could copy off `CLAUDE.md` and the report's headings, but the three places the phase-1 report
was wrong **in its own report**: §2b reaching its conclusion by naming the one cold run of eleven
that sat below the warm mean, §3a asking *is everything real listed* and never *is everything listed
real*, and §2d missed outright and found by the author an hour after the report had merged. Three
different failures, no two of them variations on each other. A procedure extracted from a run that
only succeeded would teach the shape of success.

**And seven holes are named rather than filled**, which is the output the brief asked for and the
more useful half until `T016` gives a second sample. There is **no measurement of what a level-3
session costs** anywhere in the record — every claim task's landing note carries what it cost and
T008's does not — so the skill sets no budget and says why, which is `CLAUDE.md`'s own rule about a
number in configuration applied to its own absence. `eval-uplift` is missing from the report's
declared inputs and nothing says whether it ran. The ruleset question is one known instance of a
class nobody has enumerated. Section order is not evidence of working order, so what the skill
requires is that a report **name its inputs**, not a sequence.

**And oversight level 2 found the file committing the defect it spends its §4 on.** The table of
the review's questions said *six come from `CLAUDE.md`'s level-3 list* and listed **five**: §6,
*is there still exactly one door with no key*, was missing, and it is one of the two rows that
changed the doctrine — the three seals of identical construction, and *today the guarantee is
detection rather than unopenability*. **A count asserted against a list nobody counted**, which is
§3a's one-directional coverage question and §4's second failure, in the file that names both. A
session following the draft would have asked seven of eight and not noticed, because the text said
six. The row is added and the arithmetic is now written out — nine rows, eight questions, §0 a
measurement rather than a question — so the count can be checked against the list it claims.

*Found by the session that ran the six branches, under a rule it stated before it could be
constrained by it: name the file and the line, or it is memory and does not go in.* It is worth
recording which findings that rule admitted. Its four checks on §4 were of its own writing at one
remove, and it said so and discounted them. **This one was a count against a list in two files it
did not write**, which is the only kind of finding a reviewer of its own record can offer without
the agreement being worth nothing — and `concurred` is not `closed` for exactly that reason.

**It found one thing while being written, which is filed rather than fixed.** `CLAUDE.md` says level
3 runs *at every phase boundary, without exception*; this file has `T016` and `T024` and nothing
after phase 4, which agrees with `PLAN.md`'s *before the next phase opens* and disagrees with
`CLAUDE.md`. Two documents, each defensible alone, nothing computing the product — level 3's own
subject arriving while level 3's skill was being extracted. It is in `docs/FINDINGS.md`, adrift by
declaration, because which of the two documents moves is the author's call.

**And the commit was refused by `.claude/hooks/main_guard.py`, twice, for two different reasons.**
It reads the *session's* working directory, which is the shared checkout on `main`, so it judged a
worktree demonstrably on `skills/integration-review` against the wrong repository. Then it refused a
command that runs no git at all, because the file being written **quotes** a git command: an
apostrophe in the prose unbalances the lexer, the coarse fallback takes over, and that fallback
matches a separator followed by `git` wherever it appears — including inside the text. Its own
comment names that failure and claims to have closed it. Both are the same shape as the instance
`CLAUDE.md` already records in that one file, and neither its docstring nor `.claude/README.md`'s
*what each does not catch* mentioned a worktree or a quoted command. Handed on rather than worked
around — a guarantee routed around is not one — and recorded by `#34`, then repaired by `#35`, which
found two further spellings of the same defect while repairing it. **Both were found by trying to do
this work and not by looking for it**, which is §2d's lesson arriving on the branch of the skill
that records it.

The integration-review skill is extracted **after** T000, not before: a review skill extracted while
the measuring instrument still has its blind spot would encode that blind spot into a reusable
procedure and then propagate it deliberately.

---

## Phase 2 — pipelines, the metric contract's three consumers, the model (local)

```
id            T009
title         pipelines/ingest — Zerobus driver + Lakeflow Connect definitions
branches      pipelines/ingest · pipelines/ingest-bulk-load
depends_on    T008
closes        A driver that writes as the corpus's 100 stores would: correct distribution over
              time, late arrivals, duplicates, a store that drops for two hours and then sends
              everything at once. The Lakeflow Connect definitions.
              --
              RESTATED 2026-09-02, because `closes` was incomplete and two other documents said
              so. It omits the S3 bulk load, which `CLAUDE.md`'s layout lists as the third thing
              under `pipelines/ingest/` and which `docs/DECISIONS.md` names by task -- "the S3
              bulk load in T009" -- as the unlock condition of a live deferral. Reached honestly
              as written, this task would close and leave that deferral pointing at a task that
              finished without doing the thing, and `make expiry` cannot see it: it checks that
              a condition is present, never that it is right.
              So T009 also closes the S3 bulk load, and `corpus/world/`'s writer gaining a
              Parquet target beside the CSV one, which is the same deferral's other half.
              Two branches rather than one, because streaming pathologies and Parquet writing
              are different mechanisms and one review over both is a review over neither. The
              deferral's unlock names the task and not a branch, so it stays valid untouched.
              The prior wording stays per doctrine rule 4; the delta is the finding, and it is
              in `docs/FINDINGS.md`.
              --
              And `100 stores` is a figure `CLAUDE.md` withdrew on 2026-08-29: 100 is the
              `scenario` scale, claim 2 runs at `harness`, and the size that decides anything is
              the surviving roster rather than the store count. The driver takes a scale like
              everything else and reads it off `corpus/world/scale.py`.
out_of_scope  Any apply to a workspace (Phase 3).
stop_at       When the driver produces a stream with the declared pathologies, and the bulk load
              writes what the lakehouse reads.
review        yes
status        open
```

```
id            T010
title         pipelines/silver — Spark Declarative Pipelines
branch        pipelines/silver
depends_on    T009
closes        Expectations routing to quarantine, the as-of reference dimension, stock-out marking
              (the one place inventory movements are available).
out_of_scope  —
stop_at       When silver builds against local Delta with quarantine non-empty on planted bad data.
review        yes
status        open
```

```
id            T011
title         pipelines/gold — dbt, the metric contract's Delta view + agent tool def + readout
branch        pipelines/gold
depends_on    T010
closes        The metric contract compiles into a Delta view, the agent tool definition and the
              readout query. The assignment table is written before the period opens and is
              read-only; the readout pins a Delta version.
out_of_scope  Executing the generated SQL on a real engine (deferred to Phase 3 — see DECISIONS.md).
stop_at       When gold builds against local Delta and the compiled consumers match byte-for-byte.
review        yes
status        open
```

```
id            T012
title         evals/definition/ — make claim-5 + make preview-audit
branch        evals/definition
depends_on    T011
closes        make claim-5 green — one definition, three genuinely different mechanisms, compared
              as integers with no tolerance (the reference implementation from T003 is a fourth).
              make preview-audit — reads the declared inventory of preview surfaces and fails when
              any claim's proof path touches one. This is where preview-audit first has something
              to act on; DECISIONS.md defers it to exactly here.
out_of_scope  The Unity Catalog metric view as a consumer (a preview/GA fourth consumer, added on
              the estate).
stop_at       When claim-5 is integer-equal across three mechanisms and preview-audit is green.
review        yes
status        open
```

```
id            T013
title         The two AI/BI dashboards as databricks_dashboard resources (definitions)
branch        lakehouse/dashboards
depends_on    T011
closes        The experiment readout and the decision monitor as databricks_dashboard resources,
              both consuming the metric contract (so both are claim-5 evidence). The refused
              version of the readout screen is the single most important screenshot in the project.
out_of_scope  Applying them to a workspace — that happens in T020 (lakehouse layer).
stop_at       When the definitions consume the metric contract and terraform validate passes.
review        yes
status        open
```

```
id            T014
title         pipelines/ml — training code, proved local
branch        pipelines/ml
depends_on    T005, T011
closes        Time-based split, censoring correction (claim 4), calibration gating above RMSE, the
              promotion gates and a named approver — pure code, proved local against a small corpus.
              A gate that has never refused anything has not been tested.
out_of_scope  The run that produces the deployed model (Phase 3, on the estate).
stop_at       When the promotion gate refuses a planted bad model for a stated reason.
review        yes
status        open
```

```
id            T015
title         docs/DAY-ONE.md — the workspace-to-RDS network path
branch        docs/day-one
depends_on    —
closes        The manual, no-API work recorded rather than silently done — in particular the
              network path from the Databricks workspace to RDS that Lakeflow Connect's database
              connectors require, verified BEFORE Phase 3, not inside it.
out_of_scope  Anything that has an API (that is IaC).
stop_at       Before Phase 3 begins, and specifically before the network path is attempted.
review        no
status        closed
```

**Closed 2026-09-02.** `docs/DAY-ONE.md` exists and says in its first line what it is: **a checklist
to be run before phase 3, not a record of a verification that happened.** Seven items, ordered by
what discovering each one late costs rather than by the order they are performed — because a
checklist read in performance order finds its expensive items last. Every external fact carries the
URL it came from and the date it was read, and six things that could not be established are in a
named **Not verified** section, which is `docs/REGULATORY.md`'s discipline applied to a vendor
instead of to a statute.

**What the task could not do, and why that is the better half of it.** `CLAUDE.md` requires the
workspace-to-RDS path to be *verified before phase 3, not inside it*. **That is unachievable by
anybody, funded or not**: the workspace is created by T018 and the RDS by T019, and both are phase
3. The instruction asks for a measurement between two endpoints that phase 3 is what creates. It
splits instead — design and residue now, the assertion immediately after `sources` applies and
before `backfill` is dispatched — which converts an impossible instruction into a possible one
without weakening what it was protecting. T019's `stop_at`, `PLAN.md`'s phase-3 bullet and the
deferral in `docs/DECISIONS.md` are each restated rather than overwritten.

**And the task found two things that outrank the document, both filed in `docs/FINDINGS.md` and
both the author's**, because every route out of either one edits `CLAUDE.md`. The ingestion gateway
that Lakeflow Connect's Postgres connector requires **runs on classic compute, continuously, at a
stated minimum of 8 cores** — against *"no always-on cluster anywhere in the design"* and against a
cost model that argues in as many words that the classic-compute trap does not apply here. And that
**connector is in Public Preview** while the sources table calls the surface GA, which fires half
the unlock condition on `make preview-audit` and puts a vendor's enrolment queue on the critical
path of `backfill`.

**The deferral this closes had said, for three days, that there was nothing to record until there
was an estate.** Both findings were readable on the vendor's public documentation the whole time.
The sentence was not wrong about the estate; it was a sentence that made looking feel unnecessary,
which is `CLAUDE.md`'s eighth form of *a guard tested by its author* wearing a deferral instead of a
rule.

```
id            T016          <- Phase-2 integration session (oversight level 3)
title         Phase-2 integration — read the repo against CLAUDE.md, report drift
branch        —  (dedicated session, runs the integration-review skill from T008)
depends_on    T012, T014
closes        A drift report. Builds nothing.
out_of_scope  Building any product code.
stop_at       When the report is written and each proposed fix is its own branch.
review        n/a — this task IS the review.
status        open
```

---

## Phase 3 — the estate (the only phase that costs money)

Entered with every locally provable claim already green. Layers apply bottom-up; `destroy` is never
automatic.

```
id            T017
title         infra/bootstrap — applied locally, once
branch        infra/bootstrap
depends_on    T016
closes        State backend + KMS, OIDC provider, the deploy role, published parameters, and the
              budget posture — 1,000 USD with alerts at 50/80/100% and NO stop action; a stop
              action only at 150%. Enforcement is the TTL reaper in foundation, not the budget.
out_of_scope  Anything a workflow applies (foundation and up).
stop_at       When bootstrap applies from a laptop and the budget + alerts exist.
review        yes
status        open
```

```
id            T018
title         infra/foundation — VPC, keys, S3 zones, workspace, metastore, TTL reaper
branch        infra/foundation
depends_on    T017
closes        The foundation layer, including the TTL reaper — the scheduled job that destroys
              anything tagged and older than N hours whatever happened. The real net; depends on no
              workflow's control flow.
out_of_scope  Lakehouse, pipelines, ml.
              -- 
              RESTATED 2026-09-02 by the route-2 ruling. It read "Sources, lakehouse, pipelines,
              ml"; there is no sources layer to be out of scope of. The VPC stays -- the workspace
              needs it -- and the private networking that existed for the RDS does not.
stop_at       When foundation applies via deploy and the reaper is scheduled.
review        yes
status        open
```

```
id            T019
title         infra/sources — RDS PostgreSQL playing the ERP
branch        infra/sources
depends_on    T018
closes        The smallest RDS instance that works, Single-AZ (a declared cost decision), in a
              private subnet, password generated into Secrets Manager.
out_of_scope  Seeding it (that is backfill) and driving it (that is run).
stop_at       When sources applies and the workspace-to-RDS assertion in docs/DAY-ONE.md §6
              passes — which is the first moment it can be run at all, not a re-check of T015.
review        yes
status        CLOSED 2026-09-02 — NOT BUILT, and this is the reason.

              The author ruled that the ERP's master data arrives as files on S3, dropped several
              times during `run`, rather than through Lakeflow Connect. `#43` established that the
              connector's gateway is classic compute running continuously, contradicting three
              sentences of `CLAUDE.md`, and that its PostgreSQL connector is Public Preview.

              Measured on the tree before the ruling: **Lakeflow Connect was the only reader of
              the Postgres.** Not a claim, not an eval, not a pipeline, not a `run` step — even
              the decision path's "a cost change in the ERP that moved the floor" reaches a
              decision through silver's `reference`, built from the bronze tables that connector
              filled, which is the same reader rather than a second one.

              So removing it leaves a database with a writer and no reader, and this layer's whole
              content is that database. It is not deferred and it is not blocked: there is nothing
              left for it to hold. T020 now depends on T018.

              What goes with it, named so nobody looks for it later: the RDS instance, the
              Secrets Manager password, the private subnet, `T018`'s `+ private networking`, and
              six of `docs/DAY-ONE.md`'s seven sections.
```

> **`stop_at` restated 2026-09-02 by T015.** It read *"When sources applies and the workspace-to-RDS
> path (verified in T015) holds"*, which asserts that T015 verified the path. **T015's own `stop_at`
> forbids exactly that** — *before Phase 3 begins, and specifically before the network path is
> attempted* — so the two lines could not both be true, and nothing in this file checks a pair.
>
> **And the reason is structural rather than a slip.** The path's two endpoints are the workspace,
> created by **T018**, and the RDS, created by **this task** — both in phase 3. No session, funded
> or not, can verify a path between two things that phase 3 is what creates. So T015 records the
> design and the no-API residue, and the assertion lands here, at the earliest moment it can exist
> and **before `backfill` spends anything**. The prior wording stays per doctrine rule 4, and the
> delta is the finding: *one task's line asserting something about another task, with nothing
> checking the pair.*

```
id            T020
title         infra/lakehouse — catalogs, schemas, grants, Lakebase, the dashboards
branch        infra/lakehouse
depends_on    T018, T013     <- was T019, which closed not built on 2026-09-02
closes        Catalogs, schemas, grants, external locations, Lakebase, and the two AI/BI dashboards
              (T013) applied.
out_of_scope  Pipelines and ml (separate layers, edited constantly).
stop_at       When lakehouse applies and the dashboards render.
review        yes
status        open
```

```
id            T021
title         infra/pipelines — SDP, dbt jobs, Lakeflow Jobs, Zerobus endpoints, bulk-load
branch        infra/pipelines
depends_on    T020
closes        The pipeline layer as jobs and endpoints. Split from lakehouse because pipelines are
              edited constantly and no routine edit should put an apply near catalogs and grants.
out_of_scope  Training (ml) and serving.
stop_at       When pipelines applies.
review        yes
status        open
```

```
id            T022
title         infra/ml — training job, evaluation, promotion gates, MLflow — NO endpoint
branch        infra/ml
depends_on    T021
closes        The ml layer. No serving endpoint — an endpoint cannot point at a model version that
              does not exist yet, and a version exists only after backfill has trained one.
out_of_scope  The serving endpoint and the agent runtime (T023, applied by backfill).
stop_at       When ml applies with no endpoint.
review        yes
status        open
```

```
id            T023          <- closes Phase 3
title         The five workflows + infra/serving (applied by backfill)
branch        infra/serving-workflows
depends_on    T022
closes        ci, deploy, backfill, run, destroy — each dispatching from main only. infra/serving
              (the endpoint, the agent runtime, the AI Gateway and its tool registry) applied by
              backfill once a model version exists. A run whose every figure is asserted by a step
              that fails when it is not true — at least one experiment producing a number and at
              least one refusing for the right reason — with the account confirming afterwards that
              nothing is left standing. destroy takes a target (serving | all) and is never
              automatic, on success or failure.
out_of_scope  The agent surface and claim 6 (Phase 4).
stop_at       When run's assertions pass and destroy leaves the account clean (asked, not assumed).
review        yes
status        open
```

```
id            T024          <- Phase-3 integration session (oversight level 3)
title         Phase-3 integration — read the repo against CLAUDE.md, report drift
branch        —  (dedicated session, runs the integration-review skill from T008)
depends_on    T023
closes        A drift report. Builds nothing.
out_of_scope  Building any product code.
stop_at       When the report is written and each proposed fix is its own branch.
review        n/a — this task IS the review.
status        open
```

---

## Phase 4 — the agent, and the number that matters

```
id            T025
title         The agent surface — context, tool registry, structured output, budget caps, traces
branch        agent/runtime
depends_on    T024
closes        What context the agent reads, the tool registry it is confined to, the structured
              nine-field design output, budget caps, traces. No LLM anywhere near the decision path.
out_of_scope  claim-6 (T026); the human/policy paths (T027).
stop_at       When the agent produces a structured design and is confined to its tool registry.
review        yes
status        open
```

```
id            T026          <- closes Phase 4, closes the project
title         evals/design/ — make claim-6
branch        evals/design
depends_on    T025
closes        make claim-6 green with three numbers printed: N designs proposed against a bank of
              business questions with known answers, M refused, and K of the refused that would
              have produced a confidently wrong number. The judge never rules on validity — code
              does; the judge rules only on design quality. gate-proof refuses every planted
              violation by name.
out_of_scope  README/banner/article/post/promo (T028).
stop_at       When claim-6 is green with the three numbers and its mutations bite by name.
review        yes
status        open
```

```
id            T027
title         The human path and the declared-policy path through the same engine
branch        design/three-sources
depends_on    T025
closes        The human path and the declared-policy path exercised by the SAME engine, proving the
              engine does not know and does not care who filled the form — same checks, same
              refusals, same experiment.
out_of_scope  —
stop_at       When all three sources (agent, human, policy) are first-class through one engine.
review        yes
status        open
```

```
id            T028
title         Publication — README, banner, article, debut post, promo
branch        docs/publication
depends_on    T026
closes        The publication checklist runs: README to the portfolio standard, banner, long-form
              article, debut post, promo. Every Greek citation re-opened through search.et.gr and
              updated; every console screenshot through aws-mask. The repository is public but
              unannounced until this closes.
out_of_scope  Any product claim.
stop_at       When the checklist is complete and the citations are re-verified.
review        no
status        open
```

---

## Closed — the atoms that have landed

Kept so this file is the complete registry, not just the open half. What each one settled lives in
`PLAN.md`'s prose.

```
L1  contracts/ — the metric schema, the guardrail envelope with effective windows, the nine-field
    design schema, the closed reason-code vocabulary, ladder_policy@v1, the compilers, make
    contracts, docs/REGULATORY.md.        branch contracts/schemas              status closed
L2  src/holdout/core/ — the guardrails and the certificate type (ProposedPrice ->
    CertifiedPrice | Refusal), scenario selection, the ladder. Money as integer cents with three
    roundings.                            branch core/guardrails-pricing-ladder status closed
L3  corpus/real/, evals/guardrail/, evals/gate_proof/, make claim-1, make gate-proof — claim 1
    closed; thirteen mutations, each refused by the check named in advance.
                                          branch evals/guardrail-and-gate-proof status closed
L4  Mutation ownership — a mutation belongs to exactly one claim and runs under that claim's
    target; gate-proof audits rather than executes (the orphan/duplicate ledger).
                                          branch evals/mutation-ownership       status closed
L5  CI, the protected main (a ruleset with no bypass actors), docs/DECISIONS.md.
                                          branch ops/gate-and-decisions         status closed
L6  src/holdout/core/design/ and experiment/ — the nine-field form, the eight design
    refusals, the committed lottery and its seal, the four validity checks and the
    design-based estimator. contracts/design/inference.yaml as a fourth contract family.
                                          branch core/design-experiment         status closed
L7  Stratified randomisation — strata matched on a composite distance, the lottery drawing
    within them, and inference.yaml v2 restating balance_tolerance_smd as a readout check.
    The reference set fills at the scenario's shape.
                                          branch experiment/stratified-randomisation
                                                                                status closed
L8  .claude/skills/claim/ — the method for building a claim end to end, extracted from the two
    that have closed rather than from one. CLAUDE.md's rule about a sentence widened to any
    assertion, a number in configuration included.
                                          branch ops/claim-skill                 status closed
L9  src/holdout/core/demand/, evals/censoring/, make claim-4 — claim 4 green at 12/12 with 9/9
    mutations biting. A stock-out reads as a type with no units attribute; the correction is
    fitted on days the shelf held and graded on a held-out segment of them, against receipt
    totals the corpus emitted rather than anything the generator knows.
                                          branch evals/censoring                 status closed
L10 evals/uplift/, make claim-2 — claim 2 green: the A/A harness at K = 200 over four world
    seeds, the six adversarial worlds, and the four published numbers. Phase 1's hardest claim.
                                          branch evals/aa-harness                 status closed
L11 evals/assignment/, make claim-3 — the committed seed, the seal, and the contamination
    check that reports every uncoordinated edit by name.
                                          branch evals/assignment                 status closed
L12 evals/oversight/, make claim-7 — the closed field set refusing 17,752 of 17,752 where the
    hand-written word list catches 35 of 317.
                                          branch evals/oversight                  status closed
L13 docs/SCENARIO.md — the shop, and the four kinds a number in it may be: [M] measured with
    its command, [D] declared, [C] cited, [S] scenario.
                                          branch docs/scenario                    status closed
L14 The phase-1 integration review (oversight level 3) — docs/reviews/phase-1.md, the nine
    proposed branches, and the tenth form of the rule. The ruleset required `gate` and the
    claims had left it; the review itself was rewritten in English with make language behind
    it.                                    branches docs/phase-1-integration ·
                                           ops/claims-are-required ·
                                           docs/review-in-english          status closed
L15 make figures — a gate reports on what it examined, and this is what checks the difference.
    make expiry learns what closure is. docs/FINDINGS.md, the register an open finding falls
    out of.                                branches ops/every-number-carries-its-kind ·
                                           ops/expiry-knows-what-closed ·
                                           ops/findings-register           status closed
L16 corpus/real/ — the legal claims restated: real prices, real law, derived cost, wherever
    the corpus is described as a whole.    branch corpus/legal-claims-restated     status closed
L17 evals/gate_proof/ — a check is armed by a mutation, declared un-armable with its reason, or
    unarmed and printed. make figures gains armed-or-says-why.
                                          branch evals/unarmed-checks             status closed
L18 contracts/guardrails/floor.yaml — a rule id named for what it measures, and RENAMED_RULES
    reading each window in its own vocabulary, with a time bound so a retired name cannot come
    back in a window opened after it.      branch contracts/floor-rule-id          status closed
L19 .claude/skills/integration-review/ — oversight level 3 as a versioned procedure: the eight
    questions and which of them produced a finding, the ruleset question no reading of this tree
    can answer, the three places the phase-1 report was wrong in its own report, and seven holes
    the record cannot fill.                branch skills/integration-review        status closed
L20 docs/DAY-ONE.md — the no-API residue, ordered by what finding each item late costs, with
    every vendor fact carrying its URL and read date and six holes named rather than filled.
    The verification it was asked for is impossible as written (both endpoints are phase 3),
    so the assertion moves to the earliest moment it can exist. Two findings against
    CLAUDE.md, both the author's.          branch docs/day-one                    status closed
```

**Two of those entries named branches that never existed, and `evals/world-cache-measured` found
it by asking git.** `docs/phase-1-review` and `ops/coverage-expiry-findings` were written here on
2026-08-31 and are inventions: the first was three branches — `docs/phase-1-integration`,
`ops/claims-are-required`, `docs/review-in-english` — and the second was another three. **The
registry's shape assumed one branch per atom**, and an atom that spanned three got a name somebody
made up to fill the column. Written in the branch whose subject was documents disagreeing with the
code, which is where it belongs on the record rather than quietly corrected.

Two older entries have the same defect — `contracts/schemas` and `core/guardrails-pricing-ladder`
name no branch that exists — and are left as they are, because what they were is not recoverable
from the log and inventing a second name to replace the first would be the same act again.

**L10 to L18 were added on 2026-08-31, and the gap is the finding.** This section calls itself
*the complete registry* and stopped at **L9** while nine atoms had closed after it — claim 2, claim
3, claim 7, `SCENARIO.md`, the review itself, and four of the branches the review proposed.
`docs/reviews/phase-1.md` §3e found three of them missing; by the time it was acted on there were
nine, because the section kept claiming completeness while the work went on.

**It is a hand-maintained second copy of `git log main`, and nothing compares them.** Every closed
atom is a squash commit on `main`; this section adds what each one *settled*, which the log does
not, and that is why it exists rather than being deleted. What it does not have is a gate, so it
goes stale in exactly the direction the coverage rule names: it reports on what it examined as
though that were what exists. Filed in `docs/FINDINGS.md` rather than gated here, because matching
an entry to a squash commit needs a rule for what counts as an atom, and that is a judgment.

---

## The critical path

```
T00A ─▶ T002 ─────┐    (both closed)
                  ├─▶ T00D ─▶ T00E ─▶ T003  ✅ (claim-2 green — phase 1's hardest claim)
T001 ─▶ T002B ────┤    (both closed)                    │
T000 ─────────────┘    (also blocks T004, T005, T006)   └─▶ T00B ✅ ─┬─▶ T004 (claim 3)
                                                                    ├─▶ T005 ✅ (claim 4)
                                                                    └─▶ T006 (claim 7)

remaining before T008 and phase 2:  T004 · T006, mutually independent and parallel · T007
                                    — all three closed; nothing remains. See below.
```

**T00B sits on that edge deliberately.** It needs T003 because a method extracted from one closed
claim is a copy of that claim, and it precedes T004–T006 because those three are the first evals
that will be written by following an existing shape — extract the method after them and it is a
method extracted from five samples of a habit rather than two samples of a rule, with three of the
five having inherited whatever the copying got wrong. It is T000's argument one layer up: fix the
instrument before it is copied four times, not after.

**T003 has closed.** Claim 2 is green at K = 200 and the four numbers are published rather than
ticked. What still stands between here and the phase-1 integration session is claims 3, 4 and 7 —
each of which needs nothing that T003 did not already build — and `docs/SCENARIO.md`.

**T005 has closed since**, so it is claims 3 and 7 and `docs/SCENARIO.md`. Claim 4 is green at
12/12 with 9/9 mutations biting, and it was the first claim built by following
`.claude/skills/claim/` rather than by reading the two closed evals — which is what T00B was
extracted for. The skill held: every step produced something, and the two findings it surfaced both
came from steps 8 and 9, the mutations and *write down what came out*.

**T00D and T00E were inserted on 2026-08-28, by T003 stopping on its first measurement.** They are
above, with the numbers. The short version: the corpus's geography and the design engine's
neighbour exclusion were each written correctly and never run against each other, and together they
leave a roster no holdout can be drawn from. Nothing downstream of that is worth building, which is
why T003 stops rather than tunes.

T000 and T00A gate the phase-1 evals and corpus respectively, and both had no upstream. **T00A,
T002, T001 and T002B have closed.** T003 — the A/A harness and `make claim-2`, which closes phase
1 — now waits on T000 alone, as does T005 (claim 4) on its corpus side.

**T003's inherited condition is settled, and T002B is where.** The screen's acceptance rate at the
scenario's shape left the reference set too small for the declared α; assignment is now stratified,
so the reference set fills to the contract's B = 1000 and the p-value floor sits two orders of
magnitude under α. What T003 still owes the deferral is the *published* rate — how often a
stratified draw is refused at readout as `IMBALANCED_PRE_PERIOD` — measured on the corpus rather
than on a roster this repository wrote.
