"""One writer per world-cache key, and one digest across all of them.

Until claim 2 was sharded there was exactly **one** job that generated worlds, so one key had
one writer and nobody had to say so. That property was an accident of how the work happened to
be arranged, and sharding is what ends it.

`actions/cache` is **first-writer-wins**: it reserves a key, and a later job that finds it taken
skips saving. Read off this repository's own run `33457341968`, where the digest had moved and
the cache was cold —

    claim-2  01:05:53  Cache not found for input keys: worlds-Linux-d5d27bdc...
    claim-2  01:59:34  Cache saved with key: worlds-Linux-d5d27bdc...
    claim-3  01:13:25  job ends, no save at all, 46 minutes earlier

— so with N shards on one key, the **first shard to finish** would take it with its own partial
slice, and the complete set would never be written at all.

**So the properties below are enforced rather than commented.** Somebody consolidating the keys
back into one for simplicity would be removing a property they cannot see, because the version
they are simplifying to also worked — until there were two writers.

**And one of them is the way this design goes silently wrong.** The combine job holds different
*contents* — counterfactual worlds no draw shard produces — but it has the **same dependency**:
anything that can change a world. A combine key derived from anything narrower would let a
world-source change move the shard keys while leaving the combine restoring counterfactual
worlds built by the previous generator. That is not a slow run. It is a wrong answer with no
red, which is `evals/uplift/cache.py`'s own narrowing warning arriving in the key this workflow
adds rather than the one T00G fixed.

**Each check is a function of a path, and it has two callers**: a test that runs it against
`ci.yml`, and an attack that runs it against a deliberately broken copy. `make gate-proof` does
this for a claim's gates; `CLAUDE.md` names tests as the layer nothing does it for, so the
attacks live beside the guards here rather than nowhere.

What this does **not** cover: it reads the key *expressions*. It cannot see what GitHub actually
reserved at run time, which is a fact about the forge that no file in this tree carries —
`docs/reviews/phase-1.md` §2d is what it costs to assume otherwise.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

#: The one expression every world-cache key must contain: the digest `evals/uplift/cache.py`
#: computes over everything a world is produced by. Named exactly rather than matched loosely,
#: so a key that switched to some other digest fails instead of passing on the word "digest".
DIGEST = "steps.worlds.outputs.digest"


def _jobs(path: Path) -> dict[str, Any]:
    jobs: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))["jobs"]
    return jobs


def _world_cache_keys(path: Path) -> dict[str, str]:
    """Every `actions/cache` step whose path is `.worlds`, by the job that holds it."""
    found: dict[str, str] = {}
    for name, job in _jobs(path).items():
        for step in job.get("steps") or []:
            if "actions/cache@" not in str(step.get("uses", "")):
                continue
            with_ = step.get("with") or {}
            if str(with_.get("path", "")).strip() == ".worlds":
                found[name] = str(with_["key"])
    return found


# --------------------------------------------------------------- the checks, as plain functions


def check_one_digest(path: Path) -> None:
    """Same invalidation, different namespace — the property, not the naming."""
    keys = _world_cache_keys(path)
    assert keys, "no job caches .worlds any more, so nothing here is checking anything"
    missing = sorted(job for job, key in keys.items() if DIGEST not in key)
    assert not missing, (
        f"{missing} cache `.worlds` under a key that does not carry {DIGEST!r}. The contents "
        "differ between the draw phase and the combine phase; the dependency does not."
    )


def check_shard_namespaced(path: Path) -> None:
    """Without this, N shards race for one key and the first partial slice wins it."""
    keys = _world_cache_keys(path)
    assert "claims" in keys, "the claims matrix no longer caches .worlds"
    assert "matrix.slug" in keys["claims"], (
        "the claims matrix caches .worlds under a key that does not vary by shard. "
        "`actions/cache` is first-writer-wins, so the first shard to finish would take the key "
        "with its own partial set of worlds and every later job would restore that."
    )


def check_combine_is_its_own_key(path: Path) -> None:
    """Two families, and they may not collide — which is what one writer per key means."""
    keys = _world_cache_keys(path)
    assert "combine" in keys, "the combine job no longer caches .worlds"
    assert keys["combine"] != keys["claims"], (
        "the combine job and the shard matrix use the same key expression, so they are two "
        "writers to one key again"
    )
    assert "matrix.slug" not in keys["combine"], (
        "the combine key varies by a shard slug it does not have"
    )


def check_families_share_a_prefix(path: Path) -> None:
    """Only the suffix may differ, because only the namespace differs.

    This is a string comparison and it fails the moment somebody derives the combine key
    separately — the tempting mistake, because *the combine has different inputs* is true about
    its contents and false about its dependency.
    """
    keys = _world_cache_keys(path)
    prefixes = {
        job: key[: key.index(DIGEST) + len(DIGEST)] for job, key in keys.items() if DIGEST in key
    }
    distinct = set(prefixes.values())
    assert len(distinct) == 1, (
        f"the world-cache keys are built from {len(distinct)} different prefixes: {prefixes}. "
        "Everything up to and including the digest must be identical."
    )


def check_the_draws_travel(path: Path) -> None:
    """A name that is written and a pattern that reads every one of them."""
    jobs = _jobs(path)
    uploads = [
        step
        for step in jobs["claims"]["steps"]
        if "actions/upload-artifact@" in str(step.get("uses", ""))
    ]
    downloads = [
        step
        for step in jobs["combine"]["steps"]
        if "actions/download-artifact@" in str(step.get("uses", ""))
    ]
    assert len(uploads) == 1 and len(downloads) == 1

    written = str(uploads[0]["with"]["name"])
    pattern = str(downloads[0]["with"]["pattern"])
    assert uploads[0]["with"]["if-no-files-found"] == "error", (
        "a shard that produced no draws uploads nothing and the combine would then refuse a "
        "set it was never given; the shard is the place that knows, so it fails there"
    )
    assert downloads[0]["with"]["merge-multiple"] is True, (
        "without merge-multiple the shards land in separate directories and the glob the "
        "combine target uses matches none of them"
    )
    stem = re.sub(r"\$\{\{[^}]*matrix\.slug[^}]*\}\}", "*", written)
    assert pattern == stem, (
        f"the combine downloads {pattern!r} but the shards upload {written!r}. A pattern that "
        "does not match every shard hands `gather` a partial set."
    )


def check_the_uploaded_path_survives_the_uploader(path: Path) -> None:
    """A path the uploader filters out is a job that succeeds and delivers nothing.

    `actions/upload-artifact` has excluded every path whose name begins with a dot since v4.4,
    and the filter runs **before** the glob is judged. `.shards/` is such a path, so the first
    sharded run wrote its draws on all eight machines and uploaded none of them --
    `shard 1/8: 57 draw(s) -> .shards/uplift-1-of-8.pickle`, the flag defaulting to false in the
    step's own printed inputs, and then `No files were found with the provided path`.

    **This check exists because the one above it did not cover this.**
    `check_the_draws_travel` asserts the artifact's *name* against the download's *pattern*,
    and `if-no-files-found`, and `merge-multiple` — every property of the naming. It was written
    by the session that had just fixed a naming defect, so it was written in the shape of what
    its author was thinking about, and the path was the half nobody was thinking about. The
    property is stated generally rather than as `.shards`: a dot anywhere in the path needs the
    flag, whatever the directory is later called.
    """
    jobs = _jobs(path)
    for name, job in jobs.items():
        for step in job.get("steps", []):
            if "actions/upload-artifact@" not in str(step.get("uses", "")):
                continue
            with_ = step.get("with", {})
            uploaded = str(with_.get("path", ""))
            hidden = [
                part
                for part in uploaded.split("/")
                if part.startswith(".") and part not in {".", ".."}
            ]
            if not hidden:
                continue
            assert with_.get("include-hidden-files") is True, (
                f"{name} uploads {uploaded!r}, whose component(s) {hidden} begin with a dot, "
                "without include-hidden-files. The uploader drops them before the glob is "
                "judged, so the step fails with `No files were found` on work that succeeded."
            )


def check_each_shard_has_its_own_context(path: Path) -> None:
    """A job's name is its check-run context name, so shards must not share one.

    Eight shards under `${{ matrix.target }}` put **eight contexts called `claim-2`** on one sha
    — the duplication `#39` removed, reintroduced by sharding at eight times the count. It was
    found by reading the first sharded run's **job list**, because `gh pr checks` collapses
    same-named contexts and showed nine where there were sixteen.
    """
    jobs = _jobs(path)
    name = str(jobs["claims"].get("name", ""))
    assert "matrix.name" in name, (
        f"the claims job is named {name!r}, which does not vary by shard. Every shard would "
        "report under one context name, and a checks list cannot show which of them failed."
    )


CHECKS: dict[str, Callable[[Path], None]] = {
    "one digest across every world-cache key": check_one_digest,
    "the shard key varies by shard": check_shard_namespaced,
    "the combine key is its own": check_combine_is_its_own_key,
    "the two families share a prefix": check_families_share_a_prefix,
    "every shard's draws reach the combine": check_the_draws_travel,
    "the uploaded path survives the uploader": check_the_uploaded_path_survives_the_uploader,
    "each shard reports under its own context": check_each_shard_has_its_own_context,
}


# ------------------------------------------------------------- caller one: `ci.yml` as it stands


@pytest.mark.parametrize("name", sorted(CHECKS))
def test_the_workflow_holds(name: str) -> None:
    CHECKS[name](CI_WORKFLOW)


# ----------------------------------------------- caller two: the same checks, on a broken copy


#: Each is a simplification somebody would plausibly make, and each removes a property that
#: cannot be seen from the version being simplified to — because that version also worked.
ATTACKS: dict[str, tuple[str, str]] = {
    "the two key families consolidated into one": (
        "worlds-${{ runner.os }}-${{ steps.worlds.outputs.digest }}${{ matrix.slug && "
        "format('-shard-{0}', matrix.slug) || '' }}",
        "worlds-${{ runner.os }}-${{ steps.worlds.outputs.digest }}",
    ),
    "the combine given its own, narrower digest": (
        "key: worlds-${{ runner.os }}-${{ steps.worlds.outputs.digest }}-combine",
        "key: worlds-${{ runner.os }}-${{ hashFiles('evals/uplift/checks.py') }}-combine",
    ),
    "the combine key made identical to the shard key": (
        "key: worlds-${{ runner.os }}-${{ steps.worlds.outputs.digest }}-combine",
        "key: worlds-${{ runner.os }}-${{ steps.worlds.outputs.digest }}${{ matrix.slug && "
        "format('-shard-{0}', matrix.slug) || '' }}",
    ),
    "the combine key given a different prefix": (
        "key: worlds-${{ runner.os }}-${{ steps.worlds.outputs.digest }}-combine",
        "key: combine-worlds-${{ runner.os }}-${{ steps.worlds.outputs.digest }}",
    ),
    "the download narrowed to one shard": (
        "pattern: draws-${{ matrix.target }}-*",
        "pattern: draws-${{ matrix.target }}-1-of-8",
    ),
    "the hidden-directory flag dropped": (
        "include-hidden-files: true",
        "include-hidden-files: false",
    ),
    "a shard that produced nothing allowed to pass": (
        "if-no-files-found: error",
        "if-no-files-found: warn",
    ),
    "every shard reporting under one context name": (
        "    name: ${{ matrix.name }}\n    needs: [discover]",
        "    name: ${{ matrix.target }}\n    needs: [discover]",
    ),
}


def _broken(attack: str, into: Path) -> Path:
    """One anchor, occurring **exactly once**, replaced.

    `== 1` rather than `in`, and the difference is not pedantry: the replacement takes the first
    occurrence, so an anchor that also appears in a comment above the step edits the comment and
    leaves the step intact. The attack then reports every check green and the test that reads
    that as *no guard exists* fires on a guard that is fine. It happened here, to
    `if-no-files-found: error`, in the same change that added the check two lines up — a comment
    was written quoting the value, and the attack silently started editing the prose.

    It is `docs/FINDINGS.md`'s own rule about anchors, arriving in a second population.
    """
    old, new = ATTACKS[attack]
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    found = text.count(old)
    assert found == 1, (
        f"the attack {attack!r} anchors on text occurring {found} time(s) in ci.yml. Zero means "
        "the anchor moved; more than one means the replacement may edit something that is not "
        "the step under attack, and the attack would then pass for the wrong reason."
    )
    into.write_text(text.replace(old, new, 1), encoding="utf-8")
    return into


def _bitten_by(attack: str, into: Path) -> set[str]:
    path = _broken(attack, into)
    bitten = set()
    for name, check in CHECKS.items():
        try:
            check(path)
        except (AssertionError, KeyError, ValueError):
            bitten.add(name)
    return bitten


@pytest.mark.parametrize("attack", sorted(ATTACKS))
def test_each_attack_is_refused_by_some_check(attack: str, tmp_path: Path) -> None:
    bitten = _bitten_by(attack, tmp_path / "ci.yml")
    assert bitten, (
        f"the attack {attack!r} left every check green, so none of them is the guard against it"
    )


def test_every_check_has_an_attack_that_bites_it(tmp_path: Path) -> None:
    """A guard with no attack is outside the net — this repository's own accounting, one layer
    down from `make gate-proof` refusing a claim target with nothing planted against it.

    A check that no attack can make fail has never been shown to bite, and looks identical to
    one that cannot.
    """
    bitten: set[str] = set()
    for index, attack in enumerate(sorted(ATTACKS)):
        bitten |= _bitten_by(attack, tmp_path / f"ci-{index}.yml")
    unbitten = sorted(set(CHECKS) - bitten)
    assert not unbitten, (
        f"{unbitten} are never made to fail by any attack, so nothing shows they bite where "
        "they claim to"
    )


# ------------------------------- the matrix derivation, computed twice and required to agree


#: How `discover` turns a target name into the Makefile variable that declares its shard count.
#: `claim-2` -> `CLAIM_2_SHARDS`. Written here as a second implementation of the workflow's own
#: `tr 'a-z-' 'A-Z_'`, so the two must agree rather than one being read off the other.
def _shard_variable(target: str) -> str:
    return target.upper().replace("-", "_") + "_SHARDS"


def _declared_shards(target: str, makefile: str | None = None) -> int:
    """What the Makefile declares for a target, or 1 where it declares nothing."""
    if makefile is None:
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    found = re.search(
        rf"^{_shard_variable(target)}[ \t]*:=[ \t]*(\d+)", makefile, flags=re.MULTILINE
    )
    return int(found.group(1)) if found else 1


def test_the_workflow_derives_the_variable_name_the_same_way_this_does() -> None:
    """The derivation is in `ci.yml` as shell and here as Python, and they must agree.

    If they drift, `discover` looks for a variable the Makefile does not define, finds nothing,
    and emits the target **unsharded**. That degrades safely — the claim is still proved, just
    on one machine — which is exactly why nothing would go red and why this exists.
    """
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "tr 'a-z-' 'A-Z_'" in workflow, (
        "ci.yml no longer derives the shard variable with `tr 'a-z-' 'A-Z_'`, so the "
        "derivation this file mirrors has moved and the two are no longer computed twice"
    )
    assert "_SHARDS" in workflow, "ci.yml no longer looks for a _SHARDS variable at all"


def test_claim_2_declares_the_shard_count_the_measurements_were_taken_at() -> None:
    """Eight, and it is chosen by the concurrency ceiling rather than by the work.

    A run is `discover + gate + secrets + entries + combines + claims-complete`. With five
    unsharded targets, eight shards and one combine that is **18** against this account's
    documented ceiling of 20 — one pull request fits with headroom and two do not, which is the
    one-branch-at-a-time practice this repository already follows.

    The number is asserted because the balance figures in the `Makefile` and in
    `evals/uplift/checks.py` were measured **at eight**, and a count that moved without them
    would leave two published figures describing a split nobody runs.
    """
    assert _declared_shards("claim-2") == 8

    unsharded = ("claim-1", "claim-3", "claim-4", "claim-7", "gate-proof")
    entries = sum(_declared_shards(t) for t in unsharded) + _declared_shards("claim-2")
    combines = sum(1 for t in (*unsharded, "claim-2") if _declared_shards(t) > 1)
    jobs = 3 + entries + combines + 1
    assert jobs <= 20, (
        f"a run would launch {jobs} jobs against a documented ceiling of 20. Past the ceiling "
        "the wall clock stops improving and only the flight count grows."
    )


# ---------------------------------- the target CI runs, which is not the target that is named


#: How a Makefile recipe declares which marks it hands pytest. The same shape `ops/figures.py`
#: reads, written again here rather than imported, because the two ask different questions of
#: it: that module asks whether *anything* runs a deselected test, and this one asks whether the
#: thing that runs it is the target this workflow invokes.
PYTEST_SELECTION = re.compile(r"""pytest\s+-m\s+(?:"(?P<quoted>[^"]+)"|(?P<bare>[\w.-]+))""")


