"""The six adversarial worlds, each violating a different assumption.

`CLAUDE.md`'s table, made executable:

==  ==========================================  ================================================
W1  pure noise, true effect zero                no significant uplift, at a rate <= alpha
W2  real effect + interference between          **refuse the interfering units at design**,
    neighbouring stores                         then estimate on what is left
W3  real effect + exposure fails on 30% of      report ITT with the realised rate printed, or
    treated units                               refuse below the declared threshold — never
                                                silently dilute
W4  an effect that decays (novelty)             no result before the declared end, then report
                                                what the declared window aggregated
W5  heavy-tailed baskets — variance far above   the power check fails, or the interval is
    what the power calculation assumed          honestly wide
W6  everything works, a real effect is present  **produce the number.** No refusal
==  ==========================================  ================================================

**W6 matters as much as W1.** A system that refuses everything passes every other world and is
worthless, which is why the false-refusal rate is published beside the false-positive rate.

What is public here, and what is not
------------------------------------
The *shape* of each world is public and belongs in a docstring: which assumption it breaks,
what the right answer is, and what the intervention is. A design form declares its own
`intervention: {treatment, control}`, so the policy under test was never a secret.

The **effect** is not declared anywhere, because it is not a number anybody wrote down. The
world injects behaviour — a different markdown schedule, a neighbour pulling trade, a label
that did not change — and what that does to `category_margin_per_store_week` is emergent. It
has to be *computed*, by running the counterfactual and looping over every event, which is
T003's reference implementation and which happens after the readout is written.

So reading this file tells you what W2 does to a control store's demand. It does not tell you
what the answer is, and neither does `seal.py`: what is sealed is the behaviour, not the
metric.

The honest limit, stated here rather than left for somebody to find
-------------------------------------------------------------------
These are the six failure modes we thought of. The estimator's validity does not come from
passing them — a difference of means over randomly assigned units is unbiased under any
data-generating process, which is a theorem and not our opinion. The worlds do not test the
subtraction; they test whether the machinery around it preserves that validity.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Every world's baseline rate of electronic shelf labels that do not answer back. Labels fail
#: in real estates — a flat battery, a store's gateway offline — and a world where every price
#: reached every shelf would make exposure a column nobody ever had to look at.
BASELINE_ACK_FAILURE_PCT = 2

#: What share of a town's stores are opened inside the declared 1 km neighbour radius of one
#: the chain already has there. Declared per world since T00E, because **it is the size of the
#: roster**: the design engine excludes the later-sorted member of every such pair, so every
#: clustered store is one no experiment may use.
#:
#: 15% in the five worlds that need no interference — a chain covering a dense neighbourhood
#: with two small shops rather than one large one is real, and roughly one store in seven being
#: that second shop is the assumption. It is an assumption about the trade; no chain's real
#: footprint was obtained and none is claimed, which is the same sentence `CATEGORY_SHAPE` and
#: `demand.py` make about themselves.
REALISTIC_CLUSTERED_PCT = 15

#: **W2 alone.** Interference has to exist for W2 to be a world at all, so its estate is
#: deliberately more clustered — and it is 30% rather than higher because W2's declared correct
#: behaviour is to *estimate on what is left*, and a world that excluded so much that nothing
#: was left would pass the interference half while making the estimate impossible. The two
#: halves of that sentence pull in opposite directions and this number is where they meet;
#: `ops.roster` measures the surviving roster, so the meeting point is a figure rather than a
#: hope.
INTERFERING_CLUSTERED_PCT = 30


@dataclass(frozen=True, slots=True)
class World:
    """One world. Everything below the first four fields is an injected pathology."""

    id: str
    title: str
    violates: str
    correct_behaviour: str

    #: What share of a town's stores sit inside the declared neighbour radius of another —
    #: see `REALISTIC_CLUSTERED_PCT`. It is not a pathology like the fields below it: every
    #: world declares one, and it is on `World` rather than in `chain.py` because it is the
    #: number that decides how much estate an experiment has left to run on.
    clustered_pct: int = REALISTIC_CLUSTERED_PCT

    #: Does the treatment arm get a different markdown schedule at all? False in W1 alone:
    #: *"Both arms get the same policy — nothing is applied."* An A/A world needs no ground
    #: truth, which is exactly what makes it unarguable — empty is empty.
    treats: bool = True

    #: W2. Per cent of a store's trade that crosses to a neighbour inside the declared radius
    #: while that neighbour is marking down harder than it is. Interference in its plainest
    #: form: a control store's outcome depends on another store's assignment, so the stable
    #: unit treatment value assumption is false and no arm mean means what it says.
    spillover_pct: int = 0

    #: W3. Per cent of treated store-SKU-days whose shelf label never takes the new price, on
    #: top of the baseline. The unit is assigned to treatment and is not exposed to it, so an
    #: intention-to-treat difference is diluted toward zero by an amount nobody declared.
    ack_failure_pct_treated: int = BASELINE_ACK_FAILURE_PCT

    #: W4. Days over which the novelty half of the response halves. A first week read as the
    #: whole window overstates the effect by however much this decays.
    novelty_half_life_days: int | None = None

    #: W4. How much of the response is novelty on day one, in per cent of the underlying
    #: response. It decays to nothing; the underlying response does not.
    novelty_boost_pct: int = 0

    #: W5. The Pareto index of the per-line quantity. Below 2 the variance is infinite, which
    #: is what a power calculation assuming a well-behaved basket does not survive.
    quantity_tail_alpha: float | None = None

    @property
    def is_aa(self) -> bool:
        return not self.treats


W1 = World(
    id="W1",
    title="Pure noise",
    violates="nothing — this is the null, and it is the one world that needs no ground truth",
    correct_behaviour="no significant uplift, at a rate at or below the declared alpha",
    treats=False,
)

# ---------------------------------------------------------------- restated 2026-08-28
#
# Three of the six `correct_behaviour` strings below were changed, and the prior wording is kept
# here because doctrine rule 4 says a correction never erases what was previously stated. These
# strings are **sealed into every truth.sealed.json**, so each is a promise this package makes
# about the system rather than a comment about it — which is why they are now written against the
# function that would keep the promise, named, rather than against `CLAUDE.md`'s table.
#
#   W2  read "detect the contamination and refuse; never estimate". There is no interference
#       detector: `holdout.core.experiment.contamination` compares the digest, the redraw and the
#       delivered policy, and no one of the three can see a neighbour's trade crossing the road.
#       The defence is at design — the engine excludes the later-sorted member of every
#       neighbouring pair at moment 1 — and the closed vocabulary's only interference code is
#       `at_design`. What W2 proves is that the exclusion is load-bearing.
#
#   W3  read "refuse below the declared exposure threshold; never silently dilute", which was true
#       and said only half of it: it never said what happens **above** the threshold. `exposure.py`
#       does — the estimate is intention-to-treat and the realised rate is printed beside it, pass
#       or fail. `CLAUDE.md`'s row said "exposure-adjust or refuse", which was not half a sentence
#       but a wrong one, and it is restated there too.
#
#   W4  read "report the declared window's average, not the first week extrapolated", which reads
#       as arithmetic the estimator performs. It does not: `close` takes `outcomes` as given and
#       cannot verify they span the declared period. What is guaranteed is `may_read` — the result
#       cannot be **asked for** early. The aggregation is the caller's obligation.
#
# W1, W5 and W6 were read against `Readout.is_significant`, `Statistic.detects` and `close`
# respectively, and stand unchanged.
W2 = World(
    id="W2",
    title="Interference between neighbouring stores",
    violates="SUTVA — a control store's outcome depends on its neighbour's assignment",
    correct_behaviour="exclude the interfering units at design, then estimate on what is left",
    clustered_pct=INTERFERING_CLUSTERED_PCT,
    spillover_pct=18,
)

W3 = World(
    id="W3",
    title="Exposure fails on a third of treated units",
    violates="the assumption that assignment and exposure are the same thing",
    correct_behaviour=(
        "report ITT with the realised exposure rate printed, or refuse below the "
        "declared threshold; never silently dilute"
    ),
    ack_failure_pct_treated=30,
)

W4 = World(
    id="W4",
    title="An effect that decays",
    violates="the assumption that an effect is constant over the declared window",
    correct_behaviour=(
        "no result before the declared end, then report what the declared window aggregated"
    ),
    novelty_half_life_days=9,
    novelty_boost_pct=55,
)

W5 = World(
    id="W5",
    title="Heavy-tailed baskets",
    violates="the variance the power calculation assumed",
    correct_behaviour="the power check fails, or the interval is honestly wide",
    quantity_tail_alpha=1.45,
)

W6 = World(
    id="W6",
    title="Everything works and a real effect is present",
    violates="nothing — and that is the point",
    correct_behaviour="produce the number. No refusal.",
)

WORLDS: dict[str, World] = {w.id: w for w in (W1, W2, W3, W4, W5, W6)}


def world_by_id(world_id: str) -> World:
    try:
        return WORLDS[world_id.upper()]
    except KeyError:
        raise ValueError(f"unknown world {world_id!r}; the six are {sorted(WORLDS)}") from None
