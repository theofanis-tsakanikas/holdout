"""`make language` — repository content is in English, and the exceptions are declared.

`CLAUDE.md`'s first line: *all repository content in English. Conversation with the author in
Greek.* That rule was enforced nowhere until 2026-08-30, and it had already been broken:
`docs/reviews/phase-1.md` landed on `main` carrying 12,803 Greek characters, in a public
repository, written by a session that mistook "the conversation" for "the work product".

**This is not a blanket ban, and a blanket ban would be wrong.** Greek is load-bearing in three
places and translating any of them would be a defect rather than a fix:

* a **verbatim article** of a Greek instrument, quoted so that `docs/REGULATORY.md`'s rule holds
  — *a `legal_instrument` carries either a verbatim `quote` or a `note` accounting for it*. A
  translated statute is a paraphrase of law, which is the one thing doctrine rule 3 forbids;
* **published data somebody else wrote** — the 63 regulated-basket categories and the ONS item
  descriptions under `corpus/real/data/`. They are digest-checked in `corpus/real/MANIFEST.yaml`,
  so editing them fails `tests/corpus/test_manifest.py` on the way past, and rightly: the corpus
  is evidence precisely because this repository did not write it;
* **mathematical symbols** — alpha, beta and tau, which are what the estimator and the design
  engine call them everywhere else.

So the exceptions are two closed lists rather than one loose one, and every entry carries the
reason it exists. `EXCEPTED_PATHS` is for files that quote law or carry published data;
`ALLOWED` is a closed vocabulary of tokens admitted **anywhere**, which is what keeps the paths
list short: outside the five excepted paths the whole repository uses **nineteen** distinct Greek
tokens, which is a vocabulary rather than a habit. That number is live rather than dated — it is
registered in `ops/figures.py`'s prose table and `make figures` goes red when the sentence and the
list stop agreeing, which is how the nineteenth arrived: `docs/FINDINGS.md` needed a term the
vocabulary did not have, `make language` refused the file, and `make figures` then refused this
paragraph.

The instrument may not be silently absent
-----------------------------------------
**This gate exists in the shape it does because of how the violation was first mis-measured.**
The author checked for Greek with `grep -P`, which BSD grep on macOS does not have. `grep`
exited 1, `2>/dev/null` swallowed the reason, and "no matches" and "the tool is not installed"
are the same two characters on a terminal. A count of **zero** was reported from a command that
never ran the check.

That is the twelfth form of *a guard tested by its author*, and it is not a number: **the silence
of a missing instrument is indistinguishable from a pass.** So this module refuses to report
green unless it can first show that it works — `self_check` fires the detector at a sentinel it
builds from code points, requires the scan to have reached a plausible number of files, and
requires every declared exception to still be in use. Any of those failing is a **red run**, with
its own message, never a green one.

`tests/ops/test_language.py` attacks each of those three by taking the instrument away.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Greek and Coptic (U+0370-U+03FF) and Greek Extended (U+1F00-U+1FFF). The tonos and
#: dialytika marks live inside the first block, so a gazette series letter carrying one needs
#: no special case. Written as escapes rather than as literals so that this module's own
#: bytes carry no Greek and it needs no exception for itself.
GREEK_CHAR = re.compile("[\u0370-\u03ff\u1f00-\u1fff]")

#: A *run* is a maximal stretch that starts and ends on a Greek character and may carry spaces
#: and full stops in between, so `άρθρο 9ι παρ. 2` is reported as one token rather than four.
#: Digits are deliberately excluded: an article number is not part of the vocabulary.
GREEK_RUN = re.compile(
    "[\u0370-\u03ff\u1f00-\u1fff](?:[\u0370-\u03ff\u1f00-\u1fff' .]*[\u0370-\u03ff\u1f00-\u1fff])?"
)

#: Suffixes that are not text. A gzipped corpus file is repository content in every other
#: sense and carries no prose at all, so enumerating it and then failing to decode it would show
#: up in `make figures` as this gate having examined less than exists — which would be true, and
#: not a defect. Declaring it keeps the two counts honest instead of tolerating a difference.
NOT_TEXT: frozenset[str] = frozenset({".gz", ".zip", ".png", ".jpg", ".jpeg", ".pdf", ".ico"})

#: Directories and files that are not repository content: tooling caches, the virtualenv, the
#: generated world cache, the lockfile, and `notes/`, which is gitignored and never published.
NOT_CONTENT: frozenset[str] = frozenset(
    {
        ".git",
        ".venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".worlds",
        "notes",
        "uv.lock",
    }
)


@dataclass(frozen=True, slots=True)
class Allowance:
    """One declared allowance, and the reason it is one. No entry exists without a reason."""

    what: str
    kind: str
    reason: str


#: Whole files that quote law verbatim or carry data somebody else published. Anything Greek
#: inside them passes, and that is the declared limit of this gate: it is a path, so a Greek
#: paragraph hidden in one of these five would not be caught here. The pull-request diff is what
#: catches that, which is the same answer `make expiry` gives about a deleted deferral.
EXCEPTED_PATHS: tuple[Allowance, ...] = (
    Allowance(
        "docs/REGULATORY.md",
        "verbatim_law",
        "the legal chain, argued with citations. Every provision is quoted in the language the "
        "gazette published it in, because REGULATORY.md's own rule is that a legal_instrument "
        "carries a verbatim quote or a note accounting for its absence — and a translated "
        "statute is a paraphrase of law, which is what doctrine rule 3 refuses.",
    ),
    Allowance(
        "contracts/guardrails/regulated_basket.yaml",
        "verbatim_law",
        "the margin cap's effective windows quote the article each one rests on. The 2021 and "
        "2022 regimes differ in shape rather than in numbers, and the shape is only legible in "
        "the instrument's own words.",
    ),
    Allowance(
        "contracts/guardrails/prior_price.yaml",
        "verbatim_law",
        "the prior-price rule and the perishables exemption the whole fresh path rests on, "
        "quoted from ν. 2251/1994 as amended.",
    ),
    Allowance(
        "corpus/real/MANIFEST.yaml",
        "verbatim_law",
        "names each instrument and quotes the definition it supplies, so a reader can check the "
        "corpus against the source without opening the gazette.",
    ),
    Allowance(
        "corpus/real/data/",
        "published_datum",
        "what somebody else published, kept in the publisher's own spelling — the 63 "
        "regulated-basket categories and the ONS item descriptions. Digest-checked in "
        "MANIFEST.yaml, so an edit here is already a red build; the corpus is evidence because "
        "this repository did not write it.",
    ),
)

#: Tokens admitted anywhere. Closed, in the sense `contracts/vocabularies/` uses the word: adding
#: one is a change to this file with a reason beside it, not something that happens by accident.
ALLOWED: tuple[Allowance, ...] = (
    Allowance("α", "mathematical_symbol", "alpha — the declared significance level."),
    Allowance("β", "mathematical_symbol", "beta — the type II error rate behind the power target."),
    Allowance("τ", "mathematical_symbol", "tau — the treatment effect the estimator estimates."),
    Allowance(
        "ΥΑ",
        "legal_citation",
        "the abbreviation for a Greek ministerial decision, the instrument the 2026 margin cap is.",
    ),
    Allowance(
        "ΠΝΠ",
        "legal_citation",
        "the abbreviation for an act of legislative content, which is how the 2026 cap was first imposed.",
    ),
    Allowance("ΦΕΚ", "legal_citation", "the Government Gazette, where an instrument is published."),
    Allowance(
        "ΦΕΚ Α΄",
        "legal_citation",
        "gazette series A, where statutes are published. The series letter is part of the "
        "citation: the same number in series B is a different instrument.",
    ),
    Allowance(
        "ΦΕΚ Β΄",
        "legal_citation",
        "gazette series B, where ministerial decisions are published — the series the 2026 "
        "margin cap's own list of 63 categories appeared in.",
    ),
    Allowance(
        "ΠΜΚ",
        "legal_citation",
        "the abbreviation the instrument uses for the gross margin its cap is on.",
    ),
    Allowance("άρθρο", "legal_citation", "article — the unit a provision is cited by."),
    Allowance(
        "άρθρο δεύτερο", "legal_citation", "article two, written as a word in Greek statutes."
    ),
    Allowance("παρ", "legal_citation", "the abbreviation for the paragraph inside an article."),
    Allowance(
        "ι παρ",
        "legal_citation",
        "the letter that indexes article 9i of the consumer statute. Transliterating it would name a different article.",
    ),
    Allowance(
        "ν",
        "legal_citation",
        "the abbreviation for a statute, as in the citation of the 1994 consumer law.",
    ),
    Allowance(
        "ανά μονάδα",
        "quoted_term",
        "per unit — quoted in tests/contracts/test_guardrails.py because the 2022 regime's basis "
        "is this phrase and the 2021 one does not contain it. That absence is a finding oversight "
        "level 2 made, so the words are the evidence.",
    ),
    Allowance(
        "Τιμή Πώλησης",
        "quoted_term",
        "selling price — the denominator ΥΑ 21330/2026 άρθρο 4 παρ. 4 defines the capped margin over.",
    ),
    Allowance(
        "Μέσο Κόστος Πωληθέντων",
        "quoted_term",
        "average cost of goods sold — the other term of that same definition.",
    ),
    Allowance(
        "Περίοδος Αναφοράς",
        "quoted_term",
        "reference period — what \u03ac\u03c1\u03b8\u03c1\u03bf 4 \u03c0\u03b1\u03c1. 5 actually "
        "defines, as against what a finding in docs/FINDINGS.md says it defines. The whole point of "
        "that entry is which term the article names, so naming it in translation would erase the "
        "finding while appearing to record it.",
    ),
    Allowance(
        "φτιάξε το",
        "skill_trigger",
        "a Greek invocation phrase in .claude/skills/claim/SKILL.md's description. A skill is "
        "matched on what the author would type, and the author types Greek — it is addressed to "
        "the harness rather than to a reader.",
    ),
)

#: Below this many scanned files the walk has plainly not reached the repository, whatever the
#: reason. It is a floor rather than a count: the tree grows, and a number that tracked it would
#: be a second assertion needing its own measurement. Measured 2026-08-30: 300 files.
MIN_FILES_SCANNED = 60


@dataclass(frozen=True, slots=True)
class Offence:
    path: str
    line: int
    token: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}  {self.token}"


def _allowed_tokens() -> frozenset[str]:
    return frozenset(entry.what for entry in ALLOWED)


def content_files(root: Path | None = None) -> list[Path]:
    """Every file that is repository content, in a stable order."""
    base = root or REPO_ROOT
    found: list[Path] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        if any(part in NOT_CONTENT for part in path.relative_to(base).parts):
            continue
        if path.suffix.lower() in NOT_TEXT:
            continue
        found.append(path)
    return found


def is_excepted(relative: str) -> bool:
    for entry in EXCEPTED_PATHS:
        if relative == entry.what or relative.startswith(entry.what):
            return True
    return False


def offences_in(
    text: str, *, relative: str, allowed: frozenset[str] | None = None
) -> list[Offence]:
    """Greek runs in one file's text that no declared exception admits."""
    vocabulary = _allowed_tokens() if allowed is None else allowed
    found: list[Offence] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for run in GREEK_RUN.findall(line):
            token = run.strip(" .,")
            if token and token not in vocabulary:
                found.append(Offence(path=relative, line=number, token=token))
    return found


