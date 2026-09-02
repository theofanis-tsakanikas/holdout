"""Sharding moves where the draws are produced. It may not move a single number.

`make claim-2` is the most expensive target in the repository and its draws are independent, so
they can be produced on several machines and judged on one. The whole risk is that the split
changes an answer: every rate this eval publishes has a **count of draws** as its denominator —
`U1`'s `8/200`, `U10`'s `0 of 15,360` — and a boundary that loses or duplicates a draw produces
a *plausible number* rather than an error.

**So the guarantee is exact rather than statistical: the combined output equals the unsharded
output byte for byte.** That is available because the machinery is deterministic — the same tree
on two runners in different regions, 1.69x apart in wall clock, produces identical result lines
and the same sha256. Most refactors cannot be tested this way; this one can, so it is.

These run at the **machinery** configuration rather than the published one. The published
harness is 456 draws and minutes; the property under test is arithmetic about positions and
denominators, and it holds or fails identically at either size. `test_the_published_shape_is_the`
`_one_that_ships` is what stops that being a hole: the sizes and the shard arithmetic of the
*published* configuration are asserted without running it.

**And the machinery configuration is still minutes, which is why this file is marked.** Measured
on one machine with a cold cache: the suite is 1m36s without this file and 8m14s with it, and
~200s of the difference is generating the machinery worlds — which the `gate` job caches nowhere,
so it pays that on every run. The first CI run carrying this file cancelled `make check` at its
fifteen-minute budget with the whole shard matrix already green.

So the file carries `claim_2` and `make test` deselects it: this is claim 2's evidence, and
`make check`'s own closing line has always said the claim targets are not in the suite because
they take minutes. It runs in `make claim-2` and in `make claim-2-combine`, which is the target
CI actually runs once a claim is sharded. Two gates keep that from being a deselection nobody
notices — `ops/figures.py`'s `suite` row and `tests/ops/test_ci_sharding.py` — and both are
named here because a test that runs nowhere reads exactly like a test that passes.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from evals.report import as_json
from evals.uplift import checks, shards

from holdout.contracts.loader import ContractSet, load

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Every test in this file is claim 2's, not the suite's. See the note at the top of the module
#: for what it costs and for the two gates that require it to be run somewhere.
pytestmark = pytest.mark.claim_2


@pytest.fixture(scope="module")
def contracts() -> ContractSet:
    return load()


@pytest.fixture(scope="module")
def configuration(contracts: ContractSet) -> checks.Configuration:
    return checks.machinery(contracts.aa_harness)


# ------------------------------------------------------------------ the property that matters


@pytest.mark.parametrize("count", [1, 3, 8])
def test_the_combined_report_equals_the_unsharded_one_byte_for_byte(
    contracts: ContractSet, configuration: checks.Configuration, count: int
) -> None:
    """The whole claim of the branch, driven at three shard counts.

    `count=1` is not a degenerate case worth skipping: it is the one that proves the shard path
    and the plain path meet, so a defect in the machinery rather than in the boundary is caught
    without the boundary being involved.
    """
    whole = as_json(checks.report(checks.draws(configuration), configuration, contracts=contracts))

    parts = [
        checks.shard_draws(configuration, checks.Shard(index=index, count=count))
        for index in range(count)
    ]
    combined = as_json(
        checks.report(checks.gather(parts, configuration), configuration, contracts=contracts)
    )

    assert json.dumps(combined, indent=2) == json.dumps(whole, indent=2), (
        f"{count} shard(s) produced a different report from the unsharded run. A rate whose "
        "denominator is a count of draws changes silently when a draw moves"
    )


def test_every_draw_is_delivered_exactly_once(configuration: checks.Configuration) -> None:
    """The partition is a partition — driven, because *round-robin* is easy to write wrong."""
    expected = len(checks._expanded(configuration))
    for count in (1, 2, 3, 5, 8, 13):
        positions = [
            position
            for index in range(count)
            for position, _ in _positions(configuration, checks.Shard(index=index, count=count))
        ]
        assert sorted(positions) == list(range(expected)), (
            f"{count} shards do not partition {expected} draws"
        )


def _positions(configuration: checks.Configuration, shard: checks.Shard) -> list[tuple[int, str]]:
    """The positions a shard would run, without running them."""
    return [
        (position, seed)
        for position, (_task, seed) in enumerate(checks._expanded(configuration))
        if position % shard.count == shard.index
    ]


# --------------------------------------------------------- what a missing shard must not do


def test_a_missing_shard_is_refused_rather_than_averaged_over(
    configuration: checks.Configuration,
) -> None:
    """The failure this whole file exists for: a smaller experiment reported as the whole one.

    A CI matrix produces exactly this shape — one job fails or is cancelled, and the combine
    step runs on what arrived. `U1`'s `8/200` over 150 draws is still a rate, still prints, and
    is a rate about an experiment nobody designed.
    """
    parts = [
        checks.shard_draws(configuration, checks.Shard(index=index, count=3)) for index in range(3)
    ]
    with pytest.raises(checks.ShardError) as caught:
        checks.gather(parts[:-1], configuration)
    assert "not delivered by any shard" in str(caught.value)


def test_a_draw_delivered_twice_is_refused(configuration: checks.Configuration) -> None:
    """The other direction, which doubles a denominator instead of shrinking it."""
    part = checks.shard_draws(configuration, checks.Shard(index=0, count=2))
    with pytest.raises(checks.ShardError) as caught:
        checks.gather([part, part], configuration)
    assert "more than one shard" in str(caught.value)


@pytest.mark.parametrize("text", ["0/8", "9/8", "-1/4", "three/four", "8"])
def test_a_shard_that_cannot_exist_is_refused(text: str) -> None:
    with pytest.raises(checks.ShardError):
        checks.Shard.parse(text)


# ------------------------------------------------------------------ the files, checked as a set


def test_shards_from_different_trees_do_not_combine(
    tmp_path: Path, configuration: checks.Configuration
) -> None:
    """A digest mismatch is a rate over two systems, so it is refused before it is a number."""
    drawn = checks.shard_draws(configuration, checks.Shard(index=0, count=2))
    first = shards.write(
        tmp_path / "a.pickle", configuration=configuration, shard=checks.Shard(0, 2), draws=drawn
    )
    second = shards.write(
        tmp_path / "b.pickle", configuration=configuration, shard=checks.Shard(1, 2), draws=[]
    )
    part = shards.read(second)
    forged = shards.Part(
        label=part.label,
        scale=part.scale,
        index=part.index,
        count=part.count,
        digest="a digest from another tree",
        draws=part.draws,
    )
    import pickle

    second.write_bytes(pickle.dumps({"format": shards.FORMAT, "part": forged}))
    with pytest.raises(checks.ShardError) as caught:
        shards.parts([first, second])
    assert "different trees" in str(caught.value)


def test_a_set_that_is_not_all_of_them_is_refused(
    tmp_path: Path, configuration: checks.Configuration
) -> None:
    drawn = checks.shard_draws(configuration, checks.Shard(index=0, count=3))
    only = shards.write(
        tmp_path / "one.pickle", configuration=configuration, shard=checks.Shard(0, 3), draws=drawn
    )
    with pytest.raises(checks.ShardError) as caught:
        shards.parts([only])
    assert "shard(s) are missing" in str(caught.value)


def test_no_files_at_all_is_refused_rather_than_empty(tmp_path: Path) -> None:
    """An empty combine would report a claim over zero draws, which every check would pass."""
    with pytest.raises(checks.ShardError):
        shards.parts([])


def test_a_file_that_is_not_a_shard_is_refused(tmp_path: Path) -> None:
    rogue = tmp_path / "rogue.pickle"
    rogue.write_bytes(b"not a pickle at all")
    with pytest.raises(checks.ShardError):
        shards.read(rogue)


# --------------------------------------------- the published shape, asserted without running it


def test_the_published_shape_is_the_one_that_ships(contracts: ContractSet) -> None:
    """The tests above run at the machinery size; this is what stops that being a hole.

    The property under test is arithmetic about positions, so it holds identically at either
    size — but *which* size ships is a separate fact, and a published configuration that drifted
    to a different task decomposition would leave every test above green and true about
    something nobody runs.
    """
    published = checks.published(contracts.aa_harness)
    expanded = checks._expanded(published)
    assert len(checks._tasks(published)) == 18, "the published task decomposition moved"
    assert len(expanded) == 456, "the published draw count moved"

    for count in (8,):
        sizes = [
            len([p for p in range(len(expanded)) if p % count == index]) for index in range(count)
        ]
        assert sum(sizes) == len(expanded)
        assert max(sizes) - min(sizes) <= 1, (
            f"{count} shards split 456 draws into {sizes}, which is not even. Wall clock is the "
            "slowest shard, so an uneven split is most of the benefit lost"
        )


def test_the_cli_refuses_a_shard_without_an_output_file() -> None:
    """`--shard` writes draws; without `--out` there is nowhere for them to go.

    Driven through the real entry point rather than the function, because the flag handling is
    where a shard silently producing nothing would come from.
    """
    result = subprocess.run(
        [sys.executable, "-m", "evals.uplift", "--shard", "1/2"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=300,
    )
    assert result.returncode == 2, result.stdout
    assert "--out" in result.stderr
