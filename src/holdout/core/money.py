"""Money, once, for the whole core — integer minor units and nothing else.

The choice, stated once and held everywhere
-------------------------------------------
**A monetary amount is an integer number of euro cents.** Not a float, not a `Decimal` that
happens to carry two places, not a string. `Money` wraps an `int` and exposes no way to get
a float out of it.

Two reasons, and the second is the one that would actually bite:

* A binary float cannot represent 0.10 exactly, so a floor at cost plus zero margin either
  refuses a price that equals the cost or accepts one a fraction below it, depending on
  which way the last bit fell. A guardrail that is wrong by a fraction of a cent is still a
  guardrail that let a price through.
* Claim 5 compares three consumers of the metric contract **as integers, with no
  tolerance**. Every intermediate that ever became a float has already lost that, because
  the first division introduces a difference no downstream rounding can remove. The
  contract's declared rounding — `half_even`, two decimals — is exactly the scale of a
  cent, so an amount that is born as an integer cent and stays one never needs a tolerance.

`float` is refused at runtime as well as in the type signature, because the type signature
is only checked where mypy runs and the arithmetic here is what stands between a model and
a shelf. A test under `tests/boundary/` asserts that no module in `holdout.core` contains a
float literal, a `float` annotation or a call to `float()` at all.

Percentages arrive as `Decimal`. Multiplying an integer cent amount by a `Decimal` gives an
exact `Decimal` number of cents, which then has to come back to an integer — and *how* it
comes back is a decision, not a detail.

Three roundings, because a bound is not a price
-----------------------------------------------
* `as_price` rounds **half to even**, the mode the metric contract declares. This is for an
  amount that is going to be charged.
* `as_lower_bound` rounds **up**. A floor of 123.4 cents rounded to the nearest cent is 123,
  and 123 is below the floor. A bound that rounds toward the thing it is supposed to
  exclude is not a bound.
* `as_upper_bound` rounds **down**, for the same reason in the other direction.

So the envelope's floor is always at least the true floor and its ceiling is always at most
the true ceiling, and the arithmetic can never widen the envelope by half a cent. The cost
is that a price may be refused which was legal by a fraction of a cent; that is the
direction this system is built to err in.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, Decimal, localcontext

#: Enough precision that no intermediate in this repository is ever inexact, and small
#: enough to stay honest about it. A price times a forecast quantity times a percentage is
#: nowhere near thirty-four significant digits.
PRECISION = 34

ONE_CENT = Decimal(1)


class MoneyError(TypeError):
    """A monetary amount that arrived in a representation this system does not accept."""


def _exact(value: Decimal | int | str) -> Decimal:
    """A `Decimal` that is exactly what the caller wrote, or a refusal.

    A `float` is refused rather than converted. `Decimal(0.1)` is
    `0.1000000000000000055511151231257827021181583404541015625`, and a system that quietly
    accepts that has a rounding bug it will never find. Doctrine rule 3: nothing is
    invented, and silently repairing a caller's representation is inventing.
    """
    if isinstance(value, float):  # pragma: no cover - the type checker refuses it first
        raise MoneyError(
            "a binary float is not an amount of money. Pass a Decimal, an int of cents, or "
            "a string such as '1.99'. See holdout.core.money."
        )
    if isinstance(value, Decimal):
        return value
    return Decimal(value)


def _quantise(value: Decimal | int | str, rounding: str) -> int:
    with localcontext() as context:
        context.prec = PRECISION
        return int(_exact(value).quantize(ONE_CENT, rounding=rounding))


@dataclass(frozen=True, slots=True, order=True)
class Money:
    """An amount in euro cents. Negative is meaningful — a margin can be negative."""

    cents: int

    def __post_init__(self) -> None:
        if isinstance(self.cents, bool) or not isinstance(self.cents, int):
            raise MoneyError(
                f"Money holds an integer number of cents, not {type(self.cents).__name__}. "
                "Use Money.of('1.99') or one of the rounding constructors."
            )

    # ------------------------------------------------------------------ construction

    @classmethod
    def of(cls, amount: Decimal | int | str) -> Money:
        """An amount in euros that is already exact at cent scale.

        Refuses anything with a third decimal place instead of rounding it. A caller who
        writes `Money.of('1.005')` has not decided what they meant, and picking for them is
        how a half-cent difference enters a system that compares as integers.
        """
        value = _exact(amount)
        scaled = value.scaleb(2)
        if scaled != scaled.to_integral_value():
            raise MoneyError(
                f"{value} is not an exact number of cents. Round it deliberately with "
                "Money.as_price, Money.as_lower_bound or Money.as_upper_bound, so that the "
                "direction is written down."
            )
        return cls(int(scaled))

    @classmethod
    def as_price(cls, cents: Decimal | int | str) -> Money:
        """Round a number of cents half-to-even: the metric contract's declared mode."""
        return cls(_quantise(cents, ROUND_HALF_EVEN))

    @classmethod
    def as_lower_bound(cls, cents: Decimal | int | str) -> Money:
        """Round a number of cents up. A floor never rounds down into what it forbids."""
        return cls(_quantise(cents, ROUND_CEILING))

    @classmethod
    def as_upper_bound(cls, cents: Decimal | int | str) -> Money:
        """Round a number of cents down. A ceiling never rounds up into what it forbids."""
        return cls(_quantise(cents, ROUND_FLOOR))

    # ------------------------------------------------------------------ arithmetic

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.cents + other.cents)

    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.cents - other.cents)

    def __neg__(self) -> Money:
        return Money(-self.cents)

    def times(self, factor: Decimal | int | str) -> Decimal:
        """This amount multiplied by a quantity, as an exact `Decimal` number of cents.

        Deliberately *not* a `Money`. A price times a forecast quantity is not yet an amount
        anybody is charged, and forcing the caller to name the rounding when it becomes one
        is the point: `Money.as_price(unit.times(qty))` says which way it went.
        """
        with localcontext() as context:
            context.prec = PRECISION
            return Decimal(self.cents) * _exact(factor)

    def pct(self, percent: Decimal | int | str) -> Decimal:
        """This amount scaled by a percentage, as an exact `Decimal` number of cents."""
        with localcontext() as context:
            context.prec = PRECISION
            return Decimal(self.cents) * _exact(percent) / Decimal(100)

    # ------------------------------------------------------------------ presentation

    @property
    def euros(self) -> Decimal:
        """The amount in euros, exactly. A `Decimal`, never a float."""
        return Decimal(self.cents).scaleb(-2)

    def __str__(self) -> str:
        return f"{self.euros:.2f} EUR"

    def __repr__(self) -> str:
        return f"Money.of('{self.euros:.2f}')"

    def __format__(self, spec: str) -> str:
        return format(str(self), spec)

    # `Money` deliberately defines neither `__float__` nor `__index__`, so `float(price)`
    # is already a `TypeError` at the first adapter that reaches for a float because a
    # chart library wanted one. Defining `__float__` to raise would have been worse: it
    # would make the call type-check.


ZERO = Money(0)
