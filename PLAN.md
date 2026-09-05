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
  worlds, and the barrier holding over sixteen modules — see the progress note below. Restated
  2026-08-28 by T00E: 39.2M, because the chain's placement rule moved, and the scale claim 2 is
  proved at is `harness` — 320 stores — because the number that decides whether anything is
  provable is the roster that survives the design engine's exclusions.*
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
  *`evals/censoring/` landed 2026-08-29: claim 4 green at 12/12 with nine mutations, the correction
  graded on a held-out segment of full-availability store-days against receipt totals the corpus
  emitted rather than anything the generator knows — see the progress note below.*
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
3. **"The 2025 benchmark margin" is a 2008–2020 industry median.** The instrument anchors the
   benchmark to the trader's **own** 2025 rather than to a sector figure. The corpus documents
   describe the Eurostat figure as something its sources never state, and
   `corpus/real/README.md` reads an equivalence into άρθρο 4 παρ. 4 that the article does not
   contain.

   > *Restated 2026-08-31 by `corpus/legal-claims-restated`, and the correction is to this
   > finding rather than to the code.* The sentence read *"ΥΑ 21330/2026 άρθρο 4 παρ. 5 defines
   > the benchmark as the trader's own average, per product code, over 2025."* **παρ. 5 defines
   > Περίοδος Αναφοράς** — the reference period, per undertaking, keyed to that undertaking's own
   > last closed financial year. The per-product-code average is defined elsewhere in the
   > instrument. The finding's conclusion survives untouched; the article behind it was wrong.
   >
   > It is provable inside this tree with no external source, which is the part worth keeping:
   > `docs/REGULATORY.md` and `corpus/real/MANIFEST.yaml` both have παρ. 5 right and this line
   > had it wrong, in the same repository, for four days. **Two documents agreed, a third
   > disagreed, and nothing compared them** — which is the argument for `docs/FINDINGS.md`
   > rather than a footnote to it. A restatement that repeated this wording would have imported
   > the error into the fix.

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
code. The direction is now re-decided in `evals/guardrail/rounding.py` and carried out on the
value's exact integer ratio: no precision, no context and no quantisation shared with `Decimal`,
so a defect in any of those cannot cancel out between the two.

**And the size of that defect was itself overstated, which oversight level 2 caught by running
it.** This branch first said patching the primitive left `G2`, `G3` and `G6` all green. Planted
against `main`: `G2` **fails**, 199 violations in 28,681 certified prices, because `G2` compares
against the eval's *exact* `Decimal` bound and that never went through `Money`'s rounding. What
stayed green was `G6` — the one check that shared the primitive — while its published ceiling
count moved 7,366 → 7,365 in silence. A real finding, an order of magnitude smaller, and the same
defect one level up: prose in the evidence layer asserting more than the code supports. It is
restated in all six places that carried it rather than deleted.

**And `G3`'s one-cent tolerance was an exemption for one bug rather than slack for rounding.**
Every price in the eval is a whole number of cents, so under a correctly rounded core the
tolerance branch is unreachable; the only way into it is a bound sitting a cent *above* where the
rule puts it — the shape this repository's own history says its bugs appear in. `G3` and `G4` now
compare against a bound the eval rounded itself, with nothing tolerated anywhere.

**A new check, because `G2` and `G3` both go through a price.** A bound one cent out of place
opens a gap exactly one cent wide, and both checks see it only where a corpus price sits in that
gap. Measured, on an absolute floor moved a cent loose: `G2` reports **3** violations in 28,485
certified prices, `G10` reports **232,373** disagreements in 824,790 bounds. Three cases out of
twenty-eight thousand is a gate that holds until the corpus is reshuffled. `G10` compares every
`Bound` the envelope placed against the edge the eval computed for the same rule, **as integer
cents with no tolerance** — 0 disagreements over all 824,790.

**Three mutations, and the third is what earns it.** The first two are caught elsewhere as well,
which oversight level 2 correctly said proves nothing about `G10`'s necessity — so a third was
planted: **a bound at exactly the right amount carrying another rule's id.** No arithmetic moves,
no price is wrongly certified, no refusal loses its support, and `G10` is the only check in the
eval that goes red. Claim 1's evidence is *which* guardrail fired, and a certificate's recorded
checks are derived from those ids. The margin floor built a cent too strict trips `G3` as well,
which is the empirical evidence that the tolerance is gone.

**The denominator is in the type.** `ProposedPrice.benchmark_margin_pct` named neither of the two
denominators a gross margin can be in, so 16.81% of the selling price could be applied where
20.21% of the cost was meant — safe, and silently wrong. `MarginOnPrice` and `MarkupOnCost` now
carry it, `as_markup_on_cost()` is the only route between them, and the field refuses a bare
number at runtime and not only where mypy runs. The half of the ambiguity that lives in
`regulated_basket.yaml` stays deferred: it is a contract change with a restatement chain.

The suite is **768** and `make claim-1` is **10/10 with 16/16 mutations biting**.

**What T003 found before it built anything, and what it cost — 2026-08-28.** The A/A harness was
built as far as running the whole system once against the corpus, and stopped on the first
measurement: **end to end, the system produced no number.** `corpus/world/chain.py` opened every
second store inside the 1 km exclusion radius so W2 would always have interference to detect;
`feasibility` removed one member of every such pair so no store would measure its neighbour. Both
deliberate, both documented, both tested — and never multiplied together. 100 stores gave 109
pairs, 55 exclusions, a **roster of 45** and a control arm of nine, on which no lottery in two
hundred passed the readout's balance check and four of five world seeds were refused at moment 1.
Adding stores made it worse: 1,200 left a roster of 212, because the towns were a fixed size and
the estate got denser rather than larger.

*This is the first finding in the project that was in no file.* CI was green and every test passed,
because every test was about one of the two halves; a fresh-context reviewer reading either diff
would have found nothing either. It was caught by running them together, which is what an eval is
for — and it is the argument for having built claim 2's harness before its estimator.

Two tasks were inserted ahead of T003 and both have landed. **T00D** — a design that no lottery
could have saved is refused at moment 1 rather than accepted in silence and refused identically at
every readout forever; the case it is tested on is drawn by the corpus's own hashing and the
breaking control count is found by search. **T00E** — the corpus's clustering became a declared
per-world parameter (15%, and 30% in W2, the only world that needs interference to exist) and the
estate's density stopped moving with the scale. `HARNESS` is chosen on the **surviving roster**,
not the store count, and has more stores than `scenario` rather than fewer.

What the two bought, measured: the balance pass rate on the corpus's own roster went from **0 of
200** to **145–192 of 200** in the five ordinary worlds and **121–172 of 200** in W2. No threshold
moved — `balance_tolerance_smd` is still 0.10 and `holdout_share_pct` still 20% — and the new
refusal names the roster as its remedy rather than pointing at the dial. `CLAUDE.md`'s scale
paragraph is restated: **the size a claim rests on is the surviving roster, not the store count**,
and `make roster` is the command that prints it. The suite is **780**.

The rule that follows sits beside the two `CLAUDE.md` already carries — a guard tested by its
author, and a sentence written by its author. **Two components each correct on its own have no test
between them, and the number that would have shown it is a product nobody was computing.** Where
two deliberate decisions meet on a quantity, that quantity gets a name, a command and a figure.

**What claim 2 came out at — 2026-08-28.** `make claim-2` is green: **13 checks, 456 draws across
six worlds, 8/8 mutations biting.**

```
U1  aa-false-positive-rate     8/200 = 4.0% significant against alpha=5%
                               one-sided binomial p=0.7867 at level 0.01
U3  w6-false-refusal-rate      0/200 refused by the machinery, ceiling 10%
U4  w6-coverage                163/170 = 95.9% against a nominal 95%
U5  w6-estimator-bias          +0.59 EUR against a standard error of 1.02, over 170 draws
```

Beside them, with no threshold on it in this phase: W6 refused `IMBALANCED_PRE_PERIOD` on 15% of
draws, which is arithmetic about the roster rather than the machinery reporting on the experiment.

Every draw runs the whole system. The estimator was made five times cheaper by two exact
identities and the bounds are held bit-identical against the implementation they replaced.

**Three of the six worlds' declared behaviour changed, and every change was a measurement.** W5's
heavy tail was on a basket line, where sixteen thousand of them average it away — measured, its
standard error came out *below* the world with no pathology at all; it moved to the store-day and to
the half of the calendar a power calculation is not sized on. W2 states no number at all, and the
refusal is the power check firing on variance the spillover created — a refusal by luck, since
nothing in this system detects interference, which is now a deferral with the world that would
demonstrate it as the unlock.

**And the rule about sentences gained a third limb.** W2's line had already been restated once, on
2026-08-28, against the code — and the restatement was still wrong, because it was never run. *A
sentence naming what the system does when something goes wrong is written against the function that
would make it true, and against the measurement of what comes out when it runs. A line can be true
of the code and false of the system on the corpus.* Three wrong sentences about one table is a
signal that the rule was short a limb, not that somebody was careless.

**What the `claim` skill settled, and the finding it produced by existing (T00B).** The method for
building a claim end to end now ships with the repository, in `.claude/skills/claim/`, and it is
**extracted from the two claims that have closed rather than from one** — with one sample the shape
*is* whatever that sample does, and the extraction is a copy. It is deliberately a *procedure and
not a second copy of the shape*: `evals/README.md`, `evals/report.py` and
`evals/gate_proof/README.md` already carry the rules, and a procedure that restates them is the copy
that goes stale. What only two samples can give is the divergence table — an outside-the-repository
corpus against a generator behind an enforced barrier, one question against a rate tested as a
binomial, ten seconds a mutation against a small configuration declared in a contract, nothing
cached against a world cache keyed on a digest — each with the column saying what governs the
choice.

**Laying the two side by side found something no reading of either could.** `evals/README.md`
declares `<claim>/README.md` as part of the shape; claim 1 has one and **claim 2 does not**. Its
three answers are real — the attack in `__init__.py` and `checks.py`, the independence spread across
`potential.py`, `reference.py` and `cache.py`, and the third printed on every run through
`Report.notes`, which is the enforceable half — but there is no single place a reader finds the
independence argument. It is a deferral with T012 as its unlock and a date behind that, not a fix in
an ops branch: writing claim 2's evidence in a branch that is not reading the estimator line by line
is how a document comes to assert more than the code supports.

**And the rule about sentences was short a limb for the fourth time — this one was not a sentence.**
`ci.yml`'s `claims` job was given `timeout-minutes: 45`, projected from the author's fourteen-core
laptop onto a four-core runner, which cancelled the harness before it finished. It happened inside
the same change that **closed the deferral written to prevent it** — the 25-minute gate entry, whose
argument is that a budget set from a projection is a gate reporting which machine it drew. Nothing
was careless; the rule said *"a sentence"* and this was a YAML key, so it did not appear to apply.
`CLAUDE.md` now reads **an assertion — a sentence, or a number in configuration** — written against
the function that would make it true and against the measurement of what comes out when it runs,
taken on the hardware that will meet it. A timeout, a K, a tolerance, a threshold and a budget are
each that assertion wearing a number instead of a verb. The prior wording stays, per doctrine rule
4: a rule generalised from the form the known defects wore is a rule that cannot see the next one.

`tests/skills/test_skills.py` checks the wiring only — frontmatter, the name against the directory,
the description saying *when*, no unreferenced bundled file, every relative link resolving — and
says in its docstring that it cannot check whether the skill is right or whether it is followed. The
last two checks would have been vacuously green on the real tree, so they are armed by a planted
skill directory built inside the test, which is what `tests/ops/test_expiry.py` already does for
`make expiry`. The suite is **828**.

**T006 — `evals/oversight/`, `make claim-7`, and the fifth instance of this project's most
frequent defect · 2026-08-29.** Claim 7 said *the decision key has no customer dimension, and a
test goes red if one appears*. The test existed and was good. What nobody had asked was **who
wrote the words it looked for** — a tuple of person-shaped substrings, written by whoever also
wrote the field names it was checking, which is a guard tested by its author with no prose and no
gate behind it. Claim 7's row in `CLAUDE.md` was the one row of seven with **no trap written
beside it**, and that is exactly where it sat.

