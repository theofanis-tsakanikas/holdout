"""As-of resolution over effective windows — stdlib only, so `holdout.core` may use it.

Every contract family is a timeline: a metric has versions, a guardrail has windows, a
policy has versions. The question the whole layer exists to answer is *which one was in
force on a given date*, because a decision taken in April is judged by April's rule
permanently, even after the law changes again. Resolving against "the current one" silently
rewrites history, which is the same failure as joining a historical sale to today's cost.

Two shapes are refused at validation:

* an **overlap** — two rules in force on the same day, so a decision has two correct
  answers and whichever is picked is arbitrary;
* a **gap** — a day with no rule at all, which is indistinguishable on disk from a rule
  that lapsed. A lapse is a fact and is written as a window that says so, with its own
  source. An absent window says nothing and can be read as anything.

The interval is half-open: `[effective_from, effective_to)`. `effective_to` is the first
day the window is *not* in force, so the successor's `effective_from` equals it exactly and
the midnight boundary has one owner rather than two or none.
"""

from __future__ import annotations

from datetime import date
from itertools import pairwise
from typing import Protocol


class Effective(Protocol):
    """Anything with an effective window."""

    @property
    def effective_from(self) -> date: ...

    @property
    def effective_to(self) -> date | None: ...


class TimelineError(ValueError):
    """A timeline that overlaps, gaps, or closes backwards."""


def in_order[T: Effective](items: tuple[T, ...] | list[T]) -> tuple[T, ...]:
    return tuple(sorted(items, key=lambda i: i.effective_from))


def check_timeline[T: Effective](items: tuple[T, ...] | list[T], *, what: str) -> list[str]:
    """Return every structural problem with a timeline. Empty means well-formed."""
    problems: list[str] = []
    ordered = in_order(items)
    if not ordered:
        return [f"{what}: a timeline with no entries is not a timeline"]

    for item in ordered:
        if item.effective_to is not None and item.effective_to <= item.effective_from:
            problems.append(
                f"{what}: window starting {item.effective_from} closes on "
                f"{item.effective_to}, which is not after it — a window in force for "
                f"no days cannot have applied to anything"
            )

    for earlier, later in pairwise(ordered):
        if earlier.effective_to is None:
            problems.append(
                f"{what}: the window starting {earlier.effective_from} is still in force "
                f"(effective_to: null) but {later.effective_from} starts another. Exactly "
                f"one window may be open-ended, and it is the last one."
            )
            continue
        if earlier.effective_to > later.effective_from:
            problems.append(
                f"{what}: overlap — {earlier.effective_from}..{earlier.effective_to} and "
                f"{later.effective_from}.. are both in force on {later.effective_from}. "
                f"A decision on that day would have two correct answers."
            )
        elif earlier.effective_to < later.effective_from:
            problems.append(
                f"{what}: gap — nothing is in force from {earlier.effective_to} to "
                f"{later.effective_from}. If the rule genuinely lapsed, write a window "
                f"that says so with its own source; an absent window is not a fact."
            )
    return problems


def resolve_as_of[T: Effective](items: tuple[T, ...] | list[T], on: date) -> T | None:
    """The single entry in force on `on`, or None if the timeline had not opened yet.

    None before the first `effective_from` is the honest answer and not a gap: the rule did
    not exist yet. None *inside* a timeline is impossible once `check_timeline` has passed.
    """
    for item in in_order(items):
        if item.effective_from <= on and (item.effective_to is None or on < item.effective_to):
            return item
    return None
