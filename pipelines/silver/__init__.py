"""Silver — one table per question, and the one place a bad row is kept rather than dropped.

`CLAUDE.md`'s silver layer is five tables — `sales · shelf_state · price_displayed · reference ·
quarantine` — and it is deliberately not one-to-one with bronze: `reference` collapses the ERP's
tables into one **as-of queryable** dimension, and `pos_lines` feeds two silver tables because a
sale is both revenue and an inventory movement.

The quarantine is written by hand, and that is a finding rather than a preference
--------------------------------------------------------------------------------
`CLAUDE.md`'s engine table chose Spark Declarative Pipelines for this layer because *"streaming,
out-of-order, expectations and quarantine are native"*. **Expectations are native to Databricks
Lakeflow, which extends the open-source framework. They are not in the framework this repository
runs.** Measured by printing the installed package rather than by reading a page about it:

    pyspark.pipelines 4.2.0 public API
      api · append_flow · create_auto_cdc_flow · create_sink · create_streaming_table ·
      flow · graph_element_registry · materialized_view · output · source_code_location ·
      table · temporary_view · type_error_utils

    anything expectation-shaped: []

`table`, `materialized_view`, `create_streaming_table` and `append_flow` take no constraint
argument, and the only file in the installed distribution matching *expectations* is
`pyspark/pandas/frame.py`, which is a different API entirely.

**So `expectations.py` exists**, and it is eleven lines of predicate over a DataFrame rather than
a framework feature. What it is not is a reimplementation of something available here: on the
estate the same rows would route through Lakeflow's own mechanism, and the definitions in
`pipeline.py` are the ones Databricks runs. **The gap is between the OSS framework and the
product, and it is stated here rather than papered over by calling ours a design choice.**

What each table answers
-----------------------
=================  ==========================================================================
`sales`            what was sold, deduplicated on the business key the POS supplies
`price_displayed`  what the shelf actually showed — from the acknowledgement, never the decision
`shelf_state`      whether the shelf emptied, and when, **derived from movements**
`reference`        the cost as it was known at a moment, on both of its time axes
`quarantine`       every row an expectation refused, with the reason and the key
=================  ==========================================================================

**It serves no claim**, like `pipelines/ingest/`, and says so for the same reason: claims 1 to 7
are proved by `evals/`, and this is the layer they are eventually computed over rather than
evidence itself. The one exception is negative — `reference` is where *"a sale at 14:00 joins to
the cost as it was known at 14:00"* stops being a sentence in `CLAUDE.md` and becomes a join, and
getting it wrong would silently rewrite every historical margin.
"""
