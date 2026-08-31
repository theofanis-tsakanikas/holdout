"""The register is attacked in the two shapes this project has learned to attack in.

**Removed** — the instrument cannot see: a registry with no readable section, a header that lost
its shape, a `*Closed:*` that says nothing. **Narrowed** — the instrument sees less than exists: a
site that stopped anchoring, an entry that never anchored at all.

And one shape neither of the other registers needs: **`concurred` must not read as `closed`.** Two
agents agreeing is two representations agreeing, and on 2026-08-31 that nearly retired an entry
here for the second time. If this file ever lets a concurred entry out of the open count, the
register measures the agreement of its two heaviest users rather than the repository.
"""

from __future__ import annotations

import io
from datetime import date
from pathlib import Path

import pytest
from ops.findings import REGISTRY, RegistryError, check, failures, parse

TODAY = date(2026, 8, 31)

HEADER = """# Findings

## Open

"""

ANCHORED = """**A planted finding that anchors** · found 2026-08-01
Planted by `tests/ops/test_findings.py`.
*Site:* `subject.md` :: `the line the finding is about`
*Disposition:* branch `some/branch`
*Status:* open

"""

SUBJECT = "before\nthe line the finding is about\nafter\n"


def _registry(root: Path, entries: str, subject: str = SUBJECT) -> Path:
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (root / "subject.md").write_text(subject, encoding="utf-8")
    path = docs / "FINDINGS.md"
    path.write_text(HEADER + entries, encoding="utf-8")
    return path


def _run(path: Path) -> tuple[int, str]:
    out = io.StringIO()
    code = check(path, TODAY, out)
    return code, out.getvalue()


# ------------------------------------------------------------------- it passes on a clean one


def test_a_finding_whose_anchor_still_reads_is_green(tmp_path: Path) -> None:
    code, out = _run(_registry(tmp_path, ANCHORED))
    assert code == 0, out
    assert "1 finding(s): 1 open, 0 closed" in out


# ------------------------------------------------------ narrowed: it sees less than exists


def test_a_site_whose_line_moved_is_refused(tmp_path: Path) -> None:
    """The legal finding's shape: the consequence was edited and nothing said the finding closed."""
    code, out = _run(_registry(tmp_path, ANCHORED, subject="the line was rewritten\n"))
    assert code == 1, out
    assert "MOVED" in out
    assert "only a person can say which" in out


def test_a_site_that_matches_twice_is_refused(tmp_path: Path) -> None:
    """An anchor that could mean either line proves nothing about which line was meant."""
    twice = SUBJECT + "the line the finding is about\n"
    code, out = _run(_registry(tmp_path, ANCHORED, subject=twice))
    assert code == 1, out
    assert "AMBIGUOUS" in out
    assert "occurs 2 times" in out


def test_a_finding_with_no_site_is_refused(tmp_path: Path) -> None:
    """A finding whose consequence is recorded nowhere — which the legal one was for four days."""
    entry = ANCHORED.replace("*Site:* `subject.md` :: `the line the finding is about`\n", "")
    code, out = _run(_registry(tmp_path, entry))
    assert code == 1, out
    assert "UNANCHORED" in out


def test_a_finding_with_no_disposition_is_refused(tmp_path: Path) -> None:
    """`none — <reason>` is a disposition. Saying nothing is not."""
    entry = ANCHORED.replace("*Disposition:* branch `some/branch`\n", "")
    code, out = _run(_registry(tmp_path, entry))
    assert code == 1, out
    assert "UNSCOPED" in out


def test_a_disposition_of_none_is_reported_and_not_refused(tmp_path: Path) -> None:
    """§4's shape. A finding nobody has scoped is a real state; refusing it teaches people not
    to file, and a register nobody files into is the state that lost the first finding."""
    entry = ANCHORED.replace(
        "*Disposition:* branch `some/branch`",
        "*Disposition:* none — nobody has scoped it yet",
    )
    code, out = _run(_registry(tmp_path, entry))
    assert code == 0, out
    assert "adrift  1 of 1" in out


# --------------------------------------------------- removed: the instrument cannot answer


