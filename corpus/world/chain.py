"""The chain itself: stores, products and the cost ledger behind them.

Everything here is static for a given `(seed, scale)` — it is what a real deployment would
have pulled from the ERP through Lakeflow Connect before any transaction was ever recorded,
and it is generated once and reused by every world. Two worlds built on the same seed and
scale sell the same products in the same shops; only what *happens* differs.

Geography is planar, and that is a declared assumption
-----------------------------------------------------
Stores sit at integer metre offsets from their town's centre, and "under 1 km" is then an
exact integer comparison rather than a geodesic carrying an implicit datum. A real
`store_master` would carry latitude and longitude; this one does not, because the only
question the scenario ever asks of geography is `contracts/design/inference.yaml`'s
neighbour radius, and answering it exactly matters more than looking like a GIS extract.
`docs/DECISIONS.md` records the trade.

Two numbers decide how much of the estate an experiment can use — T00E
----------------------------------------------------------------------
**How close the shops are is not a detail of the simulation; it is the size of the roster.**
The design engine excludes the later-sorted member of every pair inside the declared 1 km
radius, so every neighbour pair this file creates is a store that no experiment may use. The
first version of this module put *every second store* inside that radius, as a fixed rule,
so that W2 would always have interference to detect — and nobody multiplied the two facts
together. Measured on 2026-08-28: 100 stores gave 109 pairs, 55 exclusions and a **roster of
45**, on which no lottery in two hundred passed the readout's balance check. Adding stores
made it worse rather than better, because the towns were a fixed size and the estate got
denser: 1,200 stores left a roster of 212.

So both numbers are declared, and each is a fact about the estate rather than a constant
somebody needed:

- **`clustered_pct` is per world** (`worlds.py`), because only W2 needs interference to
  exist. It is high there and realistic in the other five, and W2's surviving roster still
  has to work — W2's correct behaviour is to *estimate on what is left*, which it cannot do
  if nothing is left.
- **`AREA_PER_STORE_M2` fixes the estate's density**, so the number of pairs that arise by
  chance rather than by intent does not move with the scale. The town's placement square
  grows with the stores it holds; before, it did not, and the ratio of pairs to stores rose
  with every store added.

Neither is measured from a real chain and neither is claimed to be — the same sentence
`CATEGORY_SHAPE` and `demand.py` make about themselves.

The cost ledger moves, and that is the point
--------------------------------------------
`CLAUDE.md`: *"A sale at 14:00 joins to the cost as it was known at 14:00. Joining to the
current cost table silently rewrites every historical margin."* A ledger that never moved
would make that sentence untestable, so costs step a handful of times over the eight months
— which also means `cost_as_of` is the only way to price a line and there is no "current
cost" to reach for by accident.
"""

from __future__ import annotations

import bisect
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from corpus.world import rng
from corpus.world.scale import CATEGORIES, Scale

#: Town centres. Enough towns that the estate is spread, and each one holds a placement square
#: that grows with the stores in it, so the estate's density is a declared constant rather than
#: a consequence of the scale — see the module docstring and `AREA_PER_STORE_M2`.
#:
#: Stores are handed out in **contiguous blocks**, so ST0001 and ST0002 are in the same town.
#: The first version dealt them round-robin, and the effect was quietly fatal: the stores in a
#: town were then every eighth ordinal, `assignment.alternating` treats every second, and every
#: neighbour pair came out with both stores in the same arm. W2 generated a world with no
#: interference in it at all and the counts matched W6 to the digit. Contiguous blocks are also
#: what a real estate looks like — store numbers grow by region, not by rotation.
TOWNS: tuple[str, ...] = (
    "Athina",
    "Thessaloniki",
    "Patra",
    "Irakleio",
    "Larisa",
    "Volos",
    "Ioannina",
    "Chania",
)

#: Store formats, their relative frequency and the size multiplier each carries.
FORMATS: tuple[tuple[str, float, float], ...] = (
    ("convenience", 0.30, 0.45),
    ("supermarket", 0.55, 1.00),
    ("hypermarket", 0.15, 2.30),
)

#: Pricing zones. A base price moves centrally, weekly, by zone — never per store per hour.
#: The zone is carried so a base-price decision has something to be central *about*, and so a
#: balance covariate that is meant to be categorical actually is one.
ZONES: tuple[str, ...] = ("zone_a", "zone_b", "zone_c")

