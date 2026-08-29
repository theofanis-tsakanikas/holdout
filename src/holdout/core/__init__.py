"""The framework-free core.

Every module under this package is a pure function over plain data. Nothing here imports
a cloud SDK, an engine, a serialisation library or a schema validator — not `boto3`, not
`databricks`, not `pyspark`, not `dbt`, not `yaml`, not `jsonschema`. That restriction is
what makes every claim provable local, on a laptop or in CI, with no workspace and no
credentials, and it is enforced by a test rather than by good intentions
(`tests/boundary/test_core_imports_nothing.py`).

The boundary with the contract layer
------------------------------------
`contracts/` is the source of truth and `holdout.contracts` is the only thing that reads
it. That package owns the YAML parsing and the JSON Schema validation; this package never
sees either. What crosses the boundary is `holdout.contracts.model` — frozen dataclasses
over stdlib types only, importable with `yaml` and `jsonschema` absent from the
interpreter entirely.

So a core function takes the resolved contract it needs as an argument:

    def certify(proposed: ProposedPrice, envelope: tuple[GuardrailWindow, ...]) -> ...

and never `def certify(proposed, contracts_dir)`. A core function that had to find, read or
parse a contract would be a core function that could not run without a filesystem layout,
and the adapters exist precisely so that it does not have to.

Two more rules, enforced by the same test
-----------------------------------------
**Determinism.** No clock, no environment, no random source. Time is an argument. A
guardrail whose answer depends on when it was asked cannot be replayed, and a decision that
cannot be replayed cannot be checked a year later.

**Money is an integer number of cents.** Never a binary float — see `holdout.core.money`
for the argument. A float literal, a `float` annotation and a call to `float()` are all
refused anywhere in this package.

What is here
------------
=================  ============================================================
`money`            integer minor units, three roundings because a bound is not a
                   price, and the one exact rational-to-decimal conversion
`hashing`          length-prefixed canonical bytes and a `blake2b` digest, so no
                   two different sequences ever encode to the same thing
`decision`         the decision key (claim 7), the two paths, and the safe state
                   neither path may inherit from the other
`demand/`          reading demand off a shelf that sometimes ran out, so a
                   stock-out is never read as zero — claim 4
`guardrails/`      the envelope and the certificate type — claim 1
`ladder/`          the deterministic markdown fallback, the markdown path's
                   declared safe state
`pricing/`         scenario selection: the model returns a table, code picks the
                   row by arithmetic
`design/`          the nine-field form and the feasibility engine — moment 1,
                   *can this experiment exist?*, and the eight refusals
`experiment/`      the committed lottery and its seal, the four validity checks,
                   and the design-based estimator — moments 2 and 3
=================  ============================================================

Exactness, and the two representations that carry it
----------------------------------------------------
`Money` is an integer number of cents and a percentage is a `Decimal`; that is the pricing
half. The experiment half adds one more: **an outcome is an integer at the metric's declared
scale and every statistic over it is a `Fraction`.** Sums stay integers, the only division is
into a mean, and `Decimal.sqrt()` appears exactly where a figure is printed for a human. The
result is that a p-value, a confidence interval and a standardised difference are
bit-identical on every machine — which is what lets an experiment be re-read a year later and
argued with rather than re-run.

Still to come, in the branches that build them: the generator and its six adversarial worlds,
the A/A harness at K = 200, and the evals that turn any of this into a proved claim. **Nothing
in this package proves a claim on its own.** It makes them provable.
"""
