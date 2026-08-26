"""As-of resolution, and the two shapes of timeline that are refused.

"A decision taken in April is judged by April's rule, permanently, even after the law
changes again." That sentence is only true if two things hold: the rule that applied in
April is still readable, and asking for it returns exactly one answer. An overlap gives two
answers, a gap gives none, and both are build failures rather than runtime surprises.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from holdout.contracts.model import ContractSet
from holdout.contracts.windows import check_timeline, resolve_as_of


@dataclass(frozen=True)
class Span:
    effective_from: date
    effective_to: date | None
    name: str


def span(start: str, end: str | None, name: str) -> Span:
    return Span(date.fromisoformat(start), date.fromisoformat(end) if end else None, name)


CONTIGUOUS = [
    span("2026-01-01", "2026-04-01", "winter"),
    span("2026-04-01", "2026-07-01", "spring"),
    span("2026-07-01", None, "current"),
]


def test_a_contiguous_timeline_is_well_formed() -> None:
    assert check_timeline(CONTIGUOUS, what="test") == []


def test_an_overlap_is_refused_because_a_decision_would_have_two_correct_answers() -> None:
    overlapping = [
        span("2026-01-01", "2026-05-01", "winter"),
        span("2026-04-01", None, "spring"),
    ]
    problems = check_timeline(overlapping, what="test")
    assert any("overlap" in p for p in problems)


def test_a_gap_is_refused_because_a_lapse_and_an_omission_look_identical() -> None:
    gapped = [
        span("2026-01-01", "2026-04-01", "winter"),
        span("2026-05-01", None, "spring"),
    ]
    problems = check_timeline(gapped, what="test")
    assert any("gap" in p for p in problems)
    assert any("lapsed" in p for p in problems)


def test_only_the_last_window_may_be_open_ended() -> None:
    problems = check_timeline(
        [span("2026-01-01", None, "first"), span("2026-04-01", None, "second")], what="test"
    )
    assert any("Exactly" in p for p in problems)


def test_a_window_that_closes_before_it_opens_is_refused() -> None:
    problems = check_timeline([span("2026-04-01", "2026-01-01", "backwards")], what="test")
    assert any("not after it" in p for p in problems)


def test_the_boundary_belongs_to_the_successor() -> None:
    """Half-open, so the day a rule is replaced has exactly one owner."""
    assert resolve_as_of(CONTIGUOUS, date(2026, 3, 31)).name == "winter"  # type: ignore[union-attr]
    assert resolve_as_of(CONTIGUOUS, date(2026, 4, 1)).name == "spring"  # type: ignore[union-attr]


def test_before_the_first_window_nothing_is_in_force() -> None:
    """Honest, and not a gap: the rule did not exist yet."""
    assert resolve_as_of(CONTIGUOUS, date(2025, 12, 31)) is None


def test_april_is_judged_by_aprils_rule_after_a_later_amendment_exists() -> None:
    april = date(2026, 4, 15)
    before_amendment = CONTIGUOUS[:2]
    assert resolve_as_of(before_amendment, april).name == "spring"  # type: ignore[union-attr]
    assert resolve_as_of(CONTIGUOUS, april).name == "spring"  # type: ignore[union-attr]


def test_every_guardrail_in_the_contract_has_a_well_formed_timeline(
    contracts: ContractSet,
) -> None:
    for guardrail in contracts.guardrails:
        assert check_timeline(guardrail.windows, what=guardrail.id) == []


def test_every_metric_family_in_the_contract_has_a_well_formed_timeline(
    contracts: ContractSet,
) -> None:
    for metric_id in contracts.metric_ids:
        assert check_timeline(contracts.metric_versions(metric_id), what=metric_id) == []


def test_the_margin_metric_resolves_to_the_version_that_was_in_force(
    contracts: ContractSet,
) -> None:
    """A readout for a period before 2026-03-01 must not silently apply v3's rounding."""
    family = contracts.metric_versions("category_margin_per_store_week")
    assert resolve_as_of(family, date(2025, 6, 1)).version == 1  # type: ignore[union-attr]
    assert resolve_as_of(family, date(2025, 10, 1)).version == 2  # type: ignore[union-attr]
    assert resolve_as_of(family, date(2026, 4, 15)).version == 3  # type: ignore[union-attr]
