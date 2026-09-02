# Holdout — the local gate.
#
# Everything here runs on a laptop or in CI with no cloud account and no credentials.
# That is not a convenience: it is the only reason the claims are checkable by anyone who
# clones the repository.
#
# `make check` is what CI runs and what a session runs before it commits.
#
# One target per claim, because a claim that is a Makefile target is a structural gate and a
# claim that is a paragraph is advice. `ci` discovers them by grepping this file rather than
# by listing them, so a claim target that exists but is never run is impossible.
#
# Still deliberately absent: `claim-5`, `claim-6` and `preview-audit`. A green target that
# proves nothing is worse than a missing one — it is a gate disarmed before it was ever
# armed — so each arrives with the eval that earns it.

UV ?= uv
RUN := $(UV) run

#: Everything that is Python and is ours. `evals/`, `corpus/`, `ops/` and the harness hooks
#: are linted and type-checked exactly as `src/` is: an eval is the evidence a claim rests on,
#: a hook is a guarantee, and evidence or a guarantee held to a lower standard than the code
#: it judges is not one for long.
PYTHON_DIRS := src tests evals corpus ops .claude/hooks

.DEFAULT_GOAL := help
.PHONY: help setup setup-locked check test lint format typecheck contracts contracts-write \
        expiry language figures findings claim-1 claim-2 claim-3 claim-4 claim-7 \
        claim-2-shard claim-2-combine claim-2-tests \
        eval-guardrail eval-uplift eval-assignment eval-censoring eval-oversight gate-proof \
        world roster corpus clean

help:  ## show this help
	@grep -hE '^[a-z][a-zA-Z0-9_-]*:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[1m%-16s\033[0m %s\n", $$1, $$2}'

setup:  ## create the virtualenv and install everything
	$(UV) sync

setup-locked:  ## install exactly what uv.lock pins — what CI runs, and what refuses a drifted lock
	$(UV) sync --locked

check: lint typecheck contracts language findings expiry figures test  ## the whole local gate, in the order that fails fastest
	@echo ""
	@echo "OK      lint · typecheck · contracts · language · findings · expiry · figures · tests"
	@echo "        the claim targets are NOT in here — they take minutes, and CI discovers"
	@echo "        and runs every one of them. Run 'make claim-1' before a claim's own PR."

lint:  ## ruff, as a linter and as a formatting check
	$(RUN) ruff check $(PYTHON_DIRS)
	$(RUN) ruff format --check $(PYTHON_DIRS)

format:  ## ruff, rewriting
	$(RUN) ruff format $(PYTHON_DIRS)
	$(RUN) ruff check --fix $(PYTHON_DIRS)

typecheck:  ## mypy, strict
	$(RUN) mypy

# **`-m "not claim_2"`, and the deselection is a gate rather than a convenience.**
#
# `tests/evals/test_uplift_shards.py` proves that sharding moves where claim 2's draws are
# produced and not a single number, byte for byte at three shard counts. That property is claim
# 2's evidence and it costs what claim 2's evidence costs: measured on one machine, cold, the
# suite went from **1m36s to 8m14s** and every second of the difference was that one file, of
# which ~200s is generating the machinery worlds the `gate` job caches nowhere. In CI it took
# `make check` past the fifteen-minute budget it had just been given, and the run was cancelled
# with the whole shard matrix already green.
#
# So it runs where claim 2 runs, which is what the line at the bottom of `check` has always
# said: the claim targets are not in the suite because they take minutes.
#
# **What that buys has to be paid for**, and it is, in two places — because a test deselected
# from the suite and run by nothing looks exactly like one that is covered, which is `claim-[1-7]`
# with a different population:
#
#   * `ops/figures.py`'s `suite` row: every test `make test` deselects must be selected by some
#     `claim-*` target, counted by asking pytest itself rather than by reading a list.
#   * `tests/ops/test_ci_sharding.py`: for a **sharded** target CI never runs the plain target at
#     all — it runs `-shard` on N machines and `-combine` on one — so whatever `claim-2` selects,
#     `claim-2-combine` must select too, or CI runs none of it.
test:  ## the suite, minus what a claim target owns
	$(RUN) pytest -m "not claim_2"

contracts:  ## validate every contract and refuse a stale or hand-edited generated artefact
	$(RUN) holdout-contracts check

contracts-write:  ## recompile every consumer and write it to generated/
	$(RUN) holdout-contracts compile

