# Claim 3 — the holdout is neither erased nor chosen after the fact

> Assignment from a committed seed, exactly reproducible.
>
> *The one door with no key.*

```
make claim-3          the eval, and the eight mutations claim 3 owns   ~3 min
make eval-assignment  the eval alone                                   ~17 s
```

---

## 1 · What is attacked

Thirty-six estates the eval's author did not lay out are turned into thirty-six committed
lotteries, and then somebody tries to move a store between arms — from inside the process, and
through the table a readout reads a month later. Ten questions:

| id | the question it would answer `false` |
|---|---|
| `A1.arms-match-an-independently-implemented-lottery` | is the arm every store holds the arm a second, separately written implementation of the draw gives it? |
| `A2.the-committed-digest-matches-an-independent-recomputation` | is the digest on the seal the one an independently framed, independently hashed recomputation puts there? |
| `A3.a-unit-s-arm-is-re-derivable-from-the-committed-record-alone` | can one store's arm be re-derived a month later from the seed, the candidate index and its own stratum — without the seal and without the roster? |
| `A4.the-lottery-does-not-depend-on-the-order-its-inputs-arrived-in` | presented with the same roster written down in another order, does the engine commit to the same record — strata, arms, covariate digest and balance figures? |
| `A5.the-same-committed-seed-reproduces-in-a-fresh-interpreter` | does another process, under another `PYTHONHASHSEED`, reach the same answer? |
| `A6.no-in-process-route-moves-a-unit-between-arms` | is every route an attacker would take inside the process refused **by the seal itself**? |
| `A7.a-flattering-candidate-cannot-be-substituted-after-the-fact` | anyone holding the seed can see which candidate would have flattered the design — is substituting it refused, even when the digest is recomputed to match? |
| `A8.an-erased-holdout-is-refused` | erase a control store, or empty the holdout — is the erasure refused **for a reason that names it**? |
| `A9.a-tampered-assignment-refuses-at-readout-with-its-own-code` | driven through the whole of moment 3, does a clean assignment pass and a substituted one refuse `CONTAMINATED_ASSIGNMENT`? |
| `A10.the-second-implementation-is-a-blake2b` | does the eval's own hash reproduce RFC 7693's published vector and agree with the standard library across a declared sweep? |

`A1` and `A6` carry the claim's two halves — *exactly reproducible*, and *the one door with no
key*. The rest bound the ways those two could be passing for the wrong reason.

---

## 2 · Where the independence is

**This claim's trap is not the one the other six carry, and it is worth stating precisely.**
For claim 1 the trap is a planter reading the same contract as the detector; for claim 2 a
simulator generating data from the process the estimator assumes. Here it is simpler and
easier to walk into:

> **Verifying that a draw is reproducible by running the draw again is a deterministic
> function repeated. It catches nothing.**

`draw` reads no clock, no environment and no random source. Called twice it agrees with
itself — and it would agree just as loudly if the committed seed never reached the key, if
the keyed hash were keyed the wrong way round, if the digest's framing could not tell one
roster from another, or if the "lottery" simply handed the holdout to the lowest-numbered
store in each stratum. Every one of those is perfectly reproducible and none of them is the
lottery that was committed to. So the independence has to arrive from somewhere else, and it
arrives by four doors, strongest last.

**The estates are not ours.** Every roster is what survives `feasibility.neighbour_exclusions`
on a chain `corpus/world/chain.py` laid out — shops placed in towns, given a format, a size
index and a pricing zone by a generator that imports nothing from `holdout` and whose author
never saw this eval. `ops/isolation.py` is the one implementation of that barrier,
`tests/boundary/test_corpus_imports_nothing.py` is the gate and `.claude/hooks/` refuses the
write before it lands. Six worlds, two chain seeds and two scales, because a lottery that
works on one estate has been tried once.

**Another path through the same answer, not the same path twice.** `A3` re-derives a store's
arm the way a readout a month later has to: from the committed seed, the candidate index and
that store's own stratum. It never touches the seal, never sees the rest of the roster and
never replays a sequence. Agreement between the whole-roster path and the per-unit path is a
fact about the lottery; agreement between the whole-roster path and itself is not.

**Another interpreter.** `A5` recomputes the entire grid in a subprocess under three declared
`PYTHONHASHSEED` values and compares one fingerprint. Python randomises string hashing per
process, so a stratification that broke a tie by whichever unit a `set` happened to offer
first would answer differently there and identically under any amount of in-process
repetition. `strata._hardest_to_match` sorts its unmatched units for exactly this reason —
which is a claim its own docstring makes, and `CLAUDE.md` says a guard tested by its author is
tested in the shape the guard already handles. This is the test that was not its author's.

