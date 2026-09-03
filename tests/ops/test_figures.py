"""The fourth attack: narrow the instrument instead of removing it.

`tests/ops/test_language.py` attacks by taking the instrument away — coverage zero, the
`grep -P` shape. This file attacks by leaving it in place and making it see **less than exists**,
which is the same lie at a coverage nobody notices, because the gate still runs, still prints,
and still says the thing it always said.

Two shapes, and both are real events in this repository's record:

* **a path outside the list** — `ops/language.py` walks the tree; a filter that quietly excludes
  a directory leaves the gate green over a file it never opened;
* **a target outside the regex** — `ci.yml`'s `discover` matched `claim-[1-7]`, so a `claim-8`
  would have been invisible to it, and `claims-complete` aggregates only what `discover` emits.
  The required check would have been silent about a claim whose gate never ran.

The second is not hypothetical: it was the state of `main` until this branch. `claim-8` does not
exist yet, so the gate was not lying — it was *going to*, and the attack is what shows the
difference between those two.
"""

from __future__ import annotations

import io
import re
import subprocess
from pathlib import Path

import pytest

from ops import figures


def _run() -> tuple[int, str]:
    out = io.StringIO()
    code = figures.check(out)
    return code, out.getvalue()


# ----------------------------------------------------------- the tree as it stands is covered


def test_every_gate_examines_at_least_what_exists() -> None:
    found, missing = figures.rows()
    assert missing == []
    under = [f"{r.gate}: {r.examined} of {r.enumerated}" for r in found if not r.passed]
    assert under == []


def test_over_coverage_is_not_a_failure() -> None:
    """ruff formats Python inside Markdown, so it examines more than this enumerates.

    Asserted rather than described, because the asymmetry is the whole design: freezing either
    number would have gone red on a version bump that is not a defect.
    """
    found, _ = figures.rows()
    lint = next(row for row in found if row.gate == "lint")
    assert lint.examined > lint.enumerated
    assert lint.passed


# ------------------------------------------------------------------ narrowing, not removing


def test_a_path_outside_the_list_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """The language gate is made to skip a directory it should have walked.

    The instrument is still there and still answers. It answers about less than exists, which
    is exactly what a gate reporting *no Greek found* must not be allowed to mean.
    """
    from ops import language

    def narrowed_scan() -> int:
        """What `language.scan` would report if its walk quietly skipped one directory."""
        return sum(1 for p in language.content_files() if "evals" not in p.parts)

    narrowed = tuple(
        figures.Coverage(
            gate=entry.gate,
            population=entry.population,
            enumerate_=entry.enumerate_,
            examine=narrowed_scan if entry.gate == "language" else entry.examine,
            note=entry.note,
        )
        for entry in figures.COVERAGE
    )
    monkeypatch.setattr(figures, "COVERAGE", narrowed)

    code, output = _run()
    assert code == 1
    assert "examined less than exists" in output
    assert "language" in output


def test_a_check_source_outside_the_walk_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """`CHECK_SOURCES` is narrowed to one eval, and the ledger keeps printing three tidy counts.

    This is the shape no reviewer notices: `make gate-proof` still runs, still says
    `N armed · M declared un-armable · K unarmed`, and every one of those numbers is now about a
    fraction of the checks that exist. Only the second enumeration can tell, because the gate's
    own output looks exactly as right as it did before.
    """
    from evals.gate_proof import ledger

    monkeypatch.setattr(ledger, "CHECK_SOURCES", ("evals/guardrail",))

    code, output = _run()
    assert code == 1
    assert "examined less than exists" in output
    assert "armed-or-says-why" in output


