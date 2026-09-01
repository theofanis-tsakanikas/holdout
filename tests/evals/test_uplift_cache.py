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

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest
from corpus.world import policy
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


# ------------------------------------------------- what the narrowing dropped, and what it kept


def test_claim_1s_corpus_leaves_the_key_alone() -> None:
    """`corpus/real/` cannot produce a byte of a world, and until 2026-09-01 it invalidated one.

    The digest read `"corpus"`, so a commit touching claim 1's hand-collected price quotes or
    claim 7's two published vocabularies threw away every world ledger. Measured over 71
    `claim-2` jobs: **11 spurious invalidations at +18.4 min each**, about 3.4 h of CI spent
    regenerating worlds that could not have changed.

    Driven by editing the file rather than by asserting the path is absent from a list, because
    a list is what this design exists to not need.
    """
    before = cache.source_digest()
    target = cache.REPO_ROOT / "corpus" / "real" / "reader.py"
    original = target.read_bytes()
    try:
        target.write_bytes(original + b"\n# claim 1's corpus, which no world is produced by\n")
        assert cache.source_digest() == before, (
            "an edit to corpus/real/ moved the world cache key. Nothing under corpus/world/ "
            "imports it, so every world ledger was thrown away for a change that could not "
            "alter one"
        )
    finally:
        target.write_bytes(original)


def test_the_corpus_package_root_still_moves_the_key() -> None:
    """The edge the narrowing must not drop, and the reason it is not simply `corpus/world`.

    `corpus/__init__.py` executes on any import of `corpus.world`. It holds only a docstring
    today, which is exactly why narrowing to the subdirectory looks safe and is not: the
    question is what *can* produce a world, not what happens to today.

    **Under-covering is the direction that fails silently.** Over-covering costs minutes and
    announces itself in a cache miss; under-covering hands a mutation a world built before it
    and the mutation reports `SURVIVED`.
    """
    before = cache.source_digest()
    target = cache.REPO_ROOT / "corpus" / "__init__.py"
    original = target.read_bytes()
    try:
        target.write_bytes(original + b"\n# executed on every import of corpus.world\n")
        assert cache.source_digest() != before, (
            "an edit to corpus/__init__.py left the key where it was. It runs on every import "
            "of corpus.world, so a world generated after it is not the world cached before it"
        )
    finally:
        target.write_bytes(original)


def test_a_dependency_that_names_nothing_raises_rather_than_shrinking_the_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A typo in `DEPENDS_ON` is the narrowing's own failure mode, so it is refused by name.

    `corpus/wolrd` matches no file. Skipping it silently would digest the two `evals/uplift`
    modules alone, every world would read back unchanged forever, and a mutation to the
    generator would report `SURVIVED`. `ops/figures.py`'s rule, at the one site in this
    repository where the smaller number is silently wrong rather than merely wrong.
    """
    monkeypatch.setattr(cache, "DEPENDS_ON", ("corpus/wolrd", "evals/uplift/outcomes.py"))
    with pytest.raises(cache.DependencyMissingError) as caught:
        cache.source_digest()
    assert "corpus/wolrd" in str(caught.value)


# ------------------------------------- the coverage is computed, not declared, and here is how


#: Where this repository's own packages live: `corpus/`, `evals/` and `ops/` at the root, and
#: `holdout` under `src/`. A name resolving under neither is somebody else's library and is not
#: something a commit here can change.
_PACKAGE_ROOTS = (cache.REPO_ROOT, cache.REPO_ROOT / "src")


def _repo_module_path(name: str) -> Path | None:
    """The file a dotted module name resolves to, if it is one this repository owns."""
    for root in _PACKAGE_ROOTS:
        candidate = root / Path(*name.split("."))
        if (candidate / "__init__.py").is_file():
            return candidate / "__init__.py"
        if candidate.with_suffix(".py").is_file():
            return candidate.with_suffix(".py")
    return None


def _imports(path: Path) -> set[str]:
    """Dotted names imported by `path` at **run time** — `TYPE_CHECKING` blocks excluded.

    A name imported only for annotations never executes, so it cannot change a byte of what
    this module caches. Relative imports raise rather than being guessed at; this repository
    does not use them, and a walker that silently mis-resolved one would understate the
    closure, which is the direction that fails silently.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test = node.test
            named = (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
                isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
            )
            if named:
                skip.update(id(child) for child in ast.walk(node) if child is not node)

    found: set[str] = set()
    for node in ast.walk(tree):
        if id(node) in skip:
            continue
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                raise AssertionError(
                    f"{path} uses a relative import, which this walk cannot resolve"
                )
            if node.module:
                found.add(node.module)
                found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return found


