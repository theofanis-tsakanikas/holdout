"""`python -m evals.uplift.machinery` — the same named checks, at a small declared configuration.

**This is the only module a planted mutation names.** `evals/gate_proof` runs an eval as a
subprocess under a cap the published harness cannot meet and should not try to: two hundred
draws across six worlds is minutes, and it runs once per mutation.

What is smaller is the number of world seeds and lotteries, and both come from
`contracts/design/aa_harness.yaml`'s `machinery` block. **The scale is not smaller.** Several
checks need a readout that produces a number, and that needs the roster and the signal the
published scale supplies — at any scale cheap enough to skip the world cache the balance check
refuses every draw, which would leave `U4`, `U6` and `U8` with no mutation at all: three gates
never shown to bite. It is affordable because world generation is outside the mutation loop and
`cache.py` keys its entries on a digest of every file they were produced by, so a mutation to
the corpus or to the code that grouped it regenerates and everything else reads back.

The rate-shaped checks — `U1`, `U2`, `U3` — are **absent** here rather than computed on a
handful of draws and printed as though they meant the same thing. `U4` stays, because it was
restated as a binomial test at a declared level: a fixed tolerance would have been a different
check at the two draw counts and a test at a level is one instrument at any.
"""

from __future__ import annotations

import sys

from evals.report import main
from evals.uplift.checks import machinery, run
from holdout.contracts.loader import load

if __name__ == "__main__":
    contracts = load()
    sys.exit(main(run(machinery(contracts.aa_harness), contracts=contracts), sys.argv[1:]))
