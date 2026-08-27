"""Rebuild `corpus/real/data/` from the sources `MANIFEST.yaml` cites.

This script needs the network and is **never run by CI or by `make claim-1`**. The data it
produces is committed, and `evals/guardrail/` reads the committed copy. What CI checks
instead is that every committed file still hashes to the digest `MANIFEST.yaml` records —
see `tests/corpus/test_manifest.py`. The distinction matters: an eval that downloaded its
own corpus would stop being reproducible the day a source moved, and it would stop running
on a laptop with no network, which is the one property every claim here depends on.

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
import sys
import urllib.request
from collections import Counter
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
