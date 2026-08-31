# Decisions

What was decided, why, and what would change it. A decision that lives only in a conversation is
not a decision — it is a thing somebody remembers differently next month.

Every entry carries the date it was taken. Where a decision has been reversed, the original stays
and the reversal is written underneath it, because the reasoning that produced the first answer is
usually still the best argument against the second.

---

## Scope

**The scenario is 1,200 stores. The corpus is 100.** · 2026-08-24
Roughly 100 stores across three fresh categories over eight months — about 36M POS lines, a few GB
of Parquet. This is a cost decision and nothing else. **Claim 2 does not get stronger with 1,200
stores**; it gets stronger with 200 seeds and six adversarial worlds, which run local and cost
nothing. Where a figure depends on corpus size it is reported as such and never extrapolated to the
full estate.

**Three decisions, one stream, and only one actuates itself.** · 2026-08-24
Markdown on expiring fresh actuates automatically; base price by zone is a proposal to a human;
a joint plan with a supplier goes through a Clean Room. The middle one is not a policy statement —
**no actuation path exists** for it in this system. That is architecture.
Since 2026-08-27 this also rests on a citation rather than an assumption: Greek law disapplies the
prior-price rule for perishable food (άρθρο 9ι παρ. 2 ν. 2251/1994, inserted by ν. 5111/2024
άρθρο 3), which is *why* the fresh path may move on its own. See `REGULATORY.md`.

**Personalised pricing is out of scope structurally, not by policy.** · 2026-08-24
The decision key has no customer dimension. Claim 7 is a test over the key's exact field set, on
every type on the decision path, not a promise in a document.

**One cloud, and it is Databricks on AWS.** · 2026-08-24
The account, the OIDC pattern, SSM for cross-layer publishing and the Terraform muscle memory
already exist across three projects. A second cloud would divide attention without proving anything
more about Databricks.

**The repository is public, and it went public to buy a gate.** · 2026-08-27
It was created private, because publication has its own checklist and that checklist has not run.
Within the hour it became public, for one reason: **on a free account, a private repository can have
neither GitHub Actions nor a protected branch.** Both routes to branch protection — classic
protection and rulesets — return *"Upgrade to GitHub Pro or make this repository public"*, and
Actions jobs never started at all. Oversight level 1 is the level everything else leans on, and a
gate that cannot run is not a gate.

*What was weighed:* paying for Pro would have kept it private, and was the recommendation. It was
declined in favour of going public now. *What that costs:* the publication checklist is now owed
rather than pending — see the restatement under **Deliberately deferred**. *What was checked
first:* `gitleaks` over all 20 commits of history, plus a read of every file ever committed. No
leaks, no credentials, no `notes/` — which is gitignored and was verified absent from the remote
before and after.

**Public but unannounced is a real state, and this is it.** No README, no banner, no article, no
post. Anyone who finds it sees an honest work in progress whose own `PLAN.md` says which claims have
not closed.

**Not claimed, and written down so it stays not claimed** · 2026-08-24
Observational uplift where randomisation is impossible. Causal identification outside the
randomised design. That the feedback loop is solved. Optimality of any decision. A Genie
replacement — backward-looking question answering is a commodity.

---

## Technology

**uv, Python 3.12, pytest, ruff, mypy strict.** · 2026-08-27
Chosen at the first commit of real code. `uv.lock` is an input, not an artefact: CI runs
`uv sync --locked` and sets `UV_FROZEN=1`, so a lockfile that has drifted from `pyproject.toml`
is a red build rather than a silent upgrade.

**PyYAML and jsonschema live in the contract layer only.** · 2026-08-27
`src/holdout/core/` imports no cloud SDK, no engine, **and neither of those two**. The contracts
layer reads YAML and hands core frozen dataclasses over plain data. A test blocks `yaml` and
`jsonschema` from `sys.modules` and imports every core module anyway. This is the only reason the
claims are provable on a laptop with no account.

**Money is integer euro cents, with three roundings.** · 2026-08-27
Never a binary float. `as_price` is half-even, the metric contract's declared mode; `as_lower_bound`
rounds **up** and `as_upper_bound` rounds **down**, because a bound that rounds toward what it
forbids is not a bound. The cost is that a price legal by half a cent can be refused. The benefit is
that claim 5 can compare as integers with no tolerance.
The AST check that bans floats in `core/` is a **lint**; `Money` is the gate. Five of ten planted
float forms slipped the AST check and every one of them was refused at runtime by `Money`.

**The guardrail set is a type, not a check.** · 2026-08-27
`ProposedPrice → CertifiedPrice | Refusal`, and the function that dispatches to a shelf accepts only
a `CertifiedPrice`. The type is not a dataclass: its slots are filled by a function held in a
closure and stamped with a witness that has no importable name. Construction, subclassing,
`dataclasses.replace`, pickling, copying and duck-typing all refuse.
**Declared limit:** a forger who rewrites the price, the bounds, the checks and the source in one
coordinated edit is not caught, because a certificate never held independent evidence of its own
provenance. A test asserts that limit rather than hiding it. The type makes the mistake impossible
and leaves the forgery visible.

**Two engines, split at a declared boundary.** · 2026-08-24
Spark Declarative Pipelines for bronze → silver, because streaming, out-of-order arrival,
expectations and quarantine are native there. dbt for silver → gold, because there are many
analytical models with tests, docs and per-model ownership, and the metric contract compiles into
exactly dbt's shape. Chosen per problem, not per preference.

**Databricks AI/BI dashboards, not Grafana.** · 2026-08-24
AI/BI is native and GA, queries Unity Catalog directly so governance continues inside the dashboard,
and has a Terraform resource. Grafana would need hosting, a JDBC source, its own auth and its own
bill **for no additional proof**. It wins where you need sub-minute refresh with alerting; the
decision monitor does not.

**GitHub Actions pinned to commit SHAs, not tags.** · 2026-08-27
A tag is mutable. `actions/checkout@v7.0.1` and `actions/checkout@3d3c42e…` are the same code today
and need not be tomorrow. The tag stays in a trailing comment so the version is still readable.

**`corpus/world/` is generated and never committed. `corpus/real/` is committed and never
generated.** · 2026-08-27
Two corpora, two opposite rules, one reason each. A world is a pure function of
`(world, seed, scale)`, so storing one would be storing something a command reproduces exactly —
and at the scenario scale it is a few GB. The ONS price quotes cannot be reproduced by any command:
a person wrote them down in a shop. So one is regenerated and the other is digest-checked, and the
rule that applies is decided by whether the data can be recomputed rather than by where it sits.

**Randomness is keyed hashing seeding a per-unit `random.Random`, never a module-level seed.**
· 2026-08-27
`blake2b(seed, key)` decides *which* stream, the Mersenne Twister produces it. Both halves are
stable across CPython versions and platforms; `hash()` is salted per process and would make every
run a different world. The property that costs the most and buys the most is that **no key contains
the arm**: generate a world under an assignment and again under all-control, and every store whose
policy did not change draws the identical numbers. T003's reference implementation of
truth-on-the-metric is that subtraction, and without common random numbers it would be measuring
simulation noise alongside the treatment.

**The world's geography is a plane, in metres.** · 2026-08-27
`contracts/design/inference.yaml` declares a neighbour radius and the only question the scenario
ever asks of geography is whether two stores are inside it. Integer metre offsets make that an exact
comparison against a squared radius — no square root, no float, no datum. A real `store_master`
carries latitude and longitude; this one does not, and says so rather than generating coordinates
that would look like a GIS extract and answer the one question less exactly.

**The sealed truth is an envelope, not a lock.** · 2026-08-27
`corpus/world/seal.py` obscures the injected behaviour under a blake2b keystream whose nonce is
stored in the same file, so anyone who reads the module can decode it. What the seal guarantees is
narrower and is the half that matters: the truth is **never in the harness's process** — `events()`
filters the exposure records out of the stream and no object a caller holds carries them — and the
legitimate opening requires a readout that already exists on disk, whose digest goes into an
append-only ledger inside the seal.
**Declared limit:** a coordinated rewrite — decode, change, re-seal with a fresh commitment, forge
the ledger — is not caught, because a seal never held independent evidence of its own provenance.
`tests/corpus/test_world_seal.py` performs that forgery and asserts that it *succeeds*, rather than
describing the limit in prose beside the code. Same shape as the certificate type's limit, same
sentence: it makes the mistake impossible and leaves the forgery visible.

**`gitleaks-action` is free here because this is a personal account.** · 2026-08-27
A licence key is required for repositories owned by an **organisation**. This one is not. Recorded
because it is a silent dependency: moving the repository under an org breaks CI until a free key is
obtained from gitleaks.io and added as a secret.

---

## Method

**Claims first.** · 2026-08-24
Seven claims, each provable local — in CI or on a laptop, with no workspace and no credentials. If a
change does not serve one of them, it is questioned. This is why the Makefile has one target per
claim: a claim that is a Makefile target is a structural gate, and a claim that is a paragraph is
advice.

**No green target for a claim that is not proved.** · 2026-08-27
`claim-1` … `claim-7`, `gate-proof` and `preview-audit` are deliberately absent from the Makefile
and are documented as absent inside it. A green target that proves nothing is worse than a missing
one: it is a gate disarmed before it was ever armed. Each arrives with the eval that earns it.
CI **discovers** claim targets by grepping the Makefile rather than listing them, so the day one
lands it is gated without anyone remembering to edit the workflow — and a claim target that exists
but is never run is impossible by construction.

> **Restated 2026-08-27, later the same day.** `claim-1` and `gate-proof` now exist, because the
> eval that earns them exists. The rule is unchanged and the other six targets are still absent:
> the discovery grep in `ci` picked both up with no edit to the workflow, which is the property the
> original decision was written for.

**One branch per closed piece of work, squash-merged.** · 2026-08-24
Not ceremony for a solo repository: `main`'s log is part of the portfolio and will be read; the gate
is structural only when the suite runs *before* anything lands; and the fresh-context reviewer needs
an object to review, which a pull-request diff is.

**The corpus contains the thing each world exists to detect, by construction rather than by
chance.** · 2026-08-27
Store placement clusters deterministically — every second store a town gets opens within 700 m of
one already there — because a probabilistic cluster left the smoke scale with **zero** neighbour
pairs, so W2 was structurally unable to interfere and every test about it would have passed
vacuously. Measured before the rule was written, not assumed after. The same argument produced the
deliberate twin basket (two receipts, same till, same second, identical contents) at a declared
rate: a pathology that only appears at some scales is a pathology no test can rely on.

**W2's direction is derived from the two schedules, and the test drives it both ways.**
· 2026-08-27
The first version hard-coded *control loses trade to treatment*, from the assumption that a
candidate markdown policy cuts deeper. `policy.candidate` cuts **shallower** — measured against its
own counterfactual, an aggressive ladder destroyed between 5% and 25% of category margin through
reference-price habituation — so the assumption had been false since the day the candidate was
chosen. A world whose interference points the wrong way still breaks SUTVA and would still have
been detected by everything downstream, which is exactly why nothing would have caught it.
`tests/corpus/test_world_worlds.py` therefore hands the neighbour a shallower ladder and then a
deeper one, built inside the test, and requires the watched store to move both ways. A hard-coded
direction passes one half and fails the other, whichever way it was wired. It is `CLAUDE.md`'s
rule about a guard tested by its author, applied to a generator.

**Blocking a module for a test goes through `sys.meta_path`, not `builtins.__import__`.**
· 2026-08-27
Both boundary tests — `core/` must import with `yaml` and `jsonschema` absent, `corpus/` must
import with `holdout` absent — made the module unavailable by patching `builtins.__import__`. That
backs the `import` **statement** and nothing else: `importlib.import_module("yaml")` goes through
`sys.meta_path` and never touches it. So a module could reach straight past the check whose whole
job was to stop it, and the check stayed green.

Found by planting the call while adding the corpus half, and it could not have been found any other
way — read side by side, the two tests look right. The rule and the fix are the ones this repository
has arrived at twice already: **one implementation, two callers** (`tests/boundary/conftest.py`,
mirroring `ops/isolation.py`), and **the instrument is driven by the shape that defeated its
predecessor** (`tests/boundary/test_blocking.py` plants `importlib.import_module`, `__import__` and
the statement, and requires each to raise, plus two negative cases so a blocker that blocked
everything would not pass).

*Both* tests were rewired, not only the new one. `CLAUDE.md`: *"when a guard is fixed, the gate
behind it is re-read. They usually share the assumption."* Here they shared the technique, and the
older of the two had carried the hole since it was written.

**Four levels of oversight, because many small sessions drift.** · 2026-08-24
CI on every PR · a fresh-context reviewer on every PR · an integration session at every phase
boundary · the author, always, and never an agent.

### The three findings — the first real evidence the oversight model works

Recorded because until now they existed only in one conversation, and because each was invisible to
the level below it.

1. **A `legal_instrument` asserted a basis its own article never states.** The 2021 margin-cap window
   declared a `per_unit` basis citing ν. 4818/2021 άρθρο 58; «ανά μονάδα» appears nowhere in that
   instrument — the per-unit framing enters with ν. 4903/2022 άρθρο 50. The window had imported its
   successor's arithmetic and stamped a citation on it. *Caught by level 2. Level 1 cannot catch this
   class at all: `make contracts` checks the **shape** of provenance — instrument, article, URL,
   date — and never its **content**.* Four more of the same class were found in the same pass,
   including a Directive cited as evidence about what Greece had done.
2. **Two lines of public API defeated claim 1's central sentence.** An empty `PriceBounds()`
   satisfied both halves of the actuator's re-check — `contains` true, `is_empty` false — turning a
   certified €2.00 into €0.01 on a shelf while the certificate still named three guardrails that no
   longer bound anything. *Caught by level 2 attacking the gate rather than reading it. A green
   suite cannot find this: nothing in the suite was trying to forge anything.*
3. **The declared safe state produced a price the guardrail set refused.** At the deepest ladder rung
   — three hours from expiry — every base price ending in five cents quoted one cent below the
   max-depth bound, because the ladder rounded its quote as a price and the guardrail rounded the
   same number as a bound. Roughly one base price in five, at the rung that matters most. *Caught by
   level 2. Invisible to a green suite for one reason: the branch delivered two modules and never
   composed them.*

**The rule that came out of finding 3:** no core module is tested only alone. A composition test is
now the default, not an extra.

**A fourth, worth recording for a different reason.** A background agent researching Greek statute
reported material it had not verified, then retracted it. Nothing it disowned had ever reached a
contract as a `legal_instrument` — every item was already named in `REGULATORY.md`'s "Not verified"
section. The `legal_instrument` / `scenario_assumption` split did exactly the job it was built for.
*The lesson is not "agents make things up". It is that the split has to exist before you need it.*

**A contract compiles; it is never interpreted by hand-written code in two places.** · 2026-08-27
13 generated artefacts, byte-compared on every run. A hand-edited consumer is a build failure,
because a hand-edited consumer is a second definition and a second definition is what the contract
layer exists to prevent.

**Where a legal fact cannot be verified, it is declared as a scenario assumption.** · 2026-08-27
Never a plausible percentage with a plausible citation. `value` without `source` is a build failure;
`source` requires either `kind: legal_instrument` with an instrument, article, URL and verification
date, or `kind: scenario_assumption`. 45 values: 30 legal, 19 assumed at last count.

**An eval is not a test, and `evals/` is shaped so the difference stays visible.** · 2026-08-27
The suite asks whether a module does what its author meant. An eval asks whether a **claim**
is true, on inputs its author did not choose, and publishes numbers rather than a tick. Six
rules, set by claim 1's eval and inherited by claims 2, 3 and 4: a check has a stable id, so
`gate-proof` can name it; a check states a falsifiable question rather than a label; numbers
are published pass or fail; **coverage is itself a check**, so an unreached refusal code is
red rather than a footnote; a boundary that has to be known is computed **twice**, in a
different unit and a different structure; and "what this does not prove" is printed on every
run rather than kept in a README where it can quietly stop being true.

**`gate-proof` has three rules, and each one closes a way of passing without proving.** ·
2026-08-27
*Green first* — a mutation whose target was already red proves nothing, and that is
`NOT-ARMED`, a failure rather than a skip. *A non-zero exit is not proof* — the eval's JSON is
parsed and the **named** check must be the one that fell; a crash is `CRASHED` and `CRASHED`
fails, because otherwise the easiest way to pass would be a mutation that makes the eval
unimportable. *A mutation whose target moved is `STALE`, never passed* — the anchor must occur
exactly once and the named check must still exist, which is what stops the set decaying into
mutations that no longer touch anything.
Thirteen mutations, all thirteen refused by the gate named in advance. Nothing is mutated in
the working tree: each run copies the source into a temporary directory.

