"""`python -m evals.assignment` — the numbers, and an exit code."""

from __future__ import annotations

import sys

from evals.assignment.checks import run
from evals.report import main

if __name__ == "__main__":
    sys.exit(main(run(), sys.argv[1:]))
