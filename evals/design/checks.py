"""The checks, each with a stable id, a falsifiable question, and its figure.

`D1` is what makes the rest worth running: a recording made against a different agent than
the one in the tree is `STALE`, and everything below it would be grading answers to questions
nobody now asks. `D5` is the sentence in `CLAUDE.md` made checkable by a mutation. `D6` is the
claim, and its figure is published beside the rate a valid design would have had by chance,
because on the null world that is what a refused design mostly produces and reading it as a
save would be this eval flattering the engine.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from evals.design import build, grade, reference
from evals.report import Check, Report
from holdout.core.design import DesignRefusal, Feasible, assess
from holdout.core.design.form import FilledBy, FilledByKind, Unit
from holdout.core.design.refusal import DesignRefusalCode

#: Every `at_design` code, and whether the agent's route can reach it. What it cannot reach is
#: named with the reason rather than left off, which is what `D7` prints.
UNREACHABLE_BY_THE_AGENT: dict[str, str] = {
    "METRIC_NOT_IN_CONTRACT": (
        "the delivery tool's schema closes the metric list at the API, so an id outside the "
        "contract is a malformed call the model never gets to make; reached by the human path"
    ),
    "UNITS_ALREADY_COMMITTED": (
        "the harness keeps no register of open experiments, so nothing is committed elsewhere; "
        "the estate's `committed_elsewhere` is empty and stated as such in `pipelines/gold`"
    ),
    "STOPPING_RULE_PERMITS_PEEKING": (
        "the stopping rule is not a field the agent fills -- the estate declares it per "
        "experiment -- so a recording cannot carry a peeking design; the estate's own readout "
        "reaches it, and did, on 2026-09-10"
    ),
    "EXCLUSIONS_DEFINED_POST_HOC": (
        "reached only when a locked design is re-submitted with moved exclusions; a recording "
        "is moment 1 and has no previously locked form to move against"
    ),
    "NO_ADMISSIBLE_ASSIGNMENT": (
        "a roster that stratifies into single-unit strata; at 320 stores and a 20% share every "
        "stratum has room, so the harness roster cannot produce it"
    ),
}


@dataclass(frozen=True, slots=True)
class Measured:
    contracts: build.ContractSet
    world: build.World
    recording: build.Recording
    fingerprints_now: tuple[str, str]
    verdicts: tuple[grade.Verdict, ...]
    anyways: tuple[grade.Anyway, ...]
    boundaries: dict[int, reference.Boundary]

    @property
    def proposals(self) -> tuple[build.Recorded, ...]:
        return tuple(o for o in self.recording.outcomes if o.proposal is not None)

    @property
    def refused(self) -> tuple[grade.Verdict, ...]:
        return tuple(v for v in self.verdicts if v.refused is not None)

    @property
    def feasible(self) -> tuple[grade.Verdict, ...]:
        return tuple(v for v in self.verdicts if v.feasible is not None)

    @property
    def ungraded(self) -> tuple[grade.Verdict, ...]:
        return tuple(v for v in self.verdicts if v.ungraded is not None and self._had_proposal(v))

    def _had_proposal(self, v: grade.Verdict) -> bool:
        return self.recording.outcomes[v.index].proposal is not None


def measure() -> Measured:
    contracts = build.contracts()
    world = build.world(contracts)
    recording = build.recording()
    verdicts = tuple(grade.verdict(o, contracts=contracts, built=world) for o in recording.outcomes)
    anyways = tuple(
        a
        for o, v in zip(recording.outcomes, verdicts, strict=True)
        if (a := grade.anyway(o, v, contracts=contracts, built=world)) is not None
    )
    boundaries: dict[int, reference.Boundary] = {}
    for o, v in zip(recording.outcomes, verdicts, strict=True):
        if o.proposal is None or v.ungraded is not None:
            continue
        if o.proposal.unit is not grade.GRADABLE_UNIT:
            # The reference is the power boundary, and power needs a roster at the design's
            # unit. A unit refused for interference was never sized, by either side.
            continue
        pre = world.pre_by_metric[o.proposal.primary_metric]
        available = _available(o, world)
        boundaries[o.index] = reference.boundary(
            build.complete(o.proposal),
            inference=contracts.inference,
            available=available,
            variance_cents2=pre.variance_per_unit_week,
            mean_cents=pre.mean_per_unit_week,
        )
    return Measured(
        contracts=contracts,
        world=world,
        recording=recording,
        fingerprints_now=build.fingerprints_now(contracts, world),
        verdicts=verdicts,
        anyways=anyways,
        boundaries=boundaries,
    )


def _available(o: build.Recorded, world: build.World) -> int:
    """The roster after the declared and the automatic exclusions, counted here on its own."""
    from holdout.core.design.feasibility import neighbour_exclusions

    assert o.proposal is not None
    pre = world.pre_by_metric[o.proposal.primary_metric]
    declared = frozenset(e.store_id for e in o.proposal.exclusions)
    after = tuple(u for u in pre.matrix.units if u not in declared)
    automatic = neighbour_exclusions(after, world.fixture.run.chain.neighbour_pairs, declared)
    return len(after) - len(automatic)


# --------------------------------------------------------------------------- the checks


def _d1(m: Measured) -> Check:
    manifest = m.recording.manifest
    registry_now, prompt_now = m.fingerprints_now
    same_registry = manifest["registry_fingerprint"] == registry_now
    same_prompt = manifest["prompt_fingerprint"] == prompt_now
    same_digest = manifest["digest"] == m.recording.digest_now
    problems = []
    if not same_registry:
        problems.append("registry moved: STALE")
    if not same_prompt:
        problems.append("prompt or context moved: STALE")
    if not same_digest:
        problems.append("an outcome file was edited after the manifest was written")
    return Check(
        id="D1.the-recording-is-from-the-agent-in-the-tree",
        question=(
            "do the registry and prompt fingerprints in the recording equal the ones this tree "
            "computes now, and does the directory's digest equal the manifest's?"
        ),
        passed=not problems,
        figure=(
            f"registry {registry_now[:12]} · prompt {prompt_now[:12]} · digest "
            f"{m.recording.digest_now[:12]} · recorded {manifest['recorded_on']} by "
            f"{manifest['model_id']}"
        ),
        detail="; ".join(problems),
        counterexamples=tuple(problems),
    )


def _d2(m: Measured) -> Check:
    manifest = m.recording.manifest
    outcomes = m.recording.outcomes
    problems: list[str] = []
    if len(outcomes) != manifest["questions"]:
        problems.append(f"{len(outcomes)} file(s) against a manifest of {manifest['questions']}")
    expected = list(range(len(outcomes)))
    if [o.index for o in outcomes] != expected:
        problems.append("the files are not 000.. in order; one is missing or renamed")
    bank = build.questions()
    if [o.question for o in outcomes] != list(bank):
        problems.append("the questions asked are not the bank, in order")
    for o in outcomes:
        if (o.proposal is None) == (o.failed is None):
            problems.append(f"{o.index:03d}: a proposal and a failure, or neither")
    return Check(
        id="D2.every-question-is-counted",
        question=(
            "is N the whole recording -- every file the manifest counts, in the bank's order, "
            "each outcome a proposal or a named failure and never both?"
        ),
        passed=not problems,
        figure=(
            f"N = {len(m.proposals)} proposal(s) of {len(outcomes)} question(s); "
            f"{sum(1 for o in outcomes if o.failed is not None)} declined"
        ),
        counterexamples=tuple(problems),
        unarmed_because=(
            "the population is the recording's own files; a break that dropped one would "
            "edit the reader, which is the detector, or the recording, which is the input"
        ),
    )


def _d3(m: Measured) -> Check:
    forbidden = ("verdict", "refused", "reasons", "feasible", "codes")
    found = [
        f"{o.index:03d} carries {key!r}"
        for o in m.recording.outcomes
        for key in forbidden
        if key in o.raw
    ]
    return Check(
        id="D3.the-engine-decides-and-not-the-record",
        question=(
            "is every verdict computed on this run from the proposal and the contracts, with no "
            "verdict read from disk?"
        ),
        passed=not found,
        figure=f"{len(m.verdicts)} verdict(s) computed; {len(found)} recorded verdict(s) found",
        counterexamples=tuple(found),
        unarmed_because=(
            "a property of the inputs: a verdict written into a recording is an edit to the "
            "recording, not to src/holdout/, and gate-proof plants breaks in the system"
        ),
    )


def _d4(m: Measured) -> Check:
    # The contract's list, not the enum's: the enum is the engine's own copy of the
    # vocabulary, and a check that read it would be the engine agreeing with itself.
    declared = {c.code for c in m.contracts.reason_codes.at_design}
    problems: list[str] = []
    for v in m.refused:
        assert v.refused is not None
        for reason in v.refused.reasons:
            if reason.code.value not in declared:
                problems.append(f"{v.index:03d}: {reason.code.value} is not a declared code")
            if not reason.detail.strip() or not reason.what_would_fix_it.strip():
                problems.append(f"{v.index:03d}: {reason.code.value} carries no detail or remedy")
    counts = Counter(code for v in m.refused for code in v.codes)
    return Check(
        id="D4.a-refusal-is-a-declared-code",
        question=(
            "is every refusal a code from the closed at_design vocabulary, carrying a detail and "
            "what would fix it?"
        ),
        passed=not problems,
        figure=(
            f"M = {len(m.refused)} refused: "
            + (", ".join(f"{code} ×{n}" for code, n in sorted(counts.items())) or "none")
        ),
        counterexamples=tuple(problems),
        unarmed_because=(
            "the codes the engine can emit are a closed enum that tests/contracts mirrors "
            "against the contract; a code outside it cannot be constructed in one file, and "
            "an empty detail is refused by DesignRefusalReason itself"
        ),
    )


def _d5(m: Measured) -> Check:
    """Three attributions, one verdict. Compared on what the engine decides, never the digest."""
    attributions = (
        FilledBy(kind=FilledByKind.AGENT),
        FilledBy(kind=FilledByKind.HUMAN, name="A. Reviewer"),
        FilledBy(kind=FilledByKind.POLICY, name="quarterly_fresh_review"),
    )
    problems: list[str] = []
    compared = 0
    for o, v in zip(m.recording.outcomes, m.verdicts, strict=True):
        if o.proposal is None or v.ungraded is not None:
            continue
        compared += 1
        pre = m.world.pre_by_metric[o.proposal.primary_metric]
        metric = m.contracts.metric_versions(o.proposal.primary_metric)[-1]
        base = build.complete(o.proposal)
        results = []
        for who in attributions:
            form = _restamped(base, who)
            results.append(
                assess(
                    form,
                    experiment_id=f"design/{o.index:03d}/{who.kind.value}",
                    seed=build.LOTTERY_SEED,
                    metric=metric,
                    metric_ids=m.contracts.metric_ids,
                    covariates=m.contracts.balance_covariates,
                    inference=m.contracts.inference,
                    roster=pre.matrix.units,
                    matrix=pre.matrix,
                    variance_per_unit_week=pre.variance_per_unit_week,
                    mean_per_unit_week=pre.mean_per_unit_week,
                    committed_elsewhere=frozenset(),
                    neighbour_pairs=m.world.fixture.run.chain.neighbour_pairs,
                    stopping=build.design_module.STOPPING,
                    previously_locked=None,
                )
            )
        signatures = {_decision_signature(r) for r in results}
        if len(signatures) != 1:
            problems.append(
                f"{o.index:03d}: {len(signatures)} different verdicts across the three sources"
            )
    return Check(
        id="D5.three-sources-one-verdict",
        question=(
            "does the same form stamped agent, human and policy produce the same roster, sample, "
            "window, arms and refusal codes -- with a planted branch on filled_by turning this red?"
        ),
        passed=not problems and compared > 0,
        figure=f"{compared} design(s) × 3 attributions, {len(problems)} disagreement(s)",
        counterexamples=tuple(problems),
    )


def _restamped(form: build.DesignForm, who: FilledBy) -> build.DesignForm:
    return build.DesignForm(
        hypothesis=form.hypothesis,
        intervention=form.intervention,
        scope=form.scope,
        primary_metric=form.primary_metric,
        unit=form.unit,
        mde=form.mde,
        max_duration=form.max_duration,
        exclusions=form.exclusions,
        decision_rule=form.decision_rule,
        filled_by=who,
    )


def _decision_signature(result: Feasible | DesignRefusal) -> tuple[object, ...]:
    if isinstance(result, DesignRefusal):
        return ("refused", *((r.code.value, r.detail) for r in result.reasons))
    return (
        "feasible",
        result.roster,
        result.required_per_arm,
        result.weeks,
        tuple(sorted((u, a.value) for u, a in result.assignment.arms.items())),
        result.assignment.draw_index,
    )


def _d6(m: Measured) -> Check:
    alpha = Fraction(m.contracts.inference.alpha)
    ran = m.anyways
    wrong = [a for a in ran if a.significant and a.excludes_truth]
    k = len(wrong)
    expected = float(alpha) * len(ran)
    codes_run = Counter(code for a in ran for code in a.codes)
    not_run = [v for v in m.refused if v.index not in {a.index for a in ran}]
    return Check(
        id="D6.a-refused-design-run-anyway-is-wrong-at-the-rate-the-refusal-predicts",
        question=(
            "over the refused designs that can be run with the guards off, is the count that "
            "produce a confident wrong number published beside what chance alone would give?"
        ),
        # On the null world every refusal here is for power, and power predicts the false-positive
        # rate alpha and no more; the check is that the measurement was made and that nothing
        # refused produced a *confident* number the truth contradicts at more than chance --
        # a K above alpha·M on W1 would be the estimator misbehaving, not the refusal saving.
        passed=len(ran) > 0
        and k <= max(1, round(expected + 3 * (expected * (1 - float(alpha))) ** 0.5)),
        figure=(
            f"K = {k} of {len(ran)} run anyway (expected by chance at α={alpha}: {expected:.2f}); "
            f"{len(not_run)} refused but not runnable; codes run: "
            + (", ".join(f"{c} ×{n}" for c, n in sorted(codes_run.items())) or "none")
        ),
        detail=(
            "; ".join(
                f"{a.index:03d} uplift {float(a.uplift_cents):+.0f}c p={float(a.p_value):.3f} "
                f"[{float(a.interval_cents[0]):+.0f}, {float(a.interval_cents[1]):+.0f}]"
                for a in ran
            )
        ),
        counterexamples=tuple(
            f"{a.index:03d}: significant and the interval excludes the truth" for a in wrong
        ),
        unarmed_because=(
            "the figure is a count against a chance bound on the null world; a break that "
            "moved K would have to make the estimator confident on a world with no effect, "
            "and that is claim 2's gate to prove, with two hundred draws rather than five"
        ),
    )


def _d7(m: Measured) -> Check:
    reached = {code for v in m.refused for code in v.codes}
    every = {code.value for code in DesignRefusalCode}
    reachable = every - set(UNREACHABLE_BY_THE_AGENT)
    unreached = sorted(reachable - reached)
    undeclared = sorted(set(UNREACHABLE_BY_THE_AGENT) - every)
    return Check(
        id="D7.every-reachable-refusal-is-reached",
        question=(
            "does the recording reach every at_design code the agent's route can reach, and is "
            "every code it cannot reach named with the reason rather than absent?"
        ),
        passed=not unreached and not undeclared,
        figure=(
            f"{len(reached)} of {len(reachable)} reachable code(s) reached; "
            f"{len(UNREACHABLE_BY_THE_AGENT)} declared unreachable by name"
        ),
        detail="unreachable: "
        + "; ".join(f"{c}: {why}" for c, why in UNREACHABLE_BY_THE_AGENT.items()),
        counterexamples=(
            *(f"{c} is reachable and unreached" for c in unreached),
            *(f"{c} is declared unreachable and is not a code" for c in undeclared),
        ),
    )


def _d8(m: Measured) -> Check:
    problems: list[str] = []
    for index, b in m.boundaries.items():
        v = m.verdicts[index]
        engine_refuses = v.refused is not None
        engine_codes = set(v.codes)
        if b.refuses != engine_refuses:
            problems.append(
                f"{index:03d}: reference {'refuses' if b.refuses else 'accepts'}, engine "
                f"{'refuses' if engine_refuses else 'accepts'}"
            )
            continue
        if b.refuses:
            if b.refuses_capacity != ("UNDERPOWERED_FOR_CAPACITY" in engine_codes):
                problems.append(f"{index:03d}: capacity verdicts differ")
            if b.refuses_duration != ("UNDERPOWERED_FOR_DURATION" in engine_codes):
                problems.append(f"{index:03d}: duration verdicts differ")
        else:
            assert v.feasible is not None
            if b.shortest_weeks != v.feasible.weeks:
                problems.append(
                    f"{index:03d}: shortest window {b.shortest_weeks} vs engine {v.feasible.weeks}"
                )
            if b.required_at_shortest != v.feasible.required_per_arm:
                problems.append(
                    f"{index:03d}: required {b.required_at_shortest} vs engine "
                    f"{v.feasible.required_per_arm}"
                )
    return Check(
        id="D8.the-power-boundary-lands-where-independent-arithmetic-puts-it",
        question=(
            "for every graded design, does a second implementation of the power boundary -- "
            "Decimal, solved rather than searched -- agree with the engine on refuse-or-accept, "
            "on which code, and on the window and sample where it accepts?"
        ),
        passed=not problems and bool(m.boundaries),
        figure=f"{len(m.boundaries)} design(s) compared, {len(problems)} disagreement(s)",
        counterexamples=tuple(problems),
    )


def _d9(m: Measured) -> Check:
    """The interference table, engine against reference, over every unit -- not over the
    recording. A break that admits a unit is caught here whatever the model proposed, which is
    what `D7` could not promise: on 2026-09-11 a recording held two interference refusals and
    admitting one unit left the code reached by the other, so the mutation survived `D7`."""
    from holdout.core.design.feasibility import interference_of

    carryover = m.contracts.inference.carryover
    problems: list[str] = []
    table: list[str] = []
    for unit in Unit:
        engine = interference_of(unit, carryover) is not None
        independent = reference.crosses_a_declared_carryover(unit, carryover)
        table.append(f"{unit.value}: {'refused' if engine else 'admitted'}")
        if engine != independent:
            problems.append(
                f"{unit.value}: the engine {'refuses' if engine else 'admits'} it and the "
                f"contract's carryover block says {'refuse' if independent else 'admit'}"
            )
    return Check(
        id="D9.the-interference-table-is-the-contracts",
        question=(
            "for every unit of randomisation, does the engine's interference verdict equal the "
            "one derived a second way from the contract's carryover block?"
        ),
        passed=not problems,
        figure="; ".join(table),
        counterexamples=tuple(problems),
    )


# --------------------------------------------------------------------------- the report

NOTES: tuple[str, ...] = (
    "The questions were written by this repository; the model chose the designs. The bank is "
    "committed, read on every run, and printed with its size.",
    "The recording is a fixed sample from a dated model, stamped with its id; the claim is "
    "about the engine and not about that model.",
    "K is computed only for refusals the harness can run with the guards off -- today, the "
    "power refusals on the null world -- and its rate there is bounded below by alpha, which "
    "is not a finding. Refusals for interference, peeking and post-hoc exclusions need the "
    "worlds that violate them and are a deferral, named in docs/DECISIONS.md.",
    "A design at a unit the harness has no roster for, or on a metric the ledger has no "
    "history for, is ungraded with the reason and never assessed against another design's "
    "roster or variance.",
    "The policy family has two members since 2026-09-11; before that every design was A/A by "
    "construction and the model declined every question.",
    "There is no LLM judge here. Validity is code and the truth is sealed; a quality score is "
    "a number nothing checks.",
    "The reference boundary takes the contract's z values as declared; the normal quantile is "
    "the one arithmetic the two implementations share.",
)


def run() -> Report:
    m = measure()
    checks = (_d1(m), _d2(m), _d3(m), _d4(m), _d5(m), _d6(m), _d7(m), _d8(m), _d9(m))
    return Report(
        claim=6,
        title="the design engine refuses an invalid design regardless of where the judgment came from",
        checks=checks,
        numbers=_numbers(m),
        notes=NOTES,
    )


def _numbers(m: Measured) -> tuple[tuple[str, str], ...]:
    manifest = m.recording.manifest
    outcomes = m.recording.outcomes
    declined = Counter(o.failed for o in outcomes if o.failed is not None)
    nudged = sum(
        1 for o in outcomes if any(r.get("kind") == "nudge" for r in o.raw.get("trace", []))
    )
    ungraded = Counter(v.ungraded.split(":")[0] for v in m.ungraded if v.ungraded)
    codes = Counter(code for v in m.refused for code in v.codes)
    units = Counter(o.proposal.unit.value for o in m.proposals if o.proposal is not None)
    metrics = Counter(o.proposal.primary_metric for o in m.proposals if o.proposal is not None)
    return (
        (
            "recording",
            f"{manifest['recorded_on']} · {manifest['model_id']} · {m.recording.directory.name}",
        ),
        (
            "world",
            f"{build.WORLD} / {build.WORLD_SEED} at {build.SCALE.name}, {len(m.world.roster)} stores",
        ),
        ("bank", f"{len(build.questions())} question(s)"),
        ("N proposed", f"{len(m.proposals)} of {len(outcomes)}; {nudged} needed the one nudge"),
        ("declined", ", ".join(f"{k} ×{n}" for k, n in sorted(declined.items())) or "0"),
        (
            "M refused",
            f"{len(m.refused)}: "
            + (", ".join(f"{c} ×{n}" for c, n in sorted(codes.items())) or "none"),
        ),
        ("feasible", str(len(m.feasible))),
        ("ungraded", ", ".join(f"{k} ×{n}" for k, n in sorted(ungraded.items())) or "0"),
        (
            "K",
            f"{sum(1 for a in m.anyways if a.significant and a.excludes_truth)} of {len(m.anyways)} run anyway",
        ),
        ("units proposed", ", ".join(f"{u} ×{n}" for u, n in sorted(units.items()))),
        ("metrics proposed", ", ".join(f"{k} ×{n}" for k, n in sorted(metrics.items()))),
        (
            "pre-period",
            "; ".join(
                f"{metric}: mean {int(pre.mean_per_unit_week)}c var {int(pre.variance_per_unit_week)} "
                f"cv {float(Decimal(pre.variance_per_unit_week).sqrt() / pre.mean_per_unit_week):.2f}"
                for metric, pre in m.world.pre_by_metric.items()
            ),
        ),
    )
