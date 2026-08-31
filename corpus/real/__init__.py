"""Two public corpora: real shelf prices for claim 1, and the names a person is known by for claim 7.

**Real inputs, derived cost.** Everything committed here was published by somebody else and is
digest-checked. The unit cost claim 1's margins rest on is not here and is not observed: no public
source carries a retailer's cost, so `evals/guardrail/build.py` derives one from a sector median.
Real prices, real law, derived cost — see `README.md`.

See `MANIFEST.yaml` for every source, its licence, its retrieval date and the digest of
every committed file, and `README.md` for what this corpus does and does not prove.

`reader.py` is the whole public surface.
"""

from corpus.real.reader import (
    CONSECUTIVE_MONTHS,
    MONTHS,
    SALE,
    BasketCategory,
    Item,
    MarginObservation,
    PersonProperty,
    PiiEntity,
    Quote,
    items,
    margin_series,
    median_gross_margin_fraction,
    person_properties,
    pii_entities,
    quotes,
    regulated_basket,
)

__all__ = [
    "CONSECUTIVE_MONTHS",
    "MONTHS",
    "SALE",
    "BasketCategory",
    "Item",
    "MarginObservation",
    "PersonProperty",
    "PiiEntity",
    "Quote",
    "items",
    "margin_series",
    "median_gross_margin_fraction",
    "person_properties",
    "pii_entities",
    "quotes",
    "regulated_basket",
]
