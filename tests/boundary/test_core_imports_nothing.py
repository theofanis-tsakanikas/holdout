"""The framework-free core, enforced rather than asserted in prose.

Two separate things are checked, because they fail in different ways.

The first is static: no module under `src/holdout/core/` may import a cloud SDK, an engine,
a serialisation library or a schema validator. That is what makes every claim provable on a
laptop with no account, and it is the kind of rule that erodes one convenient import at a
time.

The second is dynamic and is the boundary this branch is responsible for: the dataclasses
that cross from the contract layer into the core must import with `yaml` and `jsonschema`
absent from the interpreter entirely. A model module that quietly depended on the parser
that produced it would drag the whole contract layer into `core` the first time someone
imported a type.
"""

from __future__ import annotations

import ast
import builtins
import sys
from pathlib import Path

import pytest

CORE = Path(__file__).resolve().parents[2] / "src" / "holdout" / "core"

FORBIDDEN_IN_CORE = {
    "boto3",
    "botocore",
    "databricks",
    "dbt",
    "delta",
    "duckdb",
    "jsonschema",
    "mlflow",
    "pandas",
    "pyspark",
    "referencing",
    "requests",
    "sqlalchemy",
    "yaml",
}

#: Loaded lazily by the contract layer only. `holdout.contracts.model` must not reach them.
BLOCKED_FOR_MODEL = ("yaml", "jsonschema", "referencing")


def _imported_modules(source: str) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def test_core_imports_no_sdk_engine_or_parser() -> None:
    offences: list[str] = []
    for path in sorted(CORE.rglob("*.py")):
        for module in sorted(_imported_modules(path.read_text(encoding="utf-8"))):
            if module in FORBIDDEN_IN_CORE:
                offences.append(f"{path.relative_to(CORE.parents[2])} imports {module}")
    assert not offences, (
        "src/holdout/core/ is pure functions over plain data. These imports would make a "
        "claim unprovable without an account, an engine or a parser:\n  " + "\n  ".join(offences)
    )


def test_core_imports_only_contract_model_from_the_contract_layer() -> None:
    """Core may take resolved contracts as arguments; it may not go and read them."""
    offences: list[str] = []
    for path in sorted(CORE.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.ImportFrom)
                and (node.module or "").startswith("holdout.contracts")
                and node.module not in {"holdout.contracts.model", "holdout.contracts.windows"}
            ):
                offences.append(f"{path.name} imports {node.module}")
    assert not offences, (
        "core takes a resolved contract as an argument; it never loads, finds or parses "
        "one. Only holdout.contracts.model and holdout.contracts.windows may cross:\n  "
        + "\n  ".join(offences)
    )


def test_contract_model_imports_with_yaml_and_jsonschema_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def blocked(name: str, *args: object, **kwargs: object) -> object:
        if name.split(".")[0] in BLOCKED_FOR_MODEL:
            raise ModuleNotFoundError(f"blocked for this test: {name}")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    for module in list(sys.modules):
        if module.startswith("holdout.contracts") or module.split(".")[0] in BLOCKED_FOR_MODEL:
            monkeypatch.delitem(sys.modules, module, raising=False)
    monkeypatch.setattr(builtins, "__import__", blocked)

    import importlib

    model = importlib.import_module("holdout.contracts.model")
    windows = importlib.import_module("holdout.contracts.windows")
    assert model.Rounding(mode="half_even", decimals=2).canonical_integer("1.005") == 100
    assert windows.resolve_as_of([], __import__("datetime").date(2026, 4, 1)) is None
