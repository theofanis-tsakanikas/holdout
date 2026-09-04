"""The demand model: a rate per segment, shrunk toward the whole, exactly reproducible.

**Deliberately the simplest thing that can be wrong in an interesting way.** T014 builds the
apparatus a model is judged by — the split, the calibration gate, the per-segment gate, the
promotion refusal — and every one of those is a property of the *pipeline*, not of the estimator.
A gradient-boosted anything would have made this module the subject and the gates the decoration,
and it would have needed a library the repository does not have and does not need.

What it predicts, and what it does not
--------------------------------------
**Units per store-SKU-day, at the price the policy sets.** `pipelines/ml/__init__.py` carries the
measurement that decided this: on this corpus price is a deterministic function of hours-to-expiry
within an arm, so no demand-at-a-candidate-price relationship is identified from history. The
model does not take a price argument, because a parameter that cannot be estimated is a parameter
that will be estimated anyway by whoever finds it in the signature.

The shape, and the measurement that chose it
--------------------------------------------
**A `(sku, weekday)` base rate multiplied by a store factor.** A store's size scales everything it
sells; a SKU's weekday pattern is common across stores. Multiplying the two estimates each from
every row that carries it, instead of cutting the corpus into cells that each see a handful of
days.

Measured on held-out days, `W1` at `rehearsal`, RMSE in units per store-SKU-day:

    grand mean (the baseline)        35.58
    (category, weekday)              33.48
    (store,)                         30.20
    (sku,)                           28.32
    (store, sku, weekday)            25.16
    (sku, weekday)                   26.79
    (store, sku)                     19.09
    (sku, weekday) x store factor    14.09

**Two of those rows are the argument.** The multiplicative form beats the best additive cell by a
third. And `(store, sku, weekday)` is *worse* than `(store, sku)` — 25.16 against 19.09 — which is
overfitting arriving exactly where a thinner cell was cut, measured rather than asserted.

> **This module first read `(category, weekday)`, and the paragraph said *not store* — "a
> per-store rate over a rehearsal corpus is a handful of days per cell, and a per-store model
> would be memorising rather than generalising". The prior wording stays per doctrine rule 4 and
> the delta is the finding.** It was half right and it acted on the wrong half: a per-store *cell*
> does overfit, and the table above measures it. What does not follow is that store should be
> absent. It belongs as a **factor** — one number per store, estimated from every row that store
> has — and the model that excluded it scored 33.48 against a baseline of 35.58, which is a model
> that had barely learned anything at all. **The reasoning was sound and the conclusion was
> untested**, which is the shape this repository catalogues; the table is what it cost to find.

**Not price, ladder step, or hours-to-expiry.** Those three are the same variable on this corpus,
and putting any of them in would let the model absorb the price response it cannot identify,
which would then show up as a *good* calibration number. That is the shape this repository files
against itself: a number that improves because a mistake made it improve.

The recency factor, and the shift that made it necessary
--------------------------------------------------------
**One multiplier per category, estimated from the most recent training dates only.** Baseline
demand in this scenario moves with the season, so a level averaged over the whole training window
is stale on the day it is used — the structure of a week changes slowly and the *level* does not.

Measured on held-out days, `W1` at `rehearsal`, segments outside the contract's ±10% per-segment
tolerance:

    without a recency factor    8 of 21 outside, worst 27.9%
    with one                    1 of 21 outside, worst 11.2%

and the factors themselves say what happened: **bakery 0.858**, dairy 1.046, poultry 1.017. The
model without them over-predicted bakery by about a sixth in every weekday cell, which is what the
per-segment gate reported before this existed.

**The window is not a free parameter and that matters.** It is `evaluation_days` from
`contracts/ml/training.yaml` — the level is estimated over a window exactly as long as the one it
will be used to predict — rather than a number chosen because it scored well. A recency window
tuned against the evaluation half would be the model reading its own examination paper, and the
per-segment gate would then be measuring how well it had been tuned.

**And it is fitted on training dates only**, the last of them, never on the evaluation half.

**And the model's own key is deliberately not the grouping its calibration is reported over.**
`calibration.py` groups by `(category, weekday)` — the business-meaningful cut — while the model
is parameterised on `(sku, weekday)` and store. A gate that grouped exactly the way the model is
parameterised could only ever report the model's own residual structure back to itself.

Shrinkage, and why there is any
-------------------------------
A segment seen three times has a mean that is one shopper's opinion. The fitted rate is the
segment's own total pulled toward the grand mean by a fixed pseudo-count — `PRIOR_DAYS` ordinary
days at the grand rate, added to whatever the segment actually has. It is Laplace smoothing under
another name, it needs no library, and its one parameter is a **structural** choice rather than a
tuned one: it is not in `contracts/ml/training.yaml` because it is not a threshold anything
branches on, and the moment it is tuned against the evaluation half it becomes one. If a later
session tunes it, it moves into the contract that day.

Reproducibility
---------------
`digest` is a SHA-256 over the model's own numbers in sorted order. Two fits of the same features
produce the same digest or there is a bug, and the promotion record carries it so that *which
model was approved* is a fact rather than a memory. It is deliberately not a hash of the training
data: a digest over inputs answers *were these the same rows*, and the question a model card has
to answer is *is this the same model*.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from pipelines.ml.features import DemandFeature

#: How many ordinary days at the grand rate a segment is credited with before its own days count.
#: A structural choice, not a tuned one — see the module docstring. Small enough that a segment
#: with a hundred days is essentially its own mean, large enough that one with three is not.
PRIOR_DAYS = 10


class ModelError(ValueError):
    """A model that cannot be fitted, or one asked about a segment it never saw."""


@dataclass(frozen=True, slots=True)
class DemandModel:
    """A `(sku, weekday)` base rate, a factor per store, and the grand rate both fall back to.

    `Fraction` rather than `float` throughout, for the reason `holdout.core.demand` gives: the
    arithmetic is counts over counts, it is exact, and a float would make two fits of the same
    data differ in the last bits and therefore differ in digest.
    """

    rates: Mapping[tuple[str, int], Fraction]
    """Keyed `(sku_id, weekday)`. The shape of a week for one product, pooled over every store."""

    store_factors: Mapping[str, Fraction]
    """One multiplier per store, relative to the grand rate. A big shop is a number above 1."""

    recency_factors: Mapping[str, Fraction]
    """One multiplier per category, from the most recent training dates. See the module docstring.

    Separate from `store_factors` rather than multiplied into the rates, so that a reader — and a
    model card — can see how far the recent level sat from the window's average. A factor of 0.858
    is a sixth of a category's demand having moved, and folding it away would hide the size of the
    shift the model is correcting for.
    """

    grand_rate: Fraction
    fitted_on_days: int
    censored_share: Fraction
    """What fraction of the fitting rows were reconstructed rather than observed.

    Carried on the model itself, not just reported at fit time. Doctrine rule 2 again: a model
    fitted mostly on reconstructions is a different object from one fitted mostly on receipts, and
    the difference has to survive as far as whoever approves it.
    """

    def predict(self, *, sku_id: str, weekday: int, store_id: str, category: str) -> Fraction:
        """Expected units for one store-SKU-day: the base rate, scaled by the store.

        **Keyword-only, and three of them rather than a tuple**, because the two keys this model
        uses are different shapes and a positional pair would silently accept a `(category,
        weekday)` — which is what `calibration` groups by and what an earlier version of this
        model was keyed on. A signature that accepts the wrong grouping is a signature that will
        be handed it.

        **Both fallbacks are the shallowest possible answer rather than a refusal**, and that is a
        judgement worth naming: an unseen SKU or a new store is a real shape — a product listed
        mid-year, a shop that opened — and refusing would send the decision path to its safe state
        for a reason that is not about that shop. `calibration` measures what the fallback costs
        per segment rather than hiding it in a total.
        """
        base = self.rates.get((sku_id, weekday), self.grand_rate)
        return (
            base
            * self.store_factors.get(store_id, Fraction(1))
            * self.recency_factors.get(category, Fraction(1))
        )

    @property
    def digest(self) -> str:
        """SHA-256 over the model's numbers. The identity a promotion record pins."""
        parts = [f"grand={self.grand_rate}", f"days={self.fitted_on_days}"]
        parts.extend(
            f"{sku}|{weekday}={rate}" for (sku, weekday), rate in sorted(self.rates.items())
        )
        parts.extend(
            f"store:{store}={factor}" for store, factor in sorted(self.store_factors.items())
        )
        parts.extend(
            f"recent:{category}={factor}"
            for category, factor in sorted(self.recency_factors.items())
        )
        return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()

    @property
    def segments(self) -> int:
        return len(self.rates)

    @property
    def stores(self) -> int:
        return len(self.store_factors)