**Where claim 1's independence actually lives — and the one separation that carries it.** ·
2026-08-27
Three are hygiene: the corpus is published by people who have never seen this repository; a
test forbids `corpus/` from importing `holdout`; a mutation is written as a behaviour change
in domain terms rather than as "make G2 fail". The one that does the work is that **the
planter cannot tune the inputs** — `corpus/real/MANIFEST.yaml` carries a digest for every
committed file and CI recomputes it, so the only way to make a mutation catchable is to make
the gate actually catch it.
*What it does not prove, stated because it is the honest half:* that the numbers in
`contracts/guardrails/` are the right numbers. No eval can, and `make contracts` cannot
either — it checks the shape of provenance, never its content. The eval shows the machinery
honours whatever envelope it is handed.

**A retailer's unit cost is not public, so it is derived and the derivation is argued.** ·
2026-08-27
No open source carries a supermarket's cost — it is what a buyer negotiates. Rather than a
plausible number, the corpus takes Eurostat's gross margin on goods for resale over turnover
for NACE 47.11 in Greece and derives `unit_cost = price × (1 − 0.1681)`. A **median** of the
thirteen published years, not a mean, because the 2018 observation is a break in the series
at 47.8% against roughly 17% either side; the row stays in the file, and a test asserts it is
still there, because deleting it would have made the number honest by accident.
The cost is derived from the item's **median price across the corpus**, not from each row's
own price. That is the choice that makes the corpus work at all: a cost from the row's own
price makes the margin identical on every row, and the floor answers the same question thirty
thousand times. From the item, the real dispersion between 811 outlets drives it, and about a
fifth of rows land below their item's cost.

**Two survivals are kept in the record, because a mutation set that never surprises its
author was written after looking at the answers.** · 2026-08-27
`absolute-floor-is-not-applied` survived twice. First on a target that was simply wrong — the
markdown path has other lower bounds, so removing the absolute floor never empties
`bounds.lower`. Then on the right target, for a better reason: with a 0% margin floor the
derived cost was always the higher bound, so the absolute floor never decided anything.
**A gate can only be shown to bite where it is the gate that refuses**, and the fix was to the
eval's sweep, not to the assertion. `an-erased-answer-is-as-good-as-a-checked-one` survived
because the certificate has defence in depth: blanking `_bounds` is caught by the *checks*
recomputation. Good news about the design and useless as proof, so the eval gained a tamper
that erases the bounds and the checks together — internally consistent, and refused by exactly
one line.

**A mutation is owned by exactly one claim, and `gate-proof` audits rather than executes.** ·
2026-08-27
`make claim-N` runs its eval and then plants the mutations that claim owns; `make gate-proof`
runs nothing and checks the arrangement. `engine.run` requires a claim number, so there is no
"run everything" mode to fall back into.

*What prompted it:* `claim-1` and `gate-proof` both ran claim 1's thirteen mutations and the CI
job took **13m06s** to prove the same thing twice — untenable once claims 2 to 4 land. Three
alternatives were weighed and rejected: raising the timeout again (defers, does not fix);
special-casing the discovery step so it knows which targets subsume which (*a gate with special
cases is a gate with somewhere to hide*); and reducing `claim-N` to its eval alone (then no
single command proves a claim end to end).

*What it bought beyond the minutes:* **the orphan check, which nothing had before.** A mutation
dropped into `mutations/claim-9/` when no `claim-9` target exists was planted, never run, and
never missed. And the reverse — a `claim-N` target with no mutation planted against it — is now
a build failure, which is CLAUDE.md's checklist question (*if it is a gate, is there a
`gate-proof` mutation that proves it bites?*) made structural rather than remembered.

Ownership is read out of the **Makefile**, because the Makefile is what CI runs. A registry or
a naming convention would be a second source of truth about which command proves what.

**The ledger is the one gate that cannot have a gate-proof mutation, because it is gate-proof.**
· 2026-08-27
So it is proved by unit tests that break each of its checks on a deliberately broken
arrangement — `tests/evals/test_ledger.py`. A gate that has only ever been seen green has not
been tested, and that applies to the accountant as much as to anything it counts.

### The fourth finding — two files, each correct, never multiplied together · 2026-08-28

The first three findings were each a defect inside one artefact, found by reading it. **This one
is not in any file.** `corpus/world/chain.py` opened every second store within 990 m of one the
chain already had, on purpose, so that W2 would always have interference to detect.
`holdout.core.design.feasibility` excluded the later-sorted member of every pair inside the
declared 1 km radius, on purpose, so that no store would measure its neighbour. Each is right,
each is documented, each has tests. **Their product is that half the estate disappears**, and
nobody had computed it — because computing it requires running the corpus through the engine,
which is exactly what T003 was the first task to do.

What it measured, at the scale claim 2 was to be proved at:

```
100 stores -> 109 neighbour pairs -> 55 exclusions -> roster 45 -> control arm 9
0 of 200 lotteries pass the readout's balance check
4 of 5 world seeds refused at moment 1 with UNDERPOWERED_FOR_DURATION
```

And it did not scale out: 400 stores left a roster of 130, 1,200 left **212**. The towns were a
fixed size, so every store added made the estate denser rather than larger and the share the
engine excludes rose without limit.

*Caught by neither level 1 nor level 2.* CI was green — every test passed, because every test was
about one of the two files. A fresh-context reviewer reading either diff would have found nothing
either, for the same reason. It was caught by **running the two together for the first time**,
which is what an eval is for and why claim 2's eval was worth building before its estimator.

**The rule that follows, and it is the sibling of the two CLAUDE.md already carries.** A guard
tested by its author fails in the shape its author imagined. A sentence written by its author has
no gate behind it at all. And: **two components each correct on its own have no test between
them, and the number that would have shown it is a product nobody was computing.** So — *where
two deliberate decisions meet on a quantity, that quantity gets a name, a command and a figure.*
Here it is the **surviving roster**, `make roster`, and a table in `corpus/world/README.md`.
`CLAUDE.md`'s scale paragraph is restated to say that the surviving roster, not the store count,
is the number a claim rests on.

**A second, sharper thing fell out of the same measurement.** At 25 controls on that roster,
`store_format=hypermarket` sat at a **constant 0.1734** across two hundred draws: a categorical
covariate's balance is decided by how the strata are allocated to cells, not by the lottery. So
there are rosters on which no admissible assignment can ever pass the readout's balance check —
and `assess` returned `Feasible` for them without a word, to be refused identically at every
readout forever. That is the same shape as the starved reference set T002B closed, one moment
earlier, and it is T00D: `balance.attainable` computes what any draw could reach and
`NO_ADMISSIBLE_ASSIGNMENT` is returned when the answer is already outside the tolerance.

**What the two fixes bought, measured.** The balance pass rate on the corpus's own roster went
from **0 of 200** to **145–192 of 200** over three world seeds in the five ordinary worlds, and
**121–172 of 200** in W2, whose estate is deliberately the most clustered. The residue is
sampling spread on the numeric covariates, which `strata.py` already owned as a limit — and it
is a rate claim 2 publishes rather than a wall it stops at.

**What was not done, and deliberately.** No threshold moved. `balance_tolerance_smd` stayed at
0.10 and `holdout_share_pct` at 20%, which `inference.yaml` says move only by a versioned
contract change with a restatement and never as an exception granted to one experiment. The
refusal T00D added names the roster as the remedy and does not point at the dial.

### The AI layer — what earns a hook

**A hook must not duplicate a check CI already makes green-or-red.** · 2026-08-27
CLAUDE.md's three mechanisms have three jobs: a rule holds passively, a skill is a procedure
invoked by name, a hook is a guarantee the harness enforces whether it is wanted or not. The
temptation with the third is to reach for it whenever something matters, and that is how a
`.claude/` directory bloats into a second, unversioned test suite that nobody runs and nobody
trusts.

The bar taken here: **a hook exists only where the gate that already covers the rule cannot run
at the moment the mistake is made.** Both hooks in `.claude/hooks/` clear it, and neither is
the gate:

- `corpus_isolation.py` — the gate is `tests/boundary/test_corpus_imports_nothing.py`, which
  runs on every push and which `main` cannot take a violation past. What it cannot do is run
  *now*, so a session can build for an hour on top of a barrier that is already gone.
- `main_guard.py` — the gate is the `main` ruleset, with no bypass actors, which refuses the
  *push* by name. What it cannot do is stop the commit being made. The cost of that is not a
  broken `main`; it is the twenty minutes of `git reset` before the pull request can be opened,
  and the temptation at minute nineteen to just push.

*What was rejected:* a hook that runs `make check` before a commit (CI runs it, and a slow hook
on every commit is a hook that gets switched off), a hook that blocks `git push` to `main` (the
ruleset already refuses it by name), and a hook that enforces the branch-naming convention
(judgment, not a thing that must never happen — that is a rule, and `CLAUDE.md` already carries
it).

**One rule, one implementation, two callers.** · 2026-08-27
The corpus barrier is now `ops/isolation.py`, called by the boundary test *and* by the hook. The
alternative — a hook with its own copy of the AST walk — was rejected on the ordinary grounds
that two copies of one rule drift, and the copy that drifts is the one nobody reads. The hook
would have been the one nobody reads.

The hook polices the whole of `corpus/`, not `corpus/world/` alone, because that is what the
test has always policed and a hook that policed *less* than its own gate would wave through
exactly the violation it was added to catch early.

**`ops/` is a new top-level package, deliberately not inside `src/holdout/`.** · 2026-08-27
It holds the code that enforces the rules the product code is measured by — the corpus barrier
and the deferral registry. Nothing in it serves one of the seven claims, and putting it in
`src/holdout/` would have made it one more thing the claims have to be proved independent of.
It is linted and type-checked on the same terms as `src/`, along with `.claude/hooks/`: a
guarantee held to a lower standard than the code it guards is not one for long.

**Both hooks fail open on input they cannot read.** · 2026-08-27
A hook that dies on a malformed event takes the session's editing with it, and a hook that has
to be switched off to get work done is a hook that gets switched off — permanently, and for
every rule it carried. The test and CI remain the gate; failing open costs a turn, failing
closed costs the session. The one exception is `main_guard` on a command line it cannot
tokenise, where it falls back to a coarser match and refuses: an unbalanced quote is the single
case where guessing in the safe direction costs only a retry.

**A check is armed, or it says why it cannot be — and *unarmed* is a third state.** · 2026-08-31
`ledger.every-claim-target-owns-a-gate` asked the question at **target** level, which one mutation
satisfies for a claim with twelve checks. `docs/reviews/phase-1.md` §1 measured what that left:
**21 of 57 checks owned no mutation and 8 of those named no reason**, including three of the four
numbers claim 2 publishes.

So the same question per check. `Check` gains `unarmed_because`, and `make gate-proof` sorts every
declared check into three states and prints the counts:

```
37 armed by a mutation · 23 declared un-armable · 7 unarmed
```

**The third state is the design decision.** Unarmed is reported and **not** refused, for the reason
`docs/FINDINGS.md` reports `adrift` rather than refusing it: a gate nobody has armed yet is a real
state, and refusing it would buy a sentence where a mutation belongs — which is the opposite of what
the rule is for. What *is* refused is a check both armed and declared un-armable, because one of the
two is then untrue and nobody would notice which.

`unarmed_because` is for **cannot**, never *have not*, and the honest reasons turn out to be three:
the break would edit the **detector** (`ops/`, `corpus/`, the eval itself), the check asserts a
property of the **inputs** no change to `src/holdout/` can move, or the check is **absent from the
configuration a mutation runs at** and computing it there would make it a different check wearing
the same id. Twenty-three carry one of those. The ten belonging to `gate-proof` itself are among
them, armed instead by `tests/evals/test_ledger.py` — which is the arrangement that already
existed and had never been written down as part of the shape.

**Discovered by parsing rather than by importing.** The ledger reads `Check(...)` off the syntax
tree of everything under `evals/`, because importing an eval means being able to run it and
`evals/uplift/` costs half an hour. It is claim 7's `reference.py` pattern, with the same declared
limit: a `Check` built dynamically would be invisible, and today all sixty-seven are literals.

**And one of the eight was armed rather than excused.** `G7.closed-vocabulary-only` asks two
questions; `17-a-refusal-arrives-without-its-detail` blanks a refusal's detail, which moves no
bound, certifies no price and changes no code — **`G7` is the only check in the eval that falls**,
which is the standard *a gate can only be shown to bite where it is the gate that refuses*. Claim 1
is 17/17 mutations biting.

**Arming it found that G7's other question cannot fail.** *Is every reason's code one the vocabulary
declares* is checked as `reason.code.value not in declared`, and `reason.code` **is** a
`RefusalCode` — a dead branch, the type having already closed what the check re-asks. Filed in
`docs/FINDINGS.md` rather than patched here: rewriting a check while proving it bites means the
mutation was written against a shape nobody reviewed, and whether a check should re-assert what a
type guarantees is a judgment rather than a defect.

**What is still uncovered, printed on every run rather than left to be rediscovered.** Twelve
`at_decision` codes are reached by `G8` and all four `at_readout` by claims 2 and 3, but **seven of
the eight `at_design` codes are reached by no eval** — they exist only in
`tests/core/test_refusal_codes.py`, which is cases their own author wrote. `evals/design/` is claim
6 and phase 4, and claim 6's headline counts N proposed and M refused over exactly that vocabulary.

**Real inputs, derived cost — the corpus stops saying *real* on its own.** · 2026-08-31
The author's decision on the half that was never ours: a corpus presented as real, whose concrete
benchmark is a construct the regulation does not use, is not left as a declared limit in a footnote.
**Wherever the corpus is described as a whole, the wording names all three parts** — real prices,
real law, derived cost — and *real* does not stand alone.

Six sites carry it: `corpus/real/README.md` and its `__init__`, the `MANIFEST.yaml` header,
`evals/guardrail/checks.py`'s own docstring (the file that turns real inputs into derived cost),
`evals/guardrail/README.md`, and `docs/SCENARIO.md`.

*Why the wording rather than the data.* No public source carries a retailer's cost and none ever
will — it is what a buyer negotiates. So there is no version of this corpus that anybody can rebuild
from published sources in which the cost is observed. The choice was never *fix the cost* or *leave
it*; it was **say what it is every time, or say it once and let the rest of the file read as
though everything were sourced.** The second is what was there: `README.md` named three real things
and omitted the cost, and `MANIFEST.yaml`'s header said every price, category and margin came from
somebody else — true, and silent about the number the whole envelope turns on. A provenance record
that names only what it can source reads as though it sourced everything.

*What did not change:* `docs/SCENARIO.md` already said *"from which the corpus derives a unit cost.
A retailer's cost is not public"*, and `CLAUDE.md`'s two mentions say *price lists* and *claim 1's
prices* — none of the three ever claimed the cost was observed, so none was edited. The sweep is
over places that overclaimed, not over the word.

*And the finding closed through the mechanism.* `docs/FINDINGS.md`'s founding entry carries
`*Closed:* 2026-08-31` with the transition, and a `*Now:*` for each of its three sites — so the text
that closed it is held to the same exactly-once rule for as long as the entry exists. A revert turns
the register red on the entry that already knows about the defect. `1 open, 2 closed · closed and
still held 4 line(s)`.

**The corpus's benchmark is named rather than reshaped, because the shape was already there.**
· 2026-08-31
`corpus/legal-claims-restated` was scoped as *fix the prose, and give the eval's benchmark the shape
the law uses — keyed by product code rather than a scalar.* Measured before writing any of it, the
second half was **already true**:

* `ProposedPrice.benchmark_markup_on_cost` is a field on each proposal and `envelope.py` bounds
  every decision against its own, so the core already takes a benchmark per product code;
* `regulated_basket.yaml` carries `value: average_gross_margin_2025` — a name sourced to the
  instrument, never a level;
* the only thing that flattens it is the **corpus**, at four call sites in `evals/guardrail/build.py`
  passing one zero-argument function for all 232,373 decisions.

So there is no core change, no contract change and no restatement chain in this branch. **The scope
asked for a shape that exists**, and building it would have been a day spent reproducing what was
already there — which is the same defect the branch exists to fix, one layer out: an assertion about
the code made from something other than the code.

