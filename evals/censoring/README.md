# Claim 4 — a stock-out is never read as zero demand

> *Trap: a simulator that generates censoring with the model that corrects it → validated on
> a held-out segment with full shelf availability.*

```
make claim-4        the eval, and the nine mutations claim 4 owns   ~1 min
make eval-censoring the eval alone, about five seconds
```

---

## 1 · What is attacked

Three adversarial worlds are generated, ~81,000 store-SKU-days, and about a fifth of them are
days the shelf emptied on. Every one is read the way the system would read it, and then one
question is asked eleven ways: **does a truncated day ever get averaged as though nothing had
been hidden?**

| id | the question it would answer `false` |
|---|---|
| `C1.a-stock-out-is-never-a-point-observation` | does every day the shelf emptied come back censored, and every day it held come back observed? |
| `C2.a-stock-out-is-never-corrected-to-zero-demand` | over every censored day the corpus produced and every one the sweep constructed, does the correction ever answer that demand was zero? |
| `C3.a-shape-that-would-hide-a-stock-out-is-refused` | are all seven declared tampers refused — a reconstruction under its own receipts, a curve with no evidence in it, an hour outside the trading day? |
| `C4.a-day-the-shelf-held-is-never-moved` | on a day with full availability, does the correction return exactly what sold, as integers, with no tolerance? |
| `C5.the-reconstruction-recovers-more-of-the-withheld-truth` | at every censor hour, does the reconstruction land closer to the withheld truth than the naive reading? |
| `C6.the-curve-learns-only-from-days-the-shelf-held` | offered a censored day, does `fit` refuse it rather than quietly leave it out? |
| `C7.the-graded-days-are-not-the-days-the-curve-was-fitted-on` | is the held-out segment disjoint from the fitting segment, and is neither empty? |
| `C8.a-reconstructed-day-still-says-it-was-reconstructed` | does the censoring mark survive all the way out of the function? |
| `C9.every-censoring-shape-is-reached` | is there an input for every declared shape, so no branch passes by never being tried? |
| `C10.the-reconstruction-lands-where-the-independent-arithmetic-puts-it` | does a second implementation land on the same integer, and on the same hourly boundaries? |
| `C11.the-naive-reading-is-wrong-here-and-the-corpus-says-so` | is there enough censoring in these worlds for any of the above to mean anything? |
| `C12.no-sale-falls-after-the-hour-the-shelf-is-recorded-as-empty` | does any censored day sell after the hour its shelf is recorded empty from — which would inflate the reconstruction without bound? |

**`C2` carries the claim and `C5` is what makes it worth having.** A system that answers "no
number" to every censored day satisfies `C2` perfectly and is useless — which is the same
shape as W6 in claim 2, where refusing everything passes every world and proves nothing.
`C11` is the third leg: a gate shown to bite on a corpus with nothing to bite on has not been
shown to bite.

---

## 2 · Where the independence is

Four separations, strongest last.

**Nobody chose which store-days run out.** The corpus's stock-outs come out of the
simulation's replenishment arithmetic — a naive forecast (popularity, store size, day of week,
season; *not* the weather and *not* the markdown that has not happened yet) against a service
factor of 1.30, consumed first-expired-first-out. A hot Saturday sells out and a wet Tuesday
is thrown away. All three worlds used here were built for claim 2, before this claim had a
line of code, and **W5 is in the set because its heavy-tailed store-day demand is the hardest
input available** — a shock the replenishment planner ordered against and the analyst never
saw is exactly what empties a shelf.

**`corpus/world/` cannot see the system.** It imports nothing from `holdout` —
`ops/isolation.py` is the one implementation of that rule, `tests/boundary/` is the gate that
runs on every push and `.claude/hooks/corpus_isolation.py` refuses the write before it lands.
The join lives in `build.py`, in this directory, where it can be read as one thing.

**The eval may not read the simulator's shape.** `corpus/world/demand.py` holds
`HOURLY_PROFILE`, the category elasticities, the seasonal swing and the reference-price decay
— the process that produced the intraday shape this correction has to learn. No module under
`evals/censoring/` and no module under `src/holdout/core/demand/` may import it, and
`tests/evals/test_censoring_instrument.py` scans for it in both directions. Without that scan
the whole exercise would be one function agreeing with itself, one import at a time.

**The truth is a number the corpus emitted, not one the simulator declared.** This is the
answer to the trap and it is worth stating exactly. The curve is fitted on store-days in the
**first 60% of the calendar** on which the shelf held. It is graded on store-days in the
**last 40%** on which the shelf held — days with full availability, where there is no
censoring to correct and so nothing for a correction to hide behind. Each of those is censored
on purpose at a declared hour, the hours after it withheld, and the reconstruction is compared
against **what that day actually sold**. A receipt total. Not a latent Poisson intensity, not
an unserved-demand column, not anything the generator knows and the grader was told.