#: Per category: the price band in cents, the shelf life band in days, and the elasticity the
#: category's demand answers a price change with. These are the scenario's own assumptions
#: about grocery retail. They are shaped to be plausible; no chain's real figures were
#: obtained and none is claimed. `corpus/world/README.md` states that in the same words.
CATEGORY_SHAPE: dict[str, tuple[int, int, int, int, float]] = {
    #                 price_lo  price_hi  life_lo  life_hi  elasticity
    "dairy": (95, 480, 4, 9, 1.7),
    "bakery": (70, 340, 1, 3, 2.3),
    "poultry": (320, 1290, 2, 5, 1.9),
}

#: How much room the estate gives each store: an 8 km square, 64 km2. A store every 8 km is
#: denser than a hundred shops spread over Greece (about 1,300 km2 each) and looser than a
#: city centre, which is the shape of a chain that concentrates where the people are — an
#: assumption about the trade, not a measurement of one, and no chain's real footprint was
#: obtained.
#:
#: **It is here so that density does not move with the scale.** The town's placement square is
#: `sqrt(stores_in_town x AREA_PER_STORE_M2)` on a side, so the expected number of neighbours a
#: store acquires *by chance* is `pi x radius^2 / AREA_PER_STORE_M2` — about one store in
#: twenty at the declared 1 km radius — whatever the scale. Before T00E the square was a fixed
#: 10 km across, so every store added made the estate denser and the share of it the design
#: engine excludes rose without limit. That is a pathology of the generator and not a fact
#: about retail, and it is what capped the usable roster at 212 however many stores were added.
AREA_PER_STORE_M2 = 64_000_000

#: How far a clustered store is opened from the one it is clustered onto, in each axis. 700 m
#: in each axis means at most 990 m apart, so a clustered store is inside the declared radius
#: **by construction** and not by arithmetic that could drift.
_CLUSTER_RADIUS_M = 700

#: The radius `contracts/design/inference.yaml` declares for automatic neighbour exclusion.
#: It is repeated here as a number rather than read from the contract, because this module
#: uses it to *place* stores and the design engine uses it to *exclude* them: the world must
#: be able to put two shops 800 m apart whatever the contract later decides to do about it.
NEIGHBOUR_RADIUS_M = 1_000


@dataclass(frozen=True, slots=True)
class Store:
    """One shop. The unit of randomisation, and the unit interference happens between."""

    store_id: str
    town: str
    x_m: int
    y_m: int
    store_format: str
    size_index: float
    pricing_zone: str
    opened_on: date

    @property
    def size_band(self) -> str:
        """A coarse band, because that is what a balance covariate can actually be checked on."""
        if self.size_index < 0.7:
            return "small"
        return "medium" if self.size_index < 1.6 else "large"


@dataclass(frozen=True, slots=True)
class Product:
    """One SKU. Fresh, so it expires, and expiring is what makes the markdown path exist."""

    sku_id: str
    category: str
    name: str
    base_price_cents: int
    shelf_life_days: int
    popularity: float
    substitute_of: str | None


@dataclass(frozen=True, slots=True)
class CostStep:
    """What a SKU cost from a moment onward. Never superseded in place — appended."""

    sku_id: str
    effective_from: datetime
    unit_cost_cents: int


class Chain:
    """Stores, products, costs and who is next door to whom."""

    def __init__(
        self,
        stores: tuple[Store, ...],
        products: tuple[Product, ...],
        costs: dict[str, tuple[CostStep, ...]],
    ) -> None:
        self.stores = stores
        self.products = products
        self._costs = costs
        self._by_store = {store.store_id: store for store in stores}
        self._by_sku = {product.sku_id: product for product in products}
        self._cost_starts = {
            sku: [step.effective_from for step in steps] for sku, steps in costs.items()
        }
        self._neighbours = _neighbours(stores)

    def store(self, store_id: str) -> Store:
        return self._by_store[store_id]

    def product(self, sku_id: str) -> Product:
        return self._by_sku[sku_id]

    def in_category(self, category: str) -> tuple[Product, ...]:
        return tuple(p for p in self.products if p.category == category)

    def neighbours_of(self, store_id: str) -> tuple[str, ...]:
        """Every store within the declared radius. Symmetric, and never including itself."""
        return self._neighbours.get(store_id, ())

    @property
    def neighbour_pairs(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            (a, b) for a, others in sorted(self._neighbours.items()) for b in others if a < b
        )

    def cost_as_of(self, sku_id: str, moment: datetime) -> int:
        """The unit cost **as it was known at `moment`**, never the current one.

        A sale at 14:00 joins to the cost as it was known at 14:00. There is deliberately no
        `current_cost` on this class: an as-of join is the only join available, so the
        mistake `CLAUDE.md` warns about cannot be made by reaching for the easier attribute.
        """
        steps = self._costs[sku_id]
        position = bisect.bisect_right(self._cost_starts[sku_id], moment)
        if position == 0:
            raise ValueError(
                f"{sku_id} has no cost known at {moment.isoformat()}; the ledger opens at "
                f"{steps[0].effective_from.isoformat()} and nothing is inferred before it"
            )
        return steps[position - 1].unit_cost_cents

    def cost_steps(self, sku_id: str) -> tuple[CostStep, ...]:
        return self._costs[sku_id]


