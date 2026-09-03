-- Gold family A. What was thrown away, valued at the cost known on the day of disposal.
--
-- Same three operations as `decision_economics` and the same two reasons for each. The column is
-- `wasted_qty` in silver and `qty` here, because the metric contract names its measure `qty` on
-- both sources -- `sum(w.qty * w.unit_cost_as_of)` -- and a model that renamed it anywhere else
-- would be the compiled artefact referencing a column no CTE selects.
--
-- `business_date` is a string in the corpus's own shape, so it is cast with `to_date` rather
-- than left to an implicit conversion that differs between engines.
select
    store_id,
    concat(
        lpad(cast(extract(YEAROFWEEK from to_date(business_date)) as string), 4, '0'),
        '-W',
        lpad(cast(weekofyear(to_date(business_date)) as string), 2, '0')
    ) as iso_week,
    category,
    wasted_qty as qty,
    cast(unit_cost_as_of as decimal(18, 4)) / 100 as unit_cost_as_of
from {{ source('priced', 'priced_waste') }}
where unit_cost_as_of is not null