**And what remained had two disguises, either of which would have looked like the fix.** Computing a
per-code margin from the corpus's own derived cost returns `m` exactly for every code, because
`cost = price × (1 − m)` is that identity — per-code numbers that are the flat number in costume.
A per-item signature returning one constant everywhere is the same disguise reversed: per-code
*structure* around a single number. Both would read as fidelity and contain none.

**So the flatness is carried by a name.** `benchmark_markup_on_cost()` became
`sector_wide_benchmark()`, and a reader of the four call sites meets the word *sector* before
anything else — which is the inference the 2026-08-27 finding was made possible by, refused at the
place it was made. No argument that is ignored, no structure implying what is not there. If a real
per-item benchmark ever arrives it arrives as a real change, against a name that never lied.
`tests/evals/test_guardrail_instrument.py` holds both halves: the level is one for every item and
deliberately so, and no call site supplies it under a name without *sector* in it.

**Measured, against the baseline this branch actually diverges from.** The scope named `f0a9994`;
`main` was `b7ab2ae` by the time the work started, and a branch is compared with what it diverges
from rather than with what was `main` when somebody wrote the instruction. The two were verified
byte-identical for claim 1 first — `#28` touched nothing under `evals/guardrail/`, `corpus/real/` or
`core/` — so the choice changed no number, and the rule stands anyway because it was measured rather
than assumed.

```
232,373 decisions · 10 checks
baseline b7ab2ae   sha256 22a6daea80950e9c7458feb6dbf34bc6a52343f001147d5f9ebeb7a5ed47d469
after the branch   sha256 22a6daea80950e9c7458feb6dbf34bc6a52343f001147d5f9ebeb7a5ed47d469
```

Stated as a number rather than as *no change*: a refactor that provably moves nothing is a stronger
result than one nobody checked, and it is only stronger if the check is stated.

**An open finding gets a home, because it was the one thing that had none.** · 2026-08-31
`docs/FINDINGS.md`, and `make findings` behind it. Every mechanism this repository had was aimed at
a **claim**, a **gate** or a **deferral**, and an open review finding is none of the three. Two of
them fell out as a result.

**The legal half of oversight level 2's third blocking finding against claim 1**, recorded
2026-08-27, closed never, deferred never. Absent four days later. `make expiry` had nothing to read
because it was not a deferral; the phase-1 integration session had nothing to check against because
`CLAUDE.md` does not say findings are tracked. **And `docs/reviews/phase-1.md` §4** —
`pricing/selection.py` — dropped by that review's own closing table, the one that assigns every
other section to a branch. One day, in a nine-row table written for exactly that purpose, and found
by its author in his own document.

**A finding anchors to a line that already exists**, and the gate goes red when that line stops
saying what the finding says it says. It is `ledger.every-anchor-is-aimed-at-one-place` over a new
population, and the borrowing is earned rather than decorative: that check is what refused a
hand-applied mutation 16 during `ops/claims-are-required`.

*Refused:* a finding with no site — one whose consequence is recorded nowhere, which is exactly what
the legal one was; a site whose fragment does not occur **exactly once** in the file it names, since
zero means the line moved and nobody said which and two means the anchor proves nothing about which
line was meant; a finding with no disposition line at all; a `*Closed:*` with no transition after
the date.

*Reported and not refused:* **adrift** — a disposition of `none — <reason>`. A finding nobody has
scoped yet is a real state, and refusing it would teach people not to file, which is the state that
lost the first one.

**Closure restates a site rather than releasing it**, and the first draft did not. It let a closed
entry stop being checked, and the reviewing session found the hole before the file landed: *a
finding that stops being examined the moment somebody accounts for it is a claim about the past
that reads as a claim about the present.* A fix reverted in November would leave the register
saying `closed` forever — which is the legal finding's own story one layer along, since what hid
its third part was precisely that nothing re-examines a thing already accounted for. So every site
gets a `*Now:*` carrying the text that replaced the defect, held to the same exactly-once rule for
as long as the entry exists, or `gone — <reason>` where nothing replaced it. The price is naming
the replacement text, which is what the `[M]` rule already charges everywhere else.

**`concurred` is not `closed`, and that is the entry that matters.** Closure is a transition: the
anchored line changes, a branch lands and the gate goes red-to-green, or a named human says so.
Agreement between the reviewing session and the building session is a **fourth state**, carried as
open and counted separately.

It is there because it nearly happened. On 2026-08-31 the reviewing session removed §4 from the
author's list on the grounds that the two sessions concurred, and the building session refused —
*that is the precise mechanism by which the legal finding left the record: not a decision to drop
it, but two parties who held it agreeing it was handled and nobody holding them to that.* The pair
of sentences the two arrived at is in the registry and both halves are load-bearing: *it was my
finding, and that is exactly why I should not be the one deciding it needs no oversight* — and *it
was not my finding, and that is exactly why my agreement is worth less than it feels.*

If the two heaviest users of a register could retire an entry by agreeing, it would measure their
agreement rather than the repository.

**Both entries went in open, before either fix branch**, and that is `gate-proof`'s first rule
rather than a preference: *green first — a mutation whose target was already red proves nothing.* A
register entry filed with the answer already known is a mutation planted against something already
broken, and would prove nothing about whether the register would have caught it.

**The two findings fail differently, and that is what tested the design.** The legal one had two
sides that drifted apart, which the anchor check catches by construction. §4 **never had a second
side** — recorded once, never picked up — so a comparison between two sides would find nothing to
compare and report nothing. It is caught only by *adrift*, which had been specified for
completeness rather than for a case anybody had in hand. A mechanism meeting a case its author did
not have in mind, **before it shipped**, is the thing this project has spent a phase failing to
arrange, and here it arrived free.

*The standing limit, declared rather than closed.* An anchor proves a line exists and still reads as
expected. It cannot prove it is the **right** line. A true but irrelevant anchor is a green that
means nothing, and nothing here can catch that — the same limit as a mutation planted against the
detector, which this repository answered by putting the detector out of reach rather than by
testing the choice. And the registry is itself a representation: it reports on the entries somebody
wrote down, never on the findings somebody had. Its first paragraph says so, without an example,
because the only example available argued the other way.

*What it cost while being built, and both were the gates working.* `docs/FINDINGS.md` needed
**Περίοδος Αναφοράς** — the term άρθρο 4 παρ. 5 actually defines, as against what the finding says
it defines — and `make language` refused the file until the term was declared with its reason. That
made the allowed vocabulary nineteen, and `make figures` then refused `ops/language.py` for still
saying eighteen. Correcting the sentence rewrapped it, and the rewrap took it out of reach of its
own pattern — **the reviewing session's wrapped-header failure, reproduced inside an hour by the
mechanism written to catch it.** Every prose pattern in `ops/figures.py` now spans whitespace with
`\s+`, and the docstring says why.

**`make expiry` learns what closure is, and prints how much of itself it can check.** · 2026-08-31
Three things, and the first is the one `docs/reviews/phase-1.md` §2a found.

**A closed deferral is not an open one, and this target could not tell.** It read headers and
nothing else, so an entry whose finding had already returned was counted among the live ones
forever — and its `*Expires:*` date went on ticking. `next expiry 2026-09-30` pointed at *CI's gate
job runs on a temporary 25-minute timeout*, **closed on 2026-08-28 by T003**, which was the only
dated entry in the registry and the one the registry credits with arming this target at all. CI was
going to go red for a finding that had already returned. A `*Closed:* YYYY-MM-DD` marker is now read
like `*Unlock condition:*` and `*Expires:*`, a closed entry cannot expire, and open and closed are
counted apart. `next expiry` moved to **2026-11-30**, which is a real one.

It is a marker and not a scan over the closing argument, which is a block quote. A regex over prose
would be a second definition of *closed* that agrees with itself until somebody words it
differently.

**The standing limit becomes a number.** *An unlock condition is prose and no checker can evaluate
it* was written honestly in `ops/expiry.py`'s docstring from the day it was written. What it never
was is **countable**, so nobody could see how much of the registry it covered. The run now prints
`checked for TRUTH n of m` beside `checked for PRESENCE only`: today **4 of 33 open entries, 12%**.
That is `make figures`' question — *a gate reports on what it examined; it becomes a lie when it
reports what it examined as if it were what exists* — turned on this target, which is the honest
place to point it first.

**Published, not gated.** A condition-only deferral is legitimate by the registry's own rule, so
refusing one would refuse the thing the section exists for. What is refused is not saying how many
there are. And the figure is deliberately **not** written into the docstring: a live number in prose
is the assertion this repository has watched go stale ten times.

**And the thirteenth form of *a guard tested by its author*, which is the sharpest yet.** On
2026-08-30 `CLAUDE.md` gained *an unlock condition that names a session rather than an event is not
a condition; it is a date without a calendar.* **The registry was not swept when the rule was
written.** Nine open entries reached for "the phase-1 integration session" — five as the unlock
condition itself, four as a fallback clause — and the session in question had already happened
without answering any of them, which is the evidence that they were places to put a question down
rather than conditions.

The twelve before it were rules that went stale, or numbers written against a projection. **This one
is a rule that was correct, published, and simply not applied to what already existed at the moment
it was written.** Nothing decayed. The new rule and the old registry were never run against each
other — which is the fourth finding's shape, *two components each correct on its own with no test
between them*, pointed at a rule and a document instead of at two modules.

**Six were given the branch that closes them, and nothing was invented.** `floor.yaml`'s rule id →
`contracts/floor-rule-id`; the scenario-scale measurement → `evals/world-cache-measured`, because
whether a periodic run earns its CI minutes is the same question about the same minutes; W6's
`IMBALANCED_PRE_PERIOD` threshold and the `C7`/`C11`/`C12` mutations → `evals/unarmed-checks`; the
ESL penetration figure → `docs/layout-and-restatements`, the one change that opens `CLAUDE.md`
anyway; the ladder ceiling → `docs/doctrine-rule-1-ceiling`. Each condition now names the **state**
that change produces, with the branch as the pointer rather than as the condition.

**Three had a real condition already and only a fallback clause to lose**, so the clause was removed
rather than reassigned: claim 3's strata (the cache across evals), the regulated basket (the decision
and its argument), and W2's luck (the variant existing). Inventing a condition for those would have
been worse than the sentence it replaced.

*What is not enforced, and why it is a sweep rather than a gate:* telling a session from an event
means reading English. `tests/ops/test_expiry.py` asserts the **state the sweep left** — no open
entry's unlock condition names the session — which will catch a new one added in the old shape, and
will not catch one phrased differently. Closed entries keep their original wording and every
restatement quotes what it replaced, per doctrine rule 4, so the phrase survives in the file on
purpose and a blind search for it would be wrong.

**The split is published rather than a single number**, because the structure is the thing:

```
33 open deferrals
   4  carry *Expires:*                       -> checkable for truth
  29  carry an unlock condition only         -> checkable for presence
   5  name the integration session as the unlock condition
   4  name it as a fallback clause           -> still session-named; it just fails second
   8  name a task id first
```

*And these counts are this branch's own measurement, taken with `ops.expiry` itself — which
matters, because a different set reached the branch with the instruction and it was wrong.* The
figures that arrived were 25 entries, 5 dated, 20 condition-only. Measured here: **35 headers, 2
closed, 33 open, 4 dated, 29 condition-only.** Neither was adopted on authority and the method is
stated so anybody can re-run it.

**The disagreement was then explained, and it is `make figures`' own rule broken one message after
it was insisted on.** The other count came from a regex requiring `· deferred YYYY-MM-DD` on a
single line. Ten of the thirty-five headers **wrap** between the title, the middle dot and the date
— which is the exact case `ops/expiry.py`'s `_ENTRY` carries a written comment about, because a
checker that silently skipped them would under-report the registry rather than fail. So that
instrument saw **25 of 35 and reported as though it were all of them**: a gate reporting what it
examined as if it were what exists, at a coverage of 71%, in the same exchange that established the
rule.

It is the third instance of that rule in three days and the second from the reviewing side — the
first being `grep -P`, absent on macOS, at a coverage of zero. Both were found by re-execution and
neither by reading, which is the standing lesson: **an instrument's coverage is not visible in its
output, and reading its output more carefully does not make it visible.** Only running a second one
does.

**A gate reports on what it examined, and `make figures` is the difference.** · 2026-08-30
Two events in this repository's record are the same defect at two coverages, and nobody had called
them the same thing. **At zero:** the language rule was checked with `grep -P`, which BSD grep on
macOS does not implement; it exited 1, stderr was discarded, and a count of zero was read off a
command that never ran the check. **At seven of eight:** `ci.yml`'s `discover` matched claim
targets with `claim-[1-7]`, so a `claim-8` would have been invisible to it — and `claims-complete`,
the required check, aggregates only what `discover` emits. A whole claim could have landed with its
gate never running and the merge would have been green.

> **A gate reports on what it examined. It becomes a lie when it reports what it examined as if it
> were what exists.**

**Every gate declares how its population is enumerated, and `ops/figures.py` enumerates it a second
time.** It is `evals/README.md`'s rule 5 — *a boundary that has to be known is computed twice* —
pointed at coverage rather than at arithmetic.

**The declaration is a rule and never a frozen count**, and that is the first place this deviates
from how it was asked for. A count is an assertion needing its own measurement, which is the defect
`CLAUDE.md` catalogues ten times; an enumeration rule goes stale only when the thing it enumerates
changes shape. So a gate does not declare `[D] 182`; it declares *`*.py` under the six directories
`PYTHON_DIRS` names*, and the number is recomputed on every run.

**And the comparison is one-sided: red when `examined < exists`, never when `examined > exists`.**
That is the second deviation, and it was measured rather than argued. On 2026-08-30, ruff 0.16.4
reported 190 files over those six directories against an independent count of 182 `*.py`. The eight
are Markdown — ruff formats Python inside fenced blocks, and has since a version nobody here chose.
A gate that froze 190 would have gone red on that upgrade for a reason that is not a defect; one
that froze 182 would go red when ruff stops. Only under-coverage is a lie about what exists. It is
`Money`'s rule one layer up: *a bound that rounds toward what it forbids is not a bound.*

**An instrument that cannot answer raises rather than returning zero.** A tool that will not run, a
pattern that no longer matches its own output, a `PYTHON_DIRS` line that has moved — each is a red
run with its own message. That is the entire content of the `grep -P` failure, made structural:
silence and success looked identical, and now they do not.

**Six gates come out. The seventh does not, and the reason is circularity.** `lint`, `typecheck`,
`language`, `expiry`, `gate-proof` and `discover` each report what they examined against an
independent enumeration. **`test` cannot**: a suite's examined is what actually ran, which is known
only after it runs, while `make figures` runs before it inside the same `make check`. Asking pytest
to collect twice would measure collection against collection, which is a number agreeing with
itself. It is recorded as uncovered rather than covered badly.

**The prose half is deliberately small, and its size is printed rather than implied.** Two figures
are registered — the sizes of `ops/language.py`'s two closed lists — and `PLAN.md` and `TASKS.md`
are excluded on purpose: doctrine rule 4 keeps superseded figures there forever with the
restatement beside them, so re-running those would go red on history that is correct as written.
Only present-tense text can be checked this way, and *which* text is present-tense is a judgment,
not a rule, so the registry is written by hand. `docs/SCENARIO.md` does the same job with `[M]`
tags and the command beside each figure; this is the half a command can re-run.

*It found one thing on its first run:* a number in `ops/figures.py`'s own docstring, stale by two
before the module was committed. The fix was not to update it but to **date it** — it is a
measurement of a moment supporting an argument about direction, not an assertion about today, so it
carries `Measured 2026-08-30, on ruff 0.16.4` and is not in the registry. That distinction is what
makes the prose half tractable at all.

**Proved by two attacks, and the second is the one that matters.** `tests/ops/test_language.py`
**removes** the instrument — the detector edited into something that cannot match.
`tests/ops/test_figures.py` **narrows** it: a path outside the walked list, and `claim-[1-7]`
against a Makefile carrying a `claim-8`, which is the exact state `main` was in until this branch.
Narrowing is the shape no reviewer notices, because the gate still runs, still prints, and still
says what it always said.

**`discover` also gains a floor.** `claim-[0-9]+` cannot miss a target the way `claim-[1-7]` could,
but a target *deleted* still shrinks the list in silence, and a shrinking gate is the same lie one
step along. `FLOOR=6` is what exists today; finding more is ordinary growth and finding fewer is a
claim whose gate stopped running. `make figures` checks that floor against the Makefile, so it
cannot go stale downward without something going red.

