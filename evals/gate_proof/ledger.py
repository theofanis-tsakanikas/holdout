"""The accountant. `make gate-proof` executes nothing and checks that nothing is unowned.

Why this is not the executor
----------------------------
Every mutation must run, and it must run **once**. When `gate-proof` executed the whole set
itself, `make claim-1` ran claim 1's thirteen mutations and `make gate-proof` ran them again
— CI spent thirteen minutes proving the same thing twice, and would have spent half an hour
once claims 2 to 4 landed.

The fix is not to make one of the two targets do less. It is to notice that *ownership* was
never checked by anything. A mutation belongs to exactly one claim: it is planted to prove
that one claim's gate bites, and `make claim-N` is where that claim is proved end to end. So
`claim-N` executes its own mutations, and this module audits the arrangement:

* **no orphan** — a mutation that no claim target would ever run. Nothing caught that before.
  A YAML file dropped into `mutations/claim-9/` when no `claim-9` target exists was, until
  now, a mutation nobody ran and nobody missed;
* **no duplicate** — a mutation two targets both run. This is the thirteen minutes;
* **no unproven gate** — a `claim-N` target with no mutations at all. CLAUDE.md's checklist
  asks it directly: *if it is a gate, is there a `gate-proof` mutation that proves it bites?*
  A claim target that has never had a break planted against it has not answered that.

Ownership is read out of the **Makefile**, because the Makefile is what CI runs. Deriving it
from anything else — a registry, a naming convention, a constant in this file — would make a
second source of truth about which command proves what, and the whole contract layer exists
to argue against second sources of truth.

What is checked here and what is checked by the executor
--------------------------------------------------------
The three rules in `engine.py` — green first, a parsed JSON reading rather than an exit code,
`STALE` on a moved target — need the eval to run, so they belong to `make claim-N`. One half
of rule 3 does not: whether a mutation's anchor still occurs exactly once in the source is a
question about text, it costs milliseconds, and asking it here means a mutation that has come
unmoored is caught by the cheap target as well as by the expensive one.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from evals.gate_proof.engine import MUTATIONS_DIR, REPO_ROOT, Mutation, load_mutations, locate
from evals.report import Check, Report

MAKEFILE = REPO_ROOT / "Makefile"

#: The trees a mutation may never edit, because they are what *detects* a mutation.
#:
#: `engine.py`'s independence argument has three separations and says the third carries it:
#: *the planter cannot tune the inputs*. Until 2026-08-29 that was prose with nothing behind
#: it — `_inside()` refuses a path that escapes the workspace and asks nothing about which
#: tree inside it a mutation edits, and the workspace copies `corpus/` and `ops/` because the
#: evals import them. So a mutation could have been written against `corpus/real/`'s committed
#: prices, or against `ops/personhood.py`'s registry, and it would have been applied silently
#: and reported `bit`. Nothing would have been proved and nothing would have gone red.
#:
#: Found by oversight level 2 on the branch that made it reachable: claim 7 added `ops` to
#: `engine.COPIED`, and before that a mutation naming it would at least have failed on a
#: missing file. `CLAUDE.md` asks which function makes a sentence true. This is the function.
DETECTOR = ("ops/", "corpus/")

#: The module both halves live in. Naming it is not enough to be executing: `engine.run`
#: requires a claim, so a recipe that names this module **with** `--claim` executes
#: mutations and one that names it without runs this ledger. There is no third thing it
#: could be doing, which is what makes the distinction safe to draw from a recipe line.
EXECUTOR = "evals.gate_proof"

_TARGET = re.compile(r"^([A-Za-z][A-Za-z0-9_.-]*)\s*:(?!=)")
_CLAIM_FLAG = re.compile(r"--claim\s+(\d+)")
_CLAIM_TARGET = re.compile(r"^claim-(\d+)$")


@dataclass(frozen=True, slots=True)
class Target:
    name: str
    recipe: tuple[str, ...]

    @property
    def claim(self) -> int | None:
        """The claim this target proves, if it is a claim target at all."""
        match = _CLAIM_TARGET.match(self.name)
        return int(match.group(1)) if match else None

    @property
    def executes(self) -> frozenset[int]:
        """Which claims' mutations this target runs."""
        return frozenset(
            int(claim)
            for line in self.recipe
            if EXECUTOR in line
            for claim in _CLAIM_FLAG.findall(line)
        )


