"""The resolved shape of every contract — frozen dataclasses over stdlib types only.

This module is what crosses the boundary into `holdout.core`. It imports no YAML parser
and no schema validator, so a core function can take a `GuardrailWindow` as an argument in
an interpreter where neither library is installed. A test asserts that by blocking both
from `sys.modules` and importing this module anyway.

Everything is frozen and every container is a tuple or a read-only mapping. A contract that
could be mutated after loading is a contract with two values.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, localcontext
from types import MappingProxyType
from typing import Any, Literal


def freeze(value: Any) -> Any:
    """Recursively convert lists to tuples and dicts to read-only mappings."""
    if isinstance(value, dict):
        return MappingProxyType({k: freeze(v) for k, v in value.items()})
    if isinstance(value, list | tuple):
        return tuple(freeze(v) for v in value)
    return value


@dataclass(frozen=True, slots=True)
class Provenance:
    """Doctrine rule 3 — nothing is invented.

    `kind` is the whole point. A verified legal fact and a stated assumption of the
    synthetic scenario are both admissible; presenting the second as the first is not, and
    there is no third option where a number simply appears.
    """

    kind: Literal["legal_instrument", "scenario_assumption"]
    verified_on: date
    instrument: str | None = None
    article: str | None = None
    url: str | None = None
    quote: str | None = None
    note: str | None = None
    informed_by: str | None = None

    @property
    def is_law(self) -> bool:
        return self.kind == "legal_instrument"


@dataclass(frozen=True, slots=True)
class Rounding:
    """Load-bearing, not a detail.

    Claim 5 compares consumers as integers with no tolerance. Two consumers that round
    differently disagree by one cent and the claim fails for a stupid reason, so the mode
    and the scale are contract terms and every compiled consumer is emitted against them.
    """

    mode: Literal["half_even", "half_up"]
    decimals: int

    _MODES = MappingProxyType({"half_even": ROUND_HALF_EVEN, "half_up": ROUND_HALF_UP})

    #: How each mode is spelled in Spark SQL. `round` is half-up; `bround` is banker's
    #: rounding. Emitting `round` for a half_even contract is the exact one-cent bug above.
    _SQL = MappingProxyType({"half_even": "bround", "half_up": "round"})

    @property
    def sql_function(self) -> str:
        return str(self._SQL[self.mode])

    def quantize(self, value: Decimal | int | str) -> Decimal:
        """Round to the contract's scale, in the contract's mode."""
        exponent = Decimal(1).scaleb(-self.decimals)
        with localcontext() as ctx:
            ctx.prec = 34
            return Decimal(value).quantize(exponent, rounding=self._MODES[self.mode])

    def canonical_integer(self, value: Decimal | int | str) -> int:
        """The integer claim 5 compares.

        A metric value becomes a single integer at the contract's scale — cents for a
        two-decimal euro metric, whole units for a count. Comparing floats needs a
        tolerance, and a tolerance is a place for a disagreement to hide.
        """
        return int(self.quantize(value).scaleb(self.decimals).to_integral_value())


@dataclass(frozen=True, slots=True)
class MetricSource:
    alias: str
    relation: str
    join: Literal["anchor", "full_outer_on_grain"]

    @property
    def relation_name(self) -> str:
        """The unqualified table name, for dbt's `ref()`."""
        return self.relation.rsplit(".", 1)[-1]


@dataclass(frozen=True, slots=True)
class Restatement:
    from_version: int
    reason: str
    affects_past_values: bool


