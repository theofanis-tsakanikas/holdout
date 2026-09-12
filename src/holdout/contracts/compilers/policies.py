"""`contracts/policies/` compiled into a dbt model: one row per policy version, ever.

**The decision record needs the policy's marker, and the marker is a contract value.** Doctrine
rule 2 -- *a fallback is visible all the way to the end* -- puts a marker on every price the
ladder produces, and `contracts/policies/*.yaml` is where the marker is declared, beside the
policy's kind and whether it is a safe state. `gold.decisions` joins each decision's `policy_id`
to this model to carry the marker and the outcome; a `case` statement in a dbt model that
named `FALLBACK_LADDER` would be a second declaration of the contract's value, in the one
consumer nobody re-derives.

**Every version, superseded ones included**, for the reason `contracts/policies/` gives: the
meaning of last year's experiment depends on exactly what its control was, and a decision
recorded under `ladder_policy@v1` has to resolve after `v2` supersedes it.

The outcome a policy kind maps to is the decision path's own three: a `deterministic` policy is
the declared safe state's price and is the **fallback** outcome whatever produced the decision;
a `model_assisted` one is **normal**. A refusal is not a policy and has no row here -- it is a
decision with no price, and `gold.decisions` marks it by its reason code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from holdout.contracts.model import ContractSet

MODEL_PATH = "generated/dbt/models/policies.sql"

_OUTCOME_BY_KIND = {"deterministic": "fallback", "model_assisted": "normal"}


def _literal(value: object) -> str:
    if value is None:
        return "cast(null as string)"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def compile_policies_model(contracts: ContractSet) -> str:
    """The dbt model, as literal rows: the contract is the source, the lakehouse is a copy."""
    rows = []
    for policy in sorted(contracts.policies, key=lambda p: (p.id, p.version)):
        rows.append(
            "select "
            + ", ".join(
                [
                    f"{_literal(policy.ref)} as policy_ref",
                    f"{_literal(policy.id)} as policy_id",
                    f"{_literal(policy.version)} as version",
                    f"{_literal(policy.kind)} as kind",
                    f"{_literal(_OUTCOME_BY_KIND[policy.kind])} as outcome",
                    f"{_literal(policy.marker)} as marker",
                    f"{_literal(policy.safe_state)} as safe_state",
                    f"{_literal(policy.decision_path)} as decision_path",
                    f"{_literal(policy.effective_from.isoformat())} as effective_from",
                    f"{_literal(policy.effective_to.isoformat() if policy.effective_to else None)}"
                    " as effective_to",
                ]
            )
        )
    body = "\nunion all\n".join(rows)
    return (
        "-- GENERATED FILE — DO NOT EDIT\n"
        "-- source:     contracts/policies/*.yaml, every version ever declared\n"
        "-- generator:  holdout.contracts.compilers.policies\n"
        "-- regenerate: make contracts\n"
        "--\n"
        "-- `make contracts` recompiles this file and fails the build if what is on disk\n"
        "-- differs, so an edit here does not survive and does not go unnoticed either.\n"
        "\n"
        "-- One row per policy version. The marker is doctrine rule 2's, declared in the\n"
        "-- contract; the outcome is what a decision under this policy is on the decision\n"
        "-- path: a deterministic policy is the declared safe state and therefore a fallback.\n"
        "{{ config(materialized='table') }}\n"
        "\n" + body + "\n"
    )
