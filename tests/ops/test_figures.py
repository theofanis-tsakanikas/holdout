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
