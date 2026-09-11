"""The power boundary, computed a second way, so the engine does not mark its own paper.

`feasibility.assess` refuses a design as underpowered by searching the windows from one week
to fifty-two for the shortest one whose required sample fits the binding arm, in exact
`Fraction` arithmetic with a ceiling at the end. Driving designs through it answers *does it
refuse*. It does not answer *at the right place*, and if the only thing that knows where the
boundary is is the code under test, the check is a function agreeing with itself.

So the boundary is computed here **differently everywhere it is allowed to be**:

| | the engine | this reference |
|---|---|---|
| arithmetic | exact `Fraction` | `Decimal` at fifty digits, with the rounding named |
| the window | searched, 1 to 52, first fit wins | **solved**: the smallest W with `n(W) <= capacity` is `ceil(2 z² s² / (cap · d²))`, and it is checked by evaluating `n` at W and at W - 1 |
| the verdict | three codes assembled in one pass | three predicates, each evaluated on its own |
| the capacity | `_capacity`, the smaller arm | recomputed from the share as a floor, and the smaller arm taken explicitly |

What the two sides share, stated: the contract's `z_alpha` and `z_power`, which are declared
values, and the definition of the MDE in cents, which is the contract's too. Not the search,
not the ceiling, not the capacity function. **The normal quantile is not recomputed here** —
`z_alpha` is the contract's method and this eval takes it as a declared value — and that is
the one place the two implementations lean on the same code, said out loud rather than hidden.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, localcontext
from fractions import Fraction

from holdout.contracts.model import InferenceSettings
from holdout.core.design.form import DesignForm, MdeKind

HORIZON_WEEKS = 52
ARMS = 2


@dataclass(frozen=True, slots=True)
class Boundary:
    """Where this reference puts the power boundary for one design."""

    available: int
    binding_arm: int
    mde_cents: Decimal
    shortest_weeks: int | None  # None: no window up to the horizon fits
    required_at_shortest: int | None
    refuses_capacity: bool
    refuses_duration: bool

    @property
    def refuses(self) -> bool:
        return self.refuses_capacity or self.refuses_duration


def boundary(
    form: DesignForm,
    *,
    inference: InferenceSettings,
    available: int,
    variance_cents2: Decimal,
    mean_cents: Decimal,
) -> Boundary:
    """The three predicates, each from its own arithmetic."""
    with localcontext() as ctx:
        ctx.prec = 50
        share = Decimal(inference.holdout_share_pct) / Decimal(100)
        control = int((Decimal(available) * share).to_integral_value(rounding=ROUND_FLOOR))
        binding = min(control, available - control)

        if form.mde.kind is MdeKind.ABSOLUTE:
            mde = Decimal(form.mde.value)
        else:
            mde = mean_cents * Decimal(form.mde.value) / Decimal(100)

        z = Decimal(inference.z_alpha(two_sided=form.mde.is_two_sided)) + Decimal(inference.z_power)
        # n(W) = ceil(2 z² s² / (W d²)); the smallest W with n(W) <= cap solves
        # 2 z² s² / (W d²) <= cap  =>  W >= 2 z² s² / (cap d²).
        constant = Decimal(ARMS) * z * z * variance_cents2 / (mde * mde)
        if binding <= 0:
            return Boundary(
                available=available,
                binding_arm=binding,
                mde_cents=mde,
                shortest_weeks=None,
                required_at_shortest=None,
                refuses_capacity=True,
                refuses_duration=True,
            )
        solved = int((constant / Decimal(binding)).to_integral_value(rounding=ROUND_CEILING))
        shortest = max(1, solved)

        def required(weeks: int) -> int:
            return int((constant / Decimal(weeks)).to_integral_value(rounding=ROUND_CEILING))

        # The solution is checked rather than trusted: n at W fits, n at W - 1 does not.
        if required(shortest) > binding:
            raise ArithmeticError(
                f"the solved window {shortest} does not fit: n={required(shortest)} > {binding}"
            )
        if shortest > 1 and required(shortest - 1) <= binding:
            raise ArithmeticError(
                f"the window before the solved one fits too: n({shortest - 1})="
                f"{required(shortest - 1)} <= {binding}"
            )

        beyond_horizon = shortest > HORIZON_WEEKS
        return Boundary(
            available=available,
            binding_arm=binding,
            mde_cents=mde,
            shortest_weeks=None if beyond_horizon else shortest,
            required_at_shortest=None if beyond_horizon else required(shortest),
            refuses_capacity=beyond_horizon,
            refuses_duration=beyond_horizon or shortest > form.max_duration.weeks,
        )


def as_fraction(value: Decimal) -> Fraction:
    return Fraction(value)
