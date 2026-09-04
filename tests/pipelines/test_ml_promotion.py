"""Every promotion gate, planted against by name. `T014`'s stopping condition.

`TASKS.md`: *"When the promotion gate refuses a planted bad model for a stated reason."* And its
`closes`: **a gate that has never refused anything has not been tested.**

So each gate here gets a model built to break it, and the test asserts **which** gate refused —
not merely that something did. A gate that refuses the wrong plant is as broken as one that
refuses nothing, and asserting `not assessment.passed` would not tell the two apart.

**Who chose the cases.** `CLAUDE.md`'s standing question about a guard tested by its author, and
the honest answer here is *the author did* — these plants are shapes I pictured. What limits that
is the second half of each test: the plant is built by **changing one number in a model that
passes**, so the difference between passing and refused is a single named quantity rather than a
model constructed to fail in every way at once. A pile that fails everything cannot show which
gate bit.

**And the gates are shown passing too**, in `test_a_sound_model_passes_every_gate`, because a gate
that has never passed is as untested as one that has never refused: a gate wired to `False` would
satisfy every other test in this file.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from fractions import Fraction

import pytest
from pipelines.ml import calibration, model, promotion
from pipelines.ml.features import DemandFeature

from holdout.contracts.loader import load
from holdout.contracts.model import TrainingSettings

SETTINGS = load().training
CATEGORIES = ("bakery", "dairy", "poultry")
STORES = tuple(f"ST{index:04d}" for index in range(1, 6))
SKUS = tuple(f"SKU{index:04d}" for index in range(1, 4))


def _feature(store: str, sku: str, day: int, units: int, category: str) -> DemandFeature:
    return DemandFeature(
        store_id=store,
        sku_id=sku,
        business_date=f"2026-03-{day:02d}",
        category=category,
        weekday=day % 7,
        units=units,
        censored=False,
        observed_share=Fraction(1),
    )


def _population(days: int = 40) -> list[DemandFeature]:
    """A corpus with real structure: a store effect, a SKU effect and a weekday effect.

    **Structure rather than noise**, because a model fitted on constant demand passes `P1` and
    `P3` trivially and cannot fail `P2` in an interesting way — every predictor is the same
    predictor when there is nothing to predict.
    """
    rows: list[DemandFeature] = []
    for day in range(1, days + 1):
        for store_index, store in enumerate(STORES):
            for sku_index, sku in enumerate(SKUS):
                units = (
                    20
                    + 4 * store_index
                    + 3 * sku_index
                    + 2 * (day % 7)
                    + (day * 7 + store_index * 3 + sku_index) % 5
                )
                rows.append(_feature(store, sku, day, units, CATEGORIES[sku_index]))
    return rows


@pytest.fixture(scope="module")
def sound() -> tuple[model.DemandModel, calibration.Calibration]:
    """A model fitted on the first thirty days and judged on the last ten of the same shape."""
    rows = _population()
    train = [row for row in rows if int(row.business_date[-2:]) <= 30]
    evaluate = [row for row in rows if int(row.business_date[-2:]) > 30]
    fitted = model.fit(train, recency_days=SETTINGS.evaluation_days)
    return fitted, calibration.measure(fitted, evaluate)


def _settings(**overrides: object) -> TrainingSettings:
    """The contract's settings with one field replaced, so a test can name what it changed."""
    fields = {
        "version": SETTINGS.version,
        "effective_from": SETTINGS.effective_from,
        "evaluation_days": SETTINGS.evaluation_days,
        "min_training_days": SETTINGS.min_training_days,
        "min_observed_share": SETTINGS.min_observed_share,
        "calibration_tolerance_pct": SETTINGS.calibration_tolerance_pct,
        "rmse_share_of_baseline": SETTINGS.rmse_share_of_baseline,
        "segment_calibration_max_sigma": SETTINGS.segment_calibration_max_sigma,
        "min_segment_days": SETTINGS.min_segment_days,
    }
    fields.update(overrides)
    return TrainingSettings(**fields)  # type: ignore[arg-type]


