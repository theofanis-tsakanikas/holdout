"""The chain the six worlds happen in: stores, products, neighbours and the cost ledger."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
import yaml
from corpus.world import chain as chain_module
from corpus.world.chain import NEIGHBOUR_RADIUS_M
from corpus.world.scale import CATEGORIES, REHEARSAL, SCENARIO, SMOKE

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def built() -> chain_module.Chain:
    return chain_module.build("test-chain", SMOKE)


def test_the_chain_is_a_function_of_seed_and_scale_alone() -> None:
    one = chain_module.build("same", SMOKE)
    other = chain_module.build("same", SMOKE)
    assert [s.__dict__ if not hasattr(s, "__slots__") else s for s in one.stores] == list(
        other.stores
    )
    assert list(one.products) == list(other.products)
    assert one.neighbour_pairs == other.neighbour_pairs


def test_a_different_seed_is_a_different_chain() -> None:
    assert chain_module.build("a", SMOKE).stores != chain_module.build("b", SMOKE).stores


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


def test_every_scale_has_stores_inside_the_interference_radius() -> None:
    """W2 exists to be detected, so every scale has to contain the thing it detects.

    This is the assertion that made the placement rule deterministic. A probabilistic cluster
    left the smoke scale with **zero** neighbour pairs, so the interference world was
    structurally unable to interfere and every test about it would have passed vacuously.
    """
    for scale in (SMOKE, REHEARSAL, SCENARIO):
        pairs = chain_module.build("radius", scale).neighbour_pairs
        assert pairs, f"{scale.name} has no store within {NEIGHBOUR_RADIUS_M} m of another"


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
