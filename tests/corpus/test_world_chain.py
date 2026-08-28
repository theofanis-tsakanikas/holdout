"""The chain the six worlds happen in: stores, products, neighbours and the cost ledger."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
import yaml
from corpus.world import chain as chain_module
from corpus.world.chain import NEIGHBOUR_RADIUS_M
from corpus.world.scale import CATEGORIES, HARNESS, REHEARSAL, SCENARIO, SMOKE, Scale
from corpus.world.worlds import INTERFERING_CLUSTERED_PCT, REALISTIC_CLUSTERED_PCT

#: What the fixtures below build their chain at. The realistic rate, because a chain test
#: is about the estate the five ordinary worlds happen in; W2's rate is named where it is
#: the point.
CLUSTERED_PCT = REALISTIC_CLUSTERED_PCT

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def built() -> chain_module.Chain:
    return chain_module.build("test-chain", SMOKE, clustered_pct=CLUSTERED_PCT)


def test_the_chain_is_a_function_of_seed_and_scale_alone() -> None:
    one = chain_module.build("same", SMOKE, clustered_pct=CLUSTERED_PCT)
    other = chain_module.build("same", SMOKE, clustered_pct=CLUSTERED_PCT)
    assert [s.__dict__ if not hasattr(s, "__slots__") else s for s in one.stores] == list(
        other.stores
    )
    assert list(one.products) == list(other.products)
    assert one.neighbour_pairs == other.neighbour_pairs


def test_a_different_seed_is_a_different_chain() -> None:
    assert (
        chain_module.build("a", SMOKE, clustered_pct=CLUSTERED_PCT).stores
        != chain_module.build("b", SMOKE, clustered_pct=CLUSTERED_PCT).stores
    )


def test_the_three_categories_are_the_three_the_contract_names() -> None:
    """The world and `regulated_basket.yaml` must agree on what the scenario sells.

    They are not allowed to agree by *sharing* — a corpus that read a guardrail to decide what
    a shop stocks would be taking the system's opinion as an input. So they are two lists, and
    this is the test that they say the same thing. When one moves, this goes red and somebody
    decides which one was right, which is exactly what should happen.
    """
    document = yaml.safe_load(
        (REPO_ROOT / "contracts" / "guardrails" / "regulated_basket.yaml").read_text("utf-8")
    )
    declared: set[str] = set()
    for window in document["windows"]:
        for rule in window.get("rules", []):
            if rule["id"] == "regulated_category_ids":
                declared |= set(rule["value"])
    assert declared == set(CATEGORIES), (
        "the scenario's fresh categories and the contract's regulated basket have diverged; "
        f"world says {sorted(CATEGORIES)}, contract says {sorted(declared)}"
    )


def test_every_scale_has_stores_inside_the_interference_radius_at_w2_s_clustering() -> None:
    """W2 exists to be detected, so every scale has to contain the thing it detects.

    This is the assertion that keeps the placement rule deterministic. A probabilistic cluster
    left the smoke scale with **zero** neighbour pairs, so the interference world was
    structurally unable to interfere and every test about it would have passed vacuously; the
    quota per town in `chain._clustered` is what replaced the coin.

    **It is asked at W2's clustering and not at the realistic one, since T00E.** Interference
    is a property of one world, not of the corpus: at 15% a smoke-scale town of two stores
    rounds to no cluster at all, and that is correct — W1 and W6 have nothing to interfere.
    What must never be empty is the estate of the world whose whole content is interference.
    """
    for scale in (SMOKE, REHEARSAL, HARNESS, SCENARIO):
        pairs = chain_module.build(
            "radius", scale, clustered_pct=INTERFERING_CLUSTERED_PCT
        ).neighbour_pairs
        assert pairs, f"{scale.name} has no store within {NEIGHBOUR_RADIUS_M} m of another"


def test_the_estate_s_density_does_not_move_with_the_scale() -> None:
    """T00E's other half, and the one that had no test at all before it.

    The share of an estate that sits inside the exclusion radius is the share no experiment
    may use. Before T00E the placement square was a fixed 10 km across, so every store added
    made the estate denser and that share rose without limit: 100 stores gave 109 pairs and a
    usable roster of 45, and **1,200 stores gave 4,380 pairs and a roster of 212** — three
    times the estate for less than five times the roster, saturating. The square now grows
    with the stores it holds, so the share is a property of `clustered_pct` and not of how
    big the corpus happens to be.

    Measured over store counts rather than over the declared scales, because the declared
    scales differ in SKUs and days as well and only one of the three dimensions is the
    subject. Asserted as a band rather than a number: chance still puts some stores together,
    and the claim is that the trend is flat rather than that the figure is fixed.
    """
    shares = {}
    for stores in (100, 400, 1_200):
        scale = Scale("density", stores, 1, 7, SMOKE.start_date)
        chain = chain_module.build("density", scale, clustered_pct=REALISTIC_CLUSTERED_PCT)
        paired = {store for pair in chain.neighbour_pairs for store in pair}
        shares[stores] = len(paired) / stores
    assert max(shares.values()) - min(shares.values()) < 0.10, (
        f"the share of the estate inside the exclusion radius moves with the scale: {shares}. "
        "That is the pathology T00E removed, and it caps the usable roster however many "
        "stores are added"
    )
    assert max(shares.values()) < 2 * REALISTIC_CLUSTERED_PCT / 100 + 0.10, (
        f"the estate is more crowded than its declared clustering asks for: {shares}. Each "
        "clustered store makes one pair, so about twice the declared share should be inside "
        "the radius and the rest is chance"
    )


def test_only_where_the_shops_stand_moves_between_worlds() -> None:
    """W2's estate is the same chain, more clustered — not a different chain.

    `clustered_pct` is per world since T00E, so the six worlds no longer share one geography.
    They must still share everything else: the same shops, of the same format and size, in the
    same zone, opened on the same day, selling the same products at the same prices. Otherwise
    a difference between W2 and W6 could be a difference in the estate rather than in the
    pathology, and every comparison between them would be measuring two things.

    The generator gets that for free only because it is written for it: the coordinates are
    drawn from the store's own stream in both branches and *overridden* when the store is
    clustered, so the stream is consumed identically whatever the clustering is. A version that
    skipped the draw instead would pass every other test in this file.
    """
    quiet = chain_module.build("both", SMOKE, clustered_pct=REALISTIC_CLUSTERED_PCT)
    crowded = chain_module.build("both", SMOKE, clustered_pct=INTERFERING_CLUSTERED_PCT)
    assert list(quiet.products) == list(crowded.products)
    for one, other in zip(quiet.stores, crowded.stores, strict=True):
        assert one.store_id == other.store_id
        assert (one.store_format, one.size_index, one.pricing_zone, one.opened_on, one.town) == (
            other.store_format,
            other.size_index,
            other.pricing_zone,
            other.opened_on,
            other.town,
        )


def test_a_more_clustered_estate_is_the_same_estate_with_more_of_the_same() -> None:
    """The nesting: whoever is clustered at 15% is still clustered at 30%.

    Asserted on the declaration rather than on the placement, because the placement cannot show
    it — a store clustered at both rates may be opened beside a *different* neighbour, since
    which shops are already standing has changed. What must be nested is the set, and the set
    is what `clustered_pct` declares.
    """
    scale = Scale("nesting", 400, 1, 7, SMOKE.start_date)
    quiet = chain_module._clustered("nest", scale, REALISTIC_CLUSTERED_PCT)
    crowded = chain_module._clustered("nest", scale, INTERFERING_CLUSTERED_PCT)
    assert quiet, "nothing is clustered at the realistic rate — the test proves nothing"
    assert quiet < crowded, (
        "a higher clustering rate dropped stores the lower one had clustered, so W2's estate "
        "is a different estate rather than the same one with more shops opened side by side"
    )


def test_no_clustering_leaves_only_what_chance_puts_together() -> None:
    """The floor, so the two tests above cannot be passing on chance alone.

    At 0% every neighbour pair is an accident of placement, and `AREA_PER_STORE_M2` is chosen
    so accidents are rare. If this ever stopped being a small number, the declared clustering
    would have stopped being what decides the roster.
    """
    scale = Scale("nobody", 400, 1, 7, SMOKE.start_date)
    chain = chain_module.build("nobody", scale, clustered_pct=0)
    paired = {store for pair in chain.neighbour_pairs for store in pair}
    assert len(paired) / scale.stores < 0.15, (
        f"{len(paired)} of {scale.stores} stores are inside the radius with nothing clustered "
        "at all — the estate is crowded by its own density and the declared rate is decoration"
    )


def test_neighbourhood_is_symmetric_and_never_reflexive(built: chain_module.Chain) -> None:
    for store in built.stores:
        for other in built.neighbours_of(store.store_id):
            assert other != store.store_id
            assert store.store_id in built.neighbours_of(other)


def test_a_neighbour_pair_really_is_inside_the_radius(built: chain_module.Chain) -> None:
    """Checked by arithmetic on the coordinates, not by trusting the function that built it."""
    for a, b in built.neighbour_pairs:
        one, other = built.store(a), built.store(b)
        squared = (one.x_m - other.x_m) ** 2 + (one.y_m - other.y_m) ** 2
        assert squared <= NEIGHBOUR_RADIUS_M**2
        assert one.town == other.town


def test_stores_further_apart_than_the_radius_are_not_neighbours(built: chain_module.Chain) -> None:
    """The other direction, which is the one a widened radius would quietly break."""
    for one in built.stores:
        for other in built.stores:
            if one.store_id >= other.store_id:
                continue
            squared = (one.x_m - other.x_m) ** 2 + (one.y_m - other.y_m) ** 2
            near = squared <= NEIGHBOUR_RADIUS_M**2 and one.town == other.town
            assert (other.store_id in built.neighbours_of(one.store_id)) is near


def test_every_product_is_fresh_and_priced(built: chain_module.Chain) -> None:
    for product in built.products:
        assert product.category in CATEGORIES
        assert product.base_price_cents > 0
        assert 1 <= product.shelf_life_days <= 9
        if product.substitute_of is not None:
            assert built.product(product.substitute_of).category == product.category


def test_the_cost_ledger_moves_inside_the_corpus(built: chain_module.Chain) -> None:
    """A ledger that never moved would make the as-of join untestable by construction."""
    moved = [p.sku_id for p in built.products if len(built.cost_steps(p.sku_id)) > 1]
    assert moved, "no SKU's cost ever changed; `cost_as_of` would be answerable by any join"


def test_cost_as_of_answers_with_the_cost_of_the_day_not_the_latest(
    built: chain_module.Chain,
) -> None:
    for product in built.products:
        steps = built.cost_steps(product.sku_id)
        if len(steps) < 2:
            continue
        before = steps[1].effective_from - timedelta(seconds=1)
        assert built.cost_as_of(product.sku_id, before) == steps[0].unit_cost_cents
        assert built.cost_as_of(product.sku_id, steps[1].effective_from) == (
            steps[1].unit_cost_cents
        )
        assert built.cost_as_of(product.sku_id, steps[-1].effective_from) == (
            steps[-1].unit_cost_cents
        )


def test_there_is_no_current_cost_to_reach_for(built: chain_module.Chain) -> None:
    """The mistake `CLAUDE.md` warns about is made by reaching for the easier attribute.

    So the easier attribute does not exist. This asserts the absence rather than describing
    it, because a docstring saying "always use the as-of join" is advice and this is not.
    """
    assert not hasattr(built, "current_cost")
    assert not any(name.startswith("current") for name in dir(built))


def test_a_cost_asked_for_before_the_ledger_opens_is_refused(built: chain_module.Chain) -> None:
    """Doctrine rule 3: nothing is invented. A default cost is a lie with a plausible shape."""
    sku = built.products[0].sku_id
    opens = built.cost_steps(sku)[0].effective_from
    with pytest.raises(ValueError, match="no cost known"):
        built.cost_as_of(sku, opens - timedelta(seconds=1))
