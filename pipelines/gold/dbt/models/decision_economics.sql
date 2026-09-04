-- Gold family A. The revenue side of the margin, at the grain every metric contract declares.
--
-- This model does three things and none of them is a join: it projects, it converts cents to
-- euro, and it derives the ISO week. The as-of join that produced `unit_cost_as_of` happened in
-- `pipelines/gold/facts.py`, which calls silver's `cost_as_of` rather than restating it here.
--
-- **A sale whose cost was never published produces no row, and the count is printed.** That is
-- doctrine rule 3 arriving in gold: `sum(s.qty * s.price_paid) - sum(s.qty * s.unit_cost_as_of)`
-- skips nulls in the second sum and not in the first, so a line with revenue and no cost would
-- enter the metric as **pure margin** rather than as a gap. Dropping it understates the week;
-- keeping it overstates the week and calls the overstatement a profit. Neither is free, and the
-- one that is visible is the one taken: `pipelines/gold/build.py` reports how many lines were
-- dropped beside how many were kept, and `tests/pipelines/test_gold.py` asserts the number is
-- exactly the count of sales silver could not price.
--
-- Measured on this corpus at smoke scale: **1,418 of 35,695 receipt lines**, all of them before
-- the ERP's first drop of the run, which is when `known_from` begins.
--
-- **`decimal(18, 4)` rather than a float, everywhere money is divided.** A cent is an integer in
-- every layer below this one, and euro arrive only because the metric contract's `unit` is EUR.
-- Dividing into a float would make the sum depend on the order the rows arrived in, and claim 5
-- compares as integers with no tolerance.
--
-- **`iso_week` is built from `extract(YEAROFWEEK ...)` and `weekofyear`, never from
-- `date_format`.** Spark's `date_format` resolves `YYYY` through the JVM's locale week rules,
-- so the same expression yields a different week in a different locale; both functions used
-- here are ISO-8601 by definition. The last days of December belong to week 1 of the next year
-- and the year has to move with the week, which is what `YEAROFWEEK` is for and what a plain
-- `year()` would get wrong once a year.
select
    store_id,
    concat(
        lpad(cast(extract(YEAROFWEEK from event_ts) as string), 4, '0'),
        '-W',
        lpad(cast(weekofyear(event_ts) as string), 2, '0')
    ) as iso_week,
    category,
    qty,
    cast(unit_price_cents as decimal(18, 4)) / 100 as price_paid,
    cast(unit_cost_as_of as decimal(18, 4)) / 100 as unit_cost_as_of
from {{ source('priced', 'priced_sales') }}
where unit_cost_as_of is not null
