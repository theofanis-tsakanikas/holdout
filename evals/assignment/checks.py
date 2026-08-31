"""The attack. Chains nobody here drew, and one question: can the lottery be moved?

Ten checks. Each is a sentence that would be false if the check failed, each carries a
number whether it passes or not, and each has an id `make gate-proof` names.

The trap, in one line
---------------------
`CLAUDE.md` on claim 3: *the holdout is neither erased nor chosen after the fact; assignment
from a committed seed, exactly reproducible; the one door with no key.* The obvious way to
check "exactly reproducible" is to run `draw` twice and compare, and it is worth nothing: a
deterministic function repeated agrees with itself, and would agree just as loudly with a
lottery that ignored the seed. So the independence comes in from three other doors, and each
one is named on the check that uses it:

* **another implementation** — `reference.py`, over `blake2b.py`: RFC 7693 written out in
  Python, its own framing, its own rank arithmetic (`A1`, `A2`, `A10`);
* **another path through the same answer** — one unit's arm re-derived from the committed
  record alone, without the seal, without the rest of the roster and without replaying a
  sequence (`A3`);
* **another interpreter** — the whole grid recomputed in a subprocess under a different
  `PYTHONHASHSEED`, which is the only way to see a tie broken by set-iteration order (`A5`).

`A6` to `A9` are the door itself: every route somebody would take to move a store between
arms, and what refuses it — by name, and at readout end to end rather than in a docstring.
"""

from __future__ import annotations

import contextlib
import copy
import os
import pickle
import subprocess
import sys
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from hashlib import blake2b as standard_blake2b
from types import MappingProxyType
from typing import Any

from evals.assignment import build, crossprocess, reference
from evals.assignment.blake2b import blake2b
from evals.report import Check, Report
from holdout.contracts.model import ContractSet
from holdout.core.design import MdeDirection
from holdout.core.experiment import (
    Arm,
    CovariateMatrix,
    ReadoutError,
    ReadoutRefusal,
    ReadoutRefusalCode,
    SealedAssignment,
    SealForgeryError,
    ValidityCheck,
    candidate,
    close,
    digest_for,
    draw,
    reference_set,
    sealed,
    standardised,
    worst_of,
)
from holdout.core.experiment import contamination as contamination_module

#: The metric moment 3 is driven on. Claim 3 reads no metric value — see `build.py` — but
#: `close` resolves one, and a readout that named a metric outside the contract would refuse
#: for a reason that has nothing to do with this claim.
METRIC_ID = "category_margin_per_store_week"

#: Every seventh unit of each roster, for the month-later path in `A3`. A declared stride rather
#: than a sample drawn at random, so a red run reproduces exactly, and seven rather than a round
#: number so that it does not fall in step with any stratum size the grid produces — 2, 3, 5 and
#: 6. That is a precaution and not a proof: the roster is in store-id order and a stratum is a
#: set of similar shops, so the two orders have nothing to do with each other anyway.
PER_UNIT_STRIDE = 7

#: How many candidates `A7` scans for the one that would have flattered the design. Twenty-four
#: is a budget and it says so: the check is that **no** candidate can be substituted, and the
#: number only decides how strong an incentive the run is able to report.
CANDIDATE_SCAN = 24

#: The interpreter hash seeds `A5` asks for the same answer under. `0` is what `gate-proof`
#: itself sets, so the other two are the ones that could disagree with it.
HASH_SEEDS = ("0", "1", "524287")

#: The declared sweep `A10` drives the second implementation over. The messages are
#: `bytes(index % 256 for index in range(n))` — deterministic, so a red run reproduces exactly.
#:
#: The lengths are chosen against what would actually go wrong: the empty message, both sides of
#: every 128-byte block boundary, and two multi-block lengths, because the counter fed to the
#: compression function and the last-block flag are the two things a plausible reimplementation
#: gets wrong and neither is exercised inside one block. The committed digest's own message —
#: a stratum list, a roster and an arm per unit — measures **623 to 13,022 bytes** across the
#: thirty configurations `A2` hashes, and 3,324 to 13,022 over the twenty-four at the contract's
#: own share. 4,096 is inside that range rather than a round number, so the chaining is driven
#: instead of extrapolated to. It is a declared sweep and not an exhaustive one: it straddles
#: one 128-byte boundary and samples four lengths beyond it, which is enough to exercise the
#: block counter and the last-block flag and is not a claim to have covered every length.
SWEEP_MESSAGE_LENGTHS = (0, 1, 63, 64, 65, 127, 128, 129, 200, 1000, 4096)
#: 32 bytes is the key width the lottery uses; 0, 1 and 64 are the boundaries of the keyed mode.
SWEEP_KEY_LENGTHS = (0, 1, 32, 64)
#: 16 and 32 are the widths the lottery uses — a rank and a digest; 1 and 64 are the boundaries.
SWEEP_DIGEST_SIZES = (1, 16, 32, 64)

#: RFC 7693 Appendix A — the published BLAKE2b-512 digest of the message `abc`. The one input
#: in this eval whose expected answer was chosen by somebody who has never seen this
#: repository. Verified 2026-08-29 against Python's own `hashlib.blake2b`, which is a third
#: implementation again and agrees with both.
RFC_7693_ABC = (
    "ba80a53f981c4d0d6a2797b69f12f6e94c212f14685ac4b74b12bb6fdbffa2d1"
    "7d87c5392aab792dc252d5de4533cc9518d38aa8dbf1925ab92386edd4009923"
)


