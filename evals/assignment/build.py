"""The join: chains the eval's author did not draw, turned into lotteries the system runs.

This is the only module in the package that imports both sides. `corpus/world/` knows
nothing about `holdout` — `ops/isolation.py` is the rule, `tests/boundary/` is the gate and
`.claude/hooks/corpus_isolation.py` refuses the write — and `holdout.core` knows nothing
about the corpus. What they meet over is here, where it can be read as one thing.

Observed, derived, swept
------------------------
Doctrine rule 3 is the easiest rule in this repository to break by accident, so the columns
are kept sharp. There are **four**, not three, and saying so is the point: the fourth is the
eval's own instrument settings — `PERIOD_WEEKS`, `REFERENCE_DRAWS`, `CANDIDATE_SCAN`,
`PER_UNIT_STRIDE`, `HASH_SEEDS`, the two policy refs, `METRIC_ID`, the experiment seed and the
form digest. None of them is observed, derived or swept; each is a **declared constant of the
measuring instrument**, deterministic, argued for beside its definition and printed where it
decides a figure. Leaving them out of the taxonomy would be the taxonomy quietly excusing
whatever did not fit it, which is how a default becomes a lie with a plausible shape.

**observed** — from `corpus/world/chain.py`, which places shops in towns and gives each one a
format, a size index, a pricing zone, a location and an opening date. Which stores exist, how
they cluster, and therefore which of them the automatic neighbour exclusions remove, is
decided by a generator whose author had never seen this eval.

**derived**, with the arithmetic written out:

* `store_size_sqm` = ``round(size_index x 1000)``. The corpus records a size as an index
  around 1.0 rather than as an area, and every use of the column is scale-invariant — the
  composite distance divides by the covariate's own variance, and the standardised
  difference is a ratio — so the constant cannot move an answer. It is the same scaling
  `evals/uplift/design.py` declares, for the same reason;
* the **unit outcome** = ``(period.ends_on - store.opened_on).days``, the days a shop had
  been open when the window closed. It is an observed date turned into an integer and
  nothing else. **Claim 3 asserts nothing whatever about outcomes** — it is about the
  lottery — and this exists so that `A9` can drive the whole of moment 3 and watch the
  refusal come out, instead of asserting that a function would have produced it. It is
  deliberately *not* one of the covariates the strata were matched on, so the design matrix
  cannot explain it exactly;
* `mde_absolute` = a tenth of the mean unit outcome. It decides only the power check, which
  claim 3 does not assert and does not read.

**swept**, over a declared and deterministic grid — never drawn at random, so a red run
reproduces exactly: the six worlds (they differ in how clustered the estate is, which is what
moves the surviving roster), two chain seeds, two scales, and the holdout share.

Why the holdout share is swept at all
--------------------------------------
`contracts/design/inference.yaml` declares 20%, and that is the share the claim rests on;
the other two are a sweep in exactly the sense claim 1's envelopes are. An arithmetic that
happens to be right at one share and wrong at another is wrong, and only a sweep finds it —
and at 20% **no roster the corpus produces can reach the `None` that the design engine turns
into `NO_ADMISSIBLE_ASSIGNMENT`**, because a 20% control arm always leaves five units per
stratum. The refusal is a live branch that nothing at the contract's own share drives. The
swept shares are declared not to be claims about any design, and the eval reports which
share produced each figure.

Three covariates, not the contract's five, and why that is honest
------------------------------------------------------------------
`contracts/design/balance_covariates.yaml` names five. Three of them — the format, the size
and the pricing zone — the chain supplies directly. The other two, `category_revenue_8w` and
the pre-period waste rate, exist only after a POS aggregation over eight months of generated
events; that is claim 2's path and it costs minutes per world. **The lottery is a function of
the strata, not of what the covariates mean**, so claim 3 is proved over strata built from
the three the corpus hands over for nothing. The ids and kinds are read out of the contract
rather than written here, so a contract that renames a covariate moves this too.

What that leaves open is stated in the README: these strata are not the strata a real design
would draw under, and a defect that only appears with five columns would not be seen here.
`evals/uplift/` draws over all five, on the same lottery, two hundred times.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from fractions import Fraction
from types import MappingProxyType

from corpus.world.chain import Chain, Store
from corpus.world.chain import build as build_chain
from corpus.world.scale import SCALES, Scale
from corpus.world.worlds import WORLDS, World

from holdout.contracts.model import BalanceCovariates, ContractSet
from holdout.core.design import neighbour_exclusions
from holdout.core.experiment import (
    Arm,
    AssignmentError,
    CovariateKind,
    CovariateMatrix,
    CovariateValue,
    Period,
    SealedAssignment,
    Standardised,
    control_size_for,
    draw,
)

#: The corpus records a store's size as an index around 1.0, not as an area. See the module
#: docstring: every use of the column is scale-invariant, so this cannot move an answer.
SIZE_INDEX_TO_SQM = 1_000

#: The three covariates the chain supplies without a POS aggregation, each mapped to the
#: contract id it answers. Read against the contract at run time, so a renamed covariate is a
#: red run here rather than a column that quietly stopped being the one it claims to be.
FROM_THE_CHAIN = ("store_format", "store_size_sqm", "pricing_zone")

#: The two chain seeds. A chain is a pure function of its seed, so a second seed is a second
#: hundred shops in a second arrangement — which is the only way to tell a lottery that works
#: from one that works on this estate.
CHAIN_SEEDS = ("holdout-w-0001", "holdout-w-0002")

#: The scales the grid runs at. `scenario` is the declared corpus and `harness` is the scale
#: claim 2 is proved at, because the surviving roster rather than the store count is what a
#: lottery is drawn over.
GRID_SCALES = ("scenario", "harness")

#: The scale the holdout-share sweep runs at. Small on purpose: the sweep exists to reach a
#: roster no stratification can hold both arms of, and that needs few units, not many.
SWEEP_SCALE = "smoke"

#: The swept shares, in percent. **None of these is a claim about any design.** The contract's
#: own share is added to the grid separately and is the one every figure that carries the
#: claim is measured at.
SWEPT_SHARES = (Decimal(45), Decimal(70))

#: How many weeks the comparison window the readout drive declares runs for. It decides the
#: dates on a `Period` and nothing else — claim 3 reads no outcome.
PERIOD_WEEKS = 8

#: How many candidates the reference set carries when moment 3 is driven. Small and declared:
#: the permutation p-value is not a figure this eval publishes or asserts.
REFERENCE_DRAWS = 16

#: The two policy refs the arms declare when moment 3 is driven. They differ so that the
#: contamination check's delivered-policy comparison is not vacuous — in an A/A design both
#: arms name the same policy and that half of the check cannot fail, which `contamination.py`
#: says about itself and which would quietly halve what `A9` watches.
TREATMENT_POLICY = "ladder_policy@v2-candidate"
CONTROL_POLICY = "ladder_policy@v1"


class BuildError(ValueError):
    """The corpus cannot supply what a configuration needs."""


@dataclass(frozen=True, slots=True)
class Configuration:
    """One estate, one committed seed, one declared share — before any lottery is run."""

    origin: str
    world_id: str
    scale_name: str
    chain_seed: str
    experiment_seed: str
    holdout_share_pct: Decimal
    at_the_contract_share: bool

    stores: int
    excluded: int
    roster: tuple[str, ...]
    matrix: CovariateMatrix
    control_size: int

    outcomes: MappingProxyType[str, int]
    period: Period

    @property
    def experiment_id(self) -> str:
        return f"t004-{self.world_id.lower()}-{self.scale_name}-{self.chain_seed[-4:]}"

    @property
    def form_digest(self) -> str:
        """A stand-in for the design's own fingerprint, and it is a *digest of this grid row*.

        Never a constant. A single form digest shared by every configuration would make the
        committed digest agree across two different experiments, which is precisely the
        confusion the field is on the seal to prevent.
        """
        return _form_digest(self.origin)


@dataclass(frozen=True, slots=True)
class Drawn:
    """A configuration and the lottery it produced. `seal` is `None` where none exists."""

    configuration: Configuration
    seal: SealedAssignment | None
    differences: tuple[Standardised, ...]

    @property
    def refused(self) -> bool:
        return self.seal is None


def _form_digest(origin: str) -> str:
    """A 64-character fingerprint of the grid row, computed by the eval's own hash."""
    from evals.assignment import reference

    return reference.digest(("t004-form", origin), size=32)


