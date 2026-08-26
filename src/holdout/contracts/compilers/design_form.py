"""The design form with its closed lists resolved.

`contracts/design/form.schema.yaml` marks three enums `x-closed-list` and writes none of
them out. Writing them out would put the set of admissible metrics in two files, and the
second one is the one that goes stale — a metric added to `contracts/metrics/` that the
form still refuses, or worse, a metric removed that the form still offers.

The resolved schema is generated here and checked for staleness by `make contracts`, so
"the design form draws from the metric contract" is a property of the build rather than a
sentence in a document.
"""

from __future__ import annotations

import json
from typing import Any

from holdout.contracts.compilers.sql import DO_NOT_EDIT
from holdout.contracts.model import ContractSet

GENERATOR = "holdout.contracts.compilers.design_form"

CLOSED_LIST = "x-closed-list"


class UnknownClosedListError(ValueError):
    """A closed list the compiler has no source for. Refused rather than left unresolved."""


def compile_design_form(contracts: ContractSet) -> str:
    lists: dict[str, tuple[str, ...]] = {
        "metric_ids": contracts.metric_ids,
        "policy_refs": contracts.policy_refs,
    }
    resolved = _resolve(json.loads(json.dumps(dict(contracts.design_form))), lists)
    resolved["$comment"] = (
        f"{DO_NOT_EDIT}. source: contracts/design/form.schema.yaml plus the closed lists "
        f"resolved from contracts/metrics/ and contracts/policies/; "
        f"generator: {GENERATOR}; regenerate: make contracts."
    )
    return json.dumps(resolved, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _resolve(node: Any, lists: dict[str, tuple[str, ...]]) -> Any:
    if isinstance(node, dict):
        out = {key: _resolve(value, lists) for key, value in node.items()}
        name = out.pop(CLOSED_LIST, None)
        if name is not None:
            if name not in lists:
                raise UnknownClosedListError(
                    f"the form declares closed list {name!r}, which nothing compiles. Either "
                    f"the list is a typo or its source was never wired up; a list left "
                    f"unresolved would silently become free text."
                )
            out["enum"] = list(lists[name])
            out["$comment"] = (
                f"closed list `{name}`, resolved from the contracts at compile time. "
                "Do not edit: add or remove the contract instead."
            )
        return out
    if isinstance(node, list):
        return [_resolve(item, lists) for item in node]
    return node
