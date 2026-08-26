"""Fixtures shared by the contract tests.

Every negative test starts from the *real* `contracts/` directory and breaks exactly one
thing in a copy of it. A hand-built minimal fixture would drift from the contracts it is
meant to police — it would keep passing after the real schema moved on, which is the
failure mode a test suite is supposed to catch rather than exhibit.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

from holdout.contracts import loader as loader_module
from holdout.contracts.loader import CONTRACTS_DIR, REPO_ROOT, load
from holdout.contracts.model import ContractSet


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def contracts() -> ContractSet:
    """The repository's own contracts, loaded and validated."""
    return load()


@pytest.fixture
def contracts_copy(tmp_path: Path) -> Path:
    destination = tmp_path / "contracts"
    shutil.copytree(CONTRACTS_DIR, destination)
    return destination


@pytest.fixture
def edit_contract() -> Iterator[Callable[[Path, Callable[[Any], Any]], None]]:
    """Rewrite one contract file through a transformation of its parsed document."""

    def apply(path: Path, transform: Callable[[Any], Any]) -> None:
        document = yaml.load(path.read_text(encoding="utf-8"), Loader=loader_module._LiteralLoader)
        path.write_text(yaml.safe_dump(transform(document), sort_keys=False), encoding="utf-8")

    yield apply
