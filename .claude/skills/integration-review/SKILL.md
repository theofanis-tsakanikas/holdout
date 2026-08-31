---
name: integration-review
description: "Run oversight level 3 in this repository — read the whole tree against CLAUDE.md at a phase boundary, report conceptual drift, and build nothing. Carries the eight questions the phase-1 review asked, which of them produced a finding, the one question no reading of this tree can answer, and where the report and each of its findings have to end up. Use when a phase-boundary task opens (T016 for phase 2, T024 for phase 3), when asked for an integration review or a drift report, or when checking whether the last review's findings actually landed. In Greek: «integration review», «drift», «phase boundary»."
---

# integration-review — read the repository against `CLAUDE.md`, and build nothing

`CLAUDE.md`'s oversight table: level 1 is CI, level 2 is a fresh-context reviewer on every pull
request, **level 3 is a dedicated session at every phase boundary**, and level 4 is the author and
is never an agent. This skill is level 3.

It asks what CI cannot. CI proves that each piece still passes its own gate; level 3 asks whether
the gates still measure the thing they were built for, and whether the documents still describe the
repository that exists. `CLAUDE.md`: *it is scheduled, not remembered: at the end of every phase,
without exception.*

---

## This is extracted from one run, and that is the first thing to know about it

`.claude/skills/claim/` was extracted from **two** closed claims, and the reason is written into it:
one sample gives a template, two give **a rule and a variation**, and the variation is where the
judgment lives. `evals/README.md` says the same thing from the other side — with one sample the
shape *is* whatever that sample does.

**This skill has one sample.** The phase-1 integration review, `T008`, 2026-08-30, reported in
`docs/reviews/phase-1.md`, with its consequences recorded in `PLAN.md`, `TASKS.md`, and
`docs/DECISIONS.md`. Everything below is written from that record and nothing else. Where the record
does not support an instruction, this file says so instead of supplying one — the list is at the
end, and until `T016` produces a second sample it is the more useful half of this document.

So read it as *what one session did and what it cost*, not as a rule with a variation. The
divergences that would tell those apart have not happened yet.

---

## 0 · What the session is, before it starts

**A dedicated session, and it builds nothing.** `docs/reviews/phase-1.md`'s own header:
*oversight level 3 reads the whole repository against `CLAUDE.md` and reports conceptual drift. It
builds nothing. Each proposed fix becomes its own branch with its own review.* `TASKS.md`'s T008
carries `review: n/a — this task IS the review` and `out_of_scope: building any product code`.

**One declared exception, with its reason.** Two changes landed on the review's own branch rather
than in a later one: doctrine rule 7's restatement, and the rule that an unlock condition must name
an event rather than a session. `PLAN.md` gives the reason — *both because they are sentences in the
file that governs every other branch.* That is the exception's whole extent: sentences in
`CLAUDE.md`, not a fix to any module the review found something in.

**What the session may decide is enumerated in its task, not general.** T008's `closes` names
exactly two deferred items it is *expressly empowered to act on*. Everything else the review finds
becomes a branch, a task, a deferral or a finding — never a decision taken inside the review.

---

## 1 · Run the gates first, and let the report name what was run

`docs/reviews/phase-1.md` opens by declaring its own inputs:

> `make check` (919 green), `make eval-guardrail`, `make eval-assignment`, `make eval-censoring`,
> `make eval-oversight`, `make gate-proof`, `python -m ops.roster` at two scales, and the durations
> of the 31 successful `claim-2` jobs from the GitHub Actions API.

**This is not a formality, because §0's answer rests entirely on it.** *No claim's proof has
collapsed; both independence barriers hold; `ops.roster` reproduces exactly the table `CLAUDE.md`
restated on 2026-08-29* — that is a measurement, and it is what earns the report the right to say
the drift is *in the casing around the proof, not in its core*. A level-3 report that read the
documents and ran nothing could not have said either half.

The rule underneath is `CLAUDE.md`'s: *an assertion about what the system does — a sentence, or a
number in configuration — is written against the function that would make it true, named, and
against the measurement of what comes out when it runs.* A review is nothing but assertions about
what the system does.

**And it binds the fixing side too.** Claim 4 was published as 11/11 in five places while the eval
had never printed anything but 12/12; the branch that corrected them ran `make claim-4` first —
`PLAN.md`: *measured before correcting rather than taking the review's word* → **12/12 checks, 9/9
mutations biting**. A review's number is an input to be re-measured, not an authority.

*The record's own gap here: the header names four of the five `eval-*` targets and `eval-uplift` is
not among them. Whether claim 2's eval was run for this review, or its green read off the 31
successful CI jobs the same header cites, is not stated anywhere. Decide it explicitly rather than
inheriting the silence.*

---

## 2 · The eight questions, and which of them produced a finding

