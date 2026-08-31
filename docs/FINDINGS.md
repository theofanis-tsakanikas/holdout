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
