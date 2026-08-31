# Findings

A finding is something a review said is wrong. This file is where one lives while it is open,
and `make findings` is what stops it leaving without being closed.

**Read this paragraph before trusting anything below it.** A representation is not the thing, and
every mechanism in this project produces representations. `make figures` is a representation of
coverage; `make language` matches a character range and concludes about language; this file is a
representation of findings. It will fail the same way they can, and the failure will look like a
green run. What it buys is not truth — it is that **silence stops being free**.

---

## Why this file exists

Every mechanism this repository had was aimed at a **claim**, a **gate** or a **deferral**. An open
review finding is none of the three, so it had nowhere to fall out of, and two of them fell.

**On 2026-08-27 oversight level 2 recorded three blocking findings against claim 1.** T000 closed
the first two and the type-level half of the third. The legal half of the third — a 2008–2020
industry median described as the 2025 benchmark, and an equivalence read into an article that does
not contain it — was never closed and was never deferred. It simply stopped being anywhere. **Four
days, twenty-one commits, and neither `make expiry` nor the phase-1 integration session could see
it**: not a deferral, so the first had nothing to read; not named in `CLAUDE.md`, so the second had
nothing to check against.

**And the review that found that lost one of its own.** `docs/reviews/phase-1.md` §4 —
`pricing/selection.py`, the one core module no eval reaches and no mutation targets — was recorded
in a document whose closing table assigns every other section to a branch, and assigned to none.
One day, in a nine-row table written for exactly that purpose.

Two findings, two documents, two different ways of losing them. Neither was caught by anything.

---

## What the gate checks

**A finding anchors to a line that already exists.** Each `*Site:*` names a file and quotes a
fragment that must occur in it **exactly once**. Zero means the line moved or was fixed — in which
case the finding is either stale or closed, and either way somebody has to say which. Two means the
anchor is ambiguous and proves nothing about which line was meant. It is
`ledger.every-anchor-is-aimed-at-one-place` with a new population, and that check is not a guess:
it is what refused a hand-applied mutation 16 during `ops/claims-are-required`.

**A finding with no site is refused.** Not badly filed — a finding whose consequence is recorded
nowhere, which is precisely what the legal one was for four days.

**A finding declares a disposition**, and `none — <reason>` is a disposition. What is refused is
saying nothing. An entry that names no branch, no task and no reason is **adrift**: it is reported
in its own count and it does not turn the gate red, because a finding nobody has scoped yet is a
real state and refusing it would only teach people not to file.

**Closure is a transition, not a verdict.** An entry closes on exactly three things: the anchored
line changing, a branch landing with the gate going red-to-green, or a named human saying so. Any
of them goes in a `*Closed:*` line with the date and what happened.

**And closure restates a site rather than releasing it.** A closed entry keeps being checked — on
the text that replaced the defect. Every site gets a `*Now:*` line carrying either that text, held
to the same exactly-once rule for as long as the entry exists, or `gone — <reason>` where nothing
replaced it. The original `*Site:*` stays beside it, per doctrine rule 4.

This is not tidiness. **A finding that stops being examined the moment somebody accounts for it is
a claim about the past that reads as a claim about the present**, and a fix reverted in November
would leave this file saying `closed` forever. It is the legal finding's own story one layer along:
two of its three parts were closed, and what made the third invisible was that nothing re-examines
a thing already accounted for. The first draft of this registry had exactly that property and the
reviewing session found it before the file landed.

The price is naming the replacement text, not only the transition — the price the `[M]` rule
already charges: a number is not published without the command that produces it, so a defect is not
recorded as fixed without the text that fixed it.

### `concurred` is not `closed`

**Two agents agreeing is not a check.** It is two representations agreeing, which buys nothing
about truth — and it is how one of these findings would have left the record a second time. On
2026-08-31 the reviewing session removed §4 from the author's list on the grounds that the two
sessions concurred; the builder session objected that this is the exact mechanism by which the
legal finding was lost, *not a decision to drop it, but two parties who held it agreeing it was
handled and nobody holding them to that.*

