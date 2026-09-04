"""The promotion gates, and the named human who is then allowed to decide.

`T014`'s stopping condition is *the promotion gate refuses a planted bad model for a stated
reason*, and `closes` says why: **a gate that has never refused anything has not been tested.**
Every gate here is planted against in `tests/pipelines/test_ml_promotion.py` — a model made
optimistic, one made noisy, one wrong in two segments that cancel, one fitted on too little — and
each plant names the gate it must be refused by. A gate that refuses the wrong plant is as broken
as one that refuses nothing.

Not a refusal in the closed vocabulary, and why
------------------------------------------------
`contracts/vocabularies/reason_codes.yaml`: *"Three moments, because the system refuses three
different things"* — `at_decision` a price, `at_design` an experiment, `at_readout` a number. And
`holdout.core.guardrails.certificate.Refusal` says where such a refusal travels: *"to the decision
record, to the decision monitor's refusal table, and — at the same size as an uplift — to the
experiment readout."*

**A refused model goes to none of those three.** Nobody asked this pipeline for a price, a design
or a number; claim 1 counts decision refusals and claim 6 counts design refusals, and no claim
counts a refused model. So a `GateResult` is not a `Refusal`, carries no `RefusalCode`, and is
never summed with one. It refuses the way `make check` refuses — a named check with a stable id
and a figure — and the ids here are stable for exactly the reason an eval's `Check.id` is: a test
names them.

**The criterion, so the next reader has a test rather than this paragraph:** a refusal belongs in
the closed vocabulary when it is *a thing the system was asked for and did not produce*, and it is
recorded on a decision record, the monitor or a readout. If a claim ever asks how often the system
declines to act across both populations, a fourth section becomes right, and it is a contract
change with a restatement chain.

Nothing approves itself
------------------------
Doctrine rule 5, and it is a type rather than a paragraph. `Promotion` cannot be constructed
without an `approved_by`, `approved_by` cannot be empty, and it must name a human in the same
`human:<name>` shape the design form's `filled_by` uses — so *approved by the pipeline* cannot be
spelled. **Passing every gate grants nothing**: `Assessment.passed` says a human may now be
asked, and the asking is somebody else's job.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from statistics import NormalDist
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from holdout.contracts.model import TrainingSettings
    from pipelines.ml.calibration import Calibration
    from pipelines.ml.model import DemandModel

#: The one shape an approver may be written in. `human:` and a name, exactly as the design form's
#: `filled_by` spells it — so a reader who knows one knows the other, and so `agent:` and
#: `policy:`, which are legitimate there, are unspellable here.
APPROVER = re.compile(r"^human:[A-Za-z][A-Za-z .'\-]{1,62}$")


def segment_limit(judged: int, family_rate: Decimal) -> Decimal:
    """How many of its own standard errors a segment may miss by, given how many are judged.

    **Derived, never declared.** `contracts/ml/training.yaml` declares the *family-wise false
    alarm rate* — the chance this gate refuses a well-calibrated model on a run — and this turns
    it into a per-segment limit by Bonferroni: each of `judged` segments is tested two-sided at
    `family_rate / judged`.

    The reason it is not a fixed multiple is a measurement, and it is in that contract's own note.
    A flat three standard errors applied to the **worst of twenty-one** segments refuses a
    well-calibrated model on **5.52% of runs**, and it degrades as the corpus grows — 12.6% at 50
    segments, 41.8% at 200, 93.3% at 1,000. **A fixed multiple is a threshold whose meaning
    depends on a population size nothing enumerates**, which is this repository's coverage rule
    wearing a number instead of a verb.

    `statistics.NormalDist` is the standard library, so this needs no dependency — and unlike
    `holdout.core`, which writes its quantiles out in `inference.yaml` because it may not import a
    statistics module, `pipelines/` is under no such rule.
    """
    if judged < 1:
        raise PromotionError(
            "a per-segment limit over zero judged segments. P4 is what refuses that case, and "
            "reaching here means it did not run first."
        )
    per_segment = float(family_rate) / judged
    return Decimal(str(NormalDist().inv_cdf(1 - per_segment / 2))).quantize(Decimal("0.01"))


class PromotionError(ValueError):
    """A promotion that could not be recorded, or an approver that is not a person."""


@dataclass(frozen=True, slots=True)
class GateResult:
    """One gate's verdict, its figure, and the threshold it was judged against.

    The threshold travels with the result rather than being looked up by whoever prints it. A
    verdict without its threshold is unreadable a month later, and a reader who has to go and
    find the number is a reader who will assume it.
    """

    id: str
    """Stable. `tests/pipelines/test_ml_promotion.py` names these, and a rename breaks it."""

    question: str
    passed: bool
    figure: str
    threshold: str
    detail: str = ""

    def __str__(self) -> str:
        mark = "pass" if self.passed else "REFUSED"
        return f"{self.id:34} {mark:8} {self.figure}  (limit {self.threshold})"


@dataclass(frozen=True, slots=True)
class Assessment:
    """Every gate's verdict over one model. Grants nothing on its own.

    **`passed` means a human may now be asked**, not that anything is promoted. That distinction
    is doctrine rule 5 and it is why `Promotion` is a separate type that cannot be built from this
    one alone.
    """

    model_digest: str
    gates: tuple[GateResult, ...]

    @property
    def passed(self) -> bool:
        return all(gate.passed for gate in self.gates)

    @property
    def refusals(self) -> tuple[GateResult, ...]:
        """Every gate that refused, in declaration order. Plural on purpose.

        A model can fail three gates at once and reporting only the first would send whoever fixes
        it back for a second round it did not need. `evals/report.py` prints every check for the
        same reason.
        """
        return tuple(gate for gate in self.gates if not gate.passed)

    def __str__(self) -> str:
        head = f"model {self.model_digest[:12]}  {len(self.refusals)} of {len(self.gates)} refused"
        return "\n".join([head, *(str(gate) for gate in self.gates)])


@dataclass(frozen=True, slots=True)
class Promotion:
    """A model, the assessment it passed, and the person who accepted it.

    Doctrine rule 5 as a type: there is no way to construct this without naming a human, and no
    way to name anything but a human. A pipeline that wanted to promote its own output would have
    to write `human:` and then a name, which is a forgery rather than an oversight — and the
    difference between the two is the whole point of making it a type instead of a rule.
    """

    model_digest: str
    assessment: Assessment
    approved_by: str
    approved_at: datetime
    note: str

    def __post_init__(self) -> None:
        if not APPROVER.match(self.approved_by):
            raise PromotionError(
                f"{self.approved_by!r} is not a named human. An approver is written "
                "`human:<name>`, the same shape the design form's `filled_by` uses, so that "
                "`agent:` and `policy:` — legitimate there — cannot be written here. Doctrine "
                "rule 5: no model, no pipeline and no agent may approve a promotion."
            )
        if not self.assessment.passed:
            raise PromotionError(
                f"{len(self.assessment.refusals)} gate(s) refused this model: "
                f"{[gate.id for gate in self.assessment.refusals]}. An approver may not override "
                "a gate — an exception is a separate object with an expiry, and doctrine rule 6 "
                "says it returns."
            )
        if self.assessment.model_digest != self.model_digest:
            raise PromotionError(
                f"the assessment is of model {self.assessment.model_digest[:12]} and this "
                f"promotion names {self.model_digest[:12]}. A promotion carrying somebody "
                "else's assessment is the failure this field exists to make impossible."
            )
        if not self.note.strip():
            raise PromotionError(
                "an approval with no note is a signature with no reason. What was weighed is "
                "the part a later reader needs and the part nobody can reconstruct."
            )


def _pct(value: Fraction) -> str:
    return f"{float(value):+.2f}%"


def assess(model: DemandModel, calibration: Calibration, settings: TrainingSettings) -> Assessment:
    """Every gate, in order, over one fitted model and one evaluation half.

    Ordered calibration first, because it is the gate `CLAUDE.md` puts above RMSE and a reader
    scanning the output should meet it first. Every gate runs regardless of what came before —
    short-circuiting would report one defect on a model that has three.
    """
    gates: list[GateResult] = []

    tolerance = Fraction(settings.calibration_tolerance_pct)
    error = calibration.error_pct
    gates.append(
        GateResult(
            id="P1.calibrated-in-total",
            question=(
                "Over the evaluation half, does total predicted demand sit within the declared "
                "tolerance of total observed demand?"
            ),
            passed=abs(error) <= tolerance,
            figure=f"{_pct(error)} on {calibration.rows:,} row(s)",
            threshold=f"±{settings.calibration_tolerance_pct}%",
            detail=(
                ""
                if abs(error) <= tolerance
                else "a uniform bias passes every guardrail — the envelope is a per-price check "
                "and this is the only gate that can see a model wrong by the same share "
                "everywhere"
            ),
        )
    )

    share = calibration.rmse_share_of_baseline
    ceiling = Decimal(settings.rmse_share_of_baseline)
    gates.append(
        GateResult(
            id="P2.better-than-doing-nothing",
            question=(
                "Is the model's error a small enough share of what predicting the grand rate "
                "everywhere would have scored?"
            ),
            passed=share <= ceiling,
            figure=(
                f"{share} of baseline ({calibration.rmse} against "
                f"{calibration.baseline_rmse} unit(s))"
            ),
            threshold=f"≤{ceiling} of baseline",
            detail=(
                ""
                if share <= ceiling
                else "the do-nothing baseline is perfectly calibrated by construction, so P1 "
                "cannot refuse it and this is the gate that must"
            ),
        )
    )

    judged = calibration.judged(settings.min_segment_days)
    # **Computed before the gate, from the population the gate will judge.** A limit read from a
    # contract would be a fixed multiple, which is the defect this replaced.
    limit = (
        segment_limit(len(judged), settings.segment_family_false_alarm_rate)
        if judged
        else Decimal(0)
    )
    breached = [segment for segment in judged if segment.sigmas > limit]
    gates.append(
        GateResult(
            id="P3.calibrated-in-every-judged-segment",
            question=(
                "Is every segment carrying at least the declared number of evaluation days "
                "calibrated within the per-segment tolerance?"
            ),
            passed=not breached,
            figure=(
                f"{len(judged)} judged, {len(breached)} outside "
                f"(worst {max((s.sigmas for s in judged), default=Decimal(0))} sd)"
            ),
            threshold=(
                f"<={limit} standard error(s), from a family alarm rate of "
                f"{settings.segment_family_false_alarm_rate} over {len(judged)} segment(s)"
            ),
            detail=(
                ""
                if not breached
                else " · ".join(
                    f"{segment.segment[0]}/wd{segment.segment[1]}: {_pct(segment.error_pct)} "
                    f"= {segment.sigmas} sd over {segment.days} day(s)"
                    for segment in breached[:5]
                )
            ),
        )
    )

    gates.append(
        GateResult(
            id="P4.judged-on-a-population-that-exists",
            question=("Did at least one segment carry enough evaluation days to be judged at all?"),
            passed=bool(judged),
            figure=(
                f"{len(judged)} judged, "
                f"{len(calibration.unjudged(settings.min_segment_days))} too small"
            ),
            threshold=f"≥1 segment of ≥{settings.min_segment_days} day(s)",
            detail=(
                ""
                if judged
                else "P3 passes over an empty set of segments, so without this gate a model "
                "evaluated on a corpus too thin to judge would be indistinguishable from a "
                "model that passed"
            ),
        )
    )

    gates.append(
        GateResult(
            id="P5.fitted-on-enough-history",
            question="Was the model fitted on at least the declared number of business dates?",
            passed=model.fitted_on_days >= settings.min_training_days,
            figure=f"{model.fitted_on_days} date(s)",
            threshold=f"≥{settings.min_training_days} date(s)",
            detail=(
                ""
                if model.fitted_on_days >= settings.min_training_days
                else "the split refuses this too, and it is checked twice on purpose: a model "
                "can arrive here from somewhere that is not this pipeline's own split"
            ),
        )
    )

    return Assessment(model_digest=model.digest, gates=tuple(gates))
