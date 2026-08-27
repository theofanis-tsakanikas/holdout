"""`python -m evals.gate_proof` — the ledger; `--claim N` — the executor.

Two jobs, one module, and which one runs is decided by whether a claim was named. That is
the whole of the arrangement `ledger.py` audits: `make claim-N` names a claim and executes
that claim's mutations; `make gate-proof` names none and executes nothing.
"""

from __future__ import annotations

import re
import sys

from evals.gate_proof.engine import run
from evals.gate_proof.ledger import audit
from evals.report import main

_CLAIM = re.compile(r"^--claim(?:=(\d+))?$")


def _requested_claim(argv: list[str]) -> int | None:
    for index, argument in enumerate(argv):
        match = _CLAIM.match(argument)
        if not match:
            continue
        if match.group(1) is not None:
            return int(match.group(1))
        if index + 1 < len(argv):
            return int(argv[index + 1])
        raise SystemExit("--claim needs a claim number")
    return None


if __name__ == "__main__":
    claim = _requested_claim(sys.argv[1:])
    report = run(claim) if claim is not None else audit()
    sys.exit(main(report, sys.argv[1:]))