@dataclass(frozen=True, slots=True)
class Metric:
    id: str
    version: int
    effective_from: date
    effective_to: date | None
    supersedes: int | None
    grain: tuple[str, ...]
    unit: str
    rounding: Rounding
    expression: str
    sources: tuple[MetricSource, ...]
    description: str | None
    why_the_readout_needs_it: str | None
    provenance: Provenance
    restatement: Restatement | None
    source_path: str

    @property
    def ref(self) -> str:
        return f"{self.id}@v{self.version}"

    @property
    def identifier(self) -> str:
        """The metric's name where a **name is an identifier** rather than prose.

        `ref` is `category_margin_per_store_week@v3` and is for a human. This is
        `category_margin_per_store_week_v3`, and it exists because two consumers put the
        metric's name somewhere an engine parses: the SQL table function names a catalog
        object, and the dbt model takes its relation name **from its file name**.

        **The dot was the defect, and it was found by running dbt rather than by reading
        the file.** `generated/dbt/models/metrics/` was written as `{id}.v{version}.sql`
        like the other three artefacts, and dbt derives the model name from the file name,
        so `category_margin_per_store_week.v3` reached Spark as a three-part identifier:

            [REQUIRES_SINGLE_PART_NAMESPACE] spark_catalog requires a single-part
            namespace, but got identifier `gold`.`category_margin_per_store_week`.`v3`

        Measured on dbt-core 1.12.3 / dbt-spark 1.11.0 against local Delta, on all three
        metrics, every run. **It is not a local artefact**: on Databricks the same name
        resolves to `catalog`.`gold`.`category_margin_per_store_week`.`v3`, four parts,
        which is invalid there too. The other three artefacts are unaffected — none of them
        takes its file name as an identifier — which is why one shared stem hid it.

        `docs/DECISIONS.md`'s *"The generated SQL has never been executed"* deferred exactly
        this to the moment gold was built, and ruled in advance: **if gold does not match,
        the contracts move — not the other way round.** This is the contract moving.
        """
        return f"{self.id}_v{self.version}"

    @property
    def anchor(self) -> MetricSource:
        return self.sources[0]


@dataclass(frozen=True, slots=True)
class GuardrailRule:
    id: str
    statement: str
    source: Provenance
    value: Any = None
    unit: str | None = None


@dataclass(frozen=True, slots=True)
class GuardrailWindow:
    """A half-open interval `[effective_from, effective_to)`.

    A decision taken in April is judged by April's window, permanently, even after the rule
    changes again — so a window is never edited and never deleted, only closed and
    succeeded. A period during which a rule did not apply is written as a window that says
    so, with its own source, rather than as a gap; an absent window and a lapsed rule look
    identical on disk, and only one of them is a fact.
    """

    effective_from: date
    effective_to: date | None
    rules: tuple[GuardrailRule, ...]
    label: str | None = None
    note: str | None = None

    def rule(self, rule_id: str) -> GuardrailRule | None:
        return next((r for r in self.rules if r.id == rule_id), None)


@dataclass(frozen=True, slots=True)
class Guardrail:
    id: str
    title: str
    applies_to: tuple[str, ...]
    windows: tuple[GuardrailWindow, ...]
    safe_state: MappingProxyType[str, str]
    description: str | None
    source_path: str


@dataclass(frozen=True, slots=True)
class PolicyStep:
    step: int
    hours_to_expiry_at_most: float
    depth_pct: float
    source: Provenance


@dataclass(frozen=True, slots=True)
class FloorBehaviour:
    when_step_breaches_floor: Literal["clamp_to_floor", "refuse"]
    statement: str


@dataclass(frozen=True, slots=True)
class Policy:
    id: str
    version: int
    effective_from: date
    effective_to: date | None
    supersedes: str | None
    kind: Literal["deterministic", "model_assisted"]
    decision_path: Literal["markdown", "base_price"]
    safe_state: bool
    steps: tuple[PolicyStep, ...]
    floor_behaviour: FloorBehaviour
    marker: str | None
    title: str | None
    description: str | None
    idempotency_key: tuple[str, ...]
    source_path: str

    @property
    def ref(self) -> str:
        return f"{self.id}@v{self.version}"


@dataclass(frozen=True, slots=True)
class ReasonCode:
    code: str
    meaning: str
    what_would_fix_it: str | None = None
    check: str | None = None
    guardrail: str | None = None
    """Which guardrail produces a decision-time refusal, or `any` where no single one owns
    it. Absent for the design-time and readout-time codes, which are not about a price."""