The answer is that the words are not ours. `corpus/real/` gained a second corpus under the same
four rules as the first: **156 schema.org properties** whose domain or range includes `Person`
(release 30.0, pinned) and **99 Presidio PII entity types** (pinned at a commit), both extracted
mechanically and kept in the publisher's own spelling. They yield **317 names**. Measured:

```
attacks planted                          17,752      317 names on each of 56 types
  refused by the closed field set        17,752
  refused by the hand-written word list   1,960      35/317 = 11.0% of the names
```

**Eleven per cent.** The list misses `family_name`, `given_name`, `nationality`, `job_title`,
`spouse`, `buyer`, `owner`, `recipient` and 274 others. That is not an argument for a longer list —
a longer list is the same function agreeing with itself more loudly — it is the argument for the
structure, and `O7` makes it a gate: no attack may ever be caught by the word list alone.

Twelve checks, **seven mutations, all seven bit**, and the two that earn their checks are the two no
field-set comparison can see: a `customer` **parameter** on `dispatch_to_shelf`, and a
`ladder_policy@v1.yaml` that becomes idempotent per customer with **no Python changing at all**.
The second one restated `gate-proof`'s independence rule, which had said the planter edits
`src/holdout/`: what matters is not which directory the planter may touch but which one it may
not — `ops/` and `corpus/real/` are the detector and are never mutation targets. `ops/personhood.py`
now holds the registry and the word list with two callers, the way `ops/isolation.py` holds the
corpus barrier.

Six of the twelve checks cannot have a mutation, because breaking them means editing the detector
rather than the system. They are armed by `tests/evals/test_oversight_instrument.py` on a
deliberately broken arrangement — the same answer `tests/evals/test_ledger.py` already gave for
`gate-proof` itself, which had never been written down as part of the shape. It is now, in
`evals/README.md`: **a check with no mutation names the reason it cannot have one, and is broken
deliberately somewhere.**

Two deferrals, both real. Claim 7 is proved over `holdout.core` and the contracts and nothing else
exists yet — unlocked by T011, because a scan against a `pipelines/` that does not exist is a check
with nothing to check. And the two vocabularies are pinned, so nothing notices a name published
after 2026-08-29; that ages the *net* and never the *guard*, and it expires on 2027-02-28.

**What the review cost, and the one thing it could establish that the branch could not.** Oversight
level 2 re-downloaded both vocabularies, wrote its own extractor without touching
`corpus/real/fetch.py`, and reproduced both committed CSVs **byte for byte** — 156, 99, six digests,
317 derived independently, and every ALL_CAPS token in the Presidio source that is not in the corpus
accounted for. **The extraction is mechanical; nobody filtered.** An author cannot establish that
about their own extractor, which is the whole reason level 2 is not a formality.

Then four blocking findings, and the shape of all four is the same. **The branch about guards tested
by their authors shipped three of them in its own work.** Its prose named `telephone` and
`personnummer` as names the word list misses — it catches both, because `PERSON_SHAPED` contains
`phone` and `person` and matches by substring, and the exemplars had been picked by reading the
lexicon rather than by asking the function that would make the sentence true. Its replacement guard
exempted any type whose name begins with `_` while printing the question *"is every type written
down"*; the reviewer renamed the class the mutation plants and watched it survive, so the registry is
now 49 and a seventh mutation plants `_VisitContext`. Its deferral said the scan covered the whole
system while `src/holdout/contracts/` — fifteen modules — sat outside `reference.CORE`, so a
`customer` parameter on `compile_agent_tool` would have gone unseen; the identifier scan now reads
all of `src/holdout/`, 820 → 1,181. And its restatement of `gate-proof`'s independence rule
enumerated what the planter *may* edit and was false of the committed set, because three claim-2
mutations edit `evals/uplift/`; it now names what it forbids, behind
`ledger.no-mutation-edits-the-detector` — the separation `engine.py` calls the one that carries its
argument, which until this branch had no function behind it at all.

`make check` green at **919 tests** · `make claim-7` **12/12 with 7/7 mutations biting**, 37s on the
laptop and **under two minutes on the four-core runner, on every CI run so far** — measurements
spanning 1m7s to 1m45s, uncounted on purpose, because a count of CI runs is stale by the next push. Stated as a bound because the three point estimates this line carried before
it were each overtaken: by a mutation landing, by the registry growing, and finally by the next run
simply being *faster*. The quantity has two independent reasons to move, so the span is evidence for
the bound rather than a second assertion.
*Figures restated after merging `main`: claims 3 and 4 added seven types and twenty fields to the
registry, so the products moved — 15,533 → 17,752 attacks over 49 → 56 types. The 35 of 317 and the
11.0% did not move, because they are properties of the two vocabularies and not of this estate.*

**Still missing from the "read this first" table:** `docs/SCENARIO.md` and `docs/DAY-ONE.md`.
*Restated 2026-08-30 by T007: `docs/SCENARIO.md` exists. `docs/DAY-ONE.md` is still absent and has
nothing to record until there is an estate — T015, before phase 3.*
*Restated 2026-09-02 by T015: `docs/DAY-ONE.md` exists, and the clause "has nothing to record until
there is an estate" was false when it was written. The estate's ERP path depends on a connector that
is in **Public Preview and needs enrolment through a vendor's account team** — no API, a lead time
nobody here controls, blocking `backfill` — which was knowable on any of the three days that
sentence stood. Both halves of the table are now present.*

**Claim 3 closed 2026-08-29 — the one door with no key, T004.** `make claim-3` is green at 10
checks over 36 declared configurations, with nine planted mutations of which nine bit. What the
piece settled is mostly about **what a reproducibility claim is allowed to be checked by**.

`draw` reads no clock, no environment and no random source, so calling it twice agrees with itself
by construction — and would agree just as loudly on a lottery that never consulted the committed
seed. That is claim 3's trap and it is not the shape the other claims wear. Three doors carry the
independence instead: **a second implementation** (BLAKE2b written out from RFC 7693 in Python,
with its own framing, rank arithmetic and selection, driven against the vector RFC 7693 Appendix A
publishes); **the per-unit path**, which re-derives one store's arm the way a readout a month later
has to, from the seed, the candidate index and that store's own stratum; and **another
interpreter**, three subprocesses under declared `PYTHONHASHSEED` values, which is the only way to
see a tie broken by set-iteration order. The mutation that makes `strata._hardest_to_match` scan
unsorted is invisible to every in-process repetition and bites there.

**The incentive is published as a number.** A better-balanced candidate exists for **15 of 30**
designs inside a 24-candidate scan, improving the worst standardised difference by **0.2422**
against a declared tolerance of 0.10. That is the size of the prize somebody holding the seed is
asked not to take, and every substitution — including the careful forger who recomputes the digest
so the seal agrees with itself — is refused, `CONTAMINATED_ASSIGNMENT` read off the refusal after
moment 3 has actually run.

**And one finding in the door itself, which closed in the same branch.** As first measured,
`contamination.check` derived the roster it walks from the arms it is checking, so a control store
deleted from the assignment table with the digest recomputed to match was invisible to it — 24 of
72 erasure routes, refused only by `readout.close` one function later. It was carried as a
deferral, and **oversight level 2 found the deferral wrong rather than the measurement**: `check`
already computes `redraw(seal)`, whose key set is the roster the lottery was drawn over, taken
from the committed strata — and then walked `seal.roster` one line later. The fix added no
argument and moved no signature. `A8` now asserts both layers, a ninth mutation reverts the line
that closed the gap, and `docs/DECISIONS.md` keeps the deferral beside its restatement.

That is the boxed rule pointed at a **deferral** for the first time: a deferral is an assertion
about what the system does, wearing a cost estimate instead of a verb, and this one was written
against an imagined fix rather than against the function that would make it true. `make expiry`
could not have caught it — it checks that an unlock condition is present, never that it is right.

**And one mutation survived on the first run**, corrected in the eval rather than by widening the
assertion: `strata_of` is order-independent by its own sorting, not because `CovariateMatrix.units`
is sorted, so `A4` was widened to compare the whole record the seal commits to.
`evals/assignment/README.md` §6 keeps that account.


**What claim 4 settled.** `holdout.core.demand.censoring` reads a store-SKU-day as one of two
**types**: the shelf held and the day has `units`, or the shelf emptied and the reading has
`at_least` and no `units` attribute at all — so a caller who wants a number has to say what it did
about the censoring, because there is nothing to reach for. The correction fits an availability
curve on days the shelf held and expands a censored day by the share of itself that was on sale,
and it answers with **no number** in the two cases where there is no evidence to expand: the shelf
was bare before the first sale, or it sold nothing before it emptied. Neither is a threshold
somebody chose. `make claim-4` is green at 12/12 checks with 9/9 mutations biting, in about a
minute.

*Where the independence is, which is the whole of claim 4's trap.* The curve is fitted on
store-days in the first 60% of the calendar on which the shelf held and graded on store-days in the
last 40% on which the shelf held — censored on purpose, the hours after withheld — so **the truth
each reconstruction is graded against is a receipt total the corpus emitted**, not a latent
intensity the generator knows. The grader never opens the generating process, and
`tests/evals/test_censoring_instrument.py` refuses the import in both directions. The generator
could be replaced with a different model of shopping and every published figure would still be a
measurement of the same thing.

*The numbers.* 16,942 of 80,640 store-days emptied (21.0%) — the one corpus figure. Everything
after it is measured on held-out days censored **on purpose**, where the withheld total is known:
reading the truncated number as the day's demand understates by **6.0% at the last trading hour and
91.4% at the first**, while the reconstruction lands within 0.1% of the withheld truth at a share of
0.94 and comes out **36–40% high at 0.06**. That overshoot is selection and the eval publishes the
evidence rather than the argument — the same expansion over *every* graded day, conditioning on
nothing, lands at −1.5% to −0.6% on the same hour. **No threshold is declared** at which the
reconstruction stops being usable: that number would have to come from real stock-outs, and this
eval constructs its own.

*What it cost to get honest, twice, and both from running rather than reading.* `checks.py`
declared two censoring shapes unreachable from the corpus and one of them is reachable — W5 empties
a shelf inside the first trading hour three times in 26,880 — found by `gate-proof` reporting
`CRASHED` rather than by anybody reading the corpus. And `C6` offered `fit` a censored day **on its
own**, so the mutation aimed at it reported `SURVIVED`: a `fit` that skipped censored days still
went red, but by a different guard. *A gate can only be shown to bite where it is the gate that
refuses.* Both were fixed in the eval, never by widening an assertion, and both are now rows in
`CLAUDE.md` — the fifth instance of *a guard tested by its author*, and the first one `gate-proof`
found rather than a review.

**T007 — `docs/SCENARIO.md`, and the rule a background document had to be written under ·
2026-08-30.** The file the "read this first" table has pointed at since the repository was opened
now exists: the operator and the three roles that touch the design form, the three decisions with
their horizons and the one legal provision that lets the fresh path actuate itself, the ten bronze
sources and the two committed corpora that are not ours, six things that make the problem hard, and
what the synthetic corpus does and does not model.

**It is prose full of numbers, which is this repository's most expensive shape.** Eight times now
the same defect: an assertion written against a table or a projection instead of against the
measurement of what comes out when it runs. A background document is where the boxed rule is
easiest to break, because nothing in it compiles, no consumer is generated from it and no gate reads
it. So every number in the file carries one of **four kinds** — `[M]` measured, with the command,
the scale and the seed; `[D]` declared, a contract value `make contracts` refuses without a
`source`; `[C]` cited, an instrument or a publisher with a verification date; `[S]` scenario, the
chain the system is written *for*, carrying the words *it has never run*. `[D]` and `[C]` are
deliberately two kinds and not one: a declared value this project invented is held up by a gate, a
cited value somebody else measured is held up by a citation and a date, and `docs/REGULATORY.md`
exists because they were once the same field. **Anything that fits none of the four is not in the
file**, and the two things that did not fit are named in it rather than dropped.