So `*Status:* concurred` is a state this file can carry, it prints in its own count, and it is
**counted as open**. If the two heaviest users of a register could retire an entry by agreeing,
the register would measure their agreement rather than the repository.

> *It was my finding, and that is exactly why I should not be the one deciding it needs no
> oversight.*
>
> *It was not my finding, and that is exactly why my agreement is worth less than it feels.*

Neither works alone. And the instance that produced them was caught inside an hour only because
one party happened to remember a rule it had stated that morning — which is not a defence, and is
this file's own blind spot rather than an argument that it does not have one.

### The anchor and doctrine rule 4, which interact

**An anchor detects drift and revert. It cannot detect *fixed*, and that is an interaction with
this repository's own convention rather than a shortcoming of anchors.**

Doctrine rule 4 says a correction never erases what was previously stated. So a fix here usually
*restates*: the new text goes in and the defective wording is kept beside it, quoted. The anchor is
on the defective wording — so it survives the fix, and the entry stays green while its subject is
already repaired. Closure is what records that, and closure is a transition rather than an anchor
vanishing, which is why nothing breaks.

**An anchor vanishing is therefore the unusual case, and it means the site was *rewritten* rather
than restated** — that is, the repository's own convention was not followed there. `MOVED` asking a
person is exactly right for that: it fires precisely where somebody should look.

*Both behaviours appeared within an hour of this file landing, on the same fix.*
`corpus/legal-claims-restated` restated three sites with the old wording quoted, and their anchors
held; it rewrote `PLAN.md`'s, and that anchor vanished and turned the gate red. Same branch, same
finding, two behaviours, decided by how each restatement was written. Neither session saw it at
design time. The answer was to **split** the entry — one anchor was answering for two defects with
different fixes and different landing dates — rather than to loosen the check, and the split
produced this file's first closure through the mechanism instead of around it.

### The count is printed and asserted by nobody

`tests/ops/test_findings.py` asserted `len(findings) == 2` until the split above turned it red on a
legitimate change. **A frozen count standing in for the property it was there to protect**, inside
the work about numbers standing in for things. The property — both founding entries filed open,
dated before any branch that touches them — is what the test asserts now. The count is printed by
`make findings` and claimed by nothing.

**The standing limit.** An anchor proves a line exists and still reads as expected. It cannot prove
it is the **right** line. A true but irrelevant anchor is a green that means nothing, and no
mechanism here can catch it — the same limit as a mutation planted against the detector, which this
repository closed by putting the detector out of reach rather than by testing the choice.

---

## Open
**A guardrail rule id does two jobs, and a rename breaks the second one** · found 2026-08-31 · by
oversight level 2 on `contracts/floor-rule-id`, and the check that produced it was proposed rather
than assumed
**One rename cost a compatibility mapping and a guard; fifteen other rules can each do the same.**
A rule's `id` **names the rule inside a window** and **identifies the same rule across windows**.
Those are different properties carried by one string, so renaming for the first breaks the second —
and `RENAMED_RULES` in `envelope.py` is what you build when identity and spelling are the same
field. It is why the deferral did not anticipate the cost: it scoped a rename, and this was never a
rename.

*The check that settles whether a map is needed at all.* If resolving a decision meant finding the
applicable window and reading the id **in that window**, there would be nothing to map — the closed
window keeps its own spelling by contract rule 1, and each window is self-describing. So: what looks
a rule up by a single canonical name across all time?

**`envelope_as_of` does, and it does it sixteen times.** It resolves each contract rule into a
dataclass field by a hard-coded literal — `minimum_gross_margin_pct`, `cost_staleness_hours`,
`cap_benchmark`, `perishable_exemption` and twelve more. It cannot read "the window's own id"
because a window carries four or five ids and nothing says which one fills
`FloorRule.cost_staleness_hours`. The literal **is** the link, and it is the only one. So the map is
necessary in the current model, and **fifteen other rules carry the same latent cost**: each is one
rename away from needing its own entry.

*Three shapes, with their prices, so whoever takes this is choosing.*