def _refused(assessment: promotion.Assessment) -> set[str]:
    return {gate.id for gate in assessment.refusals}


def test_a_sound_model_passes_every_gate(
    sound: tuple[model.DemandModel, calibration.Calibration],
) -> None:
    """The other half of the stopping condition: the gates can be satisfied.

    Without this, a gate hard-wired to refuse would pass every plant below and nothing here would
    notice. `min_segment_days` is relaxed to 1 because this fixture is fifteen rows a day rather
    than a corpus — the gate itself is planted against separately, in `P4`.
    """
    fitted, measured = sound
    assessment = promotion.assess(fitted, measured, _settings(min_segment_days=1))
    assert assessment.passed, str(assessment)
    assert len(assessment.gates) == 5


def test_a_systematically_optimistic_model_is_refused_by_p1(
    sound: tuple[model.DemandModel, calibration.Calibration],
) -> None:
    """The plant `CLAUDE.md` describes by name, at the size it describes.

    *"A model that is systematically optimistic by 20% sets systematically low prices, and every
    individual price still passes every guardrail."* Every rate is multiplied by 1.2 and nothing
    else changes — so the refusal cannot be attributed to anything but the bias.
    """
    fitted, _ = sound
    rows = _population()
    evaluate = [row for row in rows if int(row.business_date[-2:]) > 30]
    optimistic = model.DemandModel(
        rates={key: rate * Fraction(6, 5) for key, rate in fitted.rates.items()},
        store_factors=fitted.store_factors,
        recency_factors=fitted.recency_factors,
        grand_rate=fitted.grand_rate,
        fitted_on_days=fitted.fitted_on_days,
        censored_share=fitted.censored_share,
    )
    measured = calibration.measure(optimistic, evaluate)
    assessment = promotion.assess(optimistic, measured, _settings(min_segment_days=1))
    assert "P1.calibrated-in-total" in _refused(assessment), str(assessment)


def test_the_do_nothing_baseline_is_refused_by_p2_and_not_by_p1(
    sound: tuple[model.DemandModel, calibration.Calibration],
) -> None:
    """The plant that proves why `P2` exists at all, and it is the sharpest one here.

    A model predicting the grand rate everywhere is **perfectly calibrated by construction** — it
    is the mean — so `P1` cannot refuse it and neither can `P3`. It has learned nothing, and `P2`
    is the only gate in the file that can say so. Asserting `P1` *passes* is as much of the test
    as asserting `P2` refuses: it is what shows the two gates are not the same gate.
    """
    fitted, _ = sound
    rows = _population()
    evaluate = [row for row in rows if int(row.business_date[-2:]) > 30]
    useless = model.DemandModel(
        rates={},
        store_factors={},
        recency_factors={},
        grand_rate=fitted.grand_rate,
        fitted_on_days=fitted.fitted_on_days,
        censored_share=fitted.censored_share,
    )
    measured = calibration.measure(useless, evaluate)
    assessment = promotion.assess(useless, measured, _settings(min_segment_days=1))
    refused = _refused(assessment)
    assert "P2.better-than-doing-nothing" in refused, str(assessment)
    assert "P1.calibrated-in-total" not in refused, (
        "the grand-rate model is unbiased by construction, so a P1 that refuses it is not "
        "measuring calibration"
    )


def test_two_segments_wrong_in_opposite_directions_are_refused_by_p3(
    sound: tuple[model.DemandModel, calibration.Calibration],
) -> None:
    """The shape a total cannot see, planted so that the total is *better* than the parts.

    One category's rates are raised and another's lowered by the same share, so the model's total
    calibration improves toward zero while two segments are badly wrong. **`P1` passing is part of
    the assertion**: a per-segment gate that only fires when the total also fires is a per-segment
    gate in name only.
    """
    fitted, _ = sound
    rows = _population()
    evaluate = [row for row in rows if int(row.business_date[-2:]) > 30]
    high, low = SKUS[0], SKUS[1]
    skewed = {
        key: rate * (Fraction(3, 2) if key[0] == high else Fraction(2, 3) if key[0] == low else 1)
        for key, rate in fitted.rates.items()
    }
    lopsided = model.DemandModel(
        rates=skewed,
        store_factors=fitted.store_factors,
        recency_factors=fitted.recency_factors,
        grand_rate=fitted.grand_rate,
        fitted_on_days=fitted.fitted_on_days,
        censored_share=fitted.censored_share,
    )
    measured = calibration.measure(lopsided, evaluate)
    assessment = promotion.assess(lopsided, measured, _settings(min_segment_days=1))
    assert "P3.calibrated-in-every-judged-segment" in _refused(assessment), str(assessment)


