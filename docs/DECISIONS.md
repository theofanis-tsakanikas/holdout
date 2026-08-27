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

---

## Deliberately deferred

Each entry says what would unlock it. An item with no unlock condition is not deferred, it is
forgotten.

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

*Unlock condition:* the next time `floor.yaml` opens a **new** effective window for an unrelated
reason. The new window carries the corrected id and its restatement; the closed window keeps the old
one, which is exactly what "never deleted" is for. Failing that, it is a deliberate item for the
phase-1 integration session, which is allowed to propose a restatement.

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
envelope refuses — **7,366 of 26,600 ladder quotes** in claim 1's eval, on this repository's own
contract envelope among others.

The guardrail set behaved correctly: it refused, by name, for a true reason. What is incomplete is
**doctrine rule 1**. For an expiring product the safe state is the ladder, and here the ladder's own
answer is refused, so there is nowhere left to fall. It is the same class as the finding a review
made by composing two modules that had only ever been tested alone — and it was found the same way,
by composing them over inputs nobody chose.

`G6` therefore asserts only the three bounds the ladder is built to satisfy and publishes the
ceiling count beside it as a number, rather than widening an assertion until the finding fits.

*Why it is not fixed here:* the frequency depends on the corpus's derived cost, so the first
question is how often it would happen against real costs, not how to make the number smaller. And a
ladder that took a ceiling would need `floor_behaviour`'s counterpart in the policy contract, which
is a contract change with a restatement.
*Unlock condition:* the phase-1 integration session, which reads the whole repository against
`CLAUDE.md` and is allowed to propose a restatement — or phase 2's gold layer, which supplies a
realised per-code margin and would replace the derived cost with a measured one.

**`benchmark_margin_pct` does not say which denominator it is in** · deferred 2026-08-27
ΥΑ 21330/2026 άρθρο 4 παρ. 4 defines the capped margin as
`(Τιμή Πώλησης − Μέσο Κόστος Πωληθέντων) / Τιμή Πώλησης` — a fraction of the **selling price**.
`evaluate` bounds the price at `cost + cost × benchmark_margin_pct`, a mark-up on **cost**. The two
express the same constraint and `m / (1 − m)` converts exactly, which is what claim 1's eval does.

But `contracts/guardrails/regulated_basket.yaml` names its benchmark `average_gross_margin_2025`,
and the instrument that defines that quantity defines it over the price. A caller feeding it
straight in would apply 16.81% where 20.21% was meant. That **fails safe** — a stricter cap — but it
is an ambiguity in a load-bearing field, and it was found by reading the instrument the corpus cites
rather than by reading the contract, which is exactly what an independent corpus is for.
*Unlock condition:* the next change to `regulated_basket.yaml`, which opens a window and carries a
restatement anyway. The field's name or its documentation gains the denominator then. Until it does,
`corpus/real/MANIFEST.yaml` and `evals/guardrail/README.md` both state it.

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
deliberately and with the eval's independence re-argued — the phase-1 integration session is the
right place. `docs/REGULATORY.md` item 6 carries the restatement in the meantime.

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
