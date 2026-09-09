"""Every serverless environment names a version, and the same one.

    SyntaxError: expected '(' (windows.py, line 43)

`src/holdout/contracts/windows.py` line 43 is `def in_order[T: Effective](...)` — a PEP 695
generic, which is Python 3.12 syntax and which `pyproject.toml` licenses:
`requires-python = ">=3.12"`. **Serverless environment version 2 is Python 3.11.** So the estate
was running the repository on an interpreter that cannot parse it, and the design step failed on
the *syntax* of a file three imports deep before it could fail on anything the file does.

**`client` is the deprecated spelling** of `environment_version`, and it was carrying `"2"` —
a number nobody had checked the Python of. Version 4 is Python 3.12.3.

## What this asserts

Every environment spec under `infra/` declares `environment_version`, none declares `client`, and
they all declare the **same** version. Not which version: that is a claim about a Python floor and
it belongs beside the declaration, where the argument and the measured `3.12.3` are written.

**Why sameness matters more than the number here.** Two environments on two versions is two
interpreters running one repository, and the one that is wrong is whichever a reader is not
looking at — `tests/infra/test_the_contract_layer_brings_its_imports.py` makes the same argument
about the dependency lists, for the same reason.

## What it does not check

- **It does not check the Python that version carries.** That mapping lives at Databricks and a
  copy of it here would be a hand-kept list of exactly the kind this register already holds five
  findings about. What is here is the version, the measured Python, and the link, in a comment.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
INFRA = REPO_ROOT / "infra"

_COMMENT = re.compile(r"^\s*#.*$", re.MULTILINE)
_SPEC = re.compile(r"spec\s*\{(.*?)\n\s{4}\}", re.DOTALL)
_VERSION = re.compile(r'environment_version\s*=\s*"([^"]+)"')
_CLIENT = re.compile(r'client\s*=\s*"')


def _specs() -> list[tuple[str, str]]:
    """Every `(where, spec body)` under `infra/`, comments removed."""
    found: list[tuple[str, str]] = []
    for path in sorted(INFRA.glob("*/*.tf")):
        text = _COMMENT.sub("", path.read_text(encoding="utf-8"))
        found.extend((str(path.relative_to(REPO_ROOT)), body) for body in _SPEC.findall(text))
    return found


SPECS = _specs()


def test_there_are_environments_to_check() -> None:
    """An empty population passes every assertion below it and proves nothing."""
    assert SPECS, (
        "no `spec` block under infra/. Either the estate stopped running serverless tasks — "
        "which is a finding — or this reader stopped seeing them, and the assertions below are "
        "about nothing."
    )


@pytest.mark.parametrize(
    ("where", "spec"), SPECS, ids=[f"{w}#{i}" for i, (w, _s) in enumerate(SPECS)]
)
def test_an_environment_names_a_version_and_not_a_client(where: str, spec: str) -> None:
    assert not _CLIENT.search(spec), (
        f"{where} declares `client`, which the provider deprecates in favour of "
        '`environment_version`. It was carrying `"2"` — Python 3.11 — against a repository '
        'that declares `requires-python = ">=3.12"` and uses PEP 695 generics.'
    )
    assert _VERSION.search(spec), (
        f"{where} declares no `environment_version`. Each version carries a specific Python, and "
        "a task that does not name one is a task whose interpreter nobody chose."
    )


def test_every_environment_is_on_the_same_version() -> None:
    versions = {version: where for where, spec in SPECS for version in _VERSION.findall(spec)}
    assert len(versions) == 1, (
        f"the estate declares {sorted(versions)} across {sorted(set(versions.values()))}.\n\n"
        "Two environment versions is two interpreters running one repository, and the one that "
        "is wrong is whichever a reader is not looking at."
    )
