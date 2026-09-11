"""The join: a world, the context the agent was shown, the recording, and the forms to assess.

The only module in this eval that imports both sides — the harness that makes worlds and the
engine that judges designs — so the join can be read as one thing. Three columns, kept sharp:

| | |
|---|---|
| **observed** | the recording: every outcome file, the manifest, both fingerprints. From the model, through `holdout.agent.record`, on a day the manifest names |
| **derived** | the context the agent was shown, rebuilt from the world fixture on every run so `D1` can compare what it was shown against what it would be shown now; the pre-period per metric, from the harness ledger; the forms, from each proposal plus the two fields the agent never fills |
| **swept** | nothing here is drawn at random. The world seed, the lottery seed, the max duration and the decision rule are declared constants below, so a red run reproduces exactly |

The two fields the agent never fills are supplied here, once, for every proposal alike: the
same `max_duration` and the same `decision_rule`. That is the human's half of the form, and
supplying one value to every design is what keeps the comparison about the seven fields the
model chose. A per-question duration would be this eval choosing how hard each refusal is.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from corpus.world import scale as scales

from evals.uplift import design as design_module
from evals.uplift import harness
from evals.uplift.outcomes import Ledger, Week
from holdout.agent.context import PrePeriod as ShownPrePeriod
from holdout.agent.context import Roster, enumerated
from holdout.agent.proposal import ProposedDesign
from holdout.agent.propose import parse, prompt_fingerprint
from holdout.agent.record import MANIFEST, digest_of
from holdout.agent.registry import fingerprint
from holdout.contracts.loader import load
from holdout.contracts.model import ContractSet
from holdout.core.design.form import DecisionRule, DesignForm, MaxDuration

HERE = Path(__file__).resolve().parent
QUESTIONS = HERE / "questions.yaml"
RECORDINGS = HERE / "recordings"

#: The world every question is asked against. W1 is the null world: the true effect is zero, so
#: a refused design run anyway that reports a significant effect is a false positive the
#: refusal prevented. K on other worlds is a later stage and is named in the README.
WORLD = "W1"
WORLD_SEED = "design-0"
LOTTERY_SEED = "design-lottery-0"
SCALE = scales.HARNESS

#: The human's half of every form. `weeks` is the comparison window the harness world carries;
#: a design that needs more than the world has cannot be run anyway, so it is refused as
#: `UNDERPOWERED_FOR_DURATION` rather than run against weeks that do not exist.
MAX_DURATION = MaxDuration(weeks=design_module.PERIOD_WEEKS)
DECISION_RULE = DecisionRule(
    if_significant="adopt the treatment policy chain-wide from the next pricing cycle",
    if_not_significant="keep the current ladder and close the question for two quarters",
    if_refused="redesign before running; a refused design is not run in a smaller form",
)

#: The metric the harness ledger was built for, and the second one it can compute. The third
#: metric in the contract, `units_sold_per_store_week`, has no ledger column; a design naming
#: it is `ungraded` with that reason, never assessed against another metric's variance.
MARGIN = harness.METRIC_ID
WASTE = "waste_value_per_store_week"


@dataclass(frozen=True, slots=True)
class World:
    """One built world and the pre-period of every metric it can measure."""

    fixture: harness.WorldFixture
    pre_by_metric: dict[str, design_module.PrePeriod]
    categories: tuple[str, ...]

    @property
    def roster(self) -> tuple[str, ...]:
        return self.fixture.pre.matrix.units


@dataclass(frozen=True, slots=True)
class Recorded:
    """One outcome file, read back. Exactly one of `proposal` and `failed` is set."""

    index: int
    question: str
    proposal: ProposedDesign | None
    failed: str | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class Recording:
    directory: Path
    manifest: dict[str, Any]
    outcomes: tuple[Recorded, ...]
    digest_now: str


def contracts() -> ContractSet:
    return load()


def world(contract_set: ContractSet) -> World:
    """Build W1 at harness scale and measure the pre-period for every metric the ledger has."""
    fixture = harness.build_fixture(
        WORLD, world_seed=WORLD_SEED, scale=SCALE, contracts=contract_set
    )
    ledger = _control_ledger(fixture)
    waste_by_unit_week = _waste_unit_weeks(ledger)
    weeks = ledger.weeks
    pre_weeks, _ = design_module.split_weeks(weeks)
    waste_pre = design_module.pre_period(
        fixture.run,
        by_unit_week=waste_by_unit_week,
        revenue_by_unit=harness._by_unit(ledger.revenue_cents, pre_weeks),
        cogs_by_unit=harness._by_unit(ledger.cogs_cents, pre_weeks),
        waste_by_unit=harness._by_unit(ledger.waste_cents, pre_weeks),
        weeks=weeks,
        covariates=contract_set.balance_covariates,
    )
    return World(
        fixture=fixture,
        pre_by_metric={MARGIN: fixture.pre, WASTE: waste_pre},
        categories=tuple(harness.CATEGORIES),
    )


def context(contract_set: ContractSet, built: World) -> dict[str, str]:
    """Exactly what the agent is shown, rebuilt from the world so `D1` can compare it."""
    pre = built.pre_by_metric[MARGIN]
    units = built.roster
    share = Decimal(contract_set.inference.holdout_share_pct) / 100
    shown = enumerated(
        contract_set,
        ShownPrePeriod(
            weeks=len(pre.pre_weeks),
            units=len(units),
            mean_cents=int(pre.mean_per_unit_week),
            variance_cents2=int(pre.variance_per_unit_week),
        ),
        Roster(
            stores=len(built.fixture.run.chain.stores),
            surviving=len(units),
            control_arm=int(len(units) * share),
            categories=built.categories,
        ),
    )
    waste = built.pre_by_metric[WASTE]
    shown["pre_period"] += (
        f" The figures above are for {MARGIN}. For {WASTE} the pre-period mean is "
        f"{int(waste.mean_per_unit_week)} cents and the variance {int(waste.variance_per_unit_week)}. "
        "No history is available here for units_sold_per_store_week."
    )
    return shown


def questions() -> tuple[str, ...]:
    """The bank, read on every run and printed with its size. Written by this repository."""
    document = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8"))
    bank = tuple(str(q) for q in document["questions"])
    if not bank:
        raise ValueError("questions.yaml holds no question; a bank of none proves nothing")
    return bank


def latest_recording() -> Path:
    """The most recent dated directory under `recordings/`."""
    candidates = sorted(p for p in RECORDINGS.iterdir() if (p / MANIFEST).is_file())
    if not candidates:
        raise FileNotFoundError(
            f"no recording under {RECORDINGS}. `make record-designs` makes one, deliberately."
        )
    return candidates[-1]


def recording(directory: Path | None = None) -> Recording:
    """Read a recording back, parsing each proposal through the same parser the agent uses."""
    where = directory if directory is not None else latest_recording()
    manifest = json.loads((where / MANIFEST).read_text(encoding="utf-8"))
    outcomes: list[Recorded] = []
    for path in sorted(where.glob("[0-9][0-9][0-9].json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        proposal = None if raw.get("proposal") is None else _proposal(raw["proposal"])
        outcomes.append(
            Recorded(
                index=int(path.stem),
                question=str(raw["question"]),
                proposal=proposal,
                failed=raw.get("failed"),
                raw=raw,
            )
        )
    return Recording(
        directory=where,
        manifest=manifest,
        outcomes=tuple(outcomes),
        digest_now=digest_of(where),
    )


def fingerprints_now(contract_set: ContractSet, built: World) -> tuple[str, str]:
    """The registry and prompt fingerprints as this tree computes them, for `D1`."""
    return fingerprint(), prompt_fingerprint(context(contract_set, built))


def complete(proposal: ProposedDesign) -> DesignForm:
    """The form the engine sees: the model's seven fields plus the human's two, declared above."""
    return proposal.complete(max_duration=MAX_DURATION, decision_rule=DECISION_RULE)


# --------------------------------------------------------------------------- helpers


def _proposal(document: dict[str, Any]) -> ProposedDesign:
    """A recorded proposal back into the type, through `parse`, so a hand-edited file that no
    longer parses is a red run rather than a silently skipped design."""
    arguments = dict(document)
    arguments["mde"] = dict(document["mde"], value=Decimal(str(document["mde"]["value"])))
    scope = dict(document["scope"])
    if scope.get("stores") is None:
        scope["stores"] = "all"
    arguments["scope"] = scope
    return parse(arguments)


def _control_ledger(fixture: harness.WorldFixture) -> Ledger:
    """The all-control ledger the fixture was built from, read back through the same cache."""
    from evals.uplift import cache, outcomes

    if fixture.potential_ is not None:
        return fixture.potential_.control_ledger
    (ledger,) = cache.ledgers(
        cache.key("potential/control", fixture.world.id, fixture.world_seed, fixture.scale.name),
        lambda: (outcomes.collect(fixture.run),),
    )
    return ledger


def _waste_unit_weeks(ledger: Ledger) -> dict[tuple[str, Week], int]:
    """Waste value per store and ISO week, in cents, summed across the categories in scope.

    The waste metric at its grain is the waste column itself -- one term, no subtraction --
    which is why this is three lines where `grouped_metric.cell_margins` needs a contract
    rounding: there is nothing to round in a single integer.
    """
    out: dict[tuple[str, Week], int] = defaultdict(int)
    for (store, year, week, _category), value in ledger.waste_cents.items():
        out[(store, (year, week))] += value
    return dict(out)
