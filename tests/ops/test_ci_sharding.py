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

import json
import os
import re
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
_MAKEFILE = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

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
    """**Seven since `T011`, and every figure taken at eight is now marked as history.**

    This assertion exists so a count cannot move while figures describing the old one stand as
    present-tense measurements. It **fired** when `gold` became the twenty-first job and the
    shard count came down to make room, which is the assertion working rather than an
    inconvenience: the `Makefile`'s spread — `38 43 39 42 37 40 43 41`, max over min 1.16 — was
    taken over an eight-way split and is kept there per doctrine rule 4, with the restatement
    beside it saying what it now describes.

    **The job arithmetic that used to live here has moved to
    `test_the_run_stays_under_the_concurrency_ceiling`, which runs `discover` instead of
    re-deriving what it would emit.** Written out by hand it said 18 while the matrix said 19,
    for one entry, and the whole argument of this file is that a second hand-written derivation
    agrees with itself.
    """
    assert _declared_shards("claim-2") == 7


# ---------------------------------- the target CI runs, which is not the target that is named


#: How a Makefile recipe declares which marks it hands pytest. The same shape `ops/figures.py`
#: reads, written again here rather than imported, because the two ask different questions of
#: it: that module asks whether *anything* runs a deselected test, and this one asks whether the
#: thing that runs it is a target this workflow actually invokes.
PYTEST_SELECTION = re.compile(r"""pytest\s+-m\s+(?:"(?P<quoted>[^"]+)"|(?P<bare>[\w.-]+))""")

#: `$(MAKE) other-target` inside a recipe. Followed rather than ignored, because `claim-2` runs
#: its tests that way and a reader that stopped at the recipe would conclude it runs none.
MAKE_CALL = re.compile(r"^\t\$\(MAKE\)\s+(?P<target>[\w.-]+)\s*$")


def _recipe(target: str, makefile: str) -> list[str]:
    lines = makefile.splitlines()
    for index, line in enumerate(lines):
        if line.startswith(f"{target}:"):
            recipe = []
            for following in lines[index + 1 :]:
                if not following.startswith("\t"):
                    break
                recipe.append(following)
            return recipe
    return []


def _marks_reachable(target: str, makefile: str, seen: frozenset[str] = frozenset()) -> set[str]:
    """Every mark expression `make <target>` hands pytest, following `$(MAKE)` one target on."""
    if target in seen:
        return set()
    found: set[str] = set()
    for line in _recipe(target, makefile):
        selection = PYTEST_SELECTION.search(line)
        if selection is not None:
            found.add(selection.group("quoted") or selection.group("bare"))
        call = MAKE_CALL.match(line)
        if call is not None:
            found |= _marks_reachable(call.group("target"), makefile, seen | {target})
    return found


def _targets_ci_runs_for(target: str, makefile: str) -> list[str]:
    """What the matrix invokes for one claim target, which for a sharded one is never `make <t>`.

    `discover` emits `<t>-shard` per shard and `<t>-combine` once when `<T>_SHARDS` is above
    one, and a `<t>-tests` entry wherever the Makefile declares that rule. The plain target is
    what a laptop runs.
    """
    if _declared_shards(target, makefile) <= 1:
        return [target] + ([f"{target}-tests"] if _recipe(f"{target}-tests", makefile) else [])
    running = [f"{target}-shard", f"{target}-combine"]
    if _recipe(f"{target}-tests", makefile):
        running.append(f"{target}-tests")
    return running


def check_a_sharded_target_s_tests_run_where_ci_runs_them(makefile: str) -> None:
    """For a sharded claim, CI never runs the plain target — so it may not own the tests alone.

    `discover` emits `claim-2` and the matrix turns it into `claim-2-shard` on eight machines,
    `claim-2-combine` on one, and `claim-2-tests` on one more. `make claim-2` is what a laptop
    runs and what CI does not, so a mark reachable only from there is deselected from the suite
    by `make test` and selected by nothing on any push.

    `ops/figures.py`'s `suite` row cannot see this: it asks whether *some* `claim-*` target
    selects the mark, and `claim-2` is one. The two gates are the same question at different
    resolutions, and only this one knows that sharding changes which target is invoked.
    """
    named = re.finditer(r"^(?P<name>claim-\d+):", makefile, re.MULTILINE)
    for target in sorted({match.group("name") for match in named}):
        wanted = _marks_reachable(target, makefile)
        if not wanted:
            continue
        reached: set[str] = set()
        for runnable in _targets_ci_runs_for(target, makefile):
            reached |= _marks_reachable(runnable, makefile)
        adrift = sorted(wanted - reached)
        assert not adrift, (
            f"`make {target}` reaches {adrift}, and none of "
            f"{_targets_ci_runs_for(target, makefile)} does. CI runs those and never "
            f"`make {target}`, so those tests would run on no push at all."
        )


