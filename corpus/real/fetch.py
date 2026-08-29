"""Rebuild `corpus/real/data/` from the sources `MANIFEST.yaml` cites.

This script needs the network and is **never run by CI, by `make claim-1` or by
`make claim-7`**. The data it produces is committed, and `evals/guardrail/` and
`evals/oversight/` read the committed copy. What CI checks instead is that every committed
file still hashes to the digest `MANIFEST.yaml` records — see `tests/corpus/test_manifest.py`.
The distinction matters: an eval that downloaded its own corpus would stop being reproducible
the day a source moved, and it would stop running on a laptop with no network, which is the
one property every claim here depends on.

Two corpora, two claims
-----------------------
`corpus/real/` began as claim 1's independent corpus — prices nobody here chose. It now holds
a second one for claim 7: **the names other people's published vocabularies use for a person**.
The rule is the same in both cases and it is the only rule that matters here — *somebody who
has never read this repository chose the inputs*. A list of person-shaped words written by
whoever also wrote the field names is one function agreeing with itself, which is claim 7's
trap exactly.

Run it as `python corpus/real/fetch.py` from the repository root. It prints what it kept
and what it dropped, so a rebuild that quietly loses half the corpus is visible.

Why this file exists at all, rather than a sentence in a README: the corpus is the evidence
claim 1 rests on, and evidence whose provenance is a description rather than a command is
evidence nobody can check.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import re
import sys
import urllib.request
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

ONS_BASE = (
    "https://www.ons.gov.uk/file?uri=/economy/inflationandpriceindices/datasets/"
    "consumerpriceindicescpiandretailpricesindexrpiitemindicesandpricequotes/"
)

#: The five months of 2025 that share one file schema. January 2025 is deliberately
#: excluded and April 2025 is unavailable as CSV — both are argued in `MANIFEST.yaml`
#: under "What was dropped and why".
ONS_MONTHS: tuple[tuple[str, str], ...] = (
    ("202502", "pricequotesfebruary2025/upload-pricequotes202502.csv"),
    ("202503", "pricequotesmarch2025/upload-pricequotes202503.csv"),
    ("202505", "pricequotesmay2025/upload-pricequotes202505.csv"),
    ("202506", "pricequotesjune2025/upload-pricequotes202506.csv"),
    ("202507", "pricequotesjuly2025/upload-pricequotes202507.csv"),
)

#: The ONS representative items kept, and nothing else. The set is the join key between a
#: national statistical collection and this project's scenario categories; the mapping
#: itself lives in `data/item_categories.csv`, which is **ours** and says so. Keeping the
#: two apart is the point: the prices are somebody else's, the categorisation is not.
KEPT_ITEMS: frozenset[str] = frozenset(
    {
        # bakery
        "210102",
        "210106",
        "210111",
        "210113",
        "210114",
        "210115",
        "210116",
        "210324",
        # dairy
        "211305",
        "211306",
        "211501",
        "211506",
        "211509",
        "211510",
        "211511",
        "211709",
        "211710",
        "211713",
        "211807",
        "211814",
        "211815",
        # poultry
        "210905",
        "210910",
        "211019",
        "211026",
        "211029",
        # frozen categories in the scenario — priced here so the gate can be attacked
        "211101",
        "211105",
        "211106",  # fresh_fish
        "211816",  # infant_formula
        "320108",
        "320115",
        "320206",  # tobacco
        "310401",
        "310403",
        "310406",
        "310430",  # spirits
    }
)

FIELDS = (
    "quote_month",
    "item_id",
    "item_desc",
    "cs_id",
    "cs_desc",
    "shop_code",
    "region",
    "shop_type",
    "stratum_cell",
    "price",
    "indicator_box",
    "base_price",
)


def _download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "holdout-corpus-fetch/1"})
    with urllib.request.urlopen(request, timeout=300) as response:
        body: bytes = response.read()
    return body


def _rows(month: str, payload: bytes) -> tuple[list[dict[str, str]], Counter[str]]:
    """The rows of one month that survive, and a census of everything discarded.

    Three exclusions, each for a stated reason and each counted rather than assumed:

    * `VALIDITY` other than `TRUE` — the ONS itself does not use these quotes in index
      production, so treating them as observed shelf prices would be reading the source
      as saying something it does not say;
    * a zero price — the indicator codes `T` (temporarily out of stock) and `M` (item
      missing) mean *no price was collected*. A zero here is an absence, and reading an
      absence as €0.00 is doctrine rule 3 exactly;
    * an item outside `KEPT_ITEMS`.
    """
    dropped: Counter[str] = Counter()
    kept: list[dict[str, str]] = []
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    for row in reader:
        if row["ITEM_ID"] not in KEPT_ITEMS:
            dropped["item not in scope"] += 1
            continue
        if row["VALIDITY"] != "TRUE":
            dropped["VALIDITY is not TRUE"] += 1
            continue
        price = row["PRICE"].strip()
        if not price or float(price) <= 0:
            dropped[f"no price collected (indicator {row['INDICATOR_BOX'] or 'blank'!s})"] += 1
            continue
        kept.append(
            {
                "quote_month": month,
                "item_id": row["ITEM_ID"],
                "item_desc": row["ITEM_DESC"].strip(),
                "cs_id": row["CS_ID"],
                "cs_desc": row["CS_DESC"].strip(),
                "shop_code": row["SHOP_CODE"],
                "region": row["REGION"],
                "shop_type": row["SHOP_TYPE"],
                "stratum_cell": row["STRATUM_CELL"],
                "price": price,
                "indicator_box": row["INDICATOR_BOX"],
                "base_price": row["BASE_PRICE_CPI"].strip(),
            }
        )
    return kept, dropped


# ------------------------------------------------------- claim 7's independent vocabularies
#
# Two published lists of the names a person is known by, from two publishers with nothing to
# do with each other and nothing to do with this repository. Both are pinned to an exact
# version rather than to a moving branch, because "latest" is not a provenance.

#: schema.org, pinned at release 30.0. The extraction rule is mechanical and is the whole of
#: the derivation: a property is kept when `Person` appears in its `domainIncludes` (an
#: attribute a person has) or in its `rangeIncludes` (a field that *holds* a person). The
#: second half is the one that matters — it is where `customer`, `member`, `buyer`, `owner`
#: and `recipient` come from, and none of them describes a person's body or birthday.
SCHEMA_ORG_VERSION = "30.0"
SCHEMA_ORG_PROPERTIES = (
    f"https://schema.org/version/{SCHEMA_ORG_VERSION}/schemaorg-current-https-properties.csv"
)
SCHEMA_ORG_PERSON = "https://schema.org/Person"

#: Microsoft Presidio's published list of the PII entity types it ships recognizers for,
#: pinned at the commit that produced the committed file. A different flavour of the same
#: question: not "what does a person have" but "what would a detector go looking for".
PRESIDIO_COMMIT = "eb93051b60b7daa44b4b8b1acdcce60522bacc8a"
PRESIDIO_ENTITIES = (
    f"https://raw.githubusercontent.com/microsoft/presidio/{PRESIDIO_COMMIT}"
    "/docs/supported_entities.md"
)

PERSON_PROPERTY_FIELDS = ("property", "describes_a_person", "names_a_person")
PII_ENTITY_FIELDS = ("entity", "region")

_ENTITY = re.compile(r"^[A-Z][A-Z0-9_]*$")
_SECTION = re.compile(r"^###\s+(.+?)\s*$")


def _person_properties(payload: bytes) -> list[dict[str, str]]:
    """schema.org properties that touch `Person`, in the publisher's own spelling.

    Nothing is renamed here. `familyName` is written down as `familyName`; turning it into
    `family_name` is a *derivation* and it belongs to whoever consumes the corpus, stated as
    such, not to the file that records what was published.
    """
    kept: list[dict[str, str]] = []
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    for row in reader:
        domain = {value.strip() for value in row["domainIncludes"].split(",")}
        range_ = {value.strip() for value in row["rangeIncludes"].split(",")}
        describes = SCHEMA_ORG_PERSON in domain
        names = SCHEMA_ORG_PERSON in range_
        if not (describes or names):
            continue
        kept.append(
            {
                "property": row["label"],
                "describes_a_person": "true" if describes else "false",
                "names_a_person": "true" if names else "false",
            }
        )
    kept.sort(key=lambda r: r["property"])
    return kept


def _pii_entities(payload: bytes) -> list[dict[str, str]]:
    """Presidio's entity types, with the region heading each one was published under.

    The document is a set of Markdown tables under `###` headings — Global, USA, UK, Spain,
    and so on. The heading is carried because it is published, not because anything here
    uses it: a corpus that dropped it would be answering a question nobody asked it.
    """
    kept: list[dict[str, str]] = []
    section = ""
    for line in payload.decode("utf-8").splitlines():
        stripped = line.strip()
        heading = _SECTION.match(stripped)
        if heading:
            section = heading.group(1)
            continue
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 2 or not _ENTITY.match(cells[0]):
            continue
        kept.append({"entity": cells[0], "region": section})
    kept.sort(key=lambda r: (r["region"], r["entity"]))
    return kept


def _write_csv(target: Path, fields: Sequence[str], rows: Sequence[dict[str, str]]) -> None:
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    print(f"wrote {target.relative_to(HERE.parent.parent)}  {len(rows):,} rows")
    print(f"sha256 {digest}")


def fetch_person_vocabularies() -> None:
    print("\nfetching schema.org properties … ", end="", flush=True)
    payload = _download(SCHEMA_ORG_PROPERTIES)
    print(f"{len(payload):,} bytes  sha256 {hashlib.sha256(payload).hexdigest()[:16]}…")
    _write_csv(
        DATA / "schemaorg-person-properties.csv",
        PERSON_PROPERTY_FIELDS,
        _person_properties(payload),
    )

    print("\nfetching presidio supported entities … ", end="", flush=True)
    payload = _download(PRESIDIO_ENTITIES)
    print(f"{len(payload):,} bytes  sha256 {hashlib.sha256(payload).hexdigest()[:16]}…")
    _write_csv(DATA / "presidio-pii-entities.csv", PII_ENTITY_FIELDS, _pii_entities(payload))


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    everything: list[dict[str, str]] = []
    census: Counter[str] = Counter()
    for month, suffix in ONS_MONTHS:
        url = ONS_BASE + suffix
        print(f"fetching {month} … ", end="", flush=True)
        payload = _download(url)
        print(f"{len(payload):,} bytes  sha256 {hashlib.sha256(payload).hexdigest()[:16]}…")
        kept, dropped = _rows(month, payload)
        everything.extend(kept)
        census.update(dropped)
        print(f"  kept {len(kept):,}")

    everything.sort(key=lambda r: (r["quote_month"], r["item_id"], r["shop_code"]))

    target = DATA / "ons-price-quotes-2025.csv.gz"
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(FIELDS), lineterminator="\n")
    writer.writeheader()
    writer.writerows(everything)
    # mtime=0 so a rebuild of identical data produces an identical file, and the digest in
    # MANIFEST.yaml is a statement about the data rather than about when it was zipped.
    with gzip.GzipFile(target, "wb", mtime=0) as handle:
        handle.write(buffer.getvalue().encode("utf-8"))

    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    print(f"\nwrote {target.relative_to(HERE.parent.parent)}  {len(everything):,} rows")
    print(f"sha256 {digest}")
    print("\ndropped:")
    for reason, count in census.most_common():
        print(f"  {count:>9,}  {reason}")

    fetch_person_vocabularies()
    return 0


if __name__ == "__main__":
    sys.exit(main())
