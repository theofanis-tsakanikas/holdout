# Holdout

<p align="center">
  <a href="https://github.com/theofanis-tsakanikas/holdout/actions/workflows/ci.yml"><img src="https://github.com/theofanis-tsakanikas/holdout/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-yellow.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/python-3.12+-3776AB?logo=python&logoColor=white" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/IaC-Terraform-7B42BC?logo=terraform&logoColor=white" alt="Terraform">
  <br>
  <img src="https://img.shields.io/badge/Databricks-FF3621?logo=databricks&logoColor=white" alt="Databricks">
  <img src="https://img.shields.io/badge/Delta%20Lake-003366?logo=delta&logoColor=white" alt="Delta Lake">
  <img src="https://img.shields.io/badge/dbt-FF694B?logo=dbt&logoColor=white" alt="dbt">
  <img src="https://img.shields.io/badge/Spark-E25A1C?logo=apachespark&logoColor=white" alt="Spark">
  <img src="https://img.shields.io/badge/AWS-232F3E?logo=amazonwebservices&logoColor=white" alt="AWS">
  <img src="https://img.shields.io/badge/Amazon%20Bedrock-232F3E?logo=amazonwebservices&logoColor=white" alt="Amazon Bedrock">
  <br>
  <img src="https://img.shields.io/badge/tests-1986%20passing-2ea44f" alt="1986 tests passing">
  <img src="https://img.shields.io/badge/claims-7%20of%207%20green-2ea44f" alt="7 claims green">
  <img src="https://img.shields.io/badge/gate--proof-59%20mutations%20bite-2ea44f" alt="59 mutations bite">
  <img src="https://img.shields.io/badge/A%2FA%20false%20positives-8%2F200%20%3D%204.0%25-2ea44f" alt="A/A false positive rate 4.0%">
</p>

**A pricing system for a supermarket chain that proves whether its decisions made money — and, when the proof cannot stand, produces no number and a reason code.**
*Python · Databricks on AWS · Delta Lake · dbt · Spark · Terraform · GitHub OIDC · Amazon Bedrock*

---

## The problem

A retailer's pricing team reprices thousands of expiring fresh products every day, and once a
quarter somebody shows a slide that says the system delivered €4.2M. Nobody in the room can check
it. The number was computed against a "before" that was chosen after the fact, on stores that were
picked because they looked good, read out early because the first week looked promising, or on an
experiment that never had the power to detect what it claims. Every one of those makes the number
unfalsifiable, and an unfalsifiable number is worth exactly nothing to the person who has to act
on it.

Holdout takes the decisions and then refuses to state a result unless the comparison behind it is
valid: a share of the estate held back from the start and locked, a design that is checked for
power before a single unit is assigned, a readout that will not open before its declared end, and
four checks — balance, exposure, contamination, power — every one of which has to pass. Over 200
A/A draws it reports a "significant" effect **8 times, 4.0%, against a declared α of 5%**; where
the checks fail it reports the reason instead. **An uplift number produced without a valid holdout
is a build failure.** That is the project in one sentence.

## Status

**Everything in this repository is proved locally, and the estate has been built, driven and torn
down through CI four times.** The last full cycle ran on 2026-09-13, from `main`, every dispatch
verified against the account afterwards:

