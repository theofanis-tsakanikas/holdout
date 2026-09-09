"""Every declaration of the contract layer's dependencies says the same thing.

    ModuleNotFoundError: No module named 'jsonschema'

`src/holdout/contracts/` is allowed exactly two third-party imports, and `pyproject.toml` names
them in the `contracts` extra: PyYAML reads the files and jsonschema validates them.
`src/holdout/core/` is allowed neither, which is why the ingest and silver tasks need none of it —
and why the tasks that failed are the two that ask a contract a question: the experiment, which
resolves the metric and the inference settings, and training, which reads its own.

**The serverless base image carries neither.** So the estate declares them, twice — once in
`infra/pipelines/jobs.tf` for the experiment jobs and once in `infra/ml/training.tf` — and two
declarations of one dependency set is one of them being wrong.

> **This register holds five findings of that shape already**: three lists of packages that may be
> absent, two declarations of one window, two defaults for one flag, a tag-defined population
> blind to what lacks the tag, and a parameter reader blind to `concat`. Each was found by
> something other than the mechanism that was supposed to hold it. This one compares them.

## What it does not check

- **It does not check that the versions are installable.** A bad pin fails at install with a
  resolution error, loudly, which is the cheap signal.
- **It does not check which tasks need them.** That is a property of the imports, and
  `tests/boundary/` is where the contract layer's two imports are policed.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
INFRA = REPO_ROOT / "infra"
PYPROJECT = REPO_ROOT / "pyproject.toml"

_COMMENT = re.compile(r"^\s*#.*$", re.MULTILINE)
_DEPENDENCIES = re.compile(r"dependencies\s*=\s*\[([^\]]*)\]")
_STRING = re.compile(r'"([^"]*)"')


def _declared_in_pyproject() -> list[str]:
    """The `contracts` extra, which is the one this repository calls the contract layer's."""
    document = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return sorted(document["project"]["optional-dependencies"]["contracts"])


def _declared_in_terraform() -> list[tuple[str, list[str]]]:
    """Every literal `dependencies = [...]` under `infra/`, by file, comments removed."""
    found: list[tuple[str, list[str]]] = []
    for path in sorted(INFRA.glob("*/*.tf")):
        text = _COMMENT.sub("", path.read_text(encoding="utf-8"))
        for match in _DEPENDENCIES.finditer(text):
            packages = _STRING.findall(match.group(1))
            if packages:
                found.append((str(path.relative_to(REPO_ROOT)), sorted(packages)))
    return found


CONTRACTS = _declared_in_pyproject()
TERRAFORM = [
    (where, packages)
    for where, packages in _declared_in_terraform()
    if any("jsonschema" in package.lower() for package in packages)
]


def test_the_extra_is_where_this_gate_looks() -> None:
    """An absent extra makes every comparison below it vacuous."""
    assert CONTRACTS, (
        "pyproject.toml declares no `contracts` extra, so there is nothing for the estate's "
        "declarations to agree with. If the contract layer's imports moved, this gate moves too."
    )
    assert TERRAFORM, (
        "no layer under infra/ declares jsonschema. The tasks that read a contract then fail "
        "with ModuleNotFoundError inside a job — the experiment's design step did, after the "
        "baseline, silver and gold had all succeeded."
    )


@pytest.mark.parametrize(("where", "packages"), TERRAFORM, ids=[w for w, _p in TERRAFORM])
def test_a_terraform_declaration_matches_the_extra(where: str, packages: list[str]) -> None:
    assert packages == CONTRACTS, (
        f"{where} declares {packages} and pyproject.toml's `contracts` extra is {CONTRACTS}.\n\n"
        "Two declarations of one dependency set is one of them being wrong, and the one that is "
        "wrong is the one nobody re-reads. The estate's version is only exercised by a dispatch."
    )
