"""Worlds are generated once and read back — and what invalidates that is computed, not listed.

`make claim-2` runs the harness once and then plants eight mutations, each of which runs the
machinery entry point again. Generating the same worlds ten times would be most of the target's
clock, and it would be waste rather than evidence: **a world is a pure function of `(world,
seed, scale)`** and a mutation changes *eval* code, so nine of those ten generations produce
bytes identical to the first.

So the grouped ledger is written to disk once and read back afterwards. The whole risk of that
is the exception — **a mutation that changes the corpus, or the code that groups it, must not
be handed a cache built before it** — and the danger is precise: such a mutation would report
`SURVIVED` while the thing it broke never ran. That is a gate silently disarmed, which is the
one failure this repository has paid for four times.

**So the exception is not a list of file paths somebody keeps up to date.** The key carries a
digest of every source file the cached artefact was produced by: everything under `corpus/`,
and the module in this package that grouped it. Change any byte of any of them — by a
mutation, by an edit, by a rebase — and the key changes and the world is generated again.
Nothing has to be remembered and nothing has to be declared twice.

`tests/evals/test_uplift_cache.py` drives both directions: a byte changed in `corpus/` moves
the key, a byte changed in a module the ledger does not come from does not, and a cache written
under one key is never read under another.

**It is a cache and not a corpus.** Nothing here is committed, exactly as `corpus/world/`'s own
README says of the worlds themselves: a world is regenerated rather than stored, and this only
stops it being regenerated *nine times in one command*. Deleting the directory costs minutes
and changes no answer.
"""

from __future__ import annotations

import hashlib
import os
import pickle
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path

from evals.uplift import outcomes

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Where the ledgers go. Never committed — `.gitignore` carries it — and resolved from this
#: module's own location, so a copy of the tree (which is what `evals/gate_proof` runs in)
#: caches beside itself rather than reaching back into the repository it was copied from.
CACHE_DIR = Path(os.environ.get("HOLDOUT_WORLD_CACHE", REPO_ROOT / ".worlds"))

#: What a cached artefact is produced by: `corpus/world/`, which is the world, and the two
#: modules that turn a world into something worth storing — `outcomes.py` for the grouped
#: ledgers and `reference.py` for the slow path's cells, which `U10` compares and which cost a
#: second pass over five million events.
#:
#: Nothing else is in the list, and that is as deliberate as what is. A digest over the whole
#: repository would move on every mutation, every world would be regenerated for every one of
#: them, and the claim target would not finish — which is the other way to make a cache
#: useless.
#:
#: **This read `"corpus"` until 2026-09-01, and the wider spelling had a price.** `corpus/real/`
#: is claim 1's and claim 7's corpus — hand-collected price quotes and two published
#: vocabularies — and **nothing under `corpus/world/` imports it**, so it cannot produce a byte
#: of a world. It was in the digest anyway, and a commit touching it threw away every world
#: ledger: measured over 71 `claim-2` jobs, **11 spurious invalidations at +18.4 min each**
#: (95% CI +13.5 to +23.2), about **3.4 h** of CI already spent regenerating worlds that could
#: not have changed.
#:
#: **`corpus/__init__.py` stays, and it is the whole reason this is a narrowing rather than a
#: rename.** It executes on any import of `corpus.world`, so a future edit to it can change a
#: world even though it holds only a docstring today. Narrowing to `corpus/world` alone would
#: have dropped it, and **under-covering is the direction that fails silently**: a mutation
#: handed a world built before it reports `SURVIVED` while the thing it broke never ran.
#: Over-covering costs minutes and announces itself; the trade is not symmetric and the list is
#: not narrowed past what the import graph justifies.
#:
#: `tests/evals/test_uplift_cache.py` proves the coverage rather than asserting it: it walks the
#: import closure of these three roots and requires every repository-local module in it to be a
#: file this digest reads.
#: **And one file that is not source.** `prepare()` calls `policy.contract_ladder()`, which
#: reads `contracts/policies/ladder_policy@v1.yaml` at run time — the control arm of every
#: fresh-markdown world, and therefore the markdown behaviour the whole ledger is a summary of.
#: A digest over source files cannot see a value that arrives as **data**, and this one is the
#: silent direction: change a rung, and every cached ledger describes a world with the old
#: ladder while nothing recomputes anything to disagree with it.
#:
#: Driven rather than reasoned: editing one rung moved the policy and left the digest at
#: `0b15f66b…`. It is one file rather than `contracts/`, because the rest of that directory
#: reaches no world — and the test takes the path from `policy.LADDER_CONTRACT` rather than
#: repeating it, so a contract that moves cannot leave this list pointing at the old one.
DEPENDS_ON: tuple[str, ...] = (
    "corpus/world",
    "corpus/__init__.py",
    "evals/uplift/outcomes.py",
    "evals/uplift/reference.py",
    "contracts/policies/ladder_policy@v1.yaml",
)


