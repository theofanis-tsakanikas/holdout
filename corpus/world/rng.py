"""Randomness that is reproducible, order-independent and platform-stable.

Three properties, and the third one is why this module exists rather than a module-level
`random.seed()`.

**Reproducible.** A world is a pure function of `(world, seed, scale, assignment)`. Run it
twice, anywhere, and every event is identical — which is the only reason a sealed truth means
anything, and the only reason a K = 200 harness can be re-run by someone who did not write it.

**Order-independent.** Every draw is keyed by *what it is a draw about* — this store, this
day, this SKU, this purpose — and never by how many draws came before it. So generating one
store's eight months gives byte-identical events whether or not the other ninety-nine were
generated, and a restriction to three store-days is a genuine window onto the same world
rather than a different one. A single sequential stream would make every one of those a
different world.

**Common random numbers, on purpose.** No key contains the arm. Generate a world under an
assignment and again under all-control and the two runs draw the *same numbers* for every unit
whose policy did not change, so the difference between them is the treatment effect and not
Monte-Carlo noise. T003's reference implementation of truth-on-the-metric depends on that, and
`tests/corpus/test_world_determinism.py` asserts it directly: under W6, an untreated store's
events are identical between the two runs.

How
---
`blake2b` keyed with the world seed turns the key tuple into 32 bytes; those bytes seed a
`random.Random`. The hash decides *which* stream, the Mersenne Twister produces it. Both
halves are documented as stable across CPython versions and across platforms, which a hash of
Python's own `hash()` would not be — `str.__hash__` is salted per process and would make every
run a different world.

Nothing here is cryptography and none of it is trying to be. `seal.py` says the same thing
about itself, in more detail and with more at stake.
"""

from __future__ import annotations

import hashlib
import math
import random

#: `random.Random` accepts an int of any width; 256 bits of blake2b is the whole digest, so
#: two different keys collide only if blake2b does.
_DIGEST_BYTES = 32


def stream(seed: str, *key: object) -> random.Random:
    """The stream for one key. Same key, same seed, same numbers — anywhere, always."""
    material = "\x1f".join([seed, *(str(part) for part in key)]).encode("utf-8")
    digest = hashlib.blake2b(material, digest_size=_DIGEST_BYTES).digest()
    return random.Random(int.from_bytes(digest, "big"))


def unit_interval(seed: str, *key: object) -> float:
    """One uniform draw for a key, without keeping a stream around for it.

    Most of the generator's decisions are exactly one draw — did this acknowledgement fail,
    is it raining at this store today — and giving each its own key is what keeps them
    independent of every other decision in the same hour.
    """
    return stream(seed, *key).random()


def normal(rng: random.Random, mu: float, sigma: float) -> float:
    """Box-Muller rather than `random.gauss`.

    `gauss` keeps a spare deviate between calls, so its output depends on how many times it
    was called before — the one property this module exists to refuse. Box-Muller over two
    `random()` draws has no state at all.
    """
    u1 = max(rng.random(), 1e-12)
    u2 = rng.random()
    return mu + sigma * math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def lognormal(rng: random.Random, median: float, sigma: float) -> float:
    """A positive multiplier whose *median* is the number you asked for.

    Store size, SKU popularity and shelf-life variation are all multiplicative and none of
    them can be negative, so a normal would be the wrong shape and would occasionally hand
    back a store that sells minus four loaves.
    """
    return median * math.exp(normal(rng, 0.0, sigma))


def poisson(rng: random.Random, lam: float) -> int:
    """A count of arrivals in an interval.

    Knuth's multiplication method below 30, where it costs about `lam` uniforms and is exact.
    Above that the product underflows, so a normal approximation with a continuity correction
    takes over — declared here rather than discovered, because the crossover is a real
    difference in distribution and heavy-tailed worlds push the rate up.
    """
    if lam <= 0.0:
        return 0
    if lam < 30.0:
        target = math.exp(-lam)
        count, product = 0, rng.random()
        while product > target:
            count += 1
            product *= rng.random()
        return count
    return max(0, int(normal(rng, lam, math.sqrt(lam)) + 0.5))


def pareto_shock(rng: random.Random, alpha: float, cap: float) -> float:
    """A multiplier with a heavy right tail and a mean of one, truncated at `cap`.

    W5's whole content. A Pareto tail index below 2 has finite mean and **infinite
    variance**, which is precisely the assumption a power calculation makes and does not
    check.

    **It is divided by its own mean**, so a world that carries it has the same average demand
    as one that does not and differs only in how that demand is spread. Without the division
    W5 would be a world with more trade in it as well as a wilder one, and every number it
    produced would be answering two questions at once.

    The truncation is honest about itself and it is generous — a real chain has a busiest day
    it has ever had, and an untruncated Pareto eventually produces a single day outselling a
    year. `cap` is stated by the caller rather than assumed here.

    **Restated 2026-08-28: this was `pareto_units`, a basket-line quantity.** The tail was
    real and it never reached the metric: `category_margin_per_store_week` aggregates about
    sixteen thousand lines, and the central limit theorem is not something a world can opt out
    of by drawing each line from a wild distribution. Measured, W5's standard error at the
    readout came out *below* W6's — 8.08 EUR against 11.51 — so the world whose declared
    pathology is variance had less of it than the world with none. The tail moved to the level
    the metric is aggregated over: a store-day.
    """
    draw = float(rng.random() ** (-1.0 / alpha))
    mean = alpha / (alpha - 1.0) if alpha > 1.0 else 1.0
    return min(draw, cap) / mean


def choice_index(rng: random.Random, weights: tuple[float, ...]) -> int:
    """Pick a position in proportion to `weights`, with no dependence on list identity."""
    total = math.fsum(weights)
    if total <= 0.0:
        return 0
    threshold = rng.random() * total
    running = 0.0
    for index, weight in enumerate(weights):
        running += weight
        if running >= threshold:
            return index
    return len(weights) - 1
