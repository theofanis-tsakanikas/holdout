"""One shard's draws, written to a file and read back by whatever combines them.

`make claim-2` runs the whole system 456 times and then plants eight mutations against it. The
draws are independent of one another — a lottery seed is a lottery seed — so they can be
produced on several machines and judged on one. This module is only the transport.

**Pickle, for the same reason `cache.py` uses it.** A `DrawRecord` carries `Fraction` fields,
which JSON cannot hold without a converter that would then be a second definition of what a
draw is. Nothing here is committed and nothing crosses a version boundary: every shard and the
combine step run the same tree, and the digest below is what enforces that rather than trust.

**What a file must carry beyond the draws.** A shard produced from a different tree, or from a
different shard count, would combine into a plausible number rather than an error — the same
failure `gather` refuses positionally. So each file declares the configuration it came from and
the source digest the world cache is keyed on, and the reader refuses a set that disagrees.
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from evals.uplift import cache
from evals.uplift.checks import ShardError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from evals.uplift.checks import Configuration, Shard
    from evals.uplift.harness import DrawRecord

#: Bumped when the payload's shape changes. A reader that meets a version it does not know
#: refuses rather than unpickling something it will misread.
FORMAT = "holdout-uplift-shard@1"


@dataclass(frozen=True, slots=True)
class Part:
    """One shard's contribution: which slice it was, and the draws it produced."""

    label: str
    scale: str
    index: int
    count: int
    digest: str
    draws: tuple[tuple[int, DrawRecord], ...]


def write(
    path: Path,
    *,
    configuration: Configuration,
    shard: Shard,
    draws: Sequence[tuple[int, DrawRecord]],
) -> Path:
    part = Part(
        label=configuration.label,
        scale=configuration.scale,
        index=shard.index,
        count=shard.count,
        digest=cache.source_digest(),
        draws=tuple(draws),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        pickle.dumps({"format": FORMAT, "part": part}, protocol=pickle.HIGHEST_PROTOCOL)
    )
    return path


def read(path: Path) -> Part:
    try:
        payload = pickle.loads(path.read_bytes())
    except Exception as error:
        raise ShardError(f"{path} cannot be read as a shard: {error}") from error
    if not isinstance(payload, dict) or payload.get("format") != FORMAT:
        raise ShardError(f"{path} is not a {FORMAT} file")
    part = payload["part"]
    if not isinstance(part, Part):
        raise ShardError(f"{path} does not carry a shard")
    return part


def parts(paths: Sequence[Path]) -> list[Part]:
    """Every file, checked as a *set* rather than one at a time.

    Three things are refused here, and each of them would otherwise produce a number instead of
    an error: shards from different trees, shards that disagree about how many there are, and a
    set that is not all of them. The third is the one a CI matrix can produce by having a job
    fail while the combine step still runs.
    """
    if not paths:
        raise ShardError("no shard files were given, so there is nothing to combine")
    found = [read(path) for path in paths]

    digests = {part.digest for part in found}
    if len(digests) > 1:
        raise ShardError(
            f"the shards were produced from {len(digests)} different trees — digests "
            f"{sorted(digests)}. A draw from one tree combined with a draw from another is a "
            "rate over two systems."
        )
    counts = {part.count for part in found}
    if len(counts) > 1:
        raise ShardError(f"the shards disagree about how many there are: {sorted(counts)}")
    labels = {(part.label, part.scale) for part in found}
    if len(labels) > 1:
        raise ShardError(f"the shards came from different configurations: {sorted(labels)}")

    count = counts.pop()
    seen = sorted(part.index for part in found)
    if len(seen) != len(set(seen)):
        raise ShardError(f"a shard index was delivered twice: {seen}")
    if seen != list(range(count)):
        absent = [index + 1 for index in range(count) if index not in set(seen)]
        raise ShardError(
            f"{len(absent)} of {count} shard(s) are missing — {absent}. Every rate this eval "
            "publishes has the number of draws as its denominator, so combining what arrived "
            "would report a plausible figure over a smaller experiment."
        )
    return found
