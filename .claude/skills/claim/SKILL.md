---
name: claim
description: "Build one of the seven claims end to end in this repository — the eval that attacks it from a source its author did not choose, the gate-proof mutations that prove each named gate bites, the `make claim-N` target that owns them, and the statement of where the independence is and what is not proved. Use when opening a claim task (T004 claim 3, T005 claim 4, T006 claim 7, T012 claim 5, T026 claim 6), when adding a check or a mutation to a claim that already exists, or when reviewing whether a claim target proves anything. In Greek: «claim», «eval», «φτιάξε το claim-N», «mutation», «gate-proof»."
---

# claim — build a claim's eval, its `gate-proof`, and its `make claim-N`

An eval is not a test. `tests/` asks whether a module does what its author meant. **An eval asks
whether a claim in `CLAUDE.md` is true, on inputs its author did not choose**, and it publishes
numbers rather than a tick.

This skill is the procedure. It is **not** a second copy of the shape:

| the shape lives in | and says |
|---|---|
| `evals/README.md` | the directory layout, and the six rules with the argument for each |
| `evals/report.py` | `Check` · `Report` · the printer · the JSON reading `gate-proof` parses |
| `evals/gate_proof/README.md` | the three rules, the verdicts, and how to add a mutation |

**Read those three before doing anything here.** Restating them in this file would create a second
source of truth about the shape, which is the thing the whole contract layer exists to argue
against — and the copy that goes stale is always the one in the procedure.

---

## Extracted from two, and the second one is why this exists

Claim 1 (`evals/guardrail/`) and claim 2 (`evals/uplift/`) are both closed. One sample gives a
template; two give **a rule and a variation**, and the variation is where the judgment is. Every
divergence below was a decision somebody had to make, and the right-hand column is what actually
governs it.

| | claim 1 · guardrail | claim 2 · uplift | what governs |
|---|---|---|---|
| the independent source | **outside the repository** — 32,480 price quotes the ONS collected by hand in shops | **inside it**, behind an enforced barrier: `corpus/world/` imports nothing from `holdout` | outside is stronger. Where nothing outside exists, a *structural* barrier plus a lottery is the next rung — never "we wrote a second one carefully" |
| what carries the claim | `G2`, one question asked over real prices | `U1`, a **rate over 200 draws** tested as a one-sided binomial | a rate is not a number; it is a sample, and it gets a test at a declared level |
| the second implementation | `reference.py`, exact `Decimal` euros against integer cents | `reference.py`, a per-event ledger walked forward against a grouped `GROUP BY` | it must differ **everywhere it is allowed to**. Slow is the point — a fast second implementation is one that made the same decisions as the first |
| cost of one run | about ten seconds | minutes, and `make claim-2` is the most expensive target in the repository | see *the mutation configuration* below |
| what a mutation runs | the eval itself, `evals.guardrail` | `evals.uplift.machinery` — **the same code and the same check ids** at a small declared configuration | one implementation. Two would be two things to keep in step, and only one of them would ever be run by a gate |
| caching | nothing | the worlds, keyed on **a digest of every file they were produced by** | never a hand-kept list of paths. A mutation that changes what is cached must miss the cache, and a digest is the only thing that knows that without being told |
| the three-question README | `evals/guardrail/README.md` | **absent** — the argument is in module docstrings and in `notes` | a divergence, not a choice. See *the finding this extraction produced* |

---

## The procedure

### 0 · Read the claim's row in `CLAUDE.md`, and its trap

Every claim in the table carries one, and **they are all the same trap wearing different
clothes: something checking its own work and calling the agreement evidence.** A planter reading
the same contract as the detector. A simulator generating data from the process the estimator
assumes. Two consumers calling one function. An LLM judge in the same family.

Write the trap out in your own words before writing code. If you cannot say what agreeing with
itself would look like here, you cannot yet tell whether the eval you are about to write does it.

### 1 · Name the independent source, before any code