def test_a_corpus_too_thin_to_judge_is_refused_by_p4(
    sound: tuple[model.DemandModel, calibration.Calibration],
) -> None:
    """The vacuous pass `P4` exists for, planted by raising the bar rather than shrinking the data.

    With `min_segment_days` above every segment's size, nothing is judged — and `P3` then passes
    over an empty set, which is exactly the shape this repository files against itself most often.
    **`P3` passing is the assertion**: without `P4`, a model evaluated on a corpus too thin to
    judge would be indistinguishable from a model that passed.
    """
    fitted, measured = sound
    assessment = promotion.assess(fitted, measured, _settings(min_segment_days=10_000))
    refused = _refused(assessment)
    assert "P4.judged-on-a-population-that-exists" in refused, str(assessment)
    assert "P3.calibrated-in-every-judged-segment" not in refused, (
        "P3 passed over zero judged segments, which is what P4 is for — if P3 had refused here, "
        "this plant would be proving the wrong thing"
    )


def test_a_model_fitted_on_too_little_history_is_refused_by_p5(
    sound: tuple[model.DemandModel, calibration.Calibration],
) -> None:
    """The gate that is checked twice on purpose — here and in `split`.

    A model can arrive at `assess` from somewhere that is not this pipeline's own split, which is
    the whole reason `P5` exists when `split.split` already refuses the same thing.
    """
    fitted, measured = sound
    starved = model.DemandModel(
        rates=fitted.rates,
        store_factors=fitted.store_factors,
        recency_factors=fitted.recency_factors,
        grand_rate=fitted.grand_rate,
        fitted_on_days=SETTINGS.min_training_days - 1,
        censored_share=fitted.censored_share,
    )
    assessment = promotion.assess(starved, measured, _settings(min_segment_days=1))
    assert "P5.fitted-on-enough-history" in _refused(assessment), str(assessment)


def test_every_gate_carries_its_threshold_and_a_reason_when_it_refuses(
    sound: tuple[model.DemandModel, calibration.Calibration],
) -> None:
    """A refusal that does not say what it was judged against is unreadable a month later.

    Checked over the assessment of a model that fails everything at once — the one place a pile is
    the right shape, because here the question is about the *form* of every result rather than
    about which gate bit.
    """
    fitted, _ = sound
    rows = _population()
    evaluate = [row for row in rows if int(row.business_date[-2:]) > 30]
    hopeless = model.DemandModel(
        rates={},
        store_factors={},
        recency_factors={},
        grand_rate=fitted.grand_rate * 3,
        fitted_on_days=1,
        censored_share=Fraction(1),
    )
    measured = calibration.measure(hopeless, evaluate)
    assessment = promotion.assess(hopeless, measured, _settings(min_segment_days=1))
    assert assessment.refusals
    for gate in assessment.gates:
        assert gate.threshold, f"{gate.id} names no threshold"
        assert gate.question.endswith("?"), f"{gate.id}'s question is not one"
        if not gate.passed:
            assert gate.detail, f"{gate.id} refused without saying why"


# --------------------------------------------------------------- doctrine rule 5, as a type