**The rule paid for itself inside the branch, which is the part worth keeping.** Recording a figure
as `[M]` means running the command again rather than copying it, and W5's did not come back the
same. At the same default seed `corpus/world/README.md` records **33,582,648** POS lines at
`scenario` and **4,588,490** at `harness`; the command prints **38,068,537** and **5,028,772**, and
W5's acknowledgements come out *above* W1's rather than 40% below, which is what the prose beside
the table asserted. W1 reproduces to the line at both scales, so it is not the seed — it is **T003
moving W5's pathology from the basket line to the store-day**, a change this file already records,
and counts taken before it. That README's own six-worlds table still read *"heavy-tailed baskets"*
while `worlds.py` had read *"Heavy-tailed store-day demand"* since the move. Four figures, one row
and two sentences are restated there rather than overwritten. **A measured table is measured only as
of the last time somebody ran it**, and `docs/DECISIONS.md`'s *"the scenario scale is measured by
hand, not by a gate"* deferral is the entry that had been carrying the risk — this is the first time
it cost anything.

**And one number was excluded for having nothing behind it at all.** `CLAUDE.md`'s *"ESL penetration
is ~30% of large European retailers"* is not `[M]`, not `[D]`, not `[S]` — and not `[C]` either,
because no publisher, no URL and no verification date sits behind it anywhere in the repository. It
is a fact asserted about the outside world with no source, which is the one shape the guardrail
contracts make a build failure and which nothing checks in prose. It is a `docs/DECISIONS.md`
deferral rather than an edit: rewriting `CLAUDE.md`'s envelope table inside a documentation task
would be a change made in the place it is least reviewed.

*The file republishes no claim's figures.* Those are each eval's evidence, printed on every run, and
a copy of them in a document nothing executes is the stale table above waiting to happen again.

**T008 — the phase-1 integration review, and the first thing it found was that it had nowhere to
live · 2026-08-30.** Oversight level 3 read the whole repository against `CLAUDE.md` and the report
is `docs/reviews/phase-1.md`. It is committed rather than delivered in a terminal, which is the
defect it catalogues ten times over: an assertion with no place anybody but its author reads.

**No claim's proof has collapsed.** The two independence barriers hold, the five closed claims are
green, and `ops.roster` reproduces the scale table `CLAUDE.md` restated on 2026-08-29 exactly. The
drift is in the layer around the proof, and it comes in three shapes. **Gates that count the wrong
thing:** `make expiry` has no notion of a deferral being closed, so its "35 deferred" includes three
that are, and its `next expiry 2026-09-30` points at an entry that closed on 2026-08-28 — the one
dated entry the registry credits with arming it. **Assertions never measured:** across 31 CI runs
`make claim-2` spans 32.2 to 77.1 minutes with the two *fastest* being cache misses, so *"generation
is about half the harness"* — carried in `ci.yml`, `docs/DECISIONS.md` and `evals/README.md` — has no
measurement behind it, and the cache key over-covers by digesting `corpus/real/`, which produces no
world. **Rules applied to one sample:** 21 of 57 checks own no mutation and 8 of those name no
reason, including three of claim 2's four published numbers; the rule requiring that reason was
written from claim 7 on 2026-08-29 and never applied backwards.

Two things landed here rather than in a later branch, both because they are sentences in the file
that governs every other branch. **Doctrine rule 7 is restated:** the repository holds three seals of
identical construction, each declaring that a coordinated forgery is not caught, so *today the
guarantee is detection* — unopenability arrives in phase 3 with the read-only assignment table, and
the door this rule names is `gold.experiment_assignment` rather than a Python type. And **an unlock
condition now has to name an event rather than a session**: nine open deferrals pointed at T008, so
the review whose job was to read arrived owing eleven decisions. Both prior wordings stay, per
doctrine rule 4.

**And the review found the tenth instance of this project's most frequent defect inside T008's own
task note.** `TASKS.md` instructs the session that renaming `floor.yaml`'s rule id turns `G10` red,
so move the contract and the eval together. `refuse_when_no_legal_price_sells` is never a
`Bound.rule_id` — `envelope.py` attributes six and it is not among them — so `G10` would not move at
all; what goes red is `O2`, because the id is a field name in `ops/personhood.py`'s registry. The
note was written against `G10`'s *argument* rather than against its six strings. **The nine known
forms were a sentence, a timeout, a deferral, a cost estimate, a stale measurement, a minuted
figure, a cache hypothesis and the rule's own statement; the tenth is an instruction to the next
session** — the form with the longest reach, because it does not describe the system, it aims the
hand that changes it. Nothing caught it: it was found by reading the six `rule_id=` lines.

The report's own conclusion is that the rule cannot be completed by widening it again. Ten
instances, ten forms, one invariant — *the assertion was checked against the artefact it came from
rather than against the thing that would falsify it* — which is already what the boxed rule says.
What it lacks is a gate, and `docs/SCENARIO.md`'s four-kinds discipline is the one mechanism in this
repository that has caught this defect by construction instead of by reading. Extending it to every
published number, with a target that re-runs the commands behind the `[M]`s, is the first of the
nine branches the report opens and the only one that stops the rest recurring.

**And the review's own §2 had missed the largest one, which the author found the next hour ·
2026-08-30.** *Has any gate stopped biting?* had the wrong answer, and the gate was the one that
decides whether anything merges at all. The `main` ruleset required `gate` and `secrets`. **T003
moved the claim targets out of `gate` and into the `claims` matrix, and the ruleset kept pointing
at `gate`** — so from that commit until `ops/claims-are-required`, **a pull request with a red
`claim-2` merged.** Oversight level 1's sentence, *a session cannot merge something that breaks a
claim, because the gate is structural rather than advisory*, was false at the level everything
else leans on.

**No reading finds it.** What the ruleset requires is a fact about the forge, carried in no file
here: `ci.yml` declares which jobs *exist* and never which are *required*, `make check` cannot see
it, no test touches it. The review read `ci.yml` line by line and measured 31 of its runs. The
fingerprint had been in `docs/DECISIONS.md` since 2026-08-27 — the entry's own verification quotes
*"2 of 2 required status checks are expected"*, and the **2** was the finding, unread because the
sentence beside it said which two and they agreed.

**One summary context, never a list of names.** `claims-complete` — `needs: [claims]`,
`if: always()` — fails on anything that is not `success`, and the case that matters is
**`skipped`**, because a skipped required check reports neutral rather than red and that is how a
matrix job passes silently. The ruleset requires that one context, so a claim landing tomorrow is
covered by nobody remembering anything; enumerating the targets there would be a second registry
of which claims exist, kept by hand where no session reads it.

**Verified by attacking, and it took three attacks because the first two proved less than they
looked like proving.** Hiding every `claim-N:` from `discover` (matrix `skipping`) and applying
claim 7's planted break 01 (matrix `failure`) both turned `claims-complete` red and both left the
merge `BLOCKED` — but `gate` was red in both, because `tests/evals/test_ledger.py` parses the real
Makefile and the decision key has a test of its own. That shows the job fires on both non-success
results; it does not show the context is **necessary**, which is this repository's own standard —
*a gate can only be shown to bite where it is the gate that refuses.* No committed mutation could
supply the isolated case either: number 16 was tried and `gate` went red, because
`ledger.every-anchor-is-aimed-at-one-place` requires each anchor to occur exactly once and applying
the mutation removes it.

So the third break was written fresh: **`cap_benchmark`'s bound attributed to
`markdown_max_depth_pct`** — right amount, wrong rule name, a certificate asserting a check that
never ran. `make check` **green at 919**, `G10` red with **156,294 disagreements in 746,643
bounds**, `gate` green, `claim-1` red, and the refusal naming one context:
*"Required status check `claims-complete` is failing."* **Before this branch that exact tree would
have merged.**

**What it cannot close, and the shape of the answer.** Nothing in this tree checks the ruleset
itself; remove the required context tomorrow and the job reports on into a void. Anything living
here can only be checked by something the forge has already agreed to run. So it closes as a
**question in a procedure** — *what does the ruleset require, and does it match the jobs that
exist today?* is now in T008's `closes` for the `integration-review` skill. It is the first rule
in this repository that is deliberately a question rather than a gate, because the thing it
guards is outside the repository.

**The method leaves the conversation, and it is written by the session that was not there ·
2026-08-31.** `skills/integration-review` closes `T008`. Oversight level 3 is now
`.claude/skills/integration-review/` — a versioned procedure that goes through a pull request like
everything else, rather than the ad hoc instructions the phase-1 review actually ran on.

**The extraction rule is the opposite of the `claim` skill's, and deliberately.** `skills/claim/`
was written from two closed claims by the sessions that closed them, because what it needed was
samples. This needed the other thing: **a session with no memory of the run.** The two sessions
that conducted the review are the worst placed to write down what it was, for the reason they are
the best placed — a method written from memory by whoever executed it is a copy of them, and
nothing afterwards can measure the difference between the two. So the session was opened cold,
told where to look and nothing else, and asked not to enquire further; **whatever the record could
not support was reported as a hole instead of supplied.** Seven of them are, and the largest is
that no measurement of what a level-3 session costs exists anywhere, so the skill sets no budget
and says so — `CLAUDE.md`'s rule about a number in configuration, applied to a number that is
missing rather than wrong.

**And the limits section is the experiment's result rather than a courtesy, because it is the one
thing here that was measured.** The brief the writing session was given **deliberately withheld**
this repository's *state what it does not prove* convention. It was cut in a second round of
leak-checking, on the argument that handing it over would make the draft's limits section
unreadable as evidence: it would come back with one, and we would have taught it. **Either outcome
was information** — a draft with *no* limits section, in a repository where every artefact has one,
would have been a real finding about the record.

It came back with one, unprompted, and the writing session named where it learned it:
`evals/README.md`'s rule 6, every eval printing its own silence, `docs/FINDINGS.md`'s standing
limit, `ops/figures.py` declaring what it does not cover. **So the convention is legible from the
files alone.** That is a finding about the repository and not about the skill, and it is the only
part of `#9` that was measured rather than reconstructed — because it is the one convention that
was removed on purpose. Everything else in the file could have arrived from the writer being a
competent session; this could not.

**What it does not establish, and the first clause is narrower than it was first written.** The
session was cold about the **method**, which is what the check was selecting for, and it was not
cold about the **repository** — it read eight files before writing a line. So the result is *the
record conveyed the convention to a session that had read the record*, which is exactly what was
tested and is weaker than *to a session that knew nothing*. Beyond that: one convention, one
session, one run. It says the record carries that convention, not that the method is
reconstructible and not that the skill is right. `tests/skills/test_skills.py` checks wiring, and
nothing checks whether a skill is followed. The second sample is `T016`.

**It is recorded here rather than in the skill, and the argument decided it rather than the
preference.** A skill claiming its own extraction was validated is the artefact certifying itself,
which is doctrine rule 5 in miniature and the shape both sessions spent the day refusing.
`PLAN.md` is a record of what happened; a skill is an instruction. The claim belongs in the
first.

**What the file is actually for is §4, and that is the part no participant would have written.**
The eight questions are recoverable from `CLAUDE.md` and the report's own headings. What is not is
the three places the phase-1 report was **wrong in its own report**: §2b concluding that the cache
saved nothing by citing the one cold run of eleven that fell below the warm mean, §3a asking *is
everything real listed* and never *is everything listed real*, and §2d — the ruleset — missed
outright and found by the author an hour after it merged. Three failures, no two alike. **A
procedure extracted from a run that only succeeded teaches the shape of success**, and a level-3
session is the one activity in this repository with no gate behind it at all.

**And the skill's own writing produced a finding, which is the argument for the phase boundary in
one line.** `CLAUDE.md` says level 3 runs *at every phase boundary, without exception*; `TASKS.md`
has `T016` and `T024` and nothing after phase 4. `PLAN.md` phrases each as *before the next phase
opens*, so the absence agrees with this file and disagrees with `CLAUDE.md`, and no reader of any
one of the three sees a defect. It is filed in `docs/FINDINGS.md`, adrift by declaration, because
which document moves decides whether the phase that closes the project is ever read for drift —
and that is the author's call, not a session's. **Level 3's own subject arrived while level 3's
skill was being extracted**, which is what the phase boundary is for.

**What the review cost, and it was the file's own subject.** The table of the review's eight
questions announced *six come from `CLAUDE.md`'s level-3 list* and listed five. The missing one is
**§6 — *is there still exactly one door with no key***, which is not a minor row: it is one of the
two findings that changed the doctrine, the three seals of identical construction and the accepted
restatement that **today the guarantee is detection** rather than unopenability. A session
following the draft would have asked seven of eight and never known, because the sentence above the
table said six.

