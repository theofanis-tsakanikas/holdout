-- GENERATED FILE — DO NOT EDIT
-- source:     contracts/policies/*.yaml, every version ever declared
-- generator:  holdout.contracts.compilers.policies
-- regenerate: make contracts
--
-- `make contracts` recompiles this file and fails the build if what is on disk
-- differs, so an edit here does not survive and does not go unnoticed either.

-- One row per policy version. The marker is doctrine rule 2's, declared in the
-- contract; the outcome is what a decision under this policy is on the decision
-- path: a deterministic policy is the declared safe state and therefore a fallback.
{{ config(materialized='table') }}

select 'ladder_policy@v1' as policy_ref, 'ladder_policy' as policy_id, 1 as version, 'deterministic' as kind, 'fallback' as outcome, 'FALLBACK_LADDER' as marker, true as safe_state, 'markdown' as decision_path, '2026-03-01' as effective_from, cast(null as string) as effective_to
union all
select 'shallow_ladder_policy@v1' as policy_ref, 'shallow_ladder_policy' as policy_id, 1 as version, 'deterministic' as kind, 'fallback' as outcome, 'FALLBACK_LADDER' as marker, false as safe_state, 'markdown' as decision_path, '2026-03-01' as effective_from, cast(null as string) as effective_to