class DependencyMissingError(Exception):
    """A `DEPENDS_ON` entry names nothing on disk, so the digest cannot be computed."""


def _source_files() -> list[Path]:
    """Every file the digest reads, or an exception — never a quietly shorter list.

    An entry that matches nothing used to be skipped. That is the failure this whole module
    exists to prevent, wearing the shape of a typo: `corpus/wolrd` would have produced a digest
    over the two `evals/uplift` modules alone, every world would have looked unchanged forever,
    and a mutation to the generator would have reported `SURVIVED` against a world built before
    it. **An instrument that cannot answer raises rather than returning a smaller number** —
    the rule `ops/figures.py` states, at the one place in this repository where the smaller
    number is silently wrong instead of merely wrong.
    """
    found: list[Path] = []
    for entry in DEPENDS_ON:
        path = REPO_ROOT / entry
        if path.is_dir():
            found.extend(sorted(p for p in path.rglob("*.py") if "__pycache__" not in p.parts))
        elif path.is_file():
            found.append(path)
        else:
            raise DependencyMissingError(
                f"DEPENDS_ON names {entry!r} and there is no such file or directory under "
                f"{REPO_ROOT}. The digest would have been computed over what is left, every "
                "world would read back as unchanged, and a mutation to the generator would "
                "report SURVIVED while the thing it broke never ran."
            )
    return sorted(found)


def source_digest() -> str:
    """A digest over every byte the cached ledgers were produced by.

    Read from disk on every call rather than computed once at import: the mutation engine
    edits a file *between* two runs of this package, and a digest taken at import in the
    parent process would describe the tree as it was before the edit.
    """
    running = hashlib.blake2b(digest_size=16)
    for path in _source_files():
        running.update(str(path.relative_to(REPO_ROOT)).encode("utf-8"))
        running.update(path.read_bytes())
    return running.hexdigest()


def key(*parts: object) -> str:
    """A cache key: what was asked for, and what the answer would have been produced by."""
    material = "\x1f".join(str(part) for part in parts)
    return (
        f"{hashlib.blake2b(material.encode('utf-8'), digest_size=12).hexdigest()}-{source_digest()}"
    )


def cached[T](name: str, build: Callable[[], T]) -> T:
    """Read the value cached under `name`, or build it and write it there.

    A read that fails for any reason at all — a truncated file, a pickle from another version,
    a directory that is not writable — falls through to building. A cache is an optimisation
    and an optimisation that can fail a run is not one.
    """
    path = CACHE_DIR / f"{name}.pickle"
    if path.is_file():
        try:
            return pickle.loads(path.read_bytes())  # type: ignore[no-any-return]
        except Exception:
            pass
    built = build()
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        # Written beside and moved into place, so a run interrupted half way through leaves no
        # half-file for the next one to read as a hit.
        scratch = path.with_suffix(f".{os.getpid()}.partial")
        scratch.write_bytes(pickle.dumps(built, protocol=pickle.HIGHEST_PROTOCOL))
        scratch.replace(path)
    except OSError:
        pass
    return built


def ledgers(
    name: str, build: Callable[[], Sequence[outcomes.Ledger]]
) -> tuple[outcomes.Ledger, ...]:
    """`cached`, for the grouped ledgers — the shape almost every caller wants."""
    loaded = cached(name, lambda: tuple(build()))
    if isinstance(loaded, tuple) and all(isinstance(item, outcomes.Ledger) for item in loaded):
        return loaded
    return tuple(build())  # pragma: no cover - a cache holding the wrong shape is a miss


def clear() -> None:
    """Remove every cached ledger. Costs minutes and changes no answer."""
    if not CACHE_DIR.is_dir():
        return
    for path in CACHE_DIR.glob("*.pickle"):
        path.unlink(missing_ok=True)


def entries() -> Iterable[Path]:
    return sorted(CACHE_DIR.glob("*.pickle")) if CACHE_DIR.is_dir() else ()
