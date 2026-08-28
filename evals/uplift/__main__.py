"""`python -m evals.uplift` — the published harness. Numbers, not a green tick.

`make claim-2` runs this and then plants the mutations that show each gate bites. What it
prints is what CLAUDE.md asks for: the false-positive rate on an A/A split against the declared
alpha, the false-refusal rate on the world where everything works, estimator bias, and interval
coverage — with the figure beside every check whether it passed or failed.
"""

from __future__ import annotations

import sys

from evals.report import main
from evals.uplift.checks import published, run
from holdout.contracts.loader import load

if __name__ == "__main__":
    # `multiprocessing` spawns on macOS and on Python 3.14 everywhere, so a worker re-imports
    # this module. The guard is what stops it re-running the harness inside every worker.
    contracts = load()
    sys.exit(main(run(published(contracts.aa_harness), contracts=contracts), sys.argv[1:]))