**That is §3a's defect committed by the file that names it** — a coverage claim asserted in one
direction, a count never checked against the list it counts — and it is `CLAUDE.md`'s own note that
the rule does not stop applying to whoever has just finished quoting it. The row is in and the
arithmetic is written out rather than asserted: nine rows, eight questions, §0 a measurement and
not a question. **Found by the session that ran the six branches**, under the rule it declared
before the review began — *name the file and the line, or it is memory and does not go in* — and it
is the one finding of its four that was not its own writing read back at one remove, which is what
makes it worth more than agreement.

**And the branch could not be committed until the guard it exposed had been fixed.**
`.claude/hooks/main_guard.py` refused it twice, and the two refusals are one sentence: the guard was
judged against something other than the command it refuses. First the wrong **directory** — it read
the *session's* working directory, so a worktree provably on `skills/integration-review` was judged
against the shared checkout's `main`. Then the wrong **text** — it refused a command running no git
at all, because the file being written **quoted** a git command: an apostrophe unbalanced the lexer,
the coarse fallback took over, and that fallback found a separator followed by `git` inside the
prose. Its own comment named the second failure and said it was closed.

**Both were found by trying to do this work rather than by looking for it**, which is the level-3
property arriving on the branch of level 3's own skill. The drift was found by *using* the
repository and not by reading it — the same shape as §2d, the largest thing the review missed, which
no reading of `ci.yml` could have produced and which took asking the forge. Neither was worked
around and neither was fixed here: they are recorded in `docs/FINDINGS.md` by `#34` and repaired by
`#35`, which found two further spellings of the same defect while repairing it, and this branch
waited rather than routing around a guarantee. **The first thing this repository's newest guard did
was refuse the session that found its defect**, and the correct response to that was to wait.

**The guard was judged against something other than the command it refuses · 2026-08-31.**
`ops/main-guard-judges-the-command` fixes two defects in `.claude/hooks/main_guard.py`, found by a
cold session and oversight level 2 and **authorised by the author** — a hook is registered in
`settings.json`, the harness applies it whether a session consents or not, and it is the mechanism
that constrains what a session may do, so a peer's instruction was not enough.

**One sentence covers both:** the guard is judged against something other than the command it is
refusing — the wrong **directory** in the first, the wrong **text** in the second.

**The directory.** `main()` read `event["cwd"]`, the *session's* directory; `-C` was parsed only to
skip its value. So committing into a worktree on a branch was **refused**, and — the direction that
matters — `git -C <the checkout on main> commit` from a session on a branch was **allowed.** The
guard permitting exactly what it exists to prevent, in the arrangement `CLAUDE.md`'s git rule
requires when two sessions share a checkout. Never exploited: no direct commit to `main` has landed
since the hook arrived, verified commit by commit against the API.

**And the fix left the defect alive twice more, each time as a spelling the file already knew.**
The first repair enumerated `-C`, `--git-dir=` and `--work-tree=` and forgot the **environment** —
`GIT_DIR=` and `GIT_WORK_TREE=` were still allowed, though `_COARSE`'s prefix and
`_is_git_commit`'s skip both exist to handle environment assignments. The second forgot
`--git-dir <path>` **space-separated**, which sat in `_TAKES_A_VALUE` three lines above the
enumeration that omitted it. Each was found by reviewing the fix for the one before.

**So the finding is the pattern rather than the rows.** The same defect, three times, in one file:

> A flag or a variable this file already handles **for one purpose** is one it can be asked about
> **for another** — and the second question is asked by a different function, written later, by
> somebody reading the first list and not the file.

`_NAMES_A_REPOSITORY` is now a **subset of `_TAKES_A_VALUE`, asserted at import**, rather than a
second list kept in step by memory. Two lists of flags in one file, each missing a member of the
other, is how it reached three. And the comment above it — *an enumeration, not a proof of
completeness* — turned out to be right in a way its author did not intend: **a further spelling
was already in the file, within one commit of that sentence being written.** `_NAMES_A_REPOSITORY` now says in as many words that it is **an enumeration and not
a proof**, that an unrecognised spelling falls back to the session's directory *which is where the
original defect lived*, and — separately — that a target named **outside** the command by an
exported variable is a **limit rather than a defect**, because the hook is handed a command and
never an environment and no row can be added for it.

**The text, which is two defects wearing one description.** One needs **both** an apostrophe, to
unbalance `shlex` into `_COARSE`, and a shell operator inside the quoted text; the hook's own
docstring names *Don't run `git commit` here* as the case it closed, and that is the half-case that
works. The other never reaches `_COARSE`: `bash <<EOF` and `cat > f <<EOF` with **identical bodies**
get identical verdicts, and the second is wrong. **The two commands differ only in the consumer**, so
nothing about the body can separate them — the written-versus-executed distinction is not one option
among several but the only thing that carries it.

The body is excised for `cat` and `tee` with no `|`, `$(` or backtick — **a whitelist of two rather
than a classification of every consumer**, so the question is not *is this executed?* but *is this
one of the two forms that cannot be?*, which is a string comparison.

**And the accounting is what stops the next repair.** Two refusals happened. One was a false
positive; the other — a `python` heredoc, run while measuring the first — was a **correct refusal
that felt like one**. Its body executes and can reach git with no line beginning with `git`. **A
refusal recorded as a false positive is a refusal somebody later removes**, so the docstring and
`.claude/README.md` both say `python` is refused deliberately and the workaround is the editor tool,
not a wider list.

**Fifteen attacks, with the previous hook wrong on seven, and six tests that fail against it and
pass against this one.** The harness itself was wrong twice first — everything allowed because the
session had moved off `main`, then two heredoc cases still pointed at a branch and would have passed
with the heredoc logic deleted. **A vacuous green on exactly the two cases the fix exists for**,
caught by reading the table rather than the total.

`.claude/README.md` carried *"the safe direction, and a case that does not arise here"* about this
exact behaviour. Both halves were false, and the restatement stays beside them.

**A fourth candidate was tested and came back negative, and that is worth as much as the three
that did not.** `GIT_COMMON_DIR`, `GIT_OBJECT_DIRECTORY` and `GIT_CEILING_DIRECTORIES` were each
set alone against a second repository on `main`: **none makes a commit land there.**
`GIT_COMMON_DIR` was the right one to doubt, since it exists *for worktrees* and worktrees are the
fix's whole subject. The negative is recorded in the hook and in `.claude/README.md` with its
reason — the next person reaches the same list and would otherwise re-derive the same answer.

> **A method that only ever produces hits is indistinguishable from one that is finding what it
> went looking for.** *Ask rather than assert* changed the outcome three times today — the `python`
> heredoc, the `GIT_DIR` spelling, and this one. The first two were real. **This one is not, and
> recording it as a refuted candidate with its measurement is what makes the other two findings
> rather than confirmations.** A register of confirmed suspicions with no refuted ones would be a
> register worth distrusting.

**And one result in that measurement is unexplained, which is said here rather than smoothed
over.** Two probe forms disagreed on a *local* effect of `GIT_COMMON_DIR` — one commit succeeded
into its own repository, the other left that repository's `HEAD` unresolvable. The first
explanation reached for was invalid fixtures; re-running with verified repositories reproduced the
disagreement, so that explanation was wrong. **It is still unexplained.** What held across every
run is the only thing the fix depends on: the second repository's commit count never moved.

> **An unexplained result sitting beside a solid one, in the same measurement, at the end of a long
> branch, is where a clean story gets manufactured.** The honest shape is *I cannot account for
> this, and here is the invariant that never moved* — two statements, kept apart, rather than one
> reason stretched to cover both.

Not filed as a finding: it is a question about git's behaviour with no bearing on this repository,
and the register would be carrying something it cannot close.

**And CI refused the branch on a defect in the tests rather than in the fix — the third instance
of that family today, and the pointed one.** `tests/hooks/test_main_guard.py` creates real
repositories and commits into them, and **the runner has no global git identity**, so `git commit`
exits 128 there. They passed here because this machine has one.

    _layout_population   counted `notes/`, which exists on this disk and on no clean checkout
    the probe harness    assumed its cwd was on `main`, which had stopped being true
    these tests          assumed a git identity, which is a property of the machine

**The third is the sharpest: the tests proving the guard works could not run where the guard's CI
runs.** A guard verified only on its author's machine is most of the way back to where the branch
started.

**The repair is isolation rather than the symptom.** Supplying the identity fixes the one thing
that fired; `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` pointed at `/dev/null` make the fixture
independent of the machine's git configuration entirely — `init.templateDir`, `core.hooksPath` and
`init.defaultBranch` could each change what `git init` produces, and **pinning one of three while
inheriting two is how the first version passed here and failed there.**

**And the simulation of the runner was wrong twice before it was right**, which is the same
lesson one layer down. Nulling the global config alone did **not** reproduce the failure — git
falls back to an OS-derived name, and this machine has one. Forcing the name empty did reproduce
it, and then went too far the other way: an *empty* `GIT_AUTHOR_NAME` overrides `-c user.name=…`,
which the runner's *unset* variable does not, so it broke a pre-existing test that is fine on CI.
That test now takes its identity through the environment too, and the whole file passes it.

**And that claim is narrower than it first read, which is worth stating rather than trimming
quietly.** *Strictly harsher than the runner* is true along **one axis — configuration**: global
and system config nulled and the author name forced empty, all of which are stronger than the
runner's unset variables. It is **not** established along the others. The runner has a different
git version, a different platform and a different filesystem, and nulling config simulates none
of them — which is precisely where `init.defaultBranch` and `templateDir` defaults have differed
between git versions. **Strictly harsher in configuration; untested in version and platform, and
the CI run is what settles those.**

The suite is **994**.

**The guard reads git's own list, and the shell half is left as a decision · 2026-09-01.**
`ops/the-guard-reads-gits-own-list` closes the git-interface half of `main_guard`'s defects and
**deliberately does not close the shell half**, which is filed with its exposure measured.

**Two entries were missing and one was wrong**, settled against `git help git` rather than memory.
`--attr-source` and `--config-env` each accept a space-separated value and each let a `git commit`
past **unseen** — not the wrong repository, no refusal at all. `--exec-path` was present and should
not have been: its value is optional and must be attached with `=`, so listing it made the
subcommand hunt skip `commit` itself.

**And `--exec-path` is why the count was three and is two.** An earlier probe read `exit 0` as
*committed*; `git --exec-path commit` exits 0 and **does not commit** — it prints the path and
stops. Counting commits instead of reading exit codes removed a hole that was never there. *A proxy
for the question, failing for exactly the case under test.*

**The anchor is outside the file now.** `test_no_documented_option_lets_a_commit_past_the_guard`
asks one question over every option the manual documents — *did git commit, and did the guard see
it* — and **classifies nothing**, so there is no taxonomy to drift. It uses **two** repositories,
because an option that *redirects* leaves one repository's count unchanged and reads as harmless,
which is how `-C` stayed invisible for this file's whole history. It fails against the previous
hook, naming both escapes.

**What is left open is a decision, not a gap.** `cd` and `pushd` are not parsed at all —
`cd <a checkout on main> && git commit` from a branch session is allowed and **the commit lands**,
measured by counting. No list is being added for them, because **three enumerations were shown
incomplete by measurement in one day** and adding a fourth is the move the whole sequence argues
against.

The exposure is bounded and was read from the API rather than quoted: the `main` ruleset is active
with **zero bypass actors**, so a commit reaching local `main` cannot reach `origin` by anyone. The
rule is enforced twice — imperfectly here, completely at the boundary — and on that surface this
hook's job is to catch the mistake early, not to be the thing that prevents it.

**And the framing that looked obvious is wrong.** Classified two ways — surface against family —
both families appear on **both** surfaces. *Targets are closeable, detection is not* does not hold:
`cd` is a redirect and it is open; `--attr-source` was a hide and it is closed. The line falls
between git's interface and the shell, and only the first has been enumerated against.

The suite is **1001**.

