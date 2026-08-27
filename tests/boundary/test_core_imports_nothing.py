"""The framework-free core, enforced rather than asserted in prose.

Four things are checked, because they fail in different ways.

**Imports.** No module under `src/holdout/core/` may import a cloud SDK, an engine, a
serialisation library or a schema validator. That is what makes every claim provable on a
laptop with no account, and it is the kind of rule that erodes one convenient import at a
time.

**Determinism.** No module there may read a clock, an environment or a random source. Time
is an argument. A guardrail whose answer depends on when it was asked cannot be replayed,
and a decision that cannot be replayed cannot be checked.

**Money — and this one is a lint, not the gate.** No module there may contain a float
literal, a `float` annotation or a call to `float()`. A binary float cannot represent ten
cents, and claim 5 compares three consumers as integers with no tolerance, which is a
tolerance-shaped place for a disagreement to hide.

Be clear about how much this check is worth. It reads source text, so it catches the forms
someone writes by accident and misses the ones someone writes deliberately: a review of ten
planted float forms found **five slipping past it** — `float` reached through
`builtins`, an annotation written as the string `"float"` (now caught, below), a float
produced by `Decimal("1") / 3` and coerced later, a value arriving as a float from a
caller mypy never checked, and `numbers.Real`. Every one of them was still stopped at
runtime, by `Money` refusing a float in `_exact` and by `Money.of` refusing a third decimal
place. **`Money` is the gate; this test is the lint that keeps the gate from being needed.**

Deliberately not banned: `isinstance(value, float)`. Recognising a float that arrived from
PyYAML through the contract layer, and converting it on the same line, is exactly what this
boundary is for.

**The dynamic half.** Every core module, and the contract dataclasses that cross into it,
must import with `yaml` and `jsonschema` absent from the interpreter entirely. A module
that quietly depended on the parser that produced its data would drag the whole contract
layer into `core` the first time someone imported a type.

These tests were placed before `core/` had anything in it, and were vacuous until it did.
Each one now asserts it found something, so it can never silently return to that state.
"""

from __future__ import annotations

import ast
import importlib
from collections.abc import Callable
from pathlib import Path

CORE = Path(__file__).resolve().parents[2] / "src" / "holdout" / "core"

FORBIDDEN_IN_CORE = {
    # cloud SDKs, engines, parsers and validators — the account-and-framework half
    "boto3",
    "cmath",
    "botocore",
    "databricks",
    "dbt",
    "delta",
    "duckdb",
    "jsonschema",
    "math",
    "mlflow",
    "numpy",
    "pandas",
    "pyspark",
    "referencing",
    "requests",
    "scipy",
    "sqlalchemy",
    "yaml",
    # determinism — time is an argument, and nothing here reads a clock, a filesystem,
    # an environment or a random source
    "os",
    "pathlib",
    "random",
    "secrets",
    "socket",
    "subprocess",
    "sys",
    "time",
    "urllib",
    "uuid",
}

#: Calls that would make a core function answer differently on a second run. `now` and
#: `utcnow` are the obvious ones; `monotonic` and `perf_counter` are how they come back.
FORBIDDEN_CALLS = {
    "now",
    "today",
    "utcnow",
    "utcfromtimestamp",
    "fromtimestamp",
    "monotonic",
    "perf_counter",
    "getenv",
    "urandom",
    "shuffle",
    "randint",
    "choice",
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
    block_imports: Callable[..., None],
) -> None:
    """The dataclasses that cross into `core/` must not drag the parser that produced them.

    Blocked through `sys.meta_path` rather than through `builtins.__import__`, which is what
    this test used to do and which only ever covered the `import` statement: an
    `importlib.import_module("yaml")` walked past it untouched. `tests/boundary/conftest.py`
    holds the one implementation now and `test_blocking.py` drives it with that exact spelling.
    """
    block_imports(*BLOCKED_FOR_MODEL, evict=("holdout",))
    importlib.import_module("holdout.contracts.model")


def _core_modules() -> list[Path]:
    return sorted(CORE.rglob("*.py"))