def test_every_module_a_cached_artefact_is_produced_by_is_in_the_digest() -> None:
    """The list is checked against the import graph, not against whoever last edited it.

    `cache.py` claims the key carries *a digest of every source file the cached artefact was
    produced by*. That is a claim about the import closure of three roots, and this walks it:
    from `corpus.world`, `outcomes.py` and `reference.py`, following every repository-local
    import, every module reached must be a file the digest reads.

    **It is what makes the narrowing safe rather than merely smaller.** A later commit that
    makes a world depend on a module outside `DEPENDS_ON` goes red here instead of serving a
    stale world in silence.

    What it does **not** cover, because a coverage test that overstates its own coverage is the
    joke it exists to prevent: values that arrive as **data** rather than as imports. No import
    graph can see a file read at run time or a contract handed in as an argument.

    **That class was walked rather than sampled, and the walk is recorded here because *one* is
    otherwise indistinguishable from *the first one found*.** Every module in the closure — all
    fourteen, `corpus/__init__.py` included — was scanned for every construct that brings a
    value in from outside its own source: `open`, `read_text`, `read_bytes`, `glob`, `loads`,
    `safe_load`, `getenv`, `environ`, `subprocess`, `urlopen`, and any import of `yaml`, `json`,
    `csv`, `tomllib`, `sqlite3`, `pickle`, `requests`, `urllib` or `os`. **Eleven answered
    nothing. Three answered, and two of those read what the world had just written:**

    * `corpus/world/__init__.py` — four `gzip.open(..., "wt")` and a `json.dumps` into
      `run.json`. Writes only; nothing comes back in.
    * `corpus/world/seal.py` — reads a seal, which the world *produced* and which
      `open_after_readout` opens once an estimate exists. An output, never an input.
    * `corpus/world/policy.py` — `yaml.safe_load(LADDER_CONTRACT.read_text())`, the control arm
      of every fresh-markdown world. **The one input.** It is in `DEPENDS_ON`, and
      `test_the_ladder_contract_the_world_is_built_from_moves_the_key` drives it.

    So `one file, not contracts/` is a measurement. The remaining member of the class is the
    metric rounding reaching `reference.compute` as an argument, which fails **safe** — the half
    it is compared against is computed fresh, so a stale entry goes red rather than silent — and
    is filed with its own disposition.

    **The scan's own limit:** it matches call and import *names*, so a read reached through an
    alias, a callable held in a variable, or a name built at run time would not appear in it.
    Nothing in this closure does that today, and a module that started to would be invisible to
    it — which is why the ladder contract is pinned by a test that asks the generator where it
    reads rather than by this paragraph.
    """
    roots = [
        cache.REPO_ROOT / "corpus" / "world" / "__init__.py",
        cache.REPO_ROOT / "evals" / "uplift" / "outcomes.py",
        cache.REPO_ROOT / "evals" / "uplift" / "reference.py",
    ]
    seen: set[Path] = set()
    queue = list(roots)
    while queue:
        path = queue.pop()
        if path in seen:
            continue
        seen.add(path)
        for name in _imports(path):
            resolved = _repo_module_path(name)
            if resolved is not None and resolved not in seen:
                queue.append(resolved)

    digested = set(cache._source_files())
    missing = sorted(p.relative_to(cache.REPO_ROOT).as_posix() for p in seen - digested)
    assert not missing, (
        "a cached artefact is produced by module(s) the digest does not read: "
        f"{missing}. A change to one of them would leave every cached world looking "
        "unchanged, and a mutation to it would report SURVIVED while the thing it broke "
        "never ran"
    )
    assert len(seen) >= 10, f"the walk reached only {len(seen)} modules, so it did not run"


# ------------------------------------ what arrives as data rather than as an import


def test_the_ladder_contract_the_world_is_built_from_moves_the_key() -> None:
    """The silent one, and the reason `DEPENDS_ON` is not only source files.

    `corpus/world/__init__.py`'s `prepare()` calls `policy.contract_ladder()`, which reads
    `contracts/policies/ladder_policy@v1.yaml` at run time. That is the control arm of every
    fresh-markdown world — the markdown behaviour the whole ledger is a summary of — and it
    reaches the generator as **data**, which no digest over source files and no import closure
    can see.

    **It fails silently, which is what separates it from the metric-rounding gap.** There, the
    half the cached value is compared against is computed fresh, so a stale entry produces a red
    `U10`. Here there is nothing to disagree with: every consumer reads the same stale ledger and
    the run reports a world with the old ladder.

    Measured before the fix: editing one rung moved the policy and left the digest at
    `0b15f66b64bc0b4e69b6ab44decb144a`.
    """
    before = cache.source_digest()
    target = policy.LADDER_CONTRACT
    original = target.read_bytes()
    try:
        edited = original.decode().replace("depth_pct: 20", "depth_pct: 25", 1)
        assert edited != original.decode(), "the rung this test edits is not in the contract"
        target.write_bytes(edited.encode())
        assert cache.source_digest() != before, (
            "a rung moved in the ladder contract and the world cache key did not. Every "
            "cached ledger would describe a world built with the old ladder, and nothing "
            "recomputes anything that would disagree"
        )
    finally:
        target.write_bytes(original)
    assert cache.source_digest() == before


