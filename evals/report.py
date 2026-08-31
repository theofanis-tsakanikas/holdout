"""The shape every claim's eval has: named checks, published numbers, a machine reading.

Four things this module exists to force, and each of them is a rule the rest of the
repository already lives by:

**A check has a stable id.** `make gate-proof` plants a deliberate break and then demands
that a *named* check refuses it. A harness that could only see the process exit code would
accept any failure as proof, including the one where the eval crashed because the mutation
made it unimportable. So ids are the contract between an eval and its mutations, and they
are as stable as a refusal code — renaming one is a change to both files.

**A check states a falsifiable question, not a label.** `question` is the sentence that
would be false if the check failed. If it cannot be written as such a sentence, the check
is measuring something rather than asserting it, and it belongs in `numbers`.

**Numbers are published whether or not anything failed.** CLAUDE.md: *numbers, not a green
tick*. `9/200 = 4.5%` said more than "PASS" ever will, and a figure that only appears on
failure is a figure nobody has looked at. Every check prints its figure both ways.

**A failure carries counterexamples.** A red check that says "342 rows violated the margin
floor" and cannot name one is a check whose author has to start the investigation from
nothing.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, TextIO

#: How many failing rows a check carries with it. Enough to start from; not so many that a
#: red run buries its own summary. The count is always reported in full — only the examples
#: are capped — and the cap is printed, because a silent truncation reads as completeness.
MAX_COUNTEREXAMPLES = 5


@dataclass(frozen=True, slots=True)
class Check:
    """One falsifiable assertion about the system, and the number behind it."""

    id: str
    """Stable across refactors. `gate-proof` mutations name it; see the module docstring."""

    question: str
    """The sentence that is false when this check fails. Written as a question the eval answers."""

    passed: bool
    figure: str
    """The number, printed pass or fail. Never a tick and never the word 'OK'."""

    detail: str = ""
    counterexamples: tuple[str, ...] = ()

    unarmed_because: str = ""
    """Why no `gate-proof` mutation can be planted against this check.

    **Empty means one could be**, not that one exists. `make gate-proof` sorts every check into
    three states and prints the counts: armed by a mutation, declared un-armable with this
    sentence, or **unarmed** — a gate nobody has shown to bite yet. The third is reported rather
    than refused, for the reason `docs/FINDINGS.md` reports `adrift` rather than refusing it: a
    gate nobody has armed yet is a real state, and refusing it teaches people to write a sentence
    instead of a mutation.

    So this field is for *cannot*, never for *have not*. The honest reasons are narrow and the
    repository already knows all of them: the break would have to edit the **detector** rather
    than the system (`ops/`, `corpus/`, the eval itself), the check asserts a property of the
    **inputs** that no change to `src/holdout/` can move, or the check is **absent from the
    configuration a mutation runs at** and computing it there would make it a different check.
    Anything else is a mutation somebody has not written."""


@dataclass(frozen=True, slots=True)
class Report:
    """Everything one claim's eval has to say."""

    claim: int | None
    """The claim this report is about, or `None` where it is about the arrangement of
    several — `gate-proof`'s ledger audits every claim's mutations and belongs to none."""

    title: str
    checks: tuple[Check, ...]
    numbers: tuple[tuple[str, str], ...] = ()
    """Measurements that are not assertions — published because they are the evidence, and
    because a figure nobody publishes is a figure that can drift without anyone noticing."""

    notes: tuple[str, ...] = field(default=())
    """What this run does not prove. Printed every time, not kept for a README."""

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    @property
    def exit_code(self) -> int:
        return 0 if self.passed else 1


def _rule(stream: TextIO, width: int = 78) -> None:
    print("─" * width, file=stream)


def render(report: Report, stream: TextIO | None = None) -> None:
    """Print a report the way the terminal shots in CLAUDE.md's shot list want it."""
    out = stream if stream is not None else sys.stdout
    _rule(out)
    heading = f"claim {report.claim} · " if report.claim is not None else ""
    print(f"{heading}{report.title}", file=out)
    _rule(out)

    width = max((len(c.id) for c in report.checks), default=0)
    for check in report.checks:
        mark = "pass" if check.passed else "FAIL"
        print(f"  {mark}  {check.id:<{width}}  {check.figure}", file=out)
        if not check.passed:
            print(f"        {check.question}", file=out)
            if check.detail:
                print(f"        {check.detail}", file=out)
            for example in check.counterexamples[:MAX_COUNTEREXAMPLES]:
                print(f"          · {example}", file=out)
            hidden = len(check.counterexamples) - MAX_COUNTEREXAMPLES
            if hidden > 0:
                print(f"          · … {hidden} further examples not printed", file=out)

    if report.numbers:
        print("", file=out)
        label_width = max(len(label) for label, _ in report.numbers)
        for label, value in report.numbers:
            print(f"  {label:<{label_width}}  {value}", file=out)

    if report.notes:
        print("", file=out)
        print("  what this does not prove", file=out)
        for note in report.notes:
            print(f"    · {note}", file=out)

    print("", file=out)
    failed = [c.id for c in report.checks if not c.passed]
    if failed:
        print(
            f"  RED    {len(failed)}/{len(report.checks)} checks failed: {', '.join(failed)}",
            file=out,
        )
    else:
        print(f"  green  {len(report.checks)}/{len(report.checks)} checks", file=out)
    _rule(out)


def as_json(report: Report) -> dict[str, Any]:
    """The machine reading `make gate-proof` consumes.

    It exists so a mutation can be required to trip **one named check** rather than merely
    to make something go red. See `evals/gate_proof/README.md`, rule 2.
    """
    return {
        "claim": report.claim,
        "title": report.title,
        "passed": report.passed,
        "checks": [
            {
                "id": check.id,
                "question": check.question,
                "passed": check.passed,
                "figure": check.figure,
                "detail": check.detail,
                "counterexamples": list(check.counterexamples[:MAX_COUNTEREXAMPLES]),
            }
            for check in report.checks
        ],
        "numbers": dict(report.numbers),
    }


def main(report: Report, argv: Sequence[str]) -> int:
    """The entry point every `evals/<claim>/__main__.py` delegates to."""
    if "--json" in argv:
        json.dump(as_json(report), sys.stdout, ensure_ascii=False, indent=2)
        print("", file=sys.stdout)
    else:
        render(report)
    return report.exit_code