**The language rule becomes `make language`, and it is the first gate that has to prove it can
see.** · 2026-08-30
`CLAUDE.md`'s first line — *all repository content in English. Conversation with the author in
Greek* — was enforced nowhere, and it had already been broken. `docs/reviews/phase-1.md` landed on
`main` carrying **12,803 Greek characters**, in a public repository, written by a session that
took "the conversation" and "the work product" to be the same thing. The report is translated on
this branch; the gate is what stops it recurring.

**Not a blanket ban, because three kinds of Greek are load-bearing and translating any of them
would be the defect rather than the fix.** A **verbatim article** of a Greek instrument, quoted so
that `REGULATORY.md`'s own rule holds — *a `legal_instrument` carries either a verbatim `quote` or
a `note` accounting for it* — where a translated statute is a paraphrase of law and doctrine rule
3 refuses exactly that. **Published data somebody else wrote**: the 63 regulated-basket categories
and the ONS item descriptions, digest-checked in `MANIFEST.yaml`, so an edit is already a red
build and the corpus is evidence precisely because this repository did not write it. And
**mathematical symbols** — alpha, beta, tau.

So the exceptions are **two closed lists rather than one loose one**, in `ops/language.py`, each
entry carrying its reason. Five excepted **paths** for verbatim law and published data; eighteen
allowed **tokens** admitted anywhere, which is what keeps the path list to five. Measured before
the lists were written: outside those five files the whole repository uses eighteen distinct Greek
tokens — a vocabulary rather than a habit, which is what made a closed list the right shape. A
path allowlist wide enough to cover the citations in `src/`, `tests/`, `evals/` and four documents
would have admitted Greek nearly everywhere and would not have caught the review.

*The declared limit:* an excepted path is a path. A Greek paragraph hidden inside
`docs/REGULATORY.md` passes, and `tests/ops/test_language.py` asserts that rather than describing
it. The pull-request diff is what catches it — the same answer `make expiry` gives about a deferral
deleted outright.

**And the reason this gate is shaped differently from every other one: it reports the absence of
something.** The rule was violated first and measured second, and the measurement was taken with
`grep -P`, which BSD grep on macOS does not implement. `grep` exited 1, `2>/dev/null` swallowed the
reason, and *no matches* and *no such option* are the same two characters on a terminal. **A count
of zero was reported from a command that never ran the check.**

That is the twelfth instance of *a guard tested by its author*, and its form is new — not a
sentence, not a number in configuration, but **a tool that was not there**:

> **The silence of a missing instrument is indistinguishable from a pass.**

So `ops.language` refuses to report green until it has answered for itself: the detector must fire
on a sentinel built from code points (so the module's own bytes carry no Greek and it needs no
exception for itself); the walk must have read more files than a declared floor; and every declared
exception must still be **in use**, because an unused one is a pre-approval for whoever writes that
token next — claim 7's `O12` argument, one directory along. Each of the three is attacked in
`tests/ops/test_language.py` by taking the instrument away, and each attack requires a red run.

*What it found while being built, which is the part worth keeping.* The first draft of that test
file wrote its Greek fixtures as literals under a comment saying they were code points. `make
language` refused it — **the gate biting the test written to prove it bites**, before either had
been committed. The generalisation of this to every other gate is `ops/every-number-carries-its-kind`;
this entry is one gate meeting the rule early rather than a claim that the rule exists yet.

**Doctrine rule 6 becomes `make expiry`.** · 2026-08-27
*"Exceptions expire. On expiry the finding returns and CI goes red again"* was enforced nowhere.
It now is: `make expiry` reads the **Deliberately deferred** section of this file and refuses an
entry that has passed its `*Expires:*` date, or that carries neither a date nor an
`*Unlock condition:*` — the section's own opening sentence, made checkable.

It is the only target in the repository that can go red on a day nobody touched it, which is
the point rather than a side effect: a deferral outlives its reason by the calendar, not by an
edit. It runs inside `make check` and is named as its own step in `ci`, so that when it does go
red it is legible as itself.

**What oversight level 2 cost this branch, and it was the whole of it.** · 2026-08-27
A fresh-context reviewer read the diff against `CLAUDE.md` and found ten things, two of them
fatal to the branch's own closing condition, on a suite that was green at 372 tests. Recorded
because the pattern is now three for three: **every finding was prose asserting more than the
code supported, and the code was wrong in exactly the place the prose was most confident.**

1. **`main_guard` let the ordinary two-line commit through.** `_SEPARATORS` declared `"\n"` a
   separator and `shlex` with `whitespace_split` never produces a newline token, so the entry
   was dead: every line after the first joined the first command, and only its first `git` was
   ever inspected. `git add -A` on one line and `git commit -m x` on the next was **allowed on
   `main`**. The one-line `&&` form was caught — so the guard bit the shape a reviewer would
   type into a test and missed the shape a session actually writes. Lines are split before
   tokenising now, and `then`/`do` are skipped so a compound statement reaches the test.
2. **The corpus barrier missed `src.holdout`, and that import runs.** `src/` is an implicit
   namespace package and the repository root is on `sys.path`, so
   `from src.holdout.core.guardrails import Envelope` imports and works — and it is the
   spelling that matches the path on disk, which makes it the one somebody reaches for. The
   barrier looked for the installed name only *and carried a comment explaining why the other
   spelling would not be used*. `TASKS.md` had named the violation in those exact words. The
   gate behind the hook had the same hole and this branch had rewritten that gate without
   closing it.

The other eight: the partial-drift defence was blind to any drift that also dropped the bold; a
wrapped `*Expires:*` date read as no date and reported an expired deferral green; an impossible
date crashed instead of going red legibly; the text fallback was wrong in both directions and
had no test at all, because every one of the twelve sources in its parametrisation parses and
takes the AST path; the `NotebookEdit` wiring could never fire and the README advertised it;
`settings.json` was read by nothing, so a cleared exec bit or a misspelt path would leave the
suite green and both guarantees dead; the coarse fallback grepped prose inside a heredoc; and
`Deferral.is_expired` was dead code duplicated inline — in the same branch whose sibling
module's whole argument is *one rule, one implementation*.

*What was not found:* nothing out of scope, and no further plain defects. The seams that were
composed — the hook against the real `ops.isolation`, `main_guard` against real git state —
held. The one that was not composed was `settings.json`, and that is finding six.

*The rule this repeats:* the branch's tests were written by the same person as the code, and
they tested the shapes that person had in mind. Both fatal findings were shapes nobody had in
mind, and both were named in the prose as impossible.

*The standing limit, stated rather than papered over:* an unlock **condition** is prose — "the
phase-1 integration session", "phase 2's gold layer" — and no checker can evaluate it. A
condition-only deferral is therefore checked for existence and never for truth, and it cannot
expire. What the target can do about that it does: it prints the age in days of every deferral,
so one that has quietly outlived its reason is a number on a terminal rather than something
somebody has to remember. Deciding that an aged deferral is too old is a judgment, and it
belongs to the integration session rather than to a regex.

*What it refuses beyond the two obvious cases:* a **partially** drifted section. If an entry
header changes shape and eleven entries stop matching while two still do, the naive checker
reports two deferrals and stays green — the registry silently shrinks without anyone deleting
anything. Two independent counts catch it, because either alone has a blind spot: every line
that looks like a header must have been read as one, *and* the number of `· deferred YYYY-MM-DD`
markers in the section must equal the number of entries read. The first catches a header whose
`· deferred` changed shape; the second catches a header that dropped its bold — `### Title`, a
list item, a block quote — which the first cannot see at all.

*What it cannot refuse, and does not claim to:* an entry **deleted outright**. There is nothing
left to compare against — no marker, no header, no gap. Deletion is caught by the pull-request
diff, which is where a deletion should be argued anyway.

**The inference settings are a contract, not constants in a module.** · 2026-08-27
α, the target power, the balance tolerance, the exposure threshold, the holdout share, the
permutation-draw count, the attempt budget, the neighbour radius and three standard-normal
quantiles live in `contracts/design/inference.yaml`, each a `{value, source}` pair. The
alternative was a block of `Decimal` constants in `holdout/core/experiment/`, and that is precisely
the "value without a source" the contract layer exists to refuse — doctrine rule 3 does not care
what extension the file has. The argument is `balance_covariates.yaml`'s, one level up: **anything
that can be chosen after the fact will be chosen after the fact**, and an α chosen per experiment
is the most valuable dial in the building.

Every source is a `scenario_assumption`. None of these is law, this repository's guardrail
contracts carry real instruments and these do not, and the split is what keeps the difference
legible. `design` therefore joins `PROVENANCE_FAMILIES`, whose description had said "numbers that
come from outside the repository" — too narrow, since a threshold invented *inside* needs an
argument beside it just as much.

The file **compiles to nothing.** No consumer is generated from it, so `compile_all` is untouched;
it is still validated, claimed, provenance-walked and printed on the green summary, because a
contract nothing mentions is one nobody would notice going missing.

**Three quantiles are written out, and all three are recomputed by a different mechanism.** ·
2026-08-27
`holdout.core` may not import `statistics`, so `1.959964`, `1.644854` and `0.841621` are literals
in a contract. A literal is the shape of number this repository refuses to take on trust, and a
`note` saying "this is inv_cdf(0.975)" is prose. `tests/contracts/test_inference.py` recomputes all
three with `statistics.NormalDist().inv_cdf` — legal outside `core/` — and asserts agreement at the
six declared places. That is `evals/`'s rule 5, *a boundary that has to be known is computed
twice*, applied to a constant; and the test asserts the three numbers against a normal table too,
so a later edit that "fixed" the recomputation to read the YAML would have to walk past that line.

**The one-sided quantile is declared, not derived.** The SPEC this branch was built from sized
one-sided designs on a quantile it never declared. Computing `1.644854` in Python would have been a
load-bearing number with no argument beside it, in a module written to refuse exactly that, so
`z_one_sided_alpha` joined the contract with its own source.

**Permutation under the restriction, with a covariate-adjusted statistic.** · 2026-08-27
Validity comes from the lottery; precision comes from the adjustment. The re-randomisation screen
restricts the space of admissible assignments, so the ordinary confidence interval — which assumes
simple randomisation — comes out falsely wide. The reference set at readout is therefore **exactly
the set of candidates the same screen accepts**, which is what makes the inference match the
restriction instead of assuming it away.

> **Restated 2026-08-28.** The restriction is no longer a screen: assignment is **stratified**, so
> the reference set is exactly the set of candidates the same **strata** admit — one control per
> stratum, drawn from the same committed seed. Everything the paragraph above claims about the
> inference is unchanged and for the same reason, because stratification restricts the space of
> admissible assignments exactly as the screen did. What changed is that the restriction became
> constructive rather than rejective, which is what made the reference set affordable to fill; see
> the deferral below.

Four consequences, each a decision in its own right:

- **The weak (Neyman) null, so the statistic is studentized.** A raw difference of means is exact
  only under the sharp null of no effect for any unit. W5 is heavy tails and unequal arm variance,
  which is where that assumption breaks and where an unstudentized permutation test stops holding
  its level.
- **The interval inverts the same test**, by bisection over a grid of constant shifts, reusing the
  same draws at every step. Coverage is then correct by construction rather than by asymptotics,
  the endpoints are integers in the metric's own canonical unit, and there is nothing to round.
- **B = 1000, declared in the contract.** `(1 + hits) / (1 + B)` is exact at any B, so B buys
  resolution and not validity — and the readout prints B beside the p-value so nobody has to guess
  which it was.
- **ITT is the only number.** Below `exposure_min_pct` the readout refuses with
  `EXPOSURE_BELOW_THRESHOLD`; above it, the realised exposure rate is printed beside the estimate.
  There is no exposure-adjusted estimator and no field for one: the readout vocabulary is closed,
  and an exposure-adjusted number carries an exclusion restriction — an assumption, in a readout
  built to avoid them.

**The lottery is keyed hashing, not a PRNG.** · 2026-08-27
`blake2b(unit_id, key=blake2b(seed || draw_index))` per unit, sorted by `(rank, unit_id)`. Claim 3's
sentence is *exactly reproducible*, and hashing is strictly better at it than a seeded generator:
reproducible from the committed seed alone with no interpreter or platform dependency, independent
of the order the roster arrived in, and computable **per unit** — so a readout can re-derive one
unit's arm without replaying a sequence. `random` and `secrets` are banned in `core/` anyway; this
would have been the right mechanism regardless.

**The seal is the certificate pattern *and* a digest, because they close different holes.** ·
2026-08-27
`SealedAssignment` copies `CertifiedPrice`: constructor raises, subclassing raises, no `__setattr__`,
no `__reduce__`, fields read through a guarded accessor, filler in a closure beside a witness with
no importable name. That protects the in-process path. It does nothing for the path that will
actually be used to alter an assignment — writing it to `gold.experiment_assignment` and reading it
back in another process a month later — which is what the digest over
`(experiment_id, seed, form_digest, roster, arms)` is for. The contamination check recomputes it
from the seed and the roster and compares.

*The limit, in the docstring rather than glossed:* a forger who rewrites the arms, the seed and the
digest in one coordinated edit is not caught, because a seal never held independent evidence of its
own provenance. A test asserts that limit. What is caught is every edit that is **not** coordinated,
which is every edit that happens by accident and most that do not.

**The seed is supplied, never generated.** `core/` reads no clock, no environment and no random
source, so it cannot mint a seed; the SPEC's moment 1 said "generate the committed seed", which
`core/` structurally cannot do. The seed is an argument, committed alongside the design in
`experiments/`, and that is also the stronger position: a seed the engine invented would be a seed
nobody committed to in advance.

**The readout's balance check re-measures; it is not the screen re-run on the screen's own numbers.**
· 2026-08-27
A screened assignment re-checked against its own screening matrix passes by construction — a gate
that cannot bite, in the same family as the four findings under "a guard tested by its author".
`close` therefore takes the covariates **as they stood at close**, over the units that actually
reported. Restated pre-period revenue, an attrited store and a moved roster each turn the check red
in `tests/core/test_balance.py`, and each of the three is a thing that happens.

> **Restated 2026-08-28, and the argument got stronger rather than weaker.** There is no screen any
> more, so the balance tolerance is judged at exactly one moment — this check. The sentence above
> now reads: an assignment re-checked against the matrix its **strata** were built from would pass
> almost by construction, which is the same gate that cannot bite. The three planted movements are
> unchanged and still turn it red. What is new is that this check is where the tolerance actually
> decides something, so `IMBALANCED_PRE_PERIOD` is now a refusal a healthy experiment can genuinely
> receive rather than an outcome the design screen had already made unlikely.

**The eval's rounding is re-decided, not borrowed — and a tolerance was an exemption for one bug.**
· 2026-08-28
`evals/guardrail/reference.py` calls itself a second implementation of the envelope's arithmetic. It
was one for the arithmetic and not for the **rounding**: the eval's own floor ended in
`Money.as_lower_bound`, the core's primitive, under a docstring saying the direction had been
"arrived at independently". That is the fourth instance of `CLAUDE.md`'s *a guard tested by its
author is tested in the shape the guard already handles*, and the first three were each declared
impossible by prose sitting beside the code — as this one was.

What it cost, planted against `main` rather than argued about: `G2` **fails**, with 199 violations
in 28,681 certified prices, because `G2` compares against `reference.py`'s exact `Decimal` bound
and that never went through `Money`'s rounding at all. `G3` and `G4` stay green. The check that
shared the primitive was `G6`, and `G6` stayed green while its published ceiling count moved
7,366 → 7,365 in silence. This entry first said all three stayed green; oversight level 2 ran the
mutation and found the claim an order of magnitude too large. It is restated rather than deleted,
because a wrong number in the evidence layer is exactly the thing this repository is about.

`evals/guardrail/rounding.py` re-decides the direction from the contract's own statement of it and
carries it out by **integer division of a `Fraction`**. `Fraction` was not chosen because it is
nicer: it is the one representation in the standard library that cannot share a bug with `Decimal`,
because it has no precision, no context and no quantisation step to get wrong. Agreement between the
two is then worth something, and `make gate-proof` plants `Money.as_lower_bound` rounding half-to-
even to show a named check refuses it.

The same reading killed `G3`'s one-cent tolerance. A refusal was "supported" if the price sat inside
the exact bound by less than a cent — slack for the core's conservative rounding, the docstring said.
But every price in this eval is a whole number of cents, so under a correctly rounded core that
branch is **unreachable**: the only way into it is a bound sitting a cent *above* where the rule
puts it. The tolerance was an exemption for exactly one bug, and that bug is the shape this
repository's own history says its bugs appear in. Both `G3` and `G4` now compare against a bound
this eval rounded itself, with nothing tolerated anywhere.