**The skill exists, and the column that says so had nothing checking it · 2026-09-01.**
`docs/the-skill-exists` makes `CLAUDE.md`'s skills-table row true — `integration-review` moved from
`T008` to **exists** when `#36` landed — and closes the gap that update revealed.

**The row would have gone false at the moment of the merge.** It read `T008`, meaning *a task that
will produce this*, and the task produced it. That is the shape the status column was added to stop,
occurring on **the column's own first occupant**, one day after it was added.

**And nothing enumerated the column against the directory.** The column exists because the table
listed **four** skills as living here and one did. Adding it fixed the count and left the count
unchecked — so a third status going stale would have looked exactly like the two that did not. That
is the same defect the column was added to fix, one layer up, and it was mine: I added the column
and did not add the gate.

`make figures` gains a **`skills`** row: **2 = 2**, the population being every directory under
`.claude/skills/`. And a second check for the other direction, because the coverage comparison is
one-sided by design and this question is not — **a table naming a skill that is not there sends its
reader looking for it**, which is the repository layout's pair arriving in a second place. Both
directions were made to bite before either shipped:

```
skill exists, table does not mark it   →  skills: 1 of 2 never looked at
table claims a skill that is not there →  refused by name
```

**And the first test of the two was a vacuous green until it was checked.** It patched
`skills_the_table_marks_as_existing` on the module — but `COVERAGE` captured the callable at
**import**, so the patch never reached the row and the test passed against unmodified behaviour. The
row is rebuilt instead, which is what the layout narrowing test already did and what this one should
have copied. **A test asserting a gate bites, that does not reach the gate**, is the day's shape in
its smallest available form.

The suite is **1000**.

**The cache was never measured, and the branch that would have measured it never existed ·
2026-08-31.** `evals/world-cache-measured` closes the review's §2b and §2c — the last of the eight,
and the one nobody opened.

**It was proposed on 2026-08-30 and never became a branch.** For a day, two sessions filed
measurements into it by name — the determinism result, three within-commit pairs, the budget
argument — and nothing could say so, because a branch name is a representation like any other and
this one named nothing. `docs/DECISIONS.md` carried *"the change `evals/world-cache-measured`
makes"* as an unlock condition pointing at a place that did not exist, and `make expiry` could not
see it: **it checks that a condition is present and never that it is reachable.** Found by a session
that measured the nine-branch plan against `git log` instead of believing either of us.

**§2b's conclusion reverses, and so does ours.** It said the cache *saves nothing measurable*, from
31 jobs; we restated that to *the benefit is unmeasurable*. Re-pulled from the Actions API —
**71 successful `claim-2` jobs**, min 32.2, median 53.8, max **78.3**, sd 10.0 — and split by
whether the job logged a world-cache hit:

```
warm  n=60  median 50.8  mean 49.8  sd  7.0
cold  n=11  median 70.0  mean 68.2  sd 10.2
cold - warm = +18.4 min · 95% CI +13.5 to +23.2 · t = 7.43
```

**All 71 jobs carry one digest over the sources that can change a world**, so the cold arm computed
exactly what the warm arm did. The confound — that cold runs are cold *because* the work changed —
is dead by measurement rather than by argument.

**And the figure is narrower than *what the cache saves*, which is what this entry first called it.**
Every cold run in the sample was a **spurious** invalidation, so 18.4 is what a spurious
invalidation **costs**. The two quantities share a number here only because no run in this sample
ever needed to regenerate; where the world sources genuinely change, regeneration is necessary work
no cache can save. The sample lies inside **one world-source epoch**. That limit was stated in
review and **did not reach the branch until oversight level 2 grepped for it and found it absent** —
the fourth restatement chain today to stop at the terminal, and the first where the missing half was
the caveat rather than the correction.

**Which means all eleven cold runs were spurious**, and the over-coverage bug has a price:
`DEPENDS_ON = ("corpus", …)` covers `corpus/real/`, which cannot produce a byte of a world.
**202 minutes — 3.4 hours — already spent** on caches thrown away for changes that could not alter
what they held. `corpus/legal-claims-restated`, merged today, is one of the four commits that did
it.

**And §2b reached its conclusion by citing the one counterexample.** It named a cold run finishing
in 44.8 minutes: of the eleven cold runs, that is **the only one below the warm mean**. The section
was right that `ci.yml`'s assertion had no measurement behind it, and wrong in the conclusion it
drew instead — which are different failures, and ours was a third turn of the same one.

**The 90-minute budget stays, and its unlock condition had been met sixty times.** *The first CI run
with a warm world cache* has happened sixty times while the entry stayed open — the mirror of the
dead pointer, and `make expiry` is blind to both for one reason. The ceiling is not lowered to the
warm steady state: the slowest draw observed is a **cold** 78.3, and a budget set from the warm mean
fails every time the key moves.

**A gate was built for the missing branch, measured, and refused on its own numbers.** Four declared
positions enumerate 49 branch names with no judgment — that half works. Classifying them merged,
open or nowhere does not: **12 of 49 wrong**, including six merged branches called `nowhere` and
this branch called `merged` because its own name appears in a commit message. The cause is
structural — a squash-merged branch leaves no ref, so offline git cannot tell *merged and deleted*
from *never existed*, which is the pair the gate exists for. Three options are filed with their
costs.

**And checking the best of them found something I wrote this morning.** `TASKS.md`'s registry could
serve as the landing record — it already has the shape — but four of its entries name branches that
never existed, and **two are mine, from `#32`, four hours old.** The column reads `branch <name>`,
singular; an atom that spanned three branches had no way to say so; leaving it empty was not
offered. **I invented a branch name to satisfy a schema.** That is a new form and `CLAUDE.md` now
names it: the assertion was not unchecked, it was *manufactured by the shape of the form*, and it is
the more dangerous kind because the artefact looks more complete afterwards. The generalisation was
run over every required field — one instance, fixed; the rest are prose, repeatable, or single by
nature.

The suite is **981**.

**The documents are made to agree with the code · 2026-08-31.**
`docs/the-documents-agree-with-the-code` closes the review's **§3a, §3b, §3c, §3e and §7's second
half** — proposed as three branches and done as one. They could never have run concurrently,
because all three rewrite the same paragraphs in `CLAUDE.md`, `PLAN.md` and `TASKS.md`; work that
can never be parallelised is one piece written down as three because the review found it in three
sections. Four sequential matrices became two, with nothing changed about CI.

**The layout section was wrong in both directions, and only one was reported.** It omitted
`core/demand/` and the whole of `src/holdout/contracts/` — fifteen modules — plus `generated/`,
`tests/` and `notes/`. It also listed `pipelines/`, `infra/` and `experiments/`, **none of which
exist**, in the same present-tense block. Those are now marked as declared-not-built, which is the
same defect as a paragraph asserting a production path through dbt while both implementations are
Python — corrected in the same branch, a few hundred lines apart.

**And the section now has a gate — in both directions, which took two attempts.**
`make figures` gains a **`layout`** row: **20 = 20**, the population being every top-level content
directory plus every package under `src/holdout/`. Taking `core/demand/` back out — the review's own
omission — turns it red at 19 of 20, and `tests/ops/test_figures.py` does exactly that.

> **The first version of this paragraph said naming a directory that does not exist is
> over-coverage and therefore not a lie, and that was wrong.** Oversight level 2 refused it while
> CI was still running. The one-sided rule is about a **tool** examining more than exists, which is
> a tool doing more than it was asked. **A map is not a tool.** A map naming a directory that does
> not exist sends its reader looking for something that is not there, which is worse than an
> omission rather than harmless — and it was half of what §3a actually got wrong.
>
> **The gate as first written could not see it at all.** `layout_packages_named` iterates the
> directories that exist and counts how many are named; a name matching no directory is never
> iterated over and contributes to neither side. `pipelines/`, `infra/` and `experiments/` could
> have gone back tomorrow and the row would still read 20 = 20. That is **#31's F1 one file
> along** — a guard permitting exactly the thing its branch exists to end — for the second time in
> two branches, and this time inside the branch whose subject is documents disagreeing with code.
>
> So there is a second check rather than a second row, because the coverage comparison is
> one-sided by design and this question is not: **every `name/` outside the declared-future block
> must resolve to a real directory.** The phase-2 block is excluded **by declaration** — isolated
> by its own heading, the way `make language` excludes paths by a written reason rather than by a
> rule somebody has to infer. Putting `infra/` back into the present-tense block turns it red by
> name.
>
> **And the review made the same one-directional mistake.** §3a asked *is everything real listed*
> and never asked *is everything listed real*, which is why a review about that section reported
> five omissions and none of the three fabrications sitting beside them. Three instances are now
> recorded in `CLAUDE.md` **with no rule over them**, and the argument for waiting is written
> beside them: a rule generalised at three would be scoped to the forms these three wear, which is
> the mistake it would be about.

**And then CI refused the gate, on the one defect `make check` structurally could not find.**
`_layout_population` walked the working directory with a hand-written exclusion list, so it counted
**20** on this laptop and **19** on the runner: `notes/` is gitignored scratch, and it had been
added to the map as though it were repository content. Green locally, red on CI, and the local run
could not have known — **the population was being enumerated on the machine the measurement was
taken on.**

That is `CLAUDE.md`'s fourth form of the rule — *where the number will be met on hardware that is
not the author's, the measurement is taken there* — occurring **inside `ops/figures.py`**, the
module that exists to enforce it. The exclusion list is gone: `_layout_population` asks **git**,
which removes the judgment with it. `.github/` is repository content by the same test as `.claude/`
and is now in both the population and the map, and neither is there because somebody decided so.
A test pins the property — nothing git ignores may appear in the population — so the next version
cannot drift back to the working directory.

**Claim 4 was 11/11 in five places and the eval has never printed anything but 12/12.** `C12`
arrived in the same commit that closed the claim, so the number was never right — not once, with no
moment of agreement to drift from. It passed oversight level 2 on that branch. Measured before
correcting rather than taking the review's word: `make claim-4` → **12/12 checks, 9/9 mutations
biting**.

**Two restatement chains that stopped at `CLAUDE.md` now reach the end.** *"1,200 stores left a
roster of 212"* is withdrawn in both places that carried it as a measurement — `--scale` admits four
names and the largest is **320 stores**, so no declared scale reaches 1,200. And the `Scope` entry
in `docs/DECISIONS.md` finally has its reversal underneath it, which is that file's own opening
rule and the one reversed decision in it was the one without one.

**Doctrine rule 1 admits an empty safe state.** It said the ladder *is* the safe state for an
expiring product, which reads as a guarantee that something legal always exists to fall to.
`ladder.quote()` takes a floor and no ceiling, so where the margin cap binds below the base price
the declared safe state produces prices the envelope refuses — **716 of 26,600**, published by `G6`
on every run. Nothing in the code was wrong and no assertion was widened; the sentence had a silent
case. The ladder taking a ceiling stays deferred on its own limb: it is a contract change.

**Smaller, all measured rather than copied.** `docs/REGULATORY.md` claimed every `verified_on` reads
2026-08-27; counted, it is **69 · 15 · 1**. The skills table listed four skills as living here and
one does — it now carries a status column, and names `contract-change` and `defect-to-rule` as
having **no task id anywhere**, which by this file's own rule is forgotten rather than deferred. The
closed registry called itself complete and stopped at L9 while **nine** atoms had closed after it;
L10–L18 are added and the gap is filed, because a hand-maintained copy of `git log main` with no
second enumeration is the coverage rule in a document.

**And a test was identifying findings by a key that is not unique.**
`test_the_two_founding_findings_were_entered_before_their_fixes` selected `by_date[1]`, which named
the orphan finding only for as long as nothing shared its date. A finding filed on 2026-08-30 by the
same review broke it. That is `every-anchor-is-aimed-at-one-place` inside the test that guards the
register, and it now selects by title.

The suite is **981**.

**A rule id named for what it measures, and a window read in its own vocabulary · 2026-08-31.**
`contracts/floor-rule-id` closes the review's §7 half that T008 was empowered to move, with §3d's
correction inside it. `refuse_when_no_legal_price_sells` claimed a demand question the envelope
never asks — whether the item would sell — where the rule performs arithmetic: the legal range is
empty, floor above ceiling. The refusal code shed that overreach four days ago and became
`NO_PRICE_SATISFIES_EVERY_GUARDRAIL`; the id kept it, because renaming inside a live window is a
contract edit and the deferral said so.

