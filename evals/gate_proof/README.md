# `gate-proof` — break every gate on purpose, and know who owns each break

A gate that has never refused anything has not been tested. This directory refuses to take
that on trust: it plants a deliberate break in the system — `src/holdout/`, and since claim 7
`contracts/` as well — runs a claim's eval against it, and demands that **the check named in
advance** goes red for the stated reason.

Two halves, and they are different jobs.

```
make claim-N     the executor · runs the eval, then plants the mutations claim N owns
make gate-proof  the ledger   · runs nothing, audits that every mutation is owned once
```

**A mutation belongs to exactly one claim.** It is planted to prove that one claim's gate
bites, and `make claim-N` is where that claim is proved end to end — so that is where it
runs, and nowhere else. `engine.run` requires a claim number; there is deliberately no "run
everything" mode, which is what stops the duplication being reintroduced by dropping an
argument.

`make gate-proof` is then free to be an accountant instead of a second executor:

* **no orphan** — a mutation no claim target would ever run. Nothing caught that before;
  a YAML dropped into `mutations/claim-9/` with no `claim-9` target was planted and forgotten;
* **no duplicate** — a mutation two targets both run. This one is not hypothetical either:
  `claim-1` and `gate-proof` both ran claim 1's thirteen mutations, and the CI job took
  **13m06s** to prove the same thing twice;
* **no unproven gate** — a `claim-N` target with no mutations at all, which is CLAUDE.md's
  checklist question made structural.

It also asks the static half of rule 3 — does every anchor still occur exactly once in the
source it names — because that costs milliseconds and does not need the eval to run.

The ledger is itself a gate, and it is the one gate that cannot have a `gate-proof` mutation,
because it *is* `gate-proof`. `tests/evals/test_ledger.py` breaks every one of its checks on
a deliberately broken arrangement instead.

Nothing here touches the working tree. Each run copies the source it needs into a temporary
directory and mutates the copy, so an interrupted run cannot leave a planted mutation behind
— and a mutation whose `file:` resolves outside that copy raises rather than writing.

---

## The three rules

These three govern the **executor**. The ledger runs nothing, so none of them applies to it.

**1 · Green first.** Before a mutation is planted, the check it claims to trip must already
be passing. A mutation whose target was red anyway proves nothing — the failure it produces
was there before it arrived. That verdict is `NOT-ARMED`, and it fails the run rather than
being skipped.

**2 · A non-zero exit is not proof.** The eval runs as a subprocess and its **JSON** reading
is parsed. The mutation succeeds only when the *named* check reports `passed: false`.
Anything else that goes red — an import error, a crash, some other check falling over — is
`CRASHED`, and `CRASHED` fails. Without this rule the easiest way to pass `gate-proof` would
be to write a mutation that makes the eval unimportable, and it would look identical to a
gate biting. This is not hypothetical: an early draft of
`the-daily-change-budget-is-off-by-one` disabled a `None` check and produced a `TypeError`
three lines later. Under rule 2 that was `CRASHED`, and the mutation had to be rewritten into
one that changes behaviour instead of breaking the interpreter.

**3 · A mutation whose target moved is `STALE`, never passed.** The anchor text must appear
in the source **exactly once** — zero means the code it was written against has been edited,
more than one means it is aimed at something ambiguous. The rule applies to the *check* a
mutation names as well: a target the eval no longer publishes is `STALE`. This is what stops
`gate-proof` decaying into a suite of mutations that no longer touch anything and pass
because the thing they were meant to break is gone.

The verdicts are `bit` · `SURVIVED` · `STALE` · `CRASHED` · `NOT-ARMED`. Only `bit` passes.

---

## Where the independence is, and where it is not

The trap `CLAUDE.md` names for claim 1, restated for the planter: *if the thing that decides
what to break reads the same source of truth as the thing that detects it, it is one function
agreeing with itself.*

Three separations, and only the third does real work:

* **the planter edits the system; the detector reads `corpus/real/` and `ops/`.** For claim 1
  that means the planter edits `src/holdout/` and nothing else. **Restated 2026-08-29 with
  claim 7**, whose most valuable mutation edits `contracts/policies/ladder_policy@v1.yaml`:
  a decision that becomes idempotent per customer changes no Python at all, and a planter
  confined to `src/` could not have written it. What matters is not which directory the
  planter may touch but which one it may not — the detector is never a mutation target;
* **a mutation is written as a behaviour change in domain terms** — "the margin floor rounds
  the wrong way", "a frozen category is only a warning" — and never as "make `G2` fail". The
  check it must trip is declared in the file, in advance;
* **the planter cannot tune the inputs.** The corpus is committed and digest-checked by
  `tests/corpus/test_manifest.py`, so the only way to make a mutation catchable is to make
  the gate actually catch it. This is the separation that carries the argument; the first two
  are hygiene.

### What happens when a mutation survives

It is reported, and the report is acted on by fixing the *eval*, never by widening an
assertion until the mutation fits. Two survivals in this branch's own history, both kept
here because they are the best evidence the harness works:

* **`absolute-floor-is-not-applied`** originally also named
  `G1.only-a-certificate-reaches-a-shelf`, reasoning that `certified()` requires at least one
  lower bound and this is the only bound appended unconditionally. It survived, and it was
  right to: on the markdown path the max-depth bound is *also* a lower bound, so removing the
  absolute floor never empties `bounds.lower`. The target was narrowed to the check that
  genuinely catches it. Then it survived again on `G2`, for a better reason — with a 0% margin
  floor the derived cost was always the higher of the two lower bounds, so the absolute floor
  never decided anything and removing it changed no answer. **A gate can only be shown to
  bite where it is the gate that refuses.** The fix was to the eval's sweep, which now
  contains an envelope where the absolute floor is the binding one.

* **`an-erased-answer-is-as-good-as-a-checked-one`** survived because the certificate has
  defence in depth: blanking `_bounds` is refused by a *different* check, since the recorded
  `_checks` no longer agree with the bounds they were derived from. Good news about the
  design, and useless as proof that the `bounds.lower` line does anything. The eval gained a
  tamper that erases the bounds **and** the checks together — internally consistent, and
  refused by exactly one line.

Both of those are the harness doing its job. A curated mutation set that never surprises its
author is a curated mutation set that was written after looking at the answers.

---

## What this does not prove

**That every gate bites on every mutation.** These are the breaks we thought of — the same
honest limit the six adversarial worlds carry for claim 2 — and thirty curated mutations
are not mutation testing. A gate can be perfect against all of them and still have a hole
nobody imagined.

What the set *does* prove is that each named gate is load-bearing: remove it and something
goes red, by name, for the stated reason. That is the difference between a guardrail and a
comment.

---

## Adding a mutation

One YAML in `mutations/claim-N/`:

```yaml
id:          a-short-kebab-name
claim:       1
eval_module: evals.guardrail
targets:     [G2.certified-price-inside-exact-bounds]

breaks: >-
  what changes about the system's behaviour, in domain terms. Not "makes G2 fail".

file:   src/holdout/core/guardrails/envelope.py
anchor: |
  the exact source text, copied out. It must occur exactly once.
replacement: |
  what it becomes.
```

YAML strips the common leading indentation from a `|` block, so an anchor copied out of a
nested function arrives flush left with its internal structure intact. The engine searches
every indentation depth and requires the match to start at a line boundary, so the relative
indentation still has to be exact — only the absolute depth is searched for.

A mutation that makes the eval crash is not a mutation. If the break you want produces a
`TypeError` rather than a wrong answer, write the one that produces the wrong answer: that is
the bug a real change would have introduced, and it is the one worth catching.