Six come from `CLAUDE.md`'s level-3 list. The phase-1 review added two more, and they produced its
two most consequential outputs.

| § | the question | phase 1 |
|---|---|---|
| 0 | *what stands* — the claims, the barriers, the roster table | **no finding, and that is the point.** Five claims green, both barriers holding, `at_decision` 12/12 |
| 1 | does any claim's proof rest on something that has become a tautology? | **finding.** No — but **21 of 57 checks owned no mutation and 8 named no reason**, three of them numbers claim 2 publishes. Plus: seven of the eight `at_design` codes reached by no eval |
| 2 | has any gate stopped biting — and for what reason? | **finding, three of them** — `make expiry` counting closed deferrals as open, an unmeasured cache assertion carried in three files, a budget whose unlock condition had been met unnoticed. **And it missed the largest one entirely: see §3 below** |
| 3 | does the code still say what `CLAUDE.md` says it says? | **finding, the largest section.** The repository map, claim 4's 11/11, two restatement chains that stopped at `CLAUDE.md`, a `verified_on` claim that did not count, a skills table listing four skills where one existed, a closed registry calling itself complete at L9 — **and T008's own task note naming the wrong gate** |
| 4 | is there code that serves no claim? | **finding.** `src/holdout/core/pricing/selection.py` — no eval reaches it, no mutation targets it. **And the review then lost its own finding**: see §6 |
| 5 | has a claim landed on a preview surface? | **no finding.** No `infra/`, no declared inventory, `make preview-audit` deliberately absent and the `Makefile` says so |
| 7 | *(added)* what has the deferral registry become? | **finding.** Nine open deferrals named this very session as their unlock condition |
| 8 | *(added)* is the recurring rule complete? | **finding, and the one held to be worth more than all the corrections together** — the rule was not incomplete, it was **unarmed** |

Three things to read off that table.

**§5 produced nothing and is not a wasted question.** The correct answer to a question can be *no*.
It will start biting in phase 3, when `infra/` exists and `make preview-audit` is written; a
question dropped because it came back clean once is a gate removed for passing.

**The two added questions are not in `CLAUDE.md`'s list, and one run is not grounds to put them
there.** Ask them anyway — they are in this file because they produced §7's rule about unlock
conditions and §8's `make figures`, and dropping them would drop the review's two largest outputs.
Whether they belong in the standing list is a judgment for the author, on more than one sample.

**§8 is a question about the method, not about the code**, and it is the one a session is least
likely to think of unprompted. Its phase-1 answer: ten instances of *a guard tested by its author*
in one phase, ten different forms, one invariant — *the assertion was checked against the artefact
it came from rather than against the thing that would falsify it* — and **all ten found by a human
or by a run, none by a command.** The output was not an eleventh widening of the sentence. It was
`make figures`.

---

## 3 · The one question no reading of this tree can answer

T008's `closes` requires this skill to ask it, in these words:

> **what does the `main` ruleset require, and does that list match the jobs `ci.yml` defines
> today?**

**Why it is mandatory.** The ruleset required `gate` and `secrets`. `T003` moved the claim targets
out of `gate` and into the `claims` matrix — correctly — and the ruleset went on pointing at `gate`.
From that commit until `ops/claims-are-required`, **a pull request with a red `claim-2` merged**, and
`CLAUDE.md`'s sentence *a session cannot merge something that breaks a claim, because the gate is
structural rather than advisory* was false at the level everything else leans on.

**No reading finds it, and the review proved that by not finding it.** `ci.yml` declares which jobs
*exist* and never which are *required*; `make check` cannot see it; no test touches it. §2 read
`ci.yml` line by line and measured 31 of its runs. It was found by asking the API, by the author, an
hour after the report had merged.

**And its fingerprint was already in the record.** `docs/DECISIONS.md` had carried, since
2026-08-27, a verification quoting *"2 of 2 required status checks are expected"*. The **2** was the
finding. Nobody read the number, because the sentence beside it said which two and they agreed —
which is §8's invariant, in the registry, a fortnight early.

**Ask the forge, and read the number rather than the sentence.** What closed it is one summary
context — `claims-complete`, `needs: [claims]`, `if: always()`, failing on anything that is not
`success`, because `skipped` is how a matrix job passes silently and a skipped required check
reports neutral rather than red. The ruleset names that one context and never the claim names; an
enumeration there would be a second hand-kept registry of which claims exist, in a place no session
reads.

**The standing limit, which cannot be closed from inside.** Nothing in this tree checks the ruleset.
Remove the required context tomorrow and `claims-complete` reports on into a void. `PLAN.md` calls
this *the first rule in this repository that is deliberately a question rather than a gate, because
the thing it guards is outside the repository.*

*And it is the only such question the record contains.* There is no general rule anywhere for
recognising the next fact that lives in the forge rather than in the tree. Treat this question as
one known instance of a class nobody has enumerated.

