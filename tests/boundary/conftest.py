"""One way of making a module unavailable, for both boundary tests.

Both files in this directory need the same thing: import a package with something else
*absent from the interpreter entirely*, and fail if it is reached. `core/` must import with
`yaml` and `jsonschema` gone; `corpus/` must import with `holdout` gone.

It lives here because the first version did not live anywhere — each test patched
`builtins.__import__` itself, and **the patch does not work**. `builtins.__import__` backs the
`import` *statement*; `importlib.import_module("holdout")` goes through `sys.meta_path` and
never touches it. So a module could reach straight past a check whose whole job was to stop it,
and the check would stay green. It was found by planting the call, which is the only way it
could have been found: reading the two tests, they look right.

A `sys.meta_path` finder is the level every import mechanism goes through — the statement,
`__import__`, `importlib.import_module`, and a lazy loader. `tests/boundary/test_blocking.py`
plants both spellings against this fixture and requires each to raise.

`ops/isolation.py` learned the same lesson the same way: one implementation, two callers, and
the copy that drifts is the one nobody reads.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterator, Sequence
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec
from types import ModuleType

import pytest


class _Refuse(MetaPathFinder):
    """A finder that refuses a set of top-level packages and defers on everything else."""

    def __init__(self, names: Sequence[str]) -> None:
        self._names = tuple(names)

    def _blocks(self, fullname: str) -> bool:
        return any(fullname == name or fullname.startswith(f"{name}.") for name in self._names)

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None = None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        del path, target
        if self._blocks(fullname):
            raise ModuleNotFoundError(f"blocked for this test: {fullname}")
        return None


@pytest.fixture
def block_imports(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., None]]:
    """Make packages unreachable, and evict anything already imported that depends on them.

    `evict` names packages to drop from `sys.modules` as well — the package under test, which
    must be re-executed for the block to mean anything, since an already-imported module does
    not run its imports a second time.
    """

    def block(*names: str, evict: Sequence[str] = ()) -> None:
        for prefix in (*names, *evict):
            for module in list(sys.modules):
                if module == prefix or module.startswith(f"{prefix}."):
                    monkeypatch.delitem(sys.modules, module, raising=False)
        monkeypatch.setattr(sys, "meta_path", [_Refuse(names), *sys.meta_path])

    yield block
