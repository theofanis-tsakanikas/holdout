"""Can a `SealedAssignment` exist that the lottery did not draw — or change after it did?

Doctrine rule 7: **no unit changes arm after its first observation, not by anyone, including
an approver.** From the moment it can, every number the system produces becomes
unfalsifiable, and having exactly one unopenable door is what keeps the other six honest.

This file walks the seal the way `test_certificate_forgery.py` walks the certificate,
because the two types make the same promise by the same mechanism and a promise tested in
one place and asserted in the other is a promise with a hole in it. Written as an attacker:
each test is a route somebody would actually take to move a store between arms.

The last section is the honest half. It asserts the limit rather than hiding it — a claim
whose limits are not written down is a claim nobody can check.
"""

from __future__ import annotations

import copy
import dataclasses
import pickle

import pytest

from holdout.contracts.model import InferenceSettings
from holdout.core.experiment import (
    Arm,
    CovariateMatrix,
    SealedAssignment,
    SealForgeryError,
    control_size_for,
    digest_for,
    draw,
    sealed,
)

SEED = "holdout-t001-committed-seed"
FORM_DIGEST = "a" * 64


@pytest.fixture
def seal(matrix: CovariateMatrix, inference: InferenceSettings) -> SealedAssignment:
    drawn = draw(
        experiment_id="exp-forgery",
        roster=matrix.units,
        seed=SEED,
        form_digest=FORM_DIGEST,
        matrix=matrix,
        control_size=control_size_for(len(matrix.units), inference.holdout_share_pct),
    )
    assert drawn is not None
    return drawn[0]


# ------------------------------------------------------------------ the ordinary path


def test_a_drawn_assignment_is_sealed(seal: SealedAssignment) -> None:
    assert sealed(seal)
    assert seal.experiment_id == "exp-forgery"
    assert seal.seed == SEED
    assert seal.form_digest == FORM_DIGEST
    assert set(seal.arms.values()) == {Arm.TREATMENT, Arm.CONTROL}
    assert seal.covariate_digest, "a seal records the matrix its strata were built from"
    assert seal.strata, "a seal records the restriction the lottery drew under"


# ------------------------------------------------------------------ the closed routes


def test_the_constructor_refuses() -> None:
    """A seal is not constructed; it is drawn. Building one directly in a test would be
    asserting the type can be bypassed, and it cannot."""
    with pytest.raises(SealForgeryError, match="not constructed"):
        SealedAssignment()


def test_it_cannot_be_subclassed() -> None:
    """A subclass satisfies every isinstance check a readout makes while carrying whatever
    its own constructor put in it."""
    with pytest.raises(TypeError, match="may not be subclassed"):

        class Fake(SealedAssignment):  # pragma: no cover - the class body never runs
            pass


def test_dataclasses_replace_does_not_apply(seal: SealedAssignment) -> None:
    """The route a hurried adapter reaches for, and the reason this is written by hand
    while almost everything around it is a dataclass."""
    with pytest.raises(TypeError):
        dataclasses.replace(seal)  # type: ignore[type-var]


def test_an_arm_cannot_be_set(seal: SealedAssignment) -> None:
    with pytest.raises(SealForgeryError, match="one door with no key"):
        setattr(seal, "_draw_index", 99)  # noqa: B010


def test_nothing_can_be_deleted(seal: SealedAssignment) -> None:
    with pytest.raises(SealForgeryError, match="nothing is deleted"):
        delattr(seal, "_seed")


def test_it_cannot_be_pickled(seal: SealedAssignment) -> None:
    """One that survived a round trip could be restored in a process where no lottery ever
    ran, and the readout there would have no way to tell."""
    with pytest.raises(SealForgeryError, match="not serialisable"):
        pickle.dumps(seal)


def test_copying_yields_the_same_object_rather_than_a_fillable_one(
    seal: SealedAssignment,
) -> None:
    assert copy.copy(seal) is seal
    assert copy.deepcopy(seal) is seal


def test_an_empty_shell_from_object_new_is_not_a_seal() -> None:
    """`object.__new__` is one of the two routes Python does not let a library close. What
    is closed is what the shell is worth: it has the shape and not the contents, and every
    accessor says so."""
    shell = object.__new__(SealedAssignment)
    assert not sealed(shell)
    with pytest.raises(SealForgeryError, match="shape of a sealed assignment"):
        _ = shell.seed


def test_a_look_alike_is_not_a_seal(seal: SealedAssignment) -> None:
    """Something with the same attributes and no witness. `sealed()` asks for the type
    first, so duck typing gets nowhere."""

    class LookAlike:
        experiment_id = "exp-forgery"
        seed = SEED
        draw_index = 0
        arms = seal.arms
        digest = seal.digest

    assert not sealed(LookAlike())


# ------------------------------------------------------------------ tampering after issue