**Closed through the unlock condition rather than around it.** The opening window closes at
2026-09-01 and a new one opens carrying `refuse_when_no_price_satisfies_every_guardrail`. The closed
window keeps the old id, which is what contract rule 1 is for. **No value moved** — `true` in both —
so no past decision is judged differently and no published figure changes.

**And the deferral had not anticipated the cost.** It named the window, the restatement chain and
anything that had recorded the id. One more thing: **the closed window has to stay readable.** Every
decision dated before 2026-09-01 resolves against it, which on this corpus is all of them, so the
resolver cannot simply look for the new spelling. `envelope.py` gains **`RENAMED_RULES`** — each
window read in its own vocabulary — and it **refuses a window carrying both spellings**, because two
rules with one meaning leave nothing able to say which was in force. Emptying the mapping turns the
suite red, which is how it was checked rather than assumed.

**§3d's correction confirmed by running it.** The task note said a rename turns `G10` red on both
directions at once. It does not: `refuse_when_no_legal_price_sells` appears **zero** times in
`evals/guardrail/reference.py`. What goes red is `O2` — the id is a field name in the closed field
set — and putting the registry back gives `FAIL O2 · 55/56 types agree`. The tenth form of the rule
was an instruction to the next session, and this is the next session declining to follow it.

**Filed, not built: `claim-2` costs an hour and the matrix re-runs on every push.** Sharding across
the six worlds is the large safe win, a merge queue is second, and **path filtering is refused by
name** — it buys back a claim that silently does not run. Its own branch, before the first Terraform
layer. The practice adopted today at no cost: finish locally, run the gates, **push once**. The
suite is **978**. It was written as 975 and then as 976, each a real measurement that my own next
edit made stale — which is the *measurement that went stale* form of the rule rather than the
projection form, and the second time in one session that this entry's own subject bit its author.

**And oversight level 2 found the mechanism had no time bound.** As first written, `RENAMED_RULES`
was keyed by guardrail and canonical id alone. Nothing scoped an old spelling to *when* it was
valid, so a window opened in **2027** carrying the retired id resolved without complaint — the
retired name alive and in force in a window written months after the branch that retired it, which
is this branch's whole purpose undone. Nothing else catches it: `ops/personhood.py` reads dataclass
fields rather than the YAML, and the both-spellings guard does not fire when only one is present.
It reproduced before it was fixed. `Renaming` now carries `since`, and both halves are tested —
the refusal, and the historical window still resolving, so the fix is a time bound and not a ban.

**And the fix tripped two of this repository's own gates on the way through, which is the part
worth keeping.** `make findings` reported `MOVED` because the anchored line was rewritten; the
finding was not fixed — the map got *more* elaborate — so the anchor was re-aimed and the reason
written down. Then the new `Renaming` type was refused by the closed field set until it was written
into `ops/personhood.py`, which is claim 7's guard doing exactly what it says on a type that
appeared an hour ago.
**A check is armed, or it says why it cannot be · 2026-08-31.** `evals/unarmed-checks` closes the
review's §1. `ledger.every-claim-target-owns-a-gate` asked the question at target level, which one
mutation satisfies for a claim with twelve checks — leaving **21 of 57 checks with no mutation and 8
of those with no reason**, three of them numbers claim 2 publishes.

`Check` gains `unarmed_because` and `make gate-proof` prints three states:
**37 armed · 23 declared un-armable · 7 unarmed**. The third is reported and not refused, for the
reason the findings register reports `adrift`: refusing it buys a sentence where a mutation belongs.
What is refused is a check both armed and excused, because one of the two is then untrue.

The reasons turn out to be exactly three — the break would edit the **detector**, the check asserts
a property of the **inputs**, or the check is **absent from the configuration a mutation runs at**.
The ledger's own ten are among them, armed by `tests/evals/test_ledger.py`, which is the arrangement
that already existed and had never been part of the written shape. Checks are found by **parsing**
`evals/` rather than importing it, because importing an eval means being able to run it.

**One of the eight was armed rather than excused**, and it bit alone:
`17-a-refusal-arrives-without-its-detail` blanks a refusal's detail — no bound moves, no price is
certified, no code changes — and `G7` is the only check that falls. Claim 1 is **17/17**.

**Arming it found that G7's other half cannot fail**: `reason.code.value not in declared` is a dead
branch, because `reason.code` is a `RefusalCode`. Filed in `docs/FINDINGS.md` rather than patched,
since rewriting a check while proving it bites means the mutation was written against a shape nobody
reviewed. The register is now **6 findings, 4 open, 2 closed**.

And the uncovered half is published on every run: **seven of the eight `at_design` codes are reached
by no eval**, living only in cases their own author wrote, over exactly the vocabulary claim 6 will
count N and M against.

**Then oversight level 2 read the branch cold and found four things, three of which went in.**
The reviewing session was the same session that wrote the branch, resumed with an empty context —
which is the whole property level 2 needs and is available exactly once, before the author
re-derives their own reasoning.

**The wrap corrupts what is not prose, and this is the third instance.** Sixteen of the twenty-three
new reasons were reflowed on character boundaries: `It is arme d instead by`, `a pro perty`, `a diff
erent check`, and one code span broken open as `` ` src/holdout/` ``. Put beside the deferral regex
that required `· deferred DATE` on one line and missed ten wrapped headers, and `ops/figures.py`
breaking its own pattern by rewrapping the sentence that corrected it, the family is specific:
**these files are wrapped to a column and the wrap is applied to things that are not prose** — a
regex's target, a pattern, a string literal. The first two are a pattern failing because text
wrapped; this one is text corrupted by wrapping, and it is the second kind, which must not be
wrapped at all. Nothing catches it: `make language` matches a character range and ruff will not
rejoin a literal.

**The branch created a population and did not have it enumerated twice.** `CLAUDE.md` says every
gate declares how its population is enumerated and `make figures` enumerates it a second time — and
this branch shipped a gate over sixty-seven checks with no second reading. `make figures` gains an
**`armed-or-says-why`** row: **67 = 67**, walked from `PYTHON_DIRS` rather than `CHECK_SOURCES` and
resolving whatever name `Check` was imported under, so two different starting points and two
different matchers. Narrowed to one eval it reads **10**, and `tests/ops/test_figures.py` narrows it
on purpose. The branch's own mitigation was `assert len(...) >= 9` — a frozen count selecting on a
naming convention, which is the shape `CLAUDE.md` forbids in the same breath as the rule it served.
It is now the property: **every check written inside `evals/gate_proof/` carries a reason**, a
population no rename can move.

**And `C7` carried the same defect as `G7`, in the same commit.** `C7`'s stated reason for being
un-armable was that half of it is a tautology — an assertion of a dead branch sitting in prose, in
the branch whose subject is that such assertions get filed. Its sufficient reason was always the
corpus one, and that is what it now says. Recorded as a **second site on the existing `G7` entry**
rather than a new one: one fact gets one entry, which is what this register had to learn in its
first hour when one entry was answering for two defects.

The fourth is filed and not fixed: **a mutation may name a check that does not exist**, caught only
by the expensive target. Measured at **0 of 37 targets naming nothing** today. The suite is **972** — a figure that went in as **976** first, projected from "one test
added, one replaced" instead of measured, inside the change whose subject is that a number is set
from a measurement. Which is how the fifth finding was found: **that count is published where no
gate can read it**, because `PROSE` excludes `PLAN.md` so history stays green. Sound for the six
superseded figures above it, silent about the one that is present tense.

**And the author settled the half that was never ours: real inputs, derived cost · 2026-08-31.**
The prose sites were defects and got fixed. What was left was a judgment about the product — a
corpus presented as real whose concrete benchmark is a construct the regulation does not use, either
an acceptable declared limit or a claim the corpus should stop making. The decision: **wherever the
corpus is described as a whole, the wording names all three parts** — real prices, real law, derived
cost — and *real* does not stand alone with the derivation in a footnote.

Six sites carry it. `docs/SCENARIO.md` and `CLAUDE.md` were checked and left: neither ever claimed
the cost was observed, and the sweep is over places that overclaimed rather than over the word.

*Why the wording and not the data.* No public source carries a retailer's cost and none will. There
is no version of this corpus, rebuildable from published sources, in which the cost is observed — so
the choice was never *fix it* or *leave it*, but **say what it is every time, or say it once and let
the rest read as though everything were sourced.** The second is what was there: the README named
three real things and omitted the cost, and the manifest header said every price, category and
margin came from somebody else, which is true and silent about the number the envelope turns on.

**And the founding finding closed through the mechanism** — `*Closed:*` with the transition, a
`*Now:*` for each of its three sites, and the closing text held to the same exactly-once rule for as
long as the entry exists. `1 open, 2 closed · closed and still held 4 line(s)`. The one still open
is §4, adrift by design until somebody scopes it with the module in front of them.

*And a test froze a status for the third time today.* `legal.is_open` was true when written and the
finding legitimately closed. First `len(findings) == 2`, then a status — both true when written,
both holding a **state that is supposed to move** rather than the property that must not. What must
not move is that the two entries were filed open before any branch touched them, so their `found`
dates are asserted and nothing else is. `make findings` prints open, closed, adrift and concurred;
nothing asserts them, because every one of those numbers is supposed to change. The suite is **965**.

**The legal claims restated, and the second half of the scope turned out to exist already ·
2026-08-31.** `corpus/legal-claims-restated` closes the older of the register's two founding
entries in part and the newer one whole.

**The prose.** Five sites: `corpus/real/README.md` (the equivalence, and the claim that it made
`m / (1 − m)` exact — algebra made to rest on law), `corpus/real/MANIFEST.yaml` (the same
equivalence in the provenance record, the copy a reader trusts most), `evals/guardrail/build.py`
(*"The published 2025 gross margin"* — neither 2025 nor published, at the point closest to the
arithmetic), `PLAN.md` (the finding's own miscitation of άρθρο 4 παρ. 5, which defines the
reference period and not the benchmark), and `benchmark.py`, whose narrow claim **holds** and got a
verification date rather than a rewrite.

**The benchmark half was already built.** Measured before writing any of it: the core takes a
benchmark per proposal and bounds each decision against its own; the contract carries a name, never
a level; only the corpus flattens it, at four call sites. **The scope asked for a shape that
exists** — an assertion about the code made from something other than the code, one layer out from
the defect the branch was opened for.

What remained had two disguises. A per-code margin computed from the corpus's own derived cost
returns `m` exactly for every code; a per-item signature returning one constant is per-code
structure around a single number. Both read as fidelity. So the flatness is carried by a **name**:
`sector_wide_benchmark()`, met four times before anything else, refusing the inference at the place
it was made.

**Measured against the baseline the branch diverges from** — `b7ab2ae`, not the `f0a9994` the scope
named, with the two verified byte-identical for claim 1 first. **232,373 decisions, 10 checks,
sha256 `22a6daea…` on both sides.** A refactor that provably moves nothing, stated as a number.

**And the register bit on its author within an hour of landing.** Rewriting `PLAN.md`'s site removed
its anchor and `make findings` went red, asking a person whether the finding was fixed or the anchor
stale. It was neither: one entry was answering for two defects with different fixes and different
landing dates. Split — and the citation half **closed through the mechanism**, with `*Now:*` still
being checked, rather than being demonstrated after the fact.

That exposed an interaction neither session saw at design time. Doctrine rule 4 keeps defective
wording beside its correction, so three restated sites kept their anchors and the one that was
*rewritten* lost its. **An anchor detects drift and revert and cannot detect *fixed*** — and an
anchor vanishing therefore means the repository's own convention was not followed there, which is
exactly when a person should look. Declared in `docs/FINDINGS.md` as an interaction rather than a
shortcoming.

**And a frozen count went red on a legitimate split.** `len(findings) == 2` — a number standing in
for the property it protected, inside the work about numbers standing in for things. The property is
asserted now and the count is printed by the target and claimed by nobody. The suite is **965**.

