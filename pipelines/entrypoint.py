"""The file a Databricks task runs, so that the module it runs stays a module.

**Every entry point under `pipelines/` imports `pipelines.…`**, which requires the repository root
on `sys.path`. `python -m` puts it there; a `spark_python_task` runs a **file**, and whether the
Git checkout's root ends up importable is a property of the runtime rather than of this
repository.

**That is an assumption, and an assumption costs a dispatch to test.** `backfill` takes about
ninety minutes to reach its second job, so *"probably importable"* is not a thing worth finding
out at that price. This file removes the question: it puts its own parent's parent on `sys.path`
and then runs the module by name, which is exactly what `-m` does.

## Why not a wheel

A `python_wheel_task` would also work and would put a build, an upload and a version between the
code and the run — three places the artefact can differ from the tree. `infra/pipelines/jobs.tf`
argues that at length for `git_source`, and this keeps that argument intact: the task runs the
tree, and the tree is what CI proved.

## Usage

    entrypoint.py  <module>  [arguments…]

The first parameter is the module, the rest are handed to it untouched, with `sys.argv[0]`
rewritten so that a module printing its own usage names itself rather than this file.
"""

from __future__ import annotations

import inspect
import runpy
import sys
from pathlib import Path


def here() -> Path:
    """This file's own path, however the runtime chose to execute it.

    **`__file__` is not always bound, and the first version of this file assumed it was.**
    Databricks' serverless task runner does not import the file and does not run it as a script:
    it reads the bytes and `exec`s the compiled object inside a kernel —

        with open(filename, "rb") as f:
          exec(compile(f.read(), filename, 'exec'))

    — and `exec` binds no `__file__`. So the file added to remove an assumption about the runtime
    failed on an assumption about the runtime, with `NameError: name '__file__' is not defined`,
    in the first seconds of a `backfill` that had already spent an environment approval.

    **`compile(..., filename, ...)` records the path even so**, on the code object, and a frame
    carries its code object. That is the same path `__file__` would have held — measured on the
    estate: `/Workspace/Repos/.internal/<sha>/pipelines/entrypoint.py`.

    `__file__` is still preferred where it exists, because it is the answer the language
    guarantees; the frame is the fallback for the runtimes that do not bind it.
    """
    named = globals().get("__file__")
    if named:
        return Path(named).resolve()
    frame = inspect.currentframe()
    if frame is None:  # pragma: no cover - every CPython this runs on has frames
        raise RuntimeError(
            "this interpreter exposes neither __file__ nor a call frame, so the entrypoint "
            "cannot find the repository root it exists to put on sys.path."
        )
    return Path(frame.f_code.co_filename).resolve()


def roots() -> list[Path]:
    """Every directory this repository is importable from, in the order they must be searched.

    **Two, and the second is not optional.** `pipelines`, `corpus`, `ops` and `evals` are packages
    in the tree; `holdout` is not — `pyproject.toml` declares a `src/` layout, so `import holdout`
    resolves only with `src/` on the path. Seven modules under `pipelines/` import it, including
    `pipelines/gold/assignment.py` and every file in `pipelines/ml/`, which is the training job.

    **On a laptop and in CI this is invisible**, because `uv sync` installs the project and
    `holdout` is importable from site-packages. On the estate nothing is installed: the task runs
    a git checkout, and what is importable is exactly what this function returns. So the failure
    would have been `ModuleNotFoundError: No module named 'holdout'`, inside a job, in the layer
    that trains the model — three jobs and about an hour after the run began.
    """
    root = here().parents[1]
    return [root, root / "src"]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(__doc__)
        print("error: the first argument is the module to run, e.g. pipelines.ingest.bulk")
        return 2

    module, rest = args[0], args[1:]

    # Inserted at the front rather than appended, so a same-named package installed in the
    # runtime cannot shadow the checkout the task was pinned to. Reversed, so that after both
    # insertions the list reads in the order `roots()` declares.
    for path in reversed(roots()):
        entry = str(path)
        if entry not in sys.path:
            sys.path.insert(0, entry)

    # **`sys.argv[0]` becomes the module**, because every one of these parsers is built with
    # `prog=` set from its own name and a usage line naming `entrypoint.py` would send a reader to
    # the wrong file.
    sys.argv = [module, *rest]
    runpy.run_module(module, run_name="__main__", alter_sys=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