So the correction cannot be right by sharing the simulator's assumptions: it is graded against
observations, by a grader that never opens the generator. The generator could be replaced with
a completely different model of shopping and every figure below would still be a measurement
of the same thing.

**And the boundary is computed twice.** `reference.py` reconstructs every corrected day a
second time — integers only, no share ever formed, the curve rescanned per hour instead of
accumulated — and `C10` compares the two as integers with no tolerance, over 176,266
reconstructions and the 48 hourly boundaries directly. `evals/guardrail/README.md`'s argument
for `G10` applies unchanged: a reconstruction reaches a boundary *through* a store-day, so on
its own it only sees a misplaced boundary where a day's sales happen to land in the gap.

---

## 3 · Observed, derived, swept

| | |
|---|---|
| **observed** | every unit sold, the hour it sold in, whether the shelf emptied and when |
| **derived**, with the arithmetic stated | the hourly breakdown of a store-SKU-day, summed from POS lines by `event_ts.hour`. `HourlySales` refuses a day whose hours do not add up to the shelf record's `sold_qty`, so the derivation cannot drift from its source |
| **swept**, not claimed | the hour a held-out day is artificially censored at — a declared, deterministic grid, never drawn |

Three members of the grid are there for a named reason rather than to fill a range: `07:00`,
the first trading hour, where the observed window has zero width and the share is exactly `0`;
`08:00`, where a day that sold nothing in its first hour arrives with `at_least == 0` and a
share above zero, which is **the one line where dividing the evidence by the share returns
zero**; and `22:00`, the last trading hour, where the naive reading looks most defensible and
the correction is closest to a no-op. A gate shown to bite only where the error is enormous
has not been shown to bite.

---

## 4 · What came out

Measured, three worlds at `rehearsal` scale, seed `holdout-w-0001`:

```
16,942 of 80,640 store-days emptied (21.0%)   ·   fitted on 37,144, graded on 26,554

censored at   share    naive reading      reconstruction     pooled
   07:00      0.0000   no point estimate on any of 26,554 days
   08:00      0.0629   -91.4% … -91.2%    +36.4% … +40.5%    -1.5% … -0.6%
   12:00      0.3063   -68.2% … -67.8%     +3.8% …  +5.3%    +0.1% … +0.3%
   16:00      0.5523   -44.2% … -44.0%     +0.7% …  +1.2%    -0.2% … +0.3%
   19:00      0.7451   -25.1% … -25.0%     -0.0% …  +0.4%    -0.2% … +0.3%
   22:00      0.9393    -6.0% …  -5.8%     -0.1% …  +0.0%    +0.0% … +0.2%

176,266 reconstructions + 48 hourly boundaries vs a second implementation,
as integers with no tolerance: 0 disagreements
```

**The estimand is named because the choice of one would otherwise be doing work.**
`reconstruction` is a ratio of sums over the days that produced a point estimate. `pooled` is the
same expansion applied to the **sum** over every graded day, conditioning on nothing.

**The 08:00 row was not expected, and the pair is what settles what it is.** A day only yields a
point estimate if it sold something inside the observed window, so conditioning on that in a *thin*
window keeps the days that over-performed in it — and the conditional figure comes out 36–40% high
while the unconditional one lands at −1.5% to −0.6% on the very same hour. That is selection, not a
correction that breaks at small shares, and the column is published so a reader does not have to
take the sentence's word for it. Three things that could have produced the number instead, and did
not: the fit/grade drift at 08:00 is −0.6% to −1.5% relative, which pushes the reconstruction *low*
and is a thirtieth of the size; ratio-of-sums is the most flattering of the three estimands, not the
least (mean-of-ratios is +97% to +162%, the median +45% to +78%); and `C10` puts the arithmetic
itself against a second implementation at every boundary.

**`C5` is weakest exactly where the error is largest**, and that is worth saying beside the row it
concerns. At a share of 0.06 the bar `C5` sets is *beat −91.2%*, which almost any reconstruction
clears — so the +40% is measured and printed, bounded by nothing here. What `C5` bounds is the
wide-window end, where the naive reading is already close and there is little room to hide.

**Which way the correction errs is a property of the source.** `censoring.py` argues that the
reconstruction errs high, because the observed units include a partly-traded emptying hour the share
excludes. That holds only if `stocked_out_from_hour` is the hour the shelf emptied. In this corpus
it is the hour the **first shopper was turned away**, and on **7,290 of 16,942 censored store-days
(43.0%)** that is strictly later than the last hour anything sold — by up to fourteen hours — so on
those days the share covers hours nothing could have sold in and the reconstruction errs *low*
instead. Against a stock-out hour derived from the last inventory movement the same corpus corrects
**+6.3%**. Nothing here reconciles the two: what a column means belongs to whoever writes it, and
the module says so rather than defaulting. What does not depend on the source is the bound —
`C12` measures that no censored day sells *after* its recorded hour, which is the one shape that
would inflate a reconstruction without limit.

## 5 · What this does not prove

Printed on every run through `Report.notes`, not kept here where it could quietly stop being
true. In short:

