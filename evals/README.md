# `evals/` — one directory per claim

An eval is not a test.

The suite under `tests/` asks whether a module does what its author meant it to do. An eval
asks whether **a claim in `CLAUDE.md` is true**, on inputs its author did not choose, and it
publishes the numbers rather than a tick. The two fail in different ways and neither
substitutes for the other: a green suite told us nothing about the ladder producing a price
the guardrail set refused, because nothing in the suite was trying to break anything.

Claim 1's eval is the first one built, so its shape is the shape the rest inherit. This file
records that shape, and the reasoning behind each part of it, so that claims 2, 3 and 4 do
not each invent their own. **The procedure that builds one is `.claude/skills/claim/`**,
extracted from claims 1 and 2 once there were two samples to tell a rule from a variation;
this file stays the source of truth for the *shape*, and the skill does not restate it.

**Where the shape has three samples rather than one — 2026-08-29.** Claim 7 (`oversight/`)
follows it, including the `<claim>/README.md` claim 2 still owes, and it added one thing the
first two did not need: a check may be armed by a test rather than by a `gate-proof`
mutation, where planting the break would mean editing the *detector* instead of the system.
`tests/evals/test_ledger.py` had already done this for `gate-proof` itself and it was never
written down as part of the shape. It is now: **a check with no mutation names the reason it
cannot have one, and is broken deliberately somewhere.** Silence about it is how a check
that has stopped biting goes unnoticed.

---

## The shape

```
evals/
  report.py                 Check · Report · the printer · the JSON reading
  <claim>/
    README.md               what is attacked, where the independence is, what it does not prove
    build.py                the join: corpus rows -> inputs the system takes
    reference.py            a second implementation, written to disagree with the first
    checks.py               the assertions, each with a stable id
    __main__.py             `python -m evals.<claim>` -> numbers, and an exit code
  gate_proof/
    engine.py               the executor: the three rules
    ledger.py               the accountant: ownership, and nothing unowned
    mutations/claim-N/      one YAML per planted break
```

And in the `Makefile`:

```make
claim-N:
	$(RUN) python -m evals.<claim>
	$(RUN) python -m evals.gate_proof --claim N
```

`ci` discovers `claim-*` and `gate-proof` by grepping the Makefile rather than by listing
them, so a claim target that exists but is never run is impossible by construction.

**A claim target owns its mutations and is the only place they run.** `make gate-proof`
executes nothing; it audits that arrangement — every mutation owned by exactly one claim
target, no orphan, no duplicate, no claim target with nothing planted against it. That last
one is CLAUDE.md's checklist question made structural: *if it is a gate, is there a
`gate-proof` mutation that proves it bites?*

---

## Six rules, and why each is there

**1 · A check has a stable id.** `gate-proof` plants a break and demands that a *named*
check refuses it. Ids are the contract between an eval and its mutations; renaming one is a
change to two files, and a mutation whose target has moved reports `STALE` rather than
passing.

**2 · A check states a falsifiable question.** `question` is the sentence that would be
false if the check failed. If it cannot be written that way, it is measuring something
rather than asserting it, and it belongs in `numbers`.

**3 · Numbers are published whether or not anything failed.** `CLAUDE.md`: *numbers, not a
green tick*. `8/200 = 4.0%` says more than PASS ever will, and a figure that only appears on
failure is a figure nobody has looked at.

**4 · Coverage is itself a check.** An eval whose inputs cannot reach half the vocabulary has
proved half the claim. `G8.every-refusal-code-is-reached` goes red on an unreached code
rather than mentioning it in a footnote, because a footnote is where a gate that stopped
biting goes to be forgotten.

**5 · A second implementation, not a second call.** Where a check needs to know where a
boundary is, it recomputes it — in a different unit, in a different structure, and sharing
nothing with the code under test but the declared rule values. Two consumers calling the
same function prove nothing; that is claim 5's trap and it applies here too.

