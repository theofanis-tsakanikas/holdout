"""The instrument the two boundary tests are made of, tested before they are believed.

`tests/boundary/conftest.py` exists because the technique it replaced did not work: both
boundary tests patched `builtins.__import__`, which backs the `import` statement and nothing
else, so `importlib.import_module("holdout")` walked straight past a check written to stop it.
The tests stayed green. Reading them, they look right.

**A guard tested by its author is tested in the shape the guard already handles.** So the
fixture is driven here by the shape that defeated its predecessor, and by two more, each
reaching the import machinery through a different door.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest


def test_the_import_statement_is_blocked(block_imports: Callable[..., None]) -> None:
    block_imports("holdout", evict=("holdout",))
    with pytest.raises(ModuleNotFoundError, match="blocked for this test"):
        import holdout.core.money  # noqa: F401


def test_importlib_import_module_is_blocked(block_imports: Callable[..., None]) -> None:
    """The spelling that defeated the previous implementation, planted deliberately.

    `builtins.__import__` is not on this path at all. Nothing in the old technique could have
    caught it, and nothing did.
    """
    import importlib

    block_imports("holdout", evict=("holdout",))
    with pytest.raises(ModuleNotFoundError, match="blocked for this test"):
        importlib.import_module("holdout.core.money")


def test_dunder_import_is_blocked(block_imports: Callable[..., None]) -> None:
    block_imports("holdout", evict=("holdout",))
    with pytest.raises(ModuleNotFoundError, match="blocked for this test"):
        __import__("holdout.core.money")


def test_a_submodule_is_blocked_by_its_package(block_imports: Callable[..., None]) -> None:
    import importlib

    block_imports("holdout", evict=("holdout",))
    with pytest.raises(ModuleNotFoundError, match="blocked for this test"):
        importlib.import_module("holdout.contracts.model")


def test_everything_else_still_imports(block_imports: Callable[..., None]) -> None:
    """A blocker that blocked everything would make every test above pass and mean nothing."""
    import importlib

    block_imports("holdout", evict=("holdout",))
    assert importlib.import_module("json") is not None
    assert importlib.import_module("corpus.world.rng") is not None


def test_a_package_whose_name_merely_starts_the_same_is_not_blocked(
    block_imports: Callable[..., None],
) -> None:
    block_imports("json", evict=())
    import importlib

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("json")
    # `jsonschema` is a different top-level package; a prefix match on the string would have
    # taken it down with `json` and the block would be quietly wider than it says.
    assert importlib.import_module("jsonschema") is not None
