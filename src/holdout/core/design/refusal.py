"""A design that may not exist, and why — returned, never raised.

The shape `holdout.core.guardrails.certificate.Refusal` already sets, one moment along: a
refusal is a **correct output**, not an error. It is returned because a caller records a
refusal rather than handling it — it goes to the experiment register, to the readout screen
at the same size as an uplift, and to claim 6's count.

Every fired code is carried, not only the leading one. The precedence in
`codes.DESIGN_PRECEDENCE` decides which one leads and nothing else, so the ordering can
never lose a code from the count — the same rule the decision-time refusal follows, for the
same reason.

**A refusal names what would fix it.** Even where the honest answer is "nothing, for this
experiment". Without that the engine is an obstacle rather than a design partner, and the
contract's `what_would_fix_it` field would be a string nobody reads.
"""

from __future__ import annotations

from dataclasses import dataclass

from holdout.core.design.codes import (
    DESIGN_PRECEDENCE,
    JUDGMENT_REFUSALS,
    SCOPE_REFUSALS,
    DesignRefusalCode,
)

_PRECEDENCE_INDEX = {code: index for index, code in enumerate(DESIGN_PRECEDENCE)}


@dataclass(frozen=True, slots=True)
class DesignRefusalReason:
    """One check's answer of no, named precisely enough to count and to fix."""

    code: DesignRefusalCode
    detail: str
    what_would_fix_it: str

    def __post_init__(self) -> None:
        if not self.detail or not self.what_would_fix_it:
            raise ValueError(
                "a design refusal states what happened and what would fix it. A refusal "
                "with neither cannot be acted on, and one with no remedy is an obstacle."
            )

    @property
    def is_scope(self) -> bool:
        """Decided by a declared list or assumption, with no judgment inspected."""
        return self.code in SCOPE_REFUSALS

    def __str__(self) -> str:
        return f"{self.code.value}: {self.detail}"


@dataclass(frozen=True, slots=True)
class DesignRefusal:
    """The experiment does not happen, and every reason it does not."""

    experiment_id: str
    reasons: tuple[DesignRefusalReason, ...]

    def __post_init__(self) -> None:
        if not self.reasons:
            raise ValueError(
                "a refusal names at least one reason. A refusal with none cannot be "
                "counted, tested or gated, which is the whole point of a closed vocabulary."
            )
        # Ordered here rather than by whoever assembled it, so `code` is the same for the
        # same set of reasons no matter which check happened to run first. Reordering
        # `assess` must not move the leading code.
        object.__setattr__(
            self,
            "reasons",
            tuple(sorted(self.reasons, key=lambda r: (_PRECEDENCE_INDEX[r.code], r.detail))),
        )

    @property
    def code(self) -> DesignRefusalCode:
        """The leading code, by the precedence declared in `codes.DESIGN_PRECEDENCE`."""
        return self.reasons[0].code

    @property
    def codes(self) -> tuple[DesignRefusalCode, ...]:
        return tuple(r.code for r in self.reasons)

    @property
    def scope_codes(self) -> tuple[DesignRefusalCode, ...]:
        """Refused by a declared envelope. Never counted into claim 6's K."""
        return tuple(c for c in self.codes if c in SCOPE_REFUSALS)

    @property
    def judgment_codes(self) -> tuple[DesignRefusalCode, ...]:
        """Refused by arithmetic over what the proposer declared — the only kind of refusal
        that can be a design which would have produced a confidently wrong number."""
        return tuple(c for c in self.codes if c in JUDGMENT_REFUSALS)

    @property
    def is_scope_only(self) -> bool:
        """Nothing the proposer weighed was inspected.

        A report that added this refusal to a judgment one would be counting as *caught* a
        design whose judgment nothing ever looked at.
        """
        return not self.judgment_codes

    def what_would_fix_it(self) -> tuple[str, ...]:
        """Every remedy, in the order the codes are reported, deduplicated."""
        seen: list[str] = []
        for reason in self.reasons:
            if reason.what_would_fix_it not in seen:
                seen.append(reason.what_would_fix_it)
        return tuple(seen)

    def __str__(self) -> str:
        return f"REFUSED {self.code.value} ({self.experiment_id}) — {self.reasons[0].detail}"
