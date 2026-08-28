# Holdout — plan

Four phases. Each names what closes it. Nothing in a later phase starts before the earlier one
closes, because every later phase assumes the earlier one is true.

**Phase 1 is the core and the claims that need nothing else. Phase 3 is the claims that need an
estate.**

---

## Phase 1 — The core, the contracts, and the hardest claim

The phase that decides whether the project is worth building.

### Work

- `contracts/` first: the metric schema, the guardrail envelope with effective dates, the
  nine-field design schema, the closed reason-code vocabulary, `ladder_policy@v1`.
- `src/holdout/core/` as pure functions: guardrails and the certificate type, scenario selection,
  the ladder, the design feasibility engine, assignment from a committed seed, the four validity
  checks, the design-based estimator.
- `corpus/world/` — the generator and the six adversarial worlds at **100 stores across three
  fresh categories over eight months** (~36M POS lines), with **no import path** to `core/` and a
  test that enforces it. The truth lives in a sealed file the grader opens only
  after the estimate is produced. *Landed 2026-08-27: 36.7M POS lines at the declared scale, six
  worlds, and the barrier holding over sixteen modules — see the progress note below.*
- `evals/uplift/` — the A/A harness at K = 200 seeds with a one-sided binomial check against the
  declared α, and the six worlds including W6, the world where the correct answer is "yes, there
  was an effect". Every draw runs the whole system, not just the estimator.
- The reference implementation of truth: a deliberately slow Python loop over every event,
  written separately from the dbt path, so the two must agree. It doubles as a fourth independent
  check of claim 5.
- Stratification on the declared pre-period covariates, and the matching inference — a
  permutation test under the same restriction, drawn within the same strata, or a
  covariate-adjusted estimate. CI coverage drifting above nominal in the A/A harness is the
  symptom of getting this wrong. *Landed 2026-08-28, replacing a re-randomisation screen that
  could not reach the declared α — see the progress note below.*
- `evals/assignment/`, `evals/guardrail/`, `evals/censoring/` and their `gate-proof` mutations.
- `evals/oversight/` — the decision key carries no customer dimension, and the test goes red if
  one appears. It costs minutes and needs nothing else, so it is proved here rather than left
  open for months.
- The Makefile: one target per claim, plus `make contracts` — recompiles every consumer and goes
  red on a stale artefact or on a guardrail `value` with no `source`.

### What closes this phase

**`make claim-2` green.** On an A/A split the system reports a significant effect no more often
than its declared α, across K = 200 seeds; and across the six worlds it refuses exactly where it
should and — equally important — **does not refuse in W6**. Four numbers are published, not a
tick: the false-positive rate against α, the false-refusal rate on W6, estimator bias, and CI
coverage.

**If the A/A test does not stand, nothing is built on top of it.** That is the whole point of
putting it first.

### Progress

**The atom-level status now lives in `TASKS.md`** — which piece is open, which has landed, its
branch and its exact closing condition. Two answers to "what is still open" is the thing `TASKS.md`
exists to prevent, so the table that used to sit here is gone and this section keeps only the record
of what each landed piece settled and what the reviews cost. That record stays because doctrine rule
4 says a correction never erases what was previously stated.

**What the contract layer settled.** The four families are versioned with effective windows and
resolve as-of, so a decision taken in April is judged by April's rule permanently. Every numeric
`value` carries either a legal citation with a verification date or an explicit
`scenario_assumption` — 45 values, and `make contracts` prints the ratio of sourced to found so the
number can be less than 100%. The metric contract compiles into 13 artefacts that are byte-compared
on every run, so a hand-edited consumer is a build failure. A metric whose arithmetic or rounding
moved without a `restatement` is a build failure. `src/holdout/core/` is still empty by design; the
boundary test that keeps PyYAML and jsonschema out of it is placed and waiting.

**What it cost to get honest.** The review caught a `legal_instrument` asserting a basis its own
article never states — the per-unit framing belongs to 2022, not 2021 — and four more of the same
class, including a Directive cited as evidence about Greece. `make contracts` could not have caught
any of them: it checks the *shape* of provenance, never its *content*. That is the standing limit
of the mechanism, and it is why oversight level 2 reads the citations rather than trusting the
green tick. Separately, generation had been resolving paths against a fixed repository root, so
every negative test asserting only "exit code 1" had been passing for the wrong reason.

