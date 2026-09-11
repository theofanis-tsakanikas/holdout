"""`python -m evals.design.machinery` — the same checks at one lottery per design.

**This is the module a planted mutation names.** `gate-proof` runs the eval once per mutation
inside its cap, and the published configuration draws four lotteries per design under two
violations, which is minutes. `contracts/design/design_harness.yaml`'s `machinery` block
declares one lottery instead; the checks are the same code with the same ids, and what a rate
would mean at one draw is said in each figure rather than printed as though it meant the same.
"""

from __future__ import annotations

import sys

from evals.design.checks import machinery, run
from evals.report import main
from holdout.contracts.loader import load

if __name__ == "__main__":
    sys.exit(main(run(machinery(load())), sys.argv[1:]))