**A check that goes through a price is blind where no price lands in the gap.** · 2026-08-28
`G2` asks whether a certified price escaped a bound and `G3` whether a refused one had something to
refuse. A bound a single cent out of place opens a gap exactly one cent wide, so both see it only
where a corpus price happens to sit in that gap. Measured, on an absolute floor moved a cent loose:

    G2   FAIL ·       3 violations in    28,485 certified prices
    G10  FAIL · 232,373 disagreements in 824,790 bounds compared

Three real prices out of twenty-eight thousand is a gate that holds until the corpus is reshuffled.
`G10` therefore does not go through a price at all: every `Bound` the envelope attributed to a rule
is compared with the edge this eval computed for the same rule, **as integer cents with no
tolerance**, on all 824,790 of them.

*Three mutations, and the third is the one that settles it.* The rounding primitive changing
direction and the margin floor built a cent too strict are both caught elsewhere as well — the
second trips `G3`, which is the evidence that its tolerance is really gone. Oversight level 2 asked
the fair question: does `gate-proof` show `G10` catches anything nothing else does? It did not, so a
third was planted. **A bound at exactly the right amount carrying another rule's id** moves no
arithmetic whatsoever — no price wrongly certified, no refusal unsupported, no ladder rung changed —
and `G10` is the only check in the eval that goes red. Claim 1's evidence is *which* guardrail
fired, and a certificate's recorded checks are derived from those ids, so a misattributed bound
asserts a check that never ran. It is also the only mutation that exercises `G10`'s second
direction: a rule the eval bounds and the envelope did not.

**The denominator of a percentage is carried in the type.** · 2026-08-28
A gross margin over the **selling price** and a mark-up over the **cost** are the same constraint and
different numbers: 16.81% of the first is 20.21% of the second. `ProposedPrice.benchmark_margin_pct`
named neither, so the shape of the mistake was a caller taking the figure an instrument publishes —
in the instrument's denominator — and handing it to a field that multiplies the cost by it. It fails
safe, and it is still a wrong number arrived at silently.

A comment naming the denominator would have been read by whoever already knew. So
`holdout.core.guardrails.benchmark` carries it in the type: `MarginOnPrice` is what a statistic or an
instrument publishes, `MarkupOnCost` is what the envelope needs, and `as_markup_on_cost()` is the
only route between them — a named call in a diff somebody reads. The field is
`benchmark_markup_on_cost` and it refuses a bare `Decimal` **at runtime**, not only where mypy runs,
because a bare number is exactly the shape the mistake arrives in. The half of the ambiguity that
lives in `regulated_basket.yaml` is a contract change with a restatement chain and stays deferred.

---

**Three of the six worlds' declared correct behaviours were prose the code did not support.** · 2026-08-28

Three files said the same untrue thing. `CLAUDE.md`'s six-worlds table, `corpus/world/README.md` and
the `correct_behaviour` field of `W2` in `corpus/world/worlds.py` all read some version of *"detect
and refuse, never estimate"*, which reads as a detector at readout — and which is sealed into every
world's `truth.sealed.json`, so it is a promise the package makes about the system rather than a
comment.

There is no such detector, and the design never wanted one. `holdout.core.experiment.contamination`
asks two questions — does the recomputed digest describe the arms it carries, and did each unit
receive its own arm's policy — and neither can see a neighbour's trade crossing the road. The
defence against interference is at **moment 1**: `_neighbour_exclusions` drops the later-sorted
member of every pair inside `neighbour_radius_m` before the lottery is drawn, and the closed
vocabulary's only interference code, `UNIT_GUARANTEES_INTERFERENCE`, is filed under `at_design`. The
vocabulary was right and the prose was wrong.

So W2's correct behaviour is restated: **exclude the interfering units at design, then estimate on
what is left** — and `evals/uplift/` publishes the *pair*, the estimate with the neighbour pairs
declared beside the bias that arrives when they are withheld, because a mitigation nobody ever
measures the absence of is a mitigation nobody can price. The prior wording stays in all three
files, per doctrine rule 4.

**Then the whole table was read, because one bad row is a row and two is a method.** All six were
checked against the function that would make them true, and two more did not stand.

**W3** read *"exposure-adjust or refuse — never silently dilute"* in `CLAUDE.md`. There is nothing to
adjust with, and the repository already said so in the module that would have done it:
`exposure.py`'s docstring reads *"There is no CACE, no instrumental-variable estimate and no
exposure-adjusted alternative in this repository, and the absence is deliberate rather than
pending"* — the closed vocabulary has no code for it, a `Readout` has no field for it, and it would
carry an exclusion restriction this readout is built to avoid. **A row of the six-worlds table
contradicted a module in the same repository, and both had been green since they were written.**
Restated to *"report ITT with the realised exposure rate printed, or refuse below the declared
threshold — never silently dilute"*. `corpus/world/`'s two copies were not wrong, only half a
sentence — they said what happens below the threshold and never what happens above it — and they are
aligned to the same wording.

**W4** read *"report the declared window's average, not the first week extrapolated"*, which reads as
arithmetic the estimator performs. It does not. `close` takes `outcomes` as given and **cannot
verify that what it was handed spans the declared period**; what is guaranteed is `may_read`, which
refuses to compute anything before the declared end, and `STOPPING_RULE_PERMITS_PEEKING` at design.
Restated to name that: *"no result before the declared end, then report what the declared window
aggregated"*. The aggregation is the caller's obligation and `evals/uplift/`'s `U8` is where it is
checked rather than assumed — a gap now written down instead of a guarantee now assumed.

**W1, W5 and W6 stand**, against `Readout.is_significant`, `Statistic.detects` on the realised
variance, and `close` returning a `Readout` when all four checks passed. W5 is the best-supported
row in the table: both halves of *"the power check fails, or the interval is honestly wide"* have a
named function behind them.

**The class of defect, which is the part worth keeping.** `CLAUDE.md` already carries *"a guard
tested by its author is tested in the shape the guard already handles"*. This is that defect one
layer up: **prose that claims a check nobody wrote.** It cannot be caught by reading, because every
document agreed with every other document — all three sites were written from the same sentence. It
was caught by reading `contamination.py` and asking which of its two questions would fire, which is
the only way it can be caught. The rule that follows: **a sentence naming what the system does when
something goes wrong is written against the function that would do it — named — and not against the
table it came from.** Where no such function exists, that is the finding, and the sentence says so
instead.

The rule lives in `CLAUDE.md`'s **Before any change** checklist, beside *"who wrote the case it is
tested on?"*, and not only here — a rule only the decision record carries is a rule a session never
reads. `CLAUDE.md` also carries it as the sibling of *"a guard tested by its author"*, because that
is what it is: a guard tested by its author fails in the shape its author imagined, and a sentence
written by its author has **no gate behind it at all**.

It applies hardest to text that ships. `corpus/world/worlds.py`'s `correct_behaviour` is sealed into
every `truth.sealed.json`, so it is not a comment — it is a promise the package makes about the
system, carried in the artefact the grader opens after the readout is written.

---

## Deliberately deferred

Each entry says what would unlock it. An item with no unlock condition is not deferred, it is
forgotten.

**The contamination check cannot see a store erased from the assignment table** · deferred
2026-08-29
`contamination.check` asks two questions — does the digest still describe the arms, and does the
committed seed still draw them — and both walk `seal.roster`, which is derived **from the arms it is
checking**. So a control store deleted from the table, with the digest recomputed to match, leaves
nothing to compare against: the check reports the assignment intact and `sealed()` agrees. Measured
by claim 3's eval over 24 configurations: **24 of 72 erasure routes are invisible to it**, and the
figure is published on every run as `48/72 = 66.67% of them by the contamination check`.

*What refuses that erasure today:* `readout.close`, one function later — *an outcome from outside
the experiment is not a small addition to the mean; it is a unit whose price nobody randomised*. It
holds only because the erased store still reports an outcome. Erase it from the assignment table,
the digest and the outcomes together and nothing notices; that is the coordinated forgery limit the
seal already declares, one door along, and it is why the assignment table is written before the
period opens and then read-only rather than defended by arithmetic alone.

*Why it is not fixed here:* the fix is a **contract and signature change**, not an eval change. The
check would have to be handed the roster the design committed to — from the locked form, or from a
`roster` on the seal that is not derived from the arms — and `feasibility.assess`, `readout.close`
and the two consumers of `Contamination` all move with it. T004's scope is the eval that measures
the door, and widening a core signature inside a claim task is exactly the scope creep the task
schema exists to refuse.
*Unlock condition:* T008, the first task that opens `holdout.core.experiment`'s signatures for an
unrelated reason — or the phase-1 integration session, which is allowed to propose the restatement.
Until then the gap is a published figure rather than a sentence, and `A8` asks whether an erasure is
refused **for a reason that names it** rather than whether a number came out, so a readout that
declined `POWER_NOT_REACHED` on an emptied assignment does not count as a catch.

> **Closed the same day, and the deferral was wrong rather than premature. Restated
> 2026-08-29 after oversight level 2.** The measurement above stands — 24 of 72 routes were
> invisible to the check, and `readout.close` was what refused them. The paragraph that does
> not stand is *"the fix is a **contract and signature change**, not an eval change"*, and the
> unlock condition built on it.
>
> **The witness was already inside the function.** `check` computes `drawn = redraw(seal)` and
> then walks `seal.roster`, one line apart. `redraw` returns an arm for every unit the
> committed **strata** hold, so its key set *is* the roster the lottery was drawn over —
> obtained from the strata, which `digest_for` commits as their own section, rather than from
> the arms table being checked. `frozenset(drawn) - frozenset(seal.roster)` names the erased
> store. No argument was added, no signature moved, no contract value was involved:
> `Contamination` gained a `dropped` field and `is_clean` gained a clause.
>
> **And the strata are a sound witness, not merely an available one.** The obvious counter —
> delete the unit from the strata as well, so the key sets agree again — changes which unit
> holds the smallest rank in that stratum, so `reassigned` fires instead.
> `tests/evals/test_assignment_instrument.py` drives both, and `A8` now asserts the
> contamination check **and** the readout's stray-outcome guard, per route, against a phrase
> each route declares in advance. `gate-proof` gained
> `09-the-contamination-check-trusts-the-roster-it-is-handed`, which reverts the line and must
> make `A8` go red, so the closure cannot be removed in silence.
>
> **What this does not close**, and the boundary is where it was: a seal whose arms, seed,
> strata **and** digest are all rewritten together still agrees with itself, because a seal
> never held independent evidence of its own provenance. That is the declared limit in
> `tests/core/test_assignment_forgery.py` and it is a different, wider thing than the gap
> above — which is exactly why the gap was closable and that one is not.
>
> The prior wording stays because doctrine rule 4 says a correction never erases what was
> previously stated, and because **the delta is the finding**: a deferral is an assertion about
> what the system does, wearing a cost estimate instead of a verb, and this one was written
> against an imagined fix rather than against the function that would make it true. The rule
> `CLAUDE.md` boxes — *written against the function that would make it true, named, and against
> the measurement of what comes out when it runs* — had never been pointed at a deferral before.
> `make expiry` could not have caught it: it checks that an unlock condition is present, never
> that the condition is the right one.
>
> *Closed:* 2026-08-29 — by T004, in the same branch that measured the gap. `contamination.check`
> gained a `dropped` field and `is_clean` a clause; `gate-proof` gained
> `09-the-contamination-check-trusts-the-roster-it-is-handed`, so the closure cannot be removed
> in silence.

**Claim 3's strata are matched on three of the contract's five balance covariates** · deferred
2026-08-29
`contracts/design/balance_covariates.yaml` declares five. `corpus/world/chain.py` supplies three of
them directly — the store format, the size index and the pricing zone — and the other two,
`category_revenue_8w` and the pre-period waste rate, exist only after a POS aggregation over eight
months of generated events. That is claim 2's path and it costs minutes per world; claim 3 runs 36
configurations in seventeen seconds because a chain is placement arithmetic rather than a
simulation.
*Why it is defensible rather than merely cheap:* the lottery is a function of the strata, not of
what the covariates mean, and `evals/uplift/` already draws over all five, two hundred times, on
this same lottery. What it leaves open is a defect that only appears with five columns — a matching
path reached by a fifth covariate and by nothing else — which claim 3 would not see.
*Unlock condition:* `evals/uplift/`'s per-world aggregation being cached across evals — at which
point claim 3 reads the five-covariate matrix from that cache and the sweep grows on its own.
*Restated 2026-08-31:* the second half read *"failing that, a deliberate item for the phase-1
integration session, which is allowed to decide the three columns are enough"*. That named a
session, and it named one that has since happened without deciding anything — so the clause is
removed rather than reassigned. The condition above was always the real one; the fallback was a
place to put the question down.

**`floor.yaml`'s rule id `refuse_when_no_legal_price_sells`** · deferred 2026-08-27
The refusal code it corresponds to was renamed to `NO_PRICE_SATISFIES_EVERY_GUARDRAIL`, because the
condition is arithmetic — the legal range is empty, floor above ceiling — and says nothing about
whether the item would sell, which is a demand question the envelope never asks. The rule id and its
`statement` in `contracts/guardrails/floor.yaml` still carry the original overreach.

*Why it was not renamed with the code:* the rule sits inside an **effective window that is currently
in force**. Contract rule 1 says no contract version is ever deleted, and contract rule 4 says a
change affecting past values implies a restatement. Renaming an id inside a live window is therefore
a contract edit with a wider blast radius than a code rename — it touches the window, the
restatement chain and anything that has already recorded that id. The refusal code is consumed by
`core/` and by claim 1's counting; the rule id is consumed by the contract layer alone, so the
overreach is contained to prose in one file.

*Unlock condition:* the next time `floor.yaml` opens a **new** effective window — for this reason
or any other. The new window carries the corrected id and its restatement; the closed window keeps
the old one, which is exactly what "never deleted" is for. `contracts/floor-rule-id` is the branch
that opens it, and `docs/reviews/phase-1.md` §3d carries the correction that goes with it: the gate
that turns red on the rename is `O2`, because the id is a field name in `ops/personhood.py`'s
registry — not `G10`, which never bounds this rule at all.
> *Closed:* 2026-08-31 — by `contracts/floor-rule-id`, through the unlock condition rather than
> around it. `floor.yaml`'s opening window is closed at 2026-09-01 and a new one opens carrying
> `refuse_when_no_price_satisfies_every_guardrail` and a restated `statement`; the closed window
> keeps `refuse_when_no_legal_price_sells`, which is what contract rule 1 is for. No value moved —
> the rule is `true` in both windows — so no past decision is judged differently and no recorded
> figure changes.
>
> **What the deferral did not anticipate, and it is the whole cost of the change.** It said the
> blast radius touches "the window, the restatement chain and anything that has already recorded
> that id". It does, and one thing more: **the closed window has to stay readable.** Every decision
> dated before 2026-09-01 resolves against it, which on this corpus is all of them, so the resolver
> cannot simply look for the new spelling. `envelope.py` gains `RENAMED_RULES`, which reads each
> window in its own vocabulary — and refuses a window carrying **both** spellings, because two
> rules with one meaning leave nothing able to say which was in force. Emptying that mapping turns
> the suite red, so the mechanism is not decoration.
>
> **§3d's correction is confirmed by running it rather than by reading it.** Putting
> `ops/personhood.py`'s registry back the way it was and running `python -m evals.oversight` gives
> `FAIL O2.every-decision-path-type-carries-exactly-the-fields-written-down — 55/56 types agree`.
> `G10` never bounds this rule: `refuse_when_no_legal_price_sells` appears zero times in
> `evals/guardrail/reference.py`, which is what the task note asserted it did.

*Restated 2026-08-31:* this read *"failing that, a deliberate item for the phase-1 integration
session"*, which names a session rather than an event and is what `CLAUDE.md` now refuses.

**`corpus/world/` writes gzipped CSV, not Parquet** · deferred 2026-08-27
`CLAUDE.md` describes the scenario corpus as *"a few GB of Parquet"*, and on the estate it will be.
In phase 1 the generator's product is a **stream**, consumed in process by the A/A harness, and the
`write` subcommand exists so a world can be looked at rather than because anything reads the files.
Adding a Parquet engine to `corpus/` — which is stdlib-only apart from one `yaml.safe_load` — to
write files nothing in this phase reads would be a dependency bought for a screenshot.
*Unlock condition:* the S3 bulk load in T009, which is the first thing that needs files on disk in
the format the lakehouse reads. The writer gains a Parquet target there, beside the CSV one.

