-- GENERATED FILE — DO NOT EDIT
-- source:     contracts/metrics/waste_value_per_store_week.v1.yaml
-- generator:  holdout.contracts.compilers.sql_function
-- regenerate: make contracts
--
-- `make contracts` recompiles this file and fails the build if what is on disk
-- differs, so an edit here does not survive and does not go unnoticed either.

-- metric: waste_value_per_store_week@v1 — unit EUR, rounded half_even to 2 decimals

create or replace function ${catalog}.metrics.waste_value_per_store_week_v1()
returns table (store_id string, iso_week string, category string, metric_id string, metric_version int, metric_value decimal(18, 2))
return
    with w as (
        select
            store_id,
            iso_week,
            category,
            sum(cast(qty * unit_cost_as_of as decimal(38, 6))) as term_0
        from gold.waste
        group by store_id, iso_week, category
    )

    select
        w.store_id,
        w.iso_week,
        w.category,
        'waste_value_per_store_week' as metric_id,
        1 as metric_version,
        bround(coalesce(w.term_0, 0), 2) as metric_value
    from w;
