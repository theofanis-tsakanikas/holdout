"""`make figures` — a gate reports on what it examined, and this is what checks the difference.

The rule, which `CLAUDE.md` now carries:

> **A gate reports on what it examined. It becomes a lie when it reports what it examined as
> if it were what exists.**

Two instances of it are already in this repository's record and they are the same defect at two
coverages. **At zero:** the language rule was first checked with `grep -P`, which BSD grep does
not implement; it exited 1, stderr was discarded, and a count of zero was read off a command
that never ran the check. **At seven of eight:** `ci.yml`'s `discover` step matched claim targets
with `claim-[1-7]`, so a `claim-8` would have been invisible to it — and since `claims-complete`
only aggregates what `discover` emitted, invisible to the required check as well. A whole claim
could have landed with its gate never running and nothing anywhere would have said so.

So every gate declares **how its population is enumerated**, and this module enumerates it a
second time and compares against what the gate says it examined.

Why the comparison is asymmetric
--------------------------------
**Red when `examined < enumerated`. Never red when `examined > enumerated`.**

Under-coverage is the lie the rule names: the gate looked at less than exists and reported as
though it had looked at everything. Over-coverage is a tool doing *more* than it was asked, and
that is not a lie about what exists.

The distinction was measured rather than reasoned. Measured 2026-08-30, on ruff 0.16.4:
`ruff format --check` reported 190 files over the six directories `PYTHON_DIRS` names, and an
independent count of `*.py` in the same six gave 182. The eight are Markdown -- ruff formats
Python inside fenced blocks, and has since some version nobody here chose. A gate that froze 190
would have gone red on that upgrade for a reason that is not a defect, and a gate that froze 182
would have gone red when ruff stopped. Only the direction matters, and only one direction is a
lie.

**Those two numbers are dated on purpose and are not in `PROSE` below.** They are a measurement
of a moment, which is what `docs/SCENARIO.md` calls `[M]` with the command beside it; the live
figures are in the table `make figures` prints on every run. Registering them would mean every
branch that adds a Python file had to edit this paragraph, which is friction bought for nothing —
the number is evidence for an argument about direction, not an assertion about today.

It is the same shape as `Money`'s three roundings: *a bound that rounds toward what it forbids
is not a bound.*

What a population is declared as
--------------------------------
**A rule, not a number.** A frozen count is an assertion that needs its own measurement and goes
stale on ordinary work — the defect `CLAUDE.md` catalogues ten times. An enumeration rule is a
second implementation of the question *what exists*, in the sense `evals/README.md`'s rule 5 uses
the words: computed twice, sharing nothing with the thing under test but the declared inputs.

**The one gate this cannot cover is `test`, and the reason is circularity rather than effort.**
A suite's population is what pytest collected and its examined is what actually ran, and the
second is only known *after* the suite has run — while `make figures` runs before it, inside the
same `make check`. Asking pytest to collect twice would measure collection and not execution,
which is a number that agrees with itself. What stands behind `test` instead is that a skipped or
deselected test is printed in its own summary line, which is a reader's job rather than a gate's,
and that is stated here rather than left to be discovered.

What this does not cover, stated because a coverage checker that overstates its own coverage
would be the joke it is built to prevent: it covers the **gates**, not every number in prose. The
`[M]` half of the four-kinds rule — a figure in a document re-run against the command that
produces it — is `PROSE` below, and it is deliberately small and says how small. Most numbers in
`PLAN.md` and `TASKS.md` are *records*: doctrine rule 4 keeps superseded figures forever with the
restatement beside them, so re-running them would go red on history that is correct as written.
Only text that asserts the present tense can be checked this way.
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from ops import expiry, findings, language

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The six directories the Makefile lints and type-checks. Read from the Makefile rather than
#: repeated here, so this module cannot disagree with the thing it is measuring.
PYTHON_DIRS_LINE = re.compile(r"^PYTHON_DIRS\s*:=\s*(?P<dirs>.+)$", re.MULTILINE)

#: How `ci.yml` finds the claim targets it will run. Read out of the workflow for the same
#: reason: a copy of the pattern here would agree with itself.
DISCOVER_PATTERN = re.compile(r"grep -oE '(?P<pattern>\^\([^']+\):)'")

#: The floor `discover` refuses below, read out of the workflow rather than repeated here.
DISCOVER_FLOOR = re.compile(r"^\s*FLOOR=(?P<floor>\d+)\s*$", re.MULTILINE)

#: What a claim target looks like when nobody is trying to keep the list short. `discover` must
#: find every one of these; if it finds fewer, a claim exists whose gate never runs.
ANY_CLAIM_TARGET = re.compile(r"^(claim-[0-9]+|gate-proof|preview-audit):", re.MULTILINE)


class InstrumentMissingError(RuntimeError):
    """A population could not be enumerated, or a gate could not be asked what it examined.

    Raised rather than returned as zero, because zero is the answer a working instrument gives
    about an empty tree and this is not that. `grep -P` is why this class exists.
    """


@dataclass(frozen=True, slots=True)
class Coverage:
    """One gate, how its population is enumerated, and how to ask what it examined."""

    gate: str
    population: str
    enumerate_: Callable[[], int]
    examine: Callable[[], int]
    note: str = ""


@dataclass(frozen=True, slots=True)
class Row:
    gate: str
    population: str
    enumerated: int
    examined: int
    note: str

    @property
    def under(self) -> int:
        return max(0, self.enumerated - self.examined)

    @property
    def passed(self) -> bool:
        return self.examined >= self.enumerated


# --------------------------------------------------------------------- enumerating populations


def _makefile() -> str:
    return (REPO_ROOT / "Makefile").read_text(encoding="utf-8")


def _workflow() -> str:
    return (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")


def python_dirs() -> list[Path]:
    match = PYTHON_DIRS_LINE.search(_makefile())
    if match is None:
        raise InstrumentMissingError(
            "PYTHON_DIRS is not in the Makefile in the shape this module reads it. The "
            "population of the lint and typecheck gates cannot be enumerated, so nothing is "
            "reported about them rather than zero being reported."
        )
    return [REPO_ROOT / part for part in match.group("dirs").split()]


def python_files() -> int:
    found = 0
    for directory in python_dirs():
        if not directory.is_dir():
            raise InstrumentMissingError(f"{directory} is named by PYTHON_DIRS and does not exist")
        found += sum(1 for p in directory.rglob("*.py") if "__pycache__" not in p.parts)
    return found


def _tool_output(command: list[str]) -> str:
    """Run a tool and return everything it said. A tool that will not run is not a zero."""
    try:
        completed = subprocess.run(
            command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=300, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InstrumentMissingError(f"{' '.join(command)} did not run: {exc}") from exc
    return completed.stdout + completed.stderr


def _tool_count(command: list[str], pattern: str) -> int:
    """Read one count a tool prints. A parse failure is `InstrumentMissingError`.

    **Not a zero.** The whole argument of this module is that a tool which did not answer and a
    tool which answered *nothing* are different events, and only one of them is a clean tree.
    """
    text = _tool_output(command)
    match = re.search(pattern, text)
    if match is None:
        raise InstrumentMissingError(
            f"{' '.join(command)} did not print a count this module could read. Its output is a "
            f"message string and message strings change; the pattern is {pattern!r}. This is a "
            "red run rather than a count of zero."
        )
    return int(match.group(1))


def ruff_examined() -> int:
    """Every file ruff looked at, which is the sum of the two counts it prints.

    On a clean tree it says `N files already formatted`; on a dirty one it says
    `M files would be reformatted, N files already formatted`, and reading only the first
    number would report a coverage of one. That is this module's own defect, caught by this
    module on its first run against an unformatted copy of itself.
    """
    dirs = [str(d.relative_to(REPO_ROOT)) for d in python_dirs()]
    text = _tool_output(["uv", "run", "ruff", "format", "--check", *dirs])
    counts = [
        int(n) for n in re.findall(r"(\d+) files? (?:already formatted|would be reformatted)", text)
    ]
    if not counts:
        raise InstrumentMissingError(
            "ruff printed no file count this module could read. Its output is a message string "
            "and message strings change; this is a red run rather than a count of zero."
        )
    return sum(counts)


def mypy_examined() -> int:
    return _tool_count(["uv", "run", "mypy"], r"(\d+) source files?")


def language_examined() -> int:
    _, files_read, _ = language.scan()
    return files_read


def language_population() -> int:
    return len(language.content_files())


def deferrals_declared() -> int:
    """The `· deferred YYYY-MM-DD` markers in the section — `make expiry`'s second count."""
    text = (REPO_ROOT / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    body = expiry._section_body(text)
    return len(expiry._MARKER.findall(body))


def deferrals_parsed() -> int:
    return len(expiry.parse((REPO_ROOT / "docs" / "DECISIONS.md").read_text(encoding="utf-8")))


def finding_markers() -> int:
    """The `· found` markers in the registry — the second count, as `expiry` does it."""
    text = (REPO_ROOT / "docs" / "FINDINGS.md").read_text(encoding="utf-8")
    return len(findings._MARKER.findall(findings._body(text)))


def findings_parsed() -> int:
    return len(findings.parse((REPO_ROOT / "docs" / "FINDINGS.md").read_text(encoding="utf-8")))


def mutation_files() -> int:
    root = REPO_ROOT / "evals" / "gate_proof" / "mutations"
    if not root.is_dir():
        raise InstrumentMissingError("the mutation tree is not where the ledger looks for it")
    return sum(1 for p in root.rglob("*.yaml"))


def mutations_loaded() -> int:
    from evals.gate_proof import ledger

    return len(ledger.load_mutations())


#: How `evals/report.py`'s `Check` is bound in a module that constructs one. Resolved per file
#: rather than assumed to be the word `Check`, because `ledger.declared_checks` matches that word
#: and a second reading that made the same assumption would agree with it for free.
def _check_is_bound_to(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.endswith("report"):
            names |= {a.asname or a.name for a in node.names if a.name == "Check"}
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.endswith("report"):
                    names.add(f"{alias.asname or alias.name}.Check")
    return names


def check_ids_that_exist() -> int:
    """Every distinct `Check(...)` id in the tree, walked from PYTHON_DIRS.

    The **population** side of the newest gate. `ledger.declared_checks` walks `CHECK_SOURCES`
    and matches the literal word `Check`; this walks the six directories the Makefile already
    lints and resolves whatever name `Check` was imported under in each file. Two different
    starting points and two different matchers, so narrowing `CHECK_SOURCES` to a subtree, or
    importing `Check` under an alias, shows up here as under-coverage instead of quietly
    shrinking the count the ledger prints.

    Distinct **ids**, not constructions: three checks are built in two branches of one function
    and the ledger merges them by id, so counting constructions would report a permanent
    four-check shortfall that is not one.
    """
    found: set[str] = set()
    for directory in python_dirs():
        if not directory.is_dir():
            raise InstrumentMissingError(f"{directory} is named by PYTHON_DIRS and does not exist")
        for path in sorted(directory.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError as broken:  # pragma: no cover - the suite would be red first
                raise InstrumentMissingError(
                    f"{path} does not parse, so it cannot be read"
                ) from broken
            bound = _check_is_bound_to(tree)
            if not bound:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                called = (
                    func.id
                    if isinstance(func, ast.Name)
                    else ast.unparse(func)
                    if isinstance(func, ast.Attribute)
                    else ""
                )
                if called not in bound:
                    continue
                words = {k.arg: k.value for k in node.keywords if k.arg}
                identifier = words.get("id")
                if isinstance(identifier, ast.Constant) and isinstance(identifier.value, str):
                    found.add(identifier.value)
    return len(found)


def check_ids_the_ledger_declares() -> int:
    from evals.gate_proof import ledger

    return len(ledger.declared_checks())


def claim_targets_that_exist() -> int:
    return len(ANY_CLAIM_TARGET.findall(_makefile()))


def claim_targets_discover_finds() -> int:
    """Apply `ci.yml`'s own pattern, read out of `ci.yml`, to the Makefile.

    The pattern is not copied here. A copy would be a second definition that agreed with itself
    on the day it was written, which is the thing this repository refuses everywhere else.
    """
    match = DISCOVER_PATTERN.search(_workflow())
    if match is None:
        raise InstrumentMissingError(
            "the discovery grep is not in ci.yml in the shape this module reads it, so what CI "
            "would find cannot be computed. Nothing is reported rather than a zero."
        )
    pattern = match.group("pattern").replace("^(", "^(?:")
    return len(re.findall(pattern, _makefile(), re.MULTILINE))


def discover_floor() -> int:
    match = DISCOVER_FLOOR.search(_workflow())
    if match is None:
        raise InstrumentMissingError(
            "the discovery floor is not in ci.yml in the shape this module reads it, so the "
            "number CI refuses below cannot be checked against the Makefile."
        )
    return int(match.group("floor"))


#: Every gate, its population as a rule, and how to ask what it examined.
COVERAGE: tuple[Coverage, ...] = (
    Coverage(
        "lint",
        "*.py under the six directories PYTHON_DIRS names",
        python_files,
        ruff_examined,
        "ruff also formats Python inside Markdown, so it examines more than this enumerates. "
        "That is why the comparison is one-sided.",
    ),
    Coverage(
        "typecheck",
        "*.py under the six directories PYTHON_DIRS names",
        python_files,
        mypy_examined,
        "mypy's own file list is PYTHON_DIRS, declared twice — in pyproject.toml and in the "
        "Makefile — and this is the only thing that compares them.",
    ),
    Coverage(
        "language",
        "every file that is repository content",
        language_population,
        language_examined,
        "a file that cannot be decoded as UTF-8 is enumerated and not examined, which is "
        "correct and would show here as under-coverage if it ever happened.",
    ),
    Coverage(
        "findings",
        "the `· found` markers in docs/FINDINGS.md",
        finding_markers,
        findings_parsed,
        "a finding header that stopped parsing is a finding nobody is holding, which is the "
        "state the registry was built for.",
    ),
    Coverage(
        "expiry",
        "the `· deferred` markers in the Deliberately deferred section",
        deferrals_declared,
        deferrals_parsed,
        "make expiry already cross-counts these two internally; this is the same question "
        "asked from outside, so a change to its own arithmetic cannot silence it.",
    ),
    Coverage(
        "gate-proof",
        "every YAML file under evals/gate_proof/mutations/",
        mutation_files,
        mutations_loaded,
        "a mutation the loader skips is a planted break that never runs, which is the orphan "
        "the ledger was built to refuse — from the other side.",
    ),
    Coverage(
        "armed-or-says-why",
        "every distinct Check(...) id under the six directories PYTHON_DIRS names",
        check_ids_that_exist,
        check_ids_the_ledger_declares,
        "the newest gate sorts a population into armed, un-armable and unarmed — and a "
        "population it enumerates itself. Narrow CHECK_SOURCES and the three counts still "
        "print, still sum, and describe fewer checks than exist.",
    ),
    Coverage(
        "discover",
        "every claim-N, gate-proof and preview-audit target in the Makefile",
        claim_targets_that_exist,
        claim_targets_discover_finds,
        "the one that was already lying: claim-[1-7] cannot see a claim-8, and claims-complete "
        "aggregates only what discover emits, so the required check would have been silent too.",
    ),
)

#: A second question about `discover`, and it is not a coverage one: the floor it refuses
#: below is a number in a workflow, which is an assertion wearing a number instead of a verb.
#: It is checked against the Makefile here so it cannot go stale downward -- a floor above what
#: exists would fail every run, and a floor below it would let a deleted target through.
FLOOR_MUST_NOT_EXCEED = ("discover", discover_floor, claim_targets_that_exist)

#: Numbers written out as words, so a figure asserted as "eighteen" can be compared with 18.
#: Small on purpose: past twenty a document writes the digits, and a mapping that went further
#: would be inviting prose nobody can check.
WORDS: dict[str, int] = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}


@dataclass(frozen=True, slots=True)
class Figure:
    """A number asserted in prose, and the thing that produces it now.

    **Every pattern here spans whitespace with `\\s+` rather than a literal space**, and that is
    not tidiness. These files wrap at 100 columns, so a sentence that fits on one line today is
    two lines after the next edit — and a pattern that then matched nothing would report *the
    figure is not there* rather than *the figure disagrees*. That is the failure the reviewing
    session hit on 2026-08-31: a regex requiring `\u00b7 deferred` on a single line missed ten of
    thirty-five wrapped headers in `docs/DECISIONS.md` and reported as though it had read them
    all. It happened here within the hour, when this very sentence's own figure moved from
    eighteen to nineteen and the rewrap took it out of reach of its own pattern.
    """

    path: str
    pattern: str
    compute: Callable[[], int]
    says: str


def _as_int(written: str) -> int | None:
    cleaned = written.strip().lower().replace(",", "").replace("**", "")
    if cleaned.isdigit():
        return int(cleaned)
    return WORDS.get(cleaned)


#: The `[M]` half — a figure asserted in prose, and the thing that produces it.
#:
#: **Deliberately small, and the reason is doctrine rule 4.** `PLAN.md` and `TASKS.md` are the
#: record: they keep superseded figures forever with the restatement beside them, so re-running
#: a number there would go red on history that is correct as written. Only text asserting the
#: **present tense** can be checked this way, and which text that is remains a judgment rather
#: than a rule -- which is why this list is written by hand and its size is printed on every run
#: rather than implied. `docs/SCENARIO.md` does the same job with `[M]` tags and the command
#: beside each figure; this is the half a command can re-run.
PROSE: tuple[Figure, ...] = (
    Figure(
        "ops/language.py",
        r"uses\s+\*\*(?P<n>[a-z]+)\*\*\s+distinct\s+Greek\s+tokens",
        lambda: len(language.ALLOWED),
        "how many Greek tokens the allowed vocabulary holds",
    ),
    Figure(
        "ops/language.py",
        r"outside\s+the\s+(?P<n>[a-z]+)\s+excepted\s+paths",
        lambda: len(language.EXCEPTED_PATHS),
        "how many excepted paths there are",
    ),
)


def prose_failures() -> tuple[list[str], list[str]]:
    """Every registered figure, recomputed and compared with what its document says."""
    failures: list[str] = []
    missing: list[str] = []
    for figure in PROSE:
        path = REPO_ROOT / figure.path
        if not path.is_file():
            missing.append(f"{figure.path} does not exist, so {figure.says} cannot be checked")
            continue
        match = re.search(figure.pattern, path.read_text(encoding="utf-8"))
        if match is None:
            missing.append(
                f"{figure.path}: the sentence carrying {figure.says} is not there in the shape "
                "this registry reads it. A figure that cannot be found is not a figure that "
                "agrees."
            )
            continue
        written = _as_int(match.group("n"))
        now = figure.compute()
        if written is None:
            missing.append(f"{figure.path}: {match.group('n')!r} is not a number this can read")
        elif written != now:
            failures.append(
                f"{figure.path} says {match.group('n')} for {figure.says}; it is now {now}"
            )
    return failures, missing


def floor_failures() -> tuple[list[str], list[str]]:
    """The declared floor may not exceed what exists, or every run is red for the wrong reason."""
    _, floor_of, exists_of = FLOOR_MUST_NOT_EXCEED
    try:
        floor, exists = floor_of(), exists_of()
    except InstrumentMissingError as exc:
        return [], [f"discover floor: {exc}"]
    if floor > exists:
        return (
            [
                f"discover declares a floor of {floor} and the Makefile holds {exists} target(s). "
                "A floor above what exists fails every run; lower it in the change that removed "
                "the target, and say why in the same commit."
            ],
            [],
        )
    return [], []


def rows() -> tuple[list[Row], list[str]]:
    found: list[Row] = []
    missing: list[str] = []
    for entry in COVERAGE:
        try:
            enumerated = entry.enumerate_()
            examined = entry.examine()
        except InstrumentMissingError as exc:
            missing.append(f"{entry.gate}: {exc}")
            continue
        found.append(
            Row(
                gate=entry.gate,
                population=entry.population,
                enumerated=enumerated,
                examined=examined,
                note=entry.note,
            )
        )
    return found, missing


def report(found: list[Row], missing: list[str], out: TextIO) -> int:
    floors, floor_missing = floor_failures()
    prose, prose_missing = prose_failures()
    missing = [*missing, *floor_missing, *prose_missing]
    print("figures  a gate reports on what it examined; this is the difference", file=out)
    print("", file=out)
    print(f"  {'gate':<18} {'exists':>7} {'examined':>9}   population", file=out)
    for row in sorted(found, key=lambda r: r.gate):
        mark = "  " if row.passed else "<<"
        print(
            f"  {row.gate:<18} {row.enumerated:>7} {row.examined:>9} {mark} {row.population}",
            file=out,
        )
    print("", file=out)

    failures = [row for row in found if not row.passed]
    if prose:
        print(f"FAIL    {len(prose)} figure(s) in prose no longer reproduce", file=out)
        for line in prose:
            print(f"        {line}", file=out)
        print("", file=out)
    if floors:
        print("FAIL    a declared floor does not match what exists", file=out)
        for line in floors:
            print(f"        {line}", file=out)
        print("", file=out)
    if missing:
        print("FAIL    an instrument could not answer, which is not a count of zero", file=out)
        for line in missing:
            print(f"        {line}", file=out)
        print("", file=out)
    if failures:
        print(f"FAIL    {len(failures)} gate(s) examined less than exists", file=out)
        for row in failures:
            print(
                f"        {row.gate}: {row.under} of {row.enumerated} never looked at "
                f"— {row.population}",
                file=out,
            )
            if row.note:
                print(f"          {row.note}", file=out)
        print("", file=out)
        print(
            "        A gate reports on what it examined. It becomes a lie when it reports what "
            "it examined",
            file=out,
        )
        print("        as if it were what exists.", file=out)
        return 1
    if missing or floors or prose:
        return 1

    print(f"  {len(PROSE)} figure(s) in prose re-run and unchanged", file=out)
    print(
        "        Only present-tense text is registered. PLAN.md and TASKS.md keep superseded",
        file=out,
    )
    print(
        "        figures on purpose -- doctrine rule 4 -- so re-running those would go red on",
        file=out,
    )
    print("        history that is correct as written.", file=out)
    print("", file=out)
    print("OK      every gate examined at least what exists", file=out)
    print(
        "        Over-coverage is not a failure: ruff formats Python inside Markdown, so it "
        "examines",
        file=out,
    )
    print("        more than this enumerates. Only under-coverage is the lie.", file=out)
    return 0


def check(out: TextIO | None = None) -> int:
    stream = out or sys.stdout
    found, missing = rows()
    return report(found, missing, stream)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ops.figures", description=__doc__)
    parser.parse_args(list(argv) if argv is not None else None)
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
