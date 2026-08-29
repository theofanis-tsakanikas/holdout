"""A second reading of what the core carries — from the source text, never from the objects.

Why this exists
---------------
`ops/personhood.py` answers *what does this type carry* by importing the module and asking
Python: `dataclasses.fields`, `__slots__`, `getattr`. That is the right answer and it is one
answer. If the eval also asked its questions that way, the only thing that would know what a
class carries would be the class, and the eval would be asking a function to mark its own
paper — claim 1's trap, one layer over.

So this module reads the **text**. It parses every file under `src/holdout/core/` with `ast`
and never imports one, which means it is blind to everything the import machinery does and
sighted on everything written down. The two disagree in useful ways, and `O11` publishes the
disagreement rather than assuming there is none.

Differ everywhere you are allowed to
------------------------------------

| | `ops/personhood.py` | this module |
|---|---|---|
| mechanism | imports the module, asks the object | parses the file, walks the tree |
| a dataclass field | `dataclasses.fields(cls)` | an annotated assignment in the class body |
| a slotted class | `cls.__slots__` | the string literals assigned to `__slots__` |
| what it would miss | a field written down but rewritten by a decorator | a field created at runtime and never written down |
| what it can see | only what imported | every name the core **defines**, fields included |

They share `ops.personhood.tokens` and nothing else, because how a name is split into words
is the arithmetic that lets a camelCase vocabulary be compared with a snake_case field at
all. Splitting it twice would be two spellings of one convention, which is the failure mode
`contracts/` exists to argue against — not two implementations of a decision.

The identifier scan
-------------------
`identifiers()` is the half `ops/personhood.py` has no counterpart for, and it is the reason
this module is more than a cross-check. A person can arrive on the decision path without
being a *field*: a parameter on `dispatch_to_shelf`, an enum member on `PriceSource`, a
module constant. None of those is a dataclass field and none would be caught by any amount
of comparing field sets. They are caught here, or nowhere.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

CORE = Path(__file__).resolve().parents[2] / "src" / "holdout" / "core"


@dataclass(frozen=True, slots=True)
class Identifier:
    """One name the core defines, and where it defines it."""

    name: str
    where: str
    """`module.py:line`, so a red run points at a line rather than at a package."""

    kind: str
    """`class` · `function` · `parameter` · `assignment` · `attribute` · `keyword`."""


def _sources() -> Iterator[Path]:
    yield from sorted(CORE.rglob("*.py"))


def _module_name(path: Path) -> str:
    relative = path.relative_to(CORE.parent.parent).with_suffix("")
    return ".".join(relative.parts)


def _slots(node: ast.ClassDef) -> frozenset[str] | None:
    """The names assigned to `__slots__` in a class body, if it assigns any.

    `None` — rather than an empty set — when the class has no `__slots__` at all, because
    "declares no slots" and "declares an empty tuple" are different statements and the
    witness class inside `certificate.py` makes the second one on purpose.
    """
    for statement in node.body:
        targets = (
            statement.targets
            if isinstance(statement, ast.Assign)
            else [statement.target]
            if isinstance(statement, ast.AnnAssign)
            else []
        )
        if not any(isinstance(t, ast.Name) and t.id == "__slots__" for t in targets):
            continue
        value = statement.value if isinstance(statement, ast.Assign | ast.AnnAssign) else None
        if isinstance(value, ast.Tuple | ast.List | ast.Set):
            return frozenset(
                element.value
                for element in value.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            )
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return frozenset({value.value})
        return frozenset()
    return None


def _annotated_fields(node: ast.ClassDef) -> frozenset[str]:
    """Annotated assignments in the class body — a dataclass's fields, as written."""
    return frozenset(
        statement.target.id
        for statement in node.body
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
    )


