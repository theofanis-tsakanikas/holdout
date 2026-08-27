"""`python -m evals.gate_proof [--claim N]` — the verdicts, and an exit code."""

from __future__ import annotations

import sys

from evals.gate_proof.engine import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
