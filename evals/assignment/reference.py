"""The lottery, computed a second time — a different hash, a different framing, per unit.

Where the independence is
-------------------------
Claim 3's trap, stated plainly: **verifying reproducibility by running the same function
again is a deterministic function repeated, and it catches nothing.** It would agree with
itself if the seed were ignored, if the key were prefixed instead of keyed, if the framing
of the digest could not tell one roster from another, or if the control were simply the
lowest-numbered store in each stratum. Every one of those is a lottery that reproduces
perfectly and is not the lottery that was committed to.

So this module recomputes the draw from its **specification** rather than from its code, and
differs everywhere it is allowed to:

============  ==========================================  =============================
              `holdout.core.experiment.assignment`         here
============  ==========================================  =============================
the hash      `hashlib.blake2b` — a C extension            `evals.assignment.blake2b`,
                                                           RFC 7693 written out in Python
the framing   a `bytearray` appended to, with
              `len(raw).to_bytes(8, "big")`                `struct.pack(">Q", ...)` and
                                                           `b"".join`
the rank      `int.from_bytes(digest, "big")`              accumulated a byte at a time
the choice    `min(stratum, key=lambda u: (rank, u))`      an explicit scan comparing
                                                           `(rank, id)` pairs in turn
the shape     one pass over the whole roster               **per unit** — one store's arm
                                                           from the seed, the candidate
                                                           index and its own stratum,
                                                           with the rest of the roster
                                                           never consulted
============  ==========================================  =============================

The last row is the one that carries `A3`. A readout a month later re-derives a store's arm
from the committed record, not by replaying the draw over an estate that has since changed,
and the two paths agreeing is a fact about the lottery rather than about repetition.

What the two sides still share, and must
----------------------------------------
The **specification**: that a per-candidate key is `blake2b(seed || index)` at 32 bytes,
that a rank is the keyed `blake2b` of the unit id at 16, that the smallest `(rank, id)` in
a stratum is the control, and which parts the committed digest is taken over and in what
order. That is the definition of the lottery. Two implementations of one definition is the
strongest available position here — the definition itself is not attacked by anything in
this eval, and `evals/assignment/README.md` says so under *what this does not prove*.
"""

from __future__ import annotations

import struct
from collections.abc import Mapping, Sequence

from evals.assignment.blake2b import blake2b

#: Bytes of key material per candidate, and bytes of rank per unit. The same widths the
#: specification declares; a second implementation that quietly chose its own would agree
#: with nothing and prove nothing.
KEY_BYTES = 32
RANK_BYTES = 16
DIGEST_BYTES = 32

#: The width of the candidate index inside a per-draw key, and of the length prefix in the
#: canonical framing. Eight bytes, big-endian, in both places.
INDEX_FORMAT = ">Q"
LENGTH_FORMAT = ">Q"

#: The two arms, as the strings the core's `Arm` enum carries. Written out rather than
#: imported: importing the enum would be this module reaching into the package it is a
#: second opinion about, and the arms are a closed vocabulary of two.
TREATMENT = "treatment"
CONTROL = "control"


def canonical_bytes(parts: Sequence[str]) -> bytes:
    """Length-prefixed UTF-8, built by joining rather than by appending to a buffer."""
    return b"".join(
        struct.pack(LENGTH_FORMAT, len(raw)) + raw
        for raw in (part.encode("utf-8") for part in parts)
    )


def digest(parts: Sequence[str], *, size: int = DIGEST_BYTES) -> str:
    return blake2b(canonical_bytes(parts), digest_size=size).hex()


def key_for(seed: str, draw_index: int) -> bytes:
    """The per-candidate key: one committed seed gives every candidate."""
    return blake2b(
        seed.encode("utf-8") + struct.pack(INDEX_FORMAT, draw_index), digest_size=KEY_BYTES
    )


def rank_of(unit_id: str, key: bytes) -> int:
    """One unit's place in one candidate's order, accumulated a byte at a time."""
    rank = 0
    for byte in blake2b(unit_id.encode("utf-8"), key=key, digest_size=RANK_BYTES):
        rank = rank * 256 + byte
    return rank


def control_of(stratum: Sequence[str], key: bytes) -> str:
    """The stratum's control: the smallest `(rank, id)`, found by an explicit scan."""
    if not stratum:
        raise ValueError("a stratum with nobody in it has no control to draw")
    chosen = stratum[0]
    lowest = rank_of(chosen, key)
    for member in stratum[1:]:
        rank = rank_of(member, key)
        if rank < lowest or (rank == lowest and member < chosen):
            chosen, lowest = member, rank
    return chosen


def arm_of(unit_id: str, *, stratum: Sequence[str], seed: str, draw_index: int) -> str:
    """One unit's arm, from the committed record alone — the month-later path.

    The seed, the candidate index and the unit's own stratum. Not the seal, not its arms,
    not the rest of the roster and not a replay of any sequence.
    """
    if unit_id not in stratum:
        raise ValueError(f"{unit_id!r} is not in the stratum it is being read out of")
    return CONTROL if control_of(stratum, key_for(seed, draw_index)) == unit_id else TREATMENT


def lottery(strata: Sequence[Sequence[str]], *, seed: str, draw_index: int) -> dict[str, str]:
    """Every unit's arm under one candidate. The whole-roster path, for comparison."""
    key = key_for(seed, draw_index)
    arms: dict[str, str] = {}
    for stratum in strata:
        control = control_of(stratum, key)
        for unit in stratum:
            arms[unit] = CONTROL if unit == control else TREATMENT
    return arms


def digest_for(
    *,
    experiment_id: str,
    seed: str,
    form_digest: str,
    strata: Sequence[Sequence[str]],
    arms: Mapping[str, str],
) -> str:
    """The committed digest, over the parts the specification names and in its order."""
    roster = sorted(arms)
    parts: list[str] = [
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
    parts.extend(("roster", *roster))
    parts.append("arms")
    parts.extend(arms[unit] for unit in roster)
    return digest(parts)
