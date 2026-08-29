"""Read the committed corpus. Standard library only, and no knowledge of a guardrail.

This module deliberately knows nothing about `holdout`. It does not import it, it does not
name a refusal code, it does not have an opinion about whether a price is admissible. It
hands out the rows a statistical office and a government gazette published, in the plainest
types Python has, and stops.

That is the whole architecture of claim 1's independence, and it is one import away from
being lost. `tests/boundary/test_corpus_imports_nothing.py` fails the build if any module
under `corpus/` ever imports `holdout`, in the same way `corpus/world/` will be held to it
for claim 2. If the corpus could reach into the core, the corpus would start agreeing with
it — not by anyone deciding to, but by the ordinary drift of the person editing both.

Everything here is `Decimal`, never `float`. The source publishes prices as decimal strings
and they are parsed as decimal strings; a corpus that went through binary floating point
would already have lost the cent the guardrails argue over.
"""

from __future__ import annotations

import csv
import gzip
import statistics
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"

QUOTES_FILE = DATA / "ons-price-quotes-2025.csv.gz"
ITEMS_FILE = DATA / "item_categories.csv"
BASKET_FILE = DATA / "greek-regulated-basket-2026.csv"
MARGIN_FILE = DATA / "eurostat-sbs-gross-margin-el.csv"

#: Claim 7's corpus: two published vocabularies of the names a person is known by.
PERSON_PROPERTIES_FILE = DATA / "schemaorg-person-properties.csv"
PII_ENTITIES_FILE = DATA / "presidio-pii-entities.csv"

#: The months in the corpus, in order, and the pairs that are consecutive. April 2025 is
#: absent — it is published as a spreadsheet rather than a CSV — so three pairs, not four.
#: `MANIFEST.yaml` records the gap; nothing here infers across it.
MONTHS: tuple[str, ...] = ("202502", "202503", "202505", "202506", "202507")
CONSECUTIVE_MONTHS: tuple[tuple[str, str], ...] = (
    ("202502", "202503"),
    ("202505", "202506"),
    ("202506", "202507"),
)

#: The collector's indicator code for a sale or special offer, from the CPI Technical
#: Manual §5.3.3. A quote carrying it is a **real markdown taken by a real retailer**, which
#: is the only place in this project a markdown depth comes from something other than us.
SALE = "S"


@dataclass(frozen=True, slots=True)
class Quote:
    """One product, in one outlet, in one month: a price a person wrote down in a shop."""

    quote_month: str
    item_id: str
    item_desc: str
    shop_code: str
    region: str
    shop_type: str
    stratum_cell: str
    price: Decimal
    indicator_box: str
    base_price: Decimal

    @property
    def outlet(self) -> str:
        """A stable identity for the outlet stratum this quote was collected in.

        The four ONS codes are carried and combined but never *interpreted* — this project
        does not claim to know what region `2` or shop type `1` is, and does not need to.
        What it needs is that two quotes from the same place get the same identity and two
        from different places do not.
        """
        return f"{self.shop_code}-{self.region}-{self.shop_type}-{self.stratum_cell}"

    @property
    def is_sale(self) -> bool:
        return self.indicator_box == SALE


@dataclass(frozen=True, slots=True)
class Item:
    """One ONS representative item, and this repository's two judgments about it.

    `scenario_category` and `greek_basket_ordinal` are **ours**, not the ONS's and not the
    gazette's. They live here rather than in the quote file so that the line between what
    was published and what was decided stays visible in the directory listing.
    """

    item_id: str
    item_desc: str
    scenario_category: str
    greek_basket_ordinal: int | None
    match: str
    note: str

    @property
    def is_regulated(self) -> bool:
        """Whether ΥΑ 21330/2026 άρθρο 6 names this product's category.

        Answered from the decision's own table, never from
        `contracts/guardrails/regulated_basket.yaml`. The two disagree, and the disagreement
        is the reason this corpus is worth having.
        """
        return self.greek_basket_ordinal is not None


@dataclass(frozen=True, slots=True)
class BasketCategory:
    ordinal: int
    category_el: str


@dataclass(frozen=True, slots=True)
class MarginObservation:
    year: int
    turnover_meur: Decimal
    gross_margin_meur: Decimal
    gross_margin_pct_of_turnover: Decimal


