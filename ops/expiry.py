"""Doctrine rule 6 — *exceptions expire* — as a Makefile target rather than a paragraph.

`docs/DECISIONS.md` carries a **Deliberately deferred** section, and its own opening sentence
is the rule this module enforces: *"Each entry says what would unlock it. An item with no
unlock condition is not deferred, it is forgotten."* Until now nothing checked that. A
deferral could lose its unlock condition in an edit, or carry a date that came and went, and
the repository would stay green — which is the exact shape of an exception that never expires.

Two things are checked, and they are not the same thing:

**Every entry declares how it ends.** Either an `*Unlock condition:*` — some state of the
world that would make the deferral unnecessary — or an `*Expires:* YYYY-MM-DD`. An entry with
neither is refused, by the file's own sentence.

**A date that has passed goes red.** On expiry the finding returns and CI goes red again, and
it goes red on a day nobody touched the repository. That is the point of it: the alternative
is a deferral that quietly outlives the reason it was taken.

**A header that stopped being read goes red too**, by two independent counts — because the
dangerous drift is the partial one, where eleven entries stop matching, two still do, and the
target reports two deferrals and stays green. What it cannot notice is an entry **deleted
outright**: there is nothing left to compare against. Deletion is caught by the pull-request
diff, which is where a deletion should be argued anyway, and this target does not pretend
otherwise.

**The standing limit, stated rather than papered over.** An unlock *condition* is prose — "the
phase-1 integration session", "phase 2's gold layer" — and no checker can evaluate it. So a
condition-only deferral is checked for existence and never for truth, and it cannot expire.
What this module can do about that, it does: it prints the age of every deferral in days, so
one that has quietly outlived its reason is a number on the terminal rather than a thing
somebody has to remember. Turning an aged deferral into a red build is a judgment about how
long is too long, and that judgment belongs to the integration session, not to a regex.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TextIO

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY = REPO_ROOT / "docs" / "DECISIONS.md"

SECTION = "Deliberately deferred"

#: An entry header. The whitespace tolerance is not decoration: two of the entries in the
#: real registry wrap between the title, the middle dot and the date, and a checker that
#: silently skipped them would under-report the registry rather than fail.
_ENTRY = re.compile(
    r"^\*\*(?P<title>[^\n]+?)\*\*[ \t]*(?:\n[ \t]*)?"
    r"·[ \t]*(?:\n[ \t]*)?deferred[ \t]*(?:\n[ \t]*)?"
    r"(?P<deferred>\d{4}-\d{2}-\d{2})",
    re.MULTILINE,
)
_UNLOCK = re.compile(r"\*Unlock condition:\*", re.IGNORECASE)
#: The same newline tolerance as `_ENTRY`, and for the same reason: this file wraps at 100
#: columns and a wrapped `*Expires:*` read as "no date" would report an expired deferral green.
_EXPIRES = re.compile(r"\*Expires:\*[ \t]*(?:\n[ \t]*)?(?P<date>\d{4}-\d{2}-\d{2})", re.IGNORECASE)
#: Every deferral header carries this, whatever else it is wrapped in. Counting it is what
#: catches a header that dropped its bold — `### Title · deferred …`, `- **Title** · deferred …`
#: — which the bold-line scan below cannot see and which would otherwise shrink the registry
#: silently.
_MARKER = re.compile(r"·[ \t]*(?:\n[ \t]*)?deferred[ \t]*(?:\n[ \t]*)?\d{4}-\d{2}-\d{2}")
_SECTION = re.compile(rf"^##[ \t]+{re.escape(SECTION)}[ \t]*$", re.MULTILINE)
_NEXT_SECTION = re.compile(r"^##[ \t]", re.MULTILINE)


class RegistryError(Exception):
    """The registry itself cannot be read as a registry."""


@dataclass(frozen=True)
class Deferral:
    """One entry in the **Deliberately deferred** section."""

    title: str
    deferred: date
    expires: date | None
    has_unlock: bool

    @property
    def declares_how_it_ends(self) -> bool:
        return self.has_unlock or self.expires is not None

    def is_expired(self, as_of: date) -> bool:
        """On the date, not the day after. An exception that lasts one day longer than it
        declared is an exception nobody declared."""
        return self.expires is not None and self.expires <= as_of

    def age_in_days(self, as_of: date) -> int:
        return (as_of - self.deferred).days


def _section_body(text: str) -> str:
    heading = _SECTION.search(text)
    if heading is None:
        raise RegistryError(
            f"no '## {SECTION}' section. The registry this target audits does not exist, "
            "and a target with nothing to audit is green for the wrong reason."
        )
    rest = text[heading.end() :]
    following = _NEXT_SECTION.search(rest)
    return rest[: following.start()] if following else rest


def _header_offsets(body: str) -> list[tuple[int, str]]:
    """Every line that *looks like* an entry header: bold, at column 0, after a blank line.

    Wrapped prose puts bold at the start of a line too — "What is incomplete is\n**doctrine
    rule 1**." is one of the real entries — so the blank line before it is what separates a
    header from a continuation.
    """
    candidates: list[tuple[int, str]] = []
    offset = 0
    previous_blank = True
    for line in body.splitlines(keepends=True):
        if previous_blank and line.startswith("**"):
            candidates.append((offset, line.strip()))
        previous_blank = not line.strip()
        offset += len(line)
    return candidates


def parse(text: str) -> list[Deferral]:
    body = _section_body(text)
    matches = list(_ENTRY.finditer(body))
    if not matches:
        raise RegistryError(
            f"'## {SECTION}' contains no entry this target can read. Either the section is "
            "empty — in which case say so and delete it — or an entry header has changed "
            "shape and is being skipped silently, which is worse."
        )
    # A *partial* drift is the dangerous one: eleven entries stop matching, two still do, and
    # the target reports two deferrals and stays green while the registry silently shrinks.
    # Two independent counts, because either alone has a blind spot. The bold-line scan
    # catches a header whose `· deferred` changed shape; the marker count catches a header
    # that dropped its bold, which the bold-line scan cannot see at all.
    read = {match.start() for match in matches}
    skipped = [line for offset, line in _header_offsets(body) if offset not in read]
    if skipped:
        raise RegistryError(
            "these look like entry headers and were not read as entries, so the registry "
            "would have been silently under-reported:\n  "
            + "\n  ".join(skipped)
            + f"\n({len(matches)} of {len(matches) + len(skipped)} were read.) "
            "An entry header is `**title** · deferred YYYY-MM-DD`."
        )
    markers = len(_MARKER.findall(body))
    if markers != len(matches):
        raise RegistryError(
            f"{markers} deferral marker(s) in the section and {len(matches)} entry header(s) "
            "read. One of them has stopped being a header this target recognises — most "
            "likely it lost its bold — and the registry would have been silently "
            "under-reported. An entry header is `**title** · deferred YYYY-MM-DD`."
        )
    deferrals: list[Deferral] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        entry = body[match.end() : end]
        expires = _EXPIRES.search(entry)
        title = match.group("title")
        try:
            deferrals.append(
                Deferral(
                    title=title,
                    deferred=date.fromisoformat(match.group("deferred")),
                    expires=date.fromisoformat(expires.group("date")) if expires else None,
                    has_unlock=bool(_UNLOCK.search(entry)),
                )
            )
        except ValueError as error:
            # `2026-13-45` matches the digit pattern and is not a date. Raised as a registry
            # error so it comes out as the target's own RED line rather than a traceback —
            # `make expiry` is a named CI step so that a failure is legible as itself.
            raise RegistryError(f"{title}: {error}") from error
    return deferrals


def failures(deferrals: list[Deferral], as_of: date) -> list[str]:
    """Every reason this target should be red, in the registry's own words."""
    reasons: list[str] = []
    for item in deferrals:
        if not item.declares_how_it_ends:
            reasons.append(
                f"FORGOTTEN  {item.title}\n"
                "           carries neither an *Unlock condition:* nor an *Expires:* date. "
                "DECISIONS.md:\n"
                '           "An item with no unlock condition is not deferred, it is '
                'forgotten."'
            )
        elif item.is_expired(as_of):
            assert item.expires is not None  # narrowed by is_expired, for mypy
            overdue = (as_of - item.expires).days
            reasons.append(
                f"EXPIRED    {item.title}\n"
                f"           expired {item.expires.isoformat()}, {overdue} day(s) ago. "
                "Doctrine rule 6:\n"
                '           "Exceptions expire. On expiry the finding returns and CI goes '
                'red again."'
            )
    return reasons


