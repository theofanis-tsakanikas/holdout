-- Gold family D. The decision record: immutable, written at decision time, one row per decision.
--
-- `CLAUDE.md` names four families and this is the fourth; until 2026-09-12 it was the one with
-- no table, while the decision monitor -- the screen doctrine rule 2 is proved on -- was compiled
-- to read it. `ops/inspect_estate.py` read the warehouse's answer: *the table or view
-- `gold`.`decisions` cannot be found*.
--
-- **The marker and the outcome are the contract's, joined in, never typed here.** `policies` is
-- `contracts/policies/*.yaml` compiled to rows, every version ever declared, and a decision
-- resolves its policy by the ref the chain wrote. A decision whose policy the contract layer
-- does not know keeps its row and carries a null marker, which is a finding the monitor shows
-- rather than a row this model drops.
--
-- **Every price on this estate is a fallback, and the monitor will say so.** Both declared
-- policies are deterministic ladders, so `outcome` is `fallback` on every row and the stacked
-- area is one amber band. That is the truth of an estate whose decision path holds no model,
-- and it is exactly what rule 2 asks a screen to make impossible to miss.
--
-- **It carries the arm, and the readout never reads it.** A decision record that did not know
-- which arm it routed by would be a record of nothing; the readout attributes units to arms
-- from `gold.experiment_assignment` alone, and `test_no_gold_table_the_readout_reads_carries_an_arm`
-- is what keeps this table off that path.
select
    d.store_id,
    d.sku_id,
    d.event_ts as decided_at,
    d.arrival_ts,
    d.arm,
    d.policy_id as policy_ref,
    p.kind,
    coalesce(p.outcome, 'unknown') as outcome,
    p.marker,
    cast(null as string) as reason_code,
    d.ladder_step,
    d.hours_to_expiry,
    d.base_price_cents,
    d.price_decided_cents,
    round(100.0 * (d.base_price_cents - d.price_decided_cents) / d.base_price_cents, 1) as depth_pct
from {{ source('silver', 'decisions') }} d
left join {{ ref('policies') }} p on p.policy_ref = d.policy_id