The first question is not "what do I check" but **"who chose the inputs"**. Rank the options and
take the highest one available:

1. **Data from outside the repository**, published by somebody who has never read `contracts/` —
   digest-checked and committed, because it cannot be regenerated (`corpus/real/`);
2. **A generator behind a barrier that is enforced rather than promised**, plus a randomisation
   the eval does not control — never committed, because it *can* be regenerated
   (`corpus/world/`, `tests/boundary/test_corpus_imports_nothing.py`, and the lottery);
3. a second implementation inside this repository, sharing only the contract values;
4. two callers of one function — **this is nothing**, and it is what the trap looks like from
   the inside.

Whatever you land on, the eval's claim about independence is only as strong as the mechanism
that *keeps* it. `corpus/real/` cannot see the system because a boundary test fails the build;
that sentence is worth something. "We were careful" is not.

### 2 · Write the three-question README first, not last

`evals/<claim>/README.md`, answering in order:

1. **What is attacked?** The claim restated as something that could come out false.
2. **Where is the independence?** Named precisely — which inputs come from outside, which
   arithmetic is computed twice, **what the two sides share and what they do not**.
3. **What does this not prove?** Including the uncomfortable parts. A limit that is written down
   is a limit; a limit that is not is a claim.

Writing it first is what stops the eval being shaped to whatever turned out to be easy to check.
The third answer also has to be *printed on every run* — `Report.notes`, rule 6 — because a
limit that lives only in a README quietly stops being true.

### 3 · `build.py` — the join, and the only module that imports both sides

The corpus knows nothing about the system and the system knows nothing about the corpus. The
join lives here, where it can be read as one thing.

Sort every input into three columns and **keep the columns sharp**, because doctrine rule 3 is
the easiest rule in this repository to break by accident:

| | |
|---|---|
| **observed** | it came from the source. Say which one |
| **derived** | with the arithmetic written out, and which way it errs |
| **swept** | walked over a declared, deterministic grid — never drawn at random, so a red run reproduces exactly |

A value that is none of the three is invented, and a default is a lie with a plausible shape.
Put the grid's awkward member in on purpose: claim 1's grid contains `4` dispatched changes for
one reason — two envelopes carry a budget of 4, and only an input landing *on* the bound can tell
`>=` from `>`. Without it the off-by-one mutation survives.

### 4 · `reference.py` — a second implementation, written to disagree

Driving the system from outside answers *does it refuse*. It does not answer *at the right
place*, and if the only thing that knows where the boundary is is the code under test, the eval
is asking a function to mark its own paper.

So write the boundary twice, and **differ everywhere you are allowed to** — put the table in the
docstring, as both existing ones do:

| | the core | the reference |
|---|---|---|
| unit | integer cents | exact `Decimal` euros |
| structure | one pass appending attributed bounds | one predicate per rule, evaluated independently |
| lookup | a sorted index, bisected | walked forward from the first step, every time |

They may share the **contract values** and nothing else. Not a helper, not a rounding primitive,
not an index. `evals/guardrail/rounding.py` exists because the eval's own floor once ended in
`Money.as_lower_bound` under a docstring claiming independence, and `tests/evals/` now scans
every module in that package for a reach back into the core's rounding.

### 5 · `checks.py` — ids, questions, figures, counterexamples

Rules 1–4 of `evals/README.md`, applied. Two that get skipped and should not be:

- **Coverage is itself a check.** An eval whose inputs cannot reach half the vocabulary has
  proved half the claim. `G8` goes red on an unreached refusal code rather than mentioning it in
  a footnote, because a footnote is where a gate that stopped biting goes to be forgotten.
- **A check that reaches a boundary *through* something else only sees a defect where that
  something else happens to land.** `G2` and `G3` both reach a bound through a price, so both see
  a misplaced bound only where a corpus price sits in the one-cent gap it opens: measured, `G2`
  reported **3** violations where `G10` — comparing the bounds themselves — reported **232,373**.
  If a check is indirect, add the direct one beside it.

