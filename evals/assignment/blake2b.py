"""BLAKE2b, written out from RFC 7693 — the eval's own, sharing nothing with the core's.

The defect this module exists to close
--------------------------------------
Claim 3's sentence is *assignment from a committed seed, exactly reproducible*. The obvious
way to check it is to call the lottery twice and compare. That checks nothing at all: a
deterministic function run twice agrees with itself by definition, and it would agree just
as loudly if the seed were ignored, if the keyed hash were keyed the wrong way round, or if
the arms were decided by the store id alone. `CLAUDE.md` names the class:

> **A guard tested by its author is tested in the shape the guard already handles.**

So the lottery is computed a second time, and the second computation may not reach the
first one's hash. `holdout.core.hashing` and `holdout.core.experiment.assignment` both go
through `hashlib.blake2b`, which is C — OpenSSL's or libb2's. This module is the same
algorithm read out of its specification and written in Python, so the two share the
*published definition* and no line of code:

============  =======================================  ===================================
              `hashlib.blake2b`                          here
============  =======================================  ===================================
implementation a C extension, one call                   the compression function written
                                                         out: 12 rounds of eight mixes
                                                         over a sixteen-word state
keyed mode     an argument passed to the extension       the RFC's own construction — the
                                                         key length in the parameter block
                                                         and the key zero-padded into a
                                                         128-byte first block
digest size    an argument passed to the extension       the parameter block's low byte,
                                                         and a truncation of the state
speed          microseconds                              milliseconds, and that is the
                                                         point: a fast second
                                                         implementation is one that made
                                                         the same decisions as the first
============  =======================================  ===================================

What makes this a BLAKE2b rather than something that resembles one
------------------------------------------------------------------
`A10` drives it against the digest RFC 7693 Appendix A publishes for the message ``abc``,
and against `hashlib` over a declared sweep: both sides of a 128-byte block boundary and
four lengths beyond it — because the block counter and the last-block flag are what a
plausible reimplementation gets wrong and neither is exercised inside one block — and every
key width and digest size the lottery uses. The longest, 4,096 bytes with a 32-byte key, is
thirty-three blocks compared against the standard library. The vector is quoted from the instrument, not
from this repository, and the sweep's answers come from the standard library rather than
from anything here. It is a declared sweep and not an exhaustive one, which is the same
thing every other sweep in this repository is.

**And what that leaves open, said out loud.** Where this module and `hashlib` agree, the
agreement is evidence that the *composition* around the hash is right — which bytes go in,
whether the key is keyed or merely prefixed, how wide the digest is, which way the bytes
are read back. It is not evidence about BLAKE2b itself, and it never could be: two
implementations of one published algorithm agreeing says the algorithm was implemented
twice, not that the algorithm is sound. The soundness of BLAKE2b is not one of this
repository's seven claims.
"""

from __future__ import annotations

MASK64 = (1 << 64) - 1

#: The block size, in bytes. Named because the counter the compression function is fed is
#: measured in it, and a bare 128 in that arithmetic is a number a reader has to reverse.
BLOCK_BYTES = 128

MAX_DIGEST_BYTES = 64
MAX_KEY_BYTES = 64

#: RFC 7693 section 2.6 — the first eight fractional words of the square roots of the first
#: eight primes, the same initialisation vector SHA-512 uses.
IV = (
    0x6A09E667F3BCC908,
    0xBB67AE8584CAA73B,
    0x3C6EF372FE94F82B,
    0xA54FF53A5F1D36F1,
    0x510E527FADE682D1,
    0x9B05688C2B3E6C1F,
    0x1F83D9ABFB41BD6B,
    0x5BE0CD19137E2179,
)

#: RFC 7693 section 2.7 — the message word schedule. Ten permutations, and a twelve-round
#: BLAKE2b reuses the first two for rounds eleven and twelve.
SIGMA = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15),
    (14, 10, 4, 8, 9, 15, 13, 6, 1, 12, 0, 2, 11, 7, 5, 3),
    (11, 8, 12, 0, 5, 2, 15, 13, 10, 14, 3, 6, 7, 1, 9, 4),
    (7, 9, 3, 1, 13, 12, 11, 14, 2, 6, 5, 10, 4, 0, 15, 8),
    (9, 0, 5, 7, 2, 4, 10, 15, 14, 1, 11, 12, 6, 8, 3, 13),
    (2, 12, 6, 10, 0, 11, 8, 3, 4, 13, 7, 5, 15, 14, 1, 9),
    (12, 5, 1, 15, 14, 13, 4, 10, 0, 7, 6, 3, 9, 2, 8, 11),
    (13, 11, 7, 14, 12, 1, 3, 9, 5, 0, 15, 4, 8, 6, 2, 10),
    (6, 15, 14, 9, 11, 3, 0, 8, 12, 2, 13, 7, 1, 4, 10, 5),
    (10, 2, 8, 4, 7, 6, 1, 5, 15, 11, 9, 14, 3, 12, 13, 0),
)