def targets(makefile: str | None = None) -> tuple[Target, ...]:
    """Parse the Makefile into targets and their recipe lines.

    Deliberately a small hand-written parser rather than `make -pn`: shelling out to `make`
    to find out what `make` would do makes the audit depend on the tool it is auditing, and
    on that tool's version. What is needed here is only which recipe lines belong to which
    target, and that is what a tab-indented block is.
    """
    text = makefile if makefile is not None else MAKEFILE.read_text(encoding="utf-8")
    found: list[Target] = []
    name: str | None = None
    recipe: list[str] = []
    for line in text.splitlines():
        if line.startswith("\t"):
            if name is not None:
                recipe.append(line.strip())
            continue
        if name is not None:
            found.append(Target(name=name, recipe=tuple(recipe)))
            name, recipe = None, []
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _TARGET.match(line)
        if match:
            name = match.group(1)
    if name is not None:
        found.append(Target(name=name, recipe=tuple(recipe)))
    return tuple(found)


def owners_of(mutation: Mutation, all_targets: Sequence[Target]) -> tuple[str, ...]:
    """Every Makefile target that would execute this mutation."""
    return tuple(target.name for target in all_targets if mutation.claim in target.executes)


# --------------------------------------------------------------------------------- checks


def check_every_mutation_is_owned_once(
    mutations: Sequence[Mutation], all_targets: Sequence[Target]
) -> Check:
    orphans: list[str] = []
    duplicates: list[str] = []
    for mutation in mutations:
        owners = owners_of(mutation, all_targets)
        if not owners:
            orphans.append(
                f"{mutation.ref} declares claim {mutation.claim} and no Makefile target "
                "runs it — it is planted and nothing would ever trip over it"
            )
        elif len(owners) > 1:
            duplicates.append(f"{mutation.ref} is run by {', '.join(owners)}")
    failures = orphans + duplicates
    return Check(
        id="ledger.every-mutation-is-owned-once",
        question=(
            "Is every planted mutation executed by exactly one Makefile target — no orphan "
            "that nothing runs, no duplicate that two targets both run?"
        ),
        passed=not failures,
        figure=f"{len(mutations)} mutations · {len(orphans)} orphaned · {len(duplicates)} run twice",
        detail=(
            "an orphaned mutation is a break nobody plants; a duplicated one is the same "
            "eval run twice, which is minutes of CI and no additional evidence"
        ),
        counterexamples=tuple(failures),
    )


def check_every_claim_target_owns_a_gate(
    mutations: Sequence[Mutation], all_targets: Sequence[Target]
) -> Check:
    with_mutations = {m.claim for m in mutations}
    bare = [
        f"claim-{target.claim} exists and no mutation is planted against it"
        for target in all_targets
        if target.claim is not None and target.claim not in with_mutations
    ]
    claim_targets = [t for t in all_targets if t.claim is not None]
    return Check(
        id="ledger.every-claim-target-owns-a-gate",
        question=(
            "Does every `claim-N` target have at least one planted mutation — so that no "
            "claim is declared proved by a gate nobody has tried to break?"
        ),
        passed=not bare,
        figure=f"{len(claim_targets)} claim target(s) · {len(bare)} with nothing planted",
        detail=(
            "CLAUDE.md's checklist: if it is a gate, is there a gate-proof mutation that "
            "proves it bites? A target with none has not answered that question"
        ),
        counterexamples=tuple(bare),
    )