def test_a_sharded_target_s_tests_run_where_ci_runs_them() -> None:
    check_a_sharded_target_s_tests_run_where_ci_runs_them(_MAKEFILE)


def test_the_tests_target_running_nowhere_is_refused() -> None:
    """The attack, as a Makefile with the marked tests reachable only from the plain target.

    It is separate from `ATTACKS` because that mechanism breaks `ci.yml` and this check reads
    the `Makefile`. A check with no attack has never been shown to bite and looks identical to
    one that cannot.
    """
    stranded = _MAKEFILE.replace("\t$(MAKE) claim-2-tests\n", "\t$(RUN) pytest -m claim_2\n")
    stranded = stranded.replace("claim-2-tests:  ##", "claim-2-tests-disabled:  ##")
    assert stranded != _MAKEFILE, "the anchors this attack rewrites have moved"
    with pytest.raises(AssertionError, match="would run on no push"):
        check_a_sharded_target_s_tests_run_where_ci_runs_them(stranded)


# ------------------------------------- and `discover` is run rather than read


def _discovered(workflow_text: str | None = None) -> list[dict[str, str]]:
    """`discover`'s own shell, executed against this tree, and its matrix parsed.

    **Run rather than read.** Every other assertion in this file reads `ci.yml` as text or as
    YAML, which cannot see what the shell actually emits — the class `docs/reviews/phase-1.md`
    §2d names, where a fact about the forge is assumed from a file. This is the one question
    that can be taken away from that class cheaply: the step is a shell script with no network
    and no credentials, so it runs here.

    **And the limit that arrives with it, declared rather than discovered later: this check
    executes a shell fragment, so its answer is a property of the shell that runs it.** Reading
    text is the same everywhere; running `grep`, `jq`, `seq` and `tr` is not. This repository
    has been bitten three times in four days by an instrument whose answer depended on where it
    ran — `grep -P`, which BSD grep does not implement and which reported a count of zero from a
    check that never ran; `_layout_population`, which counted a gitignored directory on a laptop
    and not on a clean checkout; and the `main_guard` fixture, which assumed a git identity the
    runner did not have. Each passed where it was written.

    **So it is asserted on two platforms and only two**: `make check` runs it on the author's
    macOS and CI runs it on Linux, and the two differing is the whole of the coverage. A third
    shell is not covered, and if the emitted script ever needs a GNU-only flag or a collation
    order, this check answers differently on the two and the version that passes is the one it
    was written on. Where that happens the answer is to make the fragment portable or to say
    which platform this speaks for — not to widen the assertion until the difference fits.
    """
    workflow = yaml.safe_load(workflow_text or CI_WORKFLOW.read_text(encoding="utf-8"))
    steps = [s for s in workflow["jobs"]["discover"]["steps"] if s.get("id") == "read"]
    assert len(steps) == 1, "the discover step this test runs is no longer identifiable by id"
    with tempfile.TemporaryDirectory() as scratch:
        output = Path(scratch) / "output"
        summary = Path(scratch) / "summary"
        output.touch()
        summary.touch()
        completed = subprocess.run(
            ["bash", "-c", steps[0]["run"]],
            cwd=REPO_ROOT,
            env={
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "GITHUB_OUTPUT": str(output),
                "GITHUB_STEP_SUMMARY": str(summary),
            },
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, (
            f"discover's own shell exited {completed.returncode}: {completed.stderr.strip()}"
        )
        emitted = dict(
            line.split("=", 1)
            for line in output.read_text(encoding="utf-8").splitlines()
            if "=" in line
        )
    assert emitted.get("any") == "true", "discover found no claim targets at all"
    entries: list[dict[str, str]] = json.loads(emitted["targets"])
    return entries


def _emitted_targets(workflow_text: str | None = None) -> list[str]:
    """Every target the matrix runs, flattened out of the entries that carry them.

    **An entry carries a bin, not a target, since `T00M`.** `ci.yml` runs
    `make ${{ matrix.target }}` unquoted and `make` takes several targets on one line, so
    `claim-2-tests gold` is one entry running two targets. Every check below asks *is this
    target run* rather than *does this target have an entry* — which is the property that
    always mattered and was, until packing existed, indistinguishable from the other one.
    """
    return [t for e in _discovered(workflow_text) for t in e["target"].split()]


def _tests_entries(workflow_text: str | None = None) -> list[dict[str, str]]:
    return [
        e
        for e in _discovered(workflow_text)
        if any(t.endswith("-tests") for t in e["target"].split())
    ]


def check_every_tests_target_gets_a_job(workflow_text: str | None = None) -> None:
    """The half `ops/figures.py` cannot reach: a target that exists and no job invokes.

    `figures`' `suite` row is satisfied by `claim-2-tests` existing in the Makefile. If
    `discover` stopped emitting it, the row would stay green and the tests would run on no
    push — which is `claim-[1-7]` a third time, at the level of a matrix entry.
    """
    declared = sorted(re.findall(r"^(claim-[\w-]*-tests):", _MAKEFILE, re.MULTILINE))
    assert declared, "no -tests target exists, so this check is asserting nothing"
    emitted = _emitted_targets(workflow_text)
    missing = [target for target in declared if target not in emitted]
    assert not missing, (
        f"the Makefile declares {missing} and discover emits no job for them, so they run on "
        "no push. Every other gate would stay green."
    )


def test_discover_emits_a_job_for_every_tests_target_the_makefile_declares() -> None:
    check_every_tests_target_gets_a_job()


def check_every_generating_entry_has_its_own_cache_namespace(
    workflow_text: str | None = None,
) -> None:
    """`actions/cache` is first-writer-wins, so two entries on one key is one of them lost.

    The tests entry generates ~11 MB of worlds and the other unsharded targets generate almost
    none, so sharing the un-suffixed key means `claim-4` finishing in 92 s takes it and the
    tests entry never warms.
    """
    entries = _discovered(workflow_text)
    namespaced = [entry["slug"] for entry in entries if entry["slug"]]
    assert len(namespaced) == len(set(namespaced)), (
        f"two matrix entries share a cache namespace: {sorted(namespaced)}"
    )
    for entry in entries:
        if any(t.endswith("-tests") for t in entry["target"].split()):
            assert entry["slug"], (
                f"{entry['name']} generates worlds and has no cache namespace, so it races the "
                "unsharded targets for the un-suffixed key and loses to the fastest of them"
            )


def test_every_shard_and_tests_entry_has_its_own_cache_namespace() -> None:
    check_every_generating_entry_has_its_own_cache_namespace()


def test_the_run_stays_under_the_concurrency_ceiling() -> None:
    """`discover + gate + secrets + entries + combines + claims-complete`, counted by running it.

    Twenty is what this account documents. The count moved from 18 to 19 when the marked tests
    were given their own entry, and the whole reason to compute it here rather than to write it
    down is that the next entry will move it again.

    **It did, and it refused: `gold` made it 21 and this is what stopped the branch.** What
    followed is `T00M` — the run was slot-bound rather than time-bound, and unsharded targets
    are now packed into bins under `CI_ENTRY_BUDGET`. So this counts **entries**, which is
    machines, while the checks above count **targets**, which is work. The two were the same
    number until packing existed and the difference is the whole point of it.
    """
    entries = _discovered()
    combines = sum(1 for t in set(_emitted_targets()) if _declared_shards(t, _MAKEFILE) > 1)
    jobs = 3 + len(entries) + combines + 1
    assert jobs <= 20, (
        f"a run would launch {jobs} jobs against a documented ceiling of 20. Past the ceiling "
        "the wall clock stops improving and only the flight count grows."
    )


# ------------------------------------- and the two of those get attacks, run the same way


#: Attacks on the emission itself. `ATTACKS` above is checked by reading the broken file;
#: these are checked by **running** it, because what `discover` emits is not visible in the
#: text — the defect they model is a shell loop that stops emitting, not a key that changed.
EMISSION_ATTACKS: dict[str, tuple[str, str]] = {
    "the tests entry no longer collected": (
        '            if grep -qE "^${t}-tests:" Makefile; then\n'
        '              unsharded="$unsharded ${t}-tests"\n',
        '            if false; then\n              unsharded="$unsharded ${t}-tests"\n',
    ),
    # **Re-aimed by `T00M`, and where it moved to is the finding.** This used to blank the
    # `--arg slug "tests"` in `ci.yml`, because the namespace was decided there. It is now
    # decided by `ops/ci_pack.py`, which derives a bin's slug from its contents — so the
    # namespace cannot be blanked from this file at all and an attack that tried would be
    # aiming at text that no longer decides anything.
    #
    # What is still expressible here is the seam: the packer's output being **discarded**.
    # That leaves the matrix with no unsharded entry at all, which both checks must refuse —
    # and the property the old attack proved, that a generating entry has its own namespace,
    # is now asserted directly over `ops.ci_pack.entries` in `test_ci_pack.py`, where it lives.
    "the packed entries discarded": (
        'packed="$(python3 -m ops.ci_pack $unsharded)"',
        'packed="[]"',
    ),
    # The other half of what the blanked-slug attack used to prove, expressed at the seam that
    # still exists in this file: a packer that emits entries **without** a namespace. It models
    # a real regression — `ops/ci_pack.entries` dropping the slug — from the one place `ci.yml`
    # can still reach it, which is by standing in for the packer entirely.
    "the packer emits entries with no cache namespace": (
        'packed="$(python3 -m ops.ci_pack $unsharded)"',
        'packed="$(python3 -m ops.ci_pack $unsharded | jq -c \'[.[] | .slug = ""]\')"',
    ),
}


#: Each is a function of the workflow text, with two callers: a test that runs it against
#: `ci.yml`, and an attack that runs it against a copy whose emission has been broken.
EMISSION_CHECKS: dict[str, Callable[[str | None], None]] = {
    "every -tests target gets a job": check_every_tests_target_gets_a_job,
    "every generating entry is namespaced": check_every_generating_entry_has_its_own_cache_namespace,
}


@pytest.mark.parametrize("attack", sorted(EMISSION_ATTACKS))
def test_each_emission_attack_is_refused(attack: str) -> None:
    old, new = EMISSION_ATTACKS[attack]
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    found = text.count(old)
    assert found == 1, (
        f"the attack {attack!r} anchors on text occurring {found} time(s) in ci.yml — the same "
        "exactly-once rule `_broken` carries, for the same reason"
    )
    broken = text.replace(old, new, 1)

    bitten = []
    for name, check in EMISSION_CHECKS.items():
        try:
            check(broken)
        except AssertionError:
            bitten.append(name)
    assert bitten, (
        f"the attack {attack!r} left every emission check green, so none of them is the guard "
        "against it — and the attack really did change what discover emits, which is worse "
        "than an anchor that moved"
    )


def test_every_emission_check_has_an_attack_that_bites_it() -> None:
    """**The third substitution site, and the only one that was not asserting it applied.**

    `_broken` and `_bitten_by` both require their anchor to occur exactly once before replacing;
    this loop did not. A stale anchor here makes `broken` identical to the original, no check
    fires, and the failure reads *"X is never made to fail by any emission attack"* — **which
    blames the check when what is stale is the attack.**

    That is not hypothetical. Verifying the ceiling plant by hand, `exit 1` was removed from a
    copy of `ci.yml` with a search string that did not match; the file was unchanged, the plant
    stayed green, and it read as the plant failing to bite. **A break that never broke, reported
    as the guard not biting** — the same misdiagnosis this assertion now prevents, arriving by
    hand instead of through this loop.
    """
    bitten: set[str] = set()
    for attack, (old, new) in EMISSION_ATTACKS.items():
        text = CI_WORKFLOW.read_text(encoding="utf-8")
        assert text.count(old) == 1, (
            f"the attack {attack!r} anchors on text occurring {text.count(old)} time(s) in "
            "ci.yml, so it would edit nothing and this loop would report the checks as unbitten "
            "— the attack is stale, not the checks"
        )
        broken = text.replace(old, new, 1)
        for name, check in EMISSION_CHECKS.items():
            try:
                check(broken)
            except AssertionError:
                bitten.add(name)
        del attack
    unbitten = sorted(set(EMISSION_CHECKS) - bitten)
    assert not unbitten, (
        f"{unbitten} are never made to fail by any emission attack, so nothing shows they bite"
    )


# ---------------------------------- the ceiling check, planted rather than read


def _entry_step(workflow_text: str | None = None) -> str:
    """The `run:` body of the step that executes a matrix entry, with the placeholders bound.

    Extracted from `ci.yml` rather than restated, for the reason `_discovered` gives about
    `discover`'s own shell: reading the text cannot see what the shell does, and this check is
    about what it does.
    """
    workflow = yaml.safe_load(workflow_text or CI_WORKFLOW.read_text(encoding="utf-8"))
    bodies = [
        step["run"]
        for step in workflow["jobs"]["claims"]["steps"]
        if isinstance(step.get("name"), str) and step["name"].startswith("make $")
    ]
    assert len(bodies) == 1, "the step that runs a matrix entry is no longer identifiable"
    body: str = bodies[0]
    return (
        body.replace("${{ matrix.shard }}", "")
        .replace("${{ matrix.target }}", "probe")
        .replace("${{ matrix.name }}", "probe bin")
    )


def _run_entry_step(scratch: Path, ceiling: int, sleeps: int) -> subprocess.CompletedProcess[str]:
    """Run that step against a planted Makefile whose one target sleeps."""
    (scratch / "Makefile").write_text(
        f"CI_ENTRY_CEILING := {ceiling}\n\nprobe:\n\tsleep {sleeps}\n", encoding="utf-8"
    )
    return subprocess.run(
        ["bash", "-c", _entry_step()],
        cwd=scratch,
        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        capture_output=True,
        text=True,
        check=False,
    )


def test_an_entry_over_the_ceiling_fails_and_names_itself(tmp_path: Path) -> None:
    """**The check is proved by planting, because writing it correctly is not evidence.**

    Every bin in this tree is comfortably under the ceiling, so a green run shows the packing
    works and shows nothing at all about the check. This repository does not accept a guard on
    the grounds that it reads correctly — `test_every_emission_check_has_an_attack_that_bites_it`
    refused one two functions up, in this same change, for exactly that.

    **Lowering `CI_ENTRY_CEILING` is the plant, and lowering a `<TARGET>_COST` is not.** A cost
    changes which bin a target lands in; it never reaches this comparison. The ceiling is what
    the elapsed time is measured against, so it is the only dial that exercises the path.

    Four ways this could be silently useless and all four are covered here: the elapsed time is
    measured over the span the step thinks it is (a target that sleeps 2s reports ~2s), the
    comparison is in the units it thinks it is (seconds, not minutes or milliseconds), the
    failure **propagates** out of the step rather than being swallowed by the shell, and the
    message **names the bin** — which is the whole reason this exists rather than a slow run
    nobody attributes.

    What planting does **not** prove is that 1032 is the right number. That is a judgement,
    justified from four observations of the critical chain's floor, and it is not a mechanism.
    **The mechanism is proved by planting; the constant is justified by measurement.** Those are
    two sentences on purpose.

    **And this plant was itself verified vacuously the first time.** The verification removed
    `exit 1` from a copy of `ci.yml` and re-ran — and the test stayed green, which looked like
    the plant failing to bite. It was not: the edit searched for `that moved.` where the file
    says `that moves.`, so nothing was replaced and the check ran **unmodified**. A verification
    that a guard bites, performed against a file that was never broken, is the same defect as
    the guard it was verifying. Re-run with an assertion that the substitution applied, the
    plant goes red exactly as it should.
    """
    finished = _run_entry_step(tmp_path, ceiling=1, sleeps=2)
    output = finished.stdout + finished.stderr
    assert finished.returncode != 0, f"a bin over its ceiling passed: {output}"
    assert "probe bin" in output, f"the failure does not name the bin that caused it: {output}"
    assert "over the 1s ceiling" in output, output
    assert "took 2s" in output, f"the elapsed span is not what the step measured: {output}"


def test_an_entry_under_the_ceiling_passes_and_reports_its_cost(tmp_path: Path) -> None:
    """The other direction, so the test above cannot be passing because everything fails."""
    finished = _run_entry_step(tmp_path, ceiling=600, sleeps=1)
    output = finished.stdout + finished.stderr
    assert finished.returncode == 0, output
    assert "against a ceiling of 600s" in output, output


def test_an_entry_whose_tree_declares_no_ceiling_is_refused(tmp_path: Path) -> None:
    """Silence is not the same as being within budget, so a missing ceiling is red.

    Without this the check degrades to nothing the day somebody removes the declaration, and a
    run with no ceiling looks exactly like a run under one.
    """
    (tmp_path / "Makefile").write_text("probe:\n\ttrue\n", encoding="utf-8")
    finished = subprocess.run(
        ["bash", "-c", _entry_step()],
        cwd=tmp_path,
        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert finished.returncode != 0
    assert "CI_ENTRY_CEILING" in finished.stdout + finished.stderr