**What the core settled.** `ProposedPrice → CertifiedPrice | Refusal`, and `CertifiedPrice` is a
type rather than a convention: not a dataclass, filled by a function held in a closure and stamped
with a witness that has no importable name. Direct construction, subclassing, `dataclasses.replace`,
pickling, copying and duck-typing all refuse. The actuator re-derives the certificate's checks from
its own recorded bounds, so a tampered price contradicts what the certificate claims was checked.
Money is integer cents with three roundings, because a bound that rounds toward what it forbids is
not a bound. The ladder, the envelope and scenario selection are pure functions over plain data;
`core/` imports no SDK, no engine, and not PyYAML or jsonschema either.

**The limit, stated rather than papered over.** A forger who rewrites the price, the bounds, the
checks and the source in one coordinated edit is not caught by any check inside a certificate,
because the certificate never held independent evidence of its own provenance. A test asserts that
limit rather than hiding it. **The type makes the mistake impossible and leaves the forgery visible.**

**What the review cost, again.** Two lines of public API defeated claim 1's central sentence: an
empty `PriceBounds()` satisfied both halves of the actuator's re-check, turning a certified €2.00
into €0.01 on a shelf. And the ladder's deepest rung — the declared safe state of the primary
decision path — was refused by the envelope for roughly one base price in five, at the rung three
hours from expiry that matters most, because the ladder rounded its quote as a price and the
guardrail rounded the same number as a bound. Neither was visible to a green suite, for one reason:
**the branch delivered two modules and never composed them.** From here on, no core module is
tested only alone.

**Deliberately not built yet:** no `claim-N` target exists, because nothing here proves a claim. A
green target that proves nothing is a gate disarmed before it was ever armed. Claim 1 is not proved
by the core — it is made provable; the eval that attacks the gates from an independent corpus of
real price lists is still open, and the seam it needs is built and verified.
*Since 2026-08-27: that eval exists and claim 1 has closed. `claim-2` … `claim-7` and
`preview-audit` are still absent, on exactly the same reasoning. The seam held — the eval builds
`Envelope` objects from literal numbers without opening `contracts/`, which is what let a sweep
reach the `unspecified_in_the_instrument` branch that no contract date can reach.*

**Oversight level 1 is now structural.** `main` is protected by a ruleset with **no bypass actors**,
so the rule binds the owner: changes only through a pull request, `gate` and `secrets` both required
and both green, linear history, no force pushes, no deletion. Verified by attempting a direct push
and being rejected by name. CI runs the whole local gate, names the contract gate separately,
scans full history with `gitleaks`, and **discovers** claim targets by grepping the Makefile rather
than listing them — so a claim target that exists but is never run is impossible by construction.

The gate justified itself on its first green run by failing: `UV_FROZEN` and `uv sync --locked`
contradict each other, and nothing local had noticed.

**The repository is public.** It was created private; on a free account a private repository can
have neither Actions nor a protected branch, and oversight level 1 is what everything else leans
on. The publication *checklist* has not run, so the repository is public and **unannounced** — no
README, no banner, no article, no post. `docs/DECISIONS.md` records the trade and restates the
condition it overtook.

**What claim 1 cost, and what it bought.** The eval attacks the gates from 32,480 individual price
quotes the UK Office for National Statistics collected by hand in shops and published under the Open
Government Licence, the 63 categories of ΥΑ 21330/12.03.2026 (ΦΕΚ Β΄ 1411) — the Greek margin cap's
own list, which the contract does **not** name — and Eurostat's gross margin for Greek supermarkets.
232,373 decisions across eight envelopes, **all twelve `at_decision` codes reached**, and nine
checks green. The load-bearing one is a **second implementation** of the envelope arithmetic, in
exact `Decimal` euros against the core's integer cents, with no tolerance: zero certified prices fell
outside it, and zero refusals were unsupported by it.

`make gate-proof` plants **thirteen** deliberate breaks and every one is refused by the check named
in advance. Three rules make that mean something: green first, a parsed JSON reading rather than an
exit code, and `STALE` — never a pass — when a mutation's anchor or its named check has moved.

**What the corpus found that nothing else could.** Two things, both recorded in `docs/DECISIONS.md`
with unlock conditions rather than quietly fixed. The **ladder takes a floor and no ceiling**, so
where the margin cap binds below the base price the declared safe state produces prices the envelope
refuses — 7,366 of 26,600 ladder quotes. The guardrails were right to refuse; doctrine rule 1 is what
is incomplete, and it is the same class as the composition finding a review made earlier. And
`benchmark_margin_pct` **does not say which denominator it is in**: the Greek instrument defines the
capped margin over the selling price, the core bounds it as a mark-up on cost, and the contract's
field name points at the first while the arithmetic wants the second. It fails safe. It is still an
ambiguity in a load-bearing field, and it was found by reading the instrument rather than the
contract.

