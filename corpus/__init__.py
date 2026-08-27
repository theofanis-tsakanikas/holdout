"""Data this repository did not generate, and data it did — kept strictly apart.

Two subpackages, one rule that governs both:

* `corpus/real/` — public retail data published by a statistical office and a government
  gazette. It is what claim 1's eval attacks the guardrails with.
* `corpus/world/` — the generator and the six adversarial worlds behind claim 2. Not on
  this branch.

**No module under `corpus/` imports anything from `holdout`.** For `corpus/world/` that is
CLAUDE.md's stated barrier: a generator sharing a "compute margin" function with the
estimator would cancel a bug in it and both would agree on a wrong number. For
`corpus/real/` the argument is the same one a sentence earlier: a corpus that can reach the
gates it is meant to attack stops being independent of them. `tests/boundary/` enforces it
for the whole package, so neither has to remember.
"""
