"""Break each gate on purpose, and demand a refusal from the gate that is named.

The three rules, and what each one is defending against
-------------------------------------------------------
**1 · Green first.** Before a mutation is planted, the check it claims to trip must already
be passing. A mutation whose target was red anyway proves nothing: the failure it produces
was there before it arrived. That verdict is `NOT-ARMED`, and it is a failure of the run,
not a skip.

**2 · A non-zero exit is not proof.** The eval is run as a subprocess and its **JSON**
reading is parsed. The mutation succeeds only when the *named* check reports `passed:
false`. Anything else that goes red — an import error, a crash, a different check falling
over — is `CRASHED`, and `CRASHED` fails. Without this rule the easiest way to pass
`gate-proof` would be to write a mutation that makes the eval unimportable, and it would
look identical to a gate biting.

**3 · A mutation whose target moved is STALE, never passed.** The anchor text must appear in
the source **exactly once**. Zero occurrences means the code it was written against has been
edited and the mutation is now aimed at nothing; more than one means it is aimed at
something ambiguous. Either way the answer is `STALE`. This is the rule that stops
`gate-proof` decaying into a suite of mutations that no longer touch anything and pass
because the thing they were meant to break is gone. The same rule applies to the *check* a
mutation names: a target that no longer exists in the eval's output is `STALE`, not a pass.

Where the independence is, and where it is not
----------------------------------------------
Claim 1's trap, restated for the planter: *if the thing that decides what to break reads the
same source of truth as the thing that detects it, it is one function agreeing with itself.*

Three separations, and only the third is strong:

* the planter never edits the **detector**. For claim 1 that reads "the planter edits
  `src/holdout/`; the detector reads `corpus/real/`". **Restated 2026-08-29 with claim 7**,
  whose most valuable mutation edits `contracts/policies/ladder_policy@v1.yaml` — a decision
  that becomes idempotent per customer changes no Python at all, and a planter confined to
  `src/` could not have written it. So the rule is stated by what it forbids rather than by
  what it allows: `ops/` and `corpus/` are the detector and the inputs, and
  `ledger.no-mutation-edits-the-detector` refuses a mutation naming either. Enumerating what
  the planter *may* edit was tried here first and was false of the repository it sat in —
  three of the thirty committed mutations edit `evals/uplift/`;
* a mutation is written as a **behaviour change in domain terms** — "the margin floor rounds
  the wrong way", "a frozen category is only a warning" — and never as "make check G2 fail".
  The check it must trip is declared in advance, in the file, and if it survives that is
  reported rather than adjusted;
* **the planter cannot tune the inputs.** The corpus is committed and digest-checked, so the
  only way to make a mutation catchable is to make the gate actually catch it. This is the
  separation that does the work; the first two are hygiene.

What this does not prove
------------------------
That every gate bites on every mutation. These are the breaks we thought of — the same
honest limit the six adversarial worlds carry for claim 2 — and a curated set is not
mutation testing. A gate can be perfect against all of them and still have a hole nobody
imagined. What the set does prove is that each named gate is *load-bearing*: remove it and
something goes red, by name, for the stated reason.

Nothing here touches the working tree. Each run copies the source it needs into a temporary
directory and mutates the copy, so an interrupted run cannot leave a planted mutation behind.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from evals.report import Check, Report

HERE = Path(__file__).resolve().parent
MUTATIONS_DIR = HERE / "mutations"
REPO_ROOT = HERE.parents[1]

#: What is copied into the workspace. `src/` is what gets mutated; `contracts/` and
#: `generated/` are there because `holdout.contracts.loader` resolves them relative to the
#: package, so a copied `src/` needs a copied contract directory beside it or every envelope
#: fails to build for the wrong reason.
#:
#: `.worlds/` is claim 2's cache of generated worlds, and copying it turns the baseline run
#: from eight minutes into seconds. It is **safe to copy and that is not a matter of care**:
#: `evals/uplift/cache.py` keys every entry on a digest of the corpus and of the two modules
#: that produced it, so a mutation to any of them regenerates and a mutation to anything else
#: reads back. A cache carried past a mutation that invalidates it would be a gate reporting
#: SURVIVED while the thing it broke never ran, which is why the key does the deciding rather
#: than this tuple. Absent directories are skipped, so a first run with no cache simply builds
#: one.
#:
#: `ops/` joined the tuple with claim 7. It holds the rules the product code is measured by —
#: the corpus barrier, the deferral registry, and `ops/personhood.py`, which is the one
#: implementation of *the decision key carries no customer dimension* that the suite and
#: `evals/oversight/` both call. A copied `evals/` that imports it needs it beside it, and
#: without it every claim-7 mutation would have reported `CRASHED` on an `ImportError` rather
#: than saying anything about a gate.
#:
#: **A mutation may never edit the detector**, and since 2026-08-29 that is a check rather
#: than a sentence: `ledger.no-mutation-edits-the-detector` refuses a mutation whose `file:`
#: is under `ops/` or `corpus/`. It is stated negatively on purpose. An earlier wording here
#: enumerated what the planter *may* edit — "`src/` and `contracts/`" — and oversight level 2
#: pointed out that three of the thirty committed mutations edit `evals/uplift/`, because
#: claim 2's machinery is partly what claim 2 is proving. The rule was never about which tree
#: the planter may touch. It is about the two it may not.
COPIED = ("src", "contracts", "generated", "evals", "corpus", "ops", ".worlds")

#: A run of the eval that takes longer than this has almost certainly been mutated into a
#: loop rather than into a bug. Bounded so `make gate-proof` cannot hang CI.
#:
#: **900 since claim 2, and the reason is not that claim 2 is slow.** It is that a mutation to
#: `corpus/` or to the module that groups it *legitimately* regenerates every world the run
#: needs — `evals/uplift/cache.py` keys on a digest of exactly those files, so invalidating
#: them is the cache working rather than failing. That is minutes by design and one mutation
#: in eight pays it. 300 was sized when the only eval was claim 1's, which reads a committed
#: corpus and generates nothing at all, and under it the rounding mutation reported CRASHED —
#: a gate recorded as broken because the guard against hanging fired on work that was doing
#: exactly what it was asked to.
TIMEOUT_SECONDS = 900


class Verdict(StrEnum):
    BIT = "bit"
    SURVIVED = "SURVIVED"
    STALE = "STALE"
    CRASHED = "CRASHED"
    NOT_ARMED = "NOT-ARMED"


@dataclass(frozen=True, slots=True)
class Mutation:
    source: Path
    id: str
    claim: int
    eval_module: str
    targets: tuple[str, ...]
    breaks: str
    file: str
    anchor: str
    replacement: str

    @property
    def ref(self) -> str:
        return f"{self.source.parent.name}/{self.source.name}"


@dataclass(frozen=True, slots=True)
class Result:
    mutation: Mutation
    verdict: Verdict
    detail: str
    tripped: tuple[str, ...] = ()
    also_fell: tuple[str, ...] = ()
    #: Wall clock of the mutated run. Zero where no run happened -- a STALE anchor or an
    #: un-armed eval never reaches a subprocess -- and a zero is therefore *no run*, never a
    #: run that took no time.
    seconds: float = 0.0


def load_mutations(claim: int | None = None) -> tuple[Mutation, ...]:
    directories = sorted(MUTATIONS_DIR.glob("claim-*"))
    if claim is not None:
        directories = [d for d in directories if d.name == f"claim-{claim}"]
    found: list[Mutation] = []
    for directory in directories:
        for path in sorted(directory.glob("*.yaml")):
            document: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
            found.append(
                Mutation(
                    source=path,
                    id=document["id"],
                    claim=int(document["claim"]),
                    eval_module=document["eval_module"],
                    targets=tuple(document["targets"]),
                    breaks=document["breaks"].strip(),
                    file=document["file"],
                    anchor=document["anchor"],
                    replacement=document["replacement"],
                )
            )
    return tuple(found)


# ------------------------------------------------------------------------------ the runner


def _workspace(into: Path) -> Path:
    workspace = into / "workspace"
    workspace.mkdir()
    for name in COPIED:
        source = REPO_ROOT / name
        if not source.is_dir():
            continue
        shutil.copytree(
            source,
            workspace / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    return workspace


def _run_eval(workspace: Path, module: str) -> tuple[dict[str, Any] | None, str, float]:
    """Run one eval inside the workspace, parse its JSON, and say how long it took.

    **The seconds are returned because without them a timeout is unreadable.** `CRASHED · did
    not finish within 900s` is the same sentence whether the run needed 902 seconds or four
    thousand, and those are opposite findings: the first says a budget has no headroom on this
    hardware, the second says the mutation turned the eval into a loop, which is what the
    budget exists to catch. Run 33571168520 produced exactly that sentence and nobody could
    tell which had happened.

    `PYTHONPATH` puts the workspace ahead of the editable install, so the subprocess imports
    the **mutated** `holdout` rather than the one in the working tree.

    **That is relied on, not verified.** An earlier version of this docstring said it was
    checked and named a function that has never existed in this repository, which is a worse
    error than the gap it was covering. What makes the gap survivable is its failure mode: if
    the workspace were not what ran, every mutation would report `SURVIVED` at once, because
    every one of them would have been planted in a copy nothing imported. Every mutation in
    a claim surviving at the same moment is not a failure anybody misses.
    """
    environment = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "PYTHONPATH": f"{workspace}:{workspace / 'src'}",
        "PYTHONHASHSEED": "0",
        "HOME": str(workspace),
    }
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [sys.executable, "-m", module, "--json"],
            cwd=workspace,
            env=environment,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return (
            None,
            f"killed at the {TIMEOUT_SECONDS}s budget. That is the budget and not a "
            "measurement of what this mutation needs — what it needs is unknown and larger",
            time.monotonic() - started,
        )
    elapsed = time.monotonic() - started
    if completed.returncode not in (0, 1):
        tail = (completed.stderr or completed.stdout).strip().splitlines()[-3:]
        return None, f"exit {completed.returncode}: {' / '.join(tail)}", elapsed
    try:
        return json.loads(completed.stdout), "", elapsed
    except json.JSONDecodeError:
        tail = (completed.stderr or completed.stdout).strip().splitlines()[-3:]
        return None, f"no JSON on stdout: {' / '.join(tail)}", elapsed


def _states(payload: dict[str, Any]) -> dict[str, bool]:
    return {check["id"]: bool(check["passed"]) for check in payload["checks"]}


#: How deeply a planted anchor may be nested. Forty columns is well past anything this
#: repository's line length admits, so a miss is a genuine miss rather than a search that
#: gave up early.
MAX_INDENT = 40


def _at_indent(block: str, columns: int) -> str:
    """A YAML block scalar, put back at the column its source sits in.

    YAML strips the *common* leading indentation from a `|` block, so an anchor copied out
    of a nested function arrives here flush left with its internal structure intact but its
    absolute position lost. Re-adding a uniform prefix restores it exactly, which keeps rule
    3 exact: the anchor's relative indentation must still match line for line, and only its
    depth is searched for.
    """
    pad = " " * columns
    return "".join(pad + line if line.strip() else line for line in block.splitlines(keepends=True))


def locate(text: str, anchor: str) -> list[tuple[int, int]]:
    """Every (indent, offset) at which `anchor` occurs. Exactly one is the only good answer.

    A match must begin at the **start of a line**. Without that, an anchor dedented by YAML
    matches at every indentation shallower than its own — the same single line found once at
    four spaces, once at three, and so on — and a perfectly good mutation reports itself
    `STALE` for five occurrences that are all the same occurrence.
    """
    hits: list[tuple[int, int]] = []
    for columns in range(MAX_INDENT + 1):
        needle = _at_indent(anchor, columns)
        start = text.find(needle)
        while start != -1:
            if start == 0 or text[start - 1] == "\n":
                hits.append((columns, start))
            start = text.find(needle, start + 1)
    return hits


class MutationEscapesTheWorkspaceError(Exception):
    """A mutation named a path outside the temporary copy.

    The guarantee this harness makes — *nothing here touches the working tree* — rests on
    every write landing inside the workspace, and `workspace / mutation.file` does not
    enforce that on its own: an absolute path replaces the left side entirely, and `..`
    walks out. No committed mutation does either, which is exactly why it would have gone
    unnoticed. Raised rather than returned, because it is not a verdict about a gate: it is
    a statement that the harness was asked to do something it must never do.
    """


def _inside(workspace: Path, relative: str) -> Path:
    candidate = (workspace / relative).resolve()
    root = workspace.resolve()
    if not candidate.is_relative_to(root):
        raise MutationEscapesTheWorkspaceError(
            f"{relative!r} resolves to {candidate}, outside the workspace at {root}. "
            "A mutation may only edit the copy."
        )
    return candidate


def _apply(workspace: Path, mutation: Mutation) -> str | None:
    """Plant the mutation, or say why it is stale. Returns the original text on success."""
    target = _inside(workspace, mutation.file)
    if not target.exists():
        return None
    original = target.read_text(encoding="utf-8")
    hits = locate(original, mutation.anchor)
    if len(hits) != 1:
        return None
    columns, start = hits[0]
    needle = _at_indent(mutation.anchor, columns)
    replacement = _at_indent(mutation.replacement, columns)
    target.write_text(
        original[:start] + replacement + original[start + len(needle) :], encoding="utf-8"
    )
    return original


def _restore(workspace: Path, mutation: Mutation, original: str) -> None:
    _inside(workspace, mutation.file).write_text(original, encoding="utf-8")


def run(claim: int) -> Report:
    """Execute one claim's mutations. A claim is required, and that is the design.

    There is deliberately no "run everything" mode. A mutation is planted to prove that one
    claim's gate bites, and `make claim-N` is where that claim is proved end to end — so a
    mutation runs there and nowhere else. Making the claim mandatory means the duplication
    this split removed cannot be reintroduced by dropping an argument, and it gives
    `ledger.the-ledger-executes-nothing` something exact to look for: a recipe that names
    this module *with* `--claim` executes, and one that names it without runs the ledger.
    """
    mutations = load_mutations(claim)
    if not mutations:
        return Report(
            claim=claim,
            title="gate-proof — no mutation is declared",
            checks=(
                Check(
                    id="gate-proof.mutations-exist",
                    unarmed_because=(
                        "this is `gate-proof` refusing to run with nothing planted. A mutation that could "
                        "break it would be editing the detector, which "
                        "`ledger.no-mutation-edits-the-detector` refuses by name."
                    ),
                    question="Is there at least one planted mutation for the claims that have evals?",
                    passed=False,
                    figure="0 mutations",
                    detail=(
                        "a gate-proof target with nothing to plant is a gate disarmed before "
                        "it was ever armed"
                    ),
                ),
            ),
        )

    results: list[Result] = []
    with tempfile.TemporaryDirectory(prefix="holdout-gate-proof-") as scratch:
        workspace = _workspace(Path(scratch))

        baselines: dict[str, dict[str, bool] | None] = {}
        baseline_errors: dict[str, str] = {}
        for module in sorted({m.eval_module for m in mutations}):
            payload, error, _ = _run_eval(workspace, module)
            baselines[module] = _states(payload) if payload else None
            baseline_errors[module] = error

        for mutation in mutations:
            results.append(_judge(workspace, mutation, baselines, baseline_errors))

    return _report(claim, results)


def _judge(
    workspace: Path,
    mutation: Mutation,
    baselines: dict[str, dict[str, bool] | None],
    baseline_errors: dict[str, str],
) -> Result:
    baseline = baselines.get(mutation.eval_module)
    if baseline is None:
        # Rule 1, in its harshest form: the eval does not even run clean, so nothing planted
        # against it can mean anything.
        return Result(
            mutation,
            Verdict.NOT_ARMED,
            f"{mutation.eval_module} does not run clean — {baseline_errors[mutation.eval_module]}",
        )

    unknown = [target for target in mutation.targets if target not in baseline]
    if unknown:
        # Rule 3, applied to the *check* rather than to the source: the mutation names a
        # check the eval no longer publishes, so its target has moved.
        return Result(
            mutation,
            Verdict.STALE,
            f"names {', '.join(unknown)}, which {mutation.eval_module} does not publish",
        )

    already_red = [target for target in mutation.targets if not baseline[target]]
    if already_red:
        return Result(
            mutation,
            Verdict.NOT_ARMED,
            f"{', '.join(already_red)} was already failing before anything was planted",
        )

    original = _apply(workspace, mutation)
    if original is None:
        # Rule 3 in its usual form: the anchor is gone, or is now ambiguous.
        target = _inside(workspace, mutation.file)
        occurrences = (
            len(locate(target.read_text(encoding="utf-8"), mutation.anchor))
            if target.exists()
            else 0
        )
        return Result(
            mutation,
            Verdict.STALE,
            f"its anchor appears {occurrences} times in {mutation.file}, not once — "
            "the code it was written against has moved",
        )
    try:
        payload, error, seconds = _run_eval(workspace, mutation.eval_module)
    finally:
        _restore(workspace, mutation, original)

    if payload is None:
        # Rule 2: something went red, and it was not the gate.
        return Result(mutation, Verdict.CRASHED, error, seconds=seconds)

    states = _states(payload)
    missing = [target for target in mutation.targets if target not in states]
    if missing:
        return Result(
            mutation,
            Verdict.CRASHED,
            f"{', '.join(missing)} vanished from the mutated run",
            seconds=seconds,
        )
    survived = [target for target in mutation.targets if states[target]]
    if survived:
        return Result(
            mutation,
            Verdict.SURVIVED,
            f"{', '.join(survived)} stayed green with the gate broken",
            seconds=seconds,
        )
    also = tuple(
        check for check, passed in states.items() if not passed and check not in mutation.targets
    )
    return Result(
        mutation, Verdict.BIT, "", tripped=mutation.targets, also_fell=also, seconds=seconds
    )


def _report(claim: int, results: list[Result]) -> Report:
    checks: list[Check] = []
    for result in results:
        bit = result.verdict is Verdict.BIT
        # **The seconds are on every row that ran, not only on the slow one.** A budget is
        # judged by the distance between the slowest mutation and the limit, and that distance
        # is invisible while the only run with a number beside it is the one that already
        # exceeded it. `TIMEOUT_SECONDS` was raised once from a laptop measurement and killed a
        # mutation on a four-core runner, which is `CLAUDE.md`'s *assertion wearing a number*
        # arriving inside `gate-proof` itself.
        clock = f" · {result.seconds:.0f}s" if result.seconds else ""
        figure = f"{result.verdict.value}{clock}"
        if bit:
            figure = f"bit · {', '.join(result.tripped)}"
            if result.also_fell:
                figure += f" (also {len(result.also_fell)} more)"
            figure += clock
        checks.append(
            Check(
                id=result.mutation.id,
                question=(
                    f"Break this on purpose — {result.mutation.breaks} — and does "
                    f"{', '.join(result.mutation.targets)} refuse it?"
                ),
                passed=bit,
                figure=figure,
                detail=result.detail,
                counterexamples=() if bit else (f"declared in {result.mutation.ref}",),
            )
        )
    bit_count = sum(1 for r in results if r.verdict is Verdict.BIT)
    ran = [r for r in results if r.seconds]
    # **Published on every run, not only when something exceeds the budget.** The headroom is
    # the figure a later session needs in order to size `TIMEOUT_SECONDS` from a measurement
    # rather than from a projection, and it can only be read while nothing has failed yet.
    budget: tuple[tuple[str, str], ...] = ()
    if ran:
        slowest = max(ran, key=lambda r: r.seconds)
        budget = (
            (
                "slowest mutation",
                f"{slowest.seconds:.0f}s of a {TIMEOUT_SECONDS}s budget "
                f"({slowest.seconds / TIMEOUT_SECONDS:.0%}) · {slowest.mutation.id}",
            ),
        )
    # A crash is a fact about the harness and a survival is a fact about a gate, and the shared
    # report line calls both of them `checks failed`. Naming the difference is the only thing
    # this layer can do about it, and it is worth more than the wording: `bit 7/8` beside a
    # crash does **not** mean a gate went quiet.
    crashed = [
        r for r in results if r.verdict is not Verdict.BIT and r.verdict is not Verdict.SURVIVED
    ]
    harness = (
        (
            "that anything is known about the gates a CRASHED, STALE or NOT-ARMED mutation "
            "names: the mutated eval never produced a verdict, so no gate was asked. Only "
            "SURVIVED says a gate did not bite, and the red line above calls both of them "
            "`checks failed`",
        )
        if crashed
        else ()
    )
    return Report(
        claim=claim,
        title=f"gate-proof — every gate bites, or it is not a gate ({bit_count}/{len(results)})",
        checks=tuple(checks),
        numbers=(
            ("mutations planted", str(len(results))),
            ("bit", f"{bit_count}/{len(results)}"),
            *(
                (f"  {verdict.value}", str(sum(1 for r in results if r.verdict is verdict)))
                for verdict in Verdict
                if verdict is not Verdict.BIT and any(r.verdict is verdict for r in results)
            ),
            *budget,
        ),
        notes=(
            "that every gate bites on every possible mutation — this is the set of breaks we "
            "thought of, which is the same honest limit the six adversarial worlds carry",
            "that a surviving mutation is harmless; SURVIVED means a gate did not bite and is "
            "a finding, never something to widen an assertion around",
            *harness,
        ),
    )