**The lottery is written twice, and the second one shares no code with the first.**
`reference.py` recomputes the draw and the digest over `blake2b.py` — BLAKE2b written out from
RFC 7693 in Python, its own framing, its own rank arithmetic, its own selection. The table is
in `reference.py`'s docstring. The two share the *specification* of the draw and nothing else:

| | `holdout.core.experiment.assignment` | `evals/assignment/reference.py` |
|---|---|---|
| the hash | `hashlib.blake2b` — a C extension | RFC 7693's compression function, written out |
| keying | an argument to the extension | the key length in the parameter block, the key padded into a 128-byte first block |
| the framing | a `bytearray` appended to | `struct.pack(">Q", …)` and `b"".join` |
| the rank | `int.from_bytes(digest, "big")` | accumulated a byte at a time |
| the choice | `min(stratum, key=…)` | an explicit scan comparing `(rank, id)` pairs |
| the shape | one pass over the whole roster | **per unit**, the roster never consulted |

**Everything that reproduces the draw reproduces it from the seal's own record.** Since T002B
"exactly reproducible" takes two committed things and not one: the seed, *and* the strata the
lottery drew within. The strata are a pure function of the covariate matrix, so anyone can
recompute them — but only from the matrix **as it stood at design**, and a restatement moves
that matrix. So `A1`, `A2` and `A3` all read `seal.strata`, never `strata_of` re-run on
today's covariates: the second would pass on a day the first should have gone red. `A4` and
`A5` do re-run the construction, and that is a different question — whether the same inputs
build the same strata twice, in another order and in another interpreter — asked against the
seal's record rather than in place of it.

`A10` is what makes that worth anything. Two implementations agree loudly when both are wrong
in the same way, so the eval's own hash is driven against the digest **RFC 7693 Appendix A**
publishes for the message `abc` — an answer chosen by somebody who has never seen this
repository — and against `hashlib` over a declared sweep: both sides of every 128-byte block
boundary, two multi-block lengths, and every key width and digest size the lottery uses. It is
a declared sweep and not an exhaustive one.

---

## 3 · Observed, derived, swept

| | |
|---|---|
| **observed** | which stores exist, how they cluster, and each one's format, size index, pricing zone and opening date — from `corpus/world/chain.py` |
| **derived**, with the arithmetic written out | `store_size_sqm` = `round(size_index × 1000)`; the unit outcome = `(period.ends_on − opened_on).days`; `mde_absolute` = a tenth of the mean unit outcome |
| **swept**, over a declared deterministic grid | six worlds · two chain seeds · two scales · the holdout share |

The **holdout share** is swept for the reason claim 1 sweeps envelopes. The contract's 20% is
the share every figure that carries the claim is measured at; the other two are not claims
about any design. They are there because at 20% **no roster this corpus produces can reach the
`None` the design engine turns into `NO_ADMISSIBLE_ASSIGNMENT`** — a 20% control arm always
leaves five units to a stratum — so the branch is live code nothing at the contract's own
share drives. At 70% six of them reach it.

The **unit outcome** deserves its own sentence, because claim 3 asserts nothing about
outcomes. It exists so that `A8` and `A9` can drive the whole of moment 3 and watch the
refusal come out, instead of asserting that a function would have produced it — `CLAUDE.md`:
*an assertion about what the system does is written against the function that would make it
true, named, and against the measurement of what comes out when it runs.* It is an observed
date turned into an integer, and it is deliberately not one of the covariates the strata were
matched on, so the design matrix cannot reproduce it exactly.

---

## 4 · What came out

Measured at the grid above, 2026-08-29:

```
A1   4129/4129 units agree with the independent lottery, across 30 configurations
A5   3/3 interpreters agree on one fingerprint of every stratum and every arm
A6   273/273 attempts refused · 12 declared in-process routes, 9 of them per seal
A7   30/30 forgeries refused, over the 15 designs of 30 where a better-balanced
     candidate exists within the scan — careless and careful each
A8   72/72 erasures refused by name · 48/72 = 66.67% of them by the contamination check
A9   24/24 clean readouts pass · 9/9 substituted readouts refuse CONTAMINATED_ASSIGNMENT
A10  RFC 7693 Appendix A reproduced · 176/176 of a declared sweep against hashlib

gate-proof   8 mutations planted, 8 bit
```