**The map, which is what shipped.** Correct, guarded — a window carrying both spellings is refused,
because two rules with one meaning leave nothing able to say which was in force — and checked to
bite, since emptying it turns the suite red. Its price is that it accumulates forever and it puts
contract knowledge in the engine, when the contract layer is this repository's declared source of
truth. A real cost paid slowly rather than a defect.

**A window-scoped vocabulary.** Better placed, but it does not remove the map on its own: the
sixteen literals are the problem, and moving them into the contract only moves where the
correspondence is written.

**Separating identity from spelling** — a stable identity that never changes, and an `id` that is
the human-readable name within a window. Then a rename changes a spelling and nothing else, and no
map is ever needed. This is the real fix and it is a change to the **contract model**, so it may
not ride on a branch about one rule.

*What is not in question.* The refusal of a window carrying both spellings is right under all three
shapes and stays wherever the resolution ends up living.

*The map got a time bound before it shipped, and the review is what found it missing.* As first
written, `RENAMED_RULES` was keyed by guardrail and canonical id alone, with nothing scoping an old
spelling to *when* it was valid — so a window opened in 2027 carrying the retired id resolved
without complaint, undoing the rename the mechanism exists to serve. It reproduced before it was
fixed. `Renaming` now carries `since`, an old spelling is readable only in a window that opened
before it, and `tests/core/test_envelope.py` holds both halves — the refusal, and the historical
window still resolving, so the fix is a time bound rather than a ban. **The mechanism being a
symptom is unchanged by that, and is the finding.**

*Anchor re-aimed 2026-08-31, and the gate is what asked.* `make findings` reported `MOVED` when
`RENAMED_RULES` changed type from `tuple[str, ...]` to `Renaming` under this branch's own F1 fix.
The register says an anchor vanishing means the site was **rewritten** rather than restated, and
that only a person can say whether the finding was fixed. It was not: the map still exists, an id
still does two jobs, and the fix made the map *more* elaborate rather than less. So the anchor moves
to the line that carries it now.

*Site:* `src/holdout/core/guardrails/envelope.py` :: `RENAMED_RULES: dict[tuple[GuardrailId, str], Renaming] = {`
*Disposition:* its own branch, unlocked when **the contracts move in phase 2** — the event
`docs/DECISIONS.md` already declares for *"the generated SQL has never been executed"*: `phase 2,
when gold is built. If gold does not match, the contracts move`. That is the moment the contract
model is open anyway, and separating identity from spelling is cheap while it is being changed and
expensive at any other time. The two travel together
*Status:* open

**`claim-2` costs an hour and the whole matrix re-runs on every push** · found 2026-08-31 · by the
author, and decided rather than deferred
`claim-2` runs on one machine at **32m17s to 1h18m18s** against a 90-minute timeout, and every
intermediate push re-runs the full matrix. On `#30` that meant three draws for a pull request that
needed one — the branch, the review fixes, then a follow-up — with one cancelled at 65 minutes and
two superseded. The question raised was whether an hour a run is what a professional would do. The
answer taken: **the cost per run is justified and the dead time is not.**

*And the within-commit spread is a draw, not a constant — which is what the second pair
established.* Two pairs are now measured, each being one commit's two matrix legs, same tree, same
push, same cache key:

