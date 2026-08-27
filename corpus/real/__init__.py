"""A public retail corpus: real shelf prices, a real regulated-goods list, a real margin.

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
    Quote,
    items,
    margin_series,
    median_gross_margin_fraction,
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
    "Quote",
    "items",
    "margin_series",
    "median_gross_margin_fraction",
    "quotes",
    "regulated_basket",
]
