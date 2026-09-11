# Claim 6 — the design engine refuses an invalid design regardless of where the judgment came from

> Human, declared policy, or model. When the source is a model: N designs proposed, M refused,
> and K of those would have produced a confidently wrong number.
>
> *Trap: an LLM judge in the same family is a correlated critic → **the judge never rules on
> validity**; code does. The judge rules only on design quality.*

```
make claim-6          the eval, and the mutations claim 6 owns
make eval-design      the eval alone
make record-designs   ask the model every question in the bank and seal the answers -- deliberate,
                      never run by CI, and the only step here that opens a socket
```

**The trap, in this eval's own words.** The thing under test is a set of refusals. If the
designs it is tested on were written by whoever wrote the refusals, the engine refuses exactly
what its author imagined it should refuse — one function agreeing with itself, wearing a test.
And if a model is asked whether a refusal was *right*, and that model shares a family with the
one that proposed, or with the person who wrote the engine, its agreement is not evidence
either. So: **the designs come from something that has never read `feasibility.py`, and
validity is decided by code and by a sealed truth, never by a model.** There is no LLM judge
in this eval at all. `CLAUDE.md` permits one for design *quality*; nothing here needs a quality
score, and a second vendor dependency for a number nobody checks is code that serves no claim.

---

## 1 · What is attacked

Three numbers, and a fourth published beside them because without it the first three can be
made to look good by a proposer that never tries.

| | |
|---|---|
| **N** | designs delivered by a model, in a recording that holds every question asked and every answer given |
| **M** | how many the engine refuses, computed live on every run from the recording and the contracts as they stand, by reason code |
| **K** | how many of the M, run anyway under the violation they were refused for, produce a number that is significant at the declared α and that the sealed truth says is wrong |
| **declined** | questions the model answered with no design at all — the rate a proposer that pre-empts every refusal would drive to 100% |

`K` is the claim. `N` and `M` are counts and cost nothing; a system that refuses everything
scores perfectly on them. `K` is what turns a refusal from caution into a save with a count on
it, and it is obtained the only way it can be: **by running the refused design**. The
comparison window's outcomes exist for this — `evals/uplift/potential.py` composes them for any
assignment — so a design the engine refused as underpowered is drawn from its committed seed,
closed on the world it was proposed against, and its readout is compared to what the seal says
the effect was. A confident number on a world whose true effect is zero is a false positive the
refusal prevented. A confident number whose interval excludes the truth is a wrong one.

| id | the question it would answer `false` |
|---|---|
| `D1.the-recording-is-from-the-agent-in-the-tree` | do the registry and prompt fingerprints in the recording equal the ones this tree computes now, and does the directory's digest equal the manifest's? |
| `D2.every-question-is-counted` | is N the whole recording — every file the manifest counts, none filtered, each outcome a proposal or a named failure and never both? |
| `D3.the-engine-decides-and-not-the-record` | is every verdict computed on this run from the proposal and the contracts, with no verdict read from disk? |
| `D4.a-refusal-is-a-declared-code` | is every refusal a code from `reason_codes.yaml`'s `at_design` section carrying a detail and a remedy? |
| `D5.three-sources-one-verdict` | does the same form, stamped `agent`, `human:<name>` and `policy:<name>`, produce byte-identical verdicts — and does a planted branch on `filled_by` inside the engine turn this red? |
| `D6.a-refused-design-run-anyway-is-wrong-at-the-rate-the-refusal-predicts` | over the refused designs that can be run, is the share producing a confident wrong number at least what the refusal's own reason implies — and never below the false-positive floor a valid design would have? |
| `D7.every-reachable-refusal-is-reached` | does the recording reach every `at_design` code the agent's route can reach — and is every code it cannot reach named, with the reason, rather than absent? |
| `D9.the-interference-table-is-the-contracts` | for every unit of randomisation, does the engine's interference verdict equal the one derived a second way from the contract's carryover block — over every unit, not over the recording, so that a unit admitted by mistake is caught whatever the model proposed? |
| `D8.the-power-boundary-lands-where-independent-arithmetic-puts-it` | for every graded design, does a second implementation of the power boundary — `Decimal`, solved rather than searched — agree with the engine on refuse-or-accept, on which code, and on the window and sample where it accepts? |

`D5` is the sentence in `CLAUDE.md` — *the engine does not know and does not care who filled
the form* — made checkable, and it is checked by a mutation rather than by agreement: three
forms that happen to agree prove the engine agreed three times; a planted `if filled_by is
agent` that the eval catches proves it cannot disagree.