**Two mutations survived before they bit**, and both are kept in the record. One named a check that
could not catch it; one was caught by a *different* check, so it proved nothing about the line it was
aimed at. Each was fixed by correcting the eval, never by widening an assertion — **a gate can only
be shown to bite where it is the gate that refuses.** A mutation set that never surprises its author
was written after looking at the answers.

**What the ownership split settled.** A mutation belongs to exactly one claim and runs under
that claim's target. `make gate-proof` stopped executing and became the accountant: no
orphan, no duplicate, and no `claim-N` target with nothing planted against it — CLAUDE.md's
checklist question, made structural. The CI job goes from **13m06s to roughly half**, and the
timeout goes back to 15 minutes; but the reason to do it is the orphan, which nothing caught
before. A mutation dropped into `mutations/claim-9/` with no `claim-9` target was planted,
never run, and never missed.

**Oversight level 2 has read the claim-1 branch.** Its verdict on closure: *substantively yes;
as currently written up, not quite.* The actuation half is genuinely proved. Three things must
move before this file's claim of closure is fully earned, and all three are the same class the
phase-1 review found — **prose asserting more than the code supports**:

1. **The "7,366 ladder quotes refused by a ceiling" figure is misattributed.** 6,650 of them
   are `MARGIN_CAP_BASIS_UNEVALUABLE`, a predicate with no bound at all, which a ceiling on the
   ladder would not change. The supportable figure is **716 of 26,600**, from one envelope. That
   wrong number is now carried by a deferred `docs/DECISIONS.md` entry the phase-1 integration
   session is instructed to act on.
2. **`_exact_floor` in the eval calls `Money.as_lower_bound`** — the core's own rounding — while
   its docstring claims independence. Patching that primitive leaves G2, G3 and G6 all green, so
   a defect in the rounding rule this project chose money's representation for is invisible to
   every check that calls itself a second implementation. Relatedly, G3's one-cent tolerance
   cannot catch a bound that is one cent **too strict** — which is precisely the shape of the
   ladder bug its own docstring cites as motivation.
3. **"The 2025 benchmark margin" is a 2008–2020 industry median.** ΥΑ 21330/2026 άρθρο 4 παρ. 5
   defines the benchmark as the trader's own average, per product code, over 2025. The corpus
   documents describe the Eurostat figure as something its sources never state, and
   `corpus/real/README.md` reads an equivalence into άρθρο 4 παρ. 4 that the article does not
   contain.

Also found, not blocking: the margin-cap ceiling is algebraically the item's median price, so
the Eurostat figure cancels out of the cap entirely; `which_direction_it_errs` argues only the
floor and is wrong for the cap; the regulated list's independence is largely nominal, since the
three `contract.*` envelopes take their basket from the contract; and "the planter cannot tune
the inputs" is tamper-**evident**, not tamper-proof.

*Two of the reviewer's findings were in `evals/gate_proof/` and are fixed on this branch: a
docstring naming a verification function that has never existed, and `_apply` joining a
mutation's declared path with no containment check. The rest is a separate piece of work.*

**What the hooks settled.** Two barriers stopped being tests that run afterwards. The corpus
barrier — no module under `corpus/` may import `holdout` — now has **one** implementation in
`ops/isolation.py`, called by the boundary test and by a harness hook, so the write is refused at
the moment it is attempted rather than at the end of the session. It is registered on
`PostToolUse` for `Bash` as well as on the editing tools, because a heredoc or a `sed -i` reaches
no `PreToolUse` hook with a `file_path` at all and a Pre-only hook would have been blind to the
most ordinary route a file gets written by. That half cannot un-write the file and says so; the
test is still the gate. The second hook refuses `git commit` on `main` — not a duplicate of the
ruleset, which refuses the *push*: what the ruleset cannot do is stop the commit being made, and
the cost of that is the twenty minutes of `git reset` before a pull request can be opened.

**The bar for a hook is now written down.** A hook exists only where the gate that already covers
the rule cannot run at the moment the mistake is made. Three candidates were rejected against it
— `make check` before every commit, a block on `git push` to `main`, and branch-name enforcement
— and the reasons are in `docs/DECISIONS.md` rather than in a conversation. `.claude/settings.json`
is committed, so the hooks go through a pull request and CI like everything else, and `ops/` and
`.claude/hooks/` are linted and type-checked on the same terms as `src/`.

**Doctrine rule 6 is enforced somewhere.** `make expiry` reads the deferred registry in
`docs/DECISIONS.md` and refuses an entry past its date, or one carrying neither a date nor an
unlock condition — the section's own opening sentence, made checkable. It also refuses a
*partially* drifted section, which is the dangerous case: eleven entries stop matching, two still
do, and a naive checker reports two deferrals and stays green while the registry silently shrinks.
Two independent counts do that, because either alone has a blind spot — one catches a header whose
`· deferred` changed shape, the other catches a header that dropped its bold. What it cannot
catch is an entry deleted outright: there is nothing left to compare against, and that is left to
the pull-request diff rather than claimed. It is the only target that can go red on a day nobody
touched the repository, which is the point.

