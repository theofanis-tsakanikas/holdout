"""No policy version is ever deleted.

Deleting `ladder_policy@v3` does not only lose a file. Every experiment that named it as
its control becomes retroactively uninterpretable, because nobody can say afterwards what
the control actually did — and the whole project rests on the comparison against that
control being checkable a year later.

So the check is on references, not on files: any `<id>@v<n>` named by a policy's
`supersedes` or by a committed experiment must still be on disk.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from holdout.contracts.errors import ContractError
from holdout.contracts.loader import load
from holdout.contracts.model import ContractSet


def test_the_ladder_is_deterministic_because_it_is_the_declared_safe_state(
    contracts: ContractSet,
) -> None:
    """For an expiring product silence is not safe — the product is thrown away — so the
    fresh path falls back to the ladder. A safe state that consulted a model would fail
    exactly when the model was the thing that failed."""
    ladder = next(p for p in contracts.policies if p.id == "ladder_policy")
    assert ladder.kind == "deterministic"
    assert ladder.safe_state is True
    assert ladder.decision_path == "markdown"


def test_a_fallback_carries_a_marker_all_the_way_to_the_end(contracts: ContractSet) -> None:
    """Doctrine rule 2. A fallback that looks like a model decision is worse than an outage."""
    ladder = next(p for p in contracts.policies if p.id == "ladder_policy")
    assert ladder.marker


def test_the_ladder_steps_deepen_as_the_expiry_approaches(contracts: ContractSet) -> None:
    ladder = next(p for p in contracts.policies if p.id == "ladder_policy")
    steps = sorted(ladder.steps, key=lambda s: s.step)
    assert [s.step for s in steps] == list(range(1, len(steps) + 1))
    hours = [s.hours_to_expiry_at_most for s in steps]
    depths = [s.depth_pct for s in steps]
    assert hours == sorted(hours, reverse=True), "each step must trigger closer to expiry"
    assert depths == sorted(depths), "each step must cut at least as deep as the last"


def test_the_ladder_never_produces_the_refusal_itself(contracts: ContractSet) -> None:
    """A refusal is the guardrail set's answer — no legal price sells the item — and it is a
    correct output, donation or disposal, rather than an error the ladder invents."""
    ladder = next(p for p in contracts.policies if p.id == "ladder_policy")
    assert ladder.floor_behaviour.when_step_breaches_floor == "clamp_to_floor"


def test_a_decision_is_idempotent_per_sku_store_and_step(contracts: ContractSet) -> None:
    ladder = next(p for p in contracts.policies if p.id == "ladder_policy")
    assert ladder.idempotency_key == ("sku_id", "store_id", "ladder_step")


def test_every_policy_version_referenced_is_present_on_disk(contracts: ContractSet) -> None:
    on_disk = set(contracts.policy_refs)
    for policy in contracts.policies:
        if policy.supersedes is not None:
            assert policy.supersedes in on_disk


def test_a_superseded_version_that_was_deleted_is_a_build_failure(
    contracts_copy: Path,
) -> None:
    """The check is written against a chain the repository does not yet have, so it bites
    the day a v2 is added rather than the day someone notices it never did."""
    v1 = contracts_copy / "policies" / "ladder_policy@v1.yaml"
    document = yaml.safe_load(v1.read_text(encoding="utf-8"))
    document["version"] = 2
    document["supersedes"] = "ladder_policy@v1"
    document["effective_from"] = "2026-06-01"
    (contracts_copy / "policies" / "ladder_policy@v2.yaml").write_text(
        yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
    )
    v1.unlink()

    with pytest.raises(ContractError) as raised:
        load(contracts_copy)
    assert any(v.rule == "version_deleted" for v in raised.value.violations)


def test_an_experiment_naming_a_policy_that_is_gone_is_a_build_failure(
    contracts_copy: Path,
) -> None:
    experiments = contracts_copy.parent / "experiments"
    experiments.mkdir()
    (experiments / "fresh_ladder_2026_q2.yaml").write_text(
        "intervention:\n  treatment: ladder_policy@v4\n  control: ladder_policy@v1\n",
        encoding="utf-8",
    )
    with pytest.raises(ContractError) as raised:
        load(contracts_copy)
    violations = [v for v in raised.value.violations if v.rule == "version_deleted"]
    assert violations and "ladder_policy@v4" in violations[0].detail


def test_a_policy_step_with_a_depth_and_no_source_is_a_build_failure(
    contracts_copy: Path, edit_contract: Callable[[Path, Callable[[Any], Any]], None]
) -> None:
    """Doctrine rule 3 reaches the policies too: a markdown depth is a number that came from
    outside the repository, and a default is a lie with a plausible shape."""
    path = contracts_copy / "policies" / "ladder_policy@v1.yaml"

    def drop_source(document: Any) -> Any:
        del document["steps"][0]["source"]
        return document

    edit_contract(path, drop_source)
    with pytest.raises(ContractError) as raised:
        load(contracts_copy)
    assert any(v.rule in {"schema", "value_without_source"} for v in raised.value.violations)


def test_the_two_policy_versions_form_a_contiguous_timeline(contracts_copy: Path) -> None:
    """A gap between policy versions is a period during which the control arm was undefined."""
    v1 = contracts_copy / "policies" / "ladder_policy@v1.yaml"
    document = yaml.safe_load(v1.read_text(encoding="utf-8"))
    v1.write_text(
        yaml.safe_dump({**document, "effective_to": "2026-06-01"}, sort_keys=False), "utf-8"
    )
    successor = {
        **document,
        "version": 2,
        "supersedes": "ladder_policy@v1",
        "effective_from": "2026-09-01",
        "effective_to": None,
    }
    (contracts_copy / "policies" / "ladder_policy@v2.yaml").write_text(
        yaml.safe_dump(successor, sort_keys=False), encoding="utf-8"
    )
    with pytest.raises(ContractError) as raised:
        load(contracts_copy)
    assert any(v.rule == "timeline" for v in raised.value.violations)