def fit(features: Sequence[DemandFeature], *, recency_days: int) -> DemandModel:
    """Base rates, store factors, and a recency level — all over the training half only.

    Takes the features rather than the split, because a function that took both could be handed
    the evaluation half by a caller in a hurry. `train` in `build.py` is the one place the split
    decides which rows arrive here, and it is short enough to read.

    `recency_days` is `evaluation_days` from the contract, passed in rather than read here: the
    argument for the value belongs to the contract and the argument for *using* it belongs to the
    module docstring, and a function that fetched its own would be the third place to look.
    """
    if not features:
        raise ModelError(
            "no features to fit on. An empty fit produces a model that predicts nothing and "
            "calibrates perfectly against nothing, which is the vacuous green this repository "
            "refuses everywhere else."
        )

    grand_rate = Fraction(sum(feature.units for feature in features), len(features))

    by_rate: dict[tuple[str, int], list[int]] = {}
    by_store: dict[str, list[int]] = {}
    for feature in features:
        key = (feature.sku_id, feature.weekday)
        units, count = by_rate.setdefault(key, [0, 0])
        by_rate[key] = [units + feature.units, count + 1]
        units, count = by_store.setdefault(feature.store_id, [0, 0])
        by_store[feature.store_id] = [units + feature.units, count + 1]

    def shrunk(units: int, count: int) -> Fraction:
        return (Fraction(units) + PRIOR_DAYS * grand_rate) / (count + PRIOR_DAYS)

    rates = {key: shrunk(units, count) for key, (units, count) in by_rate.items()}
    factors = {
        store: shrunk(units, count) / grand_rate for store, (units, count) in by_store.items()
    }

    # **The recency level, fitted against what the rest of the model would have predicted.** Not
    # against the grand rate: the question is *how far is the recent level from what this model
    # says*, and answering it any other way would fold the store mix of the last fortnight into a
    # category factor.
    recent_dates = set(sorted({feature.business_date for feature in features})[-recency_days:])
    recent: dict[str, list[Fraction]] = {}
    for feature in features:
        if feature.business_date not in recent_dates:
            continue
        predicted, observed = recent.setdefault(feature.category, [Fraction(0), Fraction(0)])
        recent[feature.category] = [
            predicted
            + rates.get((feature.sku_id, feature.weekday), grand_rate)
            * factors.get(feature.store_id, Fraction(1)),
            observed + feature.units,
        ]

    censored = sum(1 for feature in features if feature.censored)
    return DemandModel(
        rates=rates,
        recency_factors={
            category: observed / predicted
            for category, (predicted, observed) in recent.items()
            if predicted > 0
        },
        # **A ratio of two shrunk means, not a shrunk ratio.** The factor is what this store sells
        # relative to the chain, and both halves are pulled toward the same grand rate — so a shop
        # with three days lands near 1 rather than near whatever those three days did.
        store_factors=factors,
        grand_rate=grand_rate,
        fitted_on_days=len({feature.business_date for feature in features}),
        censored_share=Fraction(censored, len(features)),
    )
