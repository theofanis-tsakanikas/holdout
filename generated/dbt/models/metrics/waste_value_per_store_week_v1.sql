-- GENERATED FILE — DO NOT EDIT
-- source:     contracts/metrics/waste_value_per_store_week.v1.yaml
-- generator:  holdout.contracts.compilers.dbt
-- regenerate: make contracts
--
-- `make contracts` recompiles this file and fails the build if what is on disk
-- differs, so an edit here does not survive and does not go unnoticed either.

-- metric:   waste_value_per_store_week@v1
-- grain:    store_id, iso_week, category
-- unit:     EUR
-- rounding: half_even, 2 decimals (SQL bround)

{{ config(
    materialized='table',
    tags=['metric', 'waste_value_per_store_week'],
) }}

with w as (
    select
        store_id,
        iso_week,
        category,
        sum(cast(qty * unit_cost_as_of as decimal(38, 6))) as term_0
    from {{ ref('waste') }}
    group by store_id, iso_week, category
)

select
    w.store_id,
    w.iso_week,
    w.category,
    'waste_value_per_store_week' as metric_id,
    1 as metric_version,
    bround(coalesce(w.term_0, 0), 2) as metric_value
from w
