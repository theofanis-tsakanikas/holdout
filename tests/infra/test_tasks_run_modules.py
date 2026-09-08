"""Every Databricks task runs a module through the entrypoint, never a file directly.

**Every entry point under `pipelines/` imports `pipelines.…`**, which requires the repository root
on `sys.path`. `python -m` puts it there. A `spark_python_task` runs a **file**, and whether the
Git checkout's root ends up importable is a property of the runtime rather than of this
repository — an assumption, and one that costs a dispatch to test, because `backfill` takes about
ninety minutes to reach its second job.

`pipelines/entrypoint.py` removes the question: it puts the repository root on `sys.path` and runs
the named module, which is what `-m` does. **This asserts that every task goes through it.**

## Why a gate and not a convention

`infra/pipelines` and `infra/ml` hold five tasks today and the next layer will add more. The
failure is `ModuleNotFoundError` **inside a job**, which surfaces as a red task in a workflow that
has already spent an environment approval and, in `backfill`'s case, already loaded eight months
of history. **A task added the obvious way — naming the file it wants to run — reads as correct
in review**, which is exactly the shape a gate is for.

## What it does not check

- **It does not check that the module exists.** A typo in the module name fails at run time with
  a clear message; that is a different defect with a cheap signal.
- **It reads Terraform, not the account.** A task edited in the Databricks UI is invisible here —
  and `CLAUDE.md`'s rule is *IaC only, no console actions, ever*, so this checks the promise.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
INFRA = REPO_ROOT / "infra"

#: The one file a task may name.
ENTRYPOINT = "pipelines/entrypoint.py"

_PYTHON_FILE = re.compile(r'^\s*python_file\s*=\s*"([^"]+)"', re.MULTILINE)


def _python_files() -> list[tuple[str, str]]:
    """Every `(where, python_file)` any layer's Terraform names."""
    found: list[tuple[str, str]] = []
    if not INFRA.is_dir():
        return found
    for path in sorted(INFRA.glob("*/*.tf")):
        for match in _PYTHON_FILE.finditer(path.read_text(encoding="utf-8")):
            found.append((str(path.relative_to(REPO_ROOT)), match.group(1)))
    return found


FILES = _python_files()


def test_there_are_tasks_to_check() -> None:
    """An empty population passes every assertion below it and proves nothing."""
    assert (REPO_ROOT / ENTRYPOINT).is_file(), (
        f"{ENTRYPOINT} does not exist, so nothing below can be true. If it moved, this gate and "
        "every task move with it."
    )
    assert FILES, (
        "no layer under infra/ names a `python_file`. Either no Databricks task runs Python any "
        "more — which is a finding — or this reader stopped seeing them."
    )


@pytest.mark.parametrize(
    ("where", "python_file"),
    FILES,
    ids=[f"{w}::{f}" for w, f in FILES],
)
def test_a_task_runs_a_module_through_the_entrypoint(where: str, python_file: str) -> None:
    assert python_file == ENTRYPOINT, (
        f"{where} runs `{python_file}` directly. Every entry point under pipelines/ imports "
        "`pipelines.…`, which needs the repository root on sys.path — `python -m` puts it there "
        "and a spark_python_task does not.\n\n"
        f"Name `{ENTRYPOINT}` and pass the module as the first parameter:\n"
        f'    python_file = "{ENTRYPOINT}"\n'
        '    parameters  = ["pipelines.silver", "--bronze", …]\n\n'
        "The failure otherwise is ModuleNotFoundError inside a job, after the approval has been "
        "spent and — in backfill's case — after eight months of history have been loaded."
    )
