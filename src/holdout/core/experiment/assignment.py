"""The lottery, the stratified restriction it draws under, and the one door with no key.

The draw
--------
For a candidate index ``d`` and a unit id ``u``::

    key    = blake2b(seed || d, digest_size=32).digest()
    rank_u = int(blake2b(u, key=key, digest_size=16).digest())

Within each stratum the unit with the smallest ``(rank_u, u)`` becomes the control — the id
breaks a tie, so the choice is total and never depends on the order the stratum arrived
in — and every other unit in the stratum is treated. One control per stratum, because the
strata are built with exactly that in mind (`strata.strata_of`).

**Keyed hashing rather than a seeded generator**, and not only because `random` and
`secrets` are banned in `holdout.core`. Claim 3's whole sentence is *assignment from a
committed seed, exactly reproducible*, and hashing is better at every clause of it:

* reproducible from the committed seed alone, with no dependence on an interpreter version
  or a platform's generator;
* independent of iteration order, because each rank is computed from the unit id and
  nothing else;
* computable **per unit** — a readout a month later can re-derive one store's arm without
  replaying a sequence, which is what makes the contamination check cheap enough to run on
  every unit rather than on a sample.

Stratification, where re-randomisation used to be
-------------------------------------------------
This module first drew unstratified candidates and screened them against
`balance_tolerance_smd` until one passed. At the scenario's own shape that screen accepted
about one draw in a thousand, the reference set starved, and the smallest attainable
p-value sat above the declared α — the deferral in `docs/DECISIONS.md` has the arithmetic.
The balance now lives in the **restriction**: strata are matched on a composite distance
over the declared pre-period covariates (`strata.py`), the lottery draws within them, and
every candidate is admissible by construction. The tolerance did not disappear — it moved
to the one moment it always also applied, the readout's balance check, which measures what
actually arrived. That move is a restatement, recorded in
`contracts/design/inference.yaml`'s own notes.

The reference set is the same restriction, exactly
--------------------------------------------------
The realised assignment is candidate 0 under the committed seed; the reference set is the
candidates after it. Every one of them is drawn by the same rule within the same strata,
so the permutation test compares the observed statistic against re-draws of **this exact
mechanism** — not a sample of some larger admissible set, which is what the screened
version could honestly claim and no more. Whether the machinery preserves the declared
level end to end is still claim 2, measured at K = 200 seeds, not asserted here.

No admissible stratification is a **refusal**, not an exception
---------------------------------------------------------------
`draw` returns `None` where no stratification gives every stratum both arms — the holdout
share asks for more controls than the roster can stratify at two-plus units each. It is
returned rather than raised because everything in this repository that decides an outcome
returns it: a refusal is a correct output, and an exception is a statement that the caller
is wrong. `feasibility` turns the `None` into `NO_ADMISSIBLE_ASSIGNMENT`, a code with a
`what_would_fix_it`, which is what the design engine is for.

The seal, and why it is both a type and a digest
------------------------------------------------
`SealedAssignment` is the `CertifiedPrice` pattern one module along: the constructor raises,
subclassing raises, there is no `__setattr__`, no `__reduce__`, every field is read through a
guarded accessor, and the function that fills the slots lives in a closure beside a witness
with no importable name. That closes the in-process routes.

It does nothing at all for the route by which an assignment will actually be altered:
written to `gold.experiment_assignment`, read back by a readout in another process a month
later. That is what the digest is for — `blake2b` over `(experiment_id, seed, form_digest,
strata, roster, arms)`, recomputed by the contamination check from the seal's own fields
and compared. The strata are inside it because they are part of the committed lottery: a
moved stratum boundary changes which draws were ever possible, which is the same edit as a
moved arm wearing a subtler coat.

**The honest limit, in the shape `certificate.py` already sets.** A forger who rewrites the
arms, the seed, the strata and the digest in one coordinated edit is not caught, because a
seal never held independent evidence of its own provenance. `tests/core/test_assignment_forgery.py`
asserts that limit rather than hiding it. What *is* caught is every edit that is not
coordinated — which is every edit that happens by accident, and most that do not.

**And the seed is supplied, never generated here.** `holdout.core` reads no clock, no
environment and no random source, so it could not mint one; the seed is committed alongside
the design. That is also the stronger position: a seed the engine invented would be a seed
nobody committed to in advance, and claim 3 is about the commitment.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal
from fractions import Fraction
from hashlib import blake2b
from types import MappingProxyType
from typing import Any, Protocol, cast

from holdout.core.experiment.balance import (
    CovariateMatrix,
    Standardised,
    standardised,
)
from holdout.core.experiment.codes import Arm
from holdout.core.experiment.strata import strata_of
from holdout.core.hashing import digest

#: Width of the candidate index inside the per-draw key. Eight bytes, so the reference-set
#: budget can never overflow it and the encoding never has to change — a changed encoding
#: would move every assignment this repository has ever recorded.
DRAW_INDEX_BYTES = 8

#: Size of the per-draw key and of each unit's rank. 16 bytes of rank is 128 bits, so a tie
#: between two units is not something that happens; the id breaks it anyway, because "not
#: something that happens" is not the same as "cannot happen".
KEY_BYTES = 32
RANK_BYTES = 16


class AssignmentError(ValueError):
    """The lottery was asked for something it cannot draw. Not a refusal — see the module
    docstring: a refusal is returned, and this says the caller is wrong."""


class SealForgeryError(TypeError):
    """A `SealedAssignment` was constructed, altered or serialised outside `draw`."""


class _Witness:
    """The object `draw` stamps a seal with. One instance, held in a closure."""

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return "<assignment witness>"


Strata = tuple[tuple[str, ...], ...]


# ------------------------------------------------------------------ the draw itself


def key_for(seed: str, draw_index: int) -> bytes:
    """The per-candidate key. Derived from the seed so one committed seed gives every draw."""
    if draw_index < 0:
        raise AssignmentError("candidate indices are counted from zero")
    material = seed.encode("utf-8") + draw_index.to_bytes(DRAW_INDEX_BYTES, "big")
    return blake2b(material, digest_size=KEY_BYTES).digest()


def rank_of(unit_id: str, key: bytes) -> int:
    """One unit's place in one candidate's order. Computable without the rest of the roster."""
    return int.from_bytes(
        blake2b(unit_id.encode("utf-8"), key=key, digest_size=RANK_BYTES).digest(), "big"
    )


def _check_strata(strata: Strata) -> None:
    if not strata:
        raise AssignmentError("a stratification holds at least one stratum")
    seen: set[str] = set()
    for stratum in strata:
        if len(stratum) < 2:
            raise AssignmentError(
                f"a stratum of {len(stratum)} unit(s) cannot hold both arms. A stratum of "
                "one is a unit whose arm nobody drew."
            )
        for unit in stratum:
            if unit in seen:
                raise AssignmentError(f"{unit!r} appears in two strata; each unit is assigned once")
            seen.add(unit)


def candidate(strata: Strata, *, seed: str, draw_index: int) -> MappingProxyType[str, Arm]:
    """One candidate assignment. Deterministic in `(strata, seed, draw_index)`.

    Within each stratum the unit with the smallest `(rank, id)` becomes the control; the
    rest are treated. Public because the contamination check re-derives it independently
    at readout, and because a test that could only obtain an assignment through the
    sealing machinery could not check the lottery on its own.
    """
    _check_strata(strata)
    key = key_for(seed, draw_index)
    arms: dict[str, Arm] = {}
    for stratum in strata:
        chosen = min(stratum, key=lambda unit: (rank_of(unit, key), unit))
        for unit in stratum:
            arms[unit] = Arm.CONTROL if unit == chosen else Arm.TREATMENT
    return MappingProxyType(arms)


def control_size_for(roster_size: int, holdout_share_pct: Decimal) -> int:
    """How many units the declared holdout share buys, rounded **down**.

    Down, not to nearest: the share is what is held back and every unit not held back is
    treated, so rounding up would treat fewer units than the design said it would. It is a
    bound in the same sense a floor is, and a bound that rounds toward what it excludes is
    not a bound. It is also how many strata the lottery draws within, because each stratum
    contributes exactly one control.
    """
    if roster_size < 2:
        raise AssignmentError(
            f"a roster of {roster_size} cannot be split into two arms. One unit is not an "
            "experiment, it is an anecdote with a seed."
        )
    size = int((Fraction(roster_size) * Fraction(holdout_share_pct)) / 100)
    if size < 1:
        raise AssignmentError(
            f"a holdout share of {holdout_share_pct}% of {roster_size} unit(s) rounds to "
            "nothing. The share is a contract value; the roster is what would have to change."
        )
    if size >= roster_size:
        raise AssignmentError(
            f"a holdout share of {holdout_share_pct}% of {roster_size} unit(s) leaves no "
            "treatment arm"
        )
    return size


def covariate_digest(matrix: CovariateMatrix) -> str:
    """A digest of the matrix an assignment was stratified on.

    Recorded on the seal so that a readout can say whether the covariates it is re-measuring
    are the ones the strata were built from. They very often are not — a restatement moves
    them, and that is a fact about the world rather than an attack — so this is evidence,
    never a check on its own.
    """
    parts: list[str] = ["ids", *matrix.ids, "kinds", *(k.value for k in matrix.kinds)]
    for unit in matrix.units:
        parts.append(unit)
        parts.extend(str(value) for value in matrix.rows[unit])
    return digest(parts)


def digest_for(
    *,
    experiment_id: str,
    seed: str,
    form_digest: str,
    strata: Strata,
    arms: Mapping[str, Arm],
) -> str:
    """The digest that survives a round trip through a table and back.

    Over the strata, the roster **and** the arms — the last two both in sorted-unit order —
    plus the identity of the experiment, the seed and the form. The roster is not derivable
    from the arms for this purpose even though it is the same set of keys: writing it out
    means a unit dropped from the table changes the digest, rather than changing what the
    digest is taken over. The strata are inside because they are part of the committed
    lottery — a moved stratum boundary changes which draws were ever possible.
    """
    roster = sorted(arms)
    parts = [
        "experiment_id",
        experiment_id,
        "seed",
        seed,
        "form_digest",
        form_digest,
    ]
    for stratum in strata:
        parts.append("stratum")
        parts.extend(stratum)
    parts.extend(("roster", *roster, "arms", *(arms[unit].value for unit in roster)))
    return digest(parts)


# ------------------------------------------------------------------ the seal


class SealedAssignment:
    """The committed lottery. Written before the period opens, then read-only.

    Not a dataclass and not constructible by any ordinary route — the module docstring says
    which routes are closed and which one Python does not let anyone close.
    """

    __slots__ = (
        "_arms",
        "_covariate_digest",
        "_digest",
        "_draw_index",
        "_experiment_id",
        "_form_digest",
        "_seed",
        "_strata",
        "_witness",
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise SealForgeryError(
            "a SealedAssignment is not constructed; it is drawn. The only way to obtain one "
            "is holdout.core.experiment.assignment.draw(...), which builds the strata and "
            "runs the lottery. In a test, draw one: building the object directly would be "
            "asserting that the type can be bypassed, and it cannot."
        )

    def __init_subclass__(cls, **_kwargs: object) -> None:
        raise TypeError(
            "SealedAssignment may not be subclassed. A subclass satisfies every isinstance "
            "check a readout makes while carrying whatever its own constructor put in it."
        )

    # ------------------------------------------------------------------ read-only fields

    @property
    def experiment_id(self) -> str:
        return cast(str, self._read("_experiment_id"))

    @property
    def seed(self) -> str:
        """The committed seed. Everything about the draw follows from it and the strata."""
        return cast(str, self._read("_seed"))

    @property
    def draw_index(self) -> int:
        """Which candidate is the realised one.

        On the seal because the reference set is the candidates *after* it under the same
        strata, and the realised one has to be identifiable so it is never counted twice.
        """
        return cast(int, self._read("_draw_index"))

    @property
    def strata(self) -> Strata:
        """The restriction the lottery drew under — matched on the committed covariates.

        On the seal because a readout re-derives the draw and its reference set from the
        seed and the strata, and because the digest is taken over them: the strata are the
        committed part of the lottery that the seed alone cannot reproduce.
        """
        return cast(Strata, self._read("_strata"))

    @property
    def arms(self) -> MappingProxyType[str, Arm]:
        return cast("MappingProxyType[str, Arm]", self._read("_arms"))

    @property
    def form_digest(self) -> str:
        return cast(str, self._read("_form_digest"))

    @property
    def covariate_digest(self) -> str:
        return cast(str, self._read("_covariate_digest"))

    @property
    def digest(self) -> str:
        """What survives being written to a table and read back. See the module docstring."""
        return cast(str, self._read("_digest"))

    @property
    def roster(self) -> tuple[str, ...]:
        return tuple(sorted(self.arms))

    @property
    def control(self) -> tuple[str, ...]:
        return tuple(u for u in self.roster if self.arms[u] is Arm.CONTROL)

    @property
    def treatment(self) -> tuple[str, ...]:
        return tuple(u for u in self.roster if self.arms[u] is Arm.TREATMENT)

    def arm_of(self, unit_id: str) -> Arm:
        return self.arms[unit_id]

    def _read(self, slot: str) -> Any:
        try:
            return object.__getattribute__(self, slot)
        except AttributeError as error:
            raise SealForgeryError(
                "this object has the shape of a sealed assignment and not its contents. It "
                "came from object.__new__ rather than from draw(), so no lottery was ever "
                "run for it."
            ) from error

    # ------------------------------------------------------------------ closed routes

    def __setattr__(self, name: str, value: object) -> None:
        raise SealForgeryError(
            f"the assignment is sealed; {name!r} cannot be set. This is the one door with no "
            "key: no unit changes arm after its first observation, not by anyone, including "
            "an approver. From the moment it can, every number the system produces becomes "
            "unfalsifiable."
        )

    def __delattr__(self, name: str) -> None:
        raise SealForgeryError("the assignment is sealed; nothing is deleted from it")

    def __reduce__(self) -> Any:
        raise SealForgeryError(
            "a seal is not serialisable. One that survived a round trip could be restored in "
            "a process where no lottery ever ran. Persist the assignment table and its "
            "digest instead, and re-derive the draw from the committed seed."
        )

    def __copy__(self) -> SealedAssignment:
        return self

    def __deepcopy__(self, _memo: dict[int, object]) -> SealedAssignment:
        return self

    def __repr__(self) -> str:
        return (
            f"<SealedAssignment {self.experiment_id} draw {self.draw_index} "
            f"{len(self.treatment)}T/{len(self.control)}C {self.digest[:12]}…>"
        )


class _Drawer(Protocol):
    def __call__(
        self,
        *,
        experiment_id: str,
        roster: Sequence[str],
        seed: str,
        form_digest: str,
        matrix: CovariateMatrix,
        control_size: int,
    ) -> tuple[SealedAssignment, tuple[Standardised, ...]] | None: ...


class _Verifier(Protocol):
    def __call__(self, subject: object) -> bool: ...


def _build() -> tuple[_Drawer, _Verifier]:
    """Create the witness and the only two functions that know it.

    Everything private to sealing lives in this closure. There is no module-level name bound
    to the witness or to the function that fills a seal's slots, so neither can be imported,
    monkeypatched or reached by autocomplete.
    """
    witness = _Witness()

    def issue(
        *,
        experiment_id: str,
        seed: str,
        draw_index: int,
        strata: Strata,
        arms: MappingProxyType[str, Arm],
        form_digest: str,
        matrix: CovariateMatrix,
    ) -> SealedAssignment:
        seal = object.__new__(SealedAssignment)
        put = object.__setattr__
        put(seal, "_witness", witness)
        put(seal, "_experiment_id", experiment_id)
        put(seal, "_seed", seed)
        put(seal, "_draw_index", draw_index)
        put(seal, "_strata", strata)
        put(seal, "_arms", arms)
        put(seal, "_form_digest", form_digest)
        put(seal, "_covariate_digest", covariate_digest(matrix))
        put(
            seal,
            "_digest",
            digest_for(
                experiment_id=experiment_id,
                seed=seed,
                form_digest=form_digest,
                strata=strata,
                arms=arms,
            ),
        )
        return seal

    def draw(
        *,
        experiment_id: str,
        roster: Sequence[str],
        seed: str,
        form_digest: str,
        matrix: CovariateMatrix,
        control_size: int,
    ) -> tuple[SealedAssignment, tuple[Standardised, ...]] | None:
        """Build the strata, run the lottery within them, and seal candidate 0.

        Returns the seal and the standardised differences the realised draw achieved —
        recorded, not screened: the balance is judged once, at readout, over what actually
        arrived, and a design accepted at 0.02 and one accepted at 0.09 are different
        designs whose figures the report carries either way.

        `None` is not an error: it is a roster on which no stratification gives every
        stratum both arms, and the design engine turns it into a refusal that names what
        would fix it.
        """
        if not experiment_id:
            raise AssignmentError("an assignment belongs to a named experiment")
        if not seed:
            raise AssignmentError(
                "the seed is committed in advance and is never empty. An empty seed is not a "
                "seed nobody chose; it is a seed everybody can reproduce."
            )
        if set(roster) != set(matrix.rows):
            raise AssignmentError(
                "the roster and the covariate matrix describe different units. A unit "
                "assigned without covariates is a unit nobody stratified, and a unit "
                "stratified without an arm is one that could not have been."
            )
        if len(set(roster)) != len(roster):
            raise AssignmentError("a unit appears twice in the roster; each is assigned once")
        strata = strata_of(matrix, control_size)
        if strata is None:
            return None
        arms = candidate(strata, seed=seed, draw_index=0)
        return (
            issue(
                experiment_id=experiment_id,
                seed=seed,
                draw_index=0,
                strata=strata,
                arms=arms,
                form_digest=form_digest,
                matrix=matrix,
            ),
            standardised(matrix, arms),
        )

    def sealed(subject: object) -> bool:
        """Whether `subject` is a seal this process drew and nobody has touched.

        The questions, and each is here because leaving it out leaves a hole:

        1. **the type** — exactly `SealedAssignment`, never a subclass, because subclassing
           raises;
        2. **the stamp** — the witness this process's `draw` holds;
        3. **both arms are populated** — an empty arm makes every later comparison vacuous
           in the same way an empty `PriceBounds()` made a certificate's containment check
           vacuous, which is a defect this repository has already paid for once;
        4. **the digest still describes the strata and the arms** — recomputed here from
           the seal's own fields, so rewriting either without rewriting the digest is a
           contradiction the seal carries about itself.

        It is process-scoped, like `certified()`, and for the same reason: a seal is a
        statement made here, now, by this lottery, about one experiment. That is exactly
        what makes pickling refusable.
        """
        if type(subject) is not SealedAssignment:
            return False
        try:
            stamp = object.__getattribute__(subject, "_witness")
            experiment_id = object.__getattribute__(subject, "_experiment_id")
            seed = object.__getattribute__(subject, "_seed")
            strata = object.__getattribute__(subject, "_strata")
            arms = object.__getattribute__(subject, "_arms")
            form_digest = object.__getattribute__(subject, "_form_digest")
            recorded = object.__getattribute__(subject, "_digest")
        except AttributeError:
            return False
        if stamp is not witness or not isinstance(arms, MappingProxyType):
            return False
        values = set(arms.values())
        if values != {Arm.TREATMENT, Arm.CONTROL}:
            return False
        return bool(
            recorded
            == digest_for(
                experiment_id=experiment_id,
                seed=seed,
                form_digest=form_digest,
                strata=strata,
                arms=arms,
            )
        )

    return draw, sealed


draw, sealed = _build()


# ------------------------------------------------------------------ the reference set


def reference_set(
    seal: SealedAssignment,
    *,
    draws: int,
    max_attempts: int,
) -> tuple[MappingProxyType[str, Arm], ...]:
    """The candidates after the realised one, under the same strata — what the inference
    compares against.

    This is what makes the inference match the restriction. The strata narrow the space of
    admissible assignments, so an ordinary confidence interval — which assumes simple
    randomisation — comes out falsely wide. Comparing the observed statistic against draws
    of **the same rule within the same strata** is the correction, and because nothing is
    screened, every candidate is admissible: the reference set fills to `draws` instead of
    starving, which is the whole reason the stratification replaced the screen.

    The realised draw is **excluded**. It is counted once by the `(1 + hits) / (1 + B)` rule
    in `estimator.permutation_p`; including it here as well would count it twice and make
    every p-value at least `2 / (1 + B)`.

    `max_attempts` caps the candidate indices scanned — a budget rather than an unbounded
    loop, kept in the contract because a bound nobody declared is a bound nobody can check.
    Fewer than `draws` come back only where the budget is set below them; the p-value
    divides by the number actually drawn, and the readout prints it.
    """
    if draws < 1:
        raise AssignmentError("a reference set holds at least one candidate")
    if max_attempts < 1:
        raise AssignmentError("the reference-set budget admits at least one candidate")
    found: list[MappingProxyType[str, Arm]] = []
    strata = seal.strata
    for index in range(max_attempts):
        if len(found) == draws:
            break
        if index == seal.draw_index:
            continue
        found.append(candidate(strata, seed=seal.seed, draw_index=index))
    return tuple(found)


def redraw(seal: SealedAssignment) -> MappingProxyType[str, Arm]:
    """The arms this seal's seed and strata produce, computed again from scratch.

    The contamination check's independent half. The digest catches a rewritten arms table;
    this catches it even when the digest was rewritten to match, because it does not consult
    the seal's arms at all — only its seed, its strata and its draw index.
    """
    return candidate(seal.strata, seed=seal.seed, draw_index=seal.draw_index)
