"""The envelope, and the rule that bites hardest: a `value` without a `source`.

Doctrine rule 3 — nothing is invented. A default is a lie with a plausible shape, and a
guardrail is where a plausible shape does the most damage, because a number in this
directory is the thing standing between a model and a shelf.

The rule is enforced twice on purpose. The JSON Schema requires a `source` where a rule is
expected to carry one. An independent walk descends the whole document and refuses a
`value` at any nesting depth — including inside a key that did not exist when the schema
was written, which is exactly how this kind of rule is usually lost.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from holdout.contracts.errors import ContractError
from holdout.contracts.loader import load
from holdout.contracts.model import ContractSet
from holdout.contracts.provenance import check_provenance
from holdout.contracts.windows import check_timeline, resolve_as_of

FAMILY = ("floor", "max_delta", "frozen_categories", "prior_price", "regulated_basket")


def guardrail_path(root: Path, name: str) -> Path:
    return root / "guardrails" / f"{name}.yaml"


# ------------------------------------------------------------------ the envelope exists


def test_the_envelope_is_the_five_guardrails_claude_md_names(contracts: ContractSet) -> None:
    assert {g.id for g in contracts.guardrails} == set(FAMILY)


def test_every_guardrail_declares_which_decision_paths_it_binds(
    contracts: ContractSet,
) -> None:
    for guardrail in contracts.guardrails:
        assert guardrail.applies_to
        assert set(guardrail.applies_to) <= {"markdown", "base_price"}


def test_the_safe_state_is_asymmetric_and_declared_per_path(contracts: ContractSet) -> None:
    """Doctrine rule 1. For an expiring product silence is not safe — the product is thrown
    away — so the fresh path falls to the ladder. For a price increase silence is safe. No
    path may inherit the other's answer, so both are written down."""
    for guardrail in contracts.guardrails:
        for path in guardrail.applies_to:
            assert guardrail.safe_state.get(path), f"{guardrail.id} has no safe state for {path}"
    floor = contracts.guardrail("floor")
    assert floor.safe_state["markdown"] == "ladder"
    assert floor.safe_state["base_price"] == "no_action"


def test_every_window_is_well_formed(contracts: ContractSet) -> None:
    for guardrail in contracts.guardrails:
        assert check_timeline(guardrail.windows, what=guardrail.id) == []


def test_every_rule_carries_a_source(contracts: ContractSet) -> None:
    for guardrail in contracts.guardrails:
        for window in guardrail.windows:
            for rule in window.rules:
                assert rule.source.kind in {"legal_instrument", "scenario_assumption"}
                assert rule.source.verified_on


def test_a_legal_citation_names_its_instrument_article_and_url(
    contracts: ContractSet,
) -> None:
    """If it states a legal fact: which article, which instrument, verified when."""
    citations = [
        rule.source
        for guardrail in contracts.guardrails
        for window in guardrail.windows
        for rule in window.rules
        if rule.source.is_law
    ]
    assert citations, "the envelope states at least one verified legal fact"
    for source in citations:
        assert source.instrument and source.article and source.url
        assert source.url.startswith("https://")
        assert source.verified_on <= date(2026, 12, 31)


# ------------------------------------------------------------------ the rule that bites


def test_a_value_with_no_source_is_a_build_failure(
    contracts_copy: Path, edit_contract: Callable[[Path, Callable[[Any], Any]], None]
) -> None:
    def drop_source(document: Any) -> Any:
        del document["windows"][0]["rules"][0]["source"]
        return document

    edit_contract(guardrail_path(contracts_copy, "floor"), drop_source)
    with pytest.raises(ContractError) as raised:
        load(contracts_copy)
    assert any(v.rule in {"schema", "value_without_source"} for v in raised.value.violations), (
        raised.value.violations
    )


def test_a_value_nested_where_the_schema_never_looked_is_still_a_build_failure(
    contracts_copy: Path, edit_contract: Callable[[Path, Callable[[Any], Any]], None]
) -> None:
    """The independent walk, doing the thing the schema cannot.

    A rule is deliberately permissive about shape, so a `thresholds:` block added a year
    from now validates. The walk descends into it anyway and refuses the bare number, which
    is the difference between a rule that holds and a rule that held when it was written.
    """

    def add_unsourced_threshold(document: Any) -> Any:
        document["windows"][0]["rules"][0]["thresholds"] = {"value": 12.5, "unit": "percent"}
        return document

    edit_contract(guardrail_path(contracts_copy, "floor"), add_unsourced_threshold)
    with pytest.raises(ContractError) as raised:
        load(contracts_copy)
    violations = [v for v in raised.value.violations if v.rule == "value_without_source"]
    assert violations, raised.value.violations
    assert "thresholds" in violations[0].locator