| commit | legs | apart |
|---|---|---|
| `7b1fd6c` (#30) | 32m30s · 32m47s — runs 33358845044, 33358846344 | **1.01x** |
| `46b8225` (#27) | 32m17s · 54m39s | **1.69x** |

One pair agreed to within seventeen seconds; the other disagreed by twenty-two minutes. So there is
no *within-commit variance* to use as a headroom multiplier — **one pair predicts nothing about the
next**, and the distribution to size a budget against is the distribution over **runners**, not over
commits and not over pairs. The pair that agreed is as much a measurement as the pair that did not,
and it is the one that would have been dropped as unremarkable. The honest summary of the sample:
eight or more measured runs, **32m17s to 1h18m18s, 2.43x**, with the maximum having moved once. It
is *the largest number seen so far is not the largest number*, one level along.

*Two fixes, neither of which changes what is proved.* **Sharding `claim-2` across its six worlds**
is the large safe win — the same work on more machines, nothing skipped, roughly six-fold on wall
clock, with a combine step as the real cost because the eval prints aggregates across worlds. **A
merge queue** is second: the expensive matrix once, on the merged result, rather than on every
push. `#30`'s two superseded runs are the measurement that justifies it.

*And path filtering is refused, by name and in advance.* Skipping `claim-2` when only documents
change reintroduces **a claim that silently does not run**, which is precisely what `discover` and
`claims-complete` were built to make impossible — the `claim-[1-7]` defect bought back for a saving
in minutes. It will be proposed as the obvious cheap fix, and this line is here so that whoever
proposes it meets the refusal before the argument.

*The practice that costs nothing and was adopted immediately:* finish a piece locally, run
`make check` and the relevant `make claim-N`, and **push once**. Where a review produces findings,
apply all of them and push the result. That captures most of a merge queue's benefit with no
engineering.

*Revisit trigger, so this is a decision and not a deferral with no teeth:* **if any of phase 1's six
remaining branches causes more than two full-matrix runs through incomplete work, the arithmetic
changes and this reopens.**

*Restated the same day, before it was ever evaluated, because the first wording counted the wrong
thing.* It read *"needs more than two pushes"*. A rebase forced by somebody else's merge is a
second push and is not waste: the branch was pushed once, complete and green, which is what the
practice asks, and counting it would penalise the discipline rather than the waste. What the trigger
is actually about is a matrix run caused by work that was not finished.

*And the case that produced the restatement is itself a measurement for the fixes above.* `bec0e7f`
landing on `main` forced a rebase and a second full-matrix run of `contracts/floor-rule-id` — an
hour, unavoidable **only because there is no merge queue**, since a queue rebases and runs once at
the end. So it is not a trigger hit; it is another priced argument for the second fix.

*Site:* `.github/workflows/ci.yml` :: `timeout-minutes: 90`
*Disposition:* its own branch, before the first Terraform layer — phase 2 is where the push rate
multiplies, and CI is what everything else depends on, so rebuilding it mid-phase risks the defect
it protects against. Phase 1's six remaining branches are four documents and two small ones; they
do not justify rebuilding the thing that judges them
*Status:* open

**The corpus describes an industry median as the benchmark a Greek instrument defines** · found
2026-08-27 · by oversight level 2
The third of three blocking findings against claim 1, and the one that left the record. Two
statements are wrong and they are separable.

*The equivalence.* `corpus/real/` states that Eurostat's gross margin over **turnover** is *the same
quantity* ΥΑ 21330/2026 άρθρο 4 παρ. 4 calls ΠΜΚ, a margin over the **selling price**. The same
denominator *family* is defensible; the same quantity is not. Turnover is not the selling price of
one product code, and an industry median is not a trader's own average. The article does not
contain the equivalence; it was read in. `corpus/real/README.md` then attributes the exactness of
`m / (1 − m)` to that alignment, which makes a fact of algebra depend on a legal claim that is not
in the text.

*The benchmark.* The instrument anchors the benchmark to the trader's own 2025. The corpus uses a
2008–2020 industry median and `evals/guardrail/build.py` calls it *"The published 2025 gross
margin"*, which is wrong on both words that matter, at the point closest to the arithmetic — and it
**is** the cap's benchmark: `sector_wide_benchmark_on_price()` feeds `ProposedPrice.benchmark_markup_on_cost`
on all 232,373 decisions claim 1 drives.

*What does not move.* **Claim 1 does not reopen**, and the reason was written three weeks before
anybody needed it: the eval prints on every run that it does not prove the numbers in
`contracts/guardrails/` are the right ones, only that the machinery honours whatever envelope it is
handed. `contracts/guardrails/regulated_basket.yaml` keeps its benchmark symbolic and sourced, so
the contract does not implement the law with a median either. What does not survive unqualified is
the **scenario** claim — a corpus presented as real, citing a live Greek regulation, whose concrete
benchmark is a construct that regulation does not use.

*The article behind it was also miscited*, which is its own entry below — split out on
2026-08-31 because the two have different files, different fixes and different landing dates, and
one entry covering both meant one anchor answering for two defects.

*Corroboration, labelled as what it is:* the reviewing session opened a secondary source
reproducing the decision's full text on 2026-08-31 and reports both articles verbatim. Not the
gazette, not opened here, and nothing above depends on it.

*How the scenario half was settled, which was not ours to settle.* The prose sites are defects and
were fixed. What was left is a judgment about the product: a corpus presented as real, whose
concrete benchmark is a construct the regulation does not use, is either an acceptable declared
limit or a claim the corpus should stop making. The author decided: **real inputs, derived cost** —
the wording becomes precise everywhere the corpus is described, and *real* does not stand alone with
the derivation in a footnote. Six sites carry it now: this directory's README and `__init__`, the
manifest header, the attack's own docstring in `evals/guardrail/checks.py`, the eval's README, and
`docs/SCENARIO.md`. The prices, endings, dispersion, markdowns, regulated list and margin statistic
are real; the unit cost is a construct, and it is named as one every time.

*Site:* `corpus/real/README.md` :: `That alignment is not a`
*Site:* `corpus/real/MANIFEST.yaml` :: `Eurostat's ratio is gross margin on goods for resale over turnover,`
*Site:* `evals/guardrail/build.py` :: `The published 2025 gross margin`
*Disposition:* branch `corpus/legal-claims-restated`
*Closed:* 2026-08-31 — `corpus/legal-claims-restated` landed. The four sites are restated with their prior wording kept beside them per doctrine rule 4; the corpus's benchmark is named `sector_wide_benchmark()` at every call site rather than reshaped, because the per-code shape was already in the core; and the author decided the scenario half — *real inputs, derived cost*, stated wherever the corpus is described rather than *real* alone with the derivation in a footnote. Claim 1's output is bit-identical to `b7ab2ae` over 232,373 decisions, sha256 `22a6daea…`.
*Now:* `corpus/real/README.md` :: `So the accurate description of what claim 1 is driven by is`
*Now:* `corpus/real/MANIFEST.yaml` :: `It is a corpus device for deriving a plausible`
*Now:* `evals/guardrail/build.py` :: `A sector median over 2008-2020, standing in for a quantity no public dataset contains.`

**The finding miscites the article it rests on** · found 2026-08-31 · by the reviewing session
Split out of the entry above on 2026-08-31. `PLAN.md`'s record of oversight level 2's third
blocking finding said ΥΑ 21330/2026 **άρθρο 4 παρ. 5** *"defines the benchmark as the trader's own
average, per product code, over 2025"*. παρ. 5 defines **Περίοδος Αναφοράς** — the reference period,
per undertaking, keyed to that undertaking's own last closed financial year. The per-product-code
average is defined elsewhere in the instrument.

*The conclusion survives and the citation does not.* The benchmark is still anchored to the trader's
own 2025, so a 2008–2020 sector median is still not it. What would have been imported into the fix
is the wrong article, by a restatement that repeated the wording it was correcting.

*Provable inside the tree, with no external source, which is the part worth keeping.*
`docs/REGULATORY.md` and `corpus/real/MANIFEST.yaml` both have παρ. 5 right; `PLAN.md` had it wrong.
**Two documents agreed, a third disagreed, and nothing compared them** — for four days, in one
repository. That is the argument for this file rather than a footnote to it.

*Site:* `PLAN.md` :: `defines the benchmark as the trader's own average, per product code, over 2025`
*Disposition:* branch `corpus/legal-claims-restated`
*Closed:* 2026-08-31 — restated in `PLAN.md` by `corpus/legal-claims-restated`, with the prior wording kept beside it per doctrine rule 4
*Now:* `PLAN.md` :: `benchmark to the trader's **own** 2025 rather than to a sector figure.`

**Half of `G7` cannot fail, and half of `C7` cannot either** · found 2026-08-31 · by oversight level 3, while arming it
`G7.closed-vocabulary-only` asks two questions and one of them is a dead branch. *Is every reason's
code one the vocabulary declares* is checked as `reason.code.value not in declared` — and
`reason.code` **is** a `RefusalCode`, so the condition can never be true. The type already closed
the vocabulary; the check re-asks a question the type had answered.

*What is not wrong.* `G7`'s second question is real and load-bearing: **every refusal carries a
detail**. Claim 1's evidence is *which* guardrail refused, and a code with no detail says a price
was refused without saying what about it was wrong. That half is now armed —
`17-a-refusal-arrives-without-its-detail` blanks the detail, moves no bound, certifies no price and
changes no code, and `G7` is the only check in the eval that falls.

*So the check is not removed and the figure is not touched.* `12 distinct codes over 365,591
reasons` is a real published number; what is dead is one `if`. Deleting it would lose the statement
that the vocabulary is closed, which is true and worth asserting somewhere — the question is whether
a check is the right somewhere when a type already guarantees it, and that is a judgment about where
a guarantee should live rather than a defect to patch.

*Why it is here rather than fixed in the branch that found it.* The branch's subject is arming
unarmed checks. Rewriting one of them while arming it would mean the mutation was written against a
check nobody had reviewed in its new shape — and `evals/README.md`'s rule 5 is that a boundary is
computed twice, not that a check is edited by whoever is proving it bites.

*And the same fact a second time, in `C7`.* Found by oversight level 2 reading this branch, and
recorded here rather than as its own entry because it is not a second finding: it is the same
question with a different type answering it. `C7.the-graded-days-are-not-the-days-the-curve-was-
fitted-on` asks whether the held-out segment is disjoint from the fitting segment, and `overlap`
is drawn from two complementary predicates over one business date — so that half cannot be
non-empty either. Its other half, *is neither segment empty*, is real and is a property of the
corpus. Two entries for one fact would be the mirror of what this register caught in its first
hour, when one entry was answering for two defects and had to be split.

*What this branch did change.* `C7` carried the tautology as its stated reason for being
un-armable. That reason is now the half that can actually go red, because the sufficient reason
was always the corpus one — leaving an assertion of a dead branch sitting in prose, in the branch
whose whole subject is that such assertions get filed rather than mentioned. The `if` itself is
untouched in both checks, for the reason above.

*Site:* `evals/guardrail/checks.py` :: `if reason.code.value not in declared:`
*Site:* `evals/censoring/checks.py` :: `overlap = [origin for m in worlds for origin in m.keys_in_both_segments]`
*Disposition:* none — a judgment about whether a check should re-assert what a type guarantees
*Status:* open

**The suite count is published where no gate can read it** · found 2026-08-31 · by oversight
level 2, after writing a wrong one
Every session entry in `PLAN.md` ends with `The suite is **N**`, and nothing recomputes it. `PROSE`
in `ops/figures.py` is the mechanism that would, and it excludes `PLAN.md` deliberately: the file
keeps superseded figures forever per doctrine rule 4 — 965, 965, 959, 943, 937, 928 are all in it
and all correct as written — so re-running a number there would go red on history.

*The argument is sound for the history and silent about the newest entry.* Only the last one is
present tense. It is the only figure in the file that is a claim about now, it is the one a reader
takes as current, and it is outside every gate in the repository.

*Found by writing one.* `The suite is **976**` went into `PLAN.md` as a projection — one test added,
one replaced, arithmetic — in the same change whose subject is that an assertion wearing a number is
set from a measurement of the thing that runs. It is **972**. Nothing caught it; an agent
reconsidering caught it, about ninety seconds later. That is not a mechanism and it does not survive
a tired session, which is the whole argument of `docs/reviews/phase-1.md` §2 and the reason this is
filed rather than shrugged at.

*What the fix is not.* Registering `PLAN.md` in `PROSE` as it stands would go red on six historical
figures immediately. What is needed is a rule for *which* occurrence is present tense — the last, or
one carrying a marker — and that is a judgment about the document, which is why it is a finding and
not a patch.

*A candidate, offered with its two checks already run, to be tested by whoever takes the branch
rather than adopted from here.* The four-kinds rule marks a published number `[M]` measured, `[D]`
declared, `[C]` cited, `[S]` scenario. If figures carried their kind, *present tense* would stop
being a judgment about position and become a property the text carries — a superseded figure is no
longer a measurement of anything, it is the record of one — and `PROSE` could register `PLAN.md`
and re-run exactly the marked ones. It is the same move as selecting on `where` rather than on a
name prefix, one file along.

**Check one fails as stated, and that is the important half.** `PLAN.md` contains eight marker
occurrences and every one of them is prose *about* the four-kinds rule, in the session entry that
introduced it. **No figure in the file carries a kind, and no suite line carries one.** The
repository has the vocabulary and applies it in `docs/SCENARIO.md`, where `**320 stores [M]**` and
`**[M]** python -m ops.roster --scale <name>` sit beside their commands. So the distinction is not
already here waiting to be read; it exists elsewhere and has never been applied to this file.

**Check two passes, and more cheaply than it was feared to.** Precisely *because* no figure here is
marked, adopting this rewrites none of the six historical lines — they are already unmarked, which
is the state the rule wants history to be in. Nothing doctrine rule 4 protects gets edited, and the
change is forward-only.

**What neither check found, and what the branch will actually have to answer.** The marker has to
*migrate*. If `figures` re-runs every marked figure, then the session after next must take the
marker off this entry's `972` or that number goes red the moment the suite grows — so every session
boundary carries a small edit to the previous session's line. Removing a marker does not change a
stated value, so it is not a rule 4 violation, but it is routine editing of superseded text, and it
is the kind of step that gets forgotten. A forgotten marker is a red on correct history, which is
the failure that teaches people to delete markers rather than to write them. **Any version of this
needs the migration to be enforced by the same gate, or it decays into exactly the noise it was
built to remove.**

*A second candidate, and it is the one that removes the migration rather than paying it.* The
marker has to migrate only because the present-tense figure lives in a file that cannot be
overwritten — every session must demote the last one precisely because `PLAN.md` keeps it forever.
Give the current count a home that **can** be overwritten and there is nothing to migrate: `figures`
covers that one place and re-runs it every time, and this file's numbers become history by
construction rather than by anybody remembering to demote them. `PLAN.md` then stays outside `PROSE`
legitimately rather than by judgment — not *we cannot tell which occurrence is present tense*, but
**nothing here is present tense, because present-tense figures are not written here.** One
enforceable sentence: an append-only file records what a number was; a current number lives where it
can be replaced.

**What it costs.** A home has to be chosen and created, which is a judgment about where a reader
would look — and the measurement says there is no candidate today: the count exists in `PLAN.md`
ten times and `TASKS.md` once, both append-only, and **nowhere in the tree is there an
always-current home for it.** No README line, no gated file.

**And the phrasing half is not free, which is the check that decides between the two candidates.**
The reading that *The suite is 828* inside a dated entry already reads as history does not survive
being measured. Of the ten occurrences, **exactly one sits directly under a dated header.** The
other nine sit under an intra-entry bold sub-heading — `**The denominator is in the type.**`, `**And
`C7` carried the same defect as `G7`, in the same commit.**` — which carries no date; the session's
date is twenty to sixty lines above. The suite figure is always the last line of an entry and
always the furthest from the only thing that marks it as past. Skimmed or quoted, it reads as
present tense, which is precisely how it is read.

*(The entry headers also use three different date separators, so any gate that tries to find the
newest entry by parsing them meets the wrap-and-pattern family from the other direction.)*

**So the nine would need rewording, which is the objection this candidate was raised to avoid.** It
is not a doctrine rule 4 violation — *the suite was 828 at this session* changes no stated value and
leaves the value, the reason and the delta recoverable — but it is editing text rule 4 protects, and
that is the thing to say out loud rather than discover in the branch.

**Which leaves the two candidates separated by one property, and it is not the one either of them
was argued on.** The marker's cost is **recurring**: one edit at every session boundary, forever,
and forgetting it turns correct history red. The new home's cost is **one-off**: nine lines reworded
once, plus a home that has to be chosen. A recurring cost that decays into deleted markers is worse
than a one-off cost that is simply work, so the second candidate is the stronger of the two — but
both are recorded with their prices, because whoever opens that branch should be choosing rather
than implementing.

*Site:* `ops/figures.py` :: `#: **Deliberately small, and the reason is doctrine rule 4.** `PLAN.md` and `TASKS.md` are the`
*Disposition:* `ops/the-newest-figure-is-present-tense` — small, and it belongs where the count is
published rather than in the branch that found it
*Status:* open

**A mutation may name a check that does not exist, and the cheap target cannot tell** · found
2026-08-31 · by oversight level 2, on `evals/unarmed-checks`
A mutation declares `targets:` — the checks it expects to refuse it. Nothing in `make gate-proof`
asks whether those names correspond to a check that exists. `engine.py` does ask, at
`unknown = [target for target in mutation.targets if target not in baseline]`, but only with the
eval loaded, which means only inside `make claim-N`. The ledger's own docstring gives as its reason
for existing that a mutation which has come unmoored is caught by the cheap target as well as by
the expensive one, and this is the one way of coming unmoored it does not catch.

*It is the sibling of `every-anchor-is-aimed-at-one-place`*, which asks exactly this question one
level down — does a mutation's anchor still occur in the source it names — and the implementation
is the same shape. What made it newly cheap is this branch: `declared_checks()` enumerates every
check id in the tree in milliseconds, so the comparison is now a set difference.

*This branch does not create the hole; it adds a quieter place for it to land.* Before, a renamed
check left its mutation failing at run time in `engine.py`. After, the same rename lands that check
in **unarmed** — printed, counted, and deliberately not refused. The mutation still fails when
`claim-N` runs, so nothing is unproven; what changes is that the cheap target now has a state that
looks like an honest backlog and can be reached by a typo.

*Measured today, so that tomorrow's non-zero is legible:* 37 distinct mutation targets, 67 declared
check ids, **0 naming nothing**. By
`python -c "from evals.gate_proof.ledger import load_mutations, declared_checks;
print(sorted({t for m in load_mutations() for t in m.targets} - {d.id for d in declared_checks()}))"`.

*Site:* `evals/gate_proof/ledger.py` :: `armed = sorted(i for i in by_id if i in targeted)`
*Disposition:* `evals/mutations-point-at-checks-that-exist` — a different assertion from this
branch's, so a different closed piece of work
*Status:* open

**`pricing/selection.py` serves no claim, and the review that said so assigned it nowhere** · found
2026-08-30 · by oversight level 3
`src/holdout/core/pricing/selection.py` is reached by no eval and targeted by no mutation. Only
`tests/core/test_pricing.py` and `tests/core/test_composition.py` touch it. It is on `CLAUDE.md`'s
declared decision path — *the model returns a scenario table, code picks the row by arithmetic* — so
deleting it is not the answer; **naming** it is. Either claim 1 brings it into its sweep, or it is
written down that scenario selection is proved by the suite and not by a claim.

*How it was lost, which is why it is here.* `docs/reviews/phase-1.md` closes with a nine-row table
assigning every section to a branch. §4 is not in it. The only reference to the module anywhere
outside its own source and tests is the review's own line — not in `TASKS.md`, not in `PLAN.md`, not
in `docs/DECISIONS.md`, no branch, no task, no deferral. It was found by its author, in his own
document, the day after writing it.

*Why it is the register's second entry rather than a branch tonight.* Naming a branch for it now
would repeat the error the assignment table already made once: assignment written quickly, at the
end of a long document, with no mechanism behind it. It is held here until somebody scopes it with
the module in front of them.

*And it is the entry that tests the half nothing else does.* The legal finding had two sides that
drifted apart, which a cross-check catches by construction. **This one never had a second side at
all** — recorded once, never picked up. A cross-check would find nothing to compare and report
nothing. It is caught only by *anchored against adrift*, which was specified for completeness rather
than for a case anybody had in hand, and then a case arrived.

*Site:* `docs/reviews/phase-1.md` :: `One module: **`src/holdout/core/pricing/selection.py`**`
*Disposition:* none — to be scoped by whoever picks it up, with the module in front of them
*Status:* open

---

## Closed

Nothing yet. An entry moves here with its `*Closed:*` line, its original `*Site:*` lines intact,
and a `*Now:*` for each — and it goes on being checked. What closed it has to keep being true.
