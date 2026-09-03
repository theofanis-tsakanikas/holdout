-- GENERATED FILE — DO NOT EDIT
-- source:     contracts/metrics/units_sold_per_store_week.v1.yaml
-- generator:  holdout.contracts.compilers.readout
-- regenerate: make contracts
--
-- `make contracts` recompiles this file and fails the build if what is on disk
-- differs, so an edit here does not survive and does not go unnoticed either.

-- readout: units_sold_per_store_week@v1 — unit units, rounded half_even to 0 decimals
--
-- parameters
--   :experiment_id  the experiment whose assignment is read
--   :data_version_gold_decision_economics
--                   the Delta version gold.decision_economics is pinned to. **One parameter
--                   per relation**: a Delta version counter is per table, so one
--                   number cannot index two of them. Without the pin, re-running
--                   last month's readout returns a different number as late data
--                   arrives.
--   :data_version_gold_experiment_assignment
--                   the Delta version gold.experiment_assignment is pinned to.
--   :period_start   inclusive, the declared opening of the comparison window
--   :period_end     exclusive, the declared close. Reading before it is blocked by the
--                   engine, not by this query.

with s as (
    select
        store_id,
        iso_week,
        category,
        sum(cast(qty as decimal(38, 6))) as term_0
    from gold.decision_economics version as of :data_version_gold_decision_economics
    group by store_id, iso_week, category
),

metric as (
    select
        s.store_id,
        s.iso_week,
        s.category,
        'units_sold_per_store_week' as metric_id,
        1 as metric_version,
        bround(coalesce(s.term_0, 0), 0) as metric_value
    from s
),

assignment as (
    select
        store_id,
        arm,
        assigned_at,
        seed
    from gold.experiment_assignment version as of :data_version_gold_experiment_assignment
    where experiment_id = :experiment_id
)

select
    a.arm,
    m.store_id, m.iso_week, m.category,
    m.metric_id,
    m.metric_version,
    m.metric_value
from metric m
join assignment a
  on a.store_id = m.store_id
where m.iso_week >= :period_start
  and m.iso_week <  :period_end
order by a.arm, m.store_id, m.iso_week, m.category
