"""`python -m evals.uplift` — the published harness. Numbers, not a green tick.

`make claim-2` runs this and then plants the mutations that show each gate bites. What it
prints is what CLAUDE.md asks for: the false-positive rate on an A/A split against the declared
alpha, the false-refusal rate on the world where everything works, estimator bias, and interval
coverage — with the figure beside every check whether it passed or failed.

Three ways to run it, and the first two exist only so the third is faster on more machines:

    python -m evals.uplift                          the whole thing, one machine
    python -m evals.uplift --shard 3/8 --out FILE   that slice's draws, written to FILE
    python -m evals.uplift --combine FILE...        those draws, judged

**Sharding moves where the draws are produced and nothing else.** The checks run once, over
every draw, on the combining machine — so the split cannot change a rate by changing what a
denominator is computed over. `tests/evals/test_uplift_shards.py` requires the combined output
to equal the unsharded output **byte for byte**, which is available because the machinery is
deterministic across machines: two runners in different regions, 1.69x apart in wall clock,
produce identical result lines.

**A shard writes draws, never a verdict.** It prints no report and returns no exit code about
the claim, because a shard has seen a fraction of the experiment and any judgment it made would
be a judgment over a smaller one.
"""

from __future__ import annotations

import sys
from pathlib import Path

from evals.report import main
from evals.uplift import shards
from evals.uplift.checks import Shard, ShardError, gather, published, report, run, shard_draws
from holdout.contracts.loader import load


def _value(argv: list[str], flag: str) -> str | None:
    if flag not in argv:
        return None
    position = argv.index(flag) + 1
    if position >= len(argv):
        raise ShardError(f"{flag} was given with nothing after it")
    return argv[position]


def _entry(argv: list[str]) -> int:
    contracts = load()
    configuration = published(contracts.aa_harness)

    which = _value(argv, "--shard")
    if which is not None:
        out = _value(argv, "--out")
        if out is None:
            raise ShardError(
                "--shard needs --out, because a shard writes draws rather than a report"
            )
        shard = Shard.parse(which)
        drawn = shard_draws(configuration, shard)
        path = shards.write(Path(out), configuration=configuration, shard=shard, draws=drawn)
        print(f"shard {shard.index + 1}/{shard.count}: {len(drawn)} draw(s) -> {path}")
        return 0

    files = argv[argv.index("--combine") + 1 :] if "--combine" in argv else None
    if files is not None:
        paths = [Path(f) for f in files if not f.startswith("--")]
        parts = shards.parts(paths)
        records = gather((part.draws for part in parts), configuration)
        rest = [f for f in files if f.startswith("--")]
        return main(report(records, configuration, contracts=contracts), rest)

    return main(run(configuration, contracts=contracts), argv)


if __name__ == "__main__":
    # `multiprocessing` spawns on macOS and on Python 3.14 everywhere, so a worker re-imports
    # this module. The guard is what stops it re-running the harness inside every worker.
    try:
        sys.exit(_entry(sys.argv[1:]))
    except ShardError as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(2)
