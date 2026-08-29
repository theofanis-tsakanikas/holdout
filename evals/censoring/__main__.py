"""`python -m evals.censoring` — the numbers, and an exit code."""

from __future__ import annotations

import sys

from evals.censoring.checks import run
from evals.report import main

if __name__ == "__main__":
    sys.exit(main(run(), sys.argv[1:]))