@dataclass(frozen=True, slots=True)
class ReasonCodes:
    """Three moments, because the system refuses three different things: a price, an
    experiment, and a number."""

    at_decision: tuple[ReasonCode, ...]
    at_design: tuple[ReasonCode, ...]
    at_readout: tuple[ReasonCode, ...]

    @property
    def all_codes(self) -> frozenset[str]:
        return frozenset(c.code for c in (*self.at_decision, *self.at_design, *self.at_readout))

    @property
    def decision_codes(self) -> frozenset[str]:
        """The closed vocabulary `holdout.core.guardrails` must mirror exactly."""
        return frozenset(c.code for c in self.at_decision)


@dataclass(frozen=True, slots=True)
class Covariate:
    id: str
    type: Literal["numeric", "categorical"]
    measured: Literal["pre_period"]
    description: str
    lookback_weeks: int | None = None
    source_relation: str | None = None


@dataclass(frozen=True, slots=True)
class BalanceCovariates:
    version: int
    effective_from: date
    covariates: tuple[Covariate, ...]

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(c.id for c in self.covariates)


@dataclass(frozen=True, slots=True)
class Carryover:
    """What a price moved in one place is still doing somewhere else.

    Three declared facts about grocery retail, two present and one deliberately absent.
    The interference table over the four units of randomisation is *derived* from this
    block by `holdout.core.design.feasibility.interference_of` and is nowhere written out:
    a hard-coded table would pass every test while quietly being a second definition of a
    contract value.

    `washout_weeks` is `None` where none is declared, and `None` is not zero. Zero would
    assert that no washout is needed, which is a different claim and a much stronger one.
    """

    reference_price_memory: bool
    cross_price_substitution: bool
    washout_weeks: int | None

    @property
    def reference_price_is_exhausted(self) -> bool:
        """Whether a declared washout outlasts the reference price the shopper carries.

        A washout is only a mitigation if it is long enough, and "long enough" is exactly
        what a declared number of weeks asserts. With no washout declared, nothing is
        exhausted and the memory carries across every time boundary.
        """
        return self.washout_weeks is not None and self.washout_weeks > 0


@dataclass(frozen=True, slots=True)
class InferenceSettings:
    """`contracts/design/inference.yaml`, resolved. `Decimal` and `int` only, never a float.

    Fixed in a contract rather than as constants in a module, for the reason
    `balance_covariates.yaml` gives about itself: anything that can be chosen after the
    fact will be chosen after the fact. A `Decimal` constant in a `.py` file is precisely
    the "value without a source" the contract layer exists to refuse — doctrine rule 3 does
    not care what extension the file has.
    """

    version: int
    effective_from: date
    alpha: Decimal
    target_power: Decimal
    z_two_sided_alpha: Decimal
    z_one_sided_alpha: Decimal
    z_power: Decimal
    balance_tolerance_smd: Decimal
    exposure_min_pct: Decimal
    holdout_share_pct: Decimal
    neighbour_radius_m: int
    permutation_draws: int
    max_assignment_attempts: int
    carryover: Carryover

    def z_alpha(self, *, two_sided: bool) -> Decimal:
        """The quantile the power calculation uses, named rather than chosen at the call site.

        A one-sided design sizes on a smaller quantile and therefore needs fewer units, so
        which one applies is a decision with consequences. Both are declared in the
        contract and neither is computed here.
        """
        return self.z_two_sided_alpha if two_sided else self.z_one_sided_alpha


@dataclass(frozen=True, slots=True)
class HarnessSeeds:
    """How many worlds the A/A harness generates and how many lotteries it draws against each.

    `draws` is `world x lotteries_per_world_seed` — the K claim 2 is stated at. The split
    exists because the two factors cost different things: a world seed costs a generation and
    a lottery costs a readout, and outside W2 two counterfactual generations buy every lottery.
    """

    world: int
    lotteries_per_world_seed: int
    pathology_world_seeds: int
    pathology_lotteries_per_world_seed: int
    interference_lotteries_per_world_seed: int

    @property
    def draws(self) -> int:
        """K, for the two worlds whose rates are the claim."""
        return self.world * self.lotteries_per_world_seed

    @property
    def pathology_draws(self) -> int:
        """Draws per world for W3, W4 and W5."""
        return self.pathology_world_seeds * self.pathology_lotteries_per_world_seed

    @property
    def interference_draws(self) -> int:
        """Draws for W2, on each arm of the pair it publishes."""
        return self.pathology_world_seeds * self.interference_lotteries_per_world_seed


