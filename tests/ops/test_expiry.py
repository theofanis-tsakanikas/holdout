"""`make expiry` goes red on a planted expired deferral, and on one that never said how it ends.

Doctrine rule 6 — *exceptions expire; on expiry the finding returns and CI goes red again* —
was enforced nowhere before this. The target that enforces it had the problem every new gate
has: when it was written, not one deferral in the registry carried a date, so the target was
green and would have stayed green if its arithmetic were nonsense. These tests are what arm
it, in the same way `gate-proof`'s mutations arm claim 1's checks: a planted break, refused by
the check named in advance. Since 2026-08-28 one real entry carries a date as well, which is
why the planted dates below are **computed from the registry** rather than written out: a
literal date is a second opinion about what the registry contains, and the first version of
these tests went red the day the registry gained its first real expiry.

Every negative case starts from the **real** `docs/DECISIONS.md` and breaks exactly one thing
in a copy of it, which is the rule `tests/conftest.py` already applies to the contracts. A
hand-built minimal registry would keep passing after the real file's shape moved on — which is
the failure mode a test suite is supposed to catch rather than exhibit.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
from ops.expiry import REGISTRY, RegistryError, check, parse

TODAY = date(2026, 8, 27)


def _planted(entry: str, tmp_path: Path) -> Path:
    """The real registry with one extra entry at the end of its deferred section."""
    text = REGISTRY.read_text(encoding="utf-8")
    copy = tmp_path / "DECISIONS.md"
    copy.write_text(text.rstrip("\n") + "\n\n" + entry.strip("\n") + "\n", encoding="utf-8")
    return copy


def _run(registry: Path, as_of: date, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = check(registry, as_of)
    return code, capsys.readouterr().out


# ------------------------------------------------------------------ the registry as it stands


def test_the_real_registry_is_green_today(capsys: pytest.CaptureFixture[str]) -> None:
    code, out = _run(REGISTRY, TODAY, capsys)
    assert code == 0, out


def test_the_real_registry_has_deferrals_to_police() -> None:
    """A target over an empty registry is a target that has never been tested."""
    assert len(parse(REGISTRY.read_text(encoding="utf-8"))) >= 10


def test_every_real_deferral_declares_how_it_ends() -> None:
    forgotten = [
        d.title for d in parse(REGISTRY.read_text(encoding="utf-8")) if not d.declares_how_it_ends
    ]
    assert not forgotten, forgotten


def test_the_wrapped_headers_are_read_rather_than_skipped() -> None:
    """Two real entries wrap between the title, the middle dot and the date.

    A checker that skipped them would under-report the registry and stay green, which is
    exactly the silent failure this target exists to remove.
    """
    titles = [d.title for d in parse(REGISTRY.read_text(encoding="utf-8"))]
    assert any("2021 and 2022 margin-cap windows" in t for t in titles)
    assert any("regulated basket still names three categories" in t for t in titles)


# --------------------------------------------------------------------------- the planted breaks

EXPIRED = """
**A planted deferral whose date has come and gone** · deferred 2026-01-01
Planted by `tests/ops/test_expiry.py`. It exists only to prove the target refuses it.
*Expires:* 2026-08-20
"""

FORGOTTEN = """
**A planted deferral that never says how it ends** · deferred 2026-01-01
Planted by `tests/ops/test_expiry.py`. It carries neither an unlock condition nor a date, so
by DECISIONS.md's own opening sentence it is not deferred — it is forgotten.
"""


#: A date that is still in the future on `TODAY` and **earlier than every real expiry**, so the
#: planted entry is the one the target reports as next and the one whose day-of decides the
#: verdict. Derived, because a literal would silently stop being the earliest.
def _binds_before_every_real_expiry() -> date:
    real = [d.expires for d in parse(REGISTRY.read_text(encoding="utf-8")) if d.expires]
    ceiling = min(real) if real else date(2026, 12, 31)
    planted = ceiling - timedelta(days=30)
    assert planted > TODAY, (
        f"the registry's earliest expiry is {ceiling}, which leaves no room to plant one "
        f"between {TODAY} and it. Move TODAY, or plant against a nearer horizon."
    )
    return planted


STILL_RUNNING_ON = _binds_before_every_real_expiry()

STILL_RUNNING = f"""
**A planted deferral that has not expired yet** · deferred 2026-01-01
Planted by `tests/ops/test_expiry.py`.
*Expires:* {STILL_RUNNING_ON.isoformat()}
"""


def test_an_expired_deferral_goes_red(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out = _run(_planted(EXPIRED, tmp_path), TODAY, capsys)
    assert code == 1, out
    assert "EXPIRED" in out
    assert "A planted deferral whose date has come and gone" in out
    assert "7 day(s) ago" in out
    assert "Exceptions expire" in out


def test_a_deferral_that_never_says_how_it_ends_goes_red(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out = _run(_planted(FORGOTTEN, tmp_path), TODAY, capsys)
    assert code == 1, out
    assert "FORGOTTEN" in out
    assert "it is forgotten" in out


def test_a_deferral_that_has_not_expired_yet_is_green(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out = _run(_planted(STILL_RUNNING, tmp_path), TODAY, capsys)
    assert code == 0, out
    assert f"next expiry {STILL_RUNNING_ON.isoformat()}" in out


def test_it_expires_on_the_date_and_not_the_day_after(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An exception that lasts one day longer than it declared is an exception nobody declared."""
    registry = _planted(STILL_RUNNING, tmp_path)
    assert _run(registry, STILL_RUNNING_ON - timedelta(days=1), capsys)[0] == 0
    assert _run(registry, STILL_RUNNING_ON, capsys)[0] == 1


