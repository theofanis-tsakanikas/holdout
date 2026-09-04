-- GENERATED FILE — DO NOT EDIT
-- source:     contracts/metrics/units_sold_per_store_week.v1.yaml
-- generator:  holdout.contracts.compilers.dbt
-- regenerate: make contracts
--
-- `make contracts` recompiles this file and fails the build if what is on disk
-- differs, so an edit here does not survive and does not go unnoticed either.

-- metric:   units_sold_per_store_week@v1
-- grain:    store_id, iso_week, category
-- unit:     units
-- rounding: half_even, 0 decimals (SQL bround)

{{ config(
    materialized='table',
    tags=['metric', 'units_sold_per_store_week'],
) }}

with s as (
    select
        store_id,
        iso_week,
        category,
        sum(cast(qty as decimal(38, 6))) as term_0
    from {{ ref('decision_economics') }}
    group by store_id, iso_week, category
)

select
    s.store_id,
    s.iso_week,
    s.category,
    'units_sold_per_store_week' as metric_id,
    1 as metric_version,
    bround(coalesce(s.term_0, 0), 0) as metric_value
from s