**What the review cost, a third time, and it was the same class.** Oversight level 2 read the
branch against `CLAUDE.md` and found ten things on a suite that was green at 372 tests. Two were
fatal to the branch's own closing condition, and **both were named in the prose as impossible**:

- `main_guard` **allowed the ordinary two-line commit on `main`.** It listed a newline as a
  command separator; `shlex` never produces one, so the entry was dead and every line after the
  first joined the first command. `git add -A && git commit` on one line was refused; the same
  two commands on two lines were not. The guard bit the shape a reviewer would type into a test
  and missed the shape a session actually writes.
- The corpus barrier **missed `src.holdout`, which imports and runs** — `src/` is an implicit
  namespace package and the repository root is on `sys.path`. It is the spelling that matches the
  path on disk, it is the spelling `TASKS.md` used to describe the violation, and the module
  carried a comment explaining that it would not be used. The gate behind the hook had the same
  hole, and this branch had rewritten that gate without closing it.

The other eight are in `docs/DECISIONS.md`. The one worth repeating here: **the text fallback had
no test at all**, because all twelve sources in its parametrisation parse and take the AST path —
it could have been deleted outright and the suite would have stayed green. It was also wrong in
both directions. That is a test passing for the wrong reason, in the file whose whole job is to be
the gate.

Every fix was made by correcting the code, never by widening prose to fit it, and every one landed
with a test that fails on the un-fixed version. The suite went from 372 to 407.

**Its limit is recorded as a deferral rather than glossed.** An unlock *condition* is prose and
can never expire, and all thirteen existing entries carry one, so the expiry half of the target is
armed by a planted entry in `tests/ops/test_expiry.py` and by nothing in the real registry. That
is the same shape as a `claim-N` target with no mutation planted against it, and it is answered
the same way. The target prints every deferral's age in days, because that is the only number
available about a condition nobody can evaluate.

**What the corpus settled.** `corpus/world/` is a **stream**, not a directory: a world is a pure
function of `(world, seed, scale)`, generated store by store with every draw keyed on what it is a
draw *about* rather than on how many draws came before it. Three properties follow and all three are
load-bearing — a world is reproducible by anyone who clones the repository, a restriction to three
stores is a genuine window onto the same world rather than a smaller one, and **no key contains the
arm**, so re-running under all-control redraws the identical numbers for every store whose policy did
not change. That last one is what T003's independent measurement of truth rests on: the counterfactual
differs from the observed world by the treatment effect and by nothing else, rather than by the effect
plus Monte-Carlo noise. At the declared scale — 100 stores, 120 SKUs, 244 days — it produces **36.7M
POS lines**, measured by the command in `corpus/world/README.md` rather than inferred from a smaller
run. Nothing is committed; `corpus/real/` is committed and digest-checked precisely because it
*cannot* be regenerated, and the two opposite rules are decided by that one question.

The seal holds **behaviour** and never a number about money, because the effect on the metric does
not exist anywhere until it is computed. It opens only against a readout already written to disk and
appends that readout's digest to a ledger inside itself. It is an envelope rather than a lock and
says so: the guarantee is that the truth is never in the harness's process — no function returns it,
no object a caller holds carries it, and the file yields nothing to `grep`. Its limit is asserted by
a test that performs the coordinated forgery and requires it to **succeed**.

**What measuring found that reasoning did not, twice, and both would have passed a green suite.**
Store placement was probabilistic and produced **zero** neighbour pairs at the smoke scale, so W2 was
structurally unable to interfere and every test about it would have passed vacuously — a whole
adversarial world reduced to a docstring. And W2's spillover direction was hard-coded as *control
loses trade to treatment*, on the assumption that a candidate markdown policy cuts deeper. The
candidate cuts **shallower**: measured against its own counterfactual, an aggressive ladder destroyed
between 5% and 25% of category margin, because a store that marks down harder teaches its shoppers a
lower normal price and loses more at full price the rest of the week than it saves in waste. A world
whose interference points the wrong way still breaks SUTVA and would still have been detected by
everything downstream, which is exactly why nothing would have caught it. The fix was not to flip the
constant: the direction is now derived from the two schedules, and the test hands the neighbour a
shallower ladder and then a deeper one — both built inside the test — and requires the watched store
to move both ways. That is `CLAUDE.md`'s rule about a guard tested by its author, applied to a
generator, and it is the first time in this repository the rule was applied before the defect rather
than after it.

