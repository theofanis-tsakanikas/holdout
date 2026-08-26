-- GENERATED FILE — DO NOT EDIT
-- source:     contracts/metrics/units_sold_per_store_week.v1.yaml
-- generator:  holdout.contracts.compilers.sql_function
-- regenerate: make contracts
--
-- `make contracts` recompiles this file and fails the build if what is on disk
-- differs, so an edit here does not survive and does not go unnoticed either.

-- metric: units_sold_per_store_week@v1 — unit units, rounded half_even to 0 decimals

create or replace function ${catalog}.metrics.units_sold_per_store_week_v1()
returns table (store_id string, iso_week string, category string, metric_id string, metric_version int, metric_value bigint)
return
    with s as (
        select
            store_id,
            iso_week,
            category,
            sum(cast(qty as decimal(38, 6))) as term_0
        from gold.decision_economics
        group by store_id, iso_week, category
    )

    select
        s.store_id,
        s.iso_week,
        s.category,
        'units_sold_per_store_week' as metric_id,
        1 as metric_version,
        bround(coalesce(s.term_0, 0), 0) as metric_value
    from s;