@dataclass(frozen=True, slots=True)
class MachineryConfiguration:
    """What `python -m evals.uplift.machinery` runs at — the only entry point a mutation names."""

    world_seeds: int
    lotteries: int
    scale: str


@dataclass(frozen=True, slots=True)
class AaHarness:
    """`contracts/design/aa_harness.yaml`, resolved. What the **eval** consumes.

    Kept apart from `InferenceSettings`, which is what the **core** consumes, so that a number
    the estimator never reads cannot be mistaken for one it does. `Decimal` and `int` only,
    never a float, for the reason `Money` gives one package along.
    """

    version: int
    effective_from: date
    seeds: HarnessSeeds
    binomial_level: Decimal
    false_refusal_max_pct: Decimal
    per_world_min_correct_pct: Decimal
    mde_pct_of_pre_period_mean: Decimal
    unit_exposed_min_ack_pct: Decimal
    machinery: MachineryConfiguration


@dataclass(frozen=True, slots=True)
class TrainingSettings:
    """`contracts/ml/training.yaml`, resolved. `Decimal` and `int` only, never a float.

    Every threshold `pipelines/ml/` branches on, in a contract rather than in the module it
    gates. `inference.yaml` gives the general reason — anything that can be chosen after the
    fact will be chosen after the fact — and a promotion gate is where that bites hardest:
    the model is the thing somebody wants to ship, so it is the number most likely to be
    nudged, by whoever is under the most pressure to nudge it.

    **What is deliberately absent is a price response.** Measured on this repository's corpus,
    price is a deterministic function of hours-to-expiry within an arm, so nothing about
    demand at a price the policy never set is identified from history. A declared elasticity
    here would be inventing the number the model exists to learn, and `pipelines/ml/` says so
    in the same words rather than filling the hole.
    """

    version: int
    effective_from: date
    evaluation_days: int
    min_training_days: int
    min_observed_share: Decimal
    calibration_tolerance_pct: Decimal
    rmse_share_of_baseline: Decimal
    segment_family_false_alarm_rate: Decimal
    min_segment_days: int


@dataclass(frozen=True, slots=True)
class ContractSet:
    """Every contract in the repository, validated and resolved.

    `metrics` and `policies` hold every version, superseded ones included. Nothing is ever
    dropped on load: the meaning of a closed experiment depends on the version it named
    still being readable, so 'which one applies' is a question for the as-of resolver and
    never for the loader.
    """

    metrics: tuple[Metric, ...]
    guardrails: tuple[Guardrail, ...]
    policies: tuple[Policy, ...]
    reason_codes: ReasonCodes
    balance_covariates: BalanceCovariates
    inference: InferenceSettings
    training: TrainingSettings
    aa_harness: AaHarness
    design_form: MappingProxyType[str, Any]
    census: Any
    """The provenance walk's tally — see `holdout.contracts.provenance.Census`. Typed loosely
    so that this module stays importable with nothing but the standard library."""

    @property
    def metric_ids(self) -> tuple[str, ...]:
        """The closed list the design form's `primary_metric` draws from."""
        return tuple(sorted({m.id for m in self.metrics}))

    @property
    def policy_refs(self) -> tuple[str, ...]:
        """The closed list the design form's `intervention` draws from."""
        return tuple(sorted(p.ref for p in self.policies))

    def metric_versions(self, metric_id: str) -> tuple[Metric, ...]:
        return tuple(
            sorted((m for m in self.metrics if m.id == metric_id), key=lambda m: m.version)
        )

    def guardrail(self, guardrail_id: str) -> Guardrail:
        return next(g for g in self.guardrails if g.id == guardrail_id)
