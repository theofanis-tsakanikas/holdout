"""Ops and method — the code that enforces the rules the product code is measured by.

Nothing here serves one of the seven claims, and that is deliberate: this is the layer that
makes a *rule* structural rather than advisory. `ops.isolation` is the corpus barrier, shared
by the boundary test and by the harness hook so the two cannot drift apart. `ops.expiry` is
doctrine rule 6 — exceptions expire — as a Makefile target rather than a paragraph.

It is kept out of `src/holdout/` on purpose. `src/holdout/` is the system whose decisions are
being proved; a checker that shipped inside it would be one more thing the claims have to be
independent of.
"""
