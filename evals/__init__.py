"""One directory per claim, and the shape they all share.

`evals/report.py` defines that shape: named checks with stable ids, a falsifiable question
each, a published number whether or not anything failed, and a JSON reading that
`make gate-proof` consumes. `evals/README.md` argues why each of those is there.

An eval is not a test. The suite under `tests/` asks whether a module does what its author
meant; an eval asks whether a **claim in CLAUDE.md is true**, on inputs its author did not
choose, and it publishes the numbers rather than a tick.
"""
