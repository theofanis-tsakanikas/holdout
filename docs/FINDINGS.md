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
**is** the cap's benchmark: `benchmark_margin_on_price()` feeds `ProposedPrice.benchmark_markup_on_cost`
on all 232,373 decisions claim 1 drives.

*What does not move.* **Claim 1 does not reopen**, and the reason was written three weeks before
anybody needed it: the eval prints on every run that it does not prove the numbers in
`contracts/guardrails/` are the right ones, only that the machinery honours whatever envelope it is
handed. `contracts/guardrails/regulated_basket.yaml` keeps its benchmark symbolic and sourced, so
the contract does not implement the law with a median either. What does not survive unqualified is
the **scenario** claim — a corpus presented as real, citing a live Greek regulation, whose concrete
benchmark is a construct that regulation does not use.

*And the finding miscites its own article.* It says άρθρο 4 παρ. 5 *"defines the benchmark as the
trader's own average, per product code, over 2025"*. παρ. 5 defines **Περίοδος Αναφοράς** — the
reference period, per undertaking, keyed to that undertaking's own closed financial year. The
per-product-code average is defined elsewhere. This is provable inside the tree with no external
source: `docs/REGULATORY.md` and `corpus/real/MANIFEST.yaml` both have παρ. 5 right and `PLAN.md`
has it wrong. The conclusion survives; the citation behind it does not, and a restatement repeating
it would import the error into the fix.

*Corroboration, labelled as what it is:* the reviewing session opened a secondary source
reproducing the decision's full text on 2026-08-31 and reports both articles verbatim. Not the
gazette, not opened here, and nothing above depends on it.

*Site:* `PLAN.md` :: `defines the benchmark as the trader's own average, per product code, over 2025`
*Site:* `corpus/real/README.md` :: `That alignment is not a`
*Site:* `corpus/real/MANIFEST.yaml` :: `Eurostat's ratio is gross margin on goods for resale over turnover,`
*Site:* `evals/guardrail/build.py` :: `The published 2025 gross margin`
*Disposition:* branch `corpus/legal-claims-restated`
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

Nothing yet. An entry moves here with its `*Closed:*` line and its sites intact, so that what it
anchored to stays checkable after the fact.
