"""The one exception type the contract layer raises, and the shape of a violation.

A violation is data, not a formatted string, because `make contracts` prints a count and
CI reads a list. A message baked at the raise site can only be printed."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Violation:
    """One thing wrong with one contract, located precisely enough to fix."""

    path: str
    """Repository-relative path of the offending file."""

    locator: str
    """Where inside the file — a JSON pointer-ish path, or '' for the document itself."""

    rule: str
    """Which rule was broken. A closed-ish vocabulary so violations can be counted."""

    detail: str

    def __str__(self) -> str:
        where = f"{self.path}:{self.locator}" if self.locator else self.path
        return f"[{self.rule}] {where}\n    {self.detail}"


class ContractError(Exception):
    """Raised when one or more contracts are invalid.

    Carries every violation found, not the first: a build that reports one problem per run
    turns a ten-minute fix into ten runs."""

    def __init__(self, violations: list[Violation], census: object = None) -> None:
        self.violations = violations
        self.census = census
        """Whatever the provenance walk counted before the load gave up. Carried on the
        failure so that a red build can still print how much of the envelope is sourced —
        a ratio that only ever appears on green builds cannot report bad news."""
        super().__init__(
            f"{len(violations)} contract violation(s):\n\n" + "\n".join(str(v) for v in violations)
        )


class CompilationError(Exception):
    """A contract that validates but cannot be compiled into one of its consumers.

    Kept separate from `ContractError` because it is a different failure: the contract is
    well formed and says something the compiler cannot honestly render. The rule is that a
    compiler may be opinionated but may never guess — a template that names a column the
    contract does not declare must refuse, not emit SQL that references a column no CTE
    selects. That query would compile, pass the staleness check, ship, and fail at the only
    moment nobody is watching.
    """

    def __init__(self, message: str, *, source_path: str, locator: str = "") -> None:
        self.source_path = source_path
        self.locator = locator
        super().__init__(message)
