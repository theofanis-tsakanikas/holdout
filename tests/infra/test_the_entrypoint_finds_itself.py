"""The entrypoint locates the repository root when `__file__` is not bound.

**The file added to remove an assumption about the runtime failed on an assumption about the
runtime.** `pipelines/entrypoint.py` exists because a `spark_python_task` runs a *file* and every
entry point under `pipelines/` imports `pipelines.…`, which needs the repository root on
`sys.path`. It found that root with `Path(__file__)`.

Databricks' serverless task runner does not import the file and does not run it as a script. It
reads the bytes and `exec`s the compiled object inside a kernel:

    with open(filename, "rb") as f:
      exec(compile(f.read(), filename, 'exec'))

`exec` binds no `__file__`. So the first dispatch died in its first seconds with

    NameError: name '__file__' is not defined

after the workflow had asserted a green suite, taken an environment approval and assumed a role.

**`compile(..., filename, ...)` records the path anyway**, on the code object, and a frame carries
its code object — measured on the estate as
`/Workspace/Repos/.internal/<sha>/pipelines/entrypoint.py`. That is the fallback `here()` uses.

## What this does

Executes the real file the way the estate does — compiled, with a namespace carrying **no**
`__file__` — and asserts that `here()` still answers, and answers the repository root. Restoring
`Path(__file__)` turns it red with the same `NameError` the estate produced.

## What it does not check

- **It does not run a module through it.** `tests/infra/test_tasks_run_modules.py` asserts every
  task goes through this file; what the module then does is that module's own tests.
- **`__name__` is set to something other than `__main__`**, so the `raise SystemExit(main())` at
  the bottom does not fire. The estate does bind `__main__`; what is under test here is the path
  resolution, and running the whole entrypoint would need arguments and a Spark session.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT = REPO_ROOT / "pipelines" / "entrypoint.py"


def _executed_as_the_estate_does() -> dict[str, Any]:
    """The entrypoint's namespace after `exec(compile(...))`, with no `__file__` in it."""
    namespace: dict[str, Any] = {"__name__": "holdout_entrypoint_under_test"}
    source = ENTRYPOINT.read_text(encoding="utf-8")
    exec(compile(source, str(ENTRYPOINT), "exec"), namespace)
    return namespace


def test_the_entrypoint_exists() -> None:
    """An absent file makes every assertion below it vacuous."""
    assert ENTRYPOINT.is_file(), (
        f"{ENTRYPOINT} is gone. Every Databricks task names it — "
        "`tests/infra/test_tasks_run_modules.py` is what says so — and this gate moves with it."
    )


def test_it_is_executable_without_a_bound_file() -> None:
    namespace = _executed_as_the_estate_does()
    assert "__file__" not in namespace, (
        "this test bound `__file__` itself, so it is no longer reproducing the estate's "
        "condition and would pass against the defect it exists to catch."
    )
    assert "here" in namespace, "the entrypoint no longer exposes `here()`; this gate reads it."


def test_every_package_the_pipelines_import_is_reachable_from_those_roots() -> None:
    """The tree's packages and `holdout`, which lives under `src/` and is not installed there.

    **On a laptop and in CI this cannot fail**, because `uv sync` installs the project and
    `holdout` resolves from site-packages. On the estate nothing is installed: a task runs a git
    checkout, and what is importable is exactly what `roots()` returns. Seven modules under
    `pipelines/` import `holdout` — `pipelines/gold/assignment.py` and every file in
    `pipelines/ml/` among them — so a missing `src/` is `ModuleNotFoundError` in the layer that
    trains the model, three jobs and about an hour into a run.

    Asserted as **directories that contain the packages**, rather than by importing them: an
    import here would resolve from the installed project and prove nothing about the checkout.
    """
    namespace = _executed_as_the_estate_does()
    roots = [Path(p) for p in namespace["roots"]()]
    for package in ("pipelines", "corpus", "ops", "evals", "holdout"):
        assert any((root / package / "__init__.py").is_file() for root in roots), (
            f"`{package}` is importable from none of {[str(r) for r in roots]}.\n\n"
            "Every entry point a Databricks task runs imports from the checkout and nothing is "
            "installed there. A package missing from this list is ModuleNotFoundError inside a "
            "job, after the approval has been spent."
        )


def test_it_finds_the_repository_root_without_a_bound_file() -> None:
    namespace = _executed_as_the_estate_does()
    found = namespace["here"]().parents[1]
    assert found == REPO_ROOT, (
        f"the entrypoint located {found} and the repository root is {REPO_ROOT}.\n\n"
        "It puts that path on `sys.path` so `pipelines.…` imports resolve. A wrong root is "
        "`ModuleNotFoundError` inside a job, after the approval has been spent — and a missing "
        "one is `NameError: name '__file__' is not defined`, which is what the estate produced."
    )
