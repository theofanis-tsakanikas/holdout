"""Rounding a bound to the cent, computed here — and why it is not `Money`'s.

The defect this module exists to close
--------------------------------------
`reference.py` calls itself a second implementation of the envelope's arithmetic. It was
one, for the arithmetic; it was not one for the **rounding**, because the eval's own floor
was obtained by calling `Money.as_lower_bound` — the very primitive the core uses. Patch
that primitive and the eval's bound moved with it, so on the one check that used it the core
and the eval agreed on a wrong number. `CLAUDE.md` names the class of defect and this is its
fourth instance:

> **A guard tested by its author is tested in the shape the guard already handles.**

So the direction — floors up, ceilings down — is *re-decided* here from the contract's own
statement of it, and the arithmetic that carries it out shares nothing with the core's:

============  ====================================  ==============================
              `holdout.core.money`                   here
============  ====================================  ==============================
carrier       `Decimal`, at a declared precision      the value's exact integer
              of 34 significant digits                ratio — two `int`s, and no
                                                      precision to declare
mechanism     `quantize(ONE_CENT, ROUND_CEILING)`     integer floor division of a
              / `ROUND_FLOOR`                         numerator by a denominator
failure mode  a value with more than 34 significant   none available: an `int` has
              digits is rounded before it is          no rounding step to get
              quantised                               wrong
============  ====================================  ==============================

The rational was not chosen because it is nicer. It was chosen because it is the one
representation available that **cannot** share a bug with `Decimal`: there is no precision,
no context and no quantisation, so a defect in any of those cannot cancel out between the
two. `as_integer_ratio` is exact on `Decimal`, on `Fraction` and on `int` — it is the same
pair `Fraction` would have been built from — and after it there is nothing here but integer
floor division, which is the whole implementation.

What was actually invisible, measured rather than asserted
----------------------------------------------------------
An earlier draft of this docstring said that patching `Money.as_lower_bound` left every
check green. That is false, and it was written without being run — which is the same defect
one level up, in the layer that is supposed to *be* the evidence. Planted against `main`:

    main, unmutated      G2 pass · 0 violations in 28,482 certified prices
    main + half-even     G2 FAIL · 199 violations in 28,681 certified prices
                         G3 pass · G4 pass · G6 pass, its published ceiling
                                   count moving 7,366 -> 7,365 in silence

`G2` compares a certified price against `reference`'s **exact** `Decimal` bound, which never
went through `Money`'s rounding at all, so `G2` was never blind to this. The check that
shared the primitive was `G6`, through `_exact_floor` — and `G6` stayed green while the
number it publishes moved. That is the real finding: an order of magnitude smaller than the
one first written down, and still a check agreeing with itself.

What this still does not prove, said plainly
--------------------------------------------
Both implementations were written in this repository, so agreement between them is not
independence in the strong sense claim 1's corpus has. What it is, is *non-shared*: **no line
of the core's rounding** runs when this module places a bound, so a change to it shows up as
a disagreement instead of as silence. Not "no line of the core" — `Money.euros` produced the
input and `Money.__post_init__` runs on the way out; the claim is about the rounding
decision, which is made here and nowhere else. That is the property the eval lost and this
module gives back, and `make gate-proof` plants a break in `Money.as_lower_bound` itself and
demands a named check refuse it.

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
    numerator, denominator = euros.as_integer_ratio()
    return -(-numerator * CENTS_PER_EURO // denominator)


def ceiling_cents(euros: Decimal | Fraction | int) -> int:
    """An upper bound in euros, as the largest whole number of cents that is **not above** it.

    The same argument in the other direction: a ceiling that rounds up admits a price the
    rule forbids.
    """
    numerator, denominator = euros.as_integer_ratio()
    return numerator * CENTS_PER_EURO // denominator


def as_floor(euros: Decimal | Fraction | int) -> Money:
    """`floor_cents`, carried in the type the rest of the eval passes around."""
    return Money(floor_cents(euros))


def as_ceiling(euros: Decimal | Fraction | int) -> Money:
    """`ceiling_cents`, carried in the type the rest of the eval passes around."""
    return Money(ceiling_cents(euros))