def check_the_ledger_executes_nothing(all_targets: Sequence[Target]) -> Check:
    """The invariant that keeps the arrangement from silently reverting.

    If `gate-proof` ever runs the executor again, every mutation is owned twice and the
    duplication is back. `check_every_mutation_is_owned_once` would catch it, but only as
    thirteen identical "run by claim-1, gate-proof" lines. This says it once, plainly.
    """
    offenders = [
        f"{target.name} invokes {EXECUTOR} and would run mutations it does not own"
        for target in all_targets
        if target.name == "gate-proof" and target.executes
    ]
    return Check(
        id="ledger.the-ledger-executes-nothing",
        question="Does `make gate-proof` audit the arrangement rather than re-run it?",
        passed=not offenders,
        figure="executes nothing" if not offenders else f"{len(offenders)} recipe(s) execute",
        detail="a ledger that also does the work is a second place the work can happen",
        counterexamples=tuple(offenders),
    )


def check_mutation_ids_are_unique(mutations: Sequence[Mutation]) -> Check:
    seen: dict[str, list[str]] = {}
    for mutation in mutations:
        seen.setdefault(mutation.id, []).append(mutation.ref)
    clashes = [
        f"{key!r} is declared by {', '.join(refs)}" for key, refs in seen.items() if len(refs) > 1
    ]
    return Check(
        id="ledger.mutation-ids-are-unique",
        question="Is every mutation id unique, so a verdict names exactly one planted break?",
        passed=not clashes,
        figure=f"{len(seen)} distinct ids over {len(mutations)} mutations",
        detail="two mutations sharing an id make one of the two verdicts unreadable",
        counterexamples=tuple(clashes),
    )


def check_mutation_lives_under_the_claim_it_declares(mutations: Sequence[Mutation]) -> Check:
    """The directory and the `claim:` field are two statements and they must agree.

    Ownership is computed from the field; a reader looking for claim 1's mutations reads the
    directory. If the two disagree, one of them is lying and it is not obvious which.
    """
    wrong = [
        f"{mutation.ref} declares claim {mutation.claim} but sits in {mutation.source.parent.name}"
        for mutation in mutations
        if mutation.source.parent.name != f"claim-{mutation.claim}"
    ]
    return Check(
        id="ledger.mutation-lives-under-the-claim-it-declares",
        question="Does every mutation's directory agree with the claim its own file declares?",
        passed=not wrong,
        figure=f"{len(mutations) - len(wrong)}/{len(mutations)} agree",
        detail="ownership is read from the field and looked up by the directory; both must say the same",
        counterexamples=tuple(wrong),
    )


def check_every_anchor_is_aimed_at_one_place(mutations: Sequence[Mutation]) -> Check:
    """The static half of rule 3, asked without running anything.

    The executor also asks this, against the workspace copy, and refuses with `STALE`. Asking
    it here too costs milliseconds and means a mutation that has come unmoored from the code
    it was written against is caught by the cheap target as well as by the three-minute one.
    """
    adrift: list[str] = []
    for mutation in mutations:
        target = REPO_ROOT / mutation.file
        if not target.exists():
            adrift.append(f"{mutation.ref} points at {mutation.file}, which does not exist")
            continue
        hits = len(locate(target.read_text(encoding="utf-8"), mutation.anchor))
        if hits != 1:
            adrift.append(
                f"{mutation.ref}: its anchor occurs {hits} times in {mutation.file}, not once"
            )
    return Check(
        id="ledger.every-anchor-is-aimed-at-one-place",
        question=(
            "Does every mutation's anchor still occur exactly once in the source it names — "
            "so that no planted break is aimed at code that has moved?"
        ),
        passed=not adrift,
        figure=f"{len(mutations) - len(adrift)}/{len(mutations)} anchors land",
        detail="a mutation whose target moved is STALE, never passed — asked here without running anything",
        counterexamples=tuple(adrift),
    )


