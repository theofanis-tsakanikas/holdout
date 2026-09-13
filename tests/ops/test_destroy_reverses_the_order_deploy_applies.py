"""`destroy.yml`'s layer order is `deploy.yml`'s, plus `serving`, and nothing else.

Two hand-kept orders that must be each other's mirror are two enumerations of one population,
which is the defect this repository catalogues most often; `destroy.yml` says so beside its own
list and then keeps the list by hand. This reads both lines and compares them, so a layer added
to one order and forgotten in the other is red rather than an estate that cannot come down in
the order it went up.
"""

from __future__ import annotations

import re
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
ORDER = re.compile(r'^\s*order="(?P<layers>[a-z ]+)"\s*$', re.MULTILINE)


def _order(name: str) -> list[str]:
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    found = ORDER.findall(text)
    assert len(found) == 1, f"{name} declares {len(found)} `order=` line(s); this reads exactly one"
    return found[0].split()


def test_destroy_takes_every_layer_deploy_applies_and_serving() -> None:
    assert _order("destroy.yml") == [*_order("deploy.yml"), "serving"], (
        "destroy.yml's order is not deploy.yml's order followed by serving. The two are each "
        "other's mirror by contract; a layer in one and not the other cannot be torn down in "
        "the order it was built."
    )
