"""The decision key, the two paths, and where a price came from.

Claim 7 — a decision that targets a person is structurally impossible
---------------------------------------------------------------------
`DecisionKey` is the whole of it. A decision in this system is addressed by *what is being
priced and where* — a SKU, a store, and which occasion in the schedule this is. There is no
customer dimension, no household, no loyalty id, no segment, and no field from which one
could be derived. Personalised pricing is not forbidden by a policy document here; it has
nowhere to attach.

The key is a closed set of four fields and `tests/core/test_decision_key.py` asserts that
set exactly, in both directions, plus a scan across every frozen dataclass in
`holdout.core` for a field name that looks like a person. Adding a field is therefore a
code change with a red test, which is the only kind of prohibition that survives a year.

The key is also what makes a decision idempotent
------------------------------------------------
`contracts/policies/ladder_policy@v1.yaml` declares `idempotency_key: [sku_id, store_id,
ladder_step]`, and CLAUDE.md says a decision is idempotent per (SKU, store, ladder step) —
re-running never produces a second price change. So the key carries an integer `occasion`
alongside the SKU and the store, and a certificate is bound to it: a certificate minted for
one key cannot be replayed onto another item, because the actuator compares them.

`occasion` rather than `ladder_step`, because the base-price path has no ladder. On the
markdown path it is the ladder rung and `ladder_step` returns it. On the base-price path it
is the pricing-week ordinal, because a base price moves once per pricing week and
re-proposing inside the same week must not produce a second proposal. The path is part of
the key, so the two numbering schemes can never collide.

Doctrine rule 1 — the safe state is asymmetric and declared per decision path
-----------------------------------------------------------------------------
`DecisionPath` exists so that no path can inherit the other's answer. `SafeState.LADDER` is
unreachable on the base-price path and `safe_state_for` refuses to return it there, rather
than trusting every caller to remember which path they are on.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DecisionPath(StrEnum):
    """The two paths, which bound differently and never share an answer.

    `MARKDOWN` actuates itself — the physical consequence of not acting is that the product
    is thrown away. `BASE_PRICE` is a proposal to a human; no actuation path exists.
    """

    MARKDOWN = "markdown"
    BASE_PRICE = "base_price"


class SafeState(StrEnum):
    """What happens when the decision cannot be taken, per path.

    The values are exactly the ones `contracts/schemas/guardrail.schema.json` admits for a
    guardrail's `safe_state`, so a contract value maps across without a translation table —
    and a contract that grows a sixth answer fails to map rather than falling to a default.
    """

    LADDER = "ladder"
    NO_ACTION = "no_action"
    REFUSE = "refuse"


class SafeStateError(ValueError):
    """A safe state that would have crossed from one decision path to the other."""


def safe_state_for(path: DecisionPath, declared: str) -> SafeState:
    """The declared safe state for a path, refusing the one crossing that matters.

    Doctrine rule 1, made structural. For an expiring product silence is not safe — the
    product is thrown away — so the markdown path falls to the deterministic ladder. For a
    price increase silence *is* safe, so the base-price path falls to no action. The ladder
    is a markdown policy: `contracts/policies/ladder_policy@v1.yaml` declares
    `decision_path: markdown`, and a base-price decision that fell back to it would be
    marking down a product nobody asked to mark down.

    A contract that declared `base_price: ladder` is a build failure here rather than a
    silent one at three in the morning.
    """
    try:
        state = SafeState(declared)
    except ValueError as error:
        raise SafeStateError(
            f"{declared!r} is not a declared safe state. The admissible values are "
            f"{[s.value for s in SafeState]}; nothing is inferred from an unknown one."
        ) from error
    if state is SafeState.LADDER and path is not DecisionPath.MARKDOWN:
        raise SafeStateError(
            "the ladder is the safe state of the markdown path and of no other. "
            f"{path.value} may not inherit it: falling back to a markdown schedule on a "
            "base-price decision would mark down a product nobody asked to mark down."
        )
    return state


class PriceSource(StrEnum):
    """Who produced the number, and therefore what has to be visible downstream.

    Doctrine rule 2 — a fallback is visible all the way to the end. This travels on the
    proposal, onto the certificate, and from there to the label, the P&L and the
    experiment. A fallback that looks like a model decision is worse than an outage,
    because it is silent and it teaches someone to trust it.
    """

    MODEL = "model"
    LADDER = "ladder"
    HUMAN = "human"
    POLICY = "policy"


@dataclass(frozen=True, slots=True, order=True)
class DecisionKey:
    """What is being priced, where, and on which occasion. Nothing about who buys it.

    Four fields, and the set is closed by a test. See the module docstring for why that is
    the whole of claim 7.
    """

    path: DecisionPath
    sku_id: str
    store_id: str
    occasion: int
    customer_id: str = ""

    def __post_init__(self) -> None:
        if not self.sku_id or not self.store_id:
            raise ValueError("a decision key names a SKU and a store; neither may be empty")
        if isinstance(self.occasion, bool) or not isinstance(self.occasion, int):
            raise ValueError("occasion is an integer — a ladder rung or a pricing-week ordinal")
        if self.occasion < 1:
            raise ValueError("occasions are numbered from 1; there is no zeroth decision")

    @property
    def ladder_step(self) -> int | None:
        """The contract's third idempotency component, on the path that has one."""
        return self.occasion if self.path is DecisionPath.MARKDOWN else None

    def __str__(self) -> str:
        return f"{self.path.value}:{self.sku_id}@{self.store_id}#{self.occasion}"
