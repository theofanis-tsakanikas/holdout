"""One fingerprint of the whole grid's lotteries — printed, so another interpreter can be asked.

`python -m evals.assignment.crossprocess` prints a single hex line and nothing else.

Why a second process at all
---------------------------
Claim 3's trap is that **calling the same function twice is not a check**. Calling it in
another process, under another `PYTHONHASHSEED`, is a different question: it asks whether the
answer depends on anything the interpreter chose rather than on the committed seed. Python
randomises string hashing per process by default, so a stratification that broke a tie by
whichever unit a `set` happened to offer first would answer differently here and identically
under any amount of in-process repetition.

That is not a hypothetical shape. `strata._greedy` holds its unmatched units in a `set` and
`strata._hardest_to_match` sorts them before scanning for exactly this reason — a claim its
own docstring makes, which is the shape `CLAUDE.md` says to distrust:

> **A guard tested by its author is tested in the shape the guard already handles.**

The fingerprint covers the strata as well as the arms, because the strata are the restriction
the lottery drew under and a moved boundary is a different set of admissible draws.
"""

from __future__ import annotations

from evals.assignment import build, reference
from holdout.contracts.loader import load


def fingerprint() -> str:
    """A digest of every configuration's strata and arms, in the grid's declared order."""
    contracts = load()
    parts: list[str] = []
    for configuration in build.configurations(contracts):
        parts.extend(("configuration", configuration.origin))
        drawn = build.run_the_lottery(configuration)
        if drawn.seal is None:
            parts.append("no admissible stratification")
            continue
        for stratum in drawn.seal.strata:
            parts.append("stratum")
            parts.extend(stratum)
        parts.append("arms")
        parts.extend(f"{unit}={drawn.seal.arms[unit].value}" for unit in drawn.seal.roster)
    return reference.digest(parts)


if __name__ == "__main__":
    print(fingerprint())