def _selection_of(target: str, makefile: str) -> str | None:
    lines = makefile.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith(f"{target}:"):
            continue
        for following in lines[index + 1 :]:
            if not following.startswith("\t"):
                break
            found = PYTEST_SELECTION.search(following)
            if found is not None:
                return found.group("quoted") or found.group("bare")
        return None
    return None


def check_a_sharded_target_s_tests_run_where_ci_runs_them(makefile: str) -> None:
    """For a sharded claim, CI never runs the plain target — so it may not own the tests alone.

    `discover` emits `claim-2` and the matrix turns it into `claim-2-shard` on eight machines
    and `claim-2-combine` on one. `make claim-2` is what a laptop runs and what CI does not, so
    a mark selected only there is deselected from the suite by `make test` and selected by
    nothing on any push.

    `ops/figures.py`'s `suite` row cannot see this: it asks whether *some* `claim-*` target
    selects the mark, and `claim-2` is one. The two gates are the same question at different
    resolutions, and only this one knows that sharding changes which target is invoked.
    """
    named = re.finditer(r"^(?P<name>claim-\d+):", makefile, re.MULTILINE)
    for target in sorted({match.group("name") for match in named}):
        if _declared_shards(target, makefile) <= 1:
            continue
        plain = _selection_of(target, makefile)
        if plain is None:
            continue
        combine = _selection_of(f"{target}-combine", makefile)
        assert combine == plain, (
            f"{target} is sharded and selects tests with -m {plain!r}, but "
            f"{target}-combine selects {combine!r}. CI runs the shards and the combine and "
            f"never `make {target}`, so those tests would run on no push at all."
        )


def test_a_sharded_target_s_tests_run_where_ci_runs_them() -> None:
    check_a_sharded_target_s_tests_run_where_ci_runs_them(
        (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    )


def test_the_combine_dropping_the_tests_is_refused() -> None:
    """The attack, in the shape the other checks use: a Makefile with the line removed.

    It is separate from `ATTACKS` because that mechanism breaks `ci.yml`, and this check reads
    the `Makefile`. A check with no attack has never been shown to bite and looks identical to
    one that cannot, so it gets one here rather than none.
    """
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    dropped = makefile.replace(
        "claim-2-combine:  ## claim 2's checks over every shard's draws, then the mutations\n"
        "\t$(RUN) pytest -m claim_2\n",
        "claim-2-combine:  ## claim 2's checks over every shard's draws, then the mutations\n",
    )
    assert dropped != makefile, "the combine target no longer carries the line this attack removes"
    with pytest.raises(AssertionError, match="would run on no push"):
        check_a_sharded_target_s_tests_run_where_ci_runs_them(dropped)
