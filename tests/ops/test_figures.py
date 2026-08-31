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

    monkeypatch.setattr(figures, "_makefile", lambda: makefile)
    monkeypatch.setattr(figures, "_workflow", lambda: narrowed)

    assert figures.claim_targets_that_exist() == 7
    assert figures.claim_targets_discover_finds() == 6

    code, output = _run()
    assert code == 1
    assert "discover" in output
    assert "never looked at" in output


def test_the_widened_regex_sees_the_eighth_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    """And the fix, driven the same way: the same Makefile, against `ci.yml` as it now is."""
    makefile = (figures.REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    makefile += "\nclaim-8:  ## a claim that exists\n\t@true\n"
    monkeypatch.setattr(figures, "_makefile", lambda: makefile)

    assert figures.claim_targets_that_exist() == 7
    assert figures.claim_targets_discover_finds() == 7


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
