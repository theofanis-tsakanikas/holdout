"""Scenario selection — the model returns a table, code picks the row by arithmetic."""

from holdout.core.pricing.selection import (
    Outcome,
    Scenario,
    ScenarioTableError,
    Selection,
    outcome_of,
    select,
)

__all__ = [
    "Outcome",
    "Scenario",
    "ScenarioTableError",
    "Selection",
    "outcome_of",
    "select",
]
