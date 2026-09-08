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

import runpy
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(__doc__)
        print("error: the first argument is the module to run, e.g. pipelines.ingest.bulk")
        return 2

    module, rest = args[0], args[1:]

    # `parents[1]` is the repository root: this file is `pipelines/entrypoint.py`. Inserted at the
    # front rather than appended, so a same-named package installed in the runtime cannot shadow
    # the checkout the task was pinned to.
    root = str(Path(__file__).resolve().parents[1])
    if root not in sys.path:
        sys.path.insert(0, root)

    # **`sys.argv[0]` becomes the module**, because every one of these parsers is built with
    # `prog=` set from its own name and a usage line naming `entrypoint.py` would send a reader to
    # the wrong file.
    sys.argv = [module, *rest]
    runpy.run_module(module, run_name="__main__", alter_sys=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