def scan(
    root: Path | None = None, *, allowed: frozenset[str] | None = None
) -> tuple[list[Offence], int, set[str]]:
    """Walk the tree once. Returns the offences, how many files were read, and the tokens used."""
    base = root or REPO_ROOT
    offences: list[Offence] = []
    used: set[str] = set()
    read = 0
    for path in content_files(base):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        read += 1
        relative = path.relative_to(base).as_posix()
        if is_excepted(relative):
            used.update(entry.what for entry in EXCEPTED_PATHS if relative.startswith(entry.what))
            continue
        for run in GREEK_RUN.findall(text):
            token = run.strip(" .,")
            if token:
                used.add(token)
        offences.extend(offences_in(text, relative=relative, allowed=allowed))
    return offences, read, used


def self_check(files_read: int, used: set[str], *, vocabulary_in_use: bool = True) -> list[str]:
    """Can this instrument still do the thing it claims? A green run must answer yes first.

    Three questions, and each of them is a way this gate could report *no Greek found* while
    having found nothing because it looked at nothing:

    1. **does the detector detect?** The sentinel is built from code points, so this module's own
       bytes carry no Greek and it needs no exception for itself. A regex edited into something
       that matches nothing fails here rather than passing everywhere.
    2. **did the walk reach the repository?** A wrong root, a filter that excludes everything, a
       permissions error swallowed in a loop — all of them produce zero offences.
    3. **is every declared exception still in use?** An exception nobody exercises is a
       pre-approval for whoever adds that token next, which is the argument claim 7's `O12`
       already makes about its explained collisions.

    The third is a statement about **this repository** and about no other tree, so
    `vocabulary_in_use` turns it off for the synthetic trees `tests/ops/test_language.py`
    builds. A scratch directory containing one file has not stopped using `docs/REGULATORY.md`;
    it never used it. Asking the question there would make the check fire on every caller that
    is not the repository, which is a gate that means something different depending on who runs
    it.
    """
    failures: list[str] = []

    # Two lowercase letters and a two-letter abbreviation, written as code points on purpose:
    # the detector's own test case must not have to be exempted from the detector.
    sentinel = "\u03b1\u03b2 \u03a5\u0391"
    if not GREEK_CHAR.search(sentinel) or not GREEK_RUN.findall(sentinel):
        failures.append(
            "the detector does not detect: it found no Greek in a sentinel that is Greek. "
            "This is a red run rather than a green one, because a silent instrument and a "
            "clean tree look identical."
        )

    if files_read < MIN_FILES_SCANNED:
        failures.append(
            f"the walk read {files_read} file(s), under the floor of {MIN_FILES_SCANNED}. "
            "Nothing was checked, so nothing may be reported clean."
        )

    if not vocabulary_in_use:
        return failures

    unused_paths = [e.what for e in EXCEPTED_PATHS if e.what not in used]
    unused_tokens = [e.what for e in ALLOWED if e.what not in used]
    for what in unused_paths + unused_tokens:
        failures.append(
            f"the declared exception {what!r} is no longer used anywhere. An unused exception "
            "is a pre-approval for whoever adds it next; remove it in the same change that "
            "removed its last use."
        )
    return failures


