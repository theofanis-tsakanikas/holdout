"""The measuring instrument, measured.

Claim 1's eval is evidence, and evidence held to a lower standard than the code it judges
stops being evidence. These tests are about the eval itself: they fail on the shape it had
before this branch, and each one is written against a defect somebody actually found in it
rather than against a defect its author imagined.

`CLAUDE.md`'s rule, in its own words:

> **A guard tested by its author is tested in the shape the guard already handles.**
> So: the case a guard is tested on may not come from whoever built the guard's idea of the
> failure.

Where the case comes from is therefore named in every docstring below. Two of the three come
from oversight level 2 reading the claim-1 branch in fresh context; the third is arithmetic
that follows from the corpus and could not have been chosen to flatter anything, because
`corpus/real/` is committed and digest-checked.
"""

from __future__ import annotations

import ast
import dataclasses
from decimal import Decimal
from pathlib import Path

from evals.guardrail import build, checks, reference, rounding

from holdout.contracts.loader import load
from holdout.core.guardrails import Refusal, RefusalCode, certify
from holdout.core.money import Money

#: The eval modules that compute a bound the core's own bounds are then compared against.
#: `build.py` is deliberately not among them: it rounds *inputs* — a derived unit cost, a
#: benchmark — and an input is not a second opinion about where a bound sits.
THE_SECOND_IMPLEMENTATION = ("reference.py", "rounding.py", "checks.py")

#: `Money`'s three rounding constructors. Between them they are every decision the core makes
#: about which way a number goes when it reaches the cent.
THE_CORE_S_ROUNDING = frozenset({"as_lower_bound", "as_upper_bound", "as_price"})


