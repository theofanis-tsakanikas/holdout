"""The packer's own properties, at the level where they are now decided.

`tests/ops/test_ci_sharding.py` runs `discover`'s shell and asks what the matrix contains. That
harness can still see whether entries carry a namespace, because it reads what was emitted — but
it can no longer see **why**, since `T00M` moved the decision out of `ci.yml` and into
`ops/ci_pack.py`. The attack that used to blank `--arg slug "tests"` is aiming at text that no
longer decides anything.

**So the properties are asserted here, against the function that decides them**, and the
emission harness keeps the two attacks it can still express: the packed entries discarded, and a
packer standing in for the real one with the namespaces stripped.
"""

from __future__ import annotations

import pytest

from ops import ci_pack

REAL = (ci_pack.REPO_ROOT / ci_pack.MAKEFILE).read_text(encoding="utf-8")

#: Every unsharded target this tree packs today. Written out rather than derived, because the
#: derivation is `discover`'s and this file is checking the packer rather than the discovery —
#: `test_ci_sharding.py` is where the two are compared.
TARGETS = [
    "claim-1",
    "claim-2-tests",
    "claim-3",
    "claim-4",
    "claim-7",
    "gate-proof",
    "gold",
    "silver",
]


def test_the_budget_and_the_ceiling_are_both_declared() -> None:
    """Neither is guessed at, and the ceiling is above the budget by construction.

    They are different questions — the budget is where the packer stops adding, the ceiling is
    where a bin starts costing the run — and a tree where the ceiling had fallen below the
    budget would be packing bins it then fails for being packed.
    """
    assert ci_pack.budget(REAL) > 0
    assert ci_pack.ceiling(REAL) > ci_pack.budget(REAL), (
        "the ceiling is not above the budget, so the packer would fill bins past the point at "
        "which each one fails itself"
    )


def test_a_tree_that_declares_neither_is_refused_rather_than_packed_anyway() -> None:
    """An unpacked matrix is *correct* and silently asks for one machine per target.

    That is the arrangement `T00M` replaced, so falling back to it would undo the change
    without anything going red — the shape this repository files most often.
    """
    with pytest.raises(ci_pack.DeclarationMissingError, match="CI_ENTRY_BUDGET"):
        ci_pack.pack(TARGETS, "nothing is declared here\n")
    with pytest.raises(ci_pack.DeclarationMissingError, match="CI_ENTRY_CEILING"):
        ci_pack.ceiling("nothing is declared here\n")


def test_every_bin_is_within_the_budget_and_every_target_is_in_exactly_one() -> None:
    """The two things a packer must not get wrong: overfill a bin, or lose a target."""
    limit = ci_pack.budget(REAL)
    bins = ci_pack.pack(TARGETS, REAL)
    placed = [target for one in bins for target in one]
    assert sorted(placed) == sorted(TARGETS), "a target was lost or duplicated by the packing"
    for one in bins:
        total = sum(ci_pack.cost(REAL, t, default=limit) for t in one)
        assert len(one) == 1 or total <= limit, f"{one} sums to {total}, over the {limit}s budget"


def test_a_target_costing_more_than_the_budget_is_its_own_bin() -> None:
    """A signal rather than an error — at a budget of 700, `claim-1` at 712 already is one."""
    tight = REAL.replace("CI_ENTRY_BUDGET := 800", "CI_ENTRY_BUDGET := 700")
    bins = ci_pack.pack(TARGETS, tight)
    assert ["claim-1"] in bins, bins


def test_an_undeclared_cost_is_packed_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    """**Unmeasured means unpacked**, and the direction is the whole of the choice.

    An unknown treated as *cheap* would pack a new target into a bin it might blow, and the
    failure would be a red run somebody has to diagnose. An unknown treated as the whole budget
    costs one machine and nothing else, until somebody measures it — which is what makes a new
    target need no packing decision from anybody.
    """
    del monkeypatch
    limit = ci_pack.budget(REAL)
    assert ci_pack.cost(REAL, "claim-5", default=limit) == limit
    bins = ci_pack.pack([*TARGETS, "claim-5"], REAL)
    assert ["claim-5"] in bins, bins


def test_the_packing_is_a_pure_function_of_the_declared_numbers() -> None:
    """Determinism is not tidiness here: a bin's slug is its contents and the slug is a cache key.

    A packing that reshuffled between runs would leave every world cache cold. That is measured
    rather than feared — it is what changing `CLAIM_2_SHARDS` from 8 to 7 did to seven caches on
    the branch before this one.
    """
    first = ci_pack.entries(TARGETS, REAL)
    assert first == ci_pack.entries(list(reversed(TARGETS)), REAL), (
        "the packing depends on the order it was handed, so the matrix — and every bin's cache "
        "namespace — would change on a reordering that changed no cost"
    )


def test_every_entry_carries_a_distinct_and_non_empty_namespace() -> None:
    """`actions/cache` is first-writer-wins, so two entries on one key is one of them lost.

    This is the property whose attack used to live in `ci.yml` and could not follow it here.
    """
    slugs = [entry["slug"] for entry in ci_pack.entries(TARGETS, REAL)]
    assert all(slugs), "an entry has no cache namespace and would race the others for the key"
    assert len(slugs) == len(set(slugs)), f"two entries share a namespace: {sorted(slugs)}"


def test_the_entry_runs_every_target_in_its_bin() -> None:
    """`make ${{ matrix.target }}` is unquoted, so a bin is a space-separated target list."""
    for entry in ci_pack.entries(TARGETS, REAL):
        assert entry["target"].split(), "an entry runs no target at all"
        assert entry["target"] == entry["name"]
    ran = [t for entry in ci_pack.entries(TARGETS, REAL) for t in entry["target"].split()]
    assert sorted(ran) == sorted(TARGETS)