def test_the_age_of_a_condition_only_deferral_is_reported(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A condition is prose and can never expire. Its age is the only number available."""
    _, out = _run(REGISTRY, date(2027, 2, 27), capsys)
    assert "oldest condition-only deferral is 184 day(s) old" in out


# ------------------------------------------------------------- the registry itself, broken


def test_a_registry_with_no_deferred_section_is_refused(tmp_path: Path) -> None:
    """Deleting the section is the cheapest way to make this target green. It does not work."""
    text = REGISTRY.read_text(encoding="utf-8")
    copy = tmp_path / "DECISIONS.md"
    copy.write_text(text.split("## Deliberately deferred")[0], encoding="utf-8")
    with pytest.raises(RegistryError, match="green for the wrong reason"):
        check(copy, TODAY)


def _with_section(text: str, body: str, tmp_path: Path) -> Path:
    head = text.split("## Deliberately deferred")[0]
    copy = tmp_path / "DECISIONS.md"
    copy.write_text(head + "## Deliberately deferred\n\n" + body, encoding="utf-8")
    return copy


def test_a_section_with_nothing_in_it_is_refused(tmp_path: Path) -> None:
    """An empty section reports nothing to do, which reads exactly like nothing being wrong."""
    copy = _with_section(REGISTRY.read_text(encoding="utf-8"), "Nothing here.\n", tmp_path)
    with pytest.raises(RegistryError, match="no entry this target can read"):
        check(copy, TODAY)


def test_a_header_that_stopped_parsing_is_refused_rather_than_skipped(tmp_path: Path) -> None:
    """The dangerous drift is partial: twelve entries stop matching and one still does.

    A checker that just reported one deferral would be green, and the twelve would be gone from
    the registry without anyone deleting them. So a line that looks like a header and was not
    read as one is a red build.
    """
    text = REGISTRY.read_text(encoding="utf-8")
    section = text.split("## Deliberately deferred", 1)[1].replace("· deferred", "· held")
    copy = _with_section(text, section, tmp_path)
    with pytest.raises(RegistryError, match="silently under-reported"):
        check(copy, TODAY)


ONE_HEADER = "**Branch protection covers `main` only** · deferred 2026-08-27"


@pytest.mark.parametrize(
    "replacement",
    [
        pytest.param(
            "### Branch protection covers `main` only · deferred 2026-08-27",
            id="promoted to a heading",
        ),
        pytest.param(f"- {ONE_HEADER}", id="turned into a list item"),
        pytest.param(f"> {ONE_HEADER}", id="quoted"),
    ],
)
def test_a_header_that_lost_its_bold_is_refused_too(tmp_path: Path, replacement: str) -> None:
    """The bold-line scan cannot see these, and on its own it reported them green.

    It looks for a line starting with `**`, so any drift that also drops the bold is invisible
    to it *and* to the entry regex — the registry shrinks by one and nothing notices. The
    second count is what catches it: every deferral header carries `· deferred YYYY-MM-DD`
    whatever else it is wrapped in, so the number of those and the number of entries read must
    agree.
    """
    text = REGISTRY.read_text(encoding="utf-8")
    section = text.split("## Deliberately deferred", 1)[1].replace(ONE_HEADER, replacement, 1)
    copy = _with_section(text, section, tmp_path)
    with pytest.raises(RegistryError, match="stopped being a header"):
        check(copy, TODAY)


WRAPPED_DATE = """
**A planted deferral whose expiry date wrapped** · deferred 2026-01-01
Planted by `tests/ops/test_expiry.py`. This file wraps at 100 columns and two of its real
entry headers already wrap, so a date on the next line is not a hypothetical.
*Expires:*
2026-08-20
"""

IMPOSSIBLE_DATE = """
**A planted deferral with a date that is not a date** · deferred 2026-13-45
Planted by `tests/ops/test_expiry.py`.
*Unlock condition:* never — it exists to be refused.
"""


def test_an_expiry_date_that_wrapped_is_still_read(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Read as "no date", it would fall back on its unlock condition and report green.

    That is the failure this target exists for, arriving through the door the target's own
    entry regex already documents: this file wraps, and two real headers wrap today.
    """
    code, out = _run(_planted(WRAPPED_DATE, tmp_path), TODAY, capsys)
    assert code == 1, out
    assert "EXPIRED" in out
    assert "whose expiry date wrapped" in out


def test_a_date_that_is_not_a_date_is_refused_legibly(tmp_path: Path) -> None:
    """`2026-13-45` matches the digit pattern and is not a date.

    `make expiry` is a named CI step so that a failure is legible as itself. A traceback is
    still a red build, and it is still not legible.
    """
    with pytest.raises(RegistryError, match=r"month must be in 1\.\.12"):
        check(_planted(IMPOSSIBLE_DATE, tmp_path), TODAY)


def test_an_entry_deleted_outright_is_not_caught_and_is_not_claimed_to_be(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The honest limit, asserted rather than left for a reader to discover.

    A deleted entry leaves nothing to compare against — no marker, no header, no gap. Deletion
    is caught by the pull-request diff, which is where a deletion should be argued anyway. The
    module docstring says so; this is the test that keeps it from quietly becoming untrue in
    the other direction, by claiming a defence that does not exist.
    """
    text = REGISTRY.read_text(encoding="utf-8")
    before = len(parse(text))
    section = text.split("## Deliberately deferred", 1)[1]
    start = section.index(ONE_HEADER)
    copy = _with_section(text, section[:start] + section[start:].split("\n\n", 1)[1], tmp_path)
    code, out = _run(copy, TODAY, capsys)
    assert code == 0, out
    assert f"{before - 1} deferred item(s)" in out