### 6 · `__main__.py`, and the Makefile target

`__main__.py` delegates to `evals.report.main`, which gives `--json` for free.

```make
claim-N:
	$(RUN) python -m evals.<claim>
	$(RUN) python -m evals.gate_proof --claim N
```

Add the fast half too — `eval-<claim>`, the eval without the mutations — because that is what a
session actually runs while building. **Do not list the target anywhere else.** `ci.yml`'s
`discover` job greps the Makefile, so a claim target that exists but is never run is impossible
by construction, and adding it to a workflow would take that property away.

### 7 · The mutation configuration, if the eval is expensive

`gate-proof` runs the eval **once per mutation**. Claim 1 pays ten seconds a time. Claim 2 could
not pay minutes a time, and the answer was neither a second eval nor a thinner check:

- the same module, the same check ids, at a **small configuration declared in a contract**
  (`contracts/design/aa_harness.yaml`), reached through `evals/uplift/machinery.py`;
- **the scale does not shrink.** Several checks need a readout that produces a number, and at any
  scale cheap enough to skip the world cache the balance check refuses every draw — which would
  leave three gates never shown to bite;
- **a check that would mean something different at the two sizes is absent at the small one**,
  not computed on a handful of draws and printed as though it meant the same thing. `U1`–`U3` are
  rates and a rate over three draws is not a rate. `U4` survived because it was restated as a
  binomial: a test at a declared level is one instrument at any size, a fixed tolerance is two.

If you cache anything to afford this, key the cache on a **digest of every source file the
artefact was produced by** — never a maintained list. The failure it prevents is precise: a
mutation that changes what is cached would be handed a cache built before it, report `SURVIVED`,
and the thing it broke would never have run. That is a gate silently disarmed.

### 8 · The mutations — one YAML each, owned by exactly one claim

The full format and the three rules are in `evals/gate_proof/README.md`. What that file cannot
tell you is how to *choose* them:

- **write the break in domain terms** — "the margin floor rounds the wrong way", "the neighbour
  exclusion keeps both members of a pair" — never "make `G2` fail". The check it must trip is
  declared in the file, in advance, and if it survives that is **reported**;
- **shape it after a bug that actually happened** where one is available. The margin-floor
  mutation is the ladder/guardrail rounding split, moved one module along;
- **a mutation that crashes the eval is not a mutation.** If the break you want raises a
  `TypeError` three lines later, write the one that produces a wrong *answer* instead — that is
  the bug a real change would have introduced;
- **when a mutation survives, fix the eval — never widen the assertion.** Two survived in claim
  1's history and both are kept in the record: one named a check that could not catch it, one was
  caught by a *different* check and so proved nothing about the line it was aimed at. **A gate
  can only be shown to bite where it is the gate that refuses.** A mutation set that never
  surprises its author was written after looking at the answers;
- **at least one mutation must be the reason a check exists.** `G10`'s first two are caught
  elsewhere as well; the third — a bound at exactly the right amount wearing another rule's id —
  moves no arithmetic, wrongly certifies no price, and is refused by `G10` and nothing else. That
  is what earns the check.

### 9 · Run it, and write down what came out

Run `make claim-N` — `make check` deliberately does not, and CI runs every claim target that
exists. Then publish the figures, including the ones that are not flattering, and **write down
where the measurement disagreed with what you expected**. Three of claim 2's six worlds had their
declared behaviour restated by being run; that is the eval working, and it is the most valuable
output of the whole exercise.

---

## Every number you set is a claim

`CLAUDE.md`: *an assertion about what the system does — a sentence, or a number in configuration
— is written against the function that would make it true, named, and against the measurement of
what comes out when it runs.* A claim task sets several such numbers, and each one is an
assertion wearing a number instead of a verb:

