"""What the agent is shown, as an enumerated list rather than a directory.

**A context assembled by walking a folder is a context nobody can state.** The question this
module has to be able to answer is *what did the agent know when it proposed this*, and a
glob answers it differently on every machine and every day. So the list is written out, one
entry per thing, and `tests/agent/test_the_context_is_enumerated.py` is what refuses a
seventh that arrives without an argument beside it.

What is deliberately absent
---------------------------
**Nothing under `corpus/`, and nothing that could reach an outcome.** The corpus barrier keeps
the generator and the estimator from sharing assumptions; the same reasoning applies one layer
up and harder. *An agent that has seen the answer is not proposing a way to find it out* — and
claim 6's K, the count of refused designs that would have produced a confidently wrong number,
is meaningless if the proposer could have read the truth the seal is protecting.

Pre-period aggregates are in, and the distinction is the window
---------------------------------------------------------------
The agent is shown the mean and the dispersion of the metric over the pre-period, because a
design proposed against no idea of the variance is a design proposed blind and would make
`UNDERPOWERED_FOR_CAPACITY` the answer to every question — which grades a proposer for
knowing nothing rather than for judging well. The pre-period is, by construction, before the
comparison window opens: `pipelines/window.py` is the one definition of that split. Anything
measured inside the window is an outcome and is not here.

The aggregates arrive rather than are computed
-----------------------------------------------
This module takes them as an argument. It does not read a warehouse, a Parquet file or a
corpus, because the same agent runs from a laptop against a fixture and on the estate against
the real pre-period, and a module that fetched its own inputs could only do one of those.
"""

from __future__ import annotations

from dataclasses import dataclass

from holdout.contracts.loader import ContractSet
from holdout.core.design.form import Unit


@dataclass(frozen=True, slots=True)
class PrePeriod:
    """The shape of what the metric did before the window, as the agent is told it.

    Integer cents rather than a float, for the reason every money value in this repository is:
    the contract declares a canonical integer scale and a binary float is a second rounding
    nobody declared.
    """

    weeks: int
    units: int
    mean_cents: int
    variance_cents2: int

    @property
    def coefficient_of_variation(self) -> float:
        """The one derived number, and it is derived here because it is what decides power.

        Reported to the agent because the alternative is showing it a variance of
        24,312,932 and expecting it to divide. A proposer that cannot see the dispersion
        proposes an MDE by taste.
        """
        if self.mean_cents == 0:
            raise ValueError(
                "a pre-period whose mean is zero has no coefficient of variation, and a "
                "design sized against one would be sized against a division by zero."
            )
        return float(self.variance_cents2**0.5) / self.mean_cents


@dataclass(frozen=True, slots=True)
class Roster:
    """How many units a lottery could be drawn over, which is not how many stores exist.

    `CLAUDE.md` restates this twice and it is the most-corrected figure in the repository:
    *a figure about scale names the surviving roster*. The agent is shown the roster and the
    control arm, never the store count, so that a proposal cannot be sized against a number
    that has never decided anything.
    """

    stores: int
    surviving: int
    control_arm: int
    categories: tuple[str, ...]


def enumerated(contracts: ContractSet, pre_period: PrePeriod, roster: Roster) -> dict[str, str]:
    """Every entry the agent is shown, as name -> rendered text.

    A mapping rather than a blob, so a run can record exactly which entries were present and
    a gate can compare that list against this function rather than against a prompt somebody
    read once.
    """
    metrics = sorted(metric.identifier for metric in contracts.metrics)
    policies = sorted(f"{policy.id}@v{policy.version}" for policy in contracts.policies)
    units = ", ".join(sorted(u.value for u in Unit))
    return {
        "metrics": (
            "The metrics you may measure, and the only ones. Naming anything else is refused "
            f"by the engine as METRIC_NOT_IN_CONTRACT: {', '.join(metrics)}."
        ),
        "guardrails": (
            "Prices are bounded by a versioned envelope with effective dates — an absolute "
            "floor, a margin floor, a regulated basket, a prior-price rule and a maximum "
            "daily change. You do not propose prices and you cannot widen the envelope; it "
            "is here because a treatment policy that could not act within it would produce "
            "an experiment in which nothing happens."
        ),
        "policies": (
            "The interventions available are declared policy versions, and these are all of "
            f"them: {', '.join(policies)}. Treatment and control are both policies; control is "
            "the existing policy and never the absence of one, because comparing against "
            "abandonment would inflate every uplift."
        ),
        "roster": (
            f"{roster.surviving} units survive the automatic exclusions out of {roster.stores} "
            f"stores, leaving a control arm of {roster.control_arm} at the contract's holdout "
            f"share. Categories: {', '.join(roster.categories)}. Size against the roster and "
            "the arm, never against the store count."
        ),
        "pre_period": (
            f"Over the {pre_period.weeks} weeks before the window, across {pre_period.units} "
            f"units, the primary metric has mean {pre_period.mean_cents} cents and variance "
            f"{pre_period.variance_cents2}, a coefficient of variation of "
            f"{pre_period.coefficient_of_variation:.2f}. Nothing measured inside the "
            "comparison window is available to you."
        ),
        "units_of_randomisation": (
            f"The unit of randomisation is one of: {units}. Some units guarantee interference "
            "in this trade and are refused at design."
        ),
    }