def test_moving_one_store_between_arms_is_detected(seal: SealedAssignment) -> None:
    """The edit doctrine rule 7 exists to make impossible, made through the one route that
    reaches the slots at all.

    The rewritten arms no longer produce the recorded digest, so the seal contradicts
    itself — and it contradicts itself about the one thing it is for.
    """
    moved = dict(seal.arms)
    victim = seal.control[0]
    moved[victim] = Arm.TREATMENT
    from types import MappingProxyType

    object.__setattr__(seal, "_arms", MappingProxyType(moved))
    assert not sealed(seal)


def test_emptying_an_arm_is_detected(seal: SealedAssignment) -> None:
    """The `PriceBounds()` defect, one type along: an erased answer rather than a forged
    one. Every unit in one arm makes every later comparison vacuous instead of wrong, and
    an erasure is harder to see in a diff than a rewrite.
    """
    from types import MappingProxyType

    object.__setattr__(seal, "_arms", MappingProxyType(dict.fromkeys(seal.roster, Arm.TREATMENT)))
    assert not sealed(seal)


def test_rewriting_the_seed_without_the_digest_is_detected(seal: SealedAssignment) -> None:
    object.__setattr__(seal, "_seed", "a-seed-that-flatters-us")
    assert not sealed(seal)


def test_pointing_the_seal_at_another_design_is_detected(seal: SealedAssignment) -> None:
    """A readout run against a different form than the one that was sealed is the same
    failure as an edited assignment, arriving by a different door."""
    object.__setattr__(seal, "_form_digest", "b" * 64)
    assert not sealed(seal)


def test_redrawing_the_strata_is_detected(seal: SealedAssignment) -> None:
    """The subtlest edit of the three, and the reason the strata are inside the digest.

    Merging two strata leaves every unit in the roster and every arm where it was, so an
    eye on the arms table sees nothing — and the lottery that was committed to has still
    changed, because a different set of draws was ever possible. Under the merged strata
    the same seed draws one control where it drew two.
    """
    merged = (seal.strata[0] + seal.strata[1], *seal.strata[2:])
    object.__setattr__(seal, "_strata", merged)
    assert not sealed(seal), "the digest covers the strata, so a merged one contradicts it"

    from holdout.core.experiment import contamination

    found = contamination.check(
        seal,
        delivered=dict.fromkeys(seal.roster, "ladder_policy@v1"),
        treatment_policy="ladder_policy@v1",
        control_policy="ladder_policy@v1",
        form_digest=seal.form_digest,
    )
    assert not found.redraw_matches, (
        "the redraw is the half that does not consult the arms, so it has to notice a "
        "restriction that moved even where the arms table was left alone"
    )


# ------------------------------------------------------------------ the declared limit


def test_a_coordinated_rewrite_is_a_declared_limit(seal: SealedAssignment) -> None:
    """The honest half, asserted rather than hidden.

    A forger who rewrites the arms **and** recomputes the digest to match produces
    something a seal cannot contradict, because a seal never held independent evidence of
    its own provenance. `sealed()` passes.

    What still catches it is `contamination.check`, which re-derives the arms from the
    committed seed and the roster and never consults the seal's own arms at all — and, one
    level up, the pull-request diff on the committed seed. The type makes the mistake
    impossible and leaves the forgery visible; claiming more would be exactly the sort of
    sentence this project exists to argue against.
    """
    from types import MappingProxyType

    moved = dict(seal.arms)
    moved[seal.control[0]] = Arm.TREATMENT
    moved[seal.treatment[0]] = Arm.CONTROL
    arms = MappingProxyType(moved)
    object.__setattr__(seal, "_arms", arms)
    object.__setattr__(
        seal,
        "_digest",
        digest_for(
            experiment_id=seal.experiment_id,
            seed=seal.seed,
            form_digest=seal.form_digest,
            strata=seal.strata,
            arms=arms,
        ),
    )
    assert sealed(seal), "this is the limit, and it is asserted so nobody reads rule 7 as closed"

    from holdout.core.experiment import contamination

    found = contamination.check(
        seal,
        delivered=dict.fromkeys(seal.roster, "ladder_policy@v1"),
        treatment_policy="ladder_policy@v1",
        control_policy="ladder_policy@v1",
        form_digest=seal.form_digest,
    )
    assert not found.redraw_matches, "the redraw is what catches what the digest cannot"
    assert len(found.reassigned) == 2


def test_the_witness_is_not_reachable_by_any_name() -> None:
    """No module-level name is bound to the witness or to the function that fills a seal's
    slots, so neither can be imported or monkeypatched.

    It is still reachable — through `gc`, through `ctypes`, through the closure cells — and
    `assignment.py`'s docstring says so. What this asserts is only that it takes deliberate
    introspection rather than an import.
    """
    from holdout.core.experiment import assignment

    public = vars(assignment)
    assert "witness" not in public
    assert not any(isinstance(value, assignment._Witness) for value in public.values()), (
        "a module-level witness would be a name anybody could stamp a seal with"
    )
