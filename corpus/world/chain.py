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
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from corpus.world import rng
from corpus.world.scale import CATEGORIES, Scale

#: Town centres. Enough towns that the estate is spread, few enough that stores land inside
#: the interference radius of one another — which W2 needs and which a uniformly scattered
#: estate would never produce.
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

#: How far a store may sit from its town centre, in metres.
_TOWN_RADIUS_M = 5_000

#: Every second store a town gets is opened close to one the chain already has there. Real
#: estates cluster — a chain covers a dense neighbourhood with two small shops rather than one
#: large one — and it is stated as a rule rather than a probability for a reason that is about
#: testing rather than about retail: **W2 exists to be detected, so every scale has to contain
#: the thing it detects.** Scattering stores uniformly over eight towns gives zero neighbour
#: pairs at 20 stores and a handful at 100, which was measured before this was written rather
#: than assumed after; and a *probabilistic* cluster would make the smoke scale's pairs depend
#: on the seed, so the interference test would pass or fail by luck.
#:
#: 700 m in each axis means at most 990 m apart, so a clustered store is inside the declared
#: radius by construction and not by arithmetic that could drift.
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


def _build_stores(seed: str, scale: Scale) -> tuple[Store, ...]:
    weights = tuple(share for _, share, _ in FORMATS)
    stores: list[Store] = []
    placed: dict[str, list[tuple[int, int]]] = {}
    for ordinal in range(scale.stores):
        store_id = f"ST{ordinal + 1:04d}"
        draw = rng.stream(seed, "store", store_id)
        town = TOWNS[min(ordinal * len(TOWNS) // scale.stores, len(TOWNS) - 1)]
        chosen = rng.choice_index(draw, weights)
        name, _, size = FORMATS[chosen]
        here = placed.setdefault(town, [])
        if here and len(here) % 2 == 1:
            anchor = here[draw.randrange(len(here))]
            x = anchor[0] + draw.randint(-_CLUSTER_RADIUS_M, _CLUSTER_RADIUS_M)
            y = anchor[1] + draw.randint(-_CLUSTER_RADIUS_M, _CLUSTER_RADIUS_M)
        else:
            x = draw.randint(-_TOWN_RADIUS_M, _TOWN_RADIUS_M)
            y = draw.randint(-_TOWN_RADIUS_M, _TOWN_RADIUS_M)
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


def build(seed: str, scale: Scale) -> Chain:
    """The chain for a seed and a scale. Identical for every world built on them."""
    stores = _build_stores(seed, scale)
    products = _build_products(seed, scale)
    return Chain(stores, products, _build_costs(seed, scale, products))