def _calls_to_the_core_s_rounding(source: Path) -> list[str]:
    tree = ast.parse(source.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in THE_CORE_S_ROUNDING:
            found.append(f"{source.name}:{node.lineno} {ast.unparse(node)}")
    return found


def test_the_second_implementation_never_rounds_with_the_core_s_own_primitive() -> None:
    """The defect this branch exists to close, asserted in the shape it was found in.

    The case is not one this test's author invented. It is the line that was in the
    repository — `Money.as_lower_bound(highest.scaleb(2))`, the last statement of
    `checks._exact_floor`, under a docstring that said the direction had been "arrived at
    independently, which is what makes the agreement between them worth checking". A review
    in fresh context read the docstring against the code and found they disagreed. Patching
    the primitive moved the eval's floor and the core's floor together, and G2, G3 and G6 all
    stayed green.

    This runs over `checks.py` as well as the two modules where the arithmetic now lives,
    because that is where the offending line was, and a rule scoped to the file the fix
    happens to have landed in would pass on the tree that had the bug.
    """
    here = Path(reference.__file__).parent
    offending = [
        hit
        for name in THE_SECOND_IMPLEMENTATION
        for hit in _calls_to_the_core_s_rounding(here / name)
    ]
    assert not offending, (
        "a module that computes a bound the core's bounds are checked against reached for "
        "the core's own rounding. Two implementations that share the primitive are one "
        "implementation, and a defect in it cancels out:\n  " + "\n  ".join(offending)
    )


def test_the_eval_rounds_a_bound_without_the_core_agreeing_that_it_did() -> None:
    """`rounding.py` and `Money` must agree — which is only worth asserting once they can
    disagree at all.

    The values are the awkward ones on purpose: a floor at a third of a cent, one exactly on
    a cent, and one that a half-even rounding would send the other way.
    """
    for euros in ("1.234", "1.230", "1.235", "0.005", "12.995", "0.001"):
        exact = Decimal(euros)
        assert rounding.as_floor(exact) == Money.as_lower_bound(exact.scaleb(2))
        assert rounding.as_ceiling(exact) == Money.as_upper_bound(exact.scaleb(2))


def _a_markdown_case_with_a_margin_floor() -> build.Case:
    for case in build.all_cases():
        if case.proposal.unit_cost is None:
            continue
        if any(c.name == "margin_floor" for c in reference.constraints(case)):
            return case
    raise AssertionError("the corpus produced no case with a margin floor")


def test_a_refusal_a_cent_inside_the_bound_is_no_longer_supported() -> None:
    """G3's tolerance, and why it was an exemption for one bug rather than slack for rounding.

    A refusal used to be "supported" if the price sat inside the *exact* bound by less than a
    cent. Every price in this eval is a whole number of cents, so under a correctly rounded
    core that branch is unreachable: a refused price is always at most one cent below a floor
    that has itself been rounded up, which puts it at or below the exact edge. The only way
    into the branch was a bound sitting a cent **above** where the rule puts it — precisely
    the shape `CLAUDE.md` records the ladder bug in, and the shape G3's own docstring cited
    as its motivation.

    The case is a real corpus decision with its price moved to the eval's own rounded floor —
    the one place a correct envelope certifies and a too-strict one refuses. It is arithmetic
    on committed, digest-checked inputs; nothing about it was chosen.
    """
    case = _a_markdown_case_with_a_margin_floor()
    floor = next(c for c in reference.constraints(case) if c.name == "margin_floor")
    assert floor.rounded is not None and floor.bound is not None

    on_the_floor = dataclasses.replace(
        case, proposal=dataclasses.replace(case.proposal, price=floor.rounded)
    )
    supported, detail = reference.refusal_is_supported(
        reference.constraints(on_the_floor), RefusalCode.BELOW_MARGIN_FLOOR
    )
    assert not supported, (
        "a refusal at a price that satisfies this eval's own rounded floor was accepted as "
        f"supported — {detail}"
    )
    # And the core agrees the price is admissible, which is what makes a refusal here wrong
    # rather than a disagreement about where the floor is.
    verdict = certify(on_the_floor.proposal, on_the_floor.envelope)
    if isinstance(verdict, Refusal):
        assert RefusalCode.BELOW_MARGIN_FLOOR not in verdict.codes


def test_the_ladder_finding_counts_ceilings_and_not_rules_with_no_bound() -> None:
    """The misattributed figure, pinned as a number rather than left in prose.

    `README.md`, `docs/DECISIONS.md` and the eval's own published numbers all said 7,366
    ladder quotes were refused by a ceiling. A review took the number apart: 6,650 of them
    are `MARGIN_CAP_BASIS_UNEVALUABLE`, a rule with no edge in either direction, which
    refuses every price at every rung and which a ladder that took ceilings would not move by
    one quote. The supportable figure is 716, and it comes from one envelope.

    The two counts are asserted here so that a change which quietly merges them again is red
    in the suite, not only in a paragraph somebody has to re-read.
    """
    policy = next(p for p in load().policies if p.id == "ladder_policy")
    run = checks.check_ladder_certifies_on_real_base_prices(policy)
    assert run.check.passed
    assert run.refused_by_a_ceiling == 716
    assert run.refused_by_a_rule_with_no_bound == 6650
    assert run.refused_beyond_the_three_bounds == 7366


#: What each rule is, in the only sense the ladder finding turns on: does it have an edge a
#: price can be on the wrong side of, or does it refuse whatever the price is? Written out by
#: hand, because a list read off `reference` could never disagree with `reference`.
THE_SIDE_EACH_RULE_BOUNDS_ON = {
    RefusalCode.MARGIN_CAP_EXCEEDED: "upper",
    RefusalCode.BELOW_MARGIN_FLOOR: "lower",
    RefusalCode.BELOW_ABSOLUTE_FLOOR: "lower",
    RefusalCode.MARKDOWN_EXCEEDS_MAX_DEPTH: "lower",
    RefusalCode.MARGIN_CAP_BASIS_UNEVALUABLE: "predicate",
    RefusalCode.COST_STALE: "predicate",
    RefusalCode.CATEGORY_FROZEN: "predicate",
    RefusalCode.DAILY_CHANGE_BUDGET_EXHAUSTED: "predicate",
    RefusalCode.PRIOR_PRICE_NOT_ESTABLISHED: "predicate",
}


def test_which_refusals_are_ceilings_is_read_off_the_rule_not_a_list_of_codes() -> None:
    """The classification the corrected figure rests on, over the whole corpus.

    A cap that binds is a ceiling; a cap whose basis states nothing computable is not, and
    neither is a stale cost, a frozen category or an exhausted change budget. `reference`
    decides this from the `side` it computes per rule, so a rule added to the envelope joins
    the right bucket without anyone remembering a list — and this test is the hand-written
    second opinion that would notice if it joined the wrong one.

    Every code above must actually be reached by the corpus. A row nothing exercises would
    be an assertion that passes because it never runs, which is the shape of a disarmed gate.
    """
    seen: dict[RefusalCode, set[str]] = {}
    for case in build.all_cases():
        for constraint in reference.constraints(case):
            seen.setdefault(constraint.code, set()).add(constraint.side)

    unreached = sorted(c.value for c in THE_SIDE_EACH_RULE_BOUNDS_ON if c not in seen)
    assert not unreached, f"the corpus never produced: {', '.join(unreached)}"

    wrong = {
        code.value: sorted(seen[code])
        for code, side in THE_SIDE_EACH_RULE_BOUNDS_ON.items()
        if seen[code] != {side}
    }
    assert not wrong, f"a rule bounds on a side this test did not expect: {wrong}"