**The incentive is real and it is published.** A better-balanced candidate exists for 15 of
the 30 designs within a 24-candidate scan, improving the worst standardised difference by
**0.2422** on average — against a declared tolerance of 0.10. That is the size of the prize
somebody holding the committed seed is being asked not to take, and it is why `A7` exists.

### The finding: 48 of 72, and what the other 24 are

**`contamination.check` does not see a store erased from the assignment table.** It derives
the roster it walks *from the arms it is checking*, so a unit deleted with the digest
recomputed to match leaves nothing for it to compare: it reports the assignment intact, and
`sealed()` agrees. Two of the three erasure routes are caught there; the third is not, and the
figure says which.

What refuses that one is `readout.close`, one function later, and only because the erased
store still reports an outcome — *an outcome from outside the experiment is not a small
addition to the mean; it is a unit whose price nobody randomised*. Both halves are driven
here. `A8` therefore asks whether the erasure is refused **for a reason that names it**, not
merely whether a number came out: a readout that declined `POWER_NOT_REACHED` on an emptied
assignment has caught nothing, and would have declined identically on an intact one.

The gap this leaves is in *what this does not prove*, below, and in `docs/DECISIONS.md`.

---

## 5 · What this does not prove

* **That the definition of the lottery is right.** Both implementations compute the same
  specification — a keyed BLAKE2b rank, the smallest in each stratum takes the holdout — and
  two implementations of one definition cannot tell you the definition was a good one. Nothing
  in this eval attacks the specification; `A10` only says the second one is honestly a
  BLAKE2b, and it says nothing at all about BLAKE2b.
* **That a coordinated forgery is caught.** A seal whose arms, seed, strata and digest are all
  rewritten together agrees with itself, because a seal has never held independent evidence of
  its own provenance. The limit is asserted rather than hidden, here and in
  `tests/core/test_assignment_forgery.py`. What *is* caught is every edit that is not
  coordinated — which is every edit that happens by accident, and most that do not.
* **That an erasure carried through every table at once is caught.** The 24 above are refused
  because the erased store still reports an outcome. Delete it from the assignment table, the
  digest and the outcomes together and nothing here notices; that is the same coordinated
  forgery one door along, and it is why the assignment table is written before the period
  opens and then read-only in the lakehouse rather than defended by arithmetic alone.
* **That these are the strata a real design draws under.** Three of the contract's five
  balance covariates are matched on here — the format, the size and the pricing zone, which
  the chain supplies directly. The other two need a POS aggregation over eight months of
  generated events, which is claim 2's path and costs minutes per world. `evals/uplift/` draws
  over all five, two hundred times, on this same lottery.
* **That the door holds against routes nobody thought of.** Twelve in-process routes and three
  erasures are the ones we imagined — the same honest limit the mutation set carries.
  `A10` in particular owns **no mutation**: it measures the eval's own instrument, and
  `gate-proof` plants breaks in `src/holdout/`, which is a place that check does not look.

---

## 6 · The mutation that survived, and what it corrected

Eight mutations are planted and eight bite. One of them did not, first time, and the record
stays because doctrine rule 4 says a correction never erases what was previously stated — and
because the correction is the most useful thing in this file.

**`the-covariate-matrix-is-walked-in-the-order-its-rows-arrived`** makes
`CovariateMatrix.units` hand back its units in insertion order instead of in store-id order.
It was aimed at `A4`, on the reasoning that the matching, the cells and the allocation all walk
that order. It reported `SURVIVED`.

It was right to. `strata_of` re-sorts at every point that could have depended on it —
`_greedy` sorts its units, `strata_of` sorts its cells, `_allocate` sorts its keys,
`_hardest_to_match` sorts the unmatched, the unplaced are walked in sorted order and every tie
breaks on the id. **The strata are order-independent by construction and not because `units` is
sorted**, which is good news about the design and useless as proof that `A4` was watching
anything. *A gate can only be shown to bite where it is the gate that refuses.*

What the mutation does move is the rest of the committed record: `covariate_digest` walks
`matrix.units` directly, so the digest that says *which covariates these strata were built
from* would differ for the same matrix written down in another order. `A4` compared the strata
and the arms and stopped there. It now compares the whole record the seal commits to — the
strata, the arms, the covariate digest and the standardised differences the design is reported
with — and the mutation bites.

The fix was to the eval, never to the assertion. That is the rule
`evals/gate_proof/README.md` states and the second time this repository has paid to learn it.
