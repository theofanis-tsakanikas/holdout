"""Moment 1 — *can this experiment exist?*

Everything here is arithmetic over what was handed in. No `contracts_dir`, no filesystem, no
clock: the signature discipline `holdout.core.__init__` states, applied to the one function
in the package with the most excuses to break it.

Either a **refusal that names what would fix it**, or a `Feasible` carrying the committed
lottery: the strata matched on the declared covariates, the draw taken within them from the
committed seed, the assignment sealed, the pre-period balance measured and recorded.

The eight refusals
------------------
======================================  =====================================================
`METRIC_NOT_IN_CONTRACT`                the form's `primary_metric` is not an id in the
                                        contract
`UNIT_GUARANTEES_INTERFERENCE`          a declared carryover fact crosses the dimension the
                                        unit splits arms along — derived from the contract,
                                        never written out
`STOPPING_RULE_PERMITS_PEEKING`         group-sequential with no pre-declared spending
                                        function
`EXCLUSIONS_DEFINED_POST_HOC`           the exclusion set differs from the locked one
`UNITS_ALREADY_COMMITTED`               a unit in scope belongs to an experiment that has
                                        not closed
`UNDERPOWERED_FOR_CAPACITY`             no window up to a year reaches power inside the
                                        holdout share
`UNDERPOWERED_FOR_DURATION`             the smallest window that reaches power is longer
                                        than `max_duration`
`NO_ADMISSIBLE_ASSIGNMENT`              no stratification of the roster gives every
                                        stratum both arms at the declared holdout share —
                                        **or** one exists and no draw within it could pass
                                        the readout's balance check
======================================  =====================================================

Every one that fired is carried; `codes.DESIGN_PRECEDENCE` decides only which one leads.

The interference table is derived, and it must not look like arithmetic
-----------------------------------------------------------------------
Two of the four units are refused. **The refusal does not rest on anything observed in this
repository** — and in particular not on what `corpus/world/` generates: the generator was
written to have reference-price memory and cross-price effects, so grounding the refusal in
them would be the generator and the engine agreeing with each other, and `holdout.core` may
not know that `corpus/` exists at all.

It rests on `contracts/design/inference.yaml`'s `carryover:` block — two stated facts about
grocery retail, each with a source and a verification date, and one mitigation declared
absent. `interference_of` is a pure function of that block:

============================  ==============================  =============================
unit                          splits arms along               refused while
============================  ==============================  =============================
`store`                       stores                          never — a store is what a
                                                              shopper visits, and nothing
                                                              in `carryover` crosses it
`region`                      regions                         never — strictly coarser
`store_week`                  **time, inside one store**      `reference_price_memory` and
                                                              no declared washout
`store_category`              **categories, inside one
                              store**                         `cross_price_substitution`
============================  ==============================  =============================

A contract declaring a washout long enough to exhaust the reference price would admit
`store_week` **with no code change**, and `tests/core/test_design_engine.py` asserts exactly
that by handing the function an independently built `carryover` with the flag cleared. A
hard-coded table would pass every test while quietly being a second definition of a contract
value.

What is code and what is not: *which* unit to randomise on has no single correct answer, so
a model may propose it. Whether a declared carryover fact crosses the dimension a given unit
splits has exactly one, so code decides it. **The assumption is the load-bearing part and it
is in the contract; the code is only the derivation.**

A design no lottery could have saved is refused here, not at every readout forever
----------------------------------------------------------------------------------
The balance tolerance is judged at exactly one moment — the readout, over what actually
arrived — and that has not changed. What is decided here is a different question: whether
**any** draw within the strata could have satisfied it. One control comes out of each
stratum, so a categorical covariate's control count is pinned by how the strata fall across
its levels and not by the seed; where that pinning already puts a level outside the
tolerance, every readout refuses `IMBALANCED_PRE_PERIOD`, identically, forever.

Until T00D such a design was accepted in silence. Measured on this repository's own corpus
at 25 controls: `store_format=hypermarket` at a **constant 0.1734** across two hundred
draws. That is an experiment that could never have reported anything, for a reason with
nothing to do with the lottery — the same shape as the starved reference set the
re-randomisation screen produced, one moment earlier.

`balance.attainable` computes the bound with the readout's own arithmetic, so a refusal
here is sound: nothing is refused that some draw could have carried. It is incomplete in two
named ways, and the module that owns the statistic states both. **This is the only place in
the engine where a readout-time threshold is consulted at design**, and it is consulted as a
*possibility*, never as a screen: no candidate is drawn, judged and replaced, which is the
door the stratified lottery closed and this does not reopen.

`CLAUDE.md`'s checklist asks, of any gate, whether a `gate-proof` mutation proves it bites.
**There is none yet and there cannot be**: the design engine's mutations belong to claim 6,
which has no Makefile target, and `evals/gate_proof/ledger.py` refuses a mutation no claim
target would run. What stands in for it until then is `tests/core/test_balance.py`, whose
case is drawn by the corpus's own hashing and whose breaking control count is found by
search — and which checks the refusal against two hundred real draws in both directions.

The one limit, declared rather than papered over
------------------------------------------------
**`decision_rule` is free text and code does not adjudicate free text.** The schema
guarantees three non-empty sentences and nothing more. `STOPPING_RULE_PERMITS_PEEKING` is
decided over `StoppingRule` — a structural value the engine itself holds — and never over
the prose. The guarantee that actually stops peeking is moment 2: `readout.may_read` refuses
to compute anything before the declared end whatever anybody declared. **The design-time
check is the announcement; the readout-time block is the lock.**

The power calculation is a normal approximation
-----------------------------------------------
Declared as such. For `W` weeks and a per-unit-week variance `s²`, the variance of a unit's
mean over the window is `s² / W`, and::

    n per arm  =  ceil( 2 · (z_α + z_β)² · s² / (W · d²) )

with `z_α` two-sided from the contract — one-sided where `mde.direction` is not `either` —
`z_β` from the contract, and `d` the MDE as an absolute difference on the metric. Every
quantity is an exact `Fraction`, so the ceiling is the only rounding and it is in the
direction that asks for more units rather than fewer. No square root appears: the formula
has none, and `math` is not importable here in any case.

It decides feasibility **before** the experiment. It decides nothing at readout, where the
realised variance does — which is the honest half of W5, the world where the design believed
a variance the world did not supply.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from holdout.contracts.model import BalanceCovariates, Carryover, InferenceSettings, Metric
from holdout.core.design.codes import DesignRefusalCode
from holdout.core.design.form import (
    DesignForm,
    Exclusion,
    MdeKind,
    StoppingRule,
    Unit,
)
from holdout.core.design.refusal import DesignRefusal, DesignRefusalReason
from holdout.core.experiment.assignment import (
    SealedAssignment,
    control_size_for,
    draw,
)
from holdout.core.experiment.balance import (
    CovariateMatrix,
    Standardised,
    attainable,
    worst_of,
)
from holdout.core.hashing import digest

#: Two arms, so the variance of the difference is twice the variance of one arm's mean.
ARMS = 2

#: The longest window the sizing search will consider, in weeks. A year: past it the
#: question stops being "is this design powered" and becomes "is this still the same
#: business". It is not a contract value because it bounds a *search*, not a design — no
#: experiment may run this long unless its own `max_duration` says so, and `max_duration` is
#: capped at 52 by the form schema.
SEARCH_HORIZON_WEEKS = 52


class FeasibilityError(ValueError):
    """The engine was handed inputs it cannot assess. Not a refusal — a refusal is a correct
    output about a design, and this says the caller has not finished building one."""


# ------------------------------------------------------------------ the derived table


def interference_of(unit: Unit, carryover: Carryover) -> str | None:
    """Why this unit cannot isolate arms under the declared carryover, or `None`.

    A pure function of the contract's `carryover:` block. See the module docstring for why
    it is derived rather than written out, and `docs/DECISIONS.md` for the deferral that
    records what would unlock the two units it refuses.
    """
    if unit in (Unit.STORE, Unit.REGION):
        return None
    if unit is Unit.STORE_WEEK:
        if carryover.reference_price_memory and not carryover.reference_price_is_exhausted:
            return (
                "store_week splits arms along time inside one store, and the contract "
                "declares reference_price_memory with no washout period "
                "(carryover.washout_weeks is null). The price a shopper saw in a treated "
                "week is still acting on them in the control week that follows, so the "
                "control is contaminated by construction rather than by accident."
            )
        return None
    if carryover.cross_price_substitution:
        return (
            "store_category splits arms along categories inside one store, and the "
            "contract declares cross_price_substitution: fresh categories in one store "
            "contain substitutes, so a price moved in a treated category shifts demand in "
            "a control one. The arms share customers by construction."
        )
    return None


# ------------------------------------------------------------------ the answer


@dataclass(frozen=True, slots=True)
class Feasible:
    """This experiment may exist, and here is the lottery it will run under.

    Everything a later moment needs and nothing it could recompute differently. The seal is
    on it because moment 1 is where the assignment is written: *before* the period opens,
    from the committed seed, and then read-only.
    """

    experiment_id: str
    form_digest: str
    metric_ref: str
    roster: tuple[str, ...]
    declared_exclusions: tuple[Exclusion, ...]
    automatic_exclusions: tuple[Exclusion, ...]
    required_per_arm: int
    weeks: int
    mde_absolute: Fraction
    two_sided: bool
    assignment: SealedAssignment
    balance: tuple[Standardised, ...]

    @property
    def control_size(self) -> int:
        return len(self.assignment.control)

    @property
    def treatment_size(self) -> int:
        return len(self.assignment.treatment)

    @property
    def excluded_store_ids(self) -> frozenset[str]:
        return frozenset(
            e.store_id for e in (*self.declared_exclusions, *self.automatic_exclusions)
        )


def form_digest_of(form: DesignForm) -> str:
    """The identity of a design document. See `DesignForm.canonical_fields` for what it
    covers and why that list is written out rather than derived."""
    return digest(form.canonical_fields())


# ------------------------------------------------------------------ moment 1


def assess(
    form: DesignForm,
    *,
    experiment_id: str,
    seed: str,
    metric: Metric | None,
    metric_ids: tuple[str, ...],
    covariates: BalanceCovariates,
    inference: InferenceSettings,
    roster: tuple[str, ...],
    matrix: CovariateMatrix,
    variance_per_unit_week: Decimal,
    mean_per_unit_week: Decimal,
    committed_elsewhere: frozenset[str],
    neighbour_pairs: tuple[tuple[str, str], ...],
    stopping: StoppingRule,
    previously_locked: DesignForm | None,
) -> Feasible | DesignRefusal:
    """Can this experiment exist? A `Feasible` with its sealed lottery, or a `DesignRefusal`.

    Three arguments the SPEC's signature did not carry, each because the engine cannot do
    its job without them and cannot invent them either:

    * **`seed`** — moment 1 was described as *generating* the committed seed. `holdout.core`
      reads no clock, no environment and no random source, so it structurally cannot; the
      seed is committed alongside the design, which is the stronger position anyway. A seed
      the engine invented would be a seed nobody committed to in advance.
    * **`matrix`** — the strata are matched on the covariate *values*, not only on the
      contract that names the columns.
    * **`experiment_id`** — a seal belongs to one experiment, and the digest that survives
      the round trip through a table says which.

    `metric` is `Metric | None` for the same reason: where the form names an id the contract
    does not have, there is no version to resolve, and `None` is the honest argument rather
    than a placeholder somebody would have had to invent.
    """
    reasons: list[DesignRefusalReason] = []

    def refuse(code: DesignRefusalCode, detail: str, remedy: str) -> None:
        reasons.append(DesignRefusalReason(code=code, detail=detail, what_would_fix_it=remedy))

    _check_matrix_matches_the_contract(matrix, covariates)
    _check_roster(roster, matrix)

    # --- the metric ----------------------------------------------------------------
    metric_ref = ""
    if form.primary_metric not in metric_ids or metric is None:
        refuse(
            DesignRefusalCode.METRIC_NOT_IN_CONTRACT,
            f"primary_metric is {form.primary_metric!r} and the contract holds "
            f"{list(metric_ids)}. A metric defined inside a design is a metric nobody else "
            "computes the same way.",
            "Choose an id from the contract, or add the metric to the contract first — "
            "which is a versioned change with its own restatement question.",
        )
    elif metric.id != form.primary_metric:
        raise FeasibilityError(
            f"the resolved metric is {metric.id!r} and the form names "
            f"{form.primary_metric!r}. The caller resolved the wrong one, and assessing "
            "against it would size the experiment for a metric it will never read."
        )
    else:
        metric_ref = metric.ref

    # --- the unit ------------------------------------------------------------------
    interference = interference_of(form.unit, inference.carryover)
    if interference is not None:
        refuse(
            DesignRefusalCode.UNIT_GUARANTEES_INTERFERENCE,
            interference,
            "Randomise at a coarser unit — store or region — or declare and source the "
            "mitigation the contract records as absent: a washout period long enough to "
            "exhaust the reference price, or an assortment separation between categories.",
        )

    # --- the stopping rule ---------------------------------------------------------
    if stopping.permits_peeking:
        refuse(
            DesignRefusalCode.STOPPING_RULE_PERMITS_PEEKING,
            "the declared stopping rule is group-sequential over "
            f"{stopping.looks} looks with no pre-declared alpha-spending function. Acting "
            "on an interim result inflates the false-positive rate above the declared alpha "
            "regardless of how the estimator is computed.",
            "Declare a single readout at the end, or declare the spending function in "
            "advance — in advance being the whole of it.",
        )

    # --- exclusions that moved -----------------------------------------------------
    if previously_locked is not None and previously_locked.exclusion_pairs != form.exclusion_pairs:
        was = {store for store, _ in previously_locked.exclusion_pairs}
        now = form.excluded_store_ids
        refuse(
            DesignRefusalCode.EXCLUSIONS_DEFINED_POST_HOC,
            "the exclusion set differs from the one locked when the experiment opened: "
            f"added {sorted(now - was)}, removed {sorted(was - now)}"
            + ("" if (now - was) or (was - now) else ", and a reason was rewritten")
            + ". Every such edit is a degree of freedom applied with knowledge of the "
            "outcome.",
            "Nothing, for this experiment. Declare the exclusion before the next one opens.",
        )

    # --- who is left ---------------------------------------------------------------
    declared = tuple(sorted(form.exclusions, key=lambda e: e.store_id))
    automatic = _neighbour_exclusions(roster, neighbour_pairs, form.excluded_store_ids)
    removed = form.excluded_store_ids | {e.store_id for e in automatic}
    available = tuple(u for u in roster if u not in removed)

    committed = sorted(set(available) & committed_elsewhere)
    if committed:
        refuse(
            DesignRefusalCode.UNITS_ALREADY_COMMITTED,
            f"{len(committed)} unit(s) in scope are assigned to an experiment that has not "
            f"closed: {committed[:8]}. A unit in two experiments measures the sum of both "
            "and attributes it to either.",
            "Exclude the committed units, or wait for the other experiment to close. They "
            "are deliberately not dropped here: which units an experiment runs on is the "
            "design's decision, not the engine's.",
        )

    # --- the sizing ----------------------------------------------------------------
    absolute = _absolute_mde(form, mean_per_unit_week)
    variance = Fraction(variance_per_unit_week)
    if variance <= 0:
        raise FeasibilityError(
            f"the historical per-unit-week variance is {variance_per_unit_week}. A "
            "non-positive variance would make every design infinitely powered, which is "
            "the shape of an input that was never measured."
        )
    arm_capacity, control_capacity = _capacity(len(available), inference)
    two_sided = form.mde.is_two_sided
    z_sum = Fraction(inference.z_alpha(two_sided=two_sided)) + Fraction(inference.z_power)

    weeks: int | None = None
    required = _required_per_arm(z_sum, variance, absolute, weeks=SEARCH_HORIZON_WEEKS)
    for candidate_weeks in range(1, SEARCH_HORIZON_WEEKS + 1):
        needed = _required_per_arm(z_sum, variance, absolute, weeks=candidate_weeks)
        if needed <= arm_capacity:
            weeks, required = candidate_weeks, needed
            break

    if weeks is None:
        refuse(
            DesignRefusalCode.UNDERPOWERED_FOR_CAPACITY,
            f"{required} unit(s) per arm are needed even over {SEARCH_HORIZON_WEEKS} weeks, "
            f"and the binding arm holds {arm_capacity} — {control_capacity} control out of "
            f"{len(available)} available at a {inference.holdout_share_pct}% holdout share. "
            "The holdout share is fixed and some units are already spoken for.",
            "Wait for a running experiment to close, widen the scope, or raise the MDE. "
            "Lowering the holdout share is a contract change with a restatement, not an "
            "exception granted to this experiment.",
        )
        refuse(
            DesignRefusalCode.UNDERPOWERED_FOR_DURATION,
            f"no window up to {SEARCH_HORIZON_WEEKS} weeks reaches the declared power at "
            f"the observed historical variance, so none fits inside max_duration of "
            f"{form.max_duration.weeks} week(s) either.",
            "A larger MDE, a longer max_duration, or a lower-variance unit of randomisation.",
        )
    elif weeks > form.max_duration.weeks:
        refuse(
            DesignRefusalCode.UNDERPOWERED_FOR_DURATION,
            f"the shortest window that reaches the declared power is {weeks} week(s) at "
            f"{required} unit(s) per arm, and max_duration is "
            f"{form.max_duration.weeks} week(s). The sample cannot be accumulated inside it "
            "at the observed historical variance.",
            "A larger MDE, a longer max_duration, or a lower-variance unit of "
            "randomisation. Not a shorter window: a design quietly shortened to fit is a "
            "design that reports whatever it happened to see.",
        )

    if reasons:
        return DesignRefusal(experiment_id=experiment_id, reasons=tuple(reasons))

    # --- the lottery ---------------------------------------------------------------
    assert weeks is not None  # every path that leaves it None has already refused
    fingerprint = form_digest_of(form)
    drawn = draw(
        experiment_id=experiment_id,
        roster=available,
        seed=seed,
        form_digest=fingerprint,
        matrix=matrix.restricted_to(frozenset(available)),
        control_size=control_capacity,
    )
    if drawn is None:
        return DesignRefusal(
            experiment_id=experiment_id,
            reasons=(
                DesignRefusalReason(
                    code=DesignRefusalCode.NO_ADMISSIBLE_ASSIGNMENT,
                    detail=(
                        f"no stratification of {len(available)} unit(s) into "
                        f"{control_capacity} strata gives every stratum both arms: at the "
                        f"declared {inference.holdout_share_pct}% holdout share some "
                        "stratum would hold a single unit, and a stratum of one is a unit "
                        "whose arm nobody drew. The design is feasible on paper — the "
                        "sample is there and the duration fits — and there is still no "
                        "lottery to run."
                    ),
                    what_would_fix_it=(
                        "A larger roster, so every stratum holds at least two units at the "
                        "declared share. Lowering the holdout share is a contract change "
                        "with a restatement, not an exception granted to this experiment."
                    ),
                ),
            ),
        )

    seal, balance = drawn
    unreachable = _unreachable_balance(matrix, seal, inference)
    if unreachable is not None:
        return DesignRefusal(experiment_id=experiment_id, reasons=(unreachable,))

    return Feasible(
        experiment_id=experiment_id,
        form_digest=fingerprint,
        metric_ref=metric_ref,
        roster=available,
        declared_exclusions=declared,
        automatic_exclusions=automatic,
        required_per_arm=required,
        weeks=weeks,
        mde_absolute=absolute,
        two_sided=two_sided,
        assignment=seal,
        balance=balance,
    )


# ------------------------------------------------------------------ the arithmetic


def _unreachable_balance(
    matrix: CovariateMatrix, seal: SealedAssignment, inference: InferenceSettings
) -> DesignRefusalReason | None:
    """`NO_ADMISSIBLE_ASSIGNMENT` where no draw within the strata could pass the balance check.

    Asked **after** the lottery rather than before it, and that is a cost decision with no
    consequence: building the strata is the expensive half and the draw inside them is
    arithmetic over a hash, so the seal is cheap to produce and discard. Nothing about
    *when* the design is decided follows from it — the strata this reads are the strata that
    were drawn within, and they are a pure function of the covariates.
    """
    reachable = attainable(matrix.restricted_to(frozenset(seal.roster)), seal.strata)
    if not reachable:
        return None
    worst = worst_of(reachable)
    if not worst.exceeds(inference.balance_tolerance_smd):
        return None
    return DesignRefusalReason(
        code=DesignRefusalCode.NO_ADMISSIBLE_ASSIGNMENT,
        detail=(
            f"the strata pin {worst} against a tolerance of "
            f"{inference.balance_tolerance_smd}, and that is the *best* any draw could "
            "reach: one control comes out of each stratum, so this covariate's control "
            "count is decided by how the strata fall across its levels and not by the "
            "seed. Every readout would refuse IMBALANCED_PRE_PERIOD, identically, whatever "
            "seed was committed. The design is feasible on paper — the sample is there and "
            "the duration fits — and there is still no lottery worth running."
        ),
        what_would_fix_it=(
            "A roster whose categorical composition can be split at the declared "
            f"{inference.holdout_share_pct}% holdout share — units added to the level the "
            "allocation cannot reach, or a coarser level set. Widening the balance "
            "tolerance or lowering the holdout share is a versioned contract change with a "
            "restatement, not an exception granted to this experiment."
        ),
    )


def _required_per_arm(
    z_sum: Fraction, variance: Fraction, absolute_mde: Fraction, *, weeks: int
) -> int:
    """`ceil( 2 · (z_α + z_β)² · s² / (W · d²) )`, exact, rounded up.

    Up rather than to nearest: the sample size is a threshold, and a design one unit short
    of the sample it needs is underpowered by exactly as much as one a hundred short. The
    ceiling is the only rounding in the module.
    """
    numerator = ARMS * z_sum * z_sum * variance
    denominator = weeks * absolute_mde * absolute_mde
    exact = numerator / denominator
    whole = exact.numerator // exact.denominator
    return whole if exact.denominator == 1 else whole + 1


def _absolute_mde(form: DesignForm, mean_per_unit_week: Decimal) -> Fraction:
    """The MDE as an absolute difference on the metric.

    A `relative_pct` MDE is a percentage of the historical mean, so it needs the mean and
    that mean has to be positive: a percentage of zero is zero, and a design whose MDE is
    zero asks for an infinite sample without saying so.
    """
    if form.mde.kind is MdeKind.ABSOLUTE:
        return Fraction(form.mde.value)
    mean = Fraction(mean_per_unit_week)
    if mean <= 0:
        raise FeasibilityError(
            f"a relative MDE of {form.mde.value}% is measured against a historical mean of "
            f"{mean_per_unit_week}. A percentage of a non-positive mean is not a difference "
            "anybody could detect, and reading it as an absolute one would be inventing a "
            "number the design never declared."
        )
    return mean * Fraction(form.mde.value) / 100


def _capacity(available: int, inference: InferenceSettings) -> tuple[int, int]:
    """`(binding arm, control arm)` at the declared holdout share.

    The control arm is `floor(available × holdout_share_pct / 100)` and the treatment arm is
    the rest. The **smaller** of the two binds, because the required sample is per arm and
    the design is only as powered as its thinner side. At a 20% share that is the control
    arm; the minimum is taken anyway rather than assumed, because the share is a contract
    value and a contract value can move.
    """
    control = control_size_for(available, inference.holdout_share_pct)
    return min(control, available - control), control


# ------------------------------------------------------------------ the inputs


def _check_matrix_matches_the_contract(
    matrix: CovariateMatrix, covariates: BalanceCovariates
) -> None:
    """The strata are matched on exactly the contract's covariates — no more, no fewer.

    `contracts/design/balance_covariates.yaml` fixes the list precisely so that an
    experiment cannot pick which characteristics to balance on: that would be a new way to
    fish, trying combinations until a draw came out flattering. A matrix carrying a sixth
    column, or missing the fifth, would defeat that from the other side — so it is refused
    here rather than matched on.
    """
    if matrix.ids != covariates.ids:
        raise FeasibilityError(
            f"the covariate matrix carries {list(matrix.ids)} and the contract fixes "
            f"{list(covariates.ids)}, in that order. The list is fixed so that an "
            "experiment cannot choose which characteristics to balance on; a matrix that "
            "chose for it would be the same degree of freedom entering by the back door."
        )


def _check_roster(roster: tuple[str, ...], matrix: CovariateMatrix) -> None:
    if not roster:
        raise FeasibilityError("an experiment needs a roster; none was supplied")
    if len(set(roster)) != len(roster):
        raise FeasibilityError("a unit appears twice in the roster")
    missing = sorted(set(roster) - set(matrix.rows))
    if missing:
        raise FeasibilityError(
            f"{len(missing)} unit(s) in the roster carry no covariates: {missing[:8]}. A "
            "unit that cannot be measured cannot be stratified, and stratifying the rest "
            "around it would be matching on a subset nobody declared."
        )


def _neighbour_exclusions(
    roster: tuple[str, ...],
    neighbour_pairs: tuple[tuple[str, str], ...],
    already: frozenset[str],
) -> tuple[Exclusion, ...]:
    """The later-sorted member of each neighbouring pair, with its reason.

    Deterministic on purpose: the *later-sorted* member, so the same roster and the same
    pairs always leave the same survivors. Dropping "whichever came second in the list"
    would make the surviving roster depend on the order somebody wrote the pairs in, and a
    roster that moves is an experiment that cannot be reproduced.

    Two stores inside the declared radius share shoppers, so a treated one and a control one
    would be measuring each other. Only one of the pair need go; which one has no single
    correct answer, which is exactly why it is settled by a rule rather than by a judgment.
    """
    on_roster = set(roster)
    excluded: dict[str, str] = {}
    for left, right in neighbour_pairs:
        if left == right:
            raise FeasibilityError(f"{left!r} is listed as its own neighbour")
        if left not in on_roster or right not in on_roster:
            continue
        keep, drop = sorted((left, right))
        if drop in already or keep in already:
            continue
        if drop not in excluded:
            excluded[drop] = (
                f"within the declared neighbour radius of {keep}, so the two share shoppers "
                "and a treated store would be measuring its control neighbour. The "
                "later-sorted member of the pair is the one that goes, so the surviving "
                "roster does not depend on the order the pairs arrived in."
            )
    return tuple(
        Exclusion(store_id=store, reason=reason) for store, reason in sorted(excluded.items())
    )