| the number | the assertion | how it is set |
|---|---|---|
| a `timeout-minutes` in `ci.yml` | *this target finishes inside this budget* | from a **cold** measurement on the hardware that will meet it, plus the headroom the ~40% spread between runners already demands here. Not projected from the author's laptop — `claims` was first set at 45 that way and the runner cancelled the harness |
| K, and the counts in a harness contract | *this many draws make the rate a measurement* | a budget, and it says so — except where K **is** the claim, which is not a budget and is not tuned |
| a ceiling on a published rate | *above this, the claim is false* | declared before the run, from the contract where one exists. A threshold chosen after seeing the figure is the fishing this repository exists to make impossible |
| a tolerance in a comparison | *this much disagreement is rounding* | almost always **zero**. `G3`'s one cent was an exemption for exactly one bug — the too-strict bound, which is the shape this project's history says its bugs appear in |

---

## The finding this extraction produced

`evals/README.md`'s shape block declares `<claim>/README.md` — *what is attacked, where the
independence is, what it does not prove*. **Claim 1 has one. Claim 2 does not.** Its three
answers exist and are good ones — they are in `evals/uplift/__init__.py`, in the module
docstrings, and the third is printed on every run through `Report.notes`, which is the half rule
6 makes enforceable. What is missing is the single place a reader who has not opened the package
can find the independence argument.

It was invisible while there was one claim, because with one sample the shape *is* whatever that
sample does. It became visible the moment a second was laid beside it, which is the argument for
extracting a procedure from two rather than one — and it is the same shape as the finding T003
stopped on: two things each correct on their own, with nothing computing the product.

The standard is the README, and step 2 above says so. `docs/DECISIONS.md` carries claim 2's
missing one as a deferral with its unlock condition, rather than this skill declaring a shape
half its own sample violates.

---

## What a claim target may never do

- **pass because the eval crashed.** Rule 2 of `gate-proof`: a non-zero exit is not proof;
- **own zero mutations.** `make gate-proof` is the accountant and refuses a `claim-N` target with
  nothing planted against it — `CLAUDE.md`'s checklist question made structural;
- **run another claim's mutations.** A mutation belongs to exactly one claim, and `claim-N` is
  where it runs. There is deliberately no "run everything" mode;
- **be listed in `ci.yml`.** Discovery is the property; listing destroys it;
- **report a green tick.** Numbers, pass or fail, every time;
- **discard a draw, a row or a case it does not like.** Every individual number can stay true
  while the set of them becomes fishing;
- **land with a figure in prose that the eval no longer prints.** That is the same defect one
  layer up, in the layer that is supposed to *be* the evidence — and it has happened here twice.

---

## When the claim closes

Three files, and none of them overwrites (doctrine rule 4):

- **`TASKS.md`** — the task's `status` to `closed`, and the landing note: what it settled, what it
  cost, what the review sent back, and the figures the target closes on;
- **`PLAN.md`** — the prose record of what the piece settled, in the phase's *Progress* section;
- **`docs/DECISIONS.md`** — a deferral for every limit found and not fixed, each with an unlock
  condition **or a date**. `make expiry` refuses one with neither. Deferring is not forgetting.

Then oversight level 2: a fresh-context reviewer reads the branch against `CLAUDE.md`, and on every
branch so far it has found something a green suite could not. Expect the findings to be in the
**prose**: on the claim-1 branch all three blocking items were prose asserting more than the code
supported, and on T000 — the branch whose whole subject was the measuring instrument — both were,
one of them a claim about a mutation's effect that **had never been run**. Assume your own write-up
is where the defect is, not your arithmetic.

---

## What this skill does not cover

- **Which claim to build.** That is `TASKS.md`, and the dependency order in it is real.
- **The estate.** Claims 5 and 6 need an engine and an agent; the procedure above is about the
  local half, which for those two is where the proof still has to be provable.
- **Whether the claim is worth making.** That is oversight level 4, and it is never an agent's.
- **A mutation set that is complete.** These are the breaks we thought of. A curated set is not
  mutation testing, and a gate can be perfect against all of them and still have a hole nobody
  imagined. Say so in the eval's own output.
