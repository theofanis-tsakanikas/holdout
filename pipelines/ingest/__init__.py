"""What moves a chain's own events into bronze, with the pathologies a real one has.

`CLAUDE.md`'s bronze layer is *"one table per source, in the source's shape"*, and nothing is
transformed at ingestion. This package does not transform anything either. It does the one
thing the generator deliberately refuses to do: **decide when a record arrives.**

**It serves no claim, and that is written here rather than left to be inferred.** Claims 1 to 7
are proved by `evals/`, and none of them is proved by this package. What it produces is the
*input* the silver and gold layers are built on, and the pathologies it injects are what makes
those layers' handling of lateness, duplication and out-of-order delivery testable at all. A
module that serves no claim and says so is a different object from one that serves no claim and
does not — `docs/reviews/phase-1.md` §4 is open against the second kind.
"""