def test_the_walk_finds_a_value_at_any_depth() -> None:
    document = {"a": [{"b": {"c": {"value": 3}}}]}
    violations = check_provenance(document, path="test.yaml")
    assert [v.rule for v in violations] == ["value_without_source"]
    assert violations[0].locator == "/a/0/b/c"


def test_a_source_of_an_invented_kind_is_a_build_failure(
    contracts_copy: Path, edit_contract: Callable[[Path, Callable[[Any], Any]], None]
) -> None:
    """Two kinds are admissible. There is no third where a number simply appears."""

    def invent_a_kind(document: Any) -> Any:
        document["windows"][0]["rules"][0]["source"] = {
            "kind": "industry_practice",
            "verified_on": "2026-08-27",
        }
        return document

    edit_contract(guardrail_path(contracts_copy, "max_delta"), invent_a_kind)
    with pytest.raises(ContractError) as raised:
        load(contracts_copy)
    assert any(v.rule in {"schema", "source_malformed"} for v in raised.value.violations)


def test_a_legal_citation_missing_its_url_is_a_build_failure(
    contracts_copy: Path, edit_contract: Callable[[Path, Callable[[Any], Any]], None]
) -> None:
    """A citation nobody can follow is a citation nobody can check."""

    def strip_url(document: Any) -> Any:
        document["windows"][0]["rules"][0]["source"] = {
            "kind": "legal_instrument",
            "instrument": "Directive 98/6/EC",
            "article": "Article 6a",
            "verified_on": "2026-08-27",
        }
        return document

    edit_contract(guardrail_path(contracts_copy, "prior_price"), strip_url)
    with pytest.raises(ContractError) as raised:
        load(contracts_copy)
    assert any(v.rule in {"schema", "source_malformed"} for v in raised.value.violations)


def test_a_scenario_assumption_must_actually_say_what_it_assumes(
    contracts_copy: Path, edit_contract: Callable[[Path, Callable[[Any], Any]], None]
) -> None:
    """An empty note turns the honest label into a rubber stamp."""

    def empty_note(document: Any) -> Any:
        document["windows"][0]["rules"][0]["source"] = {
            "kind": "scenario_assumption",
            "note": "because",
            "verified_on": "2026-08-27",
        }
        return document

    edit_contract(guardrail_path(contracts_copy, "floor"), empty_note)
    with pytest.raises(ContractError) as raised:
        load(contracts_copy)
    assert any(v.rule == "schema" for v in raised.value.violations)


# ------------------------------------------------------------------ as-of, concretely


def test_a_decision_is_judged_by_the_window_that_was_in_force(
    contracts: ContractSet,
) -> None:
    frozen = contracts.guardrail("frozen_categories")
    june_2025 = resolve_as_of(frozen.windows, date(2025, 6, 15))
    today = resolve_as_of(frozen.windows, date(2026, 8, 27))
    assert june_2025 is not None and today is not None
    assert june_2025 is not today
    assert "fresh_fish" not in june_2025.rules[0].value
    assert "fresh_fish" in today.rules[0].value


def test_an_overlapping_window_is_a_build_failure(
    contracts_copy: Path, edit_contract: Callable[[Path, Callable[[Any], Any]], None]
) -> None:
    def overlap(document: Any) -> Any:
        document["windows"][0]["effective_to"] = "2026-01-01"
        return document

    edit_contract(guardrail_path(contracts_copy, "frozen_categories"), overlap)
    with pytest.raises(ContractError) as raised:
        load(contracts_copy)
    assert any("overlap" in v.detail for v in raised.value.violations)


def test_a_gapped_window_is_a_build_failure(
    contracts_copy: Path, edit_contract: Callable[[Path, Callable[[Any], Any]], None]
) -> None:
    """A lapse is a fact and is written as a window that says so. A hole is not a fact."""

    def gap(document: Any) -> Any:
        document["windows"][0]["effective_to"] = "2025-09-01"
        return document

    edit_contract(guardrail_path(contracts_copy, "frozen_categories"), gap)
    with pytest.raises(ContractError) as raised:
        load(contracts_copy)
    assert any("gap" in v.detail for v in raised.value.violations)


# ------------------------------------------------------------ the envelope binds the policy


