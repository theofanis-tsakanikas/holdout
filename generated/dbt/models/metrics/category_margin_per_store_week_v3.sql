-- GENERATED FILE — DO NOT EDIT
-- source:     contracts/metrics/category_margin_per_store_week.v3.yaml
-- generator:  holdout.contracts.compilers.dbt
-- regenerate: make contracts
--
-- `make contracts` recompiles this file and fails the build if what is on disk
-- differs, so an edit here does not survive and does not go unnoticed either.

-- metric:   category_margin_per_store_week@v3
-- grain:    store_id, iso_week, category
-- unit:     EUR
-- rounding: half_even, 2 decimals (SQL bround)

{{ config(
    materialized='table',
    tags=['metric', 'category_margin_per_store_week'],
) }}

with s as (
    select
        store_id,
        iso_week,
        category,
        sum(cast(qty * price_paid as decimal(38, 6))) as term_0,
        sum(cast(qty * unit_cost_as_of as decimal(38, 6))) as term_1
    from {{ ref('decision_economics') }}
    group by store_id, iso_week, category
),

w as (
    select
        store_id,
        iso_week,
        category,
        sum(cast(qty * unit_cost_as_of as decimal(38, 6))) as term_2
    from {{ ref('waste') }}
    group by store_id, iso_week, category
),

grain as (
    select store_id, iso_week, category from s
    union
    select store_id, iso_week, category from w
)

select
    g.store_id,
    g.iso_week,
    g.category,
    'category_margin_per_store_week' as metric_id,
    3 as metric_version,
    bround(coalesce(s.term_0, 0) - coalesce(s.term_1, 0) - coalesce(w.term_2, 0), 2) as metric_value
from grain g
left join s on s.store_id = g.store_id and s.iso_week = g.iso_week and s.category = g.category
left join w on w.store_id = g.store_id and w.iso_week = g.iso_week and w.category = g.category