---

## 4 · How a finding is checked before it is written down

The most useful part of the record is not the review's findings. It is the three places the review
was **wrong in its own report**, because a level-3 session has no gate behind it and these are the
shapes the mistake takes.

**A conclusion reached by citing the counterexample.** §2b concluded that the world cache *saves
nothing measurable*, and reached it by naming a cold run that finished in 44.8 minutes — which, of
the eleven cold runs in the sample, was **the only one below the warm mean**. Re-pulled at 71 jobs
and split by whether the job logged a cache hit: warm mean **49.8**, cold **68.2**, a difference of
**+18.4 minutes, 95% CI +13.5 to +23.2**. `PLAN.md`: *the section was right that `ci.yml`'s
assertion had no measurement behind it, and wrong in the conclusion it drew instead — which are
different failures.* Separate those two. *This assertion has no measurement behind it* is a finding
and needs no substitute; *and therefore the opposite is true* is a second assertion that needs its
own.

**A question asked in one direction.** §3a asked *is everything real listed* and never *is
everything listed real*. It reported the map's omissions and none of the three names sitting in the
same present-tense block — `pipelines/`, `infra/`, `experiments/` — that resolve to no directory at
all. A map naming something that does not exist sends its reader looking for it, which is worse than
an omission rather than harmless. **Every coverage question in a review has two directions.**

**A section that read the argument instead of the artefact.** §3d found that T008's own task note
told the next session a rename would turn `G10` red. `refuse_when_no_legal_price_sells` is never a
`Bound.rule_id` — `envelope.py` attributes six and it is not among them, and it appears zero times
in `evals/guardrail/reference.py`. What goes red is `O2`. The note had been written against `G10`'s
*argument* — *the six strings are written down a second time, so a rename separates them* — rather
than against the six strings. **It was found by reading the six `rule_id=` lines and by nothing
else.**

So, per finding: **name the artefact that would falsify it, and open that one.** Not the artefact
the claim came from. And where the finding is a rate, a spread or a saving, it is a sample — say
what n is, and say what the sample cannot reach. On `evals/world-cache-measured` the measurement's
own limit, *the sample lies inside one world-source epoch*, was stated in review and did not reach
the branch until oversight level 2 grepped for the word and found it absent.

---

## 5 · Where the report lives, and in what language

**Committed, at `docs/reviews/phase-N.md`.** The phase-1 report says it of itself:

> This report existed only in a terminal until it was written here. That is the same defect it
> catalogues nine times over: an assertion with no place anybody but its author reads. Its place is
> the repository.

**In English.** `CLAUDE.md`'s first line is that all repository content is English and only the
conversation with the author is Greek. The phase-1 report landed on `main` carrying **12,803 Greek
characters**, in a public repository, and took a whole extra branch — `docs/review-in-english` — to
translate with nothing in its content moved. `make language` is what stops it recurring, and it is
in `make check` now, so a review written in the conversation's language will go red before it can
be pushed. Write it in English the first time.

**The closing table records what was proposed and is never updated afterwards.** Its own note, added
2026-08-31: rewriting the rows to match what has since landed *would overwrite history — which
doctrine rule 4 refuses, and which would destroy the thing `#9`'s author needs: what the method
produced before anyone knew which rows survived.* Present-tense status belongs in `TASKS.md` and
`docs/FINDINGS.md`, which can be overwritten.

---

## 6 · Every section ends somewhere, before the session does

**`docs/reviews/phase-1.md` §4 was lost inside a day.** It was recorded in a document whose closing
table assigns every other section to a branch, and assigned to none. `docs/FINDINGS.md` and
`make findings` exist because of it and because of an older twin — the legal half of oversight level
2's third blocking finding against claim 1, recorded 2026-08-27, closed never, deferred never,
absent four days later. Every mechanism in the repository was aimed at a claim, a gate or a
deferral; an open review finding is none of the three.

Neither of those mechanisms existed when the phase-1 review ran. They exist now, so:

**Each section of the report ends in exactly one of** — a branch, a task id in `TASKS.md`, a
deferral in `docs/DECISIONS.md` whose unlock condition names an **event**, or an entry in
`docs/FINDINGS.md`. A finding filed there anchors to a line that occurs **exactly once**; a finding
with no site is refused, and one with no disposition is refused. `none — <reason>` is a disposition
and reports as **adrift** rather than red, because a finding nobody has scoped yet is a real state.

**And `concurred` is not `closed`.** This one is load-bearing for a review, because agreement is the
cheapest way for a finding to disappear. On 2026-08-31 the reviewing session removed §4 from the
author's list on the grounds that the two sessions concurred, and `docs/FINDINGS.md` records the
objection: *this is the exact mechanism by which the legal finding was lost — not a decision to drop
it, but two parties who held it agreeing it was handled and nobody holding them to that.* Two agents
agreeing is two representations agreeing. `concurred` prints in its own count and is **counted as
open**.