def test_the_ladder_never_cuts_deeper_than_the_envelope_allows(
    contracts: ContractSet,
) -> None:
    """A guardrail looser than every policy it governs has never refused anything."""
    max_depth = contracts.guardrail("max_delta").windows[-1].rule("markdown_max_depth_pct")
    ladder = next(p for p in contracts.policies if p.id == "ladder_policy")
    assert max_depth is not None
    assert max(step.depth_pct for step in ladder.steps) <= max_depth.value


def test_the_ladder_fits_inside_the_daily_change_budget(contracts: ContractSet) -> None:
    budget = (
        contracts.guardrail("max_delta").windows[-1].rule("markdown_max_changes_per_sku_per_day")
    )
    ladder = next(p for p in contracts.policies if p.id == "ladder_policy")
    assert budget is not None
    assert len(ladder.steps) <= budget.value


# ------------------------------------------------------- the law the architecture rests on


def test_the_perishable_exemption_is_in_force_and_is_a_verified_citation(
    contracts: ContractSet,
) -> None:
    """The single provision the fresh-markdown path depends on.

    Greek law puts perishable food outside the prior-price rule. Without that, every
    automatic markdown would be an announcement of a reduction that must carry a thirty-day
    lowest price, and the primary decision path could not actuate itself. A guardrail this
    load-bearing may not be a scenario assumption.
    """
    window = resolve_as_of(contracts.guardrail("prior_price").windows, date(2026, 8, 27))
    assert window is not None
    exemption = window.rule("perishable_exemption")
    assert exemption is not None
    assert exemption.value is True
    assert exemption.source.is_law
    cited = f"{exemption.source.article} {exemption.source.instrument}"
    assert "2251/1994" in cited, "the exemption now lives in the consumer protection law"
    assert "5111/2024" in cited, "and it was put there by the 2024 instrument"


def test_the_prior_price_rule_changed_instrument_not_only_numbers(
    contracts: ContractSet,
) -> None:
    """A markdown announced in March 2024 is judged by a provision that was later repealed
    outright. An implementation that always reads the current rule would judge it by a law
    that did not exist at the time."""
    windows = contracts.guardrail("prior_price").windows
    before = resolve_as_of(windows, date(2024, 3, 1))
    after = resolve_as_of(windows, date(2024, 6, 1))
    assert before is not None and after is not None and before is not after
    old = before.rule("prior_price_lookback_days")
    new = after.rule("prior_price_lookback_days")
    assert old is not None and new is not None
    assert old.value == new.value == 30, "the number is the same"
    assert old.source.instrument != new.source.instrument, "the instrument is not"


def test_the_margin_cap_changed_shape_and_not_only_its_numbers(
    contracts: ContractSet,
) -> None:
    """The reason a single 'current cap' field could never have worked: the unit of
    comparison moved from the unit sold to the product code, and the benchmark from a point
    in time to a full-year average. Basis and benchmark are separate rules because they are
    separately sourced and they moved at different times."""
    windows = contracts.guardrail("regulated_basket").windows
    early = resolve_as_of(windows, date(2022, 4, 1))
    late = resolve_as_of(windows, date(2026, 4, 1))
    assert early is not None and late is not None
    assert early.rule("cap_basis").value == "per_unit"  # type: ignore[union-attr]
    assert late.rule("cap_basis").value == "per_product_code"  # type: ignore[union-attr]
    assert early.rule("cap_benchmark").value == "seller_margin_before_2021_09_01"  # type: ignore[union-attr]
    assert late.rule("cap_benchmark").value == "average_gross_margin_2025"  # type: ignore[union-attr]


def test_the_2021_window_claims_no_basis_because_its_instrument_states_none(
    contracts: ContractSet,
) -> None:
    """A regression test for the one defect a fresh reviewer had to find by hand.

    ν. 4818/2021 does not say what the margin is measured on — «ανά μονάδα» does not occur in
    it. An earlier version of this contract carried `per_unit_vs_seller_margin_before_2020_09_01`
    under a `legal_instrument` citation to that law, having imported the arithmetic of the
    2022 successor. Nothing here could catch it: the citation was real, the URL resolved, the
    article existed. Only the text disagreed.

    So the window now claims what the instrument states and nothing more, and the basis it
    does not state is a scenario assumption that says why.
    """
    window = resolve_as_of(contracts.guardrail("regulated_basket").windows, date(2021, 9, 1))
    assert window is not None
    basis = window.rule("cap_basis")
    assert basis is not None
    assert basis.value == "unspecified_in_the_instrument"
    assert basis.source.kind == "scenario_assumption", (
        "the 2021 instrument states no basis, so no citation may assert one"
    )
    benchmark = window.rule("cap_benchmark")
    assert benchmark is not None and benchmark.source.is_law


