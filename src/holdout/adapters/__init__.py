"""Thin cloud callers.

An adapter finds things, authenticates, serialises and calls. It holds no domain logic:
anything with exactly one correct answer belongs in `holdout.core`, where it can be proved
with no account. Deliberately empty until there is something to call.

**One seam is already named, so that it is not invented twice.** Validating a submitted
experiment design against `generated/design/form.schema.json` belongs here and nowhere else:
`holdout.core.design.form` mirrors the schema as frozen dataclasses and may not import
`jsonschema`, so the parse and the shape check happen at this boundary and a form reaches the
engine already valid. The same boundary is where a `number` from JSON becomes the `Decimal`
that `Mde.value` requires, and where an absent `mde.direction` — which the schema's own
description defines as *no one-sided expectation was declared* — becomes `either`.
"""