def report(deferrals: list[Deferral], as_of: date, out: TextIO) -> None:
    write = out.write
    dated = [d for d in deferrals if d.expires is not None]
    conditional = [d for d in deferrals if d.expires is None]
    write(f"expiry  as of {as_of.isoformat()}\n\n")
    write(f"  {len(deferrals)} deferred item(s): {len(dated)} carry a date, ")
    write(f"{len(conditional)} carry an unlock condition only\n")
    if dated:
        soonest = min(d.expires for d in dated if d.expires is not None)
        write(f"  next expiry {soonest.isoformat()}\n")
    if conditional:
        oldest = max(conditional, key=lambda d: d.age_in_days(as_of))
        write(f"  oldest condition-only deferral is {oldest.age_in_days(as_of)} day(s) old:\n")
        write(f"    {oldest.title}\n")
    write("\n")
    for item in sorted(deferrals, key=lambda d: d.deferred):
        marker = item.expires.isoformat() if item.expires else "condition"
        write(f"  {item.deferred.isoformat()}  {marker:>10}  {item.title}\n")
    write("\n")


def check(registry: Path, as_of: date, out: TextIO | None = None) -> int:
    stream = out if out is not None else sys.stdout
    deferrals = parse(registry.read_text(encoding="utf-8"))
    report(deferrals, as_of, stream)
    reasons = failures(deferrals, as_of)
    if reasons:
        stream.write("RED     doctrine rule 6\n\n")
        for reason in reasons:
            stream.write(reason + "\n\n")
        return 1
    stream.write(
        "OK      every deferral declares how it ends, and none has expired\n"
        "        A condition is prose and is never evaluated here — only its presence is.\n"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ops.expiry",
        description="Refuse a deferral that has expired, or that never said how it ends.",
    )
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=None,
        help="the date to judge against; defaults to today (UTC)",
    )
    args = parser.parse_args(argv)
    as_of = args.as_of or datetime.now(tz=UTC).date()
    try:
        return check(args.registry, as_of)
    except RegistryError as error:
        sys.stdout.write(f"RED     {args.registry}: {error}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
