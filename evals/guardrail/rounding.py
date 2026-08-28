"""Rounding a bound to the cent, computed here — and why it is not `Money`'s.

The defect this module exists to close
--------------------------------------
`reference.py` calls itself a second implementation of the envelope's arithmetic. It was
one, for the arithmetic; it was not one for the **rounding**, because the eval's own floor
was obtained by calling `Money.as_lower_bound` — the very primitive the core uses. A review
put it plainly: patch that primitive and the eval's bound moves with it, so the core and
the eval agree on a wrong number and every check that calls itself independent stays green.
`CLAUDE.md` names the class of defect and this is its fourth instance:

> **A guard tested by its author is tested in the shape the guard already handles.**

So the direction — floors up, ceilings down — is *re-decided* here from the contract's own
statement of it, and the arithmetic that carries it out shares nothing with the core's:

============  ====================================  ==============================
              `holdout.core.money`                   here
============  ====================================  ==============================
carrier       `Decimal`, at a declared precision      `Fraction`, exact by
              of 34 significant digits                construction, no precision
                                                      to declare
mechanism     `quantize(ONE_CENT, ROUND_CEILING)`     integer division of a
              / `ROUND_FLOOR`                         numerator by a denominator
failure mode  a value with more than 34 significant   none available: `Fraction`
              digits is rounded before it is          has no rounding step to get
              quantised                               wrong
============  ====================================  ==============================

`Fraction` was not chosen because it is nicer. It was chosen because it is the one
representation in the standard library that **cannot** share a bug with `Decimal`: there is
no precision, no context and no quantisation, so a defect in any of those cannot cancel out
between the two. Integer floor division is the whole implementation.

What this still does not prove, said plainly
--------------------------------------------
Both implementations were written in this repository, so agreement between them is not
independence in the strong sense claim 1's corpus has. What it is, is *non-shared*: no line
of the core runs when this module computes a bound, so a change to the core's rounding
shows up as a disagreement instead of as silence. That is the property the eval lost and
this module gives back, and it is checked by `make gate-proof`, which plants a break in
`Money.as_lower_bound` itself and demands a named check refuse it.

`Money(cents)` is constructed here, and that is not a rounding call: it is the integer the
decision above produced, wearing the type the rest of the eval passes around. The decision
— which way, at what scale — is made in this file and nowhere else.
"""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction

from holdout.core.money import Money

#: How many of the smallest unit are in one euro. Written here rather than imported,
#: because a scale imported from the thing being checked is the same mistake one level up.
CENTS_PER_EURO = 100


def floor_cents(euros: Decimal | Fraction | int) -> int:
    """A lower bound in euros, as the smallest whole number of cents that is **not below** it.

    A floor that rounds down rounds into what it forbids, so this rounds up. `-(-a // b)` is
    integer ceiling division: exact, total, and with nothing to configure.
    """
    exact = Fraction(euros) * CENTS_PER_EURO
    return -(-exact.numerator // exact.denominator)


def ceiling_cents(euros: Decimal | Fraction | int) -> int:
    """An upper bound in euros, as the largest whole number of cents that is **not above** it.

    The same argument in the other direction: a ceiling that rounds up admits a price the
    rule forbids.
    """
    exact = Fraction(euros) * CENTS_PER_EURO
    return exact.numerator // exact.denominator


def as_floor(euros: Decimal | Fraction | int) -> Money:
    """`floor_cents`, carried in the type the rest of the eval passes around."""
    return Money(floor_cents(euros))


def as_ceiling(euros: Decimal | Fraction | int) -> Money:
    """`ceiling_cents`, carried in the type the rest of the eval passes around."""
    return Money(ceiling_cents(euros))
