"""The closed refusal vocabulary of the decision path.

The set lives in `contracts/schemas/reason_codes.schema.json`, the meanings live in
`contracts/vocabularies/reason_codes.yaml`, and this enum is the third place — the one the core
actually branches on. `tests/core/test_refusal_codes.py` asserts all three agree exactly,
in both directions, and it fails on a code added to any one of them alone.

Three mechanisms and not two, deliberately. A core that read the vocabulary out of the
contract at runtime would need the parser, which is the one thing `holdout.core` may not
have; and a core that simply used free-text strings would make claim 1's evidence — *which
guardrails fired, how often* — impossible to count. So the enum is written out, and the
test is what keeps it honest.
"""

from __future__ import annotations

from enum import StrEnum


class RefusalCode(StrEnum):
    """Why the envelope would not certify a price. Closed; see the module docstring."""

    CATEGORY_FROZEN = "CATEGORY_FROZEN"
    COST_STALE = "COST_STALE"
    BELOW_ABSOLUTE_FLOOR = "BELOW_ABSOLUTE_FLOOR"
    BELOW_MARGIN_FLOOR = "BELOW_MARGIN_FLOOR"
    NO_PRICE_SATISFIES_EVERY_GUARDRAIL = "NO_PRICE_SATISFIES_EVERY_GUARDRAIL"
    MARKDOWN_EXCEEDS_MAX_DEPTH = "MARKDOWN_EXCEEDS_MAX_DEPTH"
    DAILY_CHANGE_BUDGET_EXHAUSTED = "DAILY_CHANGE_BUDGET_EXHAUSTED"
    BASE_PRICE_MOVE_EXCEEDS_WEEKLY_LIMIT = "BASE_PRICE_MOVE_EXCEEDS_WEEKLY_LIMIT"
    MARGIN_CAP_EXCEEDED = "MARGIN_CAP_EXCEEDED"
    MARGIN_CAP_BASIS_UNEVALUABLE = "MARGIN_CAP_BASIS_UNEVALUABLE"
    PRIOR_PRICE_NOT_ESTABLISHED = "PRIOR_PRICE_NOT_ESTABLISHED"
    INPUT_NOT_AVAILABLE = "INPUT_NOT_AVAILABLE"


class GuardrailId(StrEnum):
    """The five contracts that make up the envelope, by the `id` each file declares."""

    FLOOR = "floor"
    REGULATED_BASKET = "regulated_basket"
    PRIOR_PRICE = "prior_price"
    MAX_DELTA = "max_delta"
    FROZEN_CATEGORIES = "frozen_categories"


#: A declared order over the five guardrails, used wherever two of them would otherwise
#: tie: which bound binds when two land on the same cent, and which refusal leads when two
#: carry the same code. Both of those decide something real — the second decides the safe
#: state a caller acts on — so neither may fall to the order the checks happen to be
#: written in inside `evaluate`. Reordering that function must not move a safe state.
#:
#: The order is how early in a decision each guardrail has anything to say: whether the
#: path is entered at all, then whether the cost can be trusted, then the two envelopes
#: that bound the price, then what may be printed on the label.
GUARDRAIL_ORDER: tuple[GuardrailId, ...] = (
    GuardrailId.FROZEN_CATEGORIES,
    GuardrailId.FLOOR,
    GuardrailId.REGULATED_BASKET,
    GuardrailId.MAX_DELTA,
    GuardrailId.PRIOR_PRICE,
)


#: The precedence in which simultaneous refusals are reported. It decides only which code
#: leads a `Refusal`; every code that fired is carried, so nothing is lost to the ordering
#: and claim 1's count is over all of them.
#:
#: The order is "how far the decision got before it stopped". A frozen category stops the
#: path before the model is called at all; a stale cost stops it before any bound can be
#: trusted; a missing input stops the rule that needed it; and only then do the arithmetic
#: bounds have anything to say.
PRECEDENCE: tuple[RefusalCode, ...] = (
    RefusalCode.CATEGORY_FROZEN,
    RefusalCode.COST_STALE,
    RefusalCode.INPUT_NOT_AVAILABLE,
    RefusalCode.MARGIN_CAP_BASIS_UNEVALUABLE,
    RefusalCode.NO_PRICE_SATISFIES_EVERY_GUARDRAIL,
    RefusalCode.DAILY_CHANGE_BUDGET_EXHAUSTED,
    RefusalCode.BELOW_ABSOLUTE_FLOOR,
    RefusalCode.BELOW_MARGIN_FLOOR,
    RefusalCode.MARGIN_CAP_EXCEEDED,
    RefusalCode.MARKDOWN_EXCEEDS_MAX_DEPTH,
    RefusalCode.BASE_PRICE_MOVE_EXCEEDS_WEEKLY_LIMIT,
    RefusalCode.PRIOR_PRICE_NOT_ESTABLISHED,
)
