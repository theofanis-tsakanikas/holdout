"""A model whose gates refused does not become a registered version.

**A version in the Unity Catalog registry is not a record, it is a decision.** `backfill.yml`
reads `databricks model-versions list`, takes `max(version)`, and applies `infra/serving` at it —
within the same workflow run. So a version created for a refused model is a refused model serving
live traffic, promoted by arithmetic, with no human having accepted anything. That is doctrine
rule 5 exactly: `promotion.Promotion` is a type that cannot be constructed without naming a
person, and this is the other half — making sure the registry never holds a candidate that type
could not have been built for.

**And the refusal is decided before `mlflow` is imported**, which is what lets this run at all:
mlflow is the estate's package and is in none of this repository's dependency groups.

## What it does not check

- **It does not check that a passing model is registered.** That needs a workspace; `backfill` is
  where it is measured, and it now fails rather than continuing quietly when no version appears.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from pipelines.ml import registry
from pipelines.ml.promotion import Assessment, GateResult


def _assessment(*, passed: bool) -> Assessment:
    return Assessment(
        model_digest="0" * 64,
        gates=(
            GateResult(
                id="calibration_within_band",
                question="Is the model calibrated on the held-out half?",
                passed=passed,
                figure="1.42",
                threshold="1.10",
            ),
        ),
    )


def test_a_refused_model_raises_rather_than_registering() -> None:
    run = SimpleNamespace(assessment=_assessment(passed=False))
    with pytest.raises(registry.RefusedError) as refusal:
        registry.register(run, model_name="holdout.gold.demand")  # type: ignore[arg-type]

    message = str(refusal.value)
    assert "calibration_within_band" in message, (
        "the refusal does not name the gate that refused. Whoever reads a red backfill has the "
        "message and nothing else, and `promotion.Assessment.refusals` is plural for the same "
        "reason: a model can fail three gates at once."
    )


def test_the_refusal_is_decided_before_mlflow_is_imported(monkeypatch: pytest.MonkeyPatch) -> None:
    """Measured by making the import fail: it must not be reached on the refusing path."""
    import builtins

    real = builtins.__import__

    def refuse(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.split(".")[0] == "mlflow":
            raise AssertionError(
                "mlflow was imported while deciding a refusal. The check has to come first, or "
                "this gate can only run where the estate's packages are installed."
            )
        return real(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", refuse)
    with pytest.raises(registry.RefusedError):
        registry.register(
            SimpleNamespace(assessment=_assessment(passed=False)),  # type: ignore[arg-type]
            model_name="holdout.gold.demand",
        )