**And a third thing, which was not this branch's to find.** The corpus barrier's gate grew a
second half — every module under `corpus/` imported with `holdout` unreachable, closing at module
level the `importlib.import_module` hole `.claude/README.md` names. The first version of that test
blocked `builtins.__import__` and **did not catch the case it was written for**: that hook backs the
`import` statement alone, and `importlib.import_module` goes through `sys.meta_path` instead. It was
found by planting the call, which is the only way it could have been found. The same technique was
in `tests/boundary/test_core_imports_nothing.py`, where it had been since `core/` was written, so
both were rewired onto one implementation in `tests/boundary/conftest.py` — and that implementation
is itself driven, in `tests/boundary/test_blocking.py`, by the exact spelling that defeated its
predecessor. **When a guard is fixed, the gate behind it is re-read; they usually share the
assumption.** This time they shared the technique.

**What the corpus does not know, recorded rather than glossed.** It knows nothing about the guardrail
envelope — no floor, no ceiling, no regulated basket — so it produces shelf prices `core/` would
refuse, and the deepest rungs of `ladder_policy@v1` sell below the cost the ledger records. That is
what independence costs, and it is the same gap the ladder-ceiling deferral already names from the
other side. It is a deferral with the eval that closes it named, not a defect that was fixed by
letting the corpus read a guardrail.

**What the design engine and the experiment core settled.** A form, three sources, one answer:
the engine does not know and does not care who filled it, and a test runs one identical design
under all three attributions and asserts the three experiments are the same lottery. Moment 1
returns a `Feasible` carrying the sealed assignment or a `DesignRefusal` carrying **every** code
that fired; moment 2 refuses to compute anything before the declared end, consulting neither the
decision rule nor the stopping rule nor who is asking; moment 3 runs all four checks always and
reports four figures whether or not one of them failed. The estimator is Lin's adjustment,
studentized against the **weak** null, with a permutation test over the draws the same screen
accepts and an interval that inverts that test — exact in `Fraction` throughout, endpoints as
integers in the metric's own unit, no tolerance anywhere. `SealedAssignment` is the certificate
pattern one package along, and the digest is what survives the round trip through a table that a
type cannot follow.

**Two things are derived rather than written down, and both were nearly tables.** The
interference refusal over the four units of randomisation is a pure function of
`contracts/design/inference.yaml`'s `carryover:` block, so a contract declaring a washout long
enough to exhaust the reference price admits `store_week` with **no code change** — asserted by
handing the function an independently built block with the flag cleared. And the readout's
balance check re-measures the covariates as they stood at close rather than re-running the screen
on the screen's own matrix, which would have passed by construction. Restated covariates,
attrition and a moved roster each turn it red in the suite.

**A new contract family, because a `Decimal` constant in a `.py` file is a value without a
source.** α, the target power, the balance tolerance, the exposure floor, the holdout share, the
two budgets, the neighbour radius and three standard-normal quantiles now live in
`contracts/design/inference.yaml`, every one a `{value, source}` pair, every one a
`scenario_assumption` — none of this is law and the split is what keeps that legible. The
quantiles are **computed twice**: written out as literals because `core/` may not import
`statistics`, and recomputed in the contract test with `NormalDist().inv_cdf`. `design` joined
`PROVENANCE_FAMILIES`, whose description had said "numbers that come from outside the
repository" — too narrow, since a threshold invented *inside* needs an argument beside it just
as much. The provenance census went from 45 values to 59.

**One code was added to the closed vocabulary and the addition was a code change with a test.**
`NO_ADMISSIBLE_ASSIGNMENT` — the re-randomisation screen accepted nothing inside the declared
budget. Without it a roster the screen can never balance had *no correct output*: raising would
have made an infeasible design an error, and the whole point of the engine is that infeasibility
is a refusal that names what would fix it.

**Three things the SPEC asserted that did not survive being written**, and each is corrected in
the code rather than worked around. Moment 1 was to *generate* the committed seed; `core/` reads
no clock, no environment and no random source, so the seed is an argument — which is also the
stronger position, since a seed the engine invented is a seed nobody committed to in advance.
The signature carried no covariate *values*, only the contract naming the columns, and the screen
cannot run without them. And a one-sided design was to size on a one-sided quantile that the
contract never declared, so `z_one_sided_alpha` joined it with its own source rather than being
computed in Python. A fourth was an internal contradiction: `UNITS_ALREADY_COMMITTED` cannot both
be an automatic exclusion and a refusal, and it is the refusal — the contract's own remedy says
*exclude the committed units*, in the imperative, so dropping them here would be the engine
answering a question it was asked to refuse.