ROUNDS = 12

#: RFC 7693 section 3.1 — the four rotation distances of the mixing function G.
ROTATIONS = (32, 24, 16, 63)

#: The eight column-and-diagonal mixes one round performs, as (a, b, c, d) into the working
#: state. Written out rather than derived, because the diagonals are where a plausible
#: reimplementation goes wrong and a table is checkable against the RFC by eye.
MIXES = (
    (0, 4, 8, 12),
    (1, 5, 9, 13),
    (2, 6, 10, 14),
    (3, 7, 11, 15),
    (0, 5, 10, 15),
    (1, 6, 11, 12),
    (2, 7, 8, 13),
    (3, 4, 9, 14),
)


class Blake2bError(ValueError):
    """The parameters are outside what BLAKE2b defines."""


def _rotate_right(word: int, distance: int) -> int:
    return ((word >> distance) | (word << (64 - distance))) & MASK64


def _mix(state: list[int], a: int, b: int, c: int, d: int, x: int, y: int) -> None:
    """G, RFC 7693 section 3.1."""
    first, second, third, fourth = ROTATIONS
    state[a] = (state[a] + state[b] + x) & MASK64
    state[d] = _rotate_right(state[d] ^ state[a], first)
    state[c] = (state[c] + state[d]) & MASK64
    state[b] = _rotate_right(state[b] ^ state[c], second)
    state[a] = (state[a] + state[b] + y) & MASK64
    state[d] = _rotate_right(state[d] ^ state[a], third)
    state[c] = (state[c] + state[d]) & MASK64
    state[b] = _rotate_right(state[b] ^ state[c], fourth)


def _compress(chained: list[int], block: bytes, counter: int, *, last: bool) -> None:
    """F, RFC 7693 section 3.2. `chained` is updated in place."""
    message = [int.from_bytes(block[at : at + 8], "little") for at in range(0, BLOCK_BYTES, 8)]
    state = [*chained, *IV]
    state[12] ^= counter & MASK64
    state[13] ^= (counter >> 64) & MASK64
    if last:
        state[14] ^= MASK64
    for number in range(ROUNDS):
        schedule = SIGMA[number % len(SIGMA)]
        for index, (a, b, c, d) in enumerate(MIXES):
            _mix(state, a, b, c, d, message[schedule[2 * index]], message[schedule[2 * index + 1]])
    for index in range(8):
        chained[index] ^= state[index] ^ state[index + 8]


def _blocks(message: bytes, key: bytes) -> list[bytes]:
    """The padded blocks, key block first. RFC 7693 section 3.3's `d[0..dd-1]`."""
    padded: list[bytes] = []
    if key:
        padded.append(key + bytes(BLOCK_BYTES - len(key)))
    for at in range(0, len(message), BLOCK_BYTES):
        chunk = message[at : at + BLOCK_BYTES]
        padded.append(chunk + bytes(BLOCK_BYTES - len(chunk)))
    if not padded:
        # Neither a key nor a message: one all-zero block, which is what makes the digest of
        # the empty string defined rather than a special case somebody has to remember.
        padded.append(bytes(BLOCK_BYTES))
    return padded


def blake2b(message: bytes, *, key: bytes = b"", digest_size: int = MAX_DIGEST_BYTES) -> bytes:
    """The digest, computed here. RFC 7693 section 3.3, in the order the RFC states it."""
    if not 1 <= digest_size <= MAX_DIGEST_BYTES:
        raise Blake2bError(f"a BLAKE2b digest is 1 to {MAX_DIGEST_BYTES} bytes, not {digest_size}")
    if len(key) > MAX_KEY_BYTES:
        raise Blake2bError(f"a BLAKE2b key is at most {MAX_KEY_BYTES} bytes, not {len(key)}")

    chained = list(IV)
    chained[0] ^= 0x01010000 ^ (len(key) << 8) ^ digest_size

    padded = _blocks(message, key)
    for index, block in enumerate(padded[:-1]):
        _compress(chained, block, (index + 1) * BLOCK_BYTES, last=False)
    # The counter on the final block counts the message only, plus the key block where one
    # was prepended. RFC 7693 section 3.3: `ll` when kk = 0, `ll + bb` otherwise.
    final = len(message) + (BLOCK_BYTES if key else 0)
    _compress(chained, padded[-1], final, last=True)

    return b"".join(word.to_bytes(8, "little") for word in chained)[:digest_size]
