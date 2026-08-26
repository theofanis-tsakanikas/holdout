-- GENERATED FILE — DO NOT EDIT
-- source:     contracts/metrics/waste_value_per_store_week.v1.yaml
-- generator:  holdout.contracts.compilers.readout
-- regenerate: make contracts
--
-- `make contracts` recompiles this file and fails the build if what is on disk
-- differs, so an edit here does not survive and does not go unnoticed either.

-- readout: waste_value_per_store_week@v1 — unit EUR, rounded half_even to 2 decimals
--
-- parameters
--   :experiment_id  the experiment whose assignment is read
--   :data_version   the Delta version every source is pinned to, so the number is
--                   reproducible after late data has arrived
--   :period_start   inclusive, the declared opening of the comparison window
--   :period_end     exclusive, the declared close. Reading before it is blocked by the
--                   engine, not by this query.

with w as (
    select
        store_id,
        iso_week,
        category,
        sum(cast(qty * unit_cost_as_of as decimal(38, 6))) as term_0
    from gold.waste version as of :data_version
    group by store_id, iso_week, category
),

metric as (
    select
        w.store_id,
        w.iso_week,
        w.category,
        'waste_value_per_store_week' as metric_id,
        1 as metric_version,
        bround(coalesce(w.term_0, 0), 2) as metric_value
    from w
),

assignment as (
    select
        store_id,
        arm,
        assigned_at,
        seed
    from gold.experiment_assignment version as of :data_version
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
