"""`make language` is attacked by taking its instrument away, not by being run on a clean tree.

A gate that has only ever been seen green has not been tested, and this one has a second
failure mode that the others do not: it reports *the absence of something*. Every way it could
be broken produces the same output as success — an empty list of offences — so the tests below
break the instrument three ways and require a red run each time.

**Where this test came from.** The rule it enforces was violated first and measured second, and
the measurement was taken with `grep -P`, which BSD grep on macOS does not implement. The
command exited 1, `2>/dev/null` hid the reason, and *no matches* and *no such option* are the
same two characters on a terminal. A count of zero was reported from a check that never ran.

That is the twelfth instance of `CLAUDE.md`'s *a guard tested by its author*, and its form is
new: not a sentence, not a number in configuration, but **a tool that was not there.**

The rule it generalises to — *a gate goes red when its own instrument is missing, proved by
an attack that takes the instrument away* — is not in `CLAUDE.md` yet. It lands there with
`ops/every-number-carries-its-kind`, which is where it is applied to every other gate. This
file is one gate meeting it early, and saying so rather than citing a sentence that has not
been written.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from ops import language

# Written as code points, so this test file needs no exception from the gate it tests. The
# first draft of these three lines used literals under a comment claiming they did not, and
# `make language` refused it -- the gate biting the test written to prove it bites.
GREEK_SENTENCE = "\u03b7 \u03b1\u03bd\u03b1\u03c6\u03bf\u03c1\u03ac"  # "the report"
GREEK_ALPHA = "\u03b1"  # alpha
GREEK_UNUSED = "\u03c8\u03c9"  # two letters this repository does not contain


def _tree(root: Path, files: dict[str, str]) -> Path:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _padding(count: int) -> dict[str, str]:
    """Enough English files that the walk clears `MIN_FILES_SCANNED`."""
    return {f"pad/file_{i:03d}.md": "English only.\n" for i in range(count)}


def _run(root: Path) -> tuple[int, str]:
    out = io.StringIO()
    code = language.check(root, out)
    return code, out.getvalue()


# --------------------------------------------------------------- it bites on a real violation


def test_a_greek_sentence_in_repository_content_is_refused(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        {
            "docs/reviews/phase-2.md": f"# Review\n\n{GREEK_SENTENCE} is not English.\n",
            **_padding(80),
        },
    )
    code, output = _run(root)
    assert code == 1
    assert "docs/reviews/phase-2.md:3" in output
    assert "Greek run(s) no declared exception admits" in output


def test_a_declared_symbol_is_admitted_anywhere(tmp_path: Path) -> None:
    """The gate is not a blanket ban: alpha is what the estimator calls alpha."""
    root = _tree(
        tmp_path,
        {"src/estimator.py": f'"""Significant at {GREEK_ALPHA}."""\n', **_padding(80)},
    )
    code, output = _run(root)
    assert code == 0, output


def test_an_excepted_path_may_quote_the_gazette(tmp_path: Path) -> None:
    """A verbatim article stays in the language it was published in."""
    root = _tree(
        tmp_path,
        {"docs/REGULATORY.md": f"# Regulatory\n\n> {GREEK_SENTENCE}\n", **_padding(80)},
    )
    code, output = _run(root)
    assert code == 0, output


def test_the_exception_is_a_path_and_says_so(tmp_path: Path) -> None:
    """The declared limit, asserted rather than described: anything inside an excepted path
    passes, including something that has no business being there. The pull-request diff is what
    catches that, and the module's own comment says so."""
    root = _tree(
        tmp_path,
        {
            "docs/REGULATORY.md": f"# Regulatory\n\n{GREEK_SENTENCE} — a review report, hidden here.\n",
            **_padding(80),
        },
    )
    code, _ = _run(root)
    assert code == 0


# ------------------------------------------------------- it goes red when its instrument is gone


def test_a_detector_that_detects_nothing_is_a_red_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The `grep -P` failure, reproduced: the instrument is not there and the tree is dirty.

    A regex edited into something that cannot match is exactly a tool that is not installed —
    the scan completes, finds nothing, and a gate with no self-check reports success.
    """
    import re

    never = re.compile("(?!x)x")
    monkeypatch.setattr(language, "GREEK_CHAR", never)
    monkeypatch.setattr(language, "GREEK_RUN", never)

    root = _tree(
        tmp_path,
        {"docs/reviews/phase-2.md": f"{GREEK_SENTENCE}\n", **_padding(80)},
    )
    code, output = _run(root)
    assert code == 1, "a silent detector reported a clean tree"
    assert "the detector does not detect" in output
    assert "the instrument cannot show that it works" in output


def test_a_walk_that_reaches_nothing_is_a_red_run(tmp_path: Path) -> None:
    """A wrong root, a filter that excludes everything, a permissions error swallowed in a loop
    — all of them produce zero offences, and none of them is a clean repository."""
    root = _tree(tmp_path, {"only.md": "English only.\n"})
    code, output = _run(root)
    assert code == 1
    assert "under the floor" in output
    assert "Nothing was checked" in output


def test_an_exception_nobody_uses_is_a_red_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unused exception is a pre-approval for whoever adds that token next.

    The same argument claim 7's `O12` makes about its eleven explained collisions, and the same
    failure mode: the entry outlives the thing it was written for, and the next person to write
    that token inherits a permission nobody granted them.

    Planted against the **real** tree, because that is the only tree the question is about — a
    scratch directory has not stopped using an exception, it never used one.
    """
    invented = language.Allowance(
        GREEK_UNUSED,
        "mathematical_symbol",
        "a token this repository does not contain, planted to show the check fires",
    )
    monkeypatch.setattr(language, "ALLOWED", (*language.ALLOWED, invented))

    out = io.StringIO()
    code = language.check(None, out)
    assert code == 1
    assert "no longer used anywhere" in out.getvalue()


# ----------------------------------------------------------------- and the real tree is clean


def test_the_repository_itself_has_no_undeclared_greek() -> None:
    offences, files_read, used = language.scan()
    assert offences == [], [str(o) for o in offences[:10]]
    assert language.self_check(files_read, used) == []


def test_every_declared_exception_carries_a_reason() -> None:
    """No entry exists without one — the rule `contracts/` applies to a `value`, applied here."""
    for entry in (*language.EXCEPTED_PATHS, *language.ALLOWED):
        assert entry.reason.strip(), entry.what
        assert entry.kind.strip(), entry.what
        assert len(entry.reason) > 30, f"{entry.what}: a reason has to be an argument"