**And the finding that decides whether claim 2 can be computed at all.** The screen admits a
candidate only when every declared covariate is inside a standardised difference of 0.10. At the
scenario's own shape — 100 stores, a 20% holdout — the standardised difference has a spread of
about 0.25, so each of seven comparisons passes about 31% of the time and all seven pass about
**three times in ten thousand**. Measured, it is roughly one draw in a thousand. With
`max_assignment_attempts` at 10,000 the reference set therefore holds single figures of draws,
and the smallest attainable p-value — `2 / (1 + B)` inside an inverted interval, because the
mirror of the realised assignment always ties under a large shift — is **above the declared α**.
No experiment at the scenario's shape could report a significant effect, so **W6's false-refusal
rate would be 100% by construction**, for a reason that has nothing to do with the estimator.
Nothing in the code is wrong: `reference_set` returns what it found, the p-value divides by that,
and the readout prints B. What is missing is a budget or a mechanism, and choosing between the
four candidates — a far larger budget, a wider tolerance, a larger holdout share, or stratified
randomisation instead of rejection sampling — is a contract or design change that belongs to
T003. It is a `docs/DECISIONS.md` deferral **and** a test that measures the rate, so T003 cannot
start without meeting the number.

**Deliberately not built:** no `claim-N` target, no `gate-proof` mutation, nothing under `evals/`.
The suite went from 510 tests to 747 and `make claim-1` is still 9/9 with 13/13 mutations biting.

**What stratified randomisation settled — the finding above, answered.** The remedy is the
fourth of the four candidates, and it is a mechanism rather than a dial: units are matched into
strata on a composite distance over the declared covariates, the lottery draws one control per
stratum from the committed seed, and **nothing is screened**. Every candidate is admissible, so
at the scenario's own shape the reference set fills to the contract's B = 1000 and the p-value
floor `2 / (1 + B) ≈ 0.002` lands two orders of magnitude under α = 0.05. The paragraph above
stays as written because doctrine rule 4 says a correction never erases what was previously
stated; what changed is the mechanism it was describing.

**The other three were priced before being refused**, and the prices are in `docs/DECISIONS.md`
rather than in a conversation: a budget large enough to fill the reference set by screening
costs about **400 hours** across 200 seeds and six worlds; a tolerance wide enough to accept at
a usable rate is about **0.41** standardised differences, which is not a balance criterion at
all; and a 50/50 holdout raises acceptance only to about **one draw in 800** — the same
starvation, at twice the cost in treated units.

**The contract moved as a restatement, not an edit.** `contracts/design/inference.yaml` is at
v2: `balance_tolerance_smd` keeps its value and loses one of its two moments — it was the screen
at design *and* the check at readout, and it is now **the check alone**, judged over the
covariates as they actually arrived; `max_assignment_attempts` keeps its value and now budgets
the reference-set scan rather than the screen's rejections. Both prior meanings are recoverable
in the file, and `NO_ADMISSIBLE_ASSIGNMENT` carries the same restatement in the closed
vocabulary: it meant *the screen rejected everything* and now means *no stratification gives
every stratum both arms*.

**The reference set did not change, and that is the load-bearing sentence.** Stratification is a
restriction on the space of admissible assignments exactly as the screen was, so a permutation
*within strata* is a draw "under the same restriction" in precisely the sense
`balance_covariates.yaml` already required. What changed is that the restriction became
constructive instead of rejective — the same claim about the inference, with arithmetic that can
actually be run.

**What it does not buy, measured in both directions.** Stratification does not make every draw
pass the readout's balance check: with 20 controls, a covariate the others carry no information
about keeps a sampling spread near the tolerance. On a roster whose covariates hang together the
way a chain's do, a clear majority of stratified draws pass; on a deliberately orthogonal roster
most do not, and both numbers are asserted in `tests/core/test_assignment.py` rather than the
comfortable one alone. The direction is the honest one — a refusal with a reason code, never a
number nobody can check — and it makes **W6's false-refusal rate a real figure for T003 to
publish** instead of 100% by construction.

**And one thing was deleted rather than kept.** `ordering` — the roster-wide sort the
unstratified draw was built on — has no caller once the control is the minimum inside each
stratum. Code that serves no claim is the fourth question on `CLAUDE.md`'s checklist, so it went
with its test rather than staying as a public function nobody calls. The suite is 756 and
`make claim-1` is still 9/9 with 13/13 mutations biting.

**What the instrument fix settled (T000), and why it came before the next four evals.** Claim 1's
eval is the shape every later eval is built on, and oversight level 2 found three defects in it.
All three are now closed, each with a test that fails on the un-fixed instrument.