def test_the_contract_the_generator_reads_is_taken_from_the_generator() -> None:
    """The path is not repeated here, so a contract that moves cannot leave the list behind.

    `DEPENDS_ON` names the file; this asks `corpus.world.policy` where it actually reads from
    and requires the two to agree. A test that hard-coded the path would go green on a tree
    where the generator had been pointed somewhere else — the second registry problem, which
    is what `DEPENDS_ON` exists to avoid one layer down.
    """
    assert policy.LADDER_CONTRACT in cache._source_files(), (
        f"the generator reads {policy.LADDER_CONTRACT} to build every world's control arm, "
        "and the cache key is not computed over it"
    )


# --------------------------------- and the behavioural check, because a name match can be fooled


#: Generates one world at the smallest declared scale under an audit hook and prints every file
#: it opens inside the repository. Run in a subprocess: `sys.addaudithook` cannot be removed once
#: installed, and a hook left in the suite's own interpreter would outlive the test that wanted it.
_TRACE = """
import sys, json
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
opened, tracing = set(), False

def hook(event, args):
    if not tracing or event != "open":
        return
    target = args[0] if isinstance(args, tuple) and args else None
    if not isinstance(target, (str, bytes)):
        return
    text = target.decode() if isinstance(target, bytes) else target
    try:
        resolved = Path(text).resolve()
        opened.add(resolved.relative_to(REPO).as_posix())
    except (OSError, ValueError):
        pass

sys.addaudithook(hook)
sys.path.insert(0, str(REPO))

from corpus.world import prepare
from corpus.world import scale as scale_module
from evals.uplift import outcomes

tracing = True
run = prepare("w1", seed="1", scale=scale_module.SMOKE)
outcomes.collect(run)
tracing = False

print(json.dumps(sorted(p for p in opened if not p.startswith(".venv"))))
"""


def test_the_files_the_generator_actually_opens_are_all_in_the_digest() -> None:
    """The syntactic scan matches **names**; this watches the interpreter.

    `test_every_module_a_cached_artefact_is_produced_by_is_in_the_digest` walks imports, and its
    docstring records a scan of what each module reads — both of which match call and import
    names, so a read reached through an alias, a callable held in a variable, or a name built at
    run time is invisible to them by construction. That limit had a remedy and this is it:
    **generate a world under `sys.addaudithook` and record every file actually opened.** It sees
    the operation rather than the spelling, so an aliased read cannot hide from it.

    Measured: one world at `SMOKE`, generated and grouped in **0.2 s**, opens **exactly one**
    file inside the repository — `contracts/policies/ladder_policy@v1.yaml`, which is in
    `DEPENDS_ON`. The behavioural answer and the syntactic one agree, which is what makes *one
    file, not `contracts/`* a measurement twice rather than a reading of the source once.

    **What it does not cover**, since this is the test that exists to stop the coverage being
    overstated: one world, one seed, one scale. A read on a branch only some world takes — a
    scale-dependent path, a world-specific parameter file — would not appear here. Extending it
    is a loop over `worlds.py`'s six and costs a second each; it is not run because nothing in
    the closure reads conditionally today, and that is a statement about this tree rather than a
    guarantee about the next one.
    """
    result = subprocess.run(
        [sys.executable, "-c", _TRACE, str(cache.REPO_ROOT)],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=cache.REPO_ROOT,
    )
    assert result.returncode == 0, f"the traced generation failed:\n{result.stderr}"
    opened = json.loads(result.stdout.strip().splitlines()[-1])

    digested = {p.relative_to(cache.REPO_ROOT).as_posix() for p in cache._source_files()}
    unaccounted = sorted(set(opened) - digested)
    assert not unaccounted, (
        f"generating a world opened {unaccounted} inside the repository, and the cache key is "
        "not computed over it. A change to one of those would leave every cached ledger "
        "describing a world built before it, with nothing to disagree"
    )
    assert opened, "the trace recorded no repository file at all, so it did not run"