**An open finding gets a home, because it was the one thing that had none · 2026-08-31.**
`docs/FINDINGS.md` and `make findings`. Every mechanism here was aimed at a claim, a gate or a
deferral; an open review finding is none of the three, and two fell out. The legal half of oversight
level 2's third blocking finding against claim 1 — recorded 2026-08-27, closed never, deferred
never, absent four days later. And `docs/reviews/phase-1.md` §4, dropped by that review's own
closing table, the one that assigns every other section to a branch.

**A finding anchors to a line that already exists** and goes red when that line stops saying what
the finding says it says — `ledger.every-anchor-is-aimed-at-one-place` over a new population. No
site, no disposition, or a `*Closed:*` with no transition: refused. A disposition of `none —
<reason>`: reported as **adrift**, because a finding nobody has scoped is a real state and refusing
it teaches people not to file.

**Closure restates a site rather than releasing it.** The first draft let a closed entry stop being
checked; the reviewing session found the hole before it landed — a finding that stops being examined
the moment somebody accounts for it is a claim about the past reading as a claim about the present,
and that is exactly what hid the legal finding's third part. Every site gets a `*Now:*` with the
text that replaced the defect, held to the same exactly-once rule, or `gone — <reason>`.

**`concurred` is not `closed`.** Closure is a transition — the anchored line changes, a branch lands
and the gate goes red-to-green, or a named human says so. Agreement between the reviewing and
building sessions is a fourth state, carried as open and counted apart. It exists because it nearly
happened: the reviewing session removed §4 from the author's list because the two sessions
concurred, and that is the mechanism by which the legal finding was lost — *not a decision to drop
it, but two parties who held it agreeing it was handled.*

**Both entries went in open, before either fix branch**, which is `gate-proof`'s first rule and not
a preference: an entry filed with the answer already known is a mutation planted against something
already broken.

**And the two fail differently, which is what tested the design.** The legal one had two sides that
drifted, caught by the anchor check by construction. §4 never had a second side at all, so a
two-sided comparison would find nothing to compare — it is caught only by *adrift*, specified for
completeness rather than for a case anybody had. A mechanism meeting a case its author did not have
in mind **before it shipped** is what this phase has repeatedly failed to arrange, and it arrived
free.

*What it cost while being built, and both were gates working.* The registry needed a Greek term the
vocabulary did not have, `make language` refused the file until it was declared with a reason, that
made the vocabulary nineteen, and `make figures` then refused `ops/language.py` for still saying
eighteen — after which correcting the sentence rewrapped it out of reach of its own pattern, which
is the reviewing session's wrapped-header failure reproduced within the hour by the mechanism
written to catch it. Every prose pattern now spans whitespace. The suite is **959**.

**`make expiry` learns what closure is, and the rule from the day before had not been applied to
what already existed · 2026-08-31.** `ops/expiry-knows-what-closed` closes the report's §2a and
turns out to be bigger than the report said.

**The false alarm is gone.** The target read headers and had no notion of closure, so an entry whose
finding had already returned stayed among the live ones and its date went on ticking. `next expiry
2026-09-30` pointed at the CI-gate-timeout entry, **closed on 2026-08-28** — the only dated entry in
the registry and the one it credits with arming the target at all. A `*Closed:*` marker is read like
the other two, a closed entry cannot expire, open and closed are counted apart, and `next expiry` is
now **2026-11-30**, which is real.

**The standing limit becomes a number.** *A condition is prose and cannot be evaluated* was written
honestly in the module's docstring from day one; what it never was is countable. The run prints
`checked for TRUTH 4 of 33 (12%)` beside `checked for PRESENCE only 29 of 33` — `make figures`'
question turned on the target itself. Published, not gated: a condition-only deferral is legitimate
by the registry's own rule, and what is refused is not saying how many there are.

**And the thirteenth form of the recurring defect, which is the sharpest so far.** On 2026-08-30
`CLAUDE.md` gained *an unlock condition that names a session rather than an event is not a
condition; it is a date without a calendar.* **The registry was not swept when the rule was
written.** Nine open entries reached for "the phase-1 integration session" — five as the condition,
four as a fallback — and that session had already happened without answering any of them. The twelve
before it were rules that went stale or numbers written against a projection; **this one was correct,
published, and simply never run against what already existed.** It is the fourth finding's shape —
two things each right on its own with no test between them — pointed at a rule and a document.

Six were given the branch that closes them and three had a real condition already and only lost a
fallback clause. Nothing was invented. What is not enforced is stated: telling a session from an
event means reading English, so the test asserts the state the sweep left rather than pretending to
be a gate.

**Measured here, and a different count arrived with the instruction.** 35 headers, 2 closed, 33
open, 4 dated, 29 condition-only, 5 + 4 + 8 by how they name their unlock. The figures that came in
were 25 / 5 / 20, and the explanation is the same rule again: that count used a regex requiring
`· deferred` on one line, and **ten headers wrap** — the exact case `ops/expiry.py` carries a
comment about. It saw 25 of 35 and reported as though it were all of them. Third instance of
`make figures`' rule in three days, second from the reviewing side, and both found by re-execution
rather than by reading. The suite is **943**.

**The rule that had no gate now has one, and it turned out to be about coverage · 2026-08-30.**
`ops/every-number-carries-its-kind` closes the report's §8. Two events were the same defect at two
coverages and nobody had called them the same thing: `grep -P`, absent, giving **zero** from a
check that never ran; and `discover` matching `claim-[1-7]`, which could not have seen a
`claim-8` — and `claims-complete`, the required check, aggregates only what `discover` emits, so a
claim could have landed with its gate never running and the merge would have been green.

> **A gate reports on what it examined. It becomes a lie when it reports what it examined as if it
> were what exists.**

**Every gate declares how its population is enumerated and `make figures` enumerates it a second
time** — `evals/README.md`'s rule 5, *a boundary that has to be known is computed twice*, pointed
at coverage instead of arithmetic. Six gates come out: `lint`, `typecheck`, `language`, `expiry`,
`gate-proof`, `discover`.

**Two deviations from how it was asked for, both deliberate and one of them measured.** The
population is declared as a **rule, not a `[D]` value**: a frozen count is an assertion needing its
own measurement, which is the defect this branch exists to close. And the comparison is
**one-sided** — red when `examined < exists`, never the other way. Measured on ruff 0.16.4: 190
files reported against an independent count of 182 `*.py`, the eight being Markdown, because ruff
formats Python inside fenced blocks and has since a version nobody here chose. Freezing either
number would go red on that upgrade for a reason that is not a defect. Only under-coverage is a lie
about what exists — `Money`'s rule one layer up.

**And one thing does not come out: `test`.** A suite's *examined* is what actually ran, known only
after it runs, while `make figures` runs before it in the same `make check`; asking pytest to
collect twice measures collection against collection. Recorded as uncovered rather than covered
badly. **The prose half is deliberately small** — two registered figures, and `PLAN.md` and
`TASKS.md` excluded because doctrine rule 4 keeps superseded figures here forever, so re-running
them would go red on history that is correct as written. Which text asserts the present tense is a
judgment, so the registry is written by hand and its size is printed on every run.

**It found something on its first run against itself**: a number in its own docstring, stale by two
before the module was committed. The fix was to **date** it rather than update it — a measurement
of a moment supporting an argument about direction is not an assertion about today, and that
distinction is what makes the prose half tractable.

**Proved by two attacks, and the second is the one that matters.** Removing the instrument is
`tests/ops/test_language.py`. **Narrowing** it is `tests/ops/test_figures.py` — a path outside the
walked list, and `claim-[1-7]` against a Makefile carrying a `claim-8`, which is the exact state
`main` was in until this branch. Narrowing is the shape no reviewer notices, because the gate still
runs, still prints, and still says what it always said. `discover` is widened to `claim-[0-9]+` and
gains a floor of 6 that `make figures` checks against the Makefile, so a deleted target cannot
shrink it in silence. The suite is **937**.

**The review was in the wrong language, and the rule that says so was enforced nowhere ·
2026-08-30.** `docs/reviews/phase-1.md` landed on `main` carrying **12,803 Greek characters**, in
a public repository, against `CLAUDE.md`'s first line. It is translated on `docs/review-in-english`
with nothing in its content moved, and the rule is now `make language`, inside `make check`.

**Not a blanket ban.** Three kinds of Greek are load-bearing: a verbatim article of an instrument
(translating a statute is a paraphrase of law, which doctrine rule 3 refuses), published data
somebody else wrote (digest-checked, so an edit is already a red build), and the symbols alpha,
beta and tau. So the exceptions are two closed lists in `ops/language.py`, each entry with its
reason — **five paths and eighteen tokens**, and the eighteen were measured before the list was
written rather than guessed. A path allowlist wide enough to cover the citations in `src/`,
`tests/`, `evals/` and four documents would have admitted Greek nearly everywhere and would not
have caught the review.

**And this gate is shaped differently from every other one, because of how the violation was first
mis-measured.** The check was run with `grep -P`, which BSD grep on macOS does not have. It exited
1, `2>/dev/null` hid the reason, and *no matches* and *no such option* are the same two characters
on a terminal — a count of **zero** reported from a command that never ran the check. That is the
twelfth instance of *a guard tested by its author* and its form is new: not a sentence, not a
number in configuration, but **a tool that was not there**.

> **The silence of a missing instrument is indistinguishable from a pass.**

So `ops.language` will not report green until it has answered for itself: the detector fires on a
sentinel built from code points, the walk read more files than a declared floor, and every declared
exception is still in use — the last being claim 7's `O12` argument one directory along, since an
unused exception is a pre-approval for whoever writes that token next. All three are attacked in
`tests/ops/test_language.py` by removing the instrument, and each attack requires a red run;
verified live as well, with the detector edited into something that cannot match. **It found one
thing while being built:** the first draft of that test wrote its Greek fixtures as literals under
a comment claiming they were code points, and `make language` refused it — the gate biting the test
written to prove it bites. The suite is **928**.

The generalisation — *a gate goes red when its own instrument is missing, proved by an attack that
takes the instrument away* — lands in `ops/every-number-carries-its-kind` beside the four-kinds
rule, as a second requirement of equal standing. It is deliberately not asserted here: this branch
is one gate meeting the rule early, not the rule existing.

### Closed in this phase

Claims 1, 2, 3, 4 and 7 — all provable local, with no account. **All five have closed**,
and claim 2 is the one CLAUDE.md calls the one that separates this from a demo.

**Then an integration session**, before the next phase opens: read the whole repository against
`CLAUDE.md` and report conceptual drift. It builds nothing.

### Open

Everything that needs data at scale, an engine, or a workspace.

---

## Phase 2 — The pipelines, the metric contract's three consumers, and the model

### Work

- `pipelines/ingest/` — the Zerobus driver that writes as the corpus's stores would, at whatever
  scale `corpus/world/scale.py` declares: correct distribution over time, late arrivals,
  duplicates, a store that drops for two hours and then sends everything at once. The S3 bulk
  load, which is the ERP path.
  *Landed in two branches, the driver on 2026-09-03 and the bulk load the same day. The drops
  differ because the corpus's cost ledger steps during the day — measured at smoke scale, three
  steps on the driven day and five drops declaring 0, 2, 0, 1, 0 newly visible rows — and at
  `harness` scale nine days in ten carry none at all, so the driven day there is picked rather
  than found. `corpus/world/` gained the Parquet target the deferral named, written out of the
  standard library and read back by pyarrow in the dev group. Of the five intra-day changes the
  phase-3 bullet below names, this corpus supports the cost change and no other — see T009's
  landing note in `TASKS.md`.*
- `pipelines/silver/` — Spark Declarative Pipelines, with expectations routing to quarantine and
  the as-of reference dimension.
  *Landed 2026-09-03. The expectations are written by hand: they are native to Databricks
  Lakeflow and absent from the open-source framework this repository runs, measured by printing
  the installed package. The engine sits in its own extra, so 713 MB and a JVM land on one CI job
  of twenty. Silver builds against local Delta with the quarantine non-empty on planted bad data,
  the stock-out derived from movements rather than copied, and the as-of join carrying both
  `effective_from` and `known_from` — the second only because the ERP drops several times during
  the day. See T010's landing note in `TASKS.md`.*