def _neighbours(stores: tuple[Store, ...]) -> dict[str, tuple[str, ...]]:
    """Every within-radius pair, by brute force over the planar coordinates.

    Quadratic in the number of stores, which at 100 is 4,950 integer comparisons and is not
    worth an index. Exact, because the coordinates are integers and the comparison is against
    a squared radius — no square root, so no float anywhere in the answer.
    """
    limit = NEIGHBOUR_RADIUS_M * NEIGHBOUR_RADIUS_M
    found: dict[str, list[str]] = {store.store_id: [] for store in stores}
    for index, one in enumerate(stores):
        for other in stores[index + 1 :]:
            if one.town != other.town:
                continue
            dx, dy = one.x_m - other.x_m, one.y_m - other.y_m
            if dx * dx + dy * dy <= limit:
                found[one.store_id].append(other.store_id)
                found[other.store_id].append(one.store_id)
    return {store: tuple(sorted(others)) for store, others in found.items()}


def store_ids_by_town(scale: Scale) -> dict[str, tuple[str, ...]]:
    """Which stores each town holds, in ordinal order. A pure function of the scale.

    Public because both the placement square and the clustering quota are computed from it,
    and because a caller measuring the estate — `ops.roster` — should not have to re-derive
    the block assignment from the formula.
    """
    out: dict[str, list[str]] = {}
    for ordinal in range(scale.stores):
        town = TOWNS[min(ordinal * len(TOWNS) // scale.stores, len(TOWNS) - 1)]
        out.setdefault(town, []).append(f"ST{ordinal + 1:04d}")
    return {town: tuple(ids) for town, ids in out.items()}


def _half_width_m(stores_in_town: int) -> int:
    """Half the side of the town's placement square, so density is constant across scales.

    `isqrt` rather than a square root, so the answer is an integer decided by arithmetic that
    is identical on every machine — the same property every other number in this package has.
    """
    return math.isqrt(stores_in_town * AREA_PER_STORE_M2) // 2


def _clustered(seed: str, scale: Scale, clustered_pct: int) -> frozenset[str]:
    """Which stores are opened next to one the chain already has in the same town.

    A **quota per town, not a coin per store**, and the reason is about testing rather than
    about retail: a probabilistic cluster would make the smoke scale's pairs depend on the
    seed, so the interference test would pass or fail by luck. The quota rounds half up in
    integer arithmetic, is capped at one short of the town — a town's first store has nothing
    to be opened next to — and picks the stores with the lowest keyed hash.

    Two properties follow, and both are used. The choice is **order-independent**, because
    each store's key is a function of its own id. And it is **nested**: the stores clustered
    at 15% are a subset of those clustered at 40%, so W2's estate is the realistic estate
    with more of the same rather than a different one.
    """
    chosen: set[str] = set()
    for ids in store_ids_by_town(scale).values():
        quota = min((len(ids) * clustered_pct + 50) // 100, len(ids) - 1)
        if quota <= 0:
            continue
        eligible = sorted(ids[1:], key=lambda s: (rng.unit_interval(seed, "cluster", s), s))
        chosen.update(eligible[:quota])
    return frozenset(chosen)


def _build_stores(seed: str, scale: Scale, clustered_pct: int) -> tuple[Store, ...]:
    weights = tuple(share for _, share, _ in FORMATS)
    by_town = store_ids_by_town(scale)
    half = {town: _half_width_m(len(ids)) for town, ids in by_town.items()}
    town_of = {store_id: town for town, ids in by_town.items() for store_id in ids}
    clustered = _clustered(seed, scale, clustered_pct)
    stores: list[Store] = []
    placed: dict[str, list[tuple[int, int]]] = {}
    for ordinal in range(scale.stores):
        store_id = f"ST{ordinal + 1:04d}"
        draw = rng.stream(seed, "store", store_id)
        town = town_of[store_id]
        chosen = rng.choice_index(draw, weights)
        name, _, size = FORMATS[chosen]
        here = placed.setdefault(town, [])
        # Drawn from the store's own stream either way, and overridden — never skipped — when
        # the store is clustered. So the stream is consumed identically whatever
        # `clustered_pct` is, and a store's format, size and zone are the same in all six
        # worlds. Only where the shop stands moves, which is the only thing the parameter is
        # about.
        x = draw.randint(-half[town], half[town])
        y = draw.randint(-half[town], half[town])
        if here and store_id in clustered:
            pick = rng.stream(seed, "anchor", store_id)
            anchor = here[pick.randrange(len(here))]
            x = anchor[0] + pick.randint(-_CLUSTER_RADIUS_M, _CLUSTER_RADIUS_M)
            y = anchor[1] + pick.randint(-_CLUSTER_RADIUS_M, _CLUSTER_RADIUS_M)
        here.append((x, y))
        stores.append(
            Store(
                store_id=store_id,
                town=town,
                x_m=x,
                y_m=y,
                store_format=name,
                size_index=round(rng.lognormal(draw, size, 0.22), 4),
                pricing_zone=ZONES[rng.choice_index(draw, (1.0,) * len(ZONES))],
                opened_on=date(2019, 1, 1) + timedelta(days=draw.randint(0, 2000)),
            )
        )
    return tuple(stores)


def _build_products(seed: str, scale: Scale) -> tuple[Product, ...]:
    products: list[Product] = []
    for category in CATEGORIES:
        price_lo, price_hi, life_lo, life_hi, _ = CATEGORY_SHAPE[category]
        for ordinal in range(scale.skus_per_category):
            sku_id = f"{category[:3].upper()}-{ordinal + 1:03d}"
            draw = rng.stream(seed, "product", sku_id)
            # Every third SKU substitutes for the one two places before it, so a category
            # contains real substitute pairs and a cross-price effect has somewhere to land.
            substitute = (
                f"{category[:3].upper()}-{ordinal - 1:03d}"
                if ordinal >= 2 and ordinal % 3 == 2
                else None
            )
            products.append(
                Product(
                    sku_id=sku_id,
                    category=category,
                    name=f"{category} line {ordinal + 1}",
                    base_price_cents=draw.randint(price_lo, price_hi),
                    shelf_life_days=draw.randint(life_lo, life_hi),
                    popularity=round(rng.lognormal(draw, 1.0, 0.55), 4),
                    substitute_of=substitute,
                )
            )
    return tuple(products)


def _build_costs(
    seed: str, scale: Scale, products: tuple[Product, ...]
) -> dict[str, tuple[CostStep, ...]]:
    """A ledger that opens before the corpus does and steps a few times inside it.

    It opens a week early on purpose: a cost ledger whose first entry coincided with the
    first sale would make `cost_as_of` answerable for every line by accident, and would hide
    the failure mode where a line arrives before any cost is known.
    """
    opens = datetime.combine(scale.start_date - timedelta(days=7), datetime.min.time())
    ledger: dict[str, tuple[CostStep, ...]] = {}
    for product in products:
        draw = rng.stream(seed, "cost", product.sku_id)
        margin = rng.normal(draw, 0.24, 0.05)
        margin = min(max(margin, 0.08), 0.42)
        cost = max(1, round(product.base_price_cents * (1.0 - margin)))
        steps = [CostStep(product.sku_id, opens, cost)]
        for _ in range(draw.randint(1, 4)):
            day = draw.randint(1, max(1, scale.days - 1))
            moment = datetime.combine(
                scale.start_date + timedelta(days=day), datetime.min.time()
            ) + timedelta(hours=draw.randint(0, 23))
            cost = max(1, round(cost * rng.lognormal(draw, 1.0, 0.06)))
            steps.append(CostStep(product.sku_id, moment, cost))
        steps.sort(key=lambda step: step.effective_from)
        ledger[product.sku_id] = tuple(steps)
    return ledger


def build(seed: str, scale: Scale, *, clustered_pct: int) -> Chain:
    """The chain for a seed, a scale and a declared clustering.

    `clustered_pct` is required and has no default. It is the one thing about the estate that
    differs between worlds — see `worlds.World.clustered_pct` — and it decides how much of the
    estate the design engine will exclude, which is the size of the roster and therefore
    whether an experiment can exist at all. A default here would be a fourth place that number
    is decided, and the quiet one.

    Everything else is identical for every world built on the same seed and scale: the same
    products at the same prices in shops of the same format, size and zone. Only where the
    shops stand moves.
    """
    if not 0 <= clustered_pct <= 100:
        raise ValueError(
            f"clustered_pct is a percentage of the stores in a town, got {clustered_pct}"
        )
    stores = _build_stores(seed, scale, clustered_pct)
    products = _build_products(seed, scale)
    return Chain(stores, products, _build_costs(seed, scale, products))
