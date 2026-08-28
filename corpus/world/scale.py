"""How big a world is, declared rather than implied.

`CLAUDE.md`: *"The scenario is 1,200 stores. The corpus is 100."* — roughly 100 stores across
three fresh categories over eight months, about 36M POS lines. That is the **scenario** scale,
and it is the one figure in this package that costs real minutes to produce.

Four scales exist because four different things need to be true at once:

============  ==================================================================
`SMOKE`       the suite. Small enough that a test generates a whole world in
              well under a second, large enough that every mechanism fires at
              least once — a markdown, a failed acknowledgement, a stock-out, an
              expiry, a neighbour pair inside the interference radius.
`REHEARSAL`   a laptop. Big enough that an estimator has something to estimate
              and small enough to run K seeds over a coffee.
`HARNESS`     `evals/uplift/`. The **roster** of the declared corpus, on a
              calendar the A/A harness can afford K = 200 times.
`SCENARIO`    the declared corpus. 100 stores x 3 categories x 8 months.
============  ==================================================================

**A figure measured at one scale is reported at that scale.** `CLAUDE.md` is explicit that a
number depending on corpus size is never extrapolated to the full estate, and the same rule
applies one level down: a count taken at `SMOKE` is a count at `SMOKE`. The `restrict_to`
argument on `generate` exists so the scenario-scale world can be *inspected* without
materialising it — never so a slice can be multiplied up into a total.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

#: The scenario's three fresh categories. They are the three
#: `contracts/guardrails/regulated_basket.yaml` names as "the synthetic scenario's own fresh
#: categories", and the same three `CLAUDE.md` counts when it says three. The world does not
#: read that contract for them — it would be reading a *guardrail* to decide what a shop
#: sells — but the lists must agree, and `tests/corpus/test_world_chain.py` asserts they do.
CATEGORIES: tuple[str, ...] = ("dairy", "bakery", "poultry")

#: Trading hours, closed at the top. A store opens at 07:00 and takes its last basket in the
#: hour beginning 22:00. Markdowns therefore have somewhere to go late in the day, which is
#: the whole shape of the fresh decision path.
OPEN_HOUR = 7
CLOSE_HOUR = 23


@dataclass(frozen=True, slots=True)
class Scale:
    """The size of a world. Everything else in this package is a function of it and a seed."""

    name: str
    stores: int
    skus_per_category: int
    days: int
    start_date: date

    def __post_init__(self) -> None:
        if self.stores < 1 or self.skus_per_category < 1 or self.days < 1:
            raise ValueError("a scale with no stores, no products or no days is not a world")

    @property
    def skus(self) -> int:
        return self.skus_per_category * len(CATEGORIES)

    @property
    def store_days(self) -> int:
        return self.stores * self.days

    def __str__(self) -> str:
        return (
            f"{self.name}: {self.stores} stores x {self.skus} SKUs "
            f"({self.skus_per_category} per category) x {self.days} days from {self.start_date}"
        )


#: 100 stores, 120 SKUs, 244 days — 2025-09-01 through 2026-05-02, which is eight months to
#: the day. The POS line count this produces is measured, not designed: it is printed by
#: `python -m corpus.world count --scale scenario` and recorded in `corpus/world/README.md`
#: with the command that reproduces it.
SCENARIO = Scale(
    name="scenario",
    stores=100,
    skus_per_category=40,
    days=244,
    start_date=date(2025, 9, 1),
)

REHEARSAL = Scale(
    name="rehearsal",
    stores=20,
    skus_per_category=8,
    days=56,
    start_date=date(2025, 9, 1),
)

#: The A/A harness's scale, and every dimension of it is set by a measurement rather than by a
#: preference.
#:
#: **320 stores, because the surviving roster is what the lottery draws over.** Not the store
#: count: the design engine excludes the later-sorted member of every pair inside the declared
#: 1 km radius, so what an experiment may use is what `ops.roster` prints. At 100 stores — the
#: figure this scale first carried — the roster was 45 and the control arm 9, and no lottery in
#: two hundred passed the readout's balance check. 320 is the smallest round count whose
#: **worst** world clears 200 across eight world seeds, and W2 is always the worst because its
#: estate is deliberately the most clustered. `make roster` is the command and
#: `corpus/world/README.md` records what it printed.
#:
#: **112 days**, and it is load-bearing twice. Eight pre-period weeks — the declared
#: `lookback_weeks` of the balance covariates — plus eight period weeks, which is the form's
#: `max_duration`; and an *even* number of weeks, which is what makes the window mean a place
#: where the metric contract's `rounding` decides a cent rather than a place where half_even
#: and half_up cannot differ.
#:
#: **4 SKUs per category is what pays for the stores.** Generation cost is linear in all three
#: dimensions, and the roster is the one that cannot be traded away. A thinner assortment
#: raises per-store variance relative to the mean, so it makes this world *harder* to detect an
#: effect in rather than easier — the honest direction, and if it ever costs W6 a readout the
#: cost appears as the published false-refusal rate rather than as a tuned number.
HARNESS = Scale(
    name="harness",
    stores=320,
    skus_per_category=4,
    days=112,
    start_date=date(2025, 9, 1),
)

SMOKE = Scale(
    name="smoke",
    stores=12,
    skus_per_category=3,
    days=21,
    start_date=date(2025, 9, 1),
)

SCALES: dict[str, Scale] = {s.name: s for s in (SMOKE, REHEARSAL, HARNESS, SCENARIO)}


def scale_by_name(name: str) -> Scale:
    try:
        return SCALES[name]
    except KeyError:
        raise ValueError(f"unknown scale {name!r}; declared scales are {sorted(SCALES)}") from None
