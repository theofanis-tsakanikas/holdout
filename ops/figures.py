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
`ruff format --check` reported 190 files over the directories `PYTHON_DIRS` names, and an
independent count of `*.py` in the same directories gave 182. The eight are Markdown -- ruff formats
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
from functools import cache
from pathlib import Path
from typing import TextIO

from ops import expiry, findings, language

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The directories the Makefile lints and type-checks. Read from the Makefile rather than
#: repeated here, so this module cannot disagree with the thing it is measuring.
PYTHON_DIRS_LINE = re.compile(r"^PYTHON_DIRS\s*:=\s*(?P<dirs>.+)$", re.MULTILINE)

#: How `ci.yml` finds the claim targets it will run. Read out of the workflow for the same
#: reason: a copy of the pattern here would agree with itself.
DISCOVER_PATTERN = re.compile(r"grep -oE '(?P<pattern>\^\([^']+\):)'")

#: The floor `discover` refuses below, read out of the workflow rather than repeated here.
DISCOVER_FLOOR = re.compile(r"^\s*FLOOR=(?P<floor>\d+)\s*$", re.MULTILINE)

#: What a target CI must run looks like when nobody is trying to keep the list short.
#: `discover` must find every one of these; if it finds fewer, a gate exists that never runs.
#:
#: **`silver` and `gold` are here and neither is a claim.** `T010` put the engine silver needs
#: in an optional dependency group and `T011` did the same for dbt, so both sets of tests are
#: deselected from the suite and run by one job each — which is exactly the shape that must not
#: be discoverable by accident. Written out here independently of `ci.yml`, which is the whole
#: mechanism: `claim_targets_discover_finds` reads that file's own pattern out of it, and the
#: two are compared rather than shared. **Adding a target therefore means editing this line and
#: `ci.yml`'s grep and the floor**, and the three disagreeing is the failure this row reports.
ANY_CLAIM_TARGET = re.compile(
    r"^(claim-[0-9]+|gate-proof|preview-audit|silver|gold):", re.MULTILINE
)


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
    and matches the literal word `Check`; this walks the directories the Makefile already
    lints and resolves whatever name `Check` was imported under in each file. Two different
    starting points and two different matchers, so narrowing `CHECK_SOURCES` to a subtree, or
    importing `Check` under an alias, shows up here as under-coverage instead of quietly
    shrinking the count the ledger prints.

    Distinct **ids**, not constructions: three checks are built in two branches of one function
    and the ledger merges them by id, so counting constructions would report a permanent
    four-check shortfall that is not one.

    **The two populations are deliberately asymmetric, and this one is the broader.** The ledger
    walks `CHECK_SOURCES`, which is `evals/`; this walks every directory `PYTHON_DIRS` names.
    So a `Check(...)` constructed anywhere outside `evals/` is counted here and not there, and
    this gate goes red at 68 against 67.

    That is the intended behaviour rather than an edge to smooth over — a check the ledger cannot
    see is precisely the narrowing this exists to catch, and it makes no difference whether the
    narrowing was done to `CHECK_SOURCES` or to where somebody put the check. But it will also
    fire the first time a `Check` is written outside `evals/` on purpose, and at that moment the
    red reads as a bug here rather than as a question about scope. It is the second: the answer is
    either to move the check or to widen `CHECK_SOURCES`, and which one is a judgment about where
    checks live. Never to narrow this walk to match, which would delete the comparison.
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


#: The layout block in `CLAUDE.md`. Read as text rather than parsed into a tree, because what is
#: being checked is whether a reader of that section would find a package named — not whether the
#: indentation is well formed.
LAYOUT_BLOCK = re.compile(r"^## Repository layout$(?P<body>.*?)^---$", re.MULTILINE | re.DOTALL)