# CLAUDE.md's first line: "all repository content in English. Conversation with the author
# in Greek." It was enforced nowhere until 2026-08-30, and it had already been broken — a
# review report landed on `main` carrying 12,803 Greek characters, in a public repository.
#
# Not a blanket ban. A verbatim article of a Greek instrument, the 63 published basket
# categories and the ONS item descriptions, and the symbols alpha, beta and tau are all
# load-bearing, and translating any of them would be the defect rather than the fix. So the
# exceptions are two closed lists in `ops/language.py`, each entry carrying its reason.
#
# It refuses to report green until it has shown that it works: the detector must fire on a
# sentinel, the walk must have reached the tree, and every declared exception must still be
# in use. That is here because the violation was first mis-measured by `grep -P`, which BSD
# grep does not have -- it exited 1, stderr was discarded, and "no matches" was read off a
# command that never ran the check. The silence of a missing instrument is indistinguishable
# from a pass, so this one is not allowed to be silent.
language:  ## refuse Greek in repository content outside the declared exceptions
	$(RUN) python -m ops.language

# A gate reports on what it examined. It becomes a lie when it reports what it examined as
# if it were what exists. Two instances are in the record and they are the same defect at two
# coverages: `grep -P`, absent, giving a count of zero from a check that never ran; and
# `discover` matching `claim-[1-7]`, which could not have seen a `claim-8` -- and since
# `claims-complete` aggregates only what `discover` emits, the required check would have been
# silent about a claim whose gate never ran.
#
# So every gate declares how its population is enumerated, and this recomputes it a second time
# and compares. Red when examined < exists. NEVER red when examined > exists: over-coverage is a
# tool doing more than asked -- ruff formats Python inside Markdown -- and freezing either number
# would go red on a version bump that is not a defect. Same shape as Money's roundings: a bound
# that rounds toward what it forbids is not a bound.
figures:  ## refuse a gate that examined less than exists, and a figure that stopped reproducing
	$(RUN) python -m ops.figures

# Every mechanism here was aimed at a claim, a gate or a deferral. An open review finding is
# none of the three, so it had nowhere to fall out of -- and two of them fell: the legal half of
# oversight level 2's third finding against claim 1, absent four days later, and the phase-1
# review's own §4, dropped by the table that assigns every other section to a branch.
#
# So a finding anchors to a line that already exists and goes red when that line stops saying
# what the finding says it says -- `ledger.every-anchor-is-aimed-at-one-place` over a new
# population. A finding with no site is refused; one with no disposition is refused; `none --
# <reason>` is a disposition and is reported as adrift rather than refused, because a finding
# nobody has scoped yet is a real state and refusing it teaches people not to file.
#
# And `concurred` is not `closed`. Two agents agreeing is two representations agreeing, which
# is how one of these findings nearly left the record twice.
findings:  ## refuse an open finding that no longer anchors to what it named
	$(RUN) python -m ops.findings

# Doctrine rule 6: "Exceptions expire. On expiry the finding returns and CI goes red again."
# This is the only target in the file that can go red on a day nobody touched the repository,
# and that is what it is for — a deferral that outlives its reason does so by the calendar,
# not by an edit. It refuses a deferred item that carries neither an unlock condition nor a
# date, in `docs/DECISIONS.md`'s own words: an item with no unlock condition is not deferred,
# it is forgotten.
expiry:  ## refuse an expired deferral, or one that never said how it ends
	$(RUN) python -m ops.expiry

# ------------------------------------------------------------------------- the claims

# A claim target proves its claim end to end: the eval, then the mutations planted to show
# that claim's gates bite. It is the only place claim 1's mutations run.
claim-1:  ## claim 1 — no price reaches a shelf without the guardrail set
	$(RUN) python -m evals.guardrail
	$(RUN) python -m evals.gate_proof --claim 1

# Claim 2 is the one that separates this from a demo. The eval runs the whole system per
# draw at K = 200 across six adversarial worlds; the mutations then run the same named checks
# at the small configuration `contracts/design/aa_harness.yaml` declares. World generation is
# outside the mutation loop -- a world is a pure function of (world, seed, scale) and a
# mutation changes eval code -- so the ten runs generate the worlds once. What invalidates
# that is a digest, not a list: see evals/uplift/cache.py.
claim-2:  ## claim 2 — no uplift without a valid holdout, and A/A holds against alpha
	$(MAKE) claim-2-tests
	$(RUN) python -m evals.uplift
	$(RUN) python -m evals.gate_proof --claim 2