**The misattributed figure.** "7,366 ladder quotes refused by a ceiling" was every quote refused
for any reason outside the three bounds the ladder models, counted as though all of them were
ceilings. **6,650 are `MARGIN_CAP_BASIS_UNEVALUABLE`** — a rule with no edge in either direction,
which a ceiling on the ladder would not move by one quote. The supportable figure is **716 of
26,600**, from one envelope. `G6` separates the two, publishes both, and the numbers are pinned in
the suite; `README.md`, `docs/DECISIONS.md` and `corpus/real/MANIFEST.yaml` all restate rather than
overwrite, so the delta is recoverable.

**The eval was rounding with the core's own primitive.** `_exact_floor` ended in
`Money.as_lower_bound` under a docstring claiming independence — the fourth instance of *a guard
tested by its author*, and like the first three it was declared impossible by prose beside the
code. The direction is now re-decided in `evals/guardrail/rounding.py` and carried out by integer
division of a `Fraction`, which shares no precision, no context and no quantisation with `Decimal`
and therefore cannot cancel a bug out with it.

**And `G3`'s one-cent tolerance was an exemption for one bug rather than slack for rounding.**
Every price in the eval is a whole number of cents, so under a correctly rounded core the
tolerance branch is unreachable; the only way into it is a bound sitting a cent *above* where the
rule puts it — the shape this repository's own history says its bugs appear in. `G3` and `G4` now
compare against a bound the eval rounded itself, with nothing tolerated anywhere.

**A new check, because `G2` and `G3` both go through a price.** A bound one cent out of place
opens a gap exactly one cent wide, and twenty-eight thousand certified prices can miss it.
`G10` compares every `Bound` the envelope placed against the edge the eval computed for the same
rule, **as integer cents with no tolerance** — 824,790 of them, 0 disagreements. Two mutations are
planted against it: the rounding primitive changing direction, and the margin floor built a cent
too strict. The second trips `G3` as well, which is the empirical evidence that the tolerance is
gone.

**The denominator is in the type.** `ProposedPrice.benchmark_margin_pct` named neither of the two
denominators a gross margin can be in, so 16.81% of the selling price could be applied where
20.21% of the cost was meant — safe, and silently wrong. `MarginOnPrice` and `MarkupOnCost` now
carry it, `as_markup_on_cost()` is the only route between them, and the field refuses a bare
number at runtime and not only where mypy runs. The half of the ambiguity that lives in
`regulated_basket.yaml` stays deferred: it is a contract change with a restatement chain.

The suite is **767** and `make claim-1` is **10/10 with 15/15 mutations biting**.

**Still missing from the "read this first" table:** `docs/SCENARIO.md` and `docs/DAY-ONE.md`.

### Closed in this phase

Claims 1, 2, 3, 4 and 7 — all provable local, with no account. **Claim 1 has closed.**

**Then an integration session**, before the next phase opens: read the whole repository against
`CLAUDE.md` and report conceptual drift. It builds nothing.

### Open

Everything that needs data at scale, an engine, or a workspace.

---

## Phase 2 — The pipelines, the metric contract's three consumers, and the model

### Work

- `pipelines/ingest/` — the Zerobus driver that writes as the corpus's 100 stores would: correct
  distribution over time, late arrivals, duplicates, a store that drops for two hours and then
  sends everything at once. The Lakeflow Connect definitions.
- `pipelines/silver/` — Spark Declarative Pipelines, with expectations routing to quarantine and
  the as-of reference dimension.
- `pipelines/gold/` — dbt. The metric contract compiles into a Delta view, the agent tool
  definition and the readout query.
- The two AI/BI dashboards as `databricks_dashboard` resources — experiment readout and decision
  monitor. The second is required by doctrine rule 2: without it, a fallback is not visible to the
  end. Both consume the metric contract, so both are claim 5 evidence.
- `evals/definition/` — the three mechanisms compared as integers, no tolerance.
- `pipelines/ml/` — the training code: time-based split, censoring correction, calibration gating,
  the promotion gates and a named approver. Proved **local** against a small corpus. The run that
  produces the deployed model happens on the estate in phase 3, where the data is.
- `make preview-audit` — the declared inventory of preview surfaces, and the check that no
  claim's proof path touches one.

### What closes this phase

`make claim-5` green against local Delta tables, and a trained model that the promotion gate
either accepts for a stated reason or refuses for a stated reason. **A gate that has never
refused anything has not been tested.**

### Closed in this phase

Claim 5. The pipelines and the training code, proved local.

**Then an integration session**, before the next phase opens: read the whole repository against
`CLAUDE.md` and report conceptual drift. It builds nothing.

### Open