def field_sets() -> dict[str, frozenset[str]]:
    """`module.Class` -> the fields the source text says it carries.

    Slots win where a class declares both, for the same reason `ops.personhood.field_names`
    reads `dataclasses.fields` first: a dataclass declared with `slots=True` has its
    `__slots__` synthesised by the decorator and never written down, so a class that *has*
    both in the text is a hand-written slotted class and the slots are the statement.
    """
    found: dict[str, frozenset[str]] = {}
    for path in _sources():
        module = _module_name(path)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            slots = _slots(node)
            fields = _annotated_fields(node) if slots is None else slots
            found[f"{module}.{node.name}"] = fields
    return found


def identifiers() -> tuple[Identifier, ...]:
    """Every name the core defines: classes, functions, parameters, assignments, attributes.

    Deliberately generous. A name that is only *read* here — `Decimal`, `frozenset` — is
    somebody else's and says nothing about this system's vocabulary; a name this code
    **writes down** is a choice somebody made, and claim 7 is about the choices.
    """
    found: set[tuple[str, str, str]] = set()
    for path in _sources():
        module = _module_name(path)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            where = f"{module}:{getattr(node, 'lineno', 0)}"
            if isinstance(node, ast.ClassDef):
                found.add((node.name, where, "class"))
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                found.add((node.name, where, "function"))
            elif isinstance(node, ast.arg):
                found.add((node.arg, where, "parameter"))
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                found.add((node.id, where, "assignment"))
            elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
                found.add((node.attr, where, "attribute"))
            elif isinstance(node, ast.keyword) and node.arg:
                found.add((node.arg, where, "keyword"))
    return tuple(Identifier(*triple) for triple in sorted(found))


@dataclass(frozen=True, slots=True)
class Seal:
    """Whether a class can have anything stapled to it after it is built."""

    qualified: str
    frozen: bool
    slotted: bool

    @property
    def sealed(self) -> bool:
        """Frozen refuses the assignment; slots refuse the *name*. Both, or it is not sealed.

        Either one alone leaves a route open. A frozen class with a `__dict__` refuses
        `key.customer_id = x` and accepts `object.__setattr__(key, "customer_id", x)`; a
        slotted class that is not frozen accepts assignment to any slot it declares. What
        makes a decision key unable to carry a person is that there is no name to assign to
        *and* no assignment to make.
        """
        return self.frozen and self.slotted


def _dataclass_flags(node: ast.ClassDef) -> tuple[bool, bool]:
    frozen = slotted = False
    for decorator in node.decorator_list:
        call = decorator if isinstance(decorator, ast.Call) else None
        if call is None or not isinstance(call.func, ast.Name | ast.Attribute):
            continue
        name = call.func.id if isinstance(call.func, ast.Name) else call.func.attr
        if name != "dataclass":
            continue
        for keyword in call.keywords:
            if not isinstance(keyword.value, ast.Constant):
                continue
            if keyword.arg == "frozen":
                frozen = bool(keyword.value.value)
            elif keyword.arg == "slots":
                slotted = bool(keyword.value.value)
    return frozen, slotted


def seals() -> dict[str, Seal]:
    """`module.Class` -> whether the source text seals it, read from the decorator and body.

    A hand-written `__slots__` counts as slotted, and a class whose constructor refuses
    outright — `CertifiedPrice`, `SealedAssignment` — counts as frozen: there is no instance
    to freeze that the type did not issue itself. That second rule is read from the text as
    an `__init__` whose body raises, which is exactly how both of them are written.
    """
    found: dict[str, Seal] = {}
    for path in _sources():
        module = _module_name(path)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            frozen, slotted = _dataclass_flags(node)
            slotted = slotted or _slots(node) is not None
            frozen = frozen or _constructor_refuses(node)
            found[f"{module}.{node.name}"] = Seal(f"{module}.{node.name}", frozen, slotted)
    return found


def _constructor_refuses(node: ast.ClassDef) -> bool:
    """An `__init__` whose body is a `raise` — the type issues itself or not at all."""
    for statement in node.body:
        if not isinstance(statement, ast.FunctionDef) or statement.name != "__init__":
            continue
        return any(isinstance(inner, ast.Raise) for inner in statement.body)
    return False
