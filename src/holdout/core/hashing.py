"""Canonical bytes and a digest, once, for everything in the core that needs one.

Two things are shared and both have to be shared, because both are the kind of definition
that quietly acquires a second copy.

**The encoding.** A digest over concatenated text is only as good as the way the text was
joined. `"ab" + "c"` and `"a" + "bc"` are the same bytes, so a digest built by
concatenation cannot tell a roster of `["ab", "c"]` from one of `["a", "bc"]` — and an
assignment digest that cannot distinguish two rosters is an assignment digest that misses
the edit somebody actually made. Every part is therefore length-prefixed, and the length is
a fixed-width big-endian integer so the framing itself is unambiguous.

**The algorithm.** `blake2b`, in the standard library, deterministic and platform-stable.
Claim 3's sentence is *exactly reproducible*, and reproducible means on another machine, in
another interpreter, next year.

`hashlib` is not on `holdout.core`'s forbidden list and this is why: a keyed hash is not a
random source. It reads no clock, no environment and no entropy pool. The same inputs give
the same bytes forever, which is the property this package exists to have.
"""

from __future__ import annotations

from collections.abc import Iterable
from hashlib import blake2b

#: Width of the length prefix, in bytes. Eight, so no realistic part can overflow it and the
#: framing never has to grow — a framing that changed width would change every digest.
LENGTH_BYTES = 8

#: The digest size used everywhere a digest is stored and compared. 32 bytes is 64 hex
#: characters, which is what lands in `gold.experiment_assignment` and what a reader compares
#: by eye when they suspect an assignment has been altered.
DIGEST_BYTES = 32


def canonical_bytes(parts: Iterable[str]) -> bytes:
    """Length-prefixed UTF-8, so no two different sequences encode to the same bytes."""
    out = bytearray()
    for part in parts:
        raw = part.encode("utf-8")
        out += len(raw).to_bytes(LENGTH_BYTES, "big")
        out += raw
    return bytes(out)


def digest(parts: Iterable[str], *, size: int = DIGEST_BYTES) -> str:
    """The hex digest of an unambiguously encoded sequence of parts."""
    return blake2b(canonical_bytes(parts), digest_size=size).hexdigest()
