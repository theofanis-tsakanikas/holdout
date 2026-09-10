"""What the agent may produce, as a type that is not a design.

`CLAUDE.md`: **the agent proposes how we will find out. Never what we will do once we know.**
Two of the nine fields carry `# the agent never fills this` in the form it names —
`max_duration`, a business constraint, and `decision_rule`, what happens to each outcome.

**So this is a different type, not a form with two fields validated.** A validator that
refused an agent-filled `decision_rule` would be a check somebody can forget to call, and the
first thing a hurried caller does with a check is skip it. `ProposedDesign` carries seven
fields and has no place to put the other two; the only route from here to a `DesignForm` is
`complete()`, which takes them as arguments from whoever is running the agent. **The rule is
structural rather than asserted**, which is the same move `guardrails` makes with
`ProposedPrice -> CertifiedPrice | Refusal`: the function that actuates accepts only the
certified type, so there is no path that forgets to certify.

What `complete()` does not do
-----------------------------
It does not check the design. Feasibility, the exclusions, the power calculation and the
eight refusal codes all live in `holdout.core.design` and are reached the same way for all
three sources — the whole content of claim 6 is that the engine cannot tell who filled the
form, so this module must not become a second place where an agent-filled design is treated
differently.

Attribution, and the one thing it loses
---------------------------------------
The completed form is stamped `filled_by: agent`, because the judgment fields are the agent's
and those are what a design *is*. Who supplied the two constraint fields is recorded on the
proposal rather than on the form: the schema counts nine fields and one attribution, and a
tenth would be a contract change with a restatement chain behind it. `supplied_by` is
therefore part of the record of a run and not part of the design's identity, and that is a
decision rather than an omission.
"""

from __future__ import annotations

from dataclasses import dataclass

from holdout.core.design.form import (
    DecisionRule,
    DesignForm,
    Exclusion,
    FilledBy,
    FilledByKind,
    Intervention,
    MaxDuration,
    Mde,
    Scope,
    Unit,
)


class ProposalError(ValueError):
    """The agent produced something that is not a proposal.

    An error, not a refusal — the split `form.py` already draws and for the reason it draws
    it: claim 6 counts refusals, and an unparseable answer counted as a refusal would inflate
    M with things that were never designs. A model that returns prose where a metric id
    belongs has not refused a design; it has failed to make one.
    """


@dataclass(frozen=True, slots=True)
class ProposedDesign:
    """The seven fields the agent may fill.

    Frozen, like everything the engine reads, so a proposal cannot be edited between being
    made and being graded.
    """

    hypothesis: str
    intervention: Intervention
    scope: Scope
    primary_metric: str
    unit: Unit
    mde: Mde
    exclusions: tuple[Exclusion, ...]

    def complete(
        self,
        *,
        max_duration: MaxDuration,
        decision_rule: DecisionRule,
    ) -> DesignForm:
        """The only route from a proposal to a design, and it requires the two missing fields.

        Both arguments are keyword-only and neither has a default. A default here would be
        this module answering a question `CLAUDE.md` says the agent may not answer, which is
        worse than the validator it replaces: it would be silent.
        """
        return DesignForm(
            hypothesis=self.hypothesis,
            intervention=self.intervention,
            scope=self.scope,
            primary_metric=self.primary_metric,
            unit=self.unit,
            mde=self.mde,
            max_duration=max_duration,
            exclusions=self.exclusions,
            decision_rule=decision_rule,
            filled_by=FilledBy(kind=FilledByKind.AGENT),
        )
