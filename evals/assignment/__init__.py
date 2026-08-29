"""Claim 3 — the holdout is neither erased nor chosen after the fact.

Run it: `python -m evals.assignment` — or `make claim-3`, which also plants the mutations
that prove each gate bites.

**The trap, and it is not the one the other claims carry.** Claim 3's sentence is *assignment
from a committed seed, exactly reproducible*, and the obvious check — call `draw` twice and
compare — is a deterministic function repeated. It catches nothing. It would pass on a
lottery that ignored the seed, on a keyed hash keyed the wrong way round, on a framing that
cannot tell one roster from another, and on a "lottery" that simply gave the holdout to the
lowest-numbered store in each stratum.

So the independence arrives by three other doors, and `evals/assignment/README.md` says which
part of the claim each one carries: a second implementation of the draw over a BLAKE2b
written out from RFC 7693; the per-unit path a readout takes a month later, which never
consults the seal; and another interpreter, under another `PYTHONHASHSEED`, which is the only
way to see a tie broken by set-iteration order.

The rosters are not chosen here either. They are what survives `feasibility`'s automatic
neighbour exclusions on estates `corpus/world/chain.py` laid out — a generator that imports
nothing from `holdout` and whose author never saw this eval.
"""