def _covariate_ids(
    covariates: BalanceCovariates,
) -> tuple[tuple[str, ...], tuple[CovariateKind, ...]]:
    """The three the chain supplies, in the contract's own column order."""
    declared = {c.id: c for c in covariates.covariates}
    missing = [name for name in FROM_THE_CHAIN if name not in declared]
    if missing:
        raise BuildError(
            f"{missing} is not in contracts/design/balance_covariates.yaml. The three columns "
            "this eval matches on are the contract's own, read out of it rather than written "
            "here, so a renamed covariate is a red run and not a silent relabelling."
        )
    ids = tuple(name for name in covariates.ids if name in set(FROM_THE_CHAIN))
    kinds = tuple(CovariateKind(declared[name].type) for name in ids)
    return ids, kinds


def _matrix(
    chain: Chain, roster: tuple[str, ...], covariates: BalanceCovariates
) -> CovariateMatrix:
    ids, kinds = _covariate_ids(covariates)
    rows = {unit: tuple(_value(chain.store(unit), name) for name in ids) for unit in roster}
    return CovariateMatrix.of(ids, kinds, rows)


def _value(store: Store, covariate_id: str) -> CovariateValue:
    """One store's value for one contract covariate. The only derivation is written out."""
    if covariate_id == "store_format":
        return store.store_format
    if covariate_id == "store_size_sqm":
        return Fraction(round(store.size_index * SIZE_INDEX_TO_SQM))
    if covariate_id == "pricing_zone":
        return store.pricing_zone
    raise BuildError(  # pragma: no cover - _covariate_ids filters to the three above
        f"{covariate_id!r} is not one of the covariates the chain supplies directly"
    )