**The scenario scale is measured by hand, not by a gate** · deferred 2026-08-27
`make check` and CI run the smoke scale, where a whole world is generated in well under a second.
The scenario scale — 100 stores, 120 SKUs, 244 days — takes about two minutes per world and its
figures are produced by `python -m corpus.world count --scale scenario` and recorded in
`corpus/world/README.md` with the seed that produced them. So the number in that README is a
measurement somebody took, not a number CI keeps honest, and it can drift from the code the day a
demand constant moves.
*Unlock condition:* CI's world-cache budget being set from measurement — the change
`evals/world-cache-measured` makes. Whether a periodic scenario-scale run earns its minutes is the
same question about the same minutes, priced against the 35 measured `claim-2` runs rather than
against an estimate, so it is answered there or not at all. Until then the smoke scale is the gate
and the README's figures carry their command.
*Restated 2026-08-31:* this read *"the phase-1 integration session decides"*, which names a session
rather than an event.

**The world's prices are not certified prices** · deferred 2026-08-27
`corpus/world/` applies a markdown policy's declared depths and stops. It knows nothing about the
guardrail envelope — no floor, no ceiling, no regulated basket, no maximum daily delta — so it can
and does produce shelf prices that `holdout.core.guardrails` would refuse, and the deepest rungs of
`ladder_policy@v1` sell below the unit cost the cost ledger records. That is deliberate: a corpus
that consulted the envelope would be a corpus that had met the gates it exists to be independent
of, which is the whole of the barrier `ops/isolation.py` enforces.
It is recorded because it is a real gap and not only a boundary. The chain in the scenario runs
*this* system, so a world in which the envelope never bites is a world one step removed from the
one the claims describe — and it is the same gap the ladder-ceiling entry above already names from
the other side.
*Unlock condition:* the decision path being exercised end to end against a world, which is
`evals/` work rather than corpus work — the join belongs there. T003 is the first eval to run a
whole system over a world and is where the question becomes concrete.

**`evals/` and every `claim-N` target** · deferred 2026-08-27
Nothing in the repository proves a claim yet. Claim 1 in particular needs the eval that attacks the
gates from an **independent corpus of real price lists**, plus `gate-proof` mutations proving each
gate bites. The seam that eval needs is built and verified — envelopes constructed from literal
numbers, with `contracts/` never opened — but the eval itself is not written.
*Unlock condition:* `corpus/real/` and the eval directories, each with the mutation that proves its
gate. Until then claim 1 has **not** closed, and PLAN.md says so.

**`terraform validate` and `make preview-audit` in CI** · deferred 2026-08-27
CLAUDE.md lists both in the `ci` workflow. Neither has anything to act on: there is no `infra/` and
no declared inventory of preview surfaces.
*Unlock condition:* the first Terraform layer, and the first time a preview surface is considered.

**`docs/SCENARIO.md` and `docs/DAY-ONE.md`** · deferred 2026-08-27
Both are named in CLAUDE.md's "read this first" table and neither exists. `DAY-ONE.md` has nothing
to record until there is an estate; `SCENARIO.md` is a writing task, not a blocked one.
*Unlock condition:* `SCENARIO.md` before phase 2, since the pipelines assume it. `DAY-ONE.md` before
phase 3, and specifically before the network path from the workspace to RDS is attempted — CLAUDE.md
requires that verification to happen **before** phase 3, not inside it.

> **Half closed 2026-08-30 by T007.** `docs/SCENARIO.md` exists and the condition it carried is met
> ahead of phase 2. `DAY-ONE.md` is untouched and stays here on its original condition: it still has
> nothing to record until there is an estate, and writing it now would be a document describing
> manual work nobody has attempted.
>
> **What the writing of it cost, recorded because it is the reason the entry was worth keeping.**
> The file is written under a four-way rule — every number is measured, declared, cited or scenario,
> and anything that fits none of the four does not go in. Recording a figure as *measured* means
> re-running the command rather than copying it, and W5's four counts in `corpus/world/README.md`
> did not come back the same at either scale. They were taken before T003 moved that world's
> pathology from the basket line to the store-day, and nothing re-runs them — which is the entry
> two above this one, *the scenario scale is measured by hand, not by a gate*, costing something for
> the first time. The figures are restated in that README rather than overwritten.

**Greek citations point at gazette mirrors, not `et.gr` permalinks** · deferred 2026-08-27
No working direct-download URL at `et.gr` could be constructed; the citations resolve to
`sate.gr`, `elinyae.gr`, `dsanet.gr` and `kataggelies.mindev.gov.gr`. Also: `sate.gr` returns 403 to
a bare fetcher user-agent and serves normally to a browser.
*Unlock condition:* before the repository is made public. Each must be re-opened through
`search.et.gr` and the citation updated. This is on the publication checklist, which has not run.

> **Restated 2026-08-27, later the same day.** The unlock condition above was overtaken by the
> visibility decision recorded under Scope: the repository is now public and the checklist still
> has not run. The original wording stays because doctrine rule 4 says a correction never erases
> what was previously stated, and because it is the honest record of what was intended.
> **The revised condition:** before the repository is *announced* — README, banner, article, debut
> post — every Greek citation is re-opened through `search.et.gr` and updated. Until then the
> repository is public but unannounced, and `REGULATORY.md` already names each source it could not
> reach at an authenticated primary URL. Nothing asserted as law depends on a source that was
> never read.

**The generated SQL has never been executed** · deferred 2026-08-27
13 artefacts compile and are byte-compared, but the dbt models, SQL functions and readout queries
are Databricks/Spark dialect that no engine has parsed. Gold column names (`qty`, `price_paid`,
`unit_cost_as_of`, `store_id`, `iso_week`, `category`) are assumed.
*Unlock condition:* phase 2, when gold is built. If gold does not match, the contracts move — not
the other way round.

**Metric versions v1 and v2 are invented history** · deferred 2026-08-27
They exist so that as-of resolution, the supersession chain and the restatement gate are
non-vacuous rather than a single version agreeing with itself. No experiment ever ran under them.
Each file says so in its header and each declares `scenario_assumption` provenance.
*Unlock condition:* the first real metric change, at which point one of them can be retired from the
explanation but not from the repository.

**The 2021 and 2022 margin-cap windows are unreachable through `envelope_as_of`** · deferred
2026-08-27
`floor`, `max_delta` and `frozen_categories` all open 2025-01-01, so no envelope can be constructed
for an earlier date. `MARGIN_CAP_BASIS_UNEVALUABLE` and the `per_unit` basis are therefore live code
on the hand-built path and dead branches on the contract path. They correctly guard a **future**
instrument that again states no basis.
*Unlock condition:* backdating the other three guardrails, which nothing currently needs. Recorded so
that "the 2021 window refuses rather than borrowing a neighbour's arithmetic" is never claimed as
something the repository demonstrates end to end.

**The declared tolerance and holdout share leave the reference set too small to reach α** ·
deferred 2026-08-27
This is the finding that decides whether claim 2 can be computed at all, and it is recorded here
because it was created by the values this branch put into `contracts/design/inference.yaml`.

The re-randomisation screen admits a candidate only when **every** declared covariate is within
`balance_tolerance_smd` = 0.10. The standardised difference between arms has a spread of roughly
`sqrt(1/n_T + 1/n_C)`, which at the scenario's shape — 100 stores, a 20% holdout, so 80 against
20 — is 0.25. Each of the seven comparisons the five covariates produce therefore passes about
31% of the time, and all seven pass about **three times in ten thousand**. Measured on a
hundred-store roster, `tests/core/test_assignment.py` finds roughly one draw in a thousand.

The consequence is arithmetic rather than opinion. `max_assignment_attempts` is 10,000, so a
reference set drawn inside that budget holds single figures of accepted draws. The smallest
attainable p-value is `1 / (1 + B)` — and inside an inverted interval it is `2 / (1 + B)`,
because the mirror image of the realised assignment ties with it under an arbitrarily large
shift. At B in single figures both floors are **above** the declared α of 0.05, so no experiment
at the scenario's own shape could ever report a significant effect. **W6's false-refusal rate
would be 100% by construction**, and claim 2 would fail on the world where the correct answer is
"yes, there was an effect" — for a reason that has nothing to do with the estimator.

Nothing in the code is wrong and nothing here is papered over: `reference_set` returns what it
actually found, `permutation_p` divides by that, and the readout prints B. What is missing is a
budget, or a mechanism, that makes the two numbers compatible.

*Why it is not fixed on this branch:* fixing it means choosing between four things that are all
contract or design changes with their own arguments — a much larger attempt budget (a reference
set of 1,000 at 10⁻³ costs about 10⁶ screens, roughly twenty minutes per experiment, times 200
seeds times six worlds); a wider tolerance, which is a restatement; a larger holdout share, which
is a restatement; or **stratified randomisation instead of rejection sampling**, which is the
standard remedy and is a design change to `assignment.py` rather than a number. T001's scope is
the core and its composition test, and quietly picking one of the four inside it would be exactly
the kind of after-the-fact choice the whole contract layer exists to prevent.

*Unlock condition:* T003, which cannot start without meeting the number —
`test_the_screen_accepts_about_one_draw_in_a_thousand_at_the_scenario_s_shape` measures it in the
suite rather than leaving it in this paragraph, and asserts the order of magnitude so that an
improvement makes the *test* fail and this entry get re-read.

> **Restated 2026-08-28 by T002B, which is the improvement that test was waiting for.** The
> wording above stays because doctrine rule 4 says a correction never erases what was previously
> stated, and because it is the honest record of what the values on this branch cost. The
> remedy chosen is the fourth candidate: **stratified randomisation**. Strata are matched on a
> composite distance over the declared balance covariates, one control is drawn per stratum from
> the committed seed, and nothing is screened — so every candidate is admissible, the reference
> set fills to the contract's B = 1000 at the scenario's own shape, and the floor
> `2 / (1 + B) ≈ 0.002` sits two orders of magnitude **under** α = 0.05. The measurement moved
> with it: `tests/core/test_assignment.py` now asserts that the set fills and that the floor is
> under α, so the number is still in the suite rather than in this paragraph.
>
> **Why the other three were not chosen, recorded rather than passed over.** A far larger
> attempt budget costs roughly 400 hours of screening across 200 seeds and six worlds, which is
> not a budget but a different project. A tolerance wide enough to accept at a usable rate is
> about 0.41 standardised differences — past the point where the screen is balancing anything,
> so it would buy the p-value by abandoning the thing the p-value is about. A 50/50 holdout
> raises acceptance only to roughly one draw in 800, which is the same starvation at twice the
> cost in treated units. Each is a real option that was measured and refused; the fourth is a
> mechanism rather than a dial, which is why it is the one that works.
>
> **What moved in the contract, and it is a restatement rather than an edit.**
> `contracts/design/inference.yaml` is at v2. `balance_tolerance_smd` kept its value and lost
> one of its two moments: it was the screen at design *and* the check at readout, and it is now
> the check alone. `max_assignment_attempts` kept its value and changed what it budgets — the
> screen's rejections, now the reference-set scan. Both prior meanings are stated in the file's
> own header and in each entry's note, and `NO_ADMISSIBLE_ASSIGNMENT` carries the same
> restatement in `contracts/vocabularies/reason_codes.yaml`: it used to mean *the screen
> rejected everything*, and now means *no stratification gives every stratum both arms*.
>
> **The reference set did not change, and that is the load-bearing part.** Stratification is a
> restriction on the space of admissible assignments, exactly as the screen was, and a
> permutation *within strata* is a draw "under the same restriction" in precisely the sense
> `balance_covariates.yaml` already required. What changed is that the restriction is now
> constructive rather than rejective, so the same sentence about the inference is true and the
> arithmetic underneath it is affordable.
>
> **What stratification does not buy, stated because the honest half is the half that gets
> dropped.** It does not make every draw pass the readout's balance check. With 20 controls a
> covariate the others carry no information about keeps a sampling spread near the tolerance,
> so a minority of healthy stratified draws are refused as `IMBALANCED_PRE_PERIOD`: on a roster
> whose covariates hang together the way a chain's do a clear majority pass, and on a
> deliberately orthogonal one most do not. Both are measured in
> `tests/core/test_assignment.py` rather than argued. The direction is the honest one — a
> refusal with a reason code, never a number nobody can check — and it means **W6's
> false-refusal rate is a real number to be published rather than 100% by construction**, which
> is what this entry was created to prevent.
>
> **The revised condition:** T003 publishes that rate on `corpus/world/` — the false-refusal
> rate on W6 beside the false-positive rate on A/A — measured on data this repository did not
> write. Until then what is proved is that the arithmetic is now possible, not that it comes
> out well.

**Two of the four units of randomisation are refused by a declared assumption** · deferred
2026-08-27
`store_week` and `store_category` are refused with `UNIT_GUARANTEES_INTERFERENCE` before any
judgment has been exercised on anything. The refusal rests on `contracts/design/inference.yaml`'s
`carryover:` block and on nothing else: `reference_price_memory: true` with `washout_weeks: null`
crosses the dimension `store_week` splits arms along, and `cross_price_substitution: true` crosses
the one `store_category` splits along. Both are `kind: scenario_assumption` with a note and a
verification date. **Neither is an observation of anything in this repository** — and in particular
neither is grounded in what `corpus/world/` generates, which would be the generator and the engine
agreeing with each other while `core/` may not know `corpus/` exists at all.

`interference_of(unit, carryover)` is a pure function of that block, so the refusals are derived and
never written out. A contract declaring a washout long enough to exhaust the reference price would
admit `store_week` with no code change, and `tests/core/test_design_engine.py` asserts exactly that
by handing the function an independently built `carryover` with the flag cleared.

*The consequence for claim 6, recorded here because this is where it is created:* claim 6's headline
— *N proposed, M refused, K of those would have produced a confidently wrong number* — must be
**broken down by reason code and never reported as a single aggregate M**. A
`UNIT_GUARANTEES_INTERFERENCE` refusal is a design falling outside a declared envelope, exactly as
`CATEGORY_FROZEN` is not a pricing model failing. Adding the two kinds together flatters the engine
— it counts as "caught" a design whose judgment nothing inspected — and defames the proposer, by
charging it with an error it did not make. The same split governs K: only a *judgment* refusal can
be a design that would have produced a confidently wrong number.

*Unlock condition:* a **declared washout period**, sourced, at least as long as the reference price
persists, which makes `store_week` admissible; and a declared assortment separation, sourced, which
does the same for `store_category`. Until one of them is declared, two of the four units the form
admits are refused by a paragraph in a contract rather than by a calculation, and that is said out
loud rather than presented as arithmetic.

**The per-product-code cap is evaluated more strictly than the instrument requires** · deferred
2026-08-27
The 2026 measure caps gross margin **per product code against the 2025 annual average**. Core bounds
*this decision's own* margin, which is exact for the 2022 per-unit basis and stricter than required
for 2026, because the real aggregate needs a gold table rather than a pure function. Declared in
`MarginCapRule`, in `regulated_basket.yaml` and in `REGULATORY.md`, so no reader takes it for
implemented compliance.
*Unlock condition:* phase 2's gold layer, which can supply the realised per-code margin.

**The ladder knows about a floor and not about a ceiling** · deferred 2026-08-27
`ladder.quote()` takes a `floor` and clamps to it, per `floor_behaviour: clamp_to_floor` in
`ladder_policy@v1`. It takes no ceiling and the policy declares none. So wherever the margin cap
binds below the base price, the shallow rungs of the declared safe state produce prices the
envelope refuses — **716 of 26,600 ladder quotes** in claim 1's eval, on one envelope.

Restated on 2026-08-28 by T000, **because the figure this entry first carried was wrong.** It said
7,366, and 7,366 was every ladder quote the envelope refused for any reason outside the three
bounds the ladder models — counted as though all of them were ceilings. **6,650 of them are
`MARGIN_CAP_BASIS_UNEVALUABLE`**, a rule with no edge in either direction: it refuses every price at
every rung, and a ladder that took ceilings would not move one of those quotes. Doctrine rule 4 —
the prior value, the reason and the delta are all recoverable from this paragraph, and the finding
survives at a tenth of the size. `G6` now separates the two counts and publishes both, and
`tests/evals/test_guardrail_instrument.py` pins 716 and 6,650 so a change that merges them again is
red in the suite.

The guardrail set behaved correctly in both cases: it refused, by name, for a true reason. What is
incomplete is **doctrine rule 1**, and only for the 716. For an expiring product the safe state is
the ladder, and there the ladder's own answer is refused, so there is nowhere left to fall. It is
the same class as the finding a review made by composing two modules that had only ever been tested
alone — and it was found the same way, by composing them over inputs nobody chose.