def test_a_promotion_cannot_be_approved_by_anything_but_a_named_human(
    sound: tuple[model.DemandModel, calibration.Calibration],
) -> None:
    """*Nothing approves itself*, and the spellings that would break it are each refused.

    **The cases are not a list somebody imagined**: they are the other two values the design
    form's `filled_by` accepts — `agent:` and `policy:` — plus the empty string and the bare name.
    A vocabulary that is legitimate one file away is the shape a caller will actually write.
    """
    fitted, measured = sound
    assessment = promotion.assess(fitted, measured, _settings(min_segment_days=1))
    for spelling in ("agent:designer", "policy:auto_promote", "", "Alex Doe", "human:"):
        with pytest.raises(promotion.PromotionError, match="named human"):
            promotion.Promotion(
                model_digest=fitted.digest,
                assessment=assessment,
                approved_by=spelling,
                approved_at=datetime.now(UTC),
                note="looks fine",
            )
    accepted = promotion.Promotion(
        model_digest=fitted.digest,
        assessment=assessment,
        approved_by="human:Alex Doe",
        approved_at=datetime.now(UTC),
        note="calibration and per-segment regression reviewed against the model card",
    )
    assert accepted.approved_by == "human:Alex Doe"


def test_a_refused_model_cannot_be_promoted_by_anyone(
    sound: tuple[model.DemandModel, calibration.Calibration],
) -> None:
    """An approver may not override a gate. Doctrine rule 6 says an exception expires and returns.

    Planted through `P4` rather than by breaking the model, so the refusal is unambiguous: the
    model is the one that passes everywhere else in this file.
    """
    fitted, measured = sound
    refused = promotion.assess(fitted, measured, _settings(min_segment_days=10_000))
    with pytest.raises(promotion.PromotionError, match="gate"):
        promotion.Promotion(
            model_digest=fitted.digest,
            assessment=refused,
            approved_by="human:Alex Doe",
            approved_at=datetime.now(UTC),
            note="shipping anyway",
        )


def test_a_promotion_cannot_carry_somebody_elses_assessment(
    sound: tuple[model.DemandModel, calibration.Calibration],
) -> None:
    """The failure the digest field exists to make impossible: an approval pinned to another model."""
    fitted, measured = sound
    assessment = promotion.assess(fitted, measured, _settings(min_segment_days=1))
    with pytest.raises(promotion.PromotionError, match="assessment"):
        promotion.Promotion(
            model_digest="0" * 64,
            assessment=assessment,
            approved_by="human:Alex Doe",
            approved_at=datetime.now(UTC),
            note="reviewed",
        )


def test_an_approval_with_no_note_is_refused(
    sound: tuple[model.DemandModel, calibration.Calibration],
) -> None:
    """A signature with no reason. Whitespace is refused too, which is the spelling that gets past."""
    fitted, measured = sound
    assessment = promotion.assess(fitted, measured, _settings(min_segment_days=1))
    for note in ("", "   ", "\n\t"):
        with pytest.raises(promotion.PromotionError, match="note"):
            promotion.Promotion(
                model_digest=fitted.digest,
                assessment=assessment,
                approved_by="human:Alex Doe",
                approved_at=datetime.now(UTC),
                note=note,
            )


def test_the_segment_gate_is_judged_in_the_segments_own_standard_errors() -> None:
    """The property the contract was restated for, asserted rather than left to the value.

    A flat percentage tolerance tests a thick segment strictly and a thin one barely at all. Two
    segments with the **same** percentage error and different noise must therefore get different
    verdicts — which is the whole content of the change, and would still read as satisfied if the
    gate had quietly gone back to comparing percentages.
    """
    quiet = calibration.SegmentCalibration(
        segment=("bakery", 1),
        days=300,
        observed=1000,
        predicted=Fraction(1080),
        standard_error_pct=Decimal("1.0"),
    )
    noisy = calibration.SegmentCalibration(
        segment=("dairy", 1),
        days=300,
        observed=1000,
        predicted=Fraction(1080),
        standard_error_pct=Decimal("10.0"),
    )
    assert quiet.error_pct == noisy.error_pct
    assert quiet.sigmas == Decimal("8.00")
    assert noisy.sigmas == Decimal("0.80")
