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

This package is deliberately empty in the branch that created it. It is filled by the
branches that build the guardrail certificate, the scenario selection arithmetic, the
ladder, the design engine, the assignment and the estimator.
"""