- `pipelines/gold/` — dbt. The metric contract compiles into a Delta view, the agent tool
  definition and the readout query.
  *Landed 2026-09-04. Families A and C only, and the four tables that are absent are named with
  their reasons rather than built empty. dbt runs in-process against the SparkSession this
  repository configures, and reaches `generated/dbt/models` through `model-paths` rather than
  copying it — so no copy of a compiled artefact exists under `pipelines/` and `make contracts`
  is the only definition check gold needs. Python owns the as-of join, because silver's
  `cost_as_of` already is it; dbt owns everything downstream. The tests run at `rehearsal` and
  not at `smoke`, because at smoke this corpus throws nothing away and the primary metric's third
  term would be a sum over an empty table on a green run.*

  *Executing the artefacts for the first time found three defects in them and the contracts moved
  each time, which is what `docs/DECISIONS.md` ruled in advance: a dbt file name that is an
  identifier no engine can parse, a single version parameter applied to three tables whose Delta
  counters are independent, and — this branch's own — `file_format` in a dbt profile, accepted,
  ignored, and green over five parquet tables. See `T011`'s landing note in `TASKS.md`.*
- The two AI/BI dashboards as `databricks_dashboard` resources — experiment readout and decision
  monitor. The second is required by doctrine rule 2: without it, a fallback is not visible to the
  end. Both consume the metric contract, so both are claim 5 evidence.
  *Landed 2026-09-04, and the atom's own stopping condition was measured before it was trusted:
  `terraform validate` passes a dashboard whose `serialized_dashboard` contains `select nonsense
  from table_that_does_not_exist where 1=`, because that field is a string. So **both dashboards
  are a fifth compiled consumer** of the metric contract — the readout screen's dataset SQL **is**
  `compile_readout(metric)`, the same call `generated/readout/` is written from — and `make
  contracts` byte-compares them. The check tiles come from `at_readout`'s own `check` field and
  the monitor names all twelve `at_decision` codes, so nothing on either screen is typed by hand
  that a contract declares.*

  *And the screen `closes` calls the single most important screenshot in the project **has no data
  source**: `gold.readout` does not exist and the compiled readout returns per-arm metric rows with
  no uplift and no reason code. Its columns are the fields of `holdout.core.experiment.Readout`,
  compared in both directions by a test, so the naming is honest — but the row still has nobody to
  write it, and that goes to `T016` beside `T014`'s missing model-to-scenario join. See `T013`'s
  landing note in `TASKS.md`.*
- `evals/definition/` — the three mechanisms compared as integers, no tolerance.
  *Landed 2026-09-04, and the first thing it measured argues against it: **two of the three
  mechanisms `CLAUDE.md` names are one mechanism.** The dbt model, the SQL function and the
  readout all render from `metric_parts` in one compiler and their arithmetic is byte-identical,
  so comparing them proves Spark is deterministic. The fourth named consumer, the agent tool
  definition, computes nothing and cannot be a mechanism at all — `D4` holds it to the contract's
  terms instead. So the eval builds the two mechanisms that were missing, differing in **order of
  operations**, and the compiled SQL is the load-bearing third because it was compiled by a
  different mechanism at a different time. Non-sharing prevents shared code, not a shared
  misconception, and that limit is stated rather than papered over.*

  *Green at 481 cells over `W6` at `rehearsal`, `D1`–`D4`, 3 of 3 mutations biting. **One of those
  cells was written by the eval**, because the corpus cannot exercise the contract's `rounding` at
  all: every corpus cell is an exact number of cents, so `half_even` and `half_up` never part
  company. The same plant survives on 480 corpus cells and bites on the constructed one — a
  controlled comparison where only the data changed, filed against the contract and the corpus in
  `docs/FINDINGS.md`. See `T012`'s landing note in `TASKS.md`.*
- `pipelines/ml/` — the training code: time-based split, censoring correction, calibration gating,
  the promotion gates and a named approver. Proved **local** against a small corpus. The run that
  produces the deployed model happens on the estate in phase 3, where the data is.
  *Landed 2026-09-04, and the first thing it measured narrows what it claims: **the model cannot
  answer the question the decision path asks it.** `core.pricing.Scenario` takes `expected_units`
  per candidate price, and on this corpus price is a deterministic function of hours-to-expiry
  within an arm — W1 has one discount level per hours-bucket, W6 has two, and within `(hours, arm)`
  there is exactly one. So the only price contrast anywhere is the arm contrast the readout exists
  to measure. `CLAUDE.md` names the remedy and it is not built, so the pipeline forecasts units at
  the price the policy sets and says so, rather than declaring an elasticity — which would be
  inventing the number a model exists to learn.*

  *What is built is the apparatus a model is judged by, and every gate is planted against by name:
  a systematically optimistic model, the do-nothing baseline, two segments wrong in opposite
  directions, a corpus too thin to judge, a model fitted on too little history. Two of the plants
  assert a gate **passes** — the baseline must be refused by the RMSE gate and not by the
  calibration gate — and one test requires all five to pass, because a gate that has never passed
  is as untested as one that has never refused. `Promotion` cannot be constructed without a
  `human:<name>`, so doctrine rule 5 is a type here rather than a sentence.*

  *Two declared thresholds were convicted by the first measurement — an RMSE ceiling of 6 units
  against a corpus averaging 34, and a per-segment tolerance of 10% against a segment standard
  error of 5.13% — and both are now relative to something the data supplies. The model's own shape
  was chosen the same wrong way and corrected the same way: `(category, weekday)` scored 33.48
  against a do-nothing baseline of 35.58, and `(sku, weekday)` times a store factor scores 14.09.
  See `T014`'s landing note in `TASKS.md`.*
- `make preview-audit` — the declared inventory of preview surfaces, and the check that no
  claim's proof path touches one. *`terraform validate`, which shared its deferral, landed
  2026-09-04 with `T013`'s first Terraform layer and is in `make check` and CI's `gate`.*

  > **Not delivered by `T012`, and `TASKS.md` said it would be. Restated 2026-09-04.** That block
  > read *"`DECISIONS.md` defers it to exactly here"*; the deferral says *"the first Terraform
  > layer, **and** the first time a preview surface is considered"*, and `evals/definition/` is not
  > a Terraform layer. **The surface that fired the other half is gone too** — route 2 removed the
  > Lakeflow Connect Postgres connector — so the inventory is **undetermined rather than empty**,
  > and a gate over an undetermined population would report *no claim's proof path touches a
  > preview surface* while nobody knows what the surfaces are. It moves to phase 3, with the first
  > layer, and Zerobus's own status is `T015`'s open question.
- `docs/DAY-ONE.md` — the manual work with no API, written **before** phase 3 and read as a
  checklist rather than as a record. Listed here because T015 is a phase-2 atom and this list
  did not carry it. *Added 2026-09-02 by T015.*

### What closes this phase

`make claim-5` green against local Delta tables *(done 2026-09-04)*, and a trained model that the
promotion gate either accepts for a stated reason or refuses for a stated reason *(done 2026-09-04:
five gates, twelve plants, and a run in which all five pass on the honest model)*. **A gate that has never
refused anything has not been tested.**

### Closed in this phase

Claim 5. The pipelines and the training code, proved local.

**Then an integration session**, before the next phase opens: read the whole repository against
`CLAUDE.md` and report conceptual drift. It builds nothing.

**It ran on 2026-09-05 and `docs/reviews/phase-2.md` is what it produced.** Twelve proposed
branches, `T00N`–`T00Z`, and one thing that is not a branch.

*Every claim target was run rather than inherited, `make eval-uplift` included — 13/13 at
`harness`, 8m33s warm — because the phase-1 report never said whether it had run claim 2's eval and
the `integration-review` skill names that silence as a hole in its own record. Claim 5, `silver` and
`gold` were run in an isolated environment with the `dbt` extra so that the shared checkout's
virtualenv was never touched.*

**Two findings came from attacking rather than reading, which is the half a level-3 session is
least likely to do.** A mutation planted on `metric_parts` — the mechanism claim 5's own printed
note calls *the load-bearing third*, and the one none of its three mutations touches — left `make
contracts` **green at 15/15 bytes** and claim 5 **red on D1 and D2**. That both arms the gap and
demonstrates, rather than argues, why a byte comparison cannot stand in for the claim: a
wrong-but-consistent compiler agrees with itself. It also surfaced the finding underneath —
`_disagreements` stops at five and publishes the truncated length as the check's figure, so **349
missing cells printed as `5 disagreeing`** under a docstring that says *every*.

And the corpus barrier's **runtime** half blocks one of the two spellings `ops/isolation.py`
declares: `_Refuse(("holdout",))` does not block `src.holdout`, and with that finder installed
exactly as the test installs it, `importlib.import_module("src.holdout.core.money")` returns
`Money`. `tests/boundary/conftest.py` says a test *"plants both spellings"*; `src.holdout` occurs
nowhere in that file. **This is the barrier claim 2's answer to *your simulator is rigged* rests
on**, and the repository's own history records the same spelling costing the source half once
already.

**The largest section of the report is not a defect in anything.** §15 puts `T013`'s half and
`T014`'s half beside `TASKS.md` and measures that **three joins on the path phase 3 drives have no
implementation and no task id**: `Scenario(...)` is constructed only under `tests/core/`,
`experiment.close()` is called only from `evals/`, `gold.readout` is read by the compiled dashboard
and written by nothing, and no module under `pipelines/` takes a trigger and produces a decision.
`T023`'s `closes` requires the output of two of them. **Each half was filed by the atom that found
it and each was correct to say it was not theirs** — a gap with no owner is the one kind that
survives every atom — and nobody had asked the registry which atom owns the wire. The answer is
none.

**So phase 2 closes and `T017` may open; `T023` cannot close as written.** Either the joins become
atoms placed before `T021` — a pipeline layer that deploys jobs ought to know which job writes the
readout — or phase 3's scope is restated to the demonstration this corpus and this code can give,
and the shot list moves with it. Both change what the project shows rather than how it is built, so
both are the author's, and the choice has to be taken before `T018`.

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
- `infra/foundation/`, `lakehouse/`, `pipelines/`, `ml/` applied by `deploy`;
  `infra/serving/` applied by `backfill`, once a model version exists. CI only. Layer boundaries follow lifetime, blast radius, dependency direction and apply cost.
- **Before this phase begins**, not inside it: verify the network path from the Databricks
  workspace to RDS that Lakeflow Connect's database connectors require, and record whatever has
  no API in `docs/DAY-ONE.md`. Discovering this during a paid run is the expensive way.

  > **Restated 2026-09-02 by T015, because the first half of that bullet is unachievable and the
  > second half was done.** The workspace is created by `foundation` and the RDS by `sources`, and
  > **both are in this phase** — so there is nothing to verify a path *between* until the phase has
  > started, and "before this phase begins" cannot be met by anybody, funded or not. What the
  > sentence was protecting is real and unchanged: discovering it during a paid run means five
  > applied layers standing and billing while somebody debugs networking. So the instruction splits
  > — **the design and the no-API residue are recorded now**, in `docs/DAY-ONE.md`, and **the
  > assertion runs at the earliest moment it can exist**: immediately after `sources` applies and
  > before `backfill` is dispatched. The prior wording stays per doctrine rule 4, and the delta is
  > the finding: *a sentence naming when a check happens is an assertion about what the system does,
  > and this one names a moment at which its two endpoints do not exist.*

  > **And restated again 2026-09-02, one day later, by the ruling that removed the endpoints
  > altogether.** The author ruled the ERP's master data arrives as files on S3, so there is no
  > connector, no gateway and **no RDS** — `T019` closed *not built*. The bullet above and the
  > restatement under it both describe a verification of a path between two things, one of which
  > will never exist. Both stay per doctrine rule 4, and the pair is worth reading together: the
  > first restatement moved *when* the check runs, the second removes *what it was checking*.
  > **A sentence can be corrected onto ground that is itself about to go.**
- The ERP's master data arrives as files on S3. `backfill` loads eight months of it;
  further drops change it during `run`: a mid-day cost change, a product entering the regulated
  basket, a retroactive supplier term, an added column, a deactivated SKU. **What that
  demonstrates is incremental load of successive drops, not change capture against a live
  source** — the smaller claim the ruling bought in exchange for *serverless only*.
- Five workflows: `ci`, `deploy`, `backfill`, `run`, `destroy`.
- **`backfill`** — eight months of history: ERP master data bulk-loaded from files on S3,
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