def test_the_2021_quote_carries_the_clauses_that_make_the_scope_checkable(
    contracts: ContractSet,
) -> None:
    """An elided clause is invisible to every other check in this repository.

    The 2021 measure is conditional on the COVID-19 emergency, self-limited to 31.12.2021,
    and wider in scope than nutrition. All three were elided from the quote once, and each
    elision made an overreach harder to see.
    """
    window = resolve_as_of(contracts.guardrail("regulated_basket").windows, date(2021, 9, 1))
    assert window is not None
    quote = (window.rule("cap_in_force") or window.rules[0]).source.quote or ""
    assert "COVID-19" in quote
    assert "31\u03b7\u03c2.12.2021" in quote
    assert "\u03bc\u03b5\u03c4\u03b1\u03ba\u03af\u03bd\u03b7\u03c3\u03b7" in quote
    assert "\u03b1\u03c3\u03c6\u03ac\u03bb\u03b5\u03b9\u03b1" in quote
    expiry = window.rule("cap_expires_on")
    assert expiry is not None and expiry.value == "2021-12-31" and expiry.source.is_law


def test_every_citation_carries_a_quote_or_accounts_for_its_absence(
    contracts: ContractSet,
) -> None:
    """A citation with neither is an assertion with a URL attached."""
    for guardrail in contracts.guardrails:
        for window in guardrail.windows:
            for rule in window.rules:
                if rule.source.is_law:
                    assert rule.source.quote or rule.source.note, f"{guardrail.id}/{rule.id}"


def test_a_citation_with_neither_quote_nor_note_is_a_build_failure(
    contracts_copy: Path, edit_contract: Callable[[Path, Callable[[Any], Any]], None]
) -> None:
    def strip_both(document: Any) -> Any:
        source = document["windows"][-1]["rules"][0]["source"]
        source.pop("quote", None)
        source.pop("note", None)
        return document

    edit_contract(guardrail_path(contracts_copy, "prior_price"), strip_both)
    with pytest.raises(ContractError) as raised:
        load(contracts_copy)
    assert any(v.rule == "schema" for v in raised.value.violations)


def test_a_period_with_no_cap_says_so_rather_than_leaving_a_hole(
    contracts: ContractSet,
) -> None:
    """Where an instrument could not be verified, the window states that no cap is encoded
    and carries the reason. An absent window would have been read as 'no cap' by everyone
    downstream without anyone ever deciding that."""
    window = resolve_as_of(contracts.guardrail("regulated_basket").windows, date(2025, 6, 1))
    assert window is not None
    in_force = window.rule("cap_in_force")
    assert in_force is not None
    assert in_force.value is False
    assert in_force.source.kind == "scenario_assumption"
    assert in_force.source.note and "verified" in in_force.source.note


def test_every_window_of_the_basket_declares_whether_a_cap_is_in_force(
    contracts: ContractSet,
) -> None:
    for window in contracts.guardrail("regulated_basket").windows:
        rule = window.rule("cap_in_force")
        assert rule is not None, window.effective_from
        assert isinstance(rule.value, bool)


def test_no_scenario_assumption_pretends_to_be_a_citation(contracts: ContractSet) -> None:
    """The failure this whole mechanism exists to make impossible: a law number, a gazette
    reference or a percentage presented as law inside a note that is not one."""
    for guardrail in contracts.guardrails:
        for window in guardrail.windows:
            for rule in window.rules:
                if rule.source.kind == "scenario_assumption":
                    assert rule.source.instrument is None
                    assert rule.source.article is None
                    assert rule.source.url is None


def test_make_contracts_itself_goes_red_on_a_value_with_no_source(
    contracts_copy: Path,
    edit_contract: Callable[[Path, Callable[[Any], Any]], None],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The promise `make contracts` makes, tested at the command it makes it from.

    The loader-level tests above prove the rule; this proves the build actually runs it and
    exits non-zero, which is the difference between a rule and a gate.
    """
    from holdout.contracts.cli import main

    def drop_source(document: Any) -> Any:
        document["windows"][-1]["rules"][0]["thresholds"] = {"value": 3}
        return document

    edit_contract(guardrail_path(contracts_copy, "regulated_basket"), drop_source)
    exit_code = main(
        ["check", "--contracts", str(contracts_copy), "--root", str(contracts_copy.parent)]
    )
    assert exit_code == 1
    assert "value_without_source" in capsys.readouterr().err
