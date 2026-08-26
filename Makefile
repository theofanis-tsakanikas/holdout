# Holdout — the local gate.
#
# Everything here runs on a laptop or in CI with no cloud account and no credentials.
# That is not a convenience: it is the only reason the claims are checkable by anyone who
# clones the repository.
#
# `make check` is what CI runs and what a session runs before it commits.
#
# Deliberately absent: `claim-1` … `claim-7`, `gate-proof` and `preview-audit`. They are
# named in CLAUDE.md and they belong here, one target per claim, because a claim that is a
# Makefile target is a structural gate and a claim that is a paragraph is advice. They are
# absent because nothing in this repository proves them yet, and a green target that proves
# nothing is worse than a missing one — it is a gate that has been disarmed before it was
# ever armed. Each arrives with the eval that earns it.

UV ?= uv
RUN := $(UV) run

.DEFAULT_GOAL := help
.PHONY: help setup check test lint format typecheck contracts contracts-write clean

help:  ## show this help
	@grep -hE '^[a-z][a-zA-Z0-9_-]*:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[1m%-16s\033[0m %s\n", $$1, $$2}'

setup:  ## create the virtualenv and install everything
	$(UV) sync

check: lint typecheck contracts test  ## the whole local gate, in the order that fails fastest
	@echo ""
	@echo "OK      lint · typecheck · contracts · tests"

lint:  ## ruff, as a linter and as a formatting check
	$(RUN) ruff check src tests
	$(RUN) ruff format --check src tests

format:  ## ruff, rewriting
	$(RUN) ruff format src tests
	$(RUN) ruff check --fix src tests

typecheck:  ## mypy, strict
	$(RUN) mypy

test:  ## the suite
	$(RUN) pytest

contracts:  ## validate every contract and refuse a stale or hand-edited generated artefact
	$(RUN) holdout-contracts check

contracts-write:  ## recompile every consumer and write it to generated/
	$(RUN) holdout-contracts compile

clean:  ## remove tooling caches
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