def test_a_package_the_layout_does_not_name_is_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`core/demand/` is taken back out of the map — the exact omission the review found.

    Narrowing again, not removing: `CLAUDE.md` still has a layout section, it still reads as a
    map of the repository, and it is still wrong in the one direction that matters. Only the
    second enumeration can say so, because the section looks exactly as authoritative with the
    line missing as with it there.
    """
    claude = (figures.REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    line = "  demand/              the censoring correction — claim 4's reader and its curve\n"
    assert line in claude, "the layout no longer names core/demand/ in the shape this test edits"

    narrowed = tmp_path / "CLAUDE.md"
    narrowed.write_text(claude.replace(line, ""), encoding="utf-8")
    monkeypatch.setattr(figures, "REPO_ROOT", figures.REPO_ROOT)

    def named_from_the_narrowed_map() -> int:
        body = figures.LAYOUT_BLOCK.search(narrowed.read_text(encoding="utf-8"))
        assert body is not None
        text = body.group("body")
        return sum(
            1
            for d in figures._layout_population()
            if f"{d.relative_to(figures.REPO_ROOT).as_posix()}/" in text
            or re.search(rf"^\s+{re.escape(d.name)}/", text, re.MULTILINE)
        )

    patched = tuple(
        figures.Coverage(
            gate=entry.gate,
            population=entry.population,
            enumerate_=entry.enumerate_,
            examine=named_from_the_narrowed_map if entry.gate == "layout" else entry.examine,
            note=entry.note,
        )
        for entry in figures.COVERAGE
    )
    monkeypatch.setattr(figures, "COVERAGE", patched)

    code, output = _run()
    assert code == 1
    assert "examined less than exists" in output
    assert "layout" in output


def test_a_directory_the_layout_invents_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """The other direction, which the coverage row structurally cannot see.

    `layout_packages_named` iterates the directories that exist and counts how many the section
    names. A name matching no directory is never iterated over, so it contributes to neither
    side and the row stays green — which is how `pipelines/`, `infra/` and `experiments/` sat in
    the present-tense block while a review about that very section reported only omissions.
    """
    claude = (figures.REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    real = "tests/                 the suite the gates run\n"
    assert real in claude, "the layout no longer names tests/ in the shape this test edits"
    invented = real + "infra/                 bootstrap · foundation · sources · lakehouse\n"

    monkeypatch.setattr(
        figures,
        "layout_fabrications",
        lambda: _fabrications_of(claude.replace(real, invented)),
    )

    code, output = _run()
    assert code == 1
    assert "do not exist" in output
    assert "infra" in output


def _fabrications_of(text: str) -> tuple[list[str], list[str]]:
    """`layout_fabrications` against supplied text rather than the file on disk."""
    block = figures.LAYOUT_BLOCK.search(text)
    assert block is not None
    body = block.group("body")
    future = figures.LAYOUT_DECLARED_FUTURE.search(body)
    present = body[: future.start()] if future else body
    fabricated: list[str] = []
    parent = ""
    for entry in figures.LAYOUT_ENTRY.finditer(present):
        name = entry.group("name")
        if entry.group("indent"):
            candidate = f"{parent.rstrip('/')}/{name}" if parent else name
        else:
            candidate = name
            parent = name
        if not (figures.REPO_ROOT / candidate).is_dir():
            fabricated.append(candidate)
    return ([f"the layout names {n!r} and no such directory exists" for n in fabricated], [])


def test_the_layout_population_holds_nothing_git_ignores() -> None:
    """The population is what git tracks, so it is the same on every machine.

    The first version walked the working directory with a hand-written exclusion list and
    counted 20 on the author's laptop against 19 on a clean checkout: `notes/` is gitignored
    scratch, and it had been added to `CLAUDE.md`'s map as though it were repository content.
    `make check` was green and CI was red — which is `CLAUDE.md`'s fourth form of the rule,
    *where the number will be met on hardware that is not the author's, the measurement is taken
    there*, inside the module written to enforce exactly that.
    """
    population = figures._layout_population()
    assert population, "the population is empty, which means git could not be asked"

    relative = [d.relative_to(figures.REPO_ROOT).as_posix() for d in population]
    ignored = subprocess.run(
        ["git", "check-ignore", *relative],
        capture_output=True,
        text=True,
        cwd=figures.REPO_ROOT,
    )
    assert not ignored.stdout.strip(), (
        f"the layout population holds paths git ignores: {ignored.stdout.strip()}"
    )


def test_a_skill_the_table_does_not_mark_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """A skill exists and the table still says it is future work.

    The status column was added on 2026-08-31 because the table listed four skills where one
    existed. **Nothing enumerated the column against the directory** — so a third status going
    stale would have looked exactly like the two that did not, which is the defect the column
    was added to fix, one layer up.
    """
    claude = (figures.REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    marked = "| `integration-review` — bugs in the process, not the code | **exists** |"
    assert marked in claude, "the skills table no longer marks integration-review as existing"

    # `COVERAGE` captured the callable at import, so patching the module attribute would not
    # reach it — the row has to be rebuilt. The same shape as the layout narrowing test above.
    def stale() -> int:
        return _marked_in(claude.replace(marked, marked.replace("**exists**", "T008")))

    monkeypatch.setattr(
        figures,
        "COVERAGE",
        tuple(
            figures.Coverage(
                gate=entry.gate,
                population=entry.population,
                enumerate_=entry.enumerate_,
                examine=stale if entry.gate == "skills" else entry.examine,
                note=entry.note,
            )
            for entry in figures.COVERAGE
        ),
    )
    code, output = _run()
    assert code == 1
    assert "examined less than exists" in output
    assert "skills" in output


def test_a_skill_the_table_invents_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """The other direction, which the coverage row structurally cannot see.

    A row claiming a skill that is not there is never counted on either side — the same shape as
    the repository layout, where omitting a package and inventing one are different failures and
    only the first is under-coverage. A table naming a skill that is not there sends its reader
    looking for it.
    """
    claude = (figures.REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    absent = "| `contract-change` — restatement? new window? which consumers? which past results? | **no task** |"
    assert absent in claude, "the skills table no longer lists contract-change as having no task"

    monkeypatch.setattr(
        figures,
        "skills_claimed_that_are_not_there",
        lambda: _invented_in(claude.replace(absent, absent.replace("**no task**", "**exists**"))),
    )
    code, output = _run()
    assert code == 1
    assert "not there" in output
    assert "contract-change" in output


def _marked_in(text: str) -> int:
    return sum(
        1 for m in figures._SKILL_ROW.finditer(text) if m.group("status").strip("* ") == "exists"
    )


def _invented_in(text: str) -> tuple[list[str], list[str]]:
    present = {d.name for d in (figures.REPO_ROOT / ".claude" / "skills").iterdir() if d.is_dir()}
    invented = [
        m.group("name")
        for m in figures._SKILL_ROW.finditer(text)
        if m.group("status").strip("* ") == "exists" and m.group("name") not in present
    ]
    return (
        [
            f"the skills table says {n!r} exists and .claude/skills/{n}/ is not there"
            for n in sorted(set(invented))
        ],
        [],
    )


def test_a_target_outside_the_regex_is_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`claim-[1-7]` against a Makefile that has a `claim-8`.

    The exact state `main` was in until this branch, driven rather than argued: the workflow's
    own pattern is applied to a Makefile carrying an eighth claim, and the gate must notice that
    `discover` would emit seven of eight.
    """
    makefile = (figures.REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    makefile += "\nclaim-8:  ## a claim that exists\n\t@true\n"
    workflow = (figures.REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    narrowed = workflow.replace("claim-[0-9]+", "claim-[1-7]")
    assert narrowed != workflow, "the widened pattern is not in ci.yml"

    before = figures.claim_targets_that_exist()
    monkeypatch.setattr(figures, "_makefile", lambda: makefile)
    monkeypatch.setattr(figures, "_workflow", lambda: narrowed)

    # Derived rather than frozen: the tree gained `silver` and a written count would have gone
    # stale on a change that is not a defect — which is the rule this module enforces.
    assert figures.claim_targets_that_exist() == before + 1
    assert figures.claim_targets_discover_finds() == before

    code, output = _run()
    assert code == 1
    assert "discover" in output
    assert "never looked at" in output


def test_the_widened_regex_sees_the_eighth_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    """And the fix, driven the same way: the same Makefile, against `ci.yml` as it now is."""
    makefile = (figures.REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    makefile += "\nclaim-8:  ## a claim that exists\n\t@true\n"
    before = figures.claim_targets_that_exist()
    monkeypatch.setattr(figures, "_makefile", lambda: makefile)

    assert figures.claim_targets_that_exist() == before + 1
    assert figures.claim_targets_discover_finds() == before + 1


# ------------------------------------- a test the suite gave up and no claim target picked up


def test_a_deselected_test_that_no_claim_target_runs_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`make test` deselects the mark and every claim target stops selecting it.

    This is `claim-[1-7]` with tests as its population: seventeen of them exist, none of them
    runs on any push, and every target involved is green. The suite is *smaller* than it was,
    which is the direction that reads as an improvement.
    """
    makefile = (figures.REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    abandoned = makefile.replace("\t$(RUN) pytest -m claim_2\n", "")
    assert abandoned != makefile, "no claim target selects a mark, so there is nothing to remove"
    monkeypatch.setattr(figures, "_makefile", lambda: abandoned)

    assert figures.suite_selection() == "not claim_2 and not silver"
    assert figures.claim_selection() == "(silver)"
    assert figures.tests_the_suite_deselects() > 0
    assert figures.tests_a_claim_target_runs() == 0

    code, output = _run()
    assert code == 1
    assert "suite" in output
    assert "never looked at" in output


def test_a_claim_target_that_runs_other_tests_does_not_cover_these(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The reason the second count is an intersection rather than a second population.

    A claim target that selects *some* mark would make the two counts equal if they were taken
    apart from each other -- seventeen deselected, seventeen selected, and not the same
    seventeen. Here the claim targets select a mark no test carries, so the intersection is
    empty and the row is red while a union would have been green.
    """
    makefile = (figures.REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    # **Every** mark-owning target is pointed at a mark no test carries, not just one of them:
    # leaving the others intact would let this test pass for the wrong reason the day another
    # target's own tests happen to cover the deselected set.
    elsewhere = makefile
    for real in ("claim_2", "silver"):
        elsewhere = elsewhere.replace(
            f"$(RUN) pytest -m {real}", "$(RUN) pytest -m not_a_real_mark"
        )
    assert elsewhere != makefile
    monkeypatch.setattr(figures, "_makefile", lambda: elsewhere)

    assert figures.claim_selection() == "(not_a_real_mark)"
    assert figures.tests_a_claim_target_runs() == 0

    code, output = _run()
    assert code == 1
    assert "suite" in output


def test_a_suite_that_deselects_nothing_is_covered_by_nothing_and_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The state `main` is in: no mark, nothing given up, and the row is a true zero.

    It is here because zero is the answer this row must give when the mechanism is unused, and
    a gate that cannot tell *unused* from *broken* is the `grep -P` shape one file over.
    """
    makefile = (figures.REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    plain = makefile.replace('$(RUN) pytest -m "not claim_2 and not silver"', "$(RUN) pytest")
    assert plain != makefile
    monkeypatch.setattr(figures, "_makefile", lambda: plain)

    assert figures.suite_selection() is None
    assert figures.tests_the_suite_deselects() == 0
    assert figures.tests_a_claim_target_runs() == 0


# ------------------------------------------------------- the instrument may not answer zero


def test_a_population_that_cannot_be_enumerated_is_not_a_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Makefile with no `PYTHON_DIRS` line: the lint population is unknowable, not empty."""
    monkeypatch.setattr(figures, "_makefile", lambda: "# nothing this module can read\n")
    with pytest.raises(figures.InstrumentMissingError):
        figures.python_dirs()

    code, output = _run()
    assert code == 1
    assert "could not answer, which is not a count of zero" in output


def test_a_makefile_with_no_test_target_is_not_a_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """A tree whose suite cannot be read has an unknowable deselection, not an empty one."""
    monkeypatch.setattr(figures, "_makefile", lambda: "# nothing this module can read\n")
    with pytest.raises(figures.InstrumentMissingError):
        figures.suite_selection()


def test_a_collect_that_prints_no_count_is_not_a_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """The `grep -P` shape again, at the one gate whose population pytest itself enumerates."""
    figures._collected.cache_clear()
    monkeypatch.setattr(figures, "_tool_output", lambda _command: "unexpected output\n")
    with pytest.raises(figures.InstrumentMissingError):
        figures._collected("claim_2")
    figures._collected.cache_clear()


def test_a_tool_that_prints_no_count_is_not_a_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """The `grep -P` shape at one remove: the tool ran and said something unreadable."""
    monkeypatch.setattr(figures, "_tool_output", lambda _command: "unexpected output\n")
    with pytest.raises(figures.InstrumentMissingError):
        figures.mypy_examined()
    with pytest.raises(figures.InstrumentMissingError):
        figures.ruff_examined()


def test_a_floor_above_what_exists_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """A declared floor that no Makefile can meet fails every run, and says which number moved."""
    workflow = (figures.REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    monkeypatch.setattr(figures, "_workflow", lambda: re.sub(r"FLOOR=\d+", "FLOOR=99", workflow))

    code, output = _run()
    assert code == 1
    assert "a declared floor does not match what exists" in output


def test_the_declared_floor_matches_the_makefile_today() -> None:
    failures, missing = figures.floor_failures()
    assert missing == []
    assert failures == []


def test_a_target_that_owns_marked_tests_and_never_runs_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The flip side of the `suite` row: covered by a target CI does not invoke.

    Renaming `silver` is enough — the recipe still hands pytest a mark, so the left side keeps
    it, and `ci.yml`'s pattern no longer matches, so the right side loses it. That is the shape
    a person produces by naming a target something reasonable.
    """
    makefile = (figures.REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    monkeypatch.setattr(figures, "_makefile", lambda: makefile.replace("\nsilver:", "\nsilverish:"))

    failures, missing = figures.unrun_target_failures()
    assert missing == []
    assert failures and "silverish" in failures[0]


def test_a_left_side_with_nothing_in_it_is_not_a_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    """A subset assertion over an empty set is vacuously true, which is not an answer."""
    monkeypatch.setattr(figures, "mark_owning_targets", list)

    failures, missing = figures.unrun_target_failures()
    assert failures == []
    assert missing and "nothing to measure" in missing[0]


def test_every_target_that_owns_marked_tests_runs_in_ci_today() -> None:
    """Two of them, and the second arrived with the change that wrote this assertion."""
    assert figures.mark_owning_targets() == ["claim-2-tests", "silver"]
    failures, missing = figures.unrun_target_failures()
    assert missing == []
    assert failures == []
