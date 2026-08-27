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

#: Everything that is Python and is ours. `evals/` and `corpus/` are linted and type-checked
#: exactly as `src/` is: an eval is the evidence a claim rests on, and evidence held to a
#: lower standard than the code it judges is not evidence for long.
PYTHON_DIRS := src tests evals corpus

.DEFAULT_GOAL := help
.PHONY: help setup setup-locked check test lint format typecheck contracts contracts-write \
        claim-1 eval-guardrail gate-proof corpus clean

help:  ## show this help
	@grep -hE '^[a-z][a-zA-Z0-9_-]*:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[1m%-16s\033[0m %s\n", $$1, $$2}'

setup:  ## create the virtualenv and install everything
	$(UV) sync

setup-locked:  ## install exactly what uv.lock pins — what CI runs, and what refuses a drifted lock
	$(UV) sync --locked

check: lint typecheck contracts test  ## the whole local gate, in the order that fails fastest
	@echo ""
	@echo "OK      lint · typecheck · contracts · tests"
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

# ------------------------------------------------------------------------- the claims

claim-1:  ## claim 1 — no price reaches a shelf without the guardrail set
	$(RUN) python -m evals.guardrail
	$(RUN) python -m evals.gate_proof --claim 1

eval-guardrail:  ## just claim 1's eval, without the mutations — the fast half
	$(RUN) python -m evals.guardrail

gate-proof:  ## break every gate on purpose and demand a refusal from the gate that is named
	$(RUN) python -m evals.gate_proof

corpus:  ## rebuild corpus/real/data from the sources MANIFEST.yaml cites — NEEDS THE NETWORK
	@echo "This downloads ~100 MB from the ONS. CI never runs it; the committed data is"
	@echo "digest-checked by tests/corpus/test_manifest.py instead."
	$(RUN) python corpus/real/fetch.py

clean:  ## remove tooling caches
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