def check_no_mutation_edits_the_detector(mutations: Sequence[Mutation]) -> Check:
    """The separation `engine.py` says carries its independence argument, made structural.

    A mutation edits the **system**. The corpus is what the system is attacked *from* and
    `ops/` is where the rules the system is measured by live; a planter that may edit either
    is a planter that can make any gate appear to bite. This is asked here, in the cheap
    target, because it is a question about a string and needs nothing to run.
    """
    offences = [
        f"{mutation.ref} edits {mutation.file}, which is the detector rather than the system"
        for mutation in mutations
        if mutation.file.startswith(DETECTOR)
    ]
    return Check(
        id="ledger.no-mutation-edits-the-detector",
        question=(
            "Does every planted break edit the system rather than the thing that detects it — "
            f"nothing under {' or '.join(DETECTOR)}?"
        ),
        passed=not offences,
        figure=f"{len(mutations) - len(offences)}/{len(mutations)} edit the system",
        detail=(
            "a planter that can tune the inputs or rewrite the registry can make any gate "
            "appear to bite, which is the separation engine.py says carries its argument"
        ),
        counterexamples=tuple(offences),
    )


def check_the_mutation_tree_is_all_yaml() -> Check:
    """Nothing under `mutations/` that `load_mutations` would silently skip."""
    strays = [
        str(path.relative_to(MUTATIONS_DIR))
        for path in sorted(MUTATIONS_DIR.rglob("*"))
        if path.is_file() and path.suffix != ".yaml"
    ]
    misplaced = [
        str(path.relative_to(MUTATIONS_DIR)) for path in sorted(MUTATIONS_DIR.glob("*.yaml"))
    ]
    failures = strays + [
        f"{p} sits outside a claim-N directory and is never loaded" for p in misplaced
    ]
    return Check(
        id="ledger.the-mutation-tree-holds-only-loadable-mutations",
        question=(
            "Is every file under `mutations/` a YAML inside a `claim-N` directory — so that "
            "nothing is planted where the loader will not find it?"
        ),
        passed=not failures,
        figure=f"{len(strays)} non-YAML · {len(misplaced)} outside a claim directory",
        detail="a mutation the loader skips is an orphan the ownership check cannot see either",
        counterexamples=tuple(failures),
    )


# --------------------------------------------------------------------------------- report


def audit() -> Report:
    mutations = load_mutations()
    all_targets = targets()

    checks = (
        check_every_mutation_is_owned_once(mutations, all_targets),
        check_every_claim_target_owns_a_gate(mutations, all_targets),
        check_the_ledger_executes_nothing(all_targets),
        check_mutation_ids_are_unique(mutations),
        check_mutation_lives_under_the_claim_it_declares(mutations),
        check_every_anchor_is_aimed_at_one_place(mutations),
        check_no_mutation_edits_the_detector(mutations),
        check_the_mutation_tree_is_all_yaml(),
    )

    by_claim: dict[int, int] = {}
    for mutation in mutations:
        by_claim[mutation.claim] = by_claim.get(mutation.claim, 0) + 1

    numbers: list[tuple[str, str]] = [("mutations planted", str(len(mutations)))]
    for claim in sorted(by_claim):
        owners = {name for m in mutations if m.claim == claim for name in owners_of(m, all_targets)}
        numbers.append(
            (
                f"  claim {claim}",
                f"{by_claim[claim]} mutation(s), run by {', '.join(sorted(owners)) or 'NOBODY'}",
            )
        )

    return Report(
        claim=None,
        title="gate-proof — the ledger: every mutation owned once, and nothing unowned",
        checks=checks,
        numbers=tuple(numbers),
        notes=(
            "that any gate bites — this target runs nothing. `make claim-N` plants that "
            "claim's mutations and demands a refusal from the check each one names",
            "that the mutation set is complete; it is the set of breaks we thought of, and "
            "a curated set is not mutation testing",
        ),
    )
