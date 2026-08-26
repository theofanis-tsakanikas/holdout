"""The contract layer — the only code that reads `contracts/`.

`contracts/` is the source of truth for claims 1, 5 and 6, and this package is the single
door to it. It owns the YAML parsing and the JSON Schema validation, and it is the only
place in the repository allowed to import `yaml` or `jsonschema`.

Deliberately empty of imports. Importing the loader from here would drag the parser into
every module that only wanted a type, and `holdout.core` must be able to take a
`GuardrailWindow` in an interpreter where neither library is installed. So the submodules
are imported explicitly:

    from holdout.contracts.model import Guardrail, Rounding   # stdlib only, safe anywhere
    from holdout.contracts.windows import resolve_as_of       # stdlib only, safe anywhere
    from holdout.contracts.loader import load                 # yaml + jsonschema
    from holdout.contracts.compilers import compile_all       # generation

A test enforces the first two by blocking `yaml` and `jsonschema` from `sys.modules` and
importing them anyway.
"""