`G6` therefore asserts only the three bounds the ladder is built to satisfy and publishes the two
counts beside it as numbers, rather than widening an assertion until the finding fits.

*Why it is not fixed here:* the frequency depends on the corpus's derived cost, so the first
question is how often it would happen against real costs, not how to make the number smaller. And a
ladder that took a ceiling would need `floor_behaviour`'s counterpart in the policy contract, which
is a contract change with a restatement.
*Unlock condition:* doctrine rule 1 being restated to admit an empty safe state — the change
`docs/doctrine-rule-1-ceiling` makes, on the 716 of 26,600 that `make eval-guardrail` still
publishes. Or phase 2's gold layer, which supplies a realised per-code margin and would replace the
derived cost with a measured one, at which point the frequency is a different number.
*Restated 2026-08-31:* this read *"the phase-1 integration session, which is allowed to propose a
restatement"*, which names a session rather than an event.

**The regulated basket's benchmark does not say which denominator it is in** · deferred 2026-08-27
ΥΑ 21330/2026 άρθρο 4 παρ. 4 defines the capped margin as
`(Τιμή Πώλησης − Μέσο Κόστος Πωληθέντων) / Τιμή Πώλησης` — a fraction of the **selling price**.
`evaluate` bounds the price at `cost + cost × markup`, a mark-up on **cost**. The two express the
same constraint and `m / (1 − m)` converts exactly, which is what claim 1's eval does.

Half of this **closed on 2026-08-28 by T000, and the title changed with it.** It was
"`benchmark_margin_pct` does not say which denominator it is in", and the field no longer exists:
`ProposedPrice.benchmark_markup_on_cost` takes a `MarkupOnCost` and refuses a bare number at runtime
as well as in the annotation, with `MarginOnPrice.as_markup_on_cost()` the only route between the
two. A caller who has the instrument's figure now cannot hand it over by accident.

What is still deferred is the **contract**. `contracts/guardrails/regulated_basket.yaml` names its
benchmark `average_gross_margin_2025`, and the instrument that defines that quantity defines it over
the price; the contract itself says nothing about the denominator. Applying 16.81% where 20.21% was
meant **fails safe** — a stricter cap — but it is an ambiguity in a load-bearing contract value, and
it was found by reading the instrument the corpus cites rather than by reading the contract, which
is exactly what an independent corpus is for.
*Unlock condition:* the next change to `regulated_basket.yaml`, which opens a window and carries a
restatement anyway. The benchmark's name or its documentation gains the denominator then. Until it
does, `corpus/real/MANIFEST.yaml` and `evals/guardrail/README.md` both state it.

**The contract's regulated basket still names three categories, not the decision's sixty-three** ·
deferred 2026-08-27
`regulated_basket.yaml` declares `dairy`, `bakery`, `poultry` as a `scenario_assumption`, on the
stated grounds that ΥΑ 21330/2026 "was not obtained". It has now been obtained and its 63 categories
are transcribed in `corpus/real/`, with the limit that the ΦΕΚ PDF itself was still not reached.
*Why it is not moved into the contract:* a corpus is not a contract. `corpus/real/` is the
independent evidence claim 1 attacks the gates **from**, and the moment the contract is populated
from it, the eval's regulated set and the envelope's regulated set have the same author again — the
trap, restored. Separately, the change opens a new effective window on a live guardrail and pulls a
restatement chain with it.
*Unlock condition:* a decision that the scenario's basket should mirror the real one, taken
deliberately and with the eval's independence re-argued in the same change — because the moment the
contract is populated from `corpus/real/`, the eval's regulated set and the envelope's have the same
author again. `docs/REGULATORY.md` item 6 carries the restatement in the meantime.
*Restated 2026-08-31:* this ended *"the phase-1 integration session is the right place"*. The
condition is the decision and its argument, not the sitting at which somebody takes it.

**No deferral in this registry carries a date, so `make expiry` is armed by its tests alone** ·
deferred 2026-08-27
All thirteen existing entries carry an unlock **condition**, which is prose and can never expire.
So the half of `make expiry` that refuses an expired deferral has nothing in the real registry to
act on, and would stay green today if its arithmetic were nonsense.

Partly answered on 2026-08-28 by T000: the CI-timeout entry above carries an expiry date alongside
its condition, so the dated half now has one real entry to act on and the target can go red on a day
nobody touched the repository. (Naming the marker in prose here is deliberately avoided — the first
draft of this paragraph spelled it out and `make expiry` read it, dating *this* entry too. A
registry parsed by a regex is a registry whose prose has to stay out of the way.) The general point stands — nineteen of twenty entries
are still condition-only — so this stays deferred rather than closed. That is the same shape as a
`claim-N` target with no mutation planted against it, and it is answered the same way:
`tests/ops/test_expiry.py` plants an expired entry into a copy of this file and asserts the target
goes red, by name and with the number of days it is overdue.

Recorded rather than quietly accepted, because "the target is green" and "the target would notice"
are different statements and only the second one is worth anything.
*Unlock condition:* the first deferral taken with a date rather than a condition — at which point
the registry arms the target itself and the planted entry stops being the only evidence.

**CI's gate job runs on a temporary 25-minute timeout** · deferred 2026-08-28
It was 15. T000 raised it after a run was cancelled at 15m16s — but the cancelled run is not the
evidence and should not be read as it. The evidence is the **spread between runners on the same
commit**: 11m00s passing and 15m16s cancelled, four minutes apart, on identical work. That is ~40%
variance, and a budget only the fast runner fits is a gate that reports which machine it drew
rather than the state of the code. Claim 1 did grow — 13 mutations to 16, and ~15% slower per eval
because `G10` makes a full independent pass over every bound — but that is the smaller half of the
arithmetic.

*Why it is a deferral and not a decision:* a guard loosened by 66% because it bound is the shape
oversight level 3 looks for, and answering "has any gate stopped biting, and for what reason?" with
"we raised it" twice in a row is how a gate becomes advice. It is recorded so the next session
inherits the argument rather than the number.

*What must not happen:* a third increase. T003 puts K = 200 seeds and six adversarial worlds into
this same job, and the answer there is **parallelising the mutations or splitting the claim targets
into their own jobs**, with the limit coming back down in that same change. `TASKS.md` carries the
instruction inside T003's `stop_at`, where a session will actually read it.
*Unlock condition:* T003, which cannot land without touching the job this bounds.
*Expires:* 2026-09-30 — because an unlock condition is prose and can never expire, and this
registry's own entry below says that is the half of `make expiry` nothing real was arming. This is
the first entry that arms it.

> **Closed 2026-08-28 by T003, and it did not happen by raising anything.** `ci.yml` now has four
> jobs where it had two: `gate` runs `make check`, the contracts and the expiry check and nothing
> else, `discover` reads the claim targets out of the Makefile and emits them as a matrix, and
> `claims` runs one per runner with `fail-fast: false`. **`gate` is back to 15 minutes**, which is
> what `TASKS.md`'s `stop_at` demanded, and the discovery property survives untouched: the targets
> are still never listed in the workflow, so a claim target that exists but is never run is still
> impossible by construction. The entry below carries the new job's own budget.
>
> *Closed:* 2026-08-28 — by T003, which split the claim targets into their own matrix jobs and
> brought `gate` back to 15 minutes. **This entry is why `ops/expiry.py` learned what closure is:
> it kept its `*Expires:* 2026-09-30` for three days after it was answered, and it was the only
> dated entry in the registry, so `make expiry` was going to go red on 2026-09-30 for a finding
> that had already returned.**

**CI's `claims` job runs on a temporary 90-minute timeout** · deferred 2026-08-28
`make claim-2` is the most expensive target in the repository and it is expensive for a reason
rather than by accident: it runs the **whole system** — pre-period, design engine, committed
lottery, exposure, four checks, readout — two hundred times on the A/A world and two hundred more
on W6, plus the four other worlds, and then plants eight mutations against the same checks at a
smaller configuration. Measured on the author's laptop: about eleven minutes for the published
harness on four workers and about nine for one uncached baseline plus eight mutated runs.

*It was 45 first, and the runner cancelled the harness before it finished.* That is what a
projection is worth against four cores: the laptop figure was taken on fourteen, and the number was
set from an estimate made before the cold run had been measured at all. It is recorded rather than
quietly corrected, because the entry above exists to stop exactly this happening twice and it
happened again inside the same change.

*Why 90.* It is the cold measurement plus the headroom the ~40% spread between runners on identical
work already demands in this repository. A budget only the fast runner fits is a gate that reports
which machine it drew.

*The steady state is much lower, and the first lever is already in.* `ci.yml` now carries `.worlds/`
across runs with `actions/cache`, keyed on **the digest `evals/uplift/cache.py` computes** rather
than on a hand-written file list — the same guarantee one layer out, so a changed corpus is a miss
here for exactly the reason it is a miss inside a run. Every run whose corpus is unchanged skips
generation entirely, which is about half the harness. What is left after that is the counts in
`contracts/design/aa_harness.yaml`, which are budgets and say so — though K = 200 on W1 and W6 is
the claim itself and is not among them.
*Unlock condition:* the first CI run with a **warm** world cache, which is the steady state this
number should be set from rather than the cold one it is set from now.
*Expires:* 2026-11-30 — a temporary budget with no date is a permanent one, which is what the entry
above was written to stop happening twice.

**W2's refusal is luck, and at a lower spillover the system would report a contaminated number**
· deferred 2026-08-28
There is no interference detector anywhere in this system, and `contamination.check` is not one:
its two questions are whether the recorded digest describes the arms it carries and whether each
unit received its own arm's policy, and neither can see a neighbour's trade crossing the road. The
defence is `feasibility.neighbour_exclusions` at moment 1, and the closed vocabulary's only
interference code is filed under `at_design`.

Measured over sixteen draws at the harness scale, W2 produced **no number at all** — every draw
refused `POWER_NOT_REACHED`, with the neighbour pairs declared to the engine and with them withheld
alike. That reads like a guard working and it is not one. The 18% spillover inflates the residual
variance past what the power check will admit, so **an unrelated guard fired**: a refusal by luck,
not by design.

*Why that is a limit and not a result.* At a spillover low enough that the variance stays under the
threshold, every check would pass and the system would state a contaminated number in silence.
Nothing in the four validity checks looks for interference, and `U6` publishes the **pair of
refusal rates** rather than a pair of biases precisely because there are no numbers to compare —
which is a measurement of the gap and not a closing of it.

*Why it is deferred rather than fixed.* Closing it means a fifth validity check and a new
`at_readout` code, which is a closed-vocabulary change with a restatement chain behind it, and it
needs a detector somebody can defend — an interference test at readout is a research question, not
an afternoon.
*Unlock condition:* a W2 variant at a spillover low enough to pass the power check, which would
**demonstrate** the silent contaminated number rather than argue for it. That world is cheap to add
and it is deliberately not added here, because the branch that finds a limit should not also be the
branch that decides what to do about it.
*Restated 2026-08-31:* this ended *"the phase-1 integration session (T008) is where the two are
weighed against each other"*. The session happened and weighed nothing, which is the evidence the
clause was a place to put the question down rather than a condition. What would unlock this is the
variant existing; adding it is still a decision somebody has to take, and no date is invented for
it here.

**W6's `IMBALANCED_PRE_PERIOD` rate is published with no threshold on it** · deferred 2026-08-28
`false_refusal_max_pct` — claim 2's statement that *a world where everything works produces the
number* — stays at **10%** and is left exactly as it was written, before anything was measured. What
changed is what it binds: **only the refusals the machinery produces**, which is every readout
refusal that is not `IMBALANCED_PRE_PERIOD`. The share of W6 draws refused for pre-period imbalance
is published beside it as a **number with no threshold** in this phase.

*Why the split rather than a bigger number.* T00E measured the balance pass rate on the corpus's own
roster at 145–192 of 200 over three world seeds — so the imbalance rate is roughly 4% to 27%, and on
W2's smaller roster up to 40%. A single threshold covering both would have had to move from 10 to
something that admits it, and **the only evidence for the new number would be the measurement that
raised the question**. That is a gate fitted to its own result, which is the shape oversight level 3
exists to catch and which `inference.yaml` refuses in as many words for the two thresholds it owns.
Publishing the figure unthresholded hides nothing, adjusts nothing, and leaves the question where it
belongs.

*What the rate is a function of, so that whoever sets a threshold knows what they are setting it
against:* the size of the control arm (53 at the harness scale, 43–44 in W2), the five covariates
`balance_covariates.yaml` fixes, and the 0.10 `balance_tolerance_smd`. It is sampling spread on the
**numeric** covariates and nothing else — the categorical half is pinned by the strata and is
refused at design since T00D, so what is left is the residue `strata.py` already declares as its own
limit: with a finite control arm, a covariate the others carry no information about keeps a spread
near the tolerance.

*What would give grounds to set one.* Two things this phase does not have. The rate measured across
more than one roster size, so its dependence on the control arm is a **measured curve** rather than
one point with an argument attached; and a declared statement, with a source, of how often a healthy
world may be refused before the system stops being worth running — which is a judgment about the
product and not an output of the harness.
*Unlock condition:* the two things this entry says are missing actually existing — the rate
measured across more than one roster size, so its dependence on the control arm is a curve rather
than one point, and a declared statement with a source of how often a healthy world may be refused.
`evals/unarmed-checks` is where the first is produced, because it is already opening `evals/uplift/`
to arm `U1`, `U3` and `U5`; the second is a contract change and belongs with it or after it.
*Restated 2026-08-31:* this read *"the phase-1 integration session (T008), which is the level
empowered to ask"*, which names a session rather than an event — and names one that has since
happened without the threshold moving, which is the evidence that it was never a condition.

