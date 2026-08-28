"""The one thing a cache may not do: hand a mutation the world it was built before.

`evals/uplift/cache.py` writes each world's grouped ledger once and reads it back, so that
`make claim-2`'s nine runs generate ten worlds rather than a hundred. The whole risk is the
exception — a mutation that changes the corpus, or the code that groups it, must be handed a
world built **after** it — and the failure is exact: such a mutation would report `SURVIVED`
while the thing it broke never ran. A gate silently disarmed, which is the defect this
repository has already paid for four times.

So the exception is not a list of paths somebody maintains. The key carries a digest of every
file the artefact was produced by, and this module drives it in **both** directions: a byte
changed in `corpus/` moves the key, a byte changed in a module the ledger does not come from
does not, and a value written under one key is never read under another.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from evals.uplift import cache, outcomes


@pytest.fixture
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path / "worlds")
    return tmp_path


def _ledger(marker: int) -> outcomes.Ledger:
    cell = ("ST0001", 2025, 36, "dairy")
    return outcomes.Ledger(
        revenue_cents={cell: marker},
        cogs_cents={cell: 0},
        waste_cents={cell: 0},
        dispatched={"ST0001": 1},
        acknowledged={"ST0001": 1},
        delivered={"ST0001": frozenset({"ladder_policy@v1"})},
    )


def test_a_second_ask_is_a_read_and_not_a_build(isolated: Path) -> None:
    builds = 0

    def build() -> tuple[outcomes.Ledger, ...]:
        nonlocal builds
        builds += 1
        return (_ledger(7),)

    first = cache.ledgers("w6", build)
    second = cache.ledgers("w6", build)
    assert builds == 1, "the cache built twice, so it is not one"
    assert first[0].revenue_cents == second[0].revenue_cents


def test_a_byte_changed_in_the_corpus_moves_the_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """The direction that matters: a mutation to `corpus/` must not read an older world.

    Driven by actually editing a file the digest covers, in a copy of the tree, rather than by
    asserting that the path is in a list. A list is the thing this design exists to not need.
    """
    before = cache.source_digest()
    target = cache.REPO_ROOT / "corpus" / "world" / "demand.py"
    original = target.read_bytes()
    try:
        target.write_bytes(original + b"\n# a mutation lands here\n")
        assert cache.source_digest() != before, (
            "a byte changed under corpus/ left the cache key where it was, so a mutation to "
            "the generator would be handed a world built before it and would report SURVIVED "
            "while the thing it broke never ran"
        )
    finally:
        target.write_bytes(original)
    assert cache.source_digest() == before


def test_the_grouping_module_is_covered_too() -> None:
    """`outcomes.py` produced what is stored, so an edit to it invalidates what is stored."""
    before = cache.source_digest()
    target = cache.REPO_ROOT / "evals" / "uplift" / "outcomes.py"
    original = target.read_bytes()
    try:
        target.write_bytes(original + b"\n# and here\n")
        assert cache.source_digest() != before
    finally:
        target.write_bytes(original)


def test_a_module_the_ledger_does_not_come_from_leaves_the_key_alone() -> None:
    """The other direction, and it is not decoration.

    A digest over the whole repository would invalidate every world on every mutation, which
    is a cache that never hits and a claim target that never finishes. `readout.py` is where
    four of the eight planted mutations live, and none of them can change a ledger.
    """
    before = cache.source_digest()
    target = cache.REPO_ROOT / "src" / "holdout" / "core" / "experiment" / "readout.py"
    original = target.read_bytes()
    try:
        target.write_bytes(original + b"\n# not a dependency of a grouped ledger\n")
        assert cache.source_digest() == before, (
            "an edit to a module no cached ledger is produced by moved the key. Every world "
            "would be regenerated for every mutation and the target would not finish"
        )
    finally:
        target.write_bytes(original)


def test_the_key_carries_both_what_was_asked_for_and_what_produced_it() -> None:
    assert cache.key("a", 1) != cache.key("a", 2)
    assert cache.key("a", 1) == cache.key("a", 1)
    assert cache.key("a", 1).endswith(cache.source_digest())


def test_a_cache_written_under_one_key_is_never_read_under_another(isolated: Path) -> None:
    cache.ledgers(cache.key("w6", "seed-a"), lambda: (_ledger(1),))
    other = cache.ledgers(cache.key("w6", "seed-b"), lambda: (_ledger(2),))
    cell = ("ST0001", 2025, 36, "dairy")
    assert other[0].revenue_cents[cell] == 2


def test_an_unreadable_entry_is_a_miss_and_never_a_failure(isolated: Path) -> None:
    """A cache that can fail a run is not an optimisation.

    Half a file is what an interrupted run leaves behind, and the next one has to treat it as
    a world it does not have rather than as a reason to stop.
    """
    cache.CACHE_DIR.mkdir(parents=True)
    (cache.CACHE_DIR / "broken.pickle").write_bytes(b"not a pickle at all")
    cell = ("ST0001", 2025, 36, "dairy")
    assert cache.ledgers("broken", lambda: (_ledger(3),))[0].revenue_cents[cell] == 3
