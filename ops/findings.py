"""`make findings` — an open finding has to anchor to a line that still exists.

`docs/FINDINGS.md` is the registry; this is the gate behind it. **A representation is not the
thing, and this module produces one**: it reports on the entries somebody wrote down, never on
the findings somebody had. That limit is first because it is the one a green run hides.

Why the registry exists at all
------------------------------
Every mechanism in this repository was aimed at a **claim**, a **gate** or a **deferral**. An
open review finding is none of the three, so it had nowhere to fall out of, and two of them
fell:

* the legal half of oversight level 2's third blocking finding against claim 1, recorded
  2026-08-27 and simply absent four days later. Not a deferral, so `make expiry` had nothing to
  read; not in `CLAUDE.md`, so the phase-1 integration session had nothing to check against;
* `docs/reviews/phase-1.md` §4, dropped by that review's own closing table — the one that
  assigns every other section to a branch.

What is refused, and what is only reported
------------------------------------------
**Refused (red):**

* a finding with **no site** — a finding whose consequence is recorded nowhere, which is exactly
  what the legal one was;
* a site whose fragment does **not occur exactly once** in the file it names. Zero means the line
  moved or was fixed and nobody said which; two means the anchor proves nothing about which line
  was meant. This is `ledger.every-anchor-is-aimed-at-one-place` over a new population, and that
  check earns the borrowing: it is what refused a hand-applied mutation 16 during
  `ops/claims-are-required`;
* a finding with **no disposition line at all** — `none — <reason>` is a disposition; saying
  nothing is not;
* a `*Closed:*` with no transition after the date. Closure is a transition, never a verdict.

**Reported, not refused:**

* **adrift** — a finding whose disposition is `none`. A finding nobody has scoped yet is a real
  state, and refusing it would teach people not to file;
* **concurred** — see below. It is counted among the open.

`concurred` is not `closed`
---------------------------
Two agents agreeing is two representations agreeing, which buys nothing about truth. On
2026-08-31 the reviewing session removed the second finding here from the author's list because
the two sessions concurred, and that is the mechanism by which the first one was lost — not a
decision to drop it, but two parties who held it agreeing it was handled. So `concurred` is a
state this module can represent, prints in its own count, and **counts as open**. If the two
heaviest users of a register could retire an entry by agreeing, it would measure their agreement
rather than the repository.

The standing limit
------------------
An anchor proves a line exists and still reads as expected. It cannot prove it is the **right**
line. A true but irrelevant anchor is a green that means nothing, and nothing here can catch
that — the same limit as a mutation planted against the detector, which this repository closed by
putting the detector out of reach rather than by testing the choice.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TextIO

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY = REPO_ROOT / "docs" / "FINDINGS.md"

#: An entry header, in the shape `docs/DECISIONS.md`'s deferrals already use, with the same
#: tolerance for a header that wraps at 100 columns. `ops/expiry.py` carries a comment about
#: exactly this wrap; a regex that required one line missed ten of thirty-five headers there and
#: reported as though it had read them all, which is the defect this whole file is about.
_ENTRY = re.compile(
    r"^\*\*(?P<title>[^\n]+?)\*\*[ \t]*(?:\n[ \t]*)?"
    r"·[ \t]*(?:\n[ \t]*)?found[ \t]*(?:\n[ \t]*)?"
    r"(?P<found>\d{4}-\d{2}-\d{2})",
    re.MULTILINE,
)
#: Counted independently of the headers, for the reason `make expiry` counts its markers: the
#: dangerous drift is the partial one, where some entries stop matching and the rest still do.
_MARKER = re.compile(r"·[ \t]*(?:\n[ \t]*)?found[ \t]*(?:\n[ \t]*)?\d{4}-\d{2}-\d{2}")
_SITE = re.compile(
    r"^\*Site:\*[ \t]*`(?P<path>[^`]+)`[ \t]*::[ \t]*`(?P<fragment>.+)`[ \t]*$", re.MULTILINE
)
_DISPOSITION = re.compile(r"^\*Disposition:\*[ \t]*(?P<what>.+)$", re.MULTILINE)
_STATUS = re.compile(r"^\*Status:\*[ \t]*(?P<what>open|concurred)[ \t]*$", re.MULTILINE)
_CLOSED = re.compile(
    r"^\*Closed:\*[ \t]*(?P<date>\d{4}-\d{2}-\d{2})[ \t]*(?:—|--)[ \t]*(?P<transition>\S.*)$",
    re.MULTILINE,
)
_CLOSED_LOOSE = re.compile(r"^\*Closed:\*", re.MULTILINE)
_SECTION = re.compile(r"^##[ \t]+(?P<name>Open|Closed)[ \t]*$", re.MULTILINE)


class RegistryError(Exception):
    """The registry itself cannot be read as a registry."""


@dataclass(frozen=True, slots=True)
class Site:
    path: str
    fragment: str


@dataclass(frozen=True)
class Finding:
    title: str
    found: date
    sites: tuple[Site, ...]
    disposition: str | None
    closed: date | None
    closed_transition: str | None
    concurred: bool

    @property
    def is_open(self) -> bool:
        return self.closed is None

    @property
    def is_adrift(self) -> bool:
        """No branch, no task, no reason worth the name — nobody has scoped it."""
        return self.disposition is not None and self.disposition.strip().lower().startswith("none")

    def age_in_days(self, as_of: date) -> int:
        return (as_of - self.found).days


def _body(text: str) -> str:
    first = _SECTION.search(text)
    if first is None:
        raise RegistryError(
            "no '## Open' section in the registry. A register with nothing to read is green for "
            "the wrong reason, which is the shape it exists to refuse."
        )
    return text[first.start() :]


def parse(text: str) -> list[Finding]:
    body = _body(text)
    matches = list(_ENTRY.finditer(body))
    markers = len(_MARKER.findall(body))
    if markers != len(matches):
        raise RegistryError(
            f"{markers} finding marker(s) and {len(matches)} header(s) read. One has stopped "
            "being a header this module recognises — most likely it lost its bold — and the "
            "registry would have been silently under-reported. A header is "
            "`**title** · found YYYY-MM-DD`."
        )
    if not matches:
        raise RegistryError(
            "the registry holds no finding this module can read. Either it is genuinely empty — "
            "in which case say so where somebody reads it — or a header changed shape and is "
            "being skipped."
        )
    findings: list[Finding] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        entry = body[match.end() : end]
        title = match.group("title")
        closed = _CLOSED.search(entry)
        loose = _CLOSED_LOOSE.search(entry)
        if loose is not None and closed is None:
            raise RegistryError(
                f"{title}: the *Closed:* line has no date and transition. Closure is a "
                "transition, never a verdict — `*Closed:* YYYY-MM-DD — what happened`."
            )
        status = _STATUS.search(entry)
        try:
            findings.append(
                Finding(
                    title=title,
                    found=date.fromisoformat(match.group("found")),
                    sites=tuple(
                        Site(path=m.group("path"), fragment=m.group("fragment"))
                        for m in _SITE.finditer(entry)
                    ),
                    disposition=(
                        d.group("what").strip() if (d := _DISPOSITION.search(entry)) else None
                    ),
                    closed=date.fromisoformat(closed.group("date")) if closed else None,
                    closed_transition=closed.group("transition").strip() if closed else None,
                    concurred=bool(status and status.group("what") == "concurred"),
                )
            )
        except ValueError as error:
            raise RegistryError(f"{title}: {error}") from error
    return findings


def anchor_failures(findings: Sequence[Finding], root: Path | None = None) -> list[str]:
    """Every site whose fragment no longer occurs exactly once in the file it names."""
    base = root or REPO_ROOT
    reasons: list[str] = []
    for finding in findings:
        if not finding.is_open:
            continue
        for site in finding.sites:
            path = base / site.path
            if not path.is_file():
                reasons.append(
                    f"ADRIFT     {finding.title}\n"
                    f"           {site.path} does not exist. The finding names a consequence "
                    "in a file that is gone."
                )
                continue
            occurrences = path.read_text(encoding="utf-8").count(site.fragment)
            if occurrences == 1:
                continue
            if occurrences == 0:
                reasons.append(
                    f"MOVED      {finding.title}\n"
                    f"           {site.path} no longer contains its anchor. Either the finding "
                    "was fixed and\n"
                    "           nothing said so, or the anchor is stale — and only a person can "
                    "say which."
                )
            else:
                reasons.append(
                    f"AMBIGUOUS  {finding.title}\n"
                    f"           the anchor occurs {occurrences} times in {site.path}, so it "
                    "proves nothing\n"
                    "           about which line was meant."
                )
    return reasons


def failures(findings: Sequence[Finding], root: Path | None = None) -> list[str]:
    reasons: list[str] = []
    for finding in findings:
        if not finding.is_open:
            continue
        if not finding.sites:
            reasons.append(
                f"UNANCHORED {finding.title}\n"
                "           names no *Site:*. A finding whose consequence is recorded nowhere "
                "is the\n"
                "           thing this registry exists to refuse, not an entry it accepts."
            )
        if finding.disposition is None:
            reasons.append(
                f"UNSCOPED   {finding.title}\n"
                "           carries no *Disposition:*. `none — <reason>` is a disposition; "
                "saying\n"
                "           nothing is not."
            )
    return [*reasons, *anchor_failures(findings, root)]


def report(findings: Sequence[Finding], as_of: date, out: TextIO) -> None:
    live = [f for f in findings if f.is_open]
    closed = [f for f in findings if not f.is_open]
    adrift = [f for f in live if f.is_adrift]
    concurred = [f for f in live if f.concurred]
    sites = sum(len(f.sites) for f in live)

    print(f"findings  as of {as_of.isoformat()}", file=out)
    print("", file=out)
    print(f"  {len(findings)} finding(s): {len(live)} open, {len(closed)} closed", file=out)
    print(f"  anchored to {sites} line(s) that must still say what the finding says", file=out)
    print(
        f"  adrift  {len(adrift)} of {len(live)} open — no branch, no task, a written reason",
        file=out,
    )
    print(f"  concurred but not closed  {len(concurred)} of {len(live)}", file=out)
    print(
        "        Two agents agreeing is two representations agreeing. It is a state this", file=out
    )
    print("        registry carries and counts as OPEN, never as closed.", file=out)
    print("", file=out)
    for finding in sorted(findings, key=lambda f: f.found):
        if finding.closed is not None:
            marker = "closed"
        elif finding.concurred:
            marker = "concurred"
        elif finding.is_adrift:
            marker = "adrift"
        else:
            marker = "open"
        age = f"{finding.age_in_days(as_of)}d"
        print(
            f"  {finding.found.isoformat()}  {marker:>9}  {age:>5}  {finding.title[:64]}", file=out
        )
    print("", file=out)


def check(
    registry: Path | None = None, as_of: date | None = None, out: TextIO | None = None
) -> int:
    stream = out if out is not None else sys.stdout
    path = registry or REGISTRY
    today = as_of or datetime.now(UTC).date()
    findings = parse(path.read_text(encoding="utf-8"))
    report(findings, today, stream)
    reasons = failures(findings, path.parent.parent if registry else None)
    if reasons:
        stream.write("RED     a finding stopped anchoring to what it named\n\n")
        for reason in reasons:
            stream.write(reason + "\n\n")
        return 1
    stream.write(
        "OK      every open finding anchors to a line that still says what it says\n"
        "        An anchor proves a line exists and reads as expected. It cannot prove it is\n"
        "        the right line, and nothing here can — that limit is declared, not closed.\n"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ops.findings",
        description="Refuse an open finding that no longer anchors to what it named.",
    )
    parser.add_argument("--registry", default=None)
    args = parser.parse_args(argv)
    return check(Path(args.registry) if args.registry else None)


if __name__ == "__main__":
    raise SystemExit(main())
