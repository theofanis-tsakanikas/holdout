"""The five silver tables, as functions over frames rather than as pipeline definitions.

`pipeline.py` is what declares them to Spark Declarative Pipelines; this is what they do. The
split is the same one `pipelines/ingest/` makes between the driver and its sink: a transformation
that can only be exercised by starting a pipeline is a transformation nobody tests.

Every function returns **`(kept, quarantined)`** — never a single frame — because
`CLAUDE.md` says *quarantine, not drop*, and a signature that could return only the good rows is
one where dropping is the easier path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyspark.sql import Window
from pyspark.sql import functions as sf

from pipelines.silver.expectations import Expectation, apply

if TYPE_CHECKING:
    from pyspark.sql import DataFrame

#: The business key `CLAUDE.md` names for a receipt line: *"The same receipt line delivered twice
#: is one event; two identical baskets in the same second at the same till are two."* A hash of
#: the payload would collapse the second case into the first and quietly delete a sale.
SALE_KEY: tuple[str, ...] = ("transaction_id", "line_no")


def sales(pos_lines: DataFrame) -> tuple[DataFrame, DataFrame]:
    """What was sold, once per business key, whatever the transport delivered twice.

    **Deduplication keeps the earliest arrival**, not an arbitrary row: the ingest driver
    delivers a duplicate with the same `arrival_ts`, so the choice is only visible when a real
    transport redelivers later — and keeping the first is what makes the table a function of the
    events rather than of the retry.
    """
    first = Window.partitionBy(*SALE_KEY).orderBy(sf.col("arrival_ts").asc())
    deduplicated = (
        pos_lines.withColumn("_rank", sf.row_number().over(first))
        .filter(sf.col("_rank") == 1)
        .drop("_rank")
    )
    return apply(
        deduplicated,
        [
            Expectation(
                "transaction_id_present",
                sf.length(sf.col("transaction_id")) > 0,
                "a receipt line with no transaction id cannot be deduplicated by business key, "
                "and CLAUDE.md refuses to invent one",
            ),
            Expectation("qty_positive", sf.col("qty") > 0, "a sale of nothing is not a sale"),
            Expectation(
                "price_positive",
                sf.col("unit_price_cents") > 0,
                "a line at or below zero is a refund or a defect, and neither is revenue",
            ),
            Expectation(
                "line_total_is_the_arithmetic",
                sf.col("line_total_cents") == sf.col("qty") * sf.col("unit_price_cents"),
                "the till's own total disagrees with its own multiplication, so one of the "
                "three columns is wrong and nothing here can say which",
            ),
        ],
        table="sales",
        business_key=SALE_KEY,
    )


def price_displayed(esl_acks: DataFrame) -> tuple[DataFrame, DataFrame]:
    """What the shelf showed, from the acknowledgement and never from the decision.

    `CLAUDE.md`: *"The ESL acknowledgement is a first-class source, not a log. It is the only
    evidence that a price reached the shelf."* An accepted acknowledgement whose displayed price
    differs from the decided one is not a rounding difference — it is the two columns
    contradicting each other about the same event, and it goes to quarantine rather than into a
    table an experiment reads exposure from.
    """
    return apply(
        esl_acks,
        [
            Expectation(
                "displayed_price_positive",
                sf.col("price_displayed_cents") > 0,
                "a label showing nothing is not a price the shopper could have paid",
            ),
            Expectation(
                "accepted_means_displayed_equals_decided",
                (~sf.col("accepted"))
                | (sf.col("price_displayed_cents") == sf.col("price_decided_cents")),
                "the label says it accepted the price and then reports a different one",
            ),
        ],
        table="price_displayed",
        business_key=("store_id", "sku_id", "event_ts"),
    )


def shelf_state(shelf_days: DataFrame, sold: DataFrame) -> tuple[DataFrame, DataFrame]:
    """Whether the shelf emptied, and the last hour it is known to have held stock.

    **Derived from the movements, never copied from the source's own marking.** `CLAUDE.md` puts
    stock-out marking here *"because only here are the inventory movements available"*, and the
    corpus does emit a `stocked_out_from_hour` — which this function deliberately ignores. Silver
    recomputes: a store-day emptied when it **closed at zero**, and the hour it is last known to
    have held stock is the hour of its last sale.

    **`last_sale_hour` is a lower bound on the moment the shelf emptied, and is named as one.**
    The last unit can leave without a sale — it expires, or it is thrown away — so an hour
    derived from sales can only be at or before the truth. `tests/pipelines/test_silver.py`
    measures the gap against the corpus's own marking rather than asserting they are equal, and
    publishes the distribution.
    """
    last_sale = sold.groupBy(
        "store_id", "sku_id", sf.to_date("event_ts").alias("business_date")
    ).agg(
        sf.max(sf.hour("event_ts")).alias("last_sale_hour"),
        sf.sum("qty").alias("units_sold_from_receipts"),
    )
    joined = (
        shelf_days.withColumn("_date", sf.to_date("business_date"))
        .join(
            last_sale,
            (shelf_days["store_id"] == last_sale["store_id"])
            & (shelf_days["sku_id"] == last_sale["sku_id"])
            & (sf.to_date(shelf_days["business_date"]) == last_sale["business_date"]),
            "left",
        )
        .select(
            shelf_days["store_id"],
            shelf_days["sku_id"],
            shelf_days["business_date"],
            shelf_days["delivered_qty"],
            shelf_days["sold_qty"],
            shelf_days["wasted_qty"],
            shelf_days["closing_qty"],
            shelf_days["unit_cost_cents"],
            last_sale["last_sale_hour"],
            last_sale["units_sold_from_receipts"],
        )
        .withColumn("emptied", sf.col("closing_qty") == 0)
    )
    return apply(
        joined,
        [
            Expectation(
                "quantities_are_not_negative",
                (sf.col("delivered_qty") >= 0)
                & (sf.col("sold_qty") >= 0)
                & (sf.col("wasted_qty") >= 0)
                & (sf.col("closing_qty") >= 0),
                "a negative movement is a correction the source has not explained",
            ),
            Expectation(
                "receipts_account_for_the_units_sold",
                sf.coalesce(sf.col("units_sold_from_receipts"), sf.lit(0)) == sf.col("sold_qty"),
                "the day's summary and its own receipts disagree about how much left the shelf, "
                "which is the shape a lost or duplicated event makes",
            ),
        ],
        table="shelf_state",
        business_key=("store_id", "sku_id", "business_date"),
    )


def reference(cost_ledger: DataFrame) -> tuple[DataFrame, DataFrame]:
    """The cost dimension, on **both** of its time axes, from the ERP's successive drops.

    A cost step has two moments and confusing them is the defect `CLAUDE.md` warns about:

    * `effective_from` — when the price the chain pays changes. The ERP's statement.
    * `known_from` — when the ERP first told us, which is the earliest drop carrying the row.

    *"A sale at 14:00 joins to the cost as it was known at 14:00"* needs both: a step effective
    at 09:00 but first exported at 16:00 was **not known** at 14:00, and a margin computed from
    it would be one nobody could have computed on the day. `known_from` exists because
    `pipelines/ingest/bulk.py` stamps every materialised row with the drop's `_exported_at`; a
    single static snapshot would have made this column a constant and the distinction unaskable.
    """
    earliest = cost_ledger.groupBy("sku_id", "effective_from", "unit_cost_cents").agg(
        sf.min("_exported_at").alias("known_from"),
        sf.countDistinct("_source_file").alias("drops_carrying_it"),
    )
    return apply(
        earliest,
        [
            Expectation(
                "cost_positive",
                sf.col("unit_cost_cents") > 0,
                "a cost of nothing makes every margin equal to revenue",
            ),
            Expectation(
                "known_before_or_when_it_took_effect_is_not_required",
                sf.col("known_from").isNotNull(),
                "a row with no drop behind it came from nowhere; the loader stamps every "
                "materialised row and a null here means the column was lost between layers",
            ),
        ],
        table="reference",
        business_key=("sku_id", "effective_from"),
    )


def cost_as_of(reference_table: DataFrame, frame: DataFrame, moment: str) -> DataFrame:
    """Join `frame` to the cost **as it was known at** `moment`. There is no other join here.

    Two conditions, and dropping either one is a different bug: `effective_from <= moment`
    because a future price is not this sale's cost, and `known_from <= moment` because a cost
    the ERP had not yet published could not have been used. The latest surviving step wins, and
    a row with no surviving step keeps a null cost rather than borrowing the nearest one —
    `Chain.cost_as_of` refuses the same case one repository over, and inventing a cost is
    doctrine rule 3.
    """
    candidates = frame.join(
        reference_table.withColumnRenamed("sku_id", "_ref_sku"),
        (frame["sku_id"] == sf.col("_ref_sku"))
        & (sf.col("effective_from") <= sf.col(moment))
        & (sf.col("known_from") <= sf.col(moment)),
        "left",
    )
    latest = Window.partitionBy(*[frame[column] for column in frame.columns]).orderBy(
        sf.col("effective_from").desc_nulls_last(), sf.col("known_from").desc_nulls_last()
    )
    return (
        candidates.withColumn("_rank", sf.row_number().over(latest))
        .filter(sf.col("_rank") == 1)
        .drop("_rank", "_ref_sku", "drops_carrying_it")
        .withColumnRenamed("unit_cost_cents", "unit_cost_as_of")
        .withColumnRenamed("effective_from", "cost_effective_from")
        .withColumnRenamed("known_from", "cost_known_from")
    )
