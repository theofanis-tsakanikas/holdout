"""The ladder, against `ladder_policy@v1` and against arithmetic worked out here.

The policy's rungs are 24h/20%, 12h/35%, 6h/50% and 3h/70%. Every expected price below is
computed in the test from a base price and a percentage, so the test would still be right
if the implementation were thrown away.
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal

import pytest

from holdout.contracts.model import Policy
from holdout.core.ladder import LadderError, applicable_step, quote, step_thresholds_minutes
from holdout.core.money import Money

HOUR = 60


def test_the_rungs_are_the_ones_the_contract_declares(ladder_policy: Policy) -> None:
    thresholds = step_thresholds_minutes(ladder_policy)
    assert [(s.step, minutes) for s, minutes in thresholds] == [
        (1, 24 * HOUR),
        (2, 12 * HOUR),
        (3, 6 * HOUR),
        (4, 3 * HOUR),
    ]
    assert [Decimal(str(s.depth_pct)) for s, _ in thresholds] == [
        Decimal(20),
        Decimal(35),
        Decimal(50),
        Decimal(70),
    ]


@pytest.mark.parametrize(
    ("minutes_out", "expected_step"),
    [
        (30 * HOUR, None),  # nothing has triggered; that is not a markdown of zero
        (24 * HOUR + 1, None),  # one minute before the first rung
        (24 * HOUR, 1),  # `hours_to_expiry_at_most`, so 24 is at most 24
        (20 * HOUR, 1),
        (12 * HOUR, 2),
        (10 * HOUR, 2),  # both the 24h and 12h rungs have triggered; the deeper one wins
        (6 * HOUR, 3),
        (3 * HOUR, 4),
        (30, 4),
        (0, 4),  # past expiry the deepest rung still answers; the safe state never fails
        (-120, 4),
    ],
)
def test_the_deepest_triggered_rung_wins(
    minutes_out: int, expected_step: int | None, ladder_policy: Policy
) -> None:
    """Taking the *first* match instead would leave a product two hours from expiry sitting
    at 20% off while the schedule says 70%."""
    step = applicable_step(minutes_out, ladder_policy)
    assert (step.step if step else None) == expected_step


def test_the_quoted_price_is_the_base_price_less_the_rung(ladder_policy: Policy) -> None:
    # 4.00 EUR at 35% off is 4.00 - 1.40 = 2.60.
    quoted = quote(10 * HOUR, base_price=Money.of("4.00"), policy=ladder_policy)
    assert quoted is not None
    assert quoted.step == 2
    assert quoted.price == Money.of("2.60")
    assert quoted.clamped_to_floor is False


def test_a_half_cent_in_the_quote_rounds_up_toward_the_shallower_markdown(
    ladder_policy: Policy,
) -> None:
    """2.90 EUR at 35% off is 290 - 101.5 = 188.5 cents, exactly between two cents.

    It rounds **up**, to 1.89, and not half-to-even to 1.88. A markdown price rounded down
    is a markdown deeper than the schedule declares, and the schedule is a schedule of
    limits. Rounding half-to-even here also put the ladder one cent below the envelope's
    own max-depth bound — which rounds up, being a lower bound — so the declared safe state
    produced a price the guardrail set refused. See `test_composition.py`.
    """
    quoted = quote(10 * HOUR, base_price=Money.of("2.90"), policy=ladder_policy)
    assert quoted is not None
    assert quoted.price == Money.of("1.89")


def test_before_the_first_rung_there_is_no_quote(ladder_policy: Policy) -> None:
    assert quote(30 * HOUR, base_price=Money.of("4.00"), policy=ladder_policy) is None


def test_a_step_below_the_floor_is_clamped_and_says_so(ladder_policy: Policy) -> None:
    """`floor_behaviour.when_step_breaches_floor: clamp_to_floor`. The ladder never
    produces the refusal itself — that is the guardrail set's answer, and it is donation or
    disposal rather than an error."""
    # 4.00 at 70% off is 1.20, below a floor of 1.50.
    quoted = quote(
        2 * HOUR,
        base_price=Money.of("4.00"),
        policy=ladder_policy,
        floor=Money.of("1.50"),
    )
    assert quoted is not None
    assert quoted.price == Money.of("1.50")
    assert quoted.clamped_to_floor is True, (
        "a clamped price is shallower than the schedule says, and an experiment that "
        "treated it as the schedule's price would be measuring something else"
    )


def test_a_step_above_the_floor_is_not_clamped(ladder_policy: Policy) -> None:
    quoted = quote(
        2 * HOUR,
        base_price=Money.of("4.00"),
        policy=ladder_policy,
        floor=Money.of("1.00"),
    )
    assert quoted is not None
    assert quoted.price == Money.of("1.20")
    assert quoted.clamped_to_floor is False


def test_every_quote_carries_the_policy_s_marker(ladder_policy: Policy) -> None:
    """Doctrine rule 2. The marker is a required field of a frozen object, so there is no
    quote without it and nothing downstream can drop it."""
    quoted = quote(10 * HOUR, base_price=Money.of("4.00"), policy=ladder_policy)
    assert quoted is not None
    assert quoted.marker == ladder_policy.marker == "FALLBACK_LADDER"


def test_a_fallback_policy_with_no_marker_is_refused(ladder_policy: Policy) -> None:
    unmarked = dataclasses.replace(ladder_policy, marker=None)
    with pytest.raises(LadderError, match="marker"):
        quote(10 * HOUR, base_price=Money.of("4.00"), policy=unmarked)


def test_the_ladder_is_not_the_base_price_path_s_safe_state(ladder_policy: Policy) -> None:
    """Doctrine rule 1: no path may inherit the other's answer. For a price increase
    silence is safe, so the base-price path falls to no action and never here."""
    other_path = dataclasses.replace(ladder_policy, decision_path="base_price")
    with pytest.raises(LadderError, match="markdown"):
        applicable_step(10 * HOUR, other_path)


def test_a_rung_that_is_not_a_whole_number_of_minutes_is_a_build_failure(
    ladder_policy: Policy,
) -> None:
    """The ladder's whole value is that it is deterministic. One that fired half a minute
    early on one machine and half a minute late on another would not be."""
    steps = list(ladder_policy.steps)
    steps[0] = dataclasses.replace(steps[0], hours_to_expiry_at_most=1.0004)
    broken = dataclasses.replace(ladder_policy, steps=tuple(steps))
    with pytest.raises(LadderError, match="whole number of minutes"):
        applicable_step(10 * HOUR, broken)


def test_the_ladder_is_a_pure_function_of_its_arguments(ladder_policy: Policy) -> None:
    """The same inputs give the same answer, and the answer is the same object each time in
    every sense that matters — no clock is read, no state is kept."""
    first = quote(7 * HOUR, base_price=Money.of("3.33"), policy=ladder_policy)
    second = quote(7 * HOUR, base_price=Money.of("3.33"), policy=ladder_policy)
    assert first == second
    # 3.33 EUR at 35% off is 333 - 116.55 = 216.45 cents, rounded up to 217.
    assert first is not None
    assert first.price == Money.of("2.17")