def test_a_registry_with_no_open_section_is_refused(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    path = docs / "FINDINGS.md"
    path.write_text("# Findings\n\nnothing this module can read\n", encoding="utf-8")
    with pytest.raises(RegistryError, match="no '## Open' section"):
        _run(path)


def test_a_header_that_lost_its_shape_is_refused_rather_than_skipped(tmp_path: Path) -> None:
    """Two independent counts, for `make expiry`'s reason: the dangerous drift is the partial one.

    This is also the failure the reviewing session hit on 2026-08-31 from the other side — a
    regex that required the marker on one line read 25 of 35 headers and reported as though it
    had read them all.
    """
    entry = ANCHORED.replace(
        "**A planted finding that anchors**", "### A planted finding that anchors"
    )
    with pytest.raises(RegistryError, match="silently under-reported"):
        _run(_registry(tmp_path, entry))


def test_an_empty_registry_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="no finding this module can read"):
        _run(_registry(tmp_path, ""))


def test_a_closure_with_no_transition_is_refused(tmp_path: Path) -> None:
    """Closure is a transition, never a verdict."""
    entry = ANCHORED + "*Closed:* it is fine now\n"
    with pytest.raises(RegistryError, match="no date and transition"):
        _run(_registry(tmp_path, entry))


# ------------------------------------------- closure restates a site, it does not release it
#
# The first draft let a closed entry stop being checked. The reviewing session found the hole
# before the file landed: a finding that stops being examined the moment somebody accounts for
# it is a claim about the past that reads as a claim about the present, and a fix reverted in
# November would leave the register saying `closed` forever. That is the legal finding's own
# story — two of three parts closed, and what hid the third was that nothing re-examines a thing
# already accounted for.

CLOSED = """**A planted finding that anchors** · found 2026-08-01
Planted by `tests/ops/test_findings.py`.
*Site:* `subject.md` :: `the line the finding is about`
*Disposition:* branch `some/branch`
*Closed:* 2026-08-31 — branch some/branch landed and the gate went red to green
*Now:* `subject.md` :: `the line as it reads now`

"""

FIXED = "before\nthe line as it reads now\nafter\n"


def test_a_closed_finding_is_still_checked_on_what_replaced_the_defect(tmp_path: Path) -> None:
    code, out = _run(_registry(tmp_path, CLOSED, subject=FIXED))
    assert code == 0, out
    assert "0 open, 1 closed" in out
    assert "closed and still held  1 line(s)" in out


def test_a_reverted_fix_turns_a_closed_finding_red(tmp_path: Path) -> None:
    """The whole reason closure restates. The entry that already knows about the defect is the
    one that has to notice it coming back."""
    reverted = SUBJECT  # the defective text, restored
    code, out = _run(_registry(tmp_path, CLOSED, subject=reverted))
    assert code == 1, out
    assert "REVERTED" in out
    assert "no longer carries the text that closed it" in out


def test_a_closure_that_does_not_restate_its_site_is_refused(tmp_path: Path) -> None:
    """Closing without naming the replacement is the release this design refuses."""
    entry = CLOSED.replace("*Now:* `subject.md` :: `the line as it reads now`\n", "")
    code, out = _run(_registry(tmp_path, entry, subject=FIXED))
    assert code == 1, out
    assert "UNRESTATED" in out
    assert "it does\n" in out or "does not release" in out.replace("\n", " ")


def test_a_site_that_nothing_replaced_may_be_declared_gone(tmp_path: Path) -> None:
    """Where the defect was an absence, or the file went away, there is no replacement text —
    and inventing one would be worse than saying so."""
    entry = CLOSED.replace(
        "*Now:* `subject.md` :: `the line as it reads now`",
        "*Now:* `subject.md` :: gone — the section was deleted outright",
    )
    code, out = _run(_registry(tmp_path, entry, subject="nothing here\n"))
    assert code == 0, out
    assert "closed and still held  0 line(s)" in out


def test_a_closing_text_that_matches_twice_is_refused(tmp_path: Path) -> None:
    code, out = _run(_registry(tmp_path, CLOSED, subject=FIXED + "the line as it reads now\n"))
    assert code == 1, out
    assert "AMBIGUOUS" in out