---

## 7 · The closing table is a proposal, and it will be wrong in both directions

The phase-1 review proposed **nine** branches, ordered, with `ops/every-number-carries-its-kind`
first *because the rest are corrections of numbers and this is the thing that stops them recurring*.
Measured against `git log main` on 2026-08-31, after eight of them had landed:

- **Eight rows landed in six commits.** Rows 5, 6 and 8 became one branch,
  `docs/the-documents-agree-with-the-code`. `PLAN.md`: *work that can never be parallelised is one
  piece written down as three because the review found it in three sections* — all three rewrote the
  same paragraphs of the same files.
- **One row was not opened for a day.** `evals/world-cache-measured` was proposed and never became a
  branch, while two sessions filed measurements into it by name and `docs/DECISIONS.md` carried an
  unlock condition pointing at a place that did not exist. `make expiry` could not see it: **it
  checks that a condition is present, never that it is reachable.** Found by a session that measured
  the nine-branch plan against `git log` instead of believing either party.
- **Four more commits landed in the same window that the table does not name** —
  `ops/claims-are-required` (§2d, named in its own section, added to the report after it merged),
  `docs/review-in-english`, `ops/findings-register`, and `corpus/legal-claims-restated`.

So propose the branches — the ordering argument is real and the first row earned its place. Do not
treat the table as a plan. What has to survive is that **every section has a disposition**, which is
`TASKS.md`'s registry and `docs/FINDINGS.md`, and not that every row becomes a branch.

---

## 8 · Read the deferral registry as a population, not as a list

§7's finding: **nine open deferrals named the phase-1 integration session as their unlock
condition** — five as the condition and four as a fallback — so *the session whose job was to read
arrived owing eleven decisions*. None of them was individually wrong. Together they had made "the
phase-1 integration session" a synonym for "later". The rule now in `CLAUDE.md`:

> An unlock condition that names a session rather than an event is not a condition; it is a date
> without a calendar.

**And the sweep is the part that was missed.** That rule was written on 2026-08-30 and the registry
was not read against it; `ops/expiry-knows-what-closed` did that the next day and called it the
thirteenth form of the recurring defect — *correct, published, and simply never run against what
already existed.* A new rule is not applied to what already exists unless somebody runs it there,
and a level-3 session is where that happens.

So report the registry as counts, not anecdotes: how many entries, how many carry a date, how many
carry a condition only, how many name a session rather than an event, and how many name **this**
session. `make expiry` prints most of it. What it cannot tell you — because telling a session from
an event means reading English, and because a condition can point at something that does not
exist — is what the reading is for.

---

## What the record does not support, and what this skill therefore does not say

Named rather than filled in, because a hole you can point at is worth more than a plausible
instruction.

- **How long a level-3 session takes, or what it costs.** Every claim task's landing note records
  what it cost; T008's does not carry a duration. So this file sets no budget — and a budget is an
  assertion wearing a number instead of a verb, which `CLAUDE.md` says is set from a measurement of
  the thing that will run. There is no measurement. `T016` can take one.
- **In what order the questions were asked.** The report declares *what was run to produce* it and
  is numbered §0–§8, but a report's section order is not evidence of its working order. What the
  record supports is the requirement that the report **name its inputs**, not a sequence.
- **Whether `eval-uplift` was run.** See §1.
- **How to find the next fact that lives outside the tree.** One instance is known and mandated;
  there is no rule over it. See §3.
- **Whether the eight questions are the right eight.** One run: §5 produced nothing, and the two
  questions outside `CLAUDE.md`'s list produced the largest outputs. That is not enough to change
  the list either way, and changing `CLAUDE.md` is not this session's to do on its own.
- **What happens at the phase-4 boundary.** `CLAUDE.md` says *at every phase boundary, without
  exception*; `TASKS.md` has `T016` and `T024` and no integration task after phase 4, which `PLAN.md`
  is consistent with because it phrases each one as *before the next phase opens* and phase 4 closes
  the project. Two documents, each defensible, with no reconciliation written down. Noted here
  because it was found while writing this file, which is the class of thing level 3 exists to find.
- **Greek invocation phrases in the description above.** `ops/language.py` admits exactly one Greek
  skill trigger, written for `skills/claim/`. Adding more is a change to that closed list with its
  own justification, and which words the author would actually type for this skill is not in the
  record.

And, as `tests/skills/test_skills.py` states in its own docstring: nothing checks **whether a skill
is right** or **whether it is followed**. That test checks wiring. What stands behind this procedure
is the report it was extracted from and the branches that closed it — and a second sample, when
`T016` runs.