# **Its own target, because in CI it is its own machine.** `ci` emits a `<target>-tests` rule as
# a separate matrix entry wherever the Makefile declares one, so this runs beside the shards
# rather than in front of the combine.
#
# Measured, which is the whole reason it moved: 1320s on a four-core runner against 306s on the
# author's laptop -- 4.3x, and the sort of gap `CLAUDE.md` says to expect between the hardware a
# number is taken on and the hardware it is met on. Sitting in `claim-2-combine` it was 1320
# seconds of a 3369-second **serial** tail, on the critical path of the whole run, behind eight
# shards that had already finished. Here it is parallel and costs the run nothing beyond one
# job of the twenty this account allows.
claim-2-tests:  ## claim 2's own tests — exactly what `make test` deselects
	$(RUN) pytest -m claim_2

#: How many machines claim 2's draws are produced on. **Declared here and nowhere else**, so
#: `ci` reads it the way it reads the target names — by grepping this file — and the workflow
#: goes on naming no claim. A second registry of which claims are sharded, kept by hand in a
#: file no test can see, is the shape `discover` exists to refuse.
#:
#: Eight, and the number is chosen by the concurrency ceiling rather than by the work: a run is
#: ten jobs today, sharding makes it `9 + N + 1`, and this account's documented ceiling is
#: twenty. Eight fits one pull request with headroom and two do not, which matches the
#: one-branch-at-a-time practice this repository already follows.
#:
#: What it buys, measured on this repository's own corpus rather than projected: eight
#: interleaved shards at 38 43 39 42 37 40 43 41 seconds, max over min **1.16**, against 270s
#: unsharded. The balance is what interleaving buys — a contiguous split would put W1's 200
#: draws on one machine at 4.8s each and a handful of W2's on another at 0.45s.
#:
#: **And `max over min` is two things added together, which the line above reads as one.** In
#: CI, warm, over two runs:
#:
#:     33577549272   237 240 244 247 254 259 262 274     max/min 1.156
#:     33581480860   147 229 229 238 242 256 258 264     max/min 1.796
#:
#: Nothing about the split changed between them. The second run drew one runner that finished
#: in 147s; its **other seven span 229-264, which is 1.15**, and the first run's eight span
#: 1.156. So the interleaving's balance is the seven-leg figure and it reproduces the laptop's
#: 1.16 on CI hardware; the max over min is that **plus whatever the fastest machine did**, and
#: over eight legs one lucky draw is enough to double it.
#:
#: The 1.16 above is a warm laptop measurement and stands as one. What it is not is a figure a
#: CI run can be compared against directly, and a session reading 1.796 off a green run should
#: not conclude the split has degraded — it should look at the seven.
#:
#: *(The first sharded CI run gave 490-973 and 1.99, and that was neither of these: every shard
#: key was cold and each leg paid its own world generation. `docs/FINDINGS.md` carries it.)*
CLAIM_2_SHARDS := 8

#: Where a shard leaves its draws and where the combine step looks for them. Never committed —
#: `.gitignore` carries it — and it holds draws rather than worlds, so it is not the world
#: cache and is not keyed like one.
SHARD_DIR ?= .shards

claim-2-shard:  ## one slice of claim 2's draws — SHARD=i/N, written to $(SHARD_DIR)
	@test -n "$(SHARD)" || { echo "claim-2-shard needs SHARD=i/N, e.g. SHARD=3/8"; exit 2; }
	$(RUN) python -m evals.uplift --shard $(SHARD) --out $(SHARD_DIR)/uplift-$(subst /,-of-,$(SHARD)).pickle