def _fraction(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0/0"
    return f"{numerator}/{denominator} = {100 * numerator / denominator:.2f}%"


@contextlib.contextmanager
def _rewritten(seal: SealedAssignment, **slots: Any) -> Iterator[None]:
    """Write directly into a seal's slots and put them back afterwards.

    `object.__setattr__` is the one route `SealedAssignment.__setattr__` cannot close, and
    it is therefore the route an attacker takes. Used here to *be* that attacker; the
    restore is asserted by the caller, because an eval that left a tampered seal behind
    would be measuring its own damage from then on.
    """
    original = {name: object.__getattribute__(seal, name) for name in slots}
    for name, value in slots.items():
        object.__setattr__(seal, name, value)
    try:
        yield
    finally:
        for name, value in original.items():
            object.__setattr__(seal, name, value)


def _arms_as_strings(seal: SealedAssignment) -> dict[str, str]:
    return {unit: seal.arms[unit].value for unit in seal.roster}


def _core_digest(seal: SealedAssignment, arms: Mapping[str, Arm]) -> str:
    """The digest the core would record for these arms — the careful forger's recomputation."""
    return digest_for(
        experiment_id=seal.experiment_id,
        seed=seal.seed,
        form_digest=seal.form_digest,
        strata=seal.strata,
        arms=arms,
    )


# --------------------------------------------------------------- A1 · the second implementation


def check_arms_match_an_independent_lottery(drawn: Sequence[build.Drawn]) -> Check:
    """A1 — the claim's first half, computed twice and compared unit by unit."""
    agreed = 0
    total = 0
    failures: list[str] = []
    for item in drawn:
        seal = item.seal
        if seal is None:
            continue
        theirs = reference.lottery(seal.strata, seed=seal.seed, draw_index=seal.draw_index)
        ours = _arms_as_strings(seal)
        for unit in seal.roster:
            total += 1
            if theirs.get(unit) == ours[unit]:
                agreed += 1
            elif len(failures) < 40:
                failures.append(
                    f"{item.configuration.origin}: {unit} is {ours[unit]} and the "
                    f"independent lottery draws {theirs.get(unit)}"
                )
    return Check(
        id="A1.arms-match-an-independently-implemented-lottery",
        question=(
            "Over every unit of every configuration, does the arm the system drew equal the "
            "arm a second implementation of the lottery draws — a BLAKE2b written out from "
            "RFC 7693, its own framing, its own rank arithmetic?"
        ),
        passed=not failures,
        figure=f"{_fraction(agreed, total)} units agree across {len(drawn)} configurations",
        detail=(
            "the two share the published definition of the draw and no line of code; see "
            "evals/assignment/reference.py's table"
        ),
        counterexamples=tuple(failures),
    )


def check_digest_matches_an_independent_recomputation(drawn: Sequence[build.Drawn]) -> Check:
    """A2 — the digest is what survives a table, so it is recomputed by the other hash."""
    agreed = 0
    total = 0
    failures: list[str] = []
    for item in drawn:
        seal = item.seal
        if seal is None:
            continue
        total += 1
        theirs = reference.digest_for(
            experiment_id=seal.experiment_id,
            seed=seal.seed,
            form_digest=seal.form_digest,
            strata=seal.strata,
            arms=_arms_as_strings(seal),
        )
        if theirs == seal.digest:
            agreed += 1
        else:
            failures.append(
                f"{item.configuration.origin}: recorded {seal.digest[:16]}…, independent "
                f"recomputation {theirs[:16]}…"
            )
    return Check(
        id="A2.the-committed-digest-matches-an-independent-recomputation",
        question=(
            "Is the digest recorded on every seal the digest an independently framed, "
            "independently hashed recomputation puts on the same experiment, seed, form, "
            "strata, roster and arms?"
        ),
        passed=not failures,
        figure=f"{_fraction(agreed, total)} seals",
        detail="length-prefixed by struct.pack rather than by a buffer, and hashed in Python",
        counterexamples=tuple(failures),
    )


def check_a_unit_is_re_derivable_on_its_own(drawn: Sequence[build.Drawn]) -> Check:
    """A3 — the month-later path: one store's arm, from the committed record alone."""
    agreed = 0
    total = 0
    failures: list[str] = []
    for item in drawn:
        seal = item.seal
        if seal is None:
            continue
        stratum_of = {unit: stratum for stratum in seal.strata for unit in stratum}
        for index, unit in enumerate(seal.roster):
            if index % PER_UNIT_STRIDE:
                continue
            total += 1
            theirs = reference.arm_of(
                unit,
                stratum=stratum_of[unit],
                seed=seal.seed,
                draw_index=seal.draw_index,
            )
            if theirs == seal.arm_of(unit).value:
                agreed += 1
            else:
                failures.append(
                    f"{item.configuration.origin}: {unit} re-derives as {theirs} and is "
                    f"recorded as {seal.arm_of(unit).value}"
                )
    return Check(
        id="A3.a-unit-s-arm-is-re-derivable-from-the-committed-record-alone",
        question=(
            "Can one store's arm be re-derived a month later from the committed seed, the "
            "candidate index and that store's own stratum — without the seal, without the "
            "rest of the roster, and without replaying any sequence?"
        ),
        passed=not failures,
        figure=f"{_fraction(agreed, total)} units, every {PER_UNIT_STRIDE}th of each roster",
        detail=(
            "an arm follows from the seed, the candidate index and the stratum with no "
            "sequence to replay, which is why `redraw` can re-derive every unit from the "
            "committed record instead of trusting the arms column it was handed"
        ),
        counterexamples=tuple(failures),
    )


# --------------------------------------------------------------------- A4, A5 · reproducibility


def check_order_does_not_reach_the_answer(drawn: Sequence[build.Drawn]) -> Check:
    """A4 — the same inputs, presented in a different order, and the same lottery."""
    permutations = ("reversed", "rotated")
    agreed = 0
    total = 0
    failures: list[str] = []
    for item in drawn:
        seal = item.seal
        if seal is None:
            continue
        configuration = item.configuration
        for name in permutations:
            total += 1
            roster = _permuted(configuration.roster, name)
            matrix = CovariateMatrix.of(
                configuration.matrix.ids,
                configuration.matrix.kinds,
                {unit: configuration.matrix.rows[unit] for unit in roster},
            )
            again = draw(
                experiment_id=configuration.experiment_id,
                roster=roster,
                seed=configuration.experiment_seed,
                form_digest=configuration.form_digest,
                matrix=matrix,
                control_size=configuration.control_size,
            )
            if again is None:
                failures.append(f"{configuration.origin} ({name}): no lottery at all this time")
                continue
            other = again[0]
            moved = [u for u in seal.roster if other.arms.get(u) is not seal.arms[u]]
            # Everything the seal commits to, not only the arms. The covariate digest is on
            # the seal so a readout can say whether the covariates it is re-measuring are the
            # ones the strata were built from, and the standardised differences are the
            # figures the design is reported with — a record that moves when the roster is
            # written down in another order is a record nobody can reproduce either.
            if (
                other.strata == seal.strata
                and not moved
                and other.covariate_digest == seal.covariate_digest
                and again[1] == item.differences
            ):
                agreed += 1
            elif moved:
                failures.append(
                    f"{configuration.origin} ({name}): {len(moved)} unit(s) changed arm"
                )
            elif other.strata != seal.strata:
                failures.append(f"{configuration.origin} ({name}): the strata moved")
            elif other.covariate_digest != seal.covariate_digest:
                failures.append(
                    f"{configuration.origin} ({name}): the covariate digest moved — "
                    f"{seal.covariate_digest[:16]}… became {other.covariate_digest[:16]}…"
                )
            else:
                failures.append(
                    f"{configuration.origin} ({name}): the recorded standardised differences moved"
                )
    return Check(
        id="A4.the-lottery-does-not-depend-on-the-order-its-inputs-arrived-in",
        question=(
            "Presented with the same roster and the same covariates written down in a "
            "different order, does the engine commit to the same record — the same strata, "
            "the same arms, the same covariate digest and the same balance figures?"
        ),
        passed=not failures,
        figure=f"{_fraction(agreed, total)} re-presentations, {len(permutations)} per configuration",
        detail="a roster that moves with its input order is an experiment nobody can reproduce",
        counterexamples=tuple(failures),
    )


def _permuted(roster: tuple[str, ...], name: str) -> tuple[str, ...]:
    if name == "reversed":
        return tuple(reversed(roster))
    half = len(roster) // 2
    return roster[half:] + roster[:half]


def check_a_fresh_interpreter_reproduces(here: str) -> Check:
    """A5 — the answer under another process's string hashing. See `crossprocess.py`.

    **One of the three may be repetition, and the figure says which.** `gate_proof.engine`
    runs an eval with `PYTHONHASHSEED=0`, so under `make claim-3` the parent is at 0 and the
    child at `"0"` is bit-identical by construction — the very thing this check exists to
    replace. Under `make eval-assignment` from a shell the parent's seed is randomised and all
    three are informative. Rather than drop the seed or pretend, the check counts how many
    children run at a seed the parent is not using and publishes that beside the total.
    """
    parent = os.environ.get("PYTHONHASHSEED")
    informative = sum(1 for seed in HASH_SEEDS if seed != parent)
    agreed = 0
    failures: list[str] = []
    for seed in HASH_SEEDS:
        environment = dict(os.environ)
        environment["PYTHONHASHSEED"] = seed
        completed = subprocess.run(
            [sys.executable, "-m", "evals.assignment.crossprocess"],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        theirs = completed.stdout.strip().splitlines()[-1:] or [""]
        if completed.returncode == 0 and theirs[0] == here:
            agreed += 1
        else:
            tail = (completed.stderr or completed.stdout).strip().splitlines()[-1:]
            failures.append(
                f"PYTHONHASHSEED={seed}: {theirs[0][:16] or 'no output'}… against "
                f"{here[:16]}…" + (f" ({tail[0]})" if completed.returncode else "")
            )
    return Check(
        id="A5.the-same-committed-seed-reproduces-in-a-fresh-interpreter",
        question=(
            "Recomputed from scratch in another interpreter, under a different "
            "PYTHONHASHSEED, does the whole grid produce the same strata and the same arms?"
        ),
        passed=not failures,
        figure=(
            f"{_fraction(agreed, len(HASH_SEEDS))} interpreters agree, {informative} of them "
            f"at a seed the parent is not using · {here[:16]}…"
        ),
        detail=(
            "Python randomises string hashing per process, so a tie broken by set-iteration "
            "order answers differently here and identically under any in-process repetition"
        ),
        counterexamples=tuple(failures),
    )


# ------------------------------------------------------------------------ A6 · the door itself


@dataclass(frozen=True, slots=True)
class Route:
    """One way somebody would move a store between arms, and what is supposed to stop it."""

    name: str
    refused_by: str


#: Every in-process route, and the thing that is supposed to refuse it. The first nine are run
#: against **every** seal in the grid; the last three do not need one and are run once.
ROUTES = (
    Route("assign to .arms", "SealForgeryError from __setattr__"),
    Route("delete a slot", "SealForgeryError from __delattr__"),
    Route("call the constructor", "SealForgeryError from __init__"),
    Route("pickle and restore", "SealForgeryError from __reduce__"),
    Route("deepcopy into a fillable object", "__deepcopy__ returns the same object"),
    Route("write .arms with object.__setattr__", "sealed() recomputes the digest"),
    Route("write .seed with object.__setattr__", "sealed() recomputes the digest"),
    Route("write .strata with object.__setattr__", "sealed() recomputes the digest"),
    Route("point the seal at another design", "sealed() recomputes the digest"),
    Route("an empty shell from object.__new__", "sealed() finds no witness"),
    Route("a look-alike with the same fields", "sealed() checks the exact type"),
    Route("declare a subclass", "TypeError from __init_subclass__"),
)

#: The first nine routes need a seal; the last three do not. Split so that the figure `A6`
#: publishes adds up — nine attempts per seal plus three, and not a count nobody can rebuild.
PER_SEAL_ROUTES = 9


def _routes_refused(seal: SealedAssignment) -> list[tuple[Route, bool]]:
    """Every in-process route, run against one seal, with what each one produced.

    A free function rather than a loop body, so nothing here closes over a loop variable and
    the attacker's lambdas cannot quietly all point at the last seal in the grid.
    """
    flipped = MappingProxyType({unit: arm.other for unit, arm in seal.arms.items()})
    outcomes: list[tuple[Route, bool]] = [
        (ROUTES[0], _raises(lambda: setattr(seal, "arms", {}))),
        (ROUTES[1], _raises(lambda: delattr(seal, "_arms"))),
        (ROUTES[2], _raises(lambda: type(seal)())),
        (ROUTES[3], _raises(lambda: pickle.dumps(seal))),
        (ROUTES[4], copy.deepcopy(seal) is seal and copy.copy(seal) is seal),
    ]
    for route, slots in (
        (ROUTES[5], {"_arms": flipped}),
        (ROUTES[6], {"_seed": seal.seed + "-x"}),
        (ROUTES[7], {"_strata": tuple(reversed(seal.strata))}),
        (ROUTES[8], {"_form_digest": "0" * 64}),
    ):
        with _rewritten(seal, **slots):
            outcomes.append((route, not sealed(seal)))
    return outcomes


def check_no_route_moves_a_unit(drawn: Sequence[build.Drawn]) -> Check:
    """A6 — doctrine rule 7, walked as an attacker rather than described as a property."""
    refused = 0
    attempted = 0
    failures: list[str] = []

    for item in drawn:
        seal = item.seal
        if seal is None:
            continue
        where = item.configuration.origin
        for route, was_refused in _routes_refused(seal):
            attempted += 1
            if was_refused:
                refused += 1
            elif len(failures) < 40:
                failures.append(f"{where}: {route.name} was not refused — {route.refused_by}")
        if not sealed(seal):
            failures.append(f"{where}: the seal did not survive being attacked and restored")

    shell = object.__new__(SealedAssignment)
    for route, was_refused in (
        (ROUTES[9], not sealed(shell) and _raises(lambda: shell.arms)),
        (ROUTES[10], not sealed(_LookAlike())),
        (ROUTES[11], _raises(_declare_a_subclass)),
    ):
        attempted += 1
        if was_refused:
            refused += 1
        else:
            failures.append(f"{route.name} was not refused — {route.refused_by}")

    return Check(
        id="A6.no-in-process-route-moves-a-unit-between-arms",
        question=(
            "Doctrine rule 7 — walking every route an attacker would take inside the process, "
            "is each one refused, by the seal itself rather than by something downstream?"
        ),
        passed=not failures,
        figure=(
            f"{_fraction(refused, attempted)} attempts refused · {len(ROUTES)} declared "
            f"routes, {PER_SEAL_ROUTES} of them against every seal"
        ),
        detail=(
            "judged on the seal alone: an exception, or sealed() answering False. The routes "
            "through a table are A7 and A8, where the contamination check is what refuses"
        ),
        counterexamples=tuple(failures),
    )


class _LookAlike:
    """Something with a seal's field names and none of its provenance."""

    def __init__(self) -> None:
        self._witness = object()
        self._experiment_id = "look-alike"
        self._seed = "look-alike"
        self._strata = (("a", "b"),)
        self._arms = MappingProxyType({"a": Arm.CONTROL, "b": Arm.TREATMENT})
        self._form_digest = "0" * 64
        self._digest = "0" * 64


def _declare_a_subclass() -> None:
    class _Subclass(SealedAssignment):  # pragma: no cover - the class body never runs
        pass


def _raises(action: Any) -> bool:
    try:
        action()
    except (SealForgeryError, TypeError):
        return True
    except Exception:
        return False
    return False


# --------------------------------------------------------- A7, A8 · the routes through a table


@dataclass(frozen=True, slots=True)
class Substitution:
    """The candidate somebody would have preferred, and what it would have bought them."""

    origin: str
    realised: Decimal | None
    realised_index: int
    best: Decimal | None
    best_index: int
    arms: MappingProxyType[str, Arm]

    @property
    def improvement(self) -> Decimal:
        if self.realised is None or self.best is None:
            return Decimal(0)
        return self.realised - self.best


def flattering(drawn: Sequence[build.Drawn]) -> tuple[Substitution, ...]:
    """For each seal, the candidate in the reference set with the best pre-period balance.

    This is the fishing expedition claim 3 exists to make impossible, run on purpose: the
    committed seed generates every candidate, so anyone holding the seed can see which one
    would have flattered the design before deciding which to write down.
    """
    found: list[Substitution] = []
    for item in drawn:
        seal = item.seal
        if seal is None:
            continue
        realised = worst_of(item.differences).value
        best_value = realised
        best_index = seal.draw_index
        best_arms = seal.arms
        for index in range(1, CANDIDATE_SCAN + 1):
            arms = candidate(seal.strata, seed=seal.seed, draw_index=index)
            value = worst_of(standardised(item.configuration.matrix, arms)).value
            if value is not None and (best_value is None or value < best_value):
                best_value, best_index, best_arms = value, index, arms
        found.append(
            Substitution(
                origin=item.configuration.origin,
                realised=realised,
                realised_index=seal.draw_index,
                best=best_value,
                best_index=best_index,
                arms=best_arms,
            )
        )
    return tuple(found)


def check_a_flattering_candidate_cannot_be_substituted(
    drawn: Sequence[build.Drawn], substitutions: Sequence[Substitution]
) -> Check:
    """A7 — *nor chosen after the fact*, driven with the forger who fixes the digest too."""
    refused = 0
    attempted = 0
    failures: list[str] = []
    by_origin = {s.origin: s for s in substitutions}
    designs = 0
    for item in drawn:
        seal = item.seal
        if seal is None:
            continue
        substitution = by_origin[item.configuration.origin]
        if substitution.best_index == seal.draw_index:
            continue
        designs += 1
        delivered = build.delivered_by_arm(seal)

        # The careless forger: the arms are rewritten and the digest is left behind.
        attempted += 1
        with _rewritten(seal, _arms=substitution.arms):
            careless = _contamination(seal, delivered, item.configuration.form_digest)
        if not careless.digest_matches:
            refused += 1
        else:
            failures.append(f"{substitution.origin}: a rewritten arms table matched its digest")

        # The careful forger: the digest is recomputed so that the seal agrees with itself.
        attempted += 1
        with _rewritten(
            seal,
            _arms=substitution.arms,
            _digest=_core_digest(seal, substitution.arms),
        ):
            careful = _contamination(seal, delivered, item.configuration.form_digest)
        if not careful.redraw_matches and not careful.is_clean:
            refused += 1
        else:
            failures.append(
                f"{substitution.origin}: candidate {substitution.best_index} was substituted "
                "and the redraw agreed with it"
            )
        if not sealed(seal):
            failures.append(f"{substitution.origin}: the seal did not survive being restored")

    if not designs:
        failures.append(
            "no configuration in the grid has a better-balanced candidate within the scan, so "
            "this check asked nothing. A check that cannot fail is one somebody will later "
            "mistake for a check that passed."
        )
    return Check(
        id="A7.a-flattering-candidate-cannot-be-substituted-after-the-fact",
        question=(
            "Someone holding the committed seed can see every candidate and which one would "
            "have flattered the design. Substituting it — even recomputing the digest so the "
            "seal agrees with itself — is refused?"
        ),
        passed=not failures,
        figure=(
            f"{_fraction(refused, attempted)} forgeries refused, over the {designs} design(s) "
            "of {total} where a better-balanced candidate exists — careless and careful each"
        ).replace("{total}", str(len(substitutions))),
        detail=(
            "the careful forger is the one that matters: the digest half of the contamination "
            "check passes for them, and only the redraw refuses"
        ),
        counterexamples=tuple(failures),
    )


def _contamination(seal: SealedAssignment, delivered: Mapping[str, str], form_digest: str) -> Any:
    return contamination_module.check(
        seal,
        delivered=delivered,
        treatment_policy=build.TREATMENT_POLICY,
        control_policy=build.CONTROL_POLICY,
        form_digest=form_digest,
    )


@dataclass(frozen=True, slots=True)
class ErasureRoute:
    """One way to erase a unit or an arm, and the two things that must refuse it.

    `readout_guard` is the phrase `close`'s refusal has to carry, declared **per route**
    rather than left as "any `ReadoutError`". The two routes that delete a store are refused
    because that store still reports an outcome; the one that empties the holdout is refused
    because an arm is gone. Counting any exception as either would let a reordering of
    `close`'s guards keep this check green while changing which sentence is true.
    """

    name: str
    readout_guard: str


ERASURE_ROUTES = (
    ErasureRoute("a control store deleted", "never assigned"),
    ErasureRoute("the holdout emptied", "attrition emptied an arm"),
    ErasureRoute("a control store deleted, digest rewritten", "never assigned"),
)


@dataclass(frozen=True, slots=True)
class Erasure:
    """One route run against one seal, and what each of the two layers did about it."""

    route: ErasureRoute
    origin: str
    caught_by_the_contamination_check: bool
    refused_by_the_readout: bool
    readout_said: str

    @property
    def refused(self) -> bool:
        return self.caught_by_the_contamination_check and self.refused_by_the_readout


def erasures(drawn: Sequence[build.Drawn], contracts: ContractSet) -> tuple[Erasure, ...]:
    """The three erasure routes, run against every seal, judged at **both** layers.

    Both, and not either, because the two answer different questions and this eval found out
    the hard way what happens when only one of them is asked. Until 2026-08-29
    `contamination.check` walked a roster it derived from the arms it was checking, so route
    3 — a store deleted with the digest recomputed to match — was invisible to it, and the
    only thing refusing that erasure was `close`'s stray-outcome guard, which holds solely
    while the erased store still reports an outcome. The check now compares the key set of
    the redraw, which comes from the committed strata; `docs/DECISIONS.md` records the gap
    and its closure rather than overwriting either.
    """
    found: list[Erasure] = []
    for item in drawn:
        seal = item.seal
        if seal is None or not seal.control:
            continue
        origin = item.configuration.origin
        delivered = build.delivered_by_arm(seal)
        form_digest = item.configuration.form_digest
        victim = seal.control[0]
        without = MappingProxyType({u: a for u, a in seal.arms.items() if u != victim})
        emptied = MappingProxyType(dict.fromkeys(seal.roster, Arm.TREATMENT))

        for route, slots in (
            # 1 · a control store deleted from the table, and nothing else touched.
            (ERASURE_ROUTES[0], {"_arms": without}),
            # 2 · the holdout emptied outright, with the digest recomputed to match.
            (
                ERASURE_ROUTES[1],
                {"_arms": emptied, "_digest": _core_digest(seal, emptied)},
            ),
            # 3 · the coordinated deletion: the store removed and the digest rewritten to agree.
            (
                ERASURE_ROUTES[2],
                {"_arms": without, "_digest": _core_digest(seal, without)},
            ),
        ):
            with _rewritten(seal, **slots):
                caught = not _contamination(seal, delivered, form_digest).is_clean
                refused, said = _refused_by_the_readout(item, seal, contracts, route)
            found.append(
                Erasure(
                    route=route,
                    origin=origin,
                    caught_by_the_contamination_check=caught,
                    refused_by_the_readout=refused,
                    readout_said=said,
                )
            )
    return tuple(found)


def _refused_by_the_readout(
    item: build.Drawn, seal: SealedAssignment, contracts: ContractSet, route: ErasureRoute
) -> tuple[bool, str]:
    """Whether moment 3 refuses this seal **for the erasure**, rather than merely refusing.

    The distinction is the whole point of the second layer. A readout that declines
    `POWER_NOT_REACHED` on an assignment somebody has emptied has caught nothing — it
    declined for an unrelated reason and would have declined identically on an intact one.
    So the only answer that counts is `close` refusing to run at all, with the refusal
    carrying the phrase this route declared in advance.
    """
    try:
        result = _close(item, seal, contracts)
    except ReadoutError as error:
        said = str(error).split(".")[0][:70]
        return route.readout_guard in str(error), f"ReadoutError: {said}"
    if isinstance(result, ReadoutRefusal):
        return False, "refused for an unrelated reason: " + ", ".join(
            code.value for code in result.codes
        )
    return False, "a number was stated"


def check_an_erased_holdout_is_refused(found: Sequence[Erasure]) -> Check:
    """A8 — *the holdout is neither erased*, judged at both layers that are supposed to see it."""
    caught = sum(1 for e in found if e.caught_by_the_contamination_check)
    refused = sum(1 for e in found if e.refused_by_the_readout)
    failures = [
        f"{e.origin}: {e.route.name} — "
        + (
            "the contamination check reported the assignment intact"
            if not e.caught_by_the_contamination_check
            else f"the readout did not name it ({e.readout_said})"
        )
        for e in found
        if not e.refused
    ]
    if not found:
        failures.append(
            "no erasure was driven, so this check asked nothing. A check that cannot fail is "
            "one somebody will later mistake for a check that passed."
        )
    return Check(
        id="A8.an-erased-holdout-is-refused",
        question=(
            "Erase a control store from the assignment table, or empty the holdout outright — "
            "is the erasure refused by the contamination check **and** named by the readout, "
            "whichever route it took? A readout that declined POWER_NOT_REACHED has not "
            "caught anything."
        ),
        passed=not failures,
        figure=(
            f"{_fraction(caught, len(found))} caught by the contamination check · "
            f"{_fraction(refused, len(found))} named by the readout"
        ),
        detail=(
            "both layers, not either. The contamination check compares the key set of the "
            "redraw, which comes from the committed strata; the readout refuses an outcome "
            "from a unit it never assigned. Each is a declared phrase, matched per route"
        ),
        counterexamples=tuple(failures[:40]),
    )


# --------------------------------------------------------------- A9 · the refusal, end to end


def _close(item: build.Drawn, seal: SealedAssignment, contracts: ContractSet) -> Any:
    """Moment 3, driven. Claim 3 reads only the contamination check's own result."""
    configuration = item.configuration
    outcomes = dict(configuration.outcomes)
    mean = sum(outcomes.values()) / len(outcomes)
    return close(
        seal,
        outcomes=outcomes,
        exposed=frozenset(seal.treatment),
        delivered=build.delivered_by_arm(seal),
        treatment_policy=build.TREATMENT_POLICY,
        control_policy=build.CONTROL_POLICY,
        covariates_at_close=configuration.matrix,
        draws=reference_set(
            seal,
            draws=build.REFERENCE_DRAWS,
            max_attempts=contracts.inference.max_assignment_attempts,
        ),
        inference=contracts.inference,
        metric=contracts.metric_versions(METRIC_ID)[-1],
        # Derived, and the arithmetic is written out: a tenth of the mean unit outcome. It
        # decides the power check alone, which claim 3 neither asserts nor reads.
        mde_absolute=Fraction(round(mean), 10),
        direction=MdeDirection.EITHER,
        form_digest=configuration.form_digest,
        data_version=f"corpus/world/{configuration.world_id}@{configuration.chain_seed}",
        period=configuration.period,
        asked_on=configuration.period.ends_on,
    )


def _contamination_result(result: Any) -> bool:
    for check in result.checks:
        if check.check is ValidityCheck.CONTAMINATION:
            return bool(check.passed)
    raise AssertionError("a readout without a contamination check")  # pragma: no cover


def check_a_tampered_assignment_refuses_at_readout(
    drawn: Sequence[build.Drawn],
    substitutions: Sequence[Substitution],
    contracts: ContractSet,
) -> Check:
    """A9 — the code that actually comes out of moment 3, not the function that would produce it.

    `CLAUDE.md`: *a sentence naming what the system does when something goes wrong is
    written against the function that would make it true — named — and against the
    measurement of what comes out when it runs.* So the readout is run, twice per
    configuration, and the code is read off the refusal.
    """
    clean_passed = 0
    tampered_refused = 0
    substituted = 0
    total = 0
    failures: list[str] = []
    by_origin = {s.origin: s for s in substitutions}
    for item in drawn:
        seal = item.seal
        if seal is None:
            continue
        origin = item.configuration.origin
        total += 1
        honest = _close(item, seal, contracts)
        if _contamination_result(honest):
            clean_passed += 1
        else:
            failures.append(f"{origin}: an untouched assignment failed its own contamination check")

        substitution = by_origin[origin]
        if substitution.best_index == substitution.realised_index:
            continue
        substituted += 1
        with _rewritten(
            seal,
            _arms=substitution.arms,
            _digest=_core_digest(seal, substitution.arms),
        ):
            tampered = _close(item, seal, contracts)
        codes = getattr(tampered, "codes", ())
        if ReadoutRefusalCode.CONTAMINATED_ASSIGNMENT in codes:
            tampered_refused += 1
        else:
            failures.append(
                f"{origin}: a substituted assignment read out as "
                + (", ".join(c.value for c in codes) if codes else "a number")
            )
    if not substituted:
        failures.append(
            "no readout was substituted, so the second half of this check asked nothing"
        )
    return Check(
        id="A9.a-tampered-assignment-refuses-at-readout-with-its-own-code",
        question=(
            "Driven through the whole of moment 3, does an untouched assignment pass its "
            "contamination check and a substituted one refuse with CONTAMINATED_ASSIGNMENT?"
        ),
        passed=not failures,
        figure=(
            f"{_fraction(clean_passed, total)} clean readouts pass · "
            f"{_fraction(tampered_refused, substituted)} substituted readouts refuse by name"
        ),
        detail="both halves matter: a check that refuses everything proves nothing",
        counterexamples=tuple(failures[:40]),
    )


# ------------------------------------------------------------------------- A10 · the instrument


def check_the_second_implementation_is_a_blake2b() -> Check:
    """A10 — the eval's own hash, against a published vector and against the standard library.

    Without this the agreement `A1` and `A2` report would be worth nothing: two
    implementations agree loudly when both are wrong in the same way, and the way to tell is
    an answer chosen by somebody who has never seen either.
    """
    failures: list[str] = []
    if blake2b(b"abc").hex() != RFC_7693_ABC:
        failures.append(
            f"RFC 7693 Appendix A publishes {RFC_7693_ABC[:16]}… for 'abc'; this "
            f"implementation gives {blake2b(b'abc').hex()[:16]}…"
        )
    agreed = 0
    total = 0
    for length in SWEEP_MESSAGE_LENGTHS:
        message = bytes(index % 256 for index in range(length))
        for key_length in SWEEP_KEY_LENGTHS:
            key = bytes(index % 256 for index in range(key_length))
            for size in SWEEP_DIGEST_SIZES:
                total += 1
                mine = blake2b(message, key=key, digest_size=size)
                theirs = standard_blake2b(message, key=key, digest_size=size).digest()
                if mine == theirs:
                    agreed += 1
                elif len(failures) < 10:
                    failures.append(
                        f"message {length}B, key {key_length}B, digest {size}B: "
                        f"{mine.hex()[:16]}… against {theirs.hex()[:16]}…"
                    )
    return Check(
        id="A10.the-second-implementation-is-a-blake2b",
        unarmed_because=(
            "it measures the eval's own BLAKE2b against RFC 7693's published vector. Nothing in ` "
            "src/holdout/` can move it; a break would be in `evals/assignment/blake2b.py`, which  "
            "is the instrument. See `evals/assignment/README.md` §6."
        ),
        question=(
            "Does the eval's own BLAKE2b reproduce the digest RFC 7693 publishes, and agree "
            "with the standard library over a declared sweep — both sides of a 128-byte block "
            "boundary, four multi-block lengths, and every key width and digest size the "
            "lottery uses?"
        ),
        passed=not failures,
        figure=f"RFC 7693 Appendix A reproduced · {_fraction(agreed, total)} of a declared sweep",
        detail=(
            "this proves the composition — which bytes, keyed or prefixed, how wide, which "
            "way round. It proves nothing about BLAKE2b, and nothing here claims to"
        ),
        counterexamples=tuple(failures),
    )


# ------------------------------------------------------------------------------------- the run


def run(contracts: ContractSet | None = None) -> Report:
    """Every check, over the declared grid. Numbers whether or not anything failed."""
    resolved = contracts if contracts is not None else _load()
    configurations = build.configurations(resolved)
    drawn = tuple(build.run_the_lottery(configuration) for configuration in configurations)
    live = tuple(item for item in drawn if item.seal is not None)
    refused = tuple(item for item in drawn if item.seal is None)
    substitutions = flattering(live)
    # Moments 3 is driven only where an arm is large enough to estimate a variance from. The
    # swept shares run at `smoke`, where five control units against a five-parameter adjusted
    # model leave no residual degrees of freedom at all — `EstimatorError`, and correctly so.
    # Those configurations are in the grid to reach the refusal a 20% share cannot reach, not
    # to read anything out, and driving them would be testing the estimator's arithmetic under
    # a claim that is about the lottery.
    readable = tuple(item for item in live if item.configuration.at_the_contract_share)
    found = erasures(readable, resolved)

    units = sum(len(item.configuration.roster) for item in live)
    controls = sum(len(item.seal.control) for item in live if item.seal is not None)
    movable = [s for s in substitutions if s.best_index != s.realised_index]
    improvement = (
        sum((s.improvement for s in movable), Decimal(0)) / len(movable) if movable else Decimal(0)
    )

    checks = (
        check_arms_match_an_independent_lottery(live),
        check_digest_matches_an_independent_recomputation(live),
        check_a_unit_is_re_derivable_on_its_own(live),
        check_order_does_not_reach_the_answer(live),
        check_a_fresh_interpreter_reproduces(crossprocess.fingerprint()),
        check_no_route_moves_a_unit(live),
        check_a_flattering_candidate_cannot_be_substituted(live, substitutions),
        check_an_erased_holdout_is_refused(found),
        check_a_tampered_assignment_refuses_at_readout(readable, substitutions, resolved),
        check_the_second_implementation_is_a_blake2b(),
    )

    return Report(
        claim=3,
        title="the holdout is neither erased nor chosen after the fact",
        checks=checks,
        numbers=(
            ("configurations", f"{len(configurations)} declared · {len(live)} drew a lottery"),
            (
                "no admissible stratification",
                f"{len(refused)}, all of them at a swept share of "
                + ", ".join(sorted({str(i.configuration.holdout_share_pct) for i in refused}))
                + "% — the contract's "
                f"{resolved.inference.holdout_share_pct}% never reaches it",
            ),
            ("units under lottery", f"{units} · {controls} of them held back"),
            ("candidates scanned for a flattering one", str(CANDIDATE_SCAN)),
            (
                "the incentive to fish",
                f"a better-balanced candidate exists for {len(movable)}/{len(substitutions)} "
                f"designs, improving the worst SMD by {improvement:.4f} on average",
            ),
            (
                "erasure routes driven",
                f"{len(found)} through moment 3 — {len(ERASURE_ROUTES)} routes over the "
                f"{len(readable)} configurations at the contract's share · {len(ROUTES)} "
                f"in-process routes, {PER_SEAL_ROUTES} of them per seal",
            ),
            ("interpreters asked", " · ".join(f"PYTHONHASHSEED={s}" for s in HASH_SEEDS)),
        ),
        notes=(
            "that the *definition* of the lottery is right. Both implementations compute the "
            "same specification — a keyed BLAKE2b rank, the smallest in each stratum takes "
            "the holdout — and two implementations of one definition cannot tell you the "
            "definition was a good one",
            "that a coordinated forgery is caught. A seal whose arms, seed, strata and digest "
            "are all rewritten together agrees with itself; the limit is asserted rather than "
            "hidden, here and in tests/core/test_assignment_forgery.py",
            "that these strata are the strata a real design draws under. Three of the "
            "contract's five balance covariates are matched on here, because the other two "
            "need a POS aggregation; evals/uplift/ draws over all five, 200 times",
            "that the door holds against routes nobody thought of. Twelve in-process routes "
            "and three erasures are the ones we imagined, which is the same honest limit the "
            "gate-proof mutation set carries",
        ),
    )


def _load() -> ContractSet:
    from holdout.contracts.loader import load

    return load()
