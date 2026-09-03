"""Two paths into bronze: the events of a live day, and the files a backfill leaves on S3.

**The driver** (`driver.py`, `sink.py`) is the live day: a chain's own events, in arrival
order, with the pathologies a real one has. **The bulk load** (`erp.py`, `bulk.py`) is the
other half of `CLAUDE.md`'s sources table — the eight months of history and the ERP's master
data, both arriving as files on S3, several times a day for the second one. They meet nowhere
and share nothing but this package: one decides *when a record arrives*, the other decides
*whether a file has already been taken*.

The second path replaced a connector. The author ruled on 2026-09-02 that the ERP's master
data arrives as files rather than through Lakeflow Connect, whose gateway runs continuously on
classic compute — so what is demonstrated here is **incremental load of successive drops, not
change capture against a live source**, which is smaller, deliberate, and written as smaller in
`bulk.py`.

`CLAUDE.md`'s bronze layer is *"one table per source, in the source's shape"*, and nothing is
transformed at ingestion. This package does not transform anything either. It does the two
things the generator deliberately refuses to do: **decide when a record arrives**, and **decide
what an ERP knew at the moment it exported.**

**It serves no claim, and that is written here rather than left to be inferred.** Claims 1 to 7
are proved by `evals/`, and none of them is proved by this package. What it produces is the
*input* the silver and gold layers are built on: the pathologies the driver injects are what
makes those layers' handling of lateness, duplication and out-of-order delivery testable at
all, and the drops are what gives the declared decision-path trigger *"a cost change in the ERP
that moved the floor"* something to fire on. A module that serves no claim and says so is a
different object from one that serves no claim and does not — `docs/reviews/phase-1.md` §4 is
open against the second kind.

**One thing here is load-bearing for a claim, in the negative.** The ERP export withholds the
`arm` column, because master data that carried it would let a downstream join take a store's
arm from bronze rather than from the assignment written before the period opened. That is claim
3's door, and a column is a way through it.
"""
