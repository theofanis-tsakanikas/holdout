"""The structural check behind `value` without `source` is a build failure.

The JSON Schemas already require a `source` on every guardrail rule and every policy step.
This walk is deliberately a *second*, independent enforcement, and it is the one that
cannot be widened into a hole: it descends the whole document and refuses any object
carrying a `value` — at any nesting depth, inside a key nobody has thought of yet — that
has no `source` beside it. Adding a `thresholds:` block with a bare number in it is exactly
the kind of change that passes a schema written before the block existed.

It runs over the guardrail and policy families, which are where numbers from outside the
repository live. It does not run over the design form, which is a JSON Schema rather than a
contract instance and whose `value` keys are schema vocabulary, not data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from holdout.contracts.errors import Violation

RULE_VALUE_WITHOUT_SOURCE = "value_without_source"
RULE_SOURCE_MALFORMED = "source_malformed"

_REQUIRED_BY_KIND = {
    "legal_instrument": ("instrument", "article", "url", "verified_on"),
    "scenario_assumption": ("note", "verified_on"),
}


def check_provenance(document: Any, *, path: str) -> list[Violation]:
    """Every provenance failure in one document."""
    violations: list[Violation] = []
    _walk(document, path=path, locator="", out=violations)
    return violations


def _walk(node: Any, *, path: str, locator: str, out: list[Violation]) -> None:
    if isinstance(node, dict):
        if "value" in node and "source" not in node:
            out.append(
                Violation(
                    path=path,
                    locator=locator or "/",
                    rule=RULE_VALUE_WITHOUT_SOURCE,
                    detail=(
                        f"a value ({node['value']!r}) with no source beside it. Every number "
                        "that comes from outside this repository carries a citation and a "
                        "verification date, or is declared a scenario assumption. A default "
                        "is a lie with a plausible shape."
                    ),
                )
            )
        if "source" in node:
            out.extend(_check_source(node["source"], path=path, locator=f"{locator}/source"))
        for key, child in node.items():
            _walk(child, path=path, locator=f"{locator}/{key}", out=out)
    elif isinstance(node, list):
        for index, child in enumerate(node):
            _walk(child, path=path, locator=f"{locator}/{index}", out=out)


def _check_source(source: Any, *, path: str, locator: str) -> list[Violation]:
    def bad(detail: str) -> list[Violation]:
        return [Violation(path=path, locator=locator, rule=RULE_SOURCE_MALFORMED, detail=detail)]

    if not isinstance(source, dict):
        return bad("a source must be a mapping with a `kind` and a `verified_on`")
    kind = source.get("kind")
    if kind not in _REQUIRED_BY_KIND:
        return bad(
            f"unknown source kind {kind!r}. Exactly two are admissible: `legal_instrument` "
            "for a verified citation, `scenario_assumption` for a stated assumption of the "
            "synthetic scenario. There is no third kind where a number simply appears."
        )
    missing = [k for k in _REQUIRED_BY_KIND[str(kind)] if not source.get(k)]
    if missing:
        return bad(f"source of kind {kind!r} is missing: {', '.join(missing)}")
    return []


@dataclass(frozen=True, slots=True)
class Census:
    """What the provenance rule actually found, so the build can print a number that moves.

    `values` counts every `value` key in the families walked; `sourced` counts those with a
    `source` beside them. On a green build the two are equal by construction — the load
    fails otherwise — which is why the census is attached to the failure as well as to the
    success. `29/30 values sourced` printed above a violation list is the number that hurts;
    `30/30` on its own is a tautology wearing a ratio.
    """

    values: int = 0
    sourced: int = 0
    legal: int = 0
    scenario: int = 0

    def __add__(self, other: Census) -> Census:
        return Census(
            values=self.values + other.values,
            sourced=self.sourced + other.sourced,
            legal=self.legal + other.legal,
            scenario=self.scenario + other.scenario,
        )

    @property
    def unsourced(self) -> int:
        return self.values - self.sourced


def census(document: Any) -> Census:
    """Count values and sources in one document. Never raises; counting is not judging."""
    total = Census()
    if isinstance(document, dict):
        if "value" in document:
            total += Census(values=1, sourced=1 if "source" in document else 0)
        source = document.get("source")
        if isinstance(source, dict):
            kind = source.get("kind")
            total += Census(
                legal=1 if kind == "legal_instrument" else 0,
                scenario=1 if kind == "scenario_assumption" else 0,
            )
        for child in document.values():
            total += census(child)
    elif isinstance(document, list):
        for child in document:
            total += census(child)
    return total
