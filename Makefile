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
# Still deliberately absent: `claim-2` … `claim-7` and `preview-audit`. A green target that
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
        expiry claim-1 eval-guardrail gate-proof corpus clean

help:  ## show this help
	@grep -hE '^[a-z][a-zA-Z0-9_-]*:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[1m%-16s\033[0m %s\n", $$1, $$2}'

setup:  ## create the virtualenv and install everything
	$(UV) sync

setup-locked:  ## install exactly what uv.lock pins — what CI runs, and what refuses a drifted lock
	$(UV) sync --locked

check: lint typecheck contracts expiry test  ## the whole local gate, in the order that fails fastest
	@echo ""
	@echo "OK      lint · typecheck · contracts · expiry · tests"
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

test:  ## the suite
	$(RUN) pytest

contracts:  ## validate every contract and refuse a stale or hand-edited generated artefact
	$(RUN) holdout-contracts check

contracts-write:  ## recompile every consumer and write it to generated/
	$(RUN) holdout-contracts compile

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

eval-guardrail:  ## just claim 1's eval, without the mutations — the fast half
	$(RUN) python -m evals.guardrail

# The ledger, not the executor. Each claim target plants its own mutations, so this one
# runs nothing and instead checks the arrangement: every mutation owned by exactly one
# claim target, no orphan, no duplicate, no claim target with nothing planted against it.
# Before this split, `claim-1` and `gate-proof` both ran claim 1's thirteen mutations and
# CI spent thirteen minutes proving the same thing twice.
gate-proof:  ## audit mutation ownership — every planted break owned by exactly one claim
	$(RUN) python -m evals.gate_proof

corpus:  ## rebuild corpus/real/data from the sources MANIFEST.yaml cites — NEEDS THE NETWORK
	@echo "This downloads ~100 MB from the ONS. CI never runs it; the committed data is"
	@echo "digest-checked by tests/corpus/test_manifest.py instead."
	$(RUN) python corpus/real/fetch.py

clean:  ## remove tooling caches
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
