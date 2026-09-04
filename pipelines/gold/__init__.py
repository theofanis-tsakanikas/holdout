"""Gold — the business facts, the experiment's assignment table, and the metric contract's
consumers actually running.

`CLAUDE.md` gives gold four families and this layer builds two of them:

=====  ===================================================================  =============
`A`    `decision_economics` · `waste` · `store_day`                         two of three
`B`    `demand_features` — point-in-time correct                            not built
`C`    `experiment_assignment` · `exposure` · `outcomes` · `readout`        two of four
`D`    `decisions` — immutable, written at decision time                    not built
=====  ===================================================================  =============

**What is absent is absent on purpose and `T011` names neither.** `closes` asks for the metric
contract's three consumers, the assignment table and the pinned readout, and nothing else.
`store_day` has no consumer yet; `demand_features` belongs to `T014`, which is the training code
and is where point-in-time correctness has something to be correct *for*; `exposure` and
`outcomes` are collected by a running experiment, which is `run` in phase 3; `decisions` is
written by the decision path at decision time into Lakebase, and a gold table built from a
corpus that never took a decision would be a table of nothing. **Building an empty one to
satisfy an expectation about the word *gold* is worse than an absence with a reason.**

The one rule this layer is really about
---------------------------------------
`CLAUDE.md` rule 3: **a contract compiles; it is never interpreted by hand-written code in two
places.** The three consumers already exist under `generated/` and `make contracts` byte-compares
every one of them on every run. So the failure this layer had to avoid is not that it does not
work — it is that it quietly contains a **second** definition of something the contract already
defines.

**It contains none, and that is structural rather than maintained.** `dbt_project.yml` reaches
the generated models through `model-paths`, which dbt accepts outside its own project directory:

    model-paths: ["models", "../../generated/dbt/models"]

**There is no copy to go stale.** The alternative — copying `generated/dbt/models/metrics/*.sql`
into this package and keeping the copies equal — would have needed a gate of its own, and a gate
that maintains an equality is weaker than an arrangement in which the equality cannot be broken.
`tests/pipelines/test_gold.py` asserts the absence rather than the equality: nothing under
`pipelines/` duplicates a path under `generated/`.

Where the split between dbt and Python falls, and why it is not where it looks
------------------------------------------------------------------------------
`CLAUDE.md` names dbt as the silver → gold engine. **dbt owns everything downstream of the as-of
join**: the two business-fact tables' shaping, and the three compiled metric models on top of
them. **Python owns the as-of join itself**, because `pipelines/silver/tables.py::cost_as_of`
already is that join, tested, and *"a sale at 14:00 joins to the cost as it was known at 14:00"*
written a second time in SQL would be one rule in two implementations — the same defect the
contract layer exists to refuse, one layer down and with no compiler to catch it.

So `facts.py` applies `cost_as_of` and writes `gold.priced_sales` and `gold.priced_waste`; the
dbt models read those as sources and do the projection, the cents-to-euro conversion and the ISO
week. **Gold is the first production caller `cost_as_of` has ever had** — until now it was
written, tested, and invoked by nothing outside its own tests.

What is proved here and what is not
-----------------------------------
**Proved local:** the generated dbt models parse and run on Spark against Delta tables; the
readout query returns the same number after late data arrives when it is pinned and a different
one when it is not; the assignment table refuses an update, a delete and an overwrite at the
storage layer; and the digest catches the edit the storage layer allows.

**Not proved:** anything about Databricks. The relations are bound in a local metastore rather
than in Unity Catalog, `${catalog}` is never substituted, and the SQL table function — the one
compiled consumer that is a catalog object — is still text no engine has read. `docs/DECISIONS.md`
carries what remains of *"The generated SQL has never been executed"* after this branch.
"""
