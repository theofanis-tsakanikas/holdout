"""Claim 5 — one definition, three mechanisms, the same integer.

`CLAIM_5` as `CLAUDE.md` states it: *the source of truth is the contract in this repository,
compiled into a Delta view, the agent's tool definition and the experiment readout. Compared as
integers, no tolerance. Trap: two consumers calling the same function prove nothing → three
genuinely different mechanisms, sharing only the definition.*

**The three named consumers are one mechanism, and that is measured rather than argued.**
`compile_dbt_model`, `compile_sql_function` and `compile_readout` all call `metric_parts` in
`holdout/contracts/compilers/sql.py`; normalising away relation names and the version clause,
their arithmetic is byte-identical:

    sum(cast(qty * price_paid      as decimal(38, 6))) as term_0
    sum(cast(qty * unit_cost_as_of as decimal(38, 6))) as term_1
    sum(cast(qty * unit_cost_as_of as decimal(38, 6))) as term_2
    bround(coalesce(s.term_0,0) - coalesce(s.term_1,0) - coalesce(w.term_2,0), 2)

A bug in `combine()` or in the `decimal(38, 6)` cast appears identically in all three and
**cancels in every comparison between them**. Comparing them proves Spark is deterministic. It is
claim 5's own trap with a bigger number: *two consumers calling the same function prove nothing*
becomes three consumers calling the same **renderer**.

**And the fourth named consumer cannot be a mechanism at all.** The agent tool definition is JSON
declaring grain, unit, rounding and canonical scale. It computes nothing, so it has no number of
its own to compare — what it can be checked for is agreeing with the contract about those four
things, which is `D4` below and is not an arithmetic claim.

So the three are
----------------
=========================  ==========================================================
the compiled SQL           executed by Spark over the gold tables `T011` builds
`aggregate_then_combine`   sum each term per cell, combine the sums, round once
`combine_then_aggregate`   combine each row, sum the contributions, round once
=========================  ==========================================================

**They share `contracts/metrics/*.yaml` and nothing else.** The two Python paths may not share a
line and neither may their parents — `tests/evals/test_definition_independence.py` enforces it on
the import graph, the same way `evals/uplift/`'s pair is enforced.

The population is held fixed, and the drop is its own number
------------------------------------------------------------
**All three read what the contract declares its sources to be** — `gold.decision_economics` and
`gold.waste`. The `where unit_cost_as_of is not null` that shapes the first of those lives in the
dbt model that **builds** it, upstream of every mechanism, and arrives as materialised rows rather
than as logic. **No mechanism imports another's filtering.**

Feeding three mechanisms three different row sets would test the definition *and* the pipeline
*and* the drop rule at once, and a disagreement would name none of them. So the drop is reported
**beside** the comparison and never inside it: it is a property of the pipeline, established in
`T010` and `T011`, and it is `D5`.

What this does not prove
------------------------
**Non-sharing prevents shared code. It does not prevent a shared misconception.** The two Python
paths were written by one session in one sitting and could both misread the contract the same
way; every mutation would pass and the integers would agree.

**The SQL is the load-bearing third for exactly that reason** — compiled from the same contract by
a different mechanism, at a different time, for a different purpose. The Python pair mostly guards
the arithmetic; the SQL guards the reading. **A reader who sees three mechanisms should not assume
all three are equally independent.**
"""