def _period(scale: Scale) -> Period:
    ends_on = scale.start_date + timedelta(days=scale.days)
    return Period(opens_on=ends_on - timedelta(weeks=PERIOD_WEEKS), ends_on=ends_on)


def _outcomes(chain: Chain, roster: tuple[str, ...], period: Period) -> MappingProxyType[str, int]:
    """Days open at the close of the window. See the module docstring: observed, and not a
    covariate, so the design matrix cannot reproduce it exactly."""
    return MappingProxyType(
        {unit: (period.ends_on - chain.store(unit).opened_on).days for unit in roster}
    )


def _configuration(
    *,
    world: World,
    scale: Scale,
    chain_seed: str,
    share: Decimal,
    at_the_contract_share: bool,
    covariates: BalanceCovariates,
) -> Configuration | None:
    """One grid row, or `None` where the share buys an arm the roster cannot supply.

    `None` here is not the lottery refusing — it is `control_size_for` saying the arithmetic
    of the share against this roster has no answer at all, which is a different sentence and
    is reported as its own number.
    """
    chain = build_chain(chain_seed, scale, clustered_pct=world.clustered_pct)
    all_stores = tuple(store.store_id for store in chain.stores)
    excluded = {
        e.store_id for e in neighbour_exclusions(all_stores, chain.neighbour_pairs, frozenset())
    }
    roster = tuple(unit for unit in all_stores if unit not in excluded)
    try:
        control_size = control_size_for(len(roster), share)
    except AssignmentError:
        # Narrow on purpose. A bare `except Exception` here would let a genuine defect in the
        # matrix or the chain shrink the grid in silence, and "36 declared" would then be a
        # number the code does not guarantee. `AssignmentError` is the one expected answer:
        # the share's arithmetic against this roster has no answer at all, which is a
        # different sentence from the lottery refusing and is counted as its own number.
        return None
    period = _period(scale)
    origin = f"{world.id}·{scale.name}·{chain_seed}·holdout {share}%"
    return Configuration(
        origin=origin,
        world_id=world.id,
        scale_name=scale.name,
        chain_seed=chain_seed,
        experiment_seed=f"holdout-t004-{world.id.lower()}-{scale.name}-{chain_seed}-h{share}",
        holdout_share_pct=share,
        at_the_contract_share=at_the_contract_share,
        stores=len(all_stores),
        excluded=len(excluded),
        roster=roster,
        matrix=_matrix(chain, roster, covariates),
        control_size=control_size,
        outcomes=_outcomes(chain, roster, period),
        period=period,
    )


def configurations(contracts: ContractSet) -> tuple[Configuration, ...]:
    """The declared grid, in a fixed order. Nothing here is drawn at random."""
    covariates = contracts.balance_covariates
    share = contracts.inference.holdout_share_pct
    found: list[Configuration] = []
    for world_id in sorted(WORLDS):
        world = WORLDS[world_id]
        for scale_name in GRID_SCALES:
            for chain_seed in CHAIN_SEEDS:
                built = _configuration(
                    world=world,
                    scale=SCALES[scale_name],
                    chain_seed=chain_seed,
                    share=share,
                    at_the_contract_share=True,
                    covariates=covariates,
                )
                if built is not None:
                    found.append(built)
        for swept in SWEPT_SHARES:
            built = _configuration(
                world=world,
                scale=SCALES[SWEEP_SCALE],
                chain_seed=CHAIN_SEEDS[0],
                share=swept,
                at_the_contract_share=False,
                covariates=covariates,
            )
            if built is not None:
                found.append(built)
    if not found:
        raise BuildError("the declared grid produced no configuration at all")
    return tuple(found)


def run_the_lottery(configuration: Configuration) -> Drawn:
    """Moment 1's lottery, over one configuration. A `None` seal is a refusal, not an error."""
    drawn = draw(
        experiment_id=configuration.experiment_id,
        roster=configuration.roster,
        seed=configuration.experiment_seed,
        form_digest=configuration.form_digest,
        matrix=configuration.matrix,
        control_size=configuration.control_size,
    )
    if drawn is None:
        return Drawn(configuration=configuration, seal=None, differences=())
    seal, differences = drawn
    return Drawn(configuration=configuration, seal=seal, differences=differences)


def delivered_by_arm(seal: SealedAssignment) -> dict[str, str]:
    """Each unit's delivered policy ref, correct by arm — the uncontaminated delivery."""
    return {
        unit: (TREATMENT_POLICY if seal.arms[unit] is Arm.TREATMENT else CONTROL_POLICY)
        for unit in seal.roster
    }