| step | run | what it did |
|---|---|---|
| `deploy` | [34756057061](https://github.com/theofanis-tsakanikas/holdout/actions/runs/34756057061) | four Terraform layers, 135 resources, in 5 minutes |
| `backfill` | [34756473276](https://github.com/theofanis-tsakanikas/holdout/actions/runs/34756473276) | 8 weeks of history, silver and gold, a model trained, gated, registered and served |
| `run` | [34758751989](https://github.com/theofanis-tsakanikas/holdout/actions/runs/34758751989) | a live day with late and duplicated deliveries; both experiments read out; the endpoint asked which version answered |
| `inspect` | [34759485334](https://github.com/theofanis-tsakanikas/holdout/actions/runs/34759485334) | every table counted, both dashboards' datasets executed, the assignment table's door tried, ten demo queries run |
| `destroy` | [34761519867](https://github.com/theofanis-tsakanikas/holdout/actions/runs/34761519867) | 138 resources and the workspace's network removed; the account asked what is left |

What `run` read out of `gold.readout` on the estate — one experiment sized correctly, one declared
with a stopping rule that permits peeking:

```
readouts       2
with a number  1   ['fresh-ladder']          +12,398 cents  [+11,223, +13,571]  p = 0.001
refused        1   [('fresh-ladder-peeking', 'STOPPING_RULE_PERMITS_PEEKING')]
OK      every figure this step publishes was asserted
```

**The estate is torn down.** It costs nothing while it is down, it is rebuilt from `main` by one
dispatch, and a torn-down estate that provably ran is worth more here than one left standing —
the whole argument of the project is that a number has to be reproducible from what was written
down. Screenshots of the two AI/BI dashboards are the one thing this README does not yet carry;
they are taken at the console on the next cycle and go through `aws-mask` before they land.

## Contents

- [The problem](#the-problem) · [Status](#status)
- [Architecture](#architecture)
- [The seven claims, and how each is attacked](#the-seven-claims-and-how-each-is-attacked)
- [The refusal is the product](#the-refusal-is-the-product)
- [The agent proposes and never approves](#the-agent-proposes-and-never-approves)
- [The gates are proved to bite](#the-gates-are-proved-to-bite)
- [Quickstart](#quickstart) · [Testing](#testing) · [Repository layout](#repository-layout)
- [What this does not do](#what-this-does-not-do) · [Cost](#cost) · [Decisions](#decisions)
- [Docs](#docs) · [Security](#security) · [License](#license)

---

## Architecture

```mermaid
flowchart LR
  subgraph contracts["contracts/ — the source of truth"]
    M["metrics · guardrails · policies<br/>design · vocabularies · ml · agent"]
  end
  M -- "make contracts compiles" --> C1["dbt models"]
  M --> C2["SQL functions"]
  M --> C3["agent tool definitions"]
  M --> C4["readout query"]
  M --> C5["AI/BI dashboards"]

  subgraph estate["the estate — Databricks on AWS, serverless, applied by CI"]
    L["landing (S3)"] -- "bulk load" --> B["bronze<br/>7 sources, as delivered"]
    B --> S["silver<br/>as-of joins · dedup · quarantine"]
    S --> G["gold<br/>economics · waste · assignment · decisions · readout"]
    G --> D["dashboards"]
    S --> T["training → model version → endpoint"]
  end
  C1 --> G
  C4 --> R["readout: 4 checks → a number, or a reason code"]
  G --> R

  subgraph local["local — no account, no credentials"]
    W["corpus/world — six adversarial worlds<br/>(imports nothing from the system)"]
    E["evals/ — one per claim · gate-proof"]
    A["agent — Bedrock, confined to the compiled tools"]
  end
  W --> E
  A --> E
```

The boundary that matters is the one between the contract layer and everything else: a metric is
defined once, in YAML, and compiled into every consumer, so two consumers cannot disagree about
what margin means. The second boundary is between `corpus/world/` and `src/holdout/` — the
generator that produces the adversarial worlds imports nothing from the system it attacks, and a
test fails the build if it ever does. The third is the assignment table: written before the period
opens, from a committed seed, and append-only at the storage layer.

---

## The seven claims, and how each is attacked

Every claim is a Makefile target, every target owns an eval and a set of planted mutations, and
CI runs every one of them on every push. The trap beside each claim is the way an eval could agree
with itself; the attack is what stops it.

| # | claim | attacked by | measured on `main` |
|---|---|---|---|
| 1 | No price reaches a shelf without the guardrail set | 32,480 price quotes the ONS collected in shops, not a planter reading the same contract | 0 violations in 28,482 certified prices · 0 disagreements in 824,790 bounds |
| 2 | On an A/A split the system reports an effect no more often than α | 200 seeds × six adversarial worlds, a design-based estimator, a generator behind an enforced import barrier | **8/200 = 4.0%** against α = 5%; W6 false-refusal rate 0/200 |
| 3 | The holdout is neither erased nor chosen after the fact | a committed seed, a seal, and a contamination check that reports every uncoordinated edit by name | 10/10 checks; on the estate, `delta.appendOnly` refuses the `DELETE` by name |
| 4 | A stock-out is never read as zero demand | days censored on purpose where the withheld total is known | 0 of 16,942 emptied store-days read as fully observed |
| 5 | One definition, three mechanisms, the same number | the compiled SQL executed by Spark against the Python path, as integers | 4/4 checks, no tolerance |
| 6 | The design engine refuses an invalid design whoever proposed it | a real model's 13 proposals graded live; peeking and post-hoc exclusions run anyway on the null world | N = 11 proposed, M = 8 refused; peeking is confidently wrong in 4 of 28 lotteries (14.3%) |
| 7 | A decision that targets a person is structurally impossible | 317 person-names from two published vocabularies against a closed field set | 0 of 244 fields is a name a person is known by |

The figures are the ones `make claim-N` prints; `make figures` re-runs the ones that appear in
prose and fails when they drift.

## The refusal is the product

The design engine sees a nine-field form — hypothesis, intervention, scope, metric, unit, minimum
detectable effect, duration, exclusions, decision rule — and answers one question at three moments:
*can this experiment exist*, *is it running as declared*, *may the result be stated*. The
vocabulary of refusals is closed, so a refusal can be counted, tested and gated:

```
at_design:   UNDERPOWERED_FOR_DURATION · UNDERPOWERED_FOR_CAPACITY · UNIT_GUARANTEES_INTERFERENCE ·
             STOPPING_RULE_PERMITS_PEEKING · EXCLUSIONS_DEFINED_POST_HOC · METRIC_NOT_IN_CONTRACT ·
             UNITS_ALREADY_COMMITTED · NO_ADMISSIBLE_ASSIGNMENT
at_readout:  IMBALANCED_PRE_PERIOD · EXPOSURE_BELOW_THRESHOLD · CONTAMINATED_ASSIGNMENT · POWER_NOT_REACHED
```

On the estate the two declared experiments are the demonstration: the same intervention, sized
correctly, produces a number with an interval; declared with four interim looks and no spending
function, it is refused at design and never assigned. The refused version of the readout screen
is the single most important image in the project, and the dashboard shows the refusal in the same
cell the number would occupy.

A finding worth reading before trusting the number above: for four days the estate refused *both*
experiments, and the refusal was accepted as the demonstration. It was a correct output of a wrong
input — the ERP's cost ledger had been exported once, on the last day of the history, so silver
knew every cost on that day and priced no earlier sale. A fresh-context review found it by reading
`known_from` against the export day; [`docs/FINDINGS.md`](docs/FINDINGS.md) carries it, and the
gate now requires both a number and a refusal so that it cannot pass on a bug again.

## The agent proposes and never approves

The second AI system is a language model — Claude Haiku 4.5, reached through Amazon Bedrock with
the account's own credentials and no second secret — that proposes experiment designs. It is
confined rather than trusted:

- it can call exactly the three tools the metric contract compiles to; a planted call to
  `run_sql` is refused by name, and the loop edited to bypass the registry turns a test red;
- two of the nine fields — `max_duration` and `decision_rule` — cannot be filled by it, because
  the proposal type has seven fields and nowhere to put them: *the agent proposes how we will
  find out, never what we will do once we know*;
- its recording is fingerprinted over the tool registry and the prompt, and the eval recomputes
  both — a prompt edited without re-recording is `STALE`, not green;
- validity is decided by code, the same code for a human, a declared policy or the agent, and a
  mutation that makes the engine trust a human more turns the eval red in 36 seconds.

No language model is anywhere near the decision path: too slow, too expensive at 2.4M decisions
a day, and non-deterministic.

## The gates are proved to bite

`make gate-proof` plants **59 mutations** across the seven claims — the margin floor rounding the
wrong way, a neighbour exclusion keeping both members of a pair, a sample size losing a z, a prompt
edited without re-recording — and requires each to be refused **by the check named in advance**.
A mutation caught by a different check proves nothing about the line it was aimed at and is
reported as `SURVIVED`; two did, in claim 1's history, and both are kept in the record. A mutation
that crashes the eval is not a mutation. The ledger refuses a claim target with nothing planted
against it.

The same rule is turned on the repository's own documents: `make findings` refuses a finding that
no longer anchors to the line it named, `make expiry` refuses a deferral with no unlock condition
and no date, `make figures` re-runs every figure that appears in prose, and `make language`
refuses Greek outside the declared exceptions in a repository whose author works in Greek.

---

## Quickstart

Requires Python 3.12, [`uv`](https://docs.astral.sh/uv/), `jq`, and Terraform for `make terraform`.
No cloud account is needed for anything below.

```bash
# 1. clone and install the local extras
git clone https://github.com/theofanis-tsakanikas/holdout.git && cd holdout
uv sync --extra contracts --extra agent

# 2. the whole local gate: lint, types, contracts, the four document gates, the suite
make check

# 3. one claim end to end — the eval, then the mutations planted against it
make claim-1

# 4. the one that separates this from a demo: 200 A/A draws over six worlds (minutes, cached)
uv sync --extra spark && make claim-2
```

The estate is reached only through the five dispatch workflows in
[`.github/workflows/`](.github/workflows/), from `main`, and each of them refuses a sha that `ci`
has not passed. Applying `infra/bootstrap` from a laptop, once, is the one manual step and is
written up in [`infra/bootstrap/README.md`](infra/bootstrap/README.md).

---

## Testing

**1,986 tests** — 1,920 in `make test` plus 66 that need Spark and dbt and run in their own CI
bins (`silver`, `gold`, claim 2's tests) — cover the core, the contracts and their compilers, the
corpus barrier, the pipelines against local Delta, the agent against a scripted model, and the
repository's own gates. They deliberately do not touch a cloud account: the estate is exercised by
the dispatch workflows and asserted against the account, never by a test.

```bash
make check         # lint · typecheck · contracts · language · findings · expiry · figures · terraform · tests
make claim-N       # one claim's eval and its gate-proof mutations, N in 1..7
make gate-proof    # the mutation ledger: every claim target owns what is planted against it
```

CI ([`ci.yml`](.github/workflows/ci.yml)) discovers every `claim-N` target from the Makefile — a
target that exists but is never run is impossible by construction — packs them into bins sized
from measured runtimes, shards claim 2 seven ways, and requires one aggregate check on `main` that
fails on anything that is not `success`, including `skipped`. Figures above are from run
[34763261333](https://github.com/theofanis-tsakanikas/holdout/actions/runs/34763261333).

---

## Repository layout

| Path | Purpose |
|---|---|
| [`contracts/`](contracts/) | the source of truth: metrics, guardrails with effective windows, policies, the design form, the closed refusal vocabulary, training, the agent's ceilings |
| [`generated/`](generated/) | what the compilers emit — byte-compared on every run, never hand-edited |
| [`src/holdout/core/`](src/holdout/core/) | pure functions over plain data: guardrails, the ladder, the design engine, assignment, the four checks, the estimator, the censoring correction |
| [`src/holdout/contracts/`](src/holdout/contracts/) | the loader and the compilers |
| [`src/holdout/agent/`](src/holdout/agent/) | the proposer: context, tool registry, the seven-field proposal, the recording |
| [`corpus/world/`](corpus/world/) | the six adversarial worlds — imports nothing from `src/` |
| [`corpus/real/`](corpus/real/) | what somebody else published, digest-checked: 32,480 price quotes, two vocabularies of person-names |
| [`pipelines/`](pipelines/) | ingest (bulk load, the ERP's drops, the live-day driver), silver, gold (dbt), ml |
| [`evals/`](evals/) | one directory per claim, `report.py` as the shared shape, `gate_proof/` for the mutations |
| [`ops/`](ops/) | the repository's own gates: findings, expiry, figures, language, the CI packer, the estate inspector, the demo's queries |
| [`infra/`](infra/) | six Terraform layers: bootstrap (local, once), foundation, lakehouse, pipelines, ml, serving |
| [`.github/workflows/`](.github/workflows/) | `ci`, and the five that dispatch from `main`: `deploy`, `backfill`, `run`, `inspect`, `destroy` |
| [`docs/`](docs/) | scenario, decisions, findings, the regulatory posture, day-one manual steps, the three phase reviews |
| [`tests/`](tests/) | the suite the gates run |

---

## What this does not do

- **The decision path does not run on the estate.** The model is trained, gated, registered and
  served there, and is called once — by `run`, to prove which version answers. Every price on the
  estate's shelves is the corpus's own ladder price, so the decision monitor shows one amber band
  of fallbacks and no guardrail fires at decision time. The path is proved local, over real price
  lists; routing the live day through the served model and the guardrails is unbuilt.
- **Nothing streams.** The design names Zerobus for the live day; the live day arrives as files
  in the landing zone and is bulk-loaded, exactly as the history is. Lateness and duplicates are
  injected by the driver, not by a transport.
- **The number is the world's.** The uplift the estate reads out is on a synthetic world with an
  injected effect; it shows the estate can carry an experiment and read one out, not that any
  effect is real. Validity comes from the lottery and is proved by claim 2, locally.
- **Claim 2's seal is decorative.** The sealed truth file exists on the estate; the eval takes
  its truth from regeneration and never opens a seal. Same estimand, a mechanism the docs describe
  and the eval does not use — recorded, not hidden.
- **The reaper has never had to fire.** It is armed by default since 2026-09-13, its failure topic
  is subscribed, and it has reported correctly on every scheduled run; no estate has yet outlived
  its 48-hour TTL for it to collect.
- **The budget could not see the bill until 2026-09-13.** Serverless DBUs bill through the AWS
  Marketplace untagged; a second budget now watches that line, with alerts and no automatic halt.
- **The environments have no required reviewer.** `deploy` and `destroy` dispatch on a green
  `main` without a human click; that is a decision the author has kept open, on purpose.
- **Zero real sales.** The estate loads 320 stores, 4 SKUs a category, 17 weeks; the scenario's
  1,200 stores and eight months are the design and have never been run.

Everything above is filed with a site and a disposition in [`docs/FINDINGS.md`](docs/FINDINGS.md),
which currently holds 131 findings, and the gate refuses one that stops anchoring to its line.

---

## Cost

**$0 idle.** The estate is destroyed after every cycle; what survives is the Terraform state
bucket, its access-log bucket, one KMS key, five SSM parameters and one IAM role, none of which
bills. Measured with Cost Explorer for 1–12 September 2026, over four full cycles and every
dispatch that failed part-way: **47 USD** on the Databricks line and **0.42 USD** on everything
the project tag can see. A clean cycle is on the order of 10 USD. Two budgets alert at 50, 80 and
100% of 1,000 USD; the only automatic halt is at 150%, on the tagged budget, and would disable the
deploy role rather than the estate. The reaper collects Databricks compute older than 48 hours
whatever else happened.

---

## Decisions

The decision registry is [`docs/DECISIONS.md`](docs/DECISIONS.md): scope, technology, method, and
the deferrals — each with the condition that unlocks it or a date, because `make expiry` refuses
one with neither. A few that shaped the project, including the ones that turned out wrong:

| | |
|---|---|
| A design-based estimator, never model-based | validity comes from the lottery, so the six worlds test the machinery around the subtraction, not the subtraction |
| Re-randomisation rejected for stratification | the balance screen accepted one draw in a thousand and starved the permutation reference set; measured, then replaced |
| No customer-managed VPC | serverless compute runs in Databricks' account; a VPC would have been a NAT gateway billing for nothing — copied from a sibling project and refused on measurement |
| `destroy` is never automatic | on failure it destroys the evidence; on success the standing estate is what the camera needs |
| The phase-3 criterion weakened to *the refusal*, then restored | the refusal was an artefact of an export timetable; the criterion is a number and a refusal again |
| The agent's runtime is a local adapter, not an estate object | the recording graded by CI is the claim; a gateway would be a photograph with a bill |

---

## Docs

[SCENARIO](docs/SCENARIO.md) — the shop, and the four kinds a number may be ·
[DECISIONS](docs/DECISIONS.md) · [FINDINGS](docs/FINDINGS.md) ·
[REGULATORY](docs/REGULATORY.md) — the Greek margin cap and the prior-price rule, with citations ·
[DAY-ONE](docs/DAY-ONE.md) — the manual steps with no API ·
[reviews/](docs/reviews/) — the three phase-boundary reviews ·
[CHANGELOG](CHANGELOG.md)

The engineering rules, the doctrine and the claims are in [`CLAUDE.md`](CLAUDE.md); the README
links to it and does not repeat it.

## Security

No long-lived credentials: CI assumes one role through GitHub OIDC, scoped to three environment
subjects, and the role carries an explicit Deny against widening its own policy or deleting the
state. `gitleaks` is a required check. Scope, reporting and known limits: [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE) © 2026 Theofanis Tsakanikas