def report(
    offences: Sequence[Offence], failures: Sequence[str], files_read: int, out: TextIO
) -> None:
    print("language  repository content is in English; the exceptions are declared", file=out)
    print("", file=out)
    print(f"  {files_read} file(s) read", file=out)
    print(f"  {len(EXCEPTED_PATHS)} excepted path(s) · {len(ALLOWED)} allowed token(s)", file=out)
    print("", file=out)

    if failures:
        print("FAIL    the instrument cannot show that it works", file=out)
        for failure in failures:
            print(f"        {failure}", file=out)
        print("", file=out)

    if offences:
        print(f"FAIL    {len(offences)} Greek run(s) no declared exception admits", file=out)
        for offence in offences[:40]:
            print(f"        {offence}", file=out)
        if len(offences) > 40:
            print(f"        … and {len(offences) - 40} more", file=out)
        print("", file=out)
        print(
            "        CLAUDE.md: all repository content in English. Conversation with the "
            "author in Greek.",
            file=out,
        )
        print(
            "        If one of these is load-bearing — a verbatim article, a published datum, "
            "a symbol —",
            file=out,
        )
        print(
            "        declare it in ops/language.py with the reason. Otherwise translate it.",
            file=out,
        )
        return

    if not failures:
        print("OK      no Greek outside the declared exceptions", file=out)
        print("        The instrument answered for itself first: the detector fires on a", file=out)
        print(
            "        sentinel, the walk reached the tree, and every exception is still used.",
            file=out,
        )


def check(root: Path | None = None, out: TextIO | None = None) -> int:
    stream = out or sys.stdout
    offences, files_read, used = scan(root)
    # The unused-exception question is about this repository. See `self_check`.
    is_repository = root is None or root.resolve() == REPO_ROOT
    failures = self_check(files_read, used, vocabulary_in_use=is_repository)
    report(offences, failures, files_read, stream)
    return 1 if (offences or failures) else 0


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ops.language", description=__doc__)
    parser.add_argument("--root", default=None, help="the tree to scan (default: this repository)")
    args = parser.parse_args(list(argv) if argv is not None else None)
    return check(Path(args.root) if args.root else None)


if __name__ == "__main__":
    raise SystemExit(main())
