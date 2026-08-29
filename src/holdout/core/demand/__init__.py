"""Demand, read off a shelf that sometimes ran out — claim 4.

`CLAUDE.md`: *a stock-out is never read as zero demand.* One module, and the whole of it is
the difference between two sentences about the same store-day:

    the shelf sold 11 units          -> demand was 11
    the shelf sold 11 units and      -> demand was **at least** 11, and the day is not
    emptied at 16:00                    a day anybody may average

The first sentence is what a `GROUP BY` produces, and it is wrong in one direction only: it
understates. A model trained on it learns that the busiest store-days are the quiet ones,
orders less for them, empties the shelf earlier, and confirms itself. That loop is the reason
the claim exists.

What is here
------------
=====================  =========================================================
`censoring`            the reading, the availability curve, and the correction
=====================  =========================================================

Nothing in this package knows what a margin is, what an arm is, or that an experiment exists.
It is arithmetic over integer unit counts and exact `Fraction` shares, like everything else
under `holdout.core`.
"""
