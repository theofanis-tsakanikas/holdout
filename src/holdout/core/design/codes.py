"""The closed refusal vocabulary of the design moment.

The third place, exactly as `holdout.core.guardrails.codes` is for the decision moment: the
set lives in `contracts/schemas/reason_codes.schema.json`, the meanings live in
`contracts/vocabularies/reason_codes.yaml`, and this enum is the one the engine branches
on. `tests/core/test_refusal_codes.py` asserts all three agree in both directions.

Three mechanisms and not two, for the reason the decision-time twin gives: a core that read
the vocabulary out of the contract at runtime would need the parser, which is the one thing
`holdout.core` may not have; and free-text reasons would make claim 6's "N proposed, M
refused, K would have been wrong" impossible to count.

Scope refusals and judgment refusals
------------------------------------
Two of the four units of randomisation are refused **by construction**, before any judgment
has been exercised on anything — see `contracts/design/inference.yaml`'s `carryover:` block
and the deferral in `docs/DECISIONS.md`. So a single aggregate "M refused" would be two
different numbers added together, and adding them flatters the engine while defaming the
proposer: it counts as *caught* a design whose judgment nothing ever inspected, and charges
the proposer with an error it did not make.

The criterion, written down here because this is where the split is created:

* a **scope** refusal is decided by a declared list or a declared assumption, with no
  arithmetic over anything the proposer weighed. Every proposer gets the same answer for
  the same input, and no judgment was inspected;
* a **judgment** refusal is decided by arithmetic over what the proposer actually declared —
  the MDE, the duration, the exclusions, the stopping rule, the scope it chose.

**Only a judgment refusal can be a design that would have produced a confidently wrong
number**, so only a judgment refusal may be counted into claim 6's K. A scope refusal
counted into K would be evidence of a catch that never happened.

One of the eight is genuinely arguable and is resolved here rather than left to whoever
reports it. `UNITS_ALREADY_COMMITTED` is filed as **scope**: it is decided by which units
other, still-open experiments hold, which is a fact about the estate at the moment of
asking and not something the proposer could necessarily see. A reader who would file it the
other way has a case; what matters is that it is filed once, in one place, and not decided
differently by each consumer.
"""

from __future__ import annotations

from enum import StrEnum


class DesignRefusalCode(StrEnum):
    """Why the engine would not let an experiment exist. Closed; see the module docstring."""

    UNDERPOWERED_FOR_DURATION = "UNDERPOWERED_FOR_DURATION"
    UNDERPOWERED_FOR_CAPACITY = "UNDERPOWERED_FOR_CAPACITY"
    UNIT_GUARANTEES_INTERFERENCE = "UNIT_GUARANTEES_INTERFERENCE"
    STOPPING_RULE_PERMITS_PEEKING = "STOPPING_RULE_PERMITS_PEEKING"
    EXCLUSIONS_DEFINED_POST_HOC = "EXCLUSIONS_DEFINED_POST_HOC"
    METRIC_NOT_IN_CONTRACT = "METRIC_NOT_IN_CONTRACT"
    UNITS_ALREADY_COMMITTED = "UNITS_ALREADY_COMMITTED"
    NO_ADMISSIBLE_ASSIGNMENT = "NO_ADMISSIBLE_ASSIGNMENT"


#: Decided by a declared list or a declared assumption. Nothing the proposer weighed was
#: inspected, so none of these may be counted into claim 6's K.
SCOPE_REFUSALS: frozenset[DesignRefusalCode] = frozenset(
    {
        DesignRefusalCode.UNIT_GUARANTEES_INTERFERENCE,
        DesignRefusalCode.METRIC_NOT_IN_CONTRACT,
        DesignRefusalCode.UNITS_ALREADY_COMMITTED,
    }
)

#: Decided by arithmetic over what the proposer declared. These are the ones a judgment can
#: get wrong, and therefore the only ones claim 6's K may draw from. Derived rather than
#: written out, so the two sets can never overlap or leave a code in neither.
JUDGMENT_REFUSALS: frozenset[DesignRefusalCode] = frozenset(DesignRefusalCode) - SCOPE_REFUSALS


#: The precedence in which simultaneous refusals are reported. It decides only which code
#: leads a `DesignRefusal`; every code that fired is carried, so nothing is lost to the
#: ordering and claim 6's count is over all of them.
#:
#: The order is "how far the design got before it stopped". A metric outside the contract
#: stops the form from meaning anything at all; a unit that guarantees interference stops it
#: before any sample is worth computing; a stopping rule that permits peeking invalidates the
#: procedure whatever the arithmetic says; an exclusion set that moved is already using the
#: outcome. Only then does the sizing arithmetic have anything to say — and the lottery, which
#: is the last thing attempted, refuses last.
DESIGN_PRECEDENCE: tuple[DesignRefusalCode, ...] = (
    DesignRefusalCode.METRIC_NOT_IN_CONTRACT,
    DesignRefusalCode.UNIT_GUARANTEES_INTERFERENCE,
    DesignRefusalCode.STOPPING_RULE_PERMITS_PEEKING,
    DesignRefusalCode.EXCLUSIONS_DEFINED_POST_HOC,
    DesignRefusalCode.UNITS_ALREADY_COMMITTED,
    DesignRefusalCode.UNDERPOWERED_FOR_CAPACITY,
    DesignRefusalCode.UNDERPOWERED_FOR_DURATION,
    DesignRefusalCode.NO_ADMISSIBLE_ASSIGNMENT,
)
