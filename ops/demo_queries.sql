-- The queries a viewer types into the SQL editor while the estate is standing.
--
-- **These are the queries `ops/inspect_estate.py` runs, and that is the whole point of the
-- file.** A recording that shows a query nobody has run since the last change is a recording
-- of a hope; `inspect` executes every block below against the standing estate and reports its
-- rows, so what is shown live is what was measured an hour earlier by a command. Three-part
-- names throughout, so the same text works whatever the editor's default catalog is.
--
-- One block per `-- @name`. A block marked `-- @expect refused` is one the estate must
-- refuse -- the door being tried -- and `inspect` goes red if it is accepted.

-- @name the-number-or-the-reason-there-is-none
-- Claim 2. One column carries both cases: the uplift where the four checks passed, the reason
-- code where they did not. On this estate both experiments refuse at design, and that is the
-- screen the project calls its most important one.
select
  experiment_id,
  coalesce(cast(uplift as string), reason_code) as verdict,
  ci_low,
  ci_high,
  p_value,
  reason_codes,
  readout_at,
  restates,
  data_version
from (
  select *, row_number() over (partition by experiment_id order by readout_at desc) as _rank
  from holdout.gold.readout
) where _rank = 1
order by experiment_id;

-- @name the-readout-never-erases
-- Doctrine rule 4. Every readout ever taken, each naming the one it restates; the prior value,
-- the moment and the delta are all still here.
select experiment_id, readout_at, restates, coalesce(cast(uplift as string), reason_code) as verdict, data_version
from holdout.gold.readout
order by experiment_id, readout_at;

-- @name the-door-is-append-only
-- Claim 3. The storage refuses an update, a delete and an overwrite; the property is on the
-- table, not in a Python type.
show tblproperties holdout.gold.experiment_assignment ('delta.appendOnly');

-- @name the-door-tried
-- @expect refused
-- Claim 3, tried rather than described. A delete that matches no row, so nothing could move
-- even if the claim were false. Delta refuses it by name before it looks at the predicate.
delete from holdout.gold.experiment_assignment where experiment_id = 'nobody-declared-this';

-- @name one-definition-the-dbt-table
-- Claim 5. The metric compiled from contracts/metrics/ into a dbt model and built on the
-- estate: 320 stores, three categories, the weeks the world carries.
select metric_id, metric_version, count(*) as store_weeks, round(sum(metric_value), 2) as total_eur
from holdout.gold.category_margin_per_store_week_v3
group by metric_id, metric_version;

-- @name a-stock-out-is-not-zero-demand
-- Claim 4. Store-days that emptied, and what the receipts say they sold before they did -- a
-- number that understates demand by an amount the day cannot tell you.
select
  count(*) as store_days,
  sum(case when emptied then 1 else 0 end) as emptied,
  round(100.0 * sum(case when emptied then 1 else 0 end) / count(*), 1) as emptied_pct,
  round(avg(case when emptied then last_sale_hour end), 1) as mean_last_sale_hour_when_emptied
from holdout.silver.shelf_state;

-- @name the-displayed-price-is-the-ack-not-the-decision
-- The ESL acknowledgement is a source, not a log: the only evidence a price reached a shelf.
select
  accepted,
  count(*) as acks,
  sum(case when price_displayed_cents <> price_decided_cents then 1 else 0 end) as displayed_differs_from_decided
from holdout.silver.price_displayed
group by accepted
order by accepted;

-- @name every-price-on-this-estate-is-a-fallback
-- Doctrine rule 2. The decision record, by outcome and marker, on the day the run drove: both
-- declared policies are deterministic ladders, so the band is all amber -- no model touched the
-- shelf, and the screen says so rather than hiding it behind a percentage.
select
  date(decided_at) as day,
  outcome,
  marker,
  count(*) as decisions,
  round(avg(depth_pct), 1) as mean_depth_pct
from holdout.gold.decisions
where date(decided_at) = (select max(date(decided_at)) from holdout.gold.decisions)
group by 1, 2, 3
order by 1, 2, 3;

-- @name quarantine-is-a-health-metric
-- Silver quarantines rather than drops; the size of the table is the figure.
select count(*) as quarantined from holdout.silver.quarantine;

-- @name the-decision-key-has-no-customer-dimension
-- Claim 7. The grain of the economics table is what a decision is keyed on; read the columns.
describe table holdout.gold.decision_economics;

-- @name lineage-from-the-ack-to-the-readout
-- Unity Catalog draws the graph itself; this is what it holds for this catalog.
select source_table_full_name, target_table_full_name, count(*) as edges
from system.access.table_lineage
where target_table_catalog = 'holdout' and source_table_full_name is not null
group by source_table_full_name, target_table_full_name
order by target_table_full_name, source_table_full_name;