**A seventh, since 2026-08-31: a check is armed, or it says why it cannot be.** Rule 4 makes
coverage a check; this makes *proof of biting* one. `make gate-proof` sorts every declared check
into three states and prints the counts — **armed** by a mutation that names it, **declared
un-armable** by a `unarmed_because` on the check itself, or **unarmed**.

The third is reported and not refused, and that is deliberate. A gate nobody has armed yet is a
real state; refusing it would buy a sentence where a mutation belongs, which is the opposite of
what this rule is for. What *is* refused is a check that is both armed and declared un-armable,
because one of the two is then untrue and nobody would notice which.

`unarmed_because` is for **cannot**, never for *have not*, and the honest reasons are narrow: the
break would edit the **detector** rather than the system, the check asserts a property of the
**inputs** that no change to `src/holdout/` can move, or the check is **absent from the
configuration a mutation runs at** and computing it there would make it a different check.

*Why it exists.* `ledger.every-claim-target-owns-a-gate` asked the question at target level, and
one mutation satisfies it for a claim with twelve checks. `docs/reviews/phase-1.md` §1 measured the
gap: **21 of 57 checks owned no mutation and 8 of those named no reason** — including three of the
four numbers claim 2 publishes. The rule that a check with no mutation names its reason was written
on 2026-08-29 from claim 7 and never applied backwards; this is what applies it, and what stops the
next one being written from prose.

**6 · "What this does not prove" is printed on every run.** Not kept in a README where it
can quietly stop being true. The eval says out loud, each time, what it is silent about.

---

## The trap each claim's eval has to answer

`CLAUDE.md` names one for every claim, and they are all the same trap wearing different
clothes: **something checking its own work and calling the agreement evidence.** Claim 1's
is a planter reading the same contract as the detector. Claim 2's is a simulator generating
data from the process the estimator assumes. Claim 5's is two consumers calling one
function.

So every eval's README answers three questions in order, and the third is the one that
matters:

1. **What is attacked?** The claim, restated as something that could come out false.
2. **Where is the independence?** Named precisely — which inputs come from outside, which
   arithmetic is computed twice, what the two sides share and what they do not.
3. **What does this not prove?** Including the parts that are uncomfortable. A limit that is
   written down is a limit; a limit that is not is a claim.

---

## Running them

```
make claim-1          the eval and the mutations it owns   ~3 min
make claim-2          the eval and the mutations it owns   ~1 h 11 min cold
make claim-3          the eval and the mutations it owns   ~3 min 14 s
make claim-4          the eval and the mutations it owns   ~1 min
make claim-7          the eval and the mutations it owns   ~37 s
make eval-guardrail   claim 1's eval alone                 ~10 s
make eval-uplift      claim 2's eval alone                 ~32 min
make eval-assignment  claim 3's eval alone                 ~17 s
make eval-censoring   claim 4's eval alone                 ~6 s
make eval-oversight   claim 7's eval alone                 ~4 s
make gate-proof       the ownership audit, runs nothing    <1 s
```

Every figure above is a **cold measurement on a fourteen-core laptop**, not a projection —
`CLAUDE.md`: *a timeout, a K, a tolerance, a threshold or a budget is an assertion wearing a
number instead of a verb.* Claim 2's is dominated by generating six worlds and is much lower
once `.worlds/` is warm.

**That last clause was a projection until 2026-08-31, and the number that replaced it is from a
different machine.** Measured on **GitHub runners**, not the laptop the table above was timed on:
71 successful `claim-2` jobs, warm mean **49.8** against cold **68.2** — a difference of **18.4
minutes, 95% CI +13.5 to +23.2**. It is not comparable with the figures above and is not offered
as one.

And it is narrower than *what the cache saves*: **every cold run in that sample was a spurious
invalidation**, the key having moved for a change that could not alter a world, so 18.4 is what
such an invalidation **costs**. Where the world sources genuinely change, regeneration is necessary
work no cache can save.

Claim 3 has nothing to cache, because a chain is placement arithmetic
rather than a simulation.

`make check` deliberately does **not** run them: it is the fast local gate and the claims
take minutes. CI runs every claim target that exists.

Add `--json` to any eval for the machine reading `gate_proof` consumes.
