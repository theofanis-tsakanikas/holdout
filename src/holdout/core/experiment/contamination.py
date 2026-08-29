"""Is this still the lottery that was committed to? — redraw, and compare what was delivered.

Two questions, and they fail in different ways.

**Did the assignment survive?** The seal is re-derived from its own committed seed and
roster, and the digest is recomputed from its own fields. A seal whose arms were edited in a
table no longer matches either. The redraw is the stronger of the two, because it consults
the seal's arms not at all — only the seed, the strata and the draw index — so it
catches an edit even where somebody was careful enough to recompute the digest to match.

The redraw answers **two** questions and for a while it was only asked one
--------------------------------------------------------------------------
`redraw` returns an arm for every unit the committed strata hold, so its key set *is* the
roster the lottery was drawn over — obtained from the strata, which are committed and
digested as their own section, rather than from the arms table being checked. Comparing
arms answers *did a unit change arm*. Comparing the **key sets** answers *is every unit the
lottery drew still on the table*, and nothing else in this module can.

It was computed and discarded, one line apart, until 2026-08-29. `check` walked
`seal.roster` — which `SealedAssignment` derives as `tuple(sorted(self.arms))` — so a store
deleted from the assignment table with the digest recomputed to match left nothing to
compare against: the check reported the assignment intact and `sealed()` agreed. Claim 3's
eval measured it at **24 of 72 erasure routes invisible here**, and what refused them was
`readout.close`'s stray-outcome guard one function later, which holds only while the erased
store still reports an outcome. `dropped` closes it, and the fix needed no new argument and
no signature change: the witness was already inside the function.

**Deleting the unit from the strata as well does not help a forger**, which is what makes
the strata a sound witness rather than merely an available one: removing a stratum's member
changes which unit holds the smallest rank in it, so `reassigned` fires instead.

**Did each unit get its own arm's policy?** Every delivered policy is compared against the
policy its arm declared. A treated store running the control policy is not a small dilution
to correct for; it is a unit that measures the other arm and is attributed to this one.

Doctrine rule 7 — the one door with no key
------------------------------------------
No unit changes arm after its first observation, not by anyone, including an approver. From
the moment it can, every number the system produces becomes unfalsifiable, and having
exactly one unopenable door is what keeps the other six honest. `SealedAssignment` closes
the in-process routes; this module is what closes the route through a table and back.

**Where this check is vacuous, and it says so.** In an A/A design the two arms declare the
*same* policy, so the delivered-policy comparison cannot fail by construction — there is no
"other arm's policy" to receive. That is not a hole: an A/A split has nothing to contaminate
in that sense, and the redraw half still bites exactly as hard. It is written down because a
check that cannot fail is one somebody will later mistake for a check that passed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from holdout.core.experiment.assignment import (
    SealedAssignment,
    digest_for,
    redraw,
    sealed,
)
from holdout.core.experiment.codes import Arm


@dataclass(frozen=True, slots=True)
class Contamination:
    """What the two halves of the check found. All of it is reported, pass or fail."""

    digest_matches: bool
    redraw_matches: bool
    reassigned: tuple[str, ...]
    dropped: tuple[str, ...]
    """Units the committed lottery drew that the assignment table no longer carries.

    From the strata by way of `redraw`, never from the arms — see the module docstring. It
    is the erasure half of *the holdout is neither erased nor chosen after the fact*, and it
    is separate from `reassigned` because the two are different sentences: one unit holds an
    arm nobody drew, the other has no row at all."""

    misdelivered: tuple[str, ...]
    undelivered: tuple[str, ...]
    comparison_is_vacuous: bool

    @property
    def is_clean(self) -> bool:
        return (
            self.digest_matches
            and self.redraw_matches
            and not self.reassigned
            and not self.dropped
            and not self.misdelivered
            and not self.undelivered
        )

    def __str__(self) -> str:
        if self.is_clean:
            clean = "assignment intact, every unit delivered its own arm's policy"
            if self.comparison_is_vacuous:
                return clean + " (policy comparison vacuous: both arms run the same policy)"
            return clean
        parts: list[str] = []
        if not self.digest_matches:
            parts.append("the recorded digest does not describe the arms it carries")
        if not self.redraw_matches:
            parts.append(
                f"{len(self.reassigned)} unit(s) hold an arm the committed seed does not draw"
            )
        if self.dropped:
            parts.append(
                f"{len(self.dropped)} unit(s) the committed lottery drew are missing from the "
                "assignment table"
            )
        if self.misdelivered:
            parts.append(f"{len(self.misdelivered)} unit(s) received the other arm's policy")
        if self.undelivered:
            parts.append(f"{len(self.undelivered)} unit(s) have no delivery on record")
        return "; ".join(parts)


def check(
    seal: SealedAssignment,
    *,
    delivered: Mapping[str, str],
    treatment_policy: str,
    control_policy: str,
    form_digest: str,
) -> Contamination:
    """Both halves, always, so the report carries both figures whether or not one failed.

    `delivered` maps each unit to the policy ref that actually ran on it — read back from
    the decision record, which is written before the price is dispatched. `form_digest` is
    the design's own fingerprint, recomputed by the caller from the form it is reading the
    result of: a readout run against a *different* form than the one that was sealed is the
    same failure as an edited assignment, arriving by a different door.
    """
    recomputed = digest_for(
        experiment_id=seal.experiment_id,
        seed=seal.seed,
        form_digest=form_digest,
        strata=seal.strata,
        arms=seal.arms,
    )
    digest_matches = recomputed == seal.digest and sealed(seal)

    drawn = redraw(seal)
    reassigned = tuple(u for u in seal.roster if drawn.get(u) is not seal.arms[u])
    # The roster the lottery was actually drawn over, taken from the committed strata rather
    # than from the arms being checked. See the module docstring: this line and the one above
    # it are the same redraw asked two different questions, and only one of them used to be.
    dropped = tuple(sorted(frozenset(drawn) - frozenset(seal.roster)))

    expected = {Arm.TREATMENT: treatment_policy, Arm.CONTROL: control_policy}
    misdelivered = tuple(
        unit
        for unit in seal.roster
        if unit in delivered and delivered[unit] != expected[seal.arms[unit]]
    )
    undelivered = tuple(unit for unit in seal.roster if unit not in delivered)

    return Contamination(
        digest_matches=digest_matches,
        redraw_matches=not reassigned,
        reassigned=reassigned,
        dropped=dropped,
        misdelivered=misdelivered,
        undelivered=undelivered,
        comparison_is_vacuous=treatment_policy == control_policy,
    )