---

## 2 · Where the independence is

Three separations, and the third is the one that carries the claim.

**The designs are not ours.** Every design in the recording was delivered by a model that was
shown `holdout.agent.context.enumerated` — six entries, a fixed list — and the compiled tool
definitions, and nothing else. It has never read `feasibility.py`, `refusal.py` or this file.
The recording carries the fingerprint of exactly what it was shown, and `D1` recomputes that
fingerprint from the tree on every run: a recording made against a different registry, a
different prompt or a different pre-period is `STALE`, in the same word `gate-proof` uses for a
mutation whose target has moved. **The questions are ours** — a bank in `questions.yaml`,
written against the estate's own categories — and that is stated as a limit in §3 rather than
hidden: the questions choose what is asked, the model chooses what is proposed, and the claim is
about what is proposed.

**The truth is sealed, and behind a barrier.** `K` compares a readout against
`corpus/world/seal.py`'s injected truth, which is written by a package that imports nothing from
`holdout` (`tests/boundary/test_corpus_imports_nothing.py`) and is opened only after the readout
exists. The engine that refused the design and the world that says whether the refusal saved a
wrong number share one thing: the schema in `contracts/`. Not a helper, not a rounding
primitive, not an estimate.

**Validity is code.** No model, no person and no file says whether a design is valid. The
verdict is `holdout.core.design.feasibility.assess`, run on this machine, on this run. The
recording would be worthless if it carried its own verdicts — `D3` reads the outcome files and
refuses one that has a `verdict`, `refused` or `reasons` key.

What the two sides share is the contract, and the eval says so: the model is told which metrics
and which policies exist because the form's closed lists are compiled from the same files the
engine reads. That is claim 5's mechanism, not a leak.

---

## 3 · What this does not prove

Printed on every run, as `Report.notes`, because a limit that lives only here stops being true
quietly.

- **The questions were written by this repository.** The model chose the designs; the bank
  chose what to ask -- and was sharpened once, on 2026-09-11, when a recording reached every
  code but one and `D7` went red: a thirteenth question that asks for a change no roster could
  detect. A bank of questions that all invite the same refusal would inflate M and
  say nothing, and the defence is that the bank is committed, read on every run, and printed
  with its size — not that it is unbiased.
- **The recording is a fixed sample from a dated model.** It is stamped with the model id and
  the day, and `D1` refuses a stale one, but it is one model's answers on one day and the claim
  is about the engine, not about that model. A stronger proposer produces fewer refusals for
  cruder reasons and more for subtle ones; the numbers are read with the model id beside them.
- **`K` is computed only for the refusals the harness can run.** A design refused as
  underpowered can be drawn and closed; one refused because its unit guarantees interference
  can be run on the world that has interference; one refused because its metric is not in the
  contract cannot be run at all, because there is nothing to measure. Every refusal that cannot
  be run is counted and named in the output, and the rate is over the ones that can.
- **`K`'s rate on a null world is bounded below by α, and that bound is not a finding.** An
  underpowered design on W1 produces a false positive at the declared rate whatever the engine
  said; the eval publishes that expectation beside the measurement so a number that merely
  matches α is not read as a save. What `K` shows is the refusals whose reason predicts a rate
  *above* α — peeking, interference, post-hoc exclusions — where the design is wrong for a
  reason, not by chance.
- **Two of the three metrics the agent may name have a pre-period here; the third does not.**
  The harness ledger carries revenue, cost of goods and waste, so a design on the margin or on
  waste value is assessed against its own metric's history. `units_sold_per_store_week` has no
  ledger column, and a design naming it is counted under `ungraded` with the reason, never
  assessed against another metric's variance.
- **The policy family has one member.** Every intervention the model can name is
  `ladder_policy@v1` against itself, so every design is A/A by construction until a second
  version exists. Every refusal code except one is reachable regardless; what is unreachable is
  a design whose *treatment* could be wrong, and that is the author's to add.
- **`METRIC_NOT_IN_CONTRACT` cannot be reached by the agent**, because the delivery tool's
  schema closes the list at the API. It is reached by the human path instead, and `D7` says so
  rather than reporting it as coverage.
- **A proposer that declines is not refused.** A question the model answered with prose and no
  design is `no_delivery` in the recording, counted under *declined*, and outside N. It is
  published because a model that pre-empts refusals is the trap from the other side, and a
  claim about the engine's refusals cannot be proved on a proposer that never proposes.