def test_the_boundary_tests_are_not_vacuous() -> None:
    """They were placed before `core/` had anything in it. This is what stops them
    quietly returning to that state after a refactor moves the package."""
    modules = _core_modules()
    assert len(modules) >= 5, f"only {len(modules)} modules found under {CORE}"
    assert any(path.name == "certificate.py" for path in modules)


def test_core_reads_no_clock_environment_or_random_source() -> None:
    """Determinism: same inputs, same outputs, always. Time is an argument."""
    offences: list[str] = []
    for path in _core_modules():
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call):
                func = node.func
                name = func.attr if isinstance(func, ast.Attribute) else None
                if name in FORBIDDEN_CALLS:
                    offences.append(f"{path.name} calls .{name}()")
    assert not offences, (
        "a core function that reads a clock, an environment or a random source cannot be "
        "replayed, and a decision that cannot be replayed cannot be checked:\n  "
        + "\n  ".join(offences)
    )


def test_no_float_goes_anywhere_near_money() -> None:
    """A float should be impossible to write by accident in this package.

    Three forms are refused: a float literal, a `float` annotation on any argument, return
    value or field, and a call to `float()`. `isinstance(x, float)` is deliberately allowed
    — see the module docstring.
    """
    offences: list[str] = []
    for path in _core_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and type(node.value) is float:
                offences.append(f"{path.name}:{node.lineno} float literal {node.value!r}")
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "float"
            ):
                offences.append(f"{path.name}:{node.lineno} calls float()")
        for node in ast.walk(tree):
            for annotation in _annotations(node):
                if _names_float(annotation):
                    offences.append(f"{path.name}:{annotation.lineno} annotates a float")
    assert not offences, (
        "money is an integer number of cents and a percentage is a Decimal. A float here "
        "loses the exactness claim 5 compares on, at the first division:\n  "
        + "\n  ".join(offences)
    )


def _annotations(node: ast.AST) -> list[ast.expr]:
    """Every place a type is named: signatures, annotated assignments, and `cast`.

    `cast` is in the list because `holdout.core.guardrails.certificate` reads every one of
    its fields through it — `cast(Money, self._read("_price"))`. A type asserted there is
    as load-bearing as one in a signature, and mypy trusts it without checking, so it is
    the one place where writing `float` would be both invisible and believed.
    """
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        found = [a.annotation for a in node.args.args if a.annotation]
        found += [a.annotation for a in node.args.kwonlyargs if a.annotation]
        if node.returns:
            found.append(node.returns)
        return found
    if isinstance(node, ast.AnnAssign) and node.annotation:
        return [node.annotation]
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "cast"
        and node.args
    ):
        return [node.args[0]]
    return []


def _names_float(annotation: ast.expr) -> bool:
    """`float`, including when it is written as a string.

    `x: "float"` and `cast("float | None", v)` are annotations too, and both slipped an
    earlier version of this walk. A string annotation is parsed and walked in turn, so a
    forward reference nests as deeply as anyone cares to write it.
    """
    for child in ast.walk(annotation):
        if isinstance(child, ast.Name) and child.id == "float":
            return True
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            try:
                inner = ast.parse(child.value, mode="eval").body
            except SyntaxError:
                continue
            if any(isinstance(node, ast.Name) and node.id == "float" for node in ast.walk(inner)):
                return True
    return False


def test_every_core_module_imports_with_yaml_and_jsonschema_absent(
    block_imports: Callable[..., None],
) -> None:
    """Every core module, with the contract layer's two dependencies unreachable.

    Same fixture, same reason: the block has to survive `importlib.import_module`, and the
    `builtins.__import__` patch this test used to carry did not.
    """
    block_imports(*BLOCKED_FOR_MODEL, evict=("holdout",))
    names = [
        "holdout.core." + str(path.relative_to(CORE).with_suffix("")).replace("/", ".")
        for path in _core_modules()
    ]
    names = [name.removesuffix(".__init__") for name in names]
    assert len(names) >= 5
    for name in sorted(names):
        importlib.import_module(name)