# The checks run **once, over every draw**, so sharding cannot change a rate by changing what a
# denominator is computed over. `gather` refuses a set that is not the whole one rather than
# averaging over what arrived, because `U1`'s `8/200` computed over 150 draws is still a number.
# **What it deliberately does not carry is `claim-2-tests`.** It did for one run, because CI
# never invokes `make claim-2` for a sharded target and the marked tests had to be reachable
# from something CI runs. `claim-2-tests` being its own target and its own matrix entry answers
# that without putting 1320 seconds on the serial tail; `tests/ops/test_ci_sharding.py` is what
# keeps the reachability structural rather than remembered.
claim-2-combine:  ## claim 2's checks over every shard's draws, then the mutations
	$(RUN) python -m evals.uplift --combine $(SHARD_DIR)/*.pickle
	$(RUN) python -m evals.gate_proof --claim 2

# Claim 3 is the one door with no key. The eval is seconds rather than minutes -- a chain is
# placement arithmetic and not a simulation -- so the mutations run against the eval itself,
# at the published grid, and there is no smaller configuration to keep in step.
claim-3:  ## claim 3 — the holdout is neither erased nor chosen after the fact
	$(RUN) python -m evals.assignment
	$(RUN) python -m evals.gate_proof --claim 3

eval-assignment:  ## just claim 3's eval, without the mutations
	$(RUN) python -m evals.assignment

eval-uplift:  ## just claim 2's eval, without the mutations
	$(RUN) python -m evals.uplift

# Claim 4 reads demand off a shelf that sometimes ran out. The eval fits an availability
# curve on store-days where the shelf held, grades it on a **held-out** segment of such days
# by censoring them on purpose, and compares every reconstruction against a second
# implementation that never forms a share. Three worlds at rehearsal scale, about five
# seconds; no cache, because nothing here is expensive enough to earn one.
claim-4:  ## claim 4 — a stock-out is never read as zero demand
	$(RUN) python -m evals.censoring
	$(RUN) python -m evals.gate_proof --claim 4

eval-censoring:  ## just claim 4's eval, without the mutations
	$(RUN) python -m evals.censoring

eval-guardrail:  ## just claim 1's eval, without the mutations — the fast half
	$(RUN) python -m evals.guardrail

# Claim 7 is a structural claim and therefore the cheapest target here: it imports the
# package, parses it, and plants 17,752 person-names on 56 types without touching a corpus of
# prices or generating a world. Measured on a fourteen-core laptop: the eval alone 4.0s, the
# whole target 37s — one baseline run plus seven mutated ones. **This sets no new number.** It
# runs in the `claims` matrix under a budget that was measured for claim 2, and a target two
# orders of magnitude under a timeout is not an assertion about that timeout.
#
# On four cores it is **under two minutes, on every CI run so far**. The measurements span
# **1m7s to 1m45s** — a 40% spread on work that did not change between two of them, which is the
# same runner variance T000 measured at 11m00s against 15m16s on an identical commit. How many
# measurements there are is deliberately not written down: that count grows with every push, so
# stating it would guarantee this line is stale again by the next one.
#
# The bound is the assertion; the span is evidence for it, not a second assertion. This line
# has been wrong three times as a point estimate — 1m8s, left standing after a seventh mutation
# landed; "1m33s and 1m41s", overtaken when merging claims 3 and 4 grew the registry, since
# every type added to it adds 317 attacks; and then "1m32s to 1m45s", falsified by the very
# next run coming in *faster*. A quantity with two independent reasons to move should be
# asserted as a bound with room in it, never as a point and never as a tight range.
claim-7:  ## claim 7 — a decision that targets a person is structurally impossible
	$(RUN) python -m evals.oversight
	$(RUN) python -m evals.gate_proof --claim 7

eval-oversight:  ## just claim 7's eval, without the mutations — about four seconds
	$(RUN) python -m evals.oversight

# The ledger, not the executor. Each claim target plants its own mutations, so this one
# runs nothing and instead checks the arrangement: every mutation owned by exactly one
# claim target, no orphan, no duplicate, no claim target with nothing planted against it.
# Before this split, `claim-1` and `gate-proof` both ran claim 1's thirteen mutations and
# CI spent thirteen minutes proving the same thing twice.
gate-proof:  ## audit mutation ownership — every planted break owned by exactly one claim
	$(RUN) python -m evals.gate_proof

# The counterpart of `corpus` below, and the rule is the opposite one. `corpus/real/` is
# committed because it cannot be regenerated — a person wrote those prices down in a shop.
# `corpus/world/` is never committed because it can: a world is a pure function of
# (world, seed, scale). This target is the smoke-scale proof that all six still produce data;
# the scenario scale takes minutes and is a command in corpus/world/README.md, not a target.
world:  ## generate all six adversarial worlds at smoke scale and count what came out
	@for w in W1 W2 W3 W4 W5 W6; do \
	  $(RUN) python -m corpus.world count --world $$w --scale smoke; \
	done

# The number CLAUDE.md now says decides whether anything is provable: not how many stores
# the estate has, but how many an experiment may still draw a lottery over once the design
# engine's automatic neighbour exclusions have run. It is a joint fact about the corpus's
# geography and the engine's rule, so it lives in `ops/` — the corpus may not import the
# system, and a second copy of the exclusion rule inside `corpus/` would be the one that
# goes stale. A measurement, not a gate: it asserts nothing and always exits 0.
roster:  ## how much of the estate survives the automatic exclusions, per world
	$(RUN) python -m ops.roster --scale harness

corpus:  ## rebuild corpus/real/data from the sources MANIFEST.yaml cites — NEEDS THE NETWORK
	@echo "This downloads ~100 MB from the ONS. CI never runs it; the committed data is"
	@echo "digest-checked by tests/corpus/test_manifest.py instead."
	$(RUN) python corpus/real/fetch.py

clean:  ## remove tooling caches
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