# ------------------------------------------------ concurred is a state, and it is not closed


def test_concurred_is_counted_open(tmp_path: Path) -> None:
    """The failure this register nearly had twice, made structural.

    Two agents agreeing is two representations agreeing. If a concurred entry left the open
    count, the register would measure the agreement of its two heaviest users rather than the
    repository.
    """
    entry = ANCHORED.replace("*Status:* open", "*Status:* concurred")
    code, out = _run(_registry(tmp_path, entry))
    assert code == 0, out
    assert "1 open, 0 closed" in out
    assert "concurred but not closed  1 of 1" in out
    assert "counts as OPEN" in out


def test_concurred_cannot_be_spelled_as_closed(tmp_path: Path) -> None:
    """`*Status:* closed` is not a status this registry has. Closure needs a `*Closed:*` line
    with a date and a transition, so agreement cannot be written as closure by accident."""
    entry = ANCHORED.replace("*Status:* open", "*Status:* closed")
    code, out = _run(_registry(tmp_path, entry))
    assert code == 0, out
    assert "1 open, 0 closed" in out


# ------------------------------------------------------------ and the real registry stands


def test_the_real_registry_is_green_today() -> None:
    findings = parse(REGISTRY.read_text(encoding="utf-8"))
    assert failures(findings) == []


def test_the_two_founding_findings_were_entered_before_their_fixes() -> None:
    """`gate-proof`'s first rule, asserted as a property rather than as a count.

    *Green first — a mutation whose target was already red proves nothing.* A register entry
    filed with the answer already known is a mutation planted against something already broken.
    Both founding entries were filed **open**, dated before any branch that touches them.

    This asserted `len(findings) == 2` until 2026-08-31, and a legitimate split turned it red —
    a frozen count standing in for the property it was there to protect, which is the defect
    this repository has spent a phase on. The count is now printed by the target and asserted
    by nobody.
    """
    findings = parse(REGISTRY.read_text(encoding="utf-8"))

    # Selected by title, not by position in a date sort. `by_date[1]` identified the orphan for
    # as long as no second finding shared its date, and a finding filed on 2026-08-30 by the same
    # review broke it — which is `every-anchor-is-aimed-at-one-place` inside the test that guards
    # the register: a key that is not unique names whichever row sorted first.
    legal = next(f for f in findings if "industry median" in f.title)
    orphan = next(f for f in findings if "serves no claim" in f.title)
    assert legal.found == date(2026, 8, 27), "the legal finding predates the register"
    assert orphan.found == date(2026, 8, 30), "§4 predates it too"
    assert len(legal.sites) >= 3, "it names every site it is acted on"
    assert not legal.is_adrift, "it had a branch from the day it was filed"
    assert orphan.is_adrift, "§4 has no branch, and that is the state it is here to hold"


# Nothing above asserts a *status*, and that is deliberate.
#
# This test has now been rewritten twice by legitimate changes to the registry it watches. First
# it froze `len(findings) == 2` and a split turned it red. Then it asserted `legal.is_open` and
# the finding closed. Both were true when written and both were the same mistake: a test holding
# a **state that is supposed to move** instead of the property that must not.
#
# What must not move is that these two entries were filed open, before any branch touched them —
# `gate-proof`'s green-first rule, which is why their `found` dates are asserted and their
# statuses are not. `make findings` prints open, closed, adrift and concurred; nothing asserts
# them, because every one of those numbers is supposed to change.


def test_every_closed_finding_restates_each_of_its_sites() -> None:
    """Closure restates; it does not release. Asserted on the real registry, not only on a
    planted one, because the first closure went through this mechanism rather than around it."""
    for finding in parse(REGISTRY.read_text(encoding="utf-8")):
        if finding.is_open:
            continue
        assert finding.closed_transition, finding.title
        restated = {r.path for r in finding.restated}
        for site in finding.sites:
            assert site.path in restated, (
                f"{finding.title}: {site.path} released rather than restated"
            )


def test_every_open_finding_anchors_to_something_that_exists() -> None:
    findings = parse(REGISTRY.read_text(encoding="utf-8"))
    for finding in findings:
        if finding.is_open:
            assert finding.sites, finding.title