def layout_packages() -> int:
    """Every directory `CLAUDE.md`'s layout section must name, enumerated from the tree.

    **The population, stated as a rule.** Every top-level directory **git tracks**, plus every
    package under `src/holdout/`. Not every directory at any depth: the section names `evals/`
    and `evals/gate_proof/` but not `evals/guardrail/`, and demanding the rest would be
    inventing a requirement nobody stated. What it does demand is that a package a reader would
    go looking for is findable in the map they were told to read first.

    Nothing is excluded by name. `_layout_population` asks git, which is why `.github/` is in
    the population and gitignored scratch is not — see the defect recorded there.
    """
    return len(_layout_population())


def layout_packages_named() -> int:
    """How many of them the section actually names."""
    match = LAYOUT_BLOCK.search((REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8"))
    if match is None:
        raise InstrumentMissingError(
            "CLAUDE.md has no `## Repository layout` section in the shape this module reads "
            "it, so what the map names cannot be computed. Nothing is reported rather than a "
            "zero."
        )
    body = match.group("body")
    named = 0
    for directory in _layout_population():
        relative = directory.relative_to(REPO_ROOT).as_posix()
        if f"{relative}/" in body or re.search(
            rf"^\s+{re.escape(directory.name)}/", body, re.MULTILINE
        ):
            named += 1
    return named


def _tracked_paths() -> list[str]:
    """What git tracks, which is the only defensible answer to *what is repository content*."""
    listing = _tool_output(["git", "ls-files"])
    tracked = [line for line in listing.splitlines() if line.strip()]
    if not tracked:
        raise InstrumentMissingError(
            "git ls-files returned nothing, so repository content cannot be enumerated. That is "
            "an instrument that could not answer, not a repository with no files in it."
        )
    return tracked


def _layout_population() -> list[Path]:
    """Every top-level directory git tracks, plus every package under `src/holdout/`.

    **Read from git rather than from the working directory, and that was a defect before it was
    a rule.** The first version walked `REPO_ROOT.iterdir()` with a hand-written exclusion list
    — `.venv`, `.git`, dot-directories other than `.claude`. It counted **20** on the author's
    laptop and **19** on a clean checkout, because `notes/` is gitignored scratch that exists
    on one machine and not the other, and it was added to `CLAUDE.md`'s map as though it were
    repository content. CI caught it; `make check` could not, because the machine running it was
    the machine the population was measured on.

    That is `CLAUDE.md`'s fourth form of the rule — *where the number will be met on hardware
    that is not the author's, the measurement is taken there* — inside the module written to
    enforce it. Asking git removes the exclusion list and the judgment with it: `.github/` is
    repository content by the same test as `.claude/`, and neither is in it because somebody
    decided so.
    """
    tracked = _tracked_paths()
    roots = sorted({part.split("/", 1)[0] for part in tracked if "/" in part})
    packages = sorted(
        {
            str(Path(part).parent)
            for part in tracked
            if part.startswith("src/holdout/") and "/" in part
        }
    )
    return [REPO_ROOT / r for r in roots] + [REPO_ROOT / p for p in packages]


#: The row shape of `CLAUDE.md`'s skills table: a backticked name, then a status cell.
_SKILL_ROW = re.compile(
    r"^\|\s*`(?P<name>[a-z][a-z-]*)`[^|]*\|\s*(?P<status>[^|]+?)\s*\|", re.MULTILINE
)


def skills_that_exist() -> int:
    """Every directory under `.claude/skills/`."""
    root = REPO_ROOT / ".claude" / "skills"
    if not root.is_dir():
        raise InstrumentMissingError(
            ".claude/skills/ is not where this module looks for it, so the skills the table "
            "claims cannot be checked against the skills that are there."
        )
    return sum(1 for d in root.iterdir() if d.is_dir() and d.name != "__pycache__")


def skills_the_table_marks_as_existing() -> int:
    """How many rows say **exists**.

    The **examined** side. `CLAUDE.md`'s skills table gained a status column on 2026-08-31
    because it had listed four skills as living here when one did — and **nothing enumerated the
    column against the directory.** A third status going stale would have looked exactly like the
    two that did not, which is the same defect the column was added to fix, one layer up.
    """
    table = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    return sum(1 for m in _SKILL_ROW.finditer(table) if m.group("status").strip("* ") == "exists")


def skills_claimed_that_are_not_there() -> tuple[list[str], list[str]]:
    """The other direction: a row saying **exists** for a skill that does not.

    The coverage comparison is one-sided by design, and this question is not — the same pair as
    the repository layout, where omitting a package and inventing one are different failures and
    only the first is under-coverage. A table naming a skill that is not there sends its reader
    looking for it.
    """
    root = REPO_ROOT / ".claude" / "skills"
    if not root.is_dir():
        return [], [".claude/skills/ is not there, so the table's claims cannot be checked"]
    present = {d.name for d in root.iterdir() if d.is_dir()}
    table = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    invented = [
        m.group("name")
        for m in _SKILL_ROW.finditer(table)
        if m.group("status").strip("* ") == "exists" and m.group("name") not in present
    ]
    if not invented:
        return [], []
    return (
        [
            f"the skills table says {name!r} exists and .claude/skills/{name}/ is not there"
            for name in sorted(set(invented))
        ],
        [],
    )


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


# ------------------------------------- what the suite deselects, and what runs it instead

#: How a Makefile recipe declares which marks it selects. `pytest -m "not claim_2"` and
#: `pytest -m claim_2` are both read; the expression is handed to pytest verbatim, never
#: re-implemented here, because a second implementation of mark selection would be a second
#: definition of which tests exist.
PYTEST_SELECTION = re.compile(
    r"""pytest\s+-m\s+(?:"(?P<quoted>[^"]+)"|'(?P<single>[^']+)'|(?P<bare>[\w.-]+))"""
)

#: Every target in the Makefile, by name, so each can be asked what its recipe does.
#:
#: **It replaced a rule that asked by name and it is the finding `#50` filed.** That rule was
#: `^claim-[\w-]*:` — broad enough to see `claim-2-shard` and `claim-2-combine`, and silent
#: about its own narrowness: nothing requires a target that owns deselected tests to be called
#: `claim-something`, and `silver` is the first one that is not. A rule that reads **recipes**
#: cannot be satisfied by a naming convention and cannot miss a target for being named oddly.
#:
#: Measured when it changed: of the 32 targets in the Makefile, exactly two hand pytest a mark
#: expression — `test` and `claim-2-tests` — so this returned precisely what the old rule
#: returned on the tree it landed in, and `silver` entered the population by existing.
ANY_TARGET_NAME = re.compile(r"^(?P<name>[a-z][\w.-]*):", re.MULTILINE)


def _recipe(target: str) -> list[str]:
    """The tab-indented lines that follow one target, or `[]` where it has none."""
    lines = _makefile().splitlines()
    for index, line in enumerate(lines):
        if line.startswith(f"{target}:"):
            recipe = []
            for following in lines[index + 1 :]:
                if not following.startswith("\t"):
                    break
                recipe.append(following)
            return recipe
    return []


def _selection_of(target: str) -> str | None:
    """The mark expression a target hands pytest, or `None` where it hands none."""
    for line in _recipe(target):
        match = PYTEST_SELECTION.search(line)
        if match is not None:
            return match.group("quoted") or match.group("single") or match.group("bare")
    return None


def suite_selection() -> str | None:
    if not _recipe("test"):
        raise InstrumentMissingError(
            "the Makefile has no `test` target with a recipe, so what the suite runs cannot be "
            "read and neither can what it leaves out. Nothing is reported rather than a zero."
        )
    return _selection_of("test")


def mark_owning_targets() -> list[str]:
    """Every target other than `test` whose recipe hands pytest a mark expression.

    **Asked of the recipes, never of the names.** A target that owns tests the suite gave up
    need not be called `claim-something` — `silver` is not — and a rule that looked for a name
    would report those tests as run by nothing while a job was provably running them.

    `test` is excluded because it is the other side of the comparison: it is what deselects.
    """
    names = sorted({m.group("name") for m in ANY_TARGET_NAME.finditer(_makefile())})
    return [name for name in names if name != "test" and _selection_of(name) is not None]


def claim_selection() -> str | None:
    """Every mark expression those targets select, as one `or`.

    Derived from the Makefile rather than declared in a list here: a list would be a second
    registry of which target owns which tests, kept by hand, in the file that exists so nobody
    has to keep one.
    """
    found: list[str] = []
    for name in mark_owning_targets():
        selection = _selection_of(name)
        if selection is not None and selection not in found:
            found.append(selection)
    if not found:
        return None
    return " or ".join(f"({selection})" for selection in found)


@cache
def _collected(expression: str) -> int:
    """How many tests one mark expression selects, asked of pytest itself.

    Cached on the expression because the tree does not change inside one process and `check()`
    is run eight times by `tests/ops/test_figures.py` alone; a cache miss is a subprocess.
    """
    text = _tool_output(["uv", "run", "pytest", "--collect-only", "-m", expression])
    if re.search(r"no tests (?:collected|ran)", text):
        return 0
    # `17/1065 tests collected (1048 deselected)` under a filter, `1065 tests collected`
    # without one. Reading the wrong half of the first shape reports the whole tree as
    # selected, which is how this function was wrong on its first run -- and it was wrong in
    # the direction that passes, because both sides then answer 1065 and the row is equal.
    match = re.search(r"(?:(?P<selected>\d+)/)?(?P<total>\d+) tests? collected", text)
    if match is None:
        raise InstrumentMissingError(
            f"pytest --collect-only -m {expression!r} printed no count this module could read. "
            "That is a red run rather than a count of zero: an expression that selects nothing "
            "and an expression pytest refused look the same from here otherwise."
        )
    return int(match.group("selected") or match.group("total"))


def tests_the_suite_deselects() -> int:
    selection = suite_selection()
    if selection is None:
        return 0
    return _collected(f"not ({selection})")


def tests_a_claim_target_runs() -> int:
    """Of the tests the suite deselects, how many some claim target selects.

    **The intersection, not the union**, so this can never exceed what it is compared against
    and equality is the only way the row passes. Counting the two sides separately would let a
    claim target select fourteen tests that are not the fourteen the suite gave up.
    """
    suite = suite_selection()
    claims = claim_selection()
    if suite is None or claims is None:
        return 0
    return _collected(f"(not ({suite})) and ({claims})")


#: Every gate, its population as a rule, and how to ask what it examined.
COVERAGE: tuple[Coverage, ...] = (
    Coverage(
        "lint",
        "*.py under the directories PYTHON_DIRS names",
        python_files,
        ruff_examined,
        "ruff also formats Python inside Markdown, so it examines more than this enumerates. "
        "That is why the comparison is one-sided.",
    ),
    Coverage(
        "typecheck",
        "*.py under the directories PYTHON_DIRS names",
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
        "every distinct Check(...) id under the directories PYTHON_DIRS names",
        check_ids_that_exist,
        check_ids_the_ledger_declares,
        "the newest gate sorts a population into armed, un-armable and unarmed — and a "
        "population it enumerates itself. Narrow CHECK_SOURCES and the three counts still "
        "print, still sum, and describe fewer checks than exist.",
    ),
    Coverage(
        "layout",
        "every top-level directory git tracks, plus every package under src/holdout/",
        layout_packages,
        layout_packages_named,
        "the map in the file every session reads first. It omitted core/demand/ and the whole "
        "of src/holdout/contracts/ — fifteen modules — and nothing could say so. Naming a "
        "directory that does not exist yet is over-coverage and not a lie about what exists; "
        "the layout marks those separately in prose.",
    ),
    Coverage(
        "skills",
        "every directory under .claude/skills/",
        skills_that_exist,
        skills_the_table_marks_as_existing,
        "the status column was added because the table listed four skills and one existed. "
        "Nothing enumerated the column against the directory, so a third status going stale "
        "would have looked exactly like the two that did not.",
    ),
    Coverage(
        "suite",
        "every test `make test` deselects",
        tests_the_suite_deselects,
        tests_a_claim_target_runs,
        "a test deselected from the suite and selected by nothing runs on no push and looks "
        "exactly like one that passed. Both sides are asked of pytest rather than read off a "
        "list, and the second is the intersection, so equality is the only pass.",
    ),
    Coverage(
        "discover",
        "every claim-N, gate-proof, preview-audit, silver and gold target in the Makefile",
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


#: The tens, so that a compound written the way English writes it can be read. Added when
#: `evals/oversight/README.md`'s *"every one of the fifty-six types"* came back as **an
#: instrument that could not answer** rather than as a disagreement -- which is the right
#: report and is exactly why that bucket is separate, but it is not a state to leave in place.
#:
#: **A rule for compounds rather than eighty more entries.** `twenty-one` through `ninety-nine`
#: is the whole of what English hyphenates below a hundred, and enumerating them would be a
#: hand-kept population of the kind this module exists to refuse. Above ninety-nine, prose in
#: this repository uses digits, and a figure written `one hundred and six` is still reported as
#: unreadable rather than guessed at.
TENS: dict[str, int] = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


def _as_int(written: str) -> int | None:
    cleaned = written.strip().lower().replace(",", "").replace("**", "")
    if cleaned.isdigit():
        return int(cleaned)
    if "-" in cleaned:
        tens, _, unit = cleaned.partition("-")
        if tens in TENS and unit in WORDS and 1 <= WORDS[unit] <= 9:
            return TENS[tens] + WORDS[unit]
        return None
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
#: Claim 7's populations and results, computed by the modules the eval itself computes them
#: with, never re-derived here. `ops.personhood` owns the registry half and is an `ops` module
#: already; `evals.oversight` owns the attack half and is imported **inside** the function.
#:
#: **What that deferral buys, measured rather than intended.** The first version of this comment
#: said it kept `make figures` running while an eval was mid-edit. It does not, and the claim
#: was written against the intent rather than against what runs: `prose_failures()` calls
#: `compute()` on every entry that matches, so the import happens on every healthy invocation
#: and a broken `evals/oversight/build.py` fails the gate either way. Planted and measured:
#:
#:     python -m ops.figures   ->  RuntimeError, raised through this function's import line
#:
#: What it does buy is one layer narrower and is worth keeping. `tests/ops/test_figures.py`
#: does `from ops import figures` at module scope, so a module-scope import here would make a
#: broken eval fail **collection** — 23 tests that have nothing to do with claim 7 disappearing
#: rather than failing. With the import deferred, collection succeeds and only the assertions
#: that need the eval go red. It is not a cycle either: `ops.figures` -> `evals.oversight.build`
#: -> `ops.personhood` imports cleanly at module scope, tested rather than assumed.
#:
#: Measured 2026-09-05 on this laptop: the whole thing is 0.02s. Nothing here is deferred for
#: cost.
@cache
def claim_7_figures() -> dict[str, int]:
    from evals.oversight.build import attacks, lexicon
    from evals.oversight.checks import EXPLAINED, refused_by_the_word_list

    from ops.personhood import FIELDS_ON_THE_DECISION_PATH, core_types, field_names

    names = lexicon()
    planted = list(attacks(names))
    return {
        "names": len(names),
        "types": len(FIELDS_ON_THE_DECISION_PATH),
        "fields": sum(len(field_names(cls)) for cls in core_types()),
        "attacks": len(planted),
        "word_list": sum(1 for attack in planted if refused_by_the_word_list(attack)),
        "explanations": len(EXPLAINED),
    }


def _claim_7(key: str) -> Callable[[], int]:
    return lambda: claim_7_figures()[key]


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
    # ---------------------------------------------------------------- claim 7's figures
    #
    # **Overturning `docs/reviews/phase-2.md` §8, on one of its two limbs and not the other.**
    # §8 declined to widen this list and said why: *"one measurement of one stale figure is not
    # grounds to widen `PROSE`, and widening it by hand is the same act as keeping
    # `NOT_CONTENT` by hand"*. The first limb is overturned by counting. It was not one figure
    # and it was not one site: **five figures across nine registered sites**, plus two records
    # restated in `PLAN.md` and `TASKS.md`, plus `corpus/real/MANIFEST.yaml`, which was already
    # stale by a whole epoch before this one -- it said 222 fields against `TASKS.md`'s own
    # record of the move to 242, and nothing anywhere had noticed.
    #
    # The second limb is **not** overturned and is not claimed to be. This list is still kept
    # by hand, still a judgment about which text asserts the present tense, and still prints
    # its own size on every run. That defence is written above and it is the same defence.
    #
    # Why claim 7 and not every claim's numbers: its figures are enumerations of what exists,
    # computed in 0.02s from modules that share nothing with the prose. Claim 2's `8/200` is a
    # result of a sharded 200-draw eval and cannot be re-run inside `make check` -- it stays
    # `[M]` with the command beside it, which is `docs/SCENARIO.md`'s half of the same rule.
    Figure(
        "CLAUDE.md",
        r"closed\s+field\s+set\s+refuses\s+(?P<n>[\d,]+)\s+of\s+[\d,]+",
        _claim_7("attacks"),
        "how many attacks the closed field set refuses, in claim 7's row",
    ),
    Figure(
        "CLAUDE.md",
        r"closed\s+field\s+set\s+refuses\s+[\d,]+\s+of\s+(?P<n>[\d,]+)",
        _claim_7("attacks"),
        "how many attacks are planted, in claim 7's row",
    ),
    Figure(
        "CLAUDE.md",
        r"hand-written\s+list\s+catches\s+35\s+of\s+(?P<n>[\d,]+)",
        _claim_7("names"),
        "how many published person-names there are, in claim 7's row",
    ),
    Figure(
        "Makefile",
        r"plants\s+(?P<n>[\d,]+)\s+person-names",
        _claim_7("attacks"),
        "how many attacks `claim-7`'s comment says it plants",
    ),
    Figure(
        "Makefile",
        r"person-names\s+on\s+(?P<n>[\d,]+)\s+types",
        _claim_7("types"),
        "how many decision-path types `claim-7`'s comment says it plants them on",
    ),
    Figure(
        "evals/oversight/README.md",
        r"on\s+every\s+one\s+of\s+the\s+(?P<n>[a-z-]+)\s+types",
        _claim_7("types"),
        "how many types the eval's README says are attacked",
    ),
    Figure(
        "evals/oversight/README.md",
        r"\*\*(?P<n>[\d,]+)\s+attacks\*\*",
        _claim_7("attacks"),
        "how many attacks the eval's README says are planted",
    ),
    Figure(
        "evals/oversight/README.md",
        r"attacks\s+planted\s+(?P<n>[\d,]+)",
        _claim_7("attacks"),
        "how many attacks the eval's README's measurement block reports",
    ),
    Figure(
        "evals/oversight/README.md",
        r"refused\s+by\s+the\s+closed\s+field\s+set\s+(?P<n>[\d,]+)",
        _claim_7("attacks"),
        "how many of them the closed field set refuses, in that block",
    ),
    Figure(
        "evals/oversight/README.md",
        # Anchored on the clause **after** the number, not on the number's spelling. The
        # sentence above -- *on every one of the fifty-six types* -- shares the whole prefix,
        # and the two were told apart only by one being spelled in words and one in digits.
        # A README edit writing `57` there would have matched this pattern and compared it
        # against 18,069: red for a reason that is not a stale figure.
        r"every\s+one\s+of\s+the\s+(?P<n>[\d,]+),\s+and\s+it\s+would",
        _claim_7("attacks"),
        "how many attacks the README's argument for the structure names",
    ),
    Figure(
        "evals/oversight/README.md",
        r"the\s+(?P<n>[a-z]+)\s+explained\s+collisions\s+are\s+the\s+only",
        _claim_7("explanations"),
        "how many explained collisions the README's disclaimer names",
    ),
    Figure(
        "evals/oversight/README.md",
        r"refused\s+by\s+the\s+hand-written\s+word\s+list\s+(?P<n>[\d,]+)",
        _claim_7("word_list"),
        "how many attacks the word list refuses, in the eval's README",
    ),
    Figure(
        "evals/oversight/README.md",
        r"The\s+(?P<n>[a-z]+)\s+explained\s+collisions,\s+published",
        _claim_7("explanations"),
        "how many explained collisions the eval's README publishes",
    ),
    Figure(
        "corpus/real/MANIFEST.yaml",
        r"any\s+of\s+the\s+(?P<n>[\d,]+)\s+fields",
        _claim_7("fields"),
        "how many fields `O4` scans, as the manifest states it",
    ),
    Figure(
        "corpus/real/MANIFEST.yaml",
        r"the\s+(?P<n>[\d,]+)\s+types\s+in\s+`holdout\.core`",
        _claim_7("types"),
        "how many types carry those fields, as the manifest states it",
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


def unrun_target_failures() -> tuple[list[str], list[str]]:
    """Every target that owns marked tests must be one `ci.yml` emits.

    **The flip side of the `suite` row, and it fails in the direction that row cannot see.**
    That row asks whether the tests `make test` gives up are selected by some target; this asks
    whether that target is one CI actually invokes. A `foo:` running `pytest -m foo` that no
    workflow calls would satisfy the first and run on no push — coverage reported from something
    that never fires.

    **Both sides are derived, and neither names a target.** The left is every recipe that hands
    pytest a mark expression; the right is `ci.yml`'s own discovery pattern, read out of that
    file, plus the `-tests` and `-shard`/`-combine` entries the workflow derives from a
    `_SHARDS` variable. A list written here would pass today, pass after `silver` only if
    somebody edited it, and fail by a person forgetting.

    **The population is one today and two after `silver`, and that is said rather than hidden.**
    An assertion over a single element is barely exercised; what makes it worth writing now is
    that the second element arrives in the change that introduces it — not that one element
    proves anything. An empty left side would make it vacuously true, which is the defect this
    module exists to refuse, so an empty population raises rather than passing.
    """
    try:
        owning = mark_owning_targets()
        emitted = set(targets_ci_emits())
    except InstrumentMissingError as exc:
        return [], [f"targets CI emits: {exc}"]
    if not owning:
        return [], [
            "no target in the Makefile hands pytest a mark expression, so whether every such "
            "target runs in CI cannot be answered. That is an instrument with nothing to "
            "measure rather than a repository in which everything is covered."
        ]
    unrun = [name for name in owning if name not in emitted]
    if unrun:
        return (
            [
                f"{name} selects a pytest mark and `ci.yml` emits no entry for it, so the tests "
                "it owns run on no push while the suite counts them as covered"
                for name in unrun
            ],
            [],
        )
    return [], []


def targets_ci_emits() -> list[str]:
    """What `discover` would put in the matrix, derived from `ci.yml` rather than from a list.

    The base targets are its own pattern applied to the Makefile; the rest is the derivation
    the workflow declares beside them — `<T>_SHARDS` above one becomes `-shard` and `-combine`,
    and a `<target>-tests` recipe becomes its own entry. **Re-implemented here rather than read
    off the workflow's output**, because a second enumeration that consumed the first would be
    one enumeration wearing two names.
    """
    match = DISCOVER_PATTERN.search(_workflow())
    if match is None:
        raise InstrumentMissingError(
            "the discovery grep is not in ci.yml in the shape this module reads it, so what CI "
            "would emit cannot be computed. Nothing is reported rather than a shorter list."
        )
    pattern = match.group("pattern").replace("^(", "^(?:")
    makefile = _makefile()
    emitted: list[str] = []
    for target in re.findall(pattern, makefile, re.MULTILINE):
        name = target.rstrip(":")
        variable = name.upper().replace("-", "_") + "_SHARDS"
        shards = re.search(rf"^{variable}\s*:=\s*(?P<n>\d+)", makefile, re.MULTILINE)
        count = int(shards.group("n")) if shards else 1
        if count > 1:
            emitted += [f"{name}-shard", f"{name}-combine"]
        else:
            emitted.append(name)
        if re.search(rf"^{re.escape(name)}-tests:", makefile, re.MULTILINE):
            emitted.append(f"{name}-tests")
    return emitted


#: The sub-block of the layout section that names directories on purpose before they exist.
#: Isolated by its own declared heading rather than by guessing which names are aspirational —
#: `make language` excludes paths the same way, by a written reason rather than by a rule that
#: has to be inferred.
LAYOUT_DECLARED_FUTURE = re.compile(
    r"^\*\*Declared and not yet built.*?$(?P<body>.*)", re.MULTILINE | re.DOTALL
)

#: A `name/` at the start of a line in the layout block, or indented under a parent.
LAYOUT_ENTRY = re.compile(r"^(?P<indent>\s*)(?P<name>[A-Za-z_.][\w./-]*)/", re.MULTILINE)


def layout_fabrications() -> tuple[list[str], list[str]]:
    """Every directory the layout names must exist, outside the declared-future block.

    **The other direction, and the review missed it for the same reason a one-sided gate
    would.** `docs/reviews/phase-1.md` §3a asked *is everything real listed* and never asked
    *is everything listed real* — so a section whose defects were five omissions and three
    fabrications was reported as five omissions. The coverage row above catches the first kind;
    nothing catches the second, because a name matching no directory is never iterated over and
    contributes to neither side of the comparison.

    **Over-coverage in a map is not over-coverage.** The one-sided rule is about a *tool*
    examining more than exists, which is a tool doing more than it was asked. A map naming a
    directory that does not exist sends its reader looking for something that is not there,
    which is worse than an omission rather than harmless.
    """
    text = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    block = LAYOUT_BLOCK.search(text)
    if block is None:
        return [], [
            "layout: CLAUDE.md has no `## Repository layout` section in the shape this module "
            "reads it, so what the map names cannot be checked."
        ]
    body = block.group("body")
    future = LAYOUT_DECLARED_FUTURE.search(body)
    present = body[: future.start()] if future else body

    fabricated: list[str] = []
    parent = ""
    for entry in LAYOUT_ENTRY.finditer(present):
        name = entry.group("name")
        # An indented line names a child of the last unindented one — `evals/` then
        # `gate_proof/` means `evals/gate_proof`. Resolved against that parent rather than by
        # leaf name anywhere in the tree, which would accept a real directory in the wrong place.
        if entry.group("indent"):
            candidate = f"{parent.rstrip('/')}/{name}" if parent else name
        else:
            candidate = name
            parent = name
        if not (REPO_ROOT / candidate).is_dir():
            fabricated.append(candidate)
    if not fabricated:
        return [], []
    return (
        [
            f"the layout names {name!r} and no such directory exists. Either build it, or move "
            "it under 'Declared and not yet built' where a name without a directory is the "
            "point rather than a mistake."
            for name in sorted(set(fabricated))
        ],
        [],
    )


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
    unrun, unrun_missing = unrun_target_failures()
    fabricated, fabricated_missing = layout_fabrications()
    invented, invented_missing = skills_claimed_that_are_not_there()
    prose, prose_missing = prose_failures()
    missing = [
        *missing,
        *floor_missing,
        *unrun_missing,
        *fabricated_missing,
        *invented_missing,
        *prose_missing,
    ]
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
    if invented:
        print(
            f"FAIL    the skills table claims {len(invented)} skill(s) that are not there", file=out
        )
        for line in invented:
            print(f"        {line}", file=out)
        print("", file=out)
    if fabricated:
        print(
            f"FAIL    the layout names {len(fabricated)} directory(ies) that do not exist", file=out
        )
        for line in fabricated:
            print(f"        {line}", file=out)
        print(
            "        A map is wrong in two directions. Omitting what exists makes a reader "
            "miss something;",
            file=out,
        )
        print("        naming what does not sends them looking for it.", file=out)
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
    if missing or floors or unrun or fabricated or invented or prose:
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
