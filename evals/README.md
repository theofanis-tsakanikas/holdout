# `evals/` — one directory per claim

An eval is not a test.

The suite under `tests/` asks whether a module does what its author meant it to do. An eval
asks whether **a claim in `CLAUDE.md` is true**, on inputs its author did not choose, and it
publishes the numbers rather than a tick. The two fail in different ways and neither
substitutes for the other: a green suite told us nothing about the ladder producing a price
the guardrail set refused, because nothing in the suite was trying to break anything.

Claim 1's eval is the first one built, so its shape is the shape the rest inherit. This file
records that shape, and the reasoning behind each part of it, so that claims 2, 3 and 4 do
not each invent their own.

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
    engine.py               the three rules
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
green tick*. `9/200 = 4.5%` says more than PASS ever will, and a figure that only appears on
failure is a figure nobody has looked at.

**4 · Coverage is itself a check.** An eval whose inputs cannot reach half the vocabulary has
proved half the claim. `G8.every-refusal-code-is-reached` goes red on an unreached code
rather than mentioning it in a footnote, because a footnote is where a gate that stopped
biting goes to be forgotten.

**5 · A second implementation, not a second call.** Where a check needs to know where a
boundary is, it recomputes it — in a different unit, in a different structure, and sharing
nothing with the code under test but the declared rule values. Two consumers calling the
same function prove nothing; that is claim 5's trap and it applies here too.

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
make claim-1          the eval and its mutations         ~3 min
make eval-guardrail   the eval alone                     ~10 s
make gate-proof       every claim's mutations
```

`make check` deliberately does **not** run them: it is the fast local gate and the claims
take minutes. CI runs every claim target that exists.

Add `--json` to any eval for the machine reading `gate_proof` consumes.
