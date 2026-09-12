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


def decisions(price_decisions: DataFrame) -> tuple[DataFrame, DataFrame]:
    """What the chain decided, before anything was dispatched -- family D's record, at silver.

    `CLAUDE.md`: *"D · the decision record — decisions (immutable, written at decision time)"*.
    The corpus writes that record as the `price_decisions` stream, at the moment the policy
    produced a price and before the label acknowledged anything, and until 2026-09-12 it was
    the one bronze stream nothing read -- `pipelines/silver/__init__.py` said so. The decision
    monitor, which doctrine rule 2 requires, was compiled against `gold.decisions` and drew from
    nothing; `ops/inspect_estate.py` read the warehouse's answer on run 34676694580.

    The shape is the source's, one row per decision. A decision with no positive price is not
    a decision the chain could have dispatched and goes to quarantine; the arm it carries is
    the world's, which is why gold's readout never reads this table -- `experiments.py` says
    which tables may carry an arm and this is not one of them.
    """
    return apply(
        price_decisions,
        [
            Expectation(
                "decided_price_positive",
                sf.col("price_decided_cents") > 0,
                "a decision that prices the item at nothing was never dispatched",
            ),
            Expectation(
                "ladder_step_is_a_rung",
                sf.col("ladder_step") >= 0,
                "a ladder step below the first rung names nothing in the policy",
            ),
        ],
        table="decisions",
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


#: The `product_master` columns the dimension carries. **`name` is deliberately not among
#: them.** It is display text that no metric, no feature and no guardrail reads, and
#: `docs/DECISIONS.md` names `pipelines/` as a route `evals/oversight/` does not yet scan — so a
#: column literally called `name` entering a table on the decision path, ahead of the scan that
#: would police it, is a thing to do deliberately rather than by copying the source's shape.
#: Bronze keeps it, in the source's shape, which is what bronze is for.
PRODUCT_COLUMNS: tuple[str, ...] = (
    "sku_id",
    "category",
    "base_price_cents",
    "shelf_life_days",
    "substitute_of",
)


def _latest_product(product_master: DataFrame) -> DataFrame:
    """One row per sku: the attributes the **latest** drop published, and when it was first seen.

    **The latest drop wins, and that is a retroactive rewrite with no way to avoid it.**
    `CLAUDE.md` warns that joining to the current cost table *"silently rewrites every historical
    margin"*, and the cost ledger escapes it by carrying `effective_from` and `known_from`.
    `product_master` carries neither — `pipelines/ingest/erp.py` says *"`store_master` and
    `product_master` have no time"* — so when a drop changes a product's category there is no
    date to apply the change from, and it applies to all of history. That is the source's
    limitation and it is recorded here rather than papered over: a dimension cannot invent a
    time axis its source does not publish, and doctrine rule 3 forbids inventing one.

    What is kept is the evidence that it moved: `product_known_from` is the first drop that
    carried the sku and `product_drops_carrying_it` is how many did, so a product whose
    attributes changed mid-day is visible as a row seen in several drops rather than as nothing.

    Measured at smoke scale on this corpus: **45 rows, 9 skus, 5 drops each, and 0 skus whose
    category differed across them** — so the tie-break is unexercised by the data and is planted
    in `tests/pipelines/test_silver.py`.
    """
    newest = Window.partitionBy("sku_id").orderBy(sf.col("_exported_at").desc())
    first_seen = product_master.groupBy("sku_id").agg(
        sf.min("_exported_at").alias("product_known_from"),
        sf.countDistinct("_source_file").alias("product_drops_carrying_it"),
    )
    latest = (
        product_master.withColumn("_rank", sf.row_number().over(newest))
        .filter(sf.col("_rank") == 1)
        .select(*PRODUCT_COLUMNS)
    )
    return latest.join(first_seen, on="sku_id", how="inner")


#: The `store_master` columns the store dimension carries: the key, the three the balance
#: contract names, and the two coordinates the interference exclusions need. `town`, `size_band` and
#: `opened_on` are dropped for `PRODUCT_COLUMNS`' reason: nothing on the decision path reads
#: them, and bronze keeps them in the source's shape.
STORE_COLUMNS: tuple[str, ...] = (
    "store_id",
    "store_format",
    "size_index",
    "pricing_zone",
    # **The coordinates, and they are here for one reason.** `inference.yaml` declares
    # `neighbour_radius_m`, and the automatic exclusions moment 1 applies are pairs of
    # stores close enough that treating one contaminates the other. Without a position
    # there are no pairs, and an experiment with no interference exclusions is one that
    # assumed the estate has none.
    "x_m",
    "y_m",
)

#: **The column that must not be here, named so its arrival is a refusal rather than a surprise.**
#: `corpus/world/` declares `arm` on `store_master` and `pipelines/ingest/erp.py` withholds it —
#: *an ERP does not know which stores are in an experiment's control group.* If it ever arrives,
#: the layer that assigns arms would be reading the answer out of its own input, and every
#: balance figure computed downstream would be describing a lottery that had already been run.
WITHHELD_FROM_STORES: tuple[str, ...] = ("arm",)


class WithheldColumnError(ValueError):
    """A column the source is supposed to withhold arrived. Refused rather than dropped.

    Dropping it would be the polite thing and the wrong one: the column's presence means the
    export changed, and a silver build that quietly removed it would leave the export wrong and
    every run after it green.
    """


def stores(store_master: DataFrame) -> tuple[DataFrame, DataFrame]:
    """The store dimension: one row per store, carrying the three declared balance covariates.

    **This table exists because something finally asked for it.** `reference`'s docstring has
    said since the branch that wrote it that *`store_master` is still unread … it enters when
    something asks for it*, and `contracts/design/balance_covariates.yaml` is what asks:
    `store_format`, `size_index` and `pricing_zone` are three of the five covariates an
    assignment is balanced on, and no event stream carries any of them.

    **The latest drop wins, with the same retroactive rewrite `_latest_product` records.**
    `store_master` has no time axis either — `pipelines/ingest/erp.py` says so of both masters —
    so a store that changed pricing zone mid-history changed it for all of history, and the
    evidence that it moved is kept rather than the change being dated.
    """
    if any(column in store_master.columns for column in WITHHELD_FROM_STORES):
        present = [c for c in WITHHELD_FROM_STORES if c in store_master.columns]
        raise WithheldColumnError(
            f"bronze.store_master carries {present}, which `pipelines/ingest/erp.py` withholds "
            "on purpose: an ERP does not know which stores are in an experiment's control "
            "group. A store dimension carrying the arm would hand the assignment engine the "
            "answer, and every balance figure downstream would describe a lottery already run."
        )

    newest = Window.partitionBy("store_id").orderBy(sf.col("_exported_at").desc())
    first_seen = store_master.groupBy("store_id").agg(
        sf.min("_exported_at").alias("store_known_from"),
        sf.countDistinct("_source_file").alias("store_drops_carrying_it"),
    )
    latest = (
        store_master.withColumn("_rank", sf.row_number().over(newest))
        .filter(sf.col("_rank") == 1)
        .select(*STORE_COLUMNS)
    )
    return apply(
        latest.join(first_seen, on="store_id", how="inner"),
        [
            Expectation(
                "size_index_positive",
                sf.col("size_index") > 0,
                "a store with no size has no `store_sqm` covariate, and a covariate measured "
                "as zero is not a missing one — it balances the draw on a number nobody meant",
            ),
            Expectation(
                "pricing_zone_present",
                sf.col("pricing_zone").isNotNull() & (sf.length(sf.col("pricing_zone")) > 0),
                "pricing zone is a stratum as well as a covariate; a store with none would be "
                "drawn into a stratum that does not exist",
            ),
            Expectation(
                "store_format_present",
                sf.col("store_format").isNotNull() & (sf.length(sf.col("store_format")) > 0),
                "store format is a declared categorical covariate and an empty one is a "
                "category of its own that nobody declared",
            ),
        ],
        table="stores",
        business_key=("store_id",),
    )


def reference(cost_ledger: DataFrame, product_master: DataFrame) -> tuple[DataFrame, DataFrame]:
    """The ERP dimension: the cost on **both** of its time axes, and the product on neither.

    A cost step has two moments and confusing them is the defect `CLAUDE.md` warns about:

    * `effective_from` — when the price the chain pays changes. The ERP's statement.
    * `known_from` — when the ERP first told us, which is the earliest drop carrying the row.

    *"A sale at 14:00 joins to the cost as it was known at 14:00"* needs both: a step effective
    at 09:00 but first exported at 16:00 was **not known** at 14:00, and a margin computed from
    it would be one nobody could have computed on the day. `known_from` exists because
    `pipelines/ingest/bulk.py` stamps every materialised row with the drop's `_exported_at`; a
    single static snapshot would have made this column a constant and the distinction unaskable.

    Half of this dimension is as-of and half of it is not, which is the limit to read first
    ------------------------------------------------------------------------------------------
    **`product_master` has no time axis**, so a product's `category` is a fact with a key and no
    date, and it is resolved by **key** rather than as-of. `cost_as_of` carries that split, in
    two joins rather than one, and `_latest_product` carries what the missing axis costs.

    So *as-of queryable* is true of the cost columns and false of the product columns, and the
    phrase is not allowed to travel unqualified now that both are in one table. What one table
    buys is that there is one ERP dimension rather than two, which is what `CLAUDE.md`
    describes; what it costs is this paragraph.

    Why the product dimension is here at all
    ----------------------------------------
    **Every metric contract declares `grain: [store_id, iso_week, category]`**, and `category` is
    a `product_master` column. Until this branch silver read four of the seven tables `bulk.load`
    writes to bronze and none of them carried it, so no gold table could be built at the grain
    its own contract declares. `CLAUDE.md` said `reference` *"collapses six bronze tables into
    one as-of queryable dimension"* and this function collapsed one. The gap was invisible for
    exactly as long as nothing downstream of silver existed to need it.

    **`store_master` is still unread**, and is named here rather than left to be discovered: no
    metric's grain needs a store attribute and `store_id` passes through the events unchanged.
    It enters when something asks for it.

    The join has two failure directions and only one of them is a refusal
    --------------------------------------------------------------------
    A **cost step naming a product silver does not have** is quarantined: it prices something
    that is not in the catalogue, and letting it through would put a row in the dimension with a
    cost and no category, which is a null in every metric's grain.

    A **product with no cost step is kept**, with null cost columns. That is not a defect — it is
    the same state as a sale before its product's first published cost, and doctrine rule 3 says
    a missing cost is a null rather than a borrowed neighbour.

    Measured at smoke scale on this corpus: **9 products, 9 skus with a cost step, 0 in either
    direction.** Both branches are unexercised by the data, so both are planted in
    `tests/pipelines/test_silver.py` rather than asserted from a clean run.
    """
    costs, costs_bad = apply(
        cost_ledger.groupBy("sku_id", "effective_from", "unit_cost_cents").agg(
            sf.min("_exported_at").alias("known_from"),
            sf.countDistinct("_source_file").alias("drops_carrying_it"),
        ),
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
    products, products_bad = apply(
        _latest_product(product_master),
        [
            Expectation(
                "category_present",
                sf.length(sf.col("category")) > 0,
                "every metric contract's grain is (store_id, iso_week, category), so a product "
                "with no category makes a metric row nobody can attribute",
            ),
        ],
        table="reference",
        business_key=("sku_id",),
    )
    joined = products.join(
        costs.withColumnRenamed("sku_id", "_cost_sku"),
        products["sku_id"] == sf.col("_cost_sku"),
        "full_outer",
    )
    kept, orphaned = apply(
        joined,
        [
            Expectation(
                "cost_step_names_a_known_product",
                sf.col("sku_id").isNotNull(),
                "a cost step prices a sku that is not in the product master, so it would enter "
                "the dimension with a cost and no category — a null in every metric's grain",
            ),
        ],
        table="reference",
        business_key=("_cost_sku", "effective_from"),
    )
    return kept.drop("_cost_sku"), costs_bad.union(products_bad).union(orphaned)


#: The cost columns, which are the ones with a time axis and the only ones resolved as-of.
COST_COLUMNS: tuple[str, ...] = ("sku_id", "effective_from", "unit_cost_cents", "known_from")

#: The product columns, which have no time axis and are therefore resolved by key. See
#: `reference`: half of that dimension is as-of and half of it is not.
UNTIMED_COLUMNS: tuple[str, ...] = tuple(c for c in PRODUCT_COLUMNS if c != "sku_id")


def cost_as_of(reference_table: DataFrame, frame: DataFrame, moment: str) -> DataFrame:
    """Join `frame` to the ERP dimension: the cost **as it was known at** `moment`, the product
    by its key.

    Two conditions on the cost, and dropping either one is a different bug: `effective_from <=
    moment` because a future price is not this sale's cost, and `known_from <= moment` because a
    cost the ERP had not yet published could not have been used. The latest surviving step wins,
    and a row with no surviving step keeps a null cost rather than borrowing the nearest one —
    `Chain.cost_as_of` refuses the same case one repository over, and inventing a cost is
    doctrine rule 3.

    **Two joins, and the second one is not an optimisation.** The product columns carry no time
    axis, so they are resolved by key before the as-of pick runs. Resolving them through the
    as-of join instead would look identical on almost every row — a product's category is the
    same on every one of its cost steps, so whichever step wins carries the right one — and would
    be wrong on exactly the rows where **no step survives**: those keep a null cost, correctly,
    and would take a null category with it.

    That is not a corner. Measured on this corpus at smoke scale: **1,418 of 35,695 receipt
    lines have no cost known at the moment of the sale**, because the ERP's first drop lands on
    the first trading day and the corpus sells before it. Through one join those 1,418 lines
    would enter gold with a null in the `category` position of every metric's declared grain,
    and the number would still be a number.
    """
    attributes = reference_table.select("sku_id", *UNTIMED_COLUMNS).distinct()
    identified = frame.join(
        attributes.withColumnRenamed("sku_id", "_attr_sku"),
        frame["sku_id"] == sf.col("_attr_sku"),
        "left",
    ).drop("_attr_sku")
    steps = reference_table.select(*COST_COLUMNS).filter(sf.col("effective_from").isNotNull())
    candidates = identified.join(
        steps.withColumnRenamed("sku_id", "_ref_sku"),
        (identified["sku_id"] == sf.col("_ref_sku"))
        & (sf.col("effective_from") <= sf.col(moment))
        & (sf.col("known_from") <= sf.col(moment)),
        "left",
    )
    latest = Window.partitionBy(*[identified[column] for column in identified.columns]).orderBy(
        sf.col("effective_from").desc_nulls_last(), sf.col("known_from").desc_nulls_last()
    )
    return (
        candidates.withColumn("_rank", sf.row_number().over(latest))
        .filter(sf.col("_rank") == 1)
        .drop("_rank", "_ref_sku")
        .withColumnRenamed("unit_cost_cents", "unit_cost_as_of")
        .withColumnRenamed("effective_from", "cost_effective_from")
        .withColumnRenamed("known_from", "cost_known_from")
    )