Everything requiring a real workspace and a real bill.

---

## Phase 3 — The estate

The only phase that costs money. It is entered with every locally provable claim already green.

### Work

- `infra/bootstrap/` applied locally, once: state backend, OIDC, the deploy principal, and the
  budget posture — **1,000 USD with alerts at 50/80/100% and no stop action**, a stop action only
  at 150%. A budget that halts a run mid-way costs more than it saves. Enforcement is the TTL
  reaper in `foundation`, not the budget.
- `infra/foundation/`, `sources/`, `lakehouse/`, `pipelines/`, `ml/` applied by `deploy`;
  `infra/serving/` applied by `backfill`, once a model version exists. CI only. Layer boundaries follow lifetime, blast radius, dependency direction and apply cost.
- **Before this phase begins**, not inside it: verify the network path from the Databricks
  workspace to RDS that Lakeflow Connect's database connectors require, and record whatever has
  no API in `docs/DAY-ONE.md`. Discovering this during a paid run is the expensive way.
- `sources/` stands up the real Postgres playing the ERP. `backfill` seeds it with eight months;
  the **driver** changes it during `run`: a mid-day cost change, a product entering the regulated
  basket, a retroactive supplier term, an added column, a deactivated SKU.
- Five workflows: `ci`, `deploy`, `backfill`, `run`, `destroy`.
- **`backfill`** — eight months of history: ERP master data through Lakeflow Connect from RDS,
  transaction history bulk-loaded from files on S3 (streaming eight months through Zerobus is slow,
  costly and nobody does it). Then silver, gold, training on the estate, the gates, a registered
  version — and only then the `serving` apply, because an endpoint cannot point at a version that
  does not exist.
- **`run`** — one live day through Zerobus with lateness and duplicates, decisions routed by arm,
  two experiments (one produces a number, one must refuse), a live question answered at the
  endpoint, and the account asked whether it behaved. The driven day is **after** the trained
  history, so it is held out by construction.
- **`destroy`** — **never automatic**, on success or failure. It takes a target: `serving` kills
  the expensive layer in two minutes and leaves the lakehouse browsable; `all` takes everything.
  On failure the evidence survives; on success the estate is what the console recordings need. The
  TTL reaper in `foundation` is the guarantee, not the workflow.

### What closes this phase

A `run` whose every figure is asserted by a step that fails when it is not true — including at
least one experiment that produces a number and at least one that **refuses** for the right reason
— with the account confirming afterwards that nothing is left standing.

### Closed in this phase

The live evidence for claims 1 to 5. The cost model — 20–60 USD a cycle, 100–600 USD across the
five to ten cycles it realistically takes — replaced by a real bill.

**Then an integration session**, before the next phase opens: read the whole repository against
`CLAUDE.md` and report conceptual drift. It builds nothing.

### Open

The agent surface and claim 6.

---

## Phase 4 — The agent, and the number that matters

### Work

- The agent surface: what context it reads, the tool registry it is confined to, the structured
  design output, budget caps, traces.
- `evals/design/` — N designs proposed against a bank of business questions with known answers,
  M refused, and **K of the refused that would have produced a confidently wrong number**.
- The human path and the declared-policy path, exercised by the same engine to prove the engine
  does not care about the source.
- README, banner, article, debut post, promo.

### The shot list

| claim | where it is visible |
|---|---|
| 1 · guardrails | decision monitor, the guardrails that fired · `gate-proof` in a terminal |
| 2 · no false uplift | **the readout showing a REFUSAL** · the A/A rate in a terminal |
| 3 · locked holdout | the assignment table, read-only, with its seed |
| 4 · stock-out | a notebook: the same hour, with and without the correction |
| 5 · one definition | three windows side by side showing the **same** number |
| 6 · the engine refuses | the agent's design → the refusal and its reason code |
| 7 · no person | the decision key schema · the test that goes red |

### What closes this phase

`make claim-6` green with the three numbers printed, and `make gate-proof` refusing every planted
violation by name.

### Closed in this phase

Claim 6. The project.

---

## What this plan will not do

- **It will not claim causal identification outside the randomised design.** Observational
  elasticity ranks candidates. It never reports money.
- **It will not claim the feedback loop is solved.** The model trains on data its own decisions
  produced. Deliberate price randomisation limits this; it does not remove it.
- **It will not put a claim on a preview surface.** Real-Time Mode, metric views, domains,
  contextual policies and Genie Ontology are additive and removable throughout.
- **It will not claim optimality.** The claim is not that the decisions are the best available.
  It is that every number reported survives being checked.
- **It will not build a Genie replacement.** Backward-looking question answering is a commodity
  and is not where the value is.