* **A day censored on purpose is not a stock-out.** A real shelf empties on unusually busy
  days, so real censoring is correlated with the very quantity being reconstructed and the
  sweep's is not. Nothing in this repository holds the unserved demand that would close that
  gap, and the corpus deliberately does not emit it — a corpus that did would be handing this
  claim the answer it exists to reconstruct.
* **The reconstruction answers how much of a day's demand the observed window saw.** It does
  not answer what would have sold had the shelf been full. No data here contains that.
* **The intraday shape in this corpus is close to a straight line**, because the generator
  spreads a price segment's arrivals uniformly across its hours. A lumpier real profile would
  be harder, and the residual error above is a floor rather than an estimate of one.
* **A real stock-out hour is partly traded and a constructed one is not**, so the direction
  the correction errs in on a real stock-out is argued from the arithmetic rather than
  measured.
* **One pooled curve per world.** Per category, per store format, per day of week — all are a
  caller's decision and none is exercised.
* **Three worlds, one seed, one scale.** And nine mutations, which is the set of breaks we
  thought of.

---

## 6 · Two findings, both from running it rather than reading it

Neither was visible in the code. `CLAUDE.md`'s rule: *an assertion about what the system does
is written against the function that would make it true, named, **and against the measurement
of what comes out when it runs**.*

### The corpus reaches a shape this file said it could not

An earlier draft of `checks.py` declared two censoring shapes unreachable from the corpus and
constructible only by the sweep, on the reasoning that a shelf empties by being sold out.
**One of the two is reachable.** W5's heavy-tailed store-days empty a shelf inside the *first*
trading hour three times in 26,880, having sold up to three units — a shape nobody built for
this claim, produced by a pathology that exists for claim 2.

It was found by `gate-proof` reporting `CRASHED`, not by reading the corpus: the first version
of `an-empty-shelf-sold-nothing-so-demand-was-nothing` set `units=0` on both no-evidence
branches, and `DemandEstimate` refused to be constructed with zero units over the two that
day had sold. Which of the five shapes come from the corpus is now **measured and published**
rather than asserted, and the count is in `C9`'s detail line.

### A gate shown to bite by the wrong guard

`C6` offers `fit` a censored day and requires a refusal. It first offered the day **on its
own** — and `the-curve-learns-from-the-days-the-shelf-emptied` reported `SURVIVED`. It was
right to. A `fit` that *skipped* censored days instead of refusing them still went red on a
pile of one, because the empty curve it then built was refused by
`AvailabilityCurve.__post_init__` — a different guard, catching it for a different reason.

*A gate can only be shown to bite where it is the gate that refuses.* The fix was to the
eval, never to the assertion: each censored day is now offered alongside a day the shelf held,
which is the shape a caller who has not sorted their input actually hands over. A corrector
that filters silently returns a perfectly good curve from that pile, and only `fit` raising
can catch it. This is the fifth instance of *a guard tested by its author is tested in the
shape the guard already handles* — and, this time, it was the mutation harness that found it
rather than a review.

### Three sentences that were true of the mechanism and false of the run

Found by oversight level 2 in fresh context, by running things rather than by reading three
documents that had been written from the same sentence. All three are the defect
`CLAUDE.md`'s checklist names — an assertion written against a projection instead of against the
measurement of what comes out — and all three are corrected in place with the prior wording kept.

* **`build.py` said the time split cost accuracy.** *"The shape drifts between them and the
  reconstruction comes out slightly low. A random split would have made every figure in `C5` look
  better."* Neither half survives: the reconstruction comes out **high** at eleven of the fifteen
  grid points, and a random 60% split graded on the same days is better at seven and worse at
  eight, every difference under 0.5 points. The split is cheap insurance; **grading against receipt
  totals is where the independence comes from**, and §2 now says so in that order.
* **`build.py` said W6 changes the shape the correction is fitted on.** The three fitted curves lie
  within **0.0023** of one another, and W6's cumulative share is marginally *earlier* than W1's, not
  later. The worlds vary the stock-out population, not the intraday shape, and W5 earns its place
  on that rather than on shape.
* **`ShelfState` said the stock-out hour is derivable from inventory movements.** On 43.0% of
  censored store-days in this corpus it is not — see §4. The docstring now states the two readings a
  source might supply and which way each makes the correction err, and `C12` measures the one
  property that does not depend on the answer.

The review also confirmed, by running it, the thing this eval most needed confirming from outside:
the fitted curve recovers the generator's **uniform-within-segment arrival draw** and not
`HOURLY_PROFILE` — `max|curve − profile|` is 0.105 against `max|curve − uniform|` of 0.010 — and
substituting a hand-copied `HOURLY_PROFILE` for the fitted curve in *both* implementations, so `C10`
stays green, turns `C5` red at +193.5%. That backstop is real but contingent: it works because the
profile is not the realised shape. Had the generator drawn arrivals per hour from it, copying the
constant would be the right answer and nothing here would notice.
