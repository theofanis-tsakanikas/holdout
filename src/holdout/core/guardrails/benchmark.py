"""The margin cap's benchmark, and the denominator it is in.

Why a type and not a number
---------------------------
A gross margin can be written two ways and both are called "the margin":

* **over the selling price** — `(price - cost) / price`. This is the denominator
  ΥΑ 21330/2026 άρθρο 4 παρ. 4 defines the capped margin in, and the denominator every
  published retail figure this project cites is in;
* **over the cost** — `(price - cost) / cost`, a mark-up. This is the denominator the
  envelope's arithmetic is in, because it bounds the price at `cost + cost x pct`.

They are the same constraint and `m / (1 - m)` converts exactly between them. They are not
the same number: a margin of 16.81% of the price is a mark-up of 20.21% of the cost. An
independent corpus found the ambiguity by reading the instrument rather than the contract,
and the shape of the mistake it makes possible is a caller taking the instrument's published
figure and handing it straight to a field that will treat it as a mark-up — applying 16.81%
where 20.21% was meant. That fails *safe*, in that the cap comes out stricter than the law
requires. It is still a wrong number, arrived at silently.

A comment saying which denominator the field is in would have been read by whoever already
knew. So the denominator is carried in the type: `MarginOnPrice` is what an instrument
publishes, `MarkupOnCost` is what the envelope needs, and the only route from the first to
the second is a conversion that has to be written down. `ProposedPrice` accepts a
`MarkupOnCost` and refuses a bare number at runtime as well as in the annotation, because a
bare number is exactly the shape the mistake arrives in.

The one thing this cannot do is know which denominator a *contract* value is in.
`contracts/guardrails/regulated_basket.yaml` names its benchmark `average_gross_margin_2025`
and the instrument that defines that quantity defines it over the price; naming the
denominator there is a contract change with a restatement attached, and it is deferred in
`docs/DECISIONS.md` rather than made here. What this type closes is the half between a
number arriving and a bound being computed from it.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext

from holdout.core.money import PRECISION

HUNDRED = Decimal(100)


class BenchmarkError(ValueError):
    """A benchmark margin that names no denominator, or one that cannot have one."""


def _percentage(value: Decimal, what: str) -> Decimal:
    # A `float` falls into the same refusal as anything else that is not a `Decimal`, and
    # for the reason `holdout.core.money` gives at length: 16.81 is not representable in
    # binary, and a cap computed from a value that is a fraction off is a cap nobody can
    # reproduce. `bool` is an `int` and an `int` is not a `Decimal`, so both are refused
    # here without a special case.
    if not isinstance(value, Decimal):
        raise BenchmarkError(
            f"{what} is a Decimal percentage, not {type(value).__name__}. A binary float "
            "cannot represent most of them exactly; see holdout.core.money."
        )
    # `Decimal` carries `Infinity` and `NaN`, and neither is a percentage. Without this an
    # infinite mark-up passed every check here and became a `decimal.InvalidOperation` three
    # modules later, inside the envelope's rounding — a crash where the contract of this
    # layer is a refusal. `NaN` is worse: it compares false against everything, so `< 0`
    # waved it through. Checked before the sign test for that reason.
    if not value.is_finite():
        raise BenchmarkError(
            f"{what} is a finite percentage; {value} is not a number this can bound a price "
            "with. Doctrine rule 3: nothing is invented, and a bound computed from an "
            "infinity is not a bound."
        )
    if value < 0:
        raise BenchmarkError(f"{what} is not negative; {value} was supplied")
    return value


@dataclass(frozen=True, slots=True)
class MarkupOnCost:
    """A percentage **of the cost**, added to the cost. The envelope's own denominator.

    `MarkupOnCost(Decimal("20.21"))` bounds the price at `cost x 1.2021`.
    """

    pct: Decimal

    def __post_init__(self) -> None:
        _percentage(self.pct, "a mark-up on cost")

    def __str__(self) -> str:
        return f"{self.pct}% of cost"


@dataclass(frozen=True, slots=True)
class MarginOnPrice:
    """A percentage **of the selling price**. What an instrument or a statistic publishes.

    The envelope never takes one of these. `as_markup_on_cost` is the only way through, and
    it is a named call in a diff somebody reads.
    """

    pct: Decimal

    def __post_init__(self) -> None:
        value = _percentage(self.pct, "a margin on price")
        if value >= HUNDRED:
            raise BenchmarkError(
                f"a margin of {value}% of the selling price leaves no cost to mark up: "
                "m / (1 - m) is undefined at 100% and negative above it. Nothing is invented."
            )

    def as_markup_on_cost(self) -> MarkupOnCost:
        """`m / (1 - m)`, exactly — the same constraint in the denominator the envelope uses.

        Computed at the precision `money` declares, so a conversion never introduces a
        difference that a later comparison as integers would have to tolerate.
        """
        with localcontext() as context:
            context.prec = PRECISION
            return MarkupOnCost(self.pct / (HUNDRED - self.pct) * HUNDRED)

    def __str__(self) -> str:
        return f"{self.pct}% of the selling price"
