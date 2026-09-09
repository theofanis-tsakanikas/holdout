"""The environment a dbt task names declares dbt.

    + dbt deps
    /bin/bash: line 4: dbt: command not found

**A serverless `dbt_task` runs dbt in the environment it names, and the base image has none.**
The job carried one environment, shared by every task, with `client = "2"` and no dependencies —
which is right for the Python tasks, all of which import only what this repository and the
runtime already have. dbt is the exception and nothing said so.

**It cost the third dispatch of the day to find**, after the baseline, silver and the priced
tables had all succeeded. `infra/pipelines/jobs.tf` already carried a paragraph about this task
needing *an environment as well as a warehouse* — the environment being *where dbt itself runs* —
and the environment it named could not run dbt.

## What this asserts

Every `dbt_task` names an environment whose spec declares a dependency. Not which one: an adapter
is a choice with an argument, and the argument belongs beside the declaration.

## What it does not check

- **It does not check the version resolves.** A bad pin fails at install with a resolution error,
  loudly, which is the cheap signal.
- **It reads Terraform, not the account.** The same limit every gate over a file here has.
"""

from __future__ import annotations

import re

import pytest

from tests.infra import tasks

_COMMENT = re.compile(r"^\s*#.*$", re.MULTILINE)
_ENVIRONMENT = re.compile(
    r"environment\s*\{\s*environment_key\s*=\s*([^\n]+?)\s*\n\s*spec\s*\{(.*?)\n\s*\}",
    re.DOTALL,
)
_KEY = re.compile(r"environment_key\s*=\s*([^\n]+)")


def _files() -> list[tuple[str, str]]:
    """Every Terraform file under `infra/`, with its comments removed."""
    return [
        (str(path.relative_to(tasks.REPO_ROOT)), _COMMENT.sub("", path.read_text(encoding="utf-8")))
        for path in tasks.files()
    ]


def _dbt_tasks() -> list[tuple[str, str]]:
    """Each `(where, environment_key)` a `dbt_task` runs under."""
    found: list[tuple[str, str]] = []
    for where, _text in _files():
        for key, body in tasks.task_blocks(tasks.REPO_ROOT / where):
            if "dbt_task" not in _COMMENT.sub("", body):
                continue
            named = _KEY.search(_COMMENT.sub("", body))
            found.append((f"{where}::{key}", named.group(1).strip() if named else ""))
    return found


DBT = _dbt_tasks()


def test_there_is_a_dbt_task_to_check() -> None:
    """An empty population passes every assertion below it and proves nothing."""
    assert DBT, (
        "no task under infra/ runs dbt. Either the analytical models are built some other way "
        "now — which is a finding — or this reader stopped seeing the task."
    )


@pytest.mark.parametrize(("where", "key"), DBT, ids=[w for w, _k in DBT])
def test_a_dbt_task_names_an_environment_that_declares_a_dependency(where: str, key: str) -> None:
    assert key, f"{where} is a dbt task naming no environment at all."

    declared = {
        name.strip(): spec for _w, text in _files() for name, spec in _ENVIRONMENT.findall(text)
    }
    spec = declared.get(key)
    assert spec is not None, (
        f"{where} names the environment {key} and no `environment` block declares it."
    )
    assert "dependencies" in spec, (
        f"{where} runs in {key}, whose spec declares no dependencies.\n\n"
        "The serverless base image has no dbt in it: the task fails with `dbt: command not "
        "found` from `dbt deps`, after everything upstream of it has succeeded. Declare the "
        "adapter in that environment's spec — and keep it out of the one every other task "
        "shares, so eight tasks do not resolve a package one of them runs."
    )