**Branch protection covers `main` only** · deferred 2026-08-27
`main` is protected by a repository ruleset with **no bypass actors**, so the rule binds the owner
too: changes only through a pull request, `gate` and `secrets` both required and both green,
required linear history, no force pushes, no deletion. Verified rather than assumed — a direct push
to `main` was attempted and rejected by name (`GH013`, *"Changes must be made through a pull
request"*, *"2 of 2 required status checks are expected"*).

No other branch is protected and none needs to be. `deploy`, `backfill`, `run` and `destroy` are
specified to dispatch from `main` only; that constraint is currently a sentence in CLAUDE.md rather
than a workflow condition, because those workflows do not exist.
*Unlock condition:* phase 3, when they are written. Each gets an explicit `main`-only guard.

> **Restated 2026-08-30. The sentence above was true when it was written and stopped being true
> two days later, and the evidence was in its own quote.** *"`gate` and `secrets` both required
> and both green"* described the ruleset accurately on 2026-08-27, when `gate` ran every claim
> target. **T003 moved the claim targets into the `claims` matrix and the ruleset kept pointing
> at `gate`** — so from that commit until this one, **a pull request with a red `claim-2` merged.**
> Oversight level 1's whole sentence — *a session cannot merge something that breaks a claim,
> because the gate is structural rather than advisory* — was false, at the level everything else
> leans on.
>
> **The fingerprint was in this entry from the day it was written.** Its verification quotes
> *"2 of 2 required status checks are expected"*. The **2** was the finding. Nobody read the
> number, because the sentence beside it already said which two and they agreed — the defect
> `docs/reviews/phase-1.md` §8 names, one more time: the assertion checked against the sentence
> it came from.
>
> **What the ruleset requires is a fact about the forge, and nothing in this repository carries
> it.** `ci.yml` declares which jobs *exist* and never which are *required*; `make check` cannot
> read it; no test touches it. The phase-1 integration review read `ci.yml` line by line and
> measured 31 of its runs without being able to see this. It was found by asking the API.
>
> **The fix is one summary context, never a list of names.** `claims-complete` — `needs:
> [claims]`, `if: always()` — fails on anything that is not `success`, and the case that matters
> is **`skipped`**: a skipped matrix reports as neutral rather than red, which is how a matrix
> job passes silently. Enumerating `claim-1 … claim-7` in the ruleset would be a second registry
> of which claims exist, kept by hand, in a place no session reads and no test can see, needing
> somebody to remember it the day `claim-5` lands. `discover` already reads the targets out of
> the Makefile; this is the one context that summarises whatever it found, so a new claim is
> covered by nobody remembering anything.
>
> **Verified by attacking, not by reading** — the rule this repository applies to its own gates.
> It took **three** attacks, and the first two proved less than they looked like proving.
>
> | | attack | matrix | `claims-complete` | `gate` | merge |
> |---|---|---|---|---|---|
> | **A** | every `claim-N:` hidden from `discover` | `skipping` | fail in 2s | *also red* | `BLOCKED` |
> | **B** | claim 7's planted break 01, applied by hand | `failure` | fail | *also red* | `BLOCKED` |
> | **C** | the margin cap's bound carries another rule's name | `failure` | fail | **green, 919** | `BLOCKED` |
>
> **The `gate` column is why C exists.** A and B are caught by the suite as well —
> `tests/evals/test_ledger.py` parses the real Makefile, so renamed targets turn it red, and the
> decision key has a test of its own. They show the job fires on both non-success results and
> that the ruleset refuses; they do **not** show the context is necessary, which is this
> repository's own standard for a gate: *a gate can only be shown to bite where it is the gate
> that refuses.* On A the `gate` column was empty because `concurrency` had cancelled it, and
> the empty column was the finding.
>
> **No committed mutation can serve as the isolated attack.** Number 16 was tried and `gate` went
> red: `ledger.every-anchor-is-aimed-at-one-place` requires each anchor to occur exactly once,
> and applying the mutation removes it. The repository defending itself, and the consequence is
> that the isolated break had to be written fresh.
>
> **C is that break.** `cap_benchmark`'s bound is attributed to `markdown_max_depth_pct` — right
> amount, wrong rule name, so a certificate asserts a check that never ran. `make check` **green
> at 919**; `G10` red with **156,294 disagreements in 746,643 bounds**. It is the break `G10` was
> written for, and now the one `claims-complete` exists for: **before this branch that exact tree
> would have merged.** The three refusals, and the last one names a single context:
>
> ```
> A   2 of 3 required status checks have not succeeded: 1 failing.   (HTTP 405)
> B   2 of 3 required status checks are failing.                     (HTTP 405)
> C   Required status check "claims-complete" is failing.            (HTTP 405)
> ```
>
> **The standing limit, which is a real one and cannot be closed from inside.** Nothing here
> checks the *ruleset*. Remove the required context tomorrow and `claims-complete` goes on
> reporting green while nothing enforces it — the same hole one layer out. Anything living in
> this tree can only be checked by something the forge has already decided to run. So it closes
> as a **question in a procedure** rather than as a gate: *what does the ruleset require, and
> does it match the jobs that exist today?* is in T008's `closes` for the `integration-review`
> skill, because a rule only a conversation carries is a rule the next session never reads.

**Claim 2's eval has no three-question README** · deferred 2026-08-29
`evals/README.md`'s shape block declares `<claim>/README.md` — *what is attacked, where the
independence is, what it does not prove* — and `evals/guardrail/` has one. `evals/uplift/` does
not. The three answers exist and are good ones: the attack is in `evals/uplift/__init__.py` and in
`checks.py`, the independence argument is spread across `potential.py`, `reference.py` and
`cache.py`, and the third answer is **printed on every run** through `Report.notes`, which is the
half rule 6 makes enforceable and the half that cannot quietly stop being true. What is missing is
the one place a reader who has not opened the package can find the independence argument as a
single thing.

*How it was found, which is the interesting half.* It was invisible while there was one claim,
because with one sample the shape **is** whatever that sample does. It surfaced while T00B
extracted the `claim` skill from **two** closed claims rather than one — the second sample is what
turns a template into a rule, and the first thing a rule does is name what disagrees with it. It is
the same shape as the finding T003 stopped on: two artefacts each correct on their own, with
nothing computing the product.

*Why it is not fixed here.* T00B is an ops task that writes a method; writing claim 2's README is
writing claim 2's evidence, and a README synthesised in a branch that is not reading the estimator
line by line is exactly how a document comes to assert more than the code supports. This repository
has paid for that four times, twice inside the evidence layer itself. The skill records the
standard and names the divergence rather than declaring a shape half its own sample violates.
*Unlock condition:* the next task that opens `evals/uplift/` for a reason of its own — T012, whose
claim-5 work makes the two Python implementations three and therefore rewrites what that eval does
and does not prove, or T008 if it gets there first.
*Expires:* 2026-12-31 — a missing README has no natural deadline, so it gets a calendar one rather
than an unlock condition alone, which `make expiry` can never evaluate.

**No threshold at which a reconstruction stops being usable** · deferred 2026-08-29
Claim 4's correction expands a censored store-day by the share of an ordinary day its open window
covers, and how well it does that is a function of that share. Measured, on three worlds at
`rehearsal` scale: at a share of 0.94 the reconstruction lands within 0.1% of the withheld truth;
at 0.06 it comes out **36–40% high**. The reason is selection rather than arithmetic — a day only
yields a point estimate if it sold something inside the observed window, so conditioning on that in
a thin window keeps the days that over-performed in it.

A real estimator would want a rule: below some share, report the lower bound and no number. This
repository declares none, and the absence is deliberate rather than pending. Such a number is an
assertion about what the system does wearing a number instead of a verb, and `CLAUDE.md` requires
one to be set from the measurement of what comes out when it runs. What runs here is a *constructed*
censoring on days that did not actually run out; a real stock-out is endogenous — it happens on
unusually busy days — so the error at a given share on a real stock-out is not the error measured
here. Picking a threshold off this measurement would be setting a live guard from the wrong
distribution, which is the shape of `timeout-minutes: 45` one layer along.
*Unlock condition:* T014, the training pipeline, which is the first consumer that has to decide what
to do with a reconstructed store-day. The threshold — if there is one — is declared as a
`{value, source}` pair in a contract like every other number in this repository, and the source is a
measurement over the days the pipeline actually trains on.

**The endogeneity of a real stock-out is not measured, only stated** · deferred 2026-08-29
`evals/censoring/` grades its correction by censoring held-out store-days **on purpose**, at a
declared grid of hours, and comparing the reconstruction against what those days actually sold. That
is what makes the grading independent of the simulator: the truth is a receipt total the corpus
emitted, not a latent intensity the generator knows.

It is also the limit. A day censored at 16:00 by this eval is an ordinary day; a day whose shelf
emptied at 16:00 is an unusually busy one, and the correlation between running out and selling a lot
is exactly the thing that makes real censoring bite. Nothing in this repository holds the unserved
demand that would let the two be compared, and that is on purpose —
`corpus/world/events.py` says so in as many words: *"a corpus that emitted them would be handing
claim 4 the answer it is supposed to have to reconstruct."* So the eval publishes the gap in
`Report.notes` on every run rather than closing it.
*Unlock condition:* a corpus stream that carries counterfactual demand **for the eval only**, sealed
the way `corpus/world/seal.py` seals the injected truth and opened only after the reconstruction is
written. It is the same shape as claim 2's seal and it would be built the same way. It is not built
now because it is a second sealed channel for one claim, and the honest statement of the gap costs
nothing and cannot rot — it is printed on every run.

**One pooled availability curve per world** · deferred 2026-08-29
`censoring.fit` takes whatever days it is given and returns one curve; pooling is deliberately the
caller's decision, because a grouping rule baked into the core would be a silent modelling choice.
`evals/censoring/` calls it once per world, over every store and every category together. A real
estimator would almost certainly want a curve per category — bakery empties in the morning and
poultry does not — and probably per store format and per day of week.

Nothing here is wrong; what is missing is evidence that the correction survives being grouped. The
eval would show it as a *smaller* residual error, which is the direction that flatters, so adding
groupings without a consumer that needs them would be tuning a published figure.
*Unlock condition:* T014. The training pipeline is what decides what a demand feature is grouped by,
and the eval gains the grouping the pipeline actually uses rather than one chosen to improve a
number.

**The censoring correction has no consumer** · deferred 2026-08-29
`holdout.core.demand.censoring` is proved by `make claim-4` and called by nothing else. `CLAUDE.md`
puts stock-out marking in silver and the correction in training, and neither exists yet. So claim 4
today is a proof that the arithmetic and the refusals are right, not a proof that the system uses
them — which is the same standing at which claim 1 sat before the decision path was composed, and
the reason `tests/core/test_composition.py` exists.
*Unlock condition:* T014's training pipeline and T010's silver layer. When `shelf_state` is a table
and a demand feature is built from it, the composition is what claim 4 has to survive — a censored
day reaching a feature table unmarked is doctrine rule 2 broken, and it will be provable end to end
rather than one module at a time.

**No source has declared what `stocked_out_from_hour` means** · deferred 2026-08-29
`holdout.core.demand.censoring` expands a censored store-day by the share of an ordinary day its
open window covers, and which way that errs depends entirely on what the column means. The hour
on-hand reached zero and the hour the first shopper was turned away are the same number only if
somebody was there at the moment the shelf emptied. Measured on this repository's corpus they differ
on **7,290 of 16,942 censored store-days (43.0%)**, by up to fourteen hours, and correcting against
a hour derived from the last inventory movement raises the reconstructed total by **6.3%**.

The eval publishes both rather than picking one, the module's docstring states the dependence
instead of asserting a flat direction, and `C12` measures the one property that holds either way —
that no censored day sells *after* its recorded hour, which is the only shape that would inflate a
reconstruction without bound. What is *not* settled is which reading a real `shelf_state` will
carry, because no `shelf_state` exists yet.
*Unlock condition:* T010's silver layer. Stock-out marking happens there, from the inventory
movements, and the derivation it writes is what fixes the meaning — at which point the column gets
a declared definition and the correction's direction stops being conditional. Until then the
conditional statement is the honest one, and it is printed on every run.

**`C7`, `C11` and `C12` own no `gate-proof` mutation, and cannot** · deferred 2026-08-29
`make gate-proof`'s "no unproven gate" rule is a **target-level** check: `claim-4` owns nine
mutations, so the ledger is satisfied. Per check, three of claim 4's twelve are outside the net, and
for a reason rather than by oversight. `C11` and `C12` assert properties of the **corpus** — how
much of it is censored, and that no day sells after its recorded stock-out — and no break planted in
`src/holdout/` can move either. `C7`'s disjointness half is a tautology, because the two segments
are complementary predicates over one business date; only its "neither segment is empty" half can go
red, and the check says so in its own `detail` rather than leaving a reader to assume otherwise.

This is the standing limit of `gate-proof`'s guarantee and it is stated here rather than left to be
rediscovered: a check that asserts something about the *inputs* cannot be proved to bite by mutating
the *system*.
*Unlock condition:* `evals/unarmed-checks`, which is the change that answers this for all 21
checks that own no mutation rather than for these three alone: each gets either a mutation or a
written reason it cannot have one. Whether corpus-property checks want a second harness — one that
mutates the corpus rather than the system — is decided there, with the whole list in front of it.
Not built before then because one harness with a clear scope beats two with an unclear one.
*Restated 2026-08-31:* this read *"the phase-1 integration session decides"*, which names a session
rather than an event.

**Claim 7 is proved over `holdout.core` and the contracts, and nothing else exists yet** · deferred
2026-08-29
`evals/oversight/` scans every type in `holdout.core`, **every identifier `src/holdout/` defines**,
every metric grain, every idempotency key, every balance covariate and every compiled consumer
under `generated/`. That is the whole of the system today, which is why the eval can say
*structurally impossible* rather than *not currently present*. It will stop being the whole of the
system at T009.

*Restated 2026-08-29, before this entry was a day old.* The first wording said the identifier scan
read *the core's* source text, and named the uncovered routes as `adapters/` and `pipelines/`. That
was false by omission: `src/holdout/contracts/` is fifteen modules of loader and compilers, neither
empty nor nonexistent, and `reference.CORE` stopped at `core/`'s boundary — so a `customer`
parameter on `compile_agent_tool`, the exact shape mutation 05 proves `O5` catches inside `core/`,
was outside the scan. Oversight level 2 found it. `reference.identifiers` now reads all of
`src/holdout/`, which is what closed it, and the collisions that surfaced — `parents`, `url`,
`compile_agent_tool` — are published with their reasons rather than filtered. The **type** registry
still stops at `holdout.core`, deliberately: `O2`, `O3`, `O4` and `O11` are about the types a
decision passes through, and those are all in `core/`.

The routes still **not** covered, named rather than left to be discovered: `src/holdout/adapters/`
is empty; `pipelines/silver/` and `pipelines/gold/` do not exist; the contract loader's own types
are read for their *identifiers* but are not in the registry; and a bronze table is *the source's
shape* by design — CLAUDE.md is explicit that nothing is transformed at ingestion — so a POS line
arriving with a loyalty number would land in bronze and this eval would not see it. That
is not a hole in claim 7 as stated (the claim is about what a **decision** is addressed by, and a
decision is addressed by a `DecisionKey`), but it is a hole in the sentence *"a test goes red if
one appears"* the moment there is somewhere else for one to appear.

*Why it is deferred rather than fixed.* Writing a scan against `pipelines/` that does not exist
would be a check with nothing to check — vacuously green, and green in a way that reads as covered.
That is the exact shape this repository refuses in `make gate-proof`'s *no unproven gate* rule.
*Unlock condition:* T011, which builds the gold layer. `O10` already reads the metric grain the
gold models compile from, so the extension is to the silver tables' declared schemas and to the
Lakebase decision record — the two places a customer column would arrive with a straight face.

**The two person-vocabularies are pinned, so nothing notices a name published after them** ·
deferred 2026-08-29
`corpus/real/` holds schema.org release 30.0 and Presidio at commit `eb93051b`, both pinned on
purpose: *latest* is not a provenance, and a digest over a moving target is a digest that will one
day be wrong for a reason that is nobody's fault. The cost of the pin is that the 317 names are the
317 that existed on 2026-08-29. schema.org adds properties every release and Presidio adds
recognizers most months; neither addition would turn anything red here.

The consequence is bounded and worth stating exactly. `O4` and `O5` — the checks that *read names*
— would not recognise a name invented after the pin. `O2`, which is the check that carries the
claim, does not read names at all and is unaffected: it refuses a field called `q7` on the same
evidence as one called `nationality`. So the pin ages the net, never the guard.

*Why it is not fixed by fetching at run time.* An eval that downloaded its own corpus would stop
being reproducible the day a source moved and would stop running on a laptop with no network, which
is the property every claim in this repository depends on. The fix is a periodic re-fetch, which is
a calendar decision and therefore gets a calendar.
*Unlock condition:* none that a checker could evaluate — the vocabularies do not announce
themselves.
*Expires:* 2027-02-28 — six months, at which point `corpus/real/fetch.py` is re-run, the digests and
row counts are restated in `MANIFEST.yaml` rather than overwritten, and the measured reach of the
hand-written word list is published again against the new total.

**`CLAUDE.md` asserts an ESL penetration figure with no source behind it** · deferred 2026-08-30
The envelope table's row for free dynamic pricing reads *"ESL penetration is ~30% of large European
retailers; display rules are tightening"*. The row's conclusion is right and is not in question: a
price cannot be changed on a shelf that has no electronic label, and that is a real constraint on
what the system may claim to do. The **number** is the problem. It occurs exactly once in the
repository, and nothing stands behind it: no command produces it, no contract holds it so
`make contracts` has never asked it for a `source`, it is not a statement about the synthetic
scenario, and there is no publisher, no URL and no verification date for it anywhere — not in
`docs/REGULATORY.md`, not in `corpus/real/MANIFEST.yaml`.

That is the one shape this repository makes a build failure inside `contracts/`: a value about the
outside world with no citation. Doctrine rule 3 does not care what extension the file has, and
`CLAUDE.md` is the file every session reads first.

*How it was found:* by writing `docs/SCENARIO.md` under a rule that every number must be
classifiable as measured, declared, cited or scenario. This one is none of the four, so it did not
go into that file, and the absence is named there rather than left for somebody to notice.

*Why it is not fixed here:* two reasons and both are about where a change lands. Fixing it means
either finding a source — a real retail-technology survey, opened and dated, which is research and
not an edit — or deleting the number and leaving the sentence, which is a change to `CLAUDE.md`'s
envelope table made on a documentation branch, in the file that governs every other branch. A
project's own context file is the last place to make an unrequested edit.

*Unlock condition:* `docs/layout-and-restatements`, the branch that edits `CLAUDE.md` for the
review's other findings and is therefore the one change where this figure can be cited or dropped
without `CLAUDE.md` being opened for it alone. Failing that, the publication checklist, since this
is a number a public README would repeat.
*Restated 2026-08-31:* this read *"the phase-1 integration session (T008)"*, which names a session
rather than an event — and the session came and went while the figure stayed.
*Expires:* 2026-11-30 — because an unlock condition is prose and can never expire, and a sourceless
number in the file every session reads first should not be able to sit here indefinitely.