def quotes() -> Iterator[Quote]:
    with gzip.open(QUOTES_FILE, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            yield Quote(
                quote_month=row["quote_month"],
                item_id=row["item_id"],
                item_desc=row["item_desc"],
                shop_code=row["shop_code"],
                region=row["region"],
                shop_type=row["shop_type"],
                stratum_cell=row["stratum_cell"],
                price=Decimal(row["price"]),
                indicator_box=row["indicator_box"],
                base_price=Decimal(row["base_price"]),
            )


def items() -> dict[str, Item]:
    with ITEMS_FILE.open(encoding="utf-8", newline="") as handle:
        return {
            row["item_id"]: Item(
                item_id=row["item_id"],
                item_desc=row["item_desc"],
                scenario_category=row["scenario_category"],
                greek_basket_ordinal=(
                    int(row["greek_basket_ordinal"]) if row["greek_basket_ordinal"] else None
                ),
                match=row["match"],
                note=row["note"],
            )
            for row in csv.DictReader(handle)
        }


def regulated_basket() -> tuple[BasketCategory, ...]:
    """The 63 categories of ΥΑ 21330/12.03.2026 άρθρο 6, in the order the table states them."""
    with BASKET_FILE.open(encoding="utf-8", newline="") as handle:
        return tuple(
            BasketCategory(ordinal=int(row["ordinal"]), category_el=row["category_el"])
            for row in csv.DictReader(handle)
        )


def margin_series() -> tuple[MarginObservation, ...]:
    with MARGIN_FILE.open(encoding="utf-8", newline="") as handle:
        return tuple(
            MarginObservation(
                year=int(row["year"]),
                turnover_meur=Decimal(row["turnover_meur"]),
                gross_margin_meur=Decimal(row["gross_margin_on_goods_for_resale_meur"]),
                gross_margin_pct_of_turnover=Decimal(row["gross_margin_pct_of_turnover"]),
            )
            for row in csv.DictReader(handle)
        )


def median_gross_margin_fraction() -> Decimal:
    """The gross margin a Greek supermarket makes, as a fraction of what it sells for.

    The **median** of the published series and not its mean, because Eurostat's 2018
    observation is a break — 47.8% against roughly 17% either side of it — and a mean would
    carry that break into every cost this corpus derives. Choosing a median is a decision;
    deleting the row would have been a lie. The row is in the file.

    Computed from the file rather than written down as a constant, so that `MANIFEST.yaml`'s
    figure and this one cannot drift apart. `tests/corpus/test_manifest.py` asserts they agree.
    """
    return statistics.median(o.gross_margin_pct_of_turnover for o in margin_series()) / 100


# --------------------------------------------------- claim 7's independent vocabularies
#
# The same rule as everything above it: somebody who has never read this repository chose
# these names. Nothing here decides what a person is, and nothing here knows that a
# decision key exists — the rows are handed out in the spelling their publishers use, and
# whoever consumes them declares the derivation that turns `familyName` into `family_name`.


@dataclass(frozen=True, slots=True)
class PersonProperty:
    """One schema.org property that touches `Person`, as release 30.0 publishes it."""

    property: str
    describes_a_person: bool
    """`Person` is in the property's `domainIncludes` — an attribute a person has."""

    names_a_person: bool
    """`Person` is in the property's `rangeIncludes` — a field that *holds* a person.

    This is the half that matters to a pricing system. `customer`, `member`, `buyer`,
    `owner`, `recipient` and `underName` all arrive here, and not one of them describes a
    birthday or a body: they are the shapes a person takes when a record points at one.
    """


@dataclass(frozen=True, slots=True)
class PiiEntity:
    """One entity type Microsoft Presidio ships a recognizer for."""

    entity: str
    region: str
    """The heading it was published under — Global, USA, UK, Spain, … Carried because it is
    published, not because anything needs it."""


def person_properties() -> tuple[PersonProperty, ...]:
    with PERSON_PROPERTIES_FILE.open(encoding="utf-8", newline="") as handle:
        return tuple(
            PersonProperty(
                property=row["property"],
                describes_a_person=row["describes_a_person"] == "true",
                names_a_person=row["names_a_person"] == "true",
            )
            for row in csv.DictReader(handle)
        )


def pii_entities() -> tuple[PiiEntity, ...]:
    with PII_ENTITIES_FILE.open(encoding="utf-8", newline="") as handle:
        return tuple(
            PiiEntity(entity=row["entity"], region=row["region"]) for row in csv.DictReader(handle)
        )
