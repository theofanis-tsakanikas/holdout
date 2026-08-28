"""Reading `contracts/` and turning it into `ContractSet`.

This is the only module in the repository permitted to parse YAML or run a JSON Schema.
Everything downstream — the compilers, the CLI, and eventually `holdout.core` — receives
frozen dataclasses and never sees a file path.

Loading never drops a superseded version. Which one applies is the as-of resolver's
question; the loader's job is that all of them are readable.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from holdout.contracts.errors import ContractError, Violation
from holdout.contracts.expression import ExpressionError
from holdout.contracts.expression import parse as parse_expression
from holdout.contracts.model import (
    AaHarness,
    BalanceCovariates,
    Carryover,
    ContractSet,
    Covariate,
    FloorBehaviour,
    Guardrail,
    GuardrailRule,
    GuardrailWindow,
    HarnessSeeds,
    InferenceSettings,
    MachineryConfiguration,
    Metric,
    MetricSource,
    Policy,
    PolicyStep,
    Provenance,
    ReasonCode,
    ReasonCodes,
    Restatement,
    Rounding,
    freeze,
)
from holdout.contracts.provenance import Census, census, check_provenance
from holdout.contracts.windows import check_timeline


class _LiteralLoader(yaml.SafeLoader):
    """A safe loader that does not resolve an unquoted `2026-03-01` into a `date`.

    Every date in a contract is validated against an ISO-8601 pattern in the schema, and a
    pattern can only be applied to text. If PyYAML converts the scalar first, the schema
    ends up validating whatever PyYAML decided the date meant — including its
    interpretation of a timezone that was never written — rather than the characters an
    author typed and a reviewer read. The contract is the text.
    """


_LiteralLoader.yaml_implicit_resolvers = {
    first: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_DIR = REPO_ROOT / "contracts"
SCHEMA_DIR = CONTRACTS_DIR / "schemas"

#: The closed refusal vocabulary. Named once, here, because it is read by the loader, by
#: two test modules and by a reader following a docstring — and it has already moved once,
#: from `design/`, where it had been filed under the experiment-design engine while two
#: thirds of it was about prices. A path spelled out in four places moves in three of them.
REASON_CODES = Path("vocabularies") / "reason_codes.yaml"

#: Rules the loader raises that are about a file's existence or its address rather than
#: about its contents.
MISSING_CONTRACT = "missing_contract"
UNCLAIMED_CONTRACT = "unclaimed_contract"

#: Every contract file this loader reads, by the directory that holds it. The list is
#: exhaustive on purpose — see `_check_every_file_is_claimed`.
CLAIMED_FILES = {
    "metrics": None,  # every *.yaml
    "guardrails": None,  # every *.yaml
    "policies": None,  # every *.yaml
    "vocabularies": frozenset({REASON_CODES.name}),
    "design": frozenset(
        {"aa_harness.yaml", "balance_covariates.yaml", "form.schema.yaml", "inference.yaml"}
    ),
}

#: Families whose numbers the independent provenance walk descends. Originally "numbers
#: that come from outside the repository", which is why `design` was absent; `inference.yaml`
#: made that description too narrow. Its nine values come from *inside* — they are
#: conventions this repository adopts — and every one of them still needs an argument beside
#: it, because a threshold nobody justified is a dial that will be turned. `kind:
#: scenario_assumption` is what carries them, and the walk is what makes it compulsory.
#:
#: The design *form* is still excluded from the walk in the only way that matters: it is a
#: JSON Schema, read by `_check_form` rather than by `validated`, so its `value` keys — which
#: are schema vocabulary and not data — are never descended.
PROVENANCE_FAMILIES = ("guardrails", "policies", "design")


def repo_relative(path: Path, base: Path = REPO_ROOT) -> str:
    """The path as a contract cites itself: relative to whatever contains `contracts/`.

    Relative and not absolute, and relative to the *given* base rather than to a constant.
    A generated artefact names its source contract in its header, so an absolute path would
    make the artefact depend on where the repository happens to sit — the same contract
    would compile to different bytes on a laptop and in CI, and the staleness check would
    fire on a checkout rather than on a drift. It also silently defeated the sandbox in the
    tests, which copied the contracts elsewhere and could only ever see everything as stale.
    """
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(path)


# --------------------------------------------------------------------------- schemas


def _schema_registry(schema_dir: Path) -> Registry:
    registry: Registry = Registry()
    for schema_path in sorted(schema_dir.glob("*.schema.json")):
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return registry


def validator_for(schema_name: str, *, schema_dir: Path = SCHEMA_DIR) -> Draft202012Validator:
    """A validator for one contract schema, with the shared `$defs` resolvable.

    Public because the tests validate deliberately malformed documents, and building a
    bare `Draft202012Validator` there would silently skip every `$ref` into
    `common.schema.json` — a negative test that passed for the wrong reason.
    """
    schema = json.loads((schema_dir / schema_name).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=_schema_registry(schema_dir))


def _validate(
    document: Any,
    schema_name: str,
    *,
    path: Path,
    schema_dir: Path,
    registry: Registry,
    base: Path = REPO_ROOT,
) -> list[Violation]:
    schema = json.loads((schema_dir / schema_name).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, registry=registry)
    violations: list[Violation] = []
    for error in sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path)):
        locator = "/" + "/".join(str(p) for p in error.absolute_path)
        violations.append(
            Violation(
                path=repo_relative(path, base),
                locator=locator,
                rule="schema",
                detail=error.message,
            )
        )
    return violations


# --------------------------------------------------------------------------- scalars


def _as_date(value: Any) -> date:
    return date.fromisoformat(str(value))


def _as_date_or_none(value: Any) -> date | None:
    return None if value is None else _as_date(value)


def _as_decimal(value: Any) -> Decimal:
    """A contract number as an exact `Decimal`, through its text.

    PyYAML has already turned `0.05` into a binary float by the time this sees it. `str()`
    of that float is the shortest decimal string that round-trips to it, which for any
    literal a person actually typed is the literal itself — so the number that reaches the
    arithmetic is the number on disk. `holdout.core.guardrails.envelope` does the same
    thing at its own boundary and for the same reason.
    """
    if isinstance(value, Decimal | int) and not isinstance(value, bool):
        return Decimal(value)
    return Decimal(str(value))


def _provenance(raw: dict[str, Any]) -> Provenance:
    return Provenance(
        kind=raw["kind"],
        verified_on=_as_date(raw["verified_on"]),
        instrument=raw.get("instrument"),
        article=raw.get("article"),
        url=raw.get("url"),
        quote=raw.get("quote"),
        note=raw.get("note"),
        informed_by=raw.get("informed_by"),
    )


# --------------------------------------------------------------------------- families


def _metric(raw: dict[str, Any], path: Path, base: Path) -> Metric:
    restatement = raw.get("restatement")
    return Metric(
        id=raw["id"],
        version=raw["version"],
        effective_from=_as_date(raw["effective_from"]),
        effective_to=_as_date_or_none(raw.get("effective_to")),
        supersedes=raw.get("supersedes"),
        grain=tuple(raw["grain"]),
        unit=raw["unit"],
        rounding=Rounding(mode=raw["rounding"]["mode"], decimals=raw["rounding"]["decimals"]),
        expression=raw["expression"],
        sources=tuple(
            MetricSource(alias=s["alias"], relation=s["relation"], join=s.get("join", "anchor"))
            for s in raw["sources"]
        ),
        description=raw.get("description"),
        why_the_readout_needs_it=raw.get("why_the_readout_needs_it"),
        provenance=_provenance(raw["provenance"]),
        restatement=(
            None
            if restatement is None
            else Restatement(
                from_version=restatement["from_version"],
                reason=restatement["reason"],
                affects_past_values=restatement["affects_past_values"],
            )
        ),
        source_path=repo_relative(path, base),
    )


def _guardrail(raw: dict[str, Any], path: Path, base: Path) -> Guardrail:
    return Guardrail(
        id=raw["id"],
        title=raw["title"],
        applies_to=tuple(raw["applies_to"]),
        description=raw.get("description"),
        safe_state=MappingProxyType(dict(raw.get("safe_state", {}))),
        windows=tuple(
            GuardrailWindow(
                effective_from=_as_date(w["effective_from"]),
                effective_to=_as_date_or_none(w["effective_to"]),
                label=w.get("label"),
                note=w.get("note"),
                rules=tuple(
                    GuardrailRule(
                        id=r["id"],
                        statement=r["statement"],
                        source=_provenance(r["source"]),
                        value=freeze(r.get("value")),
                        unit=r.get("unit"),
                    )
                    for r in w["rules"]
                ),
            )
            for w in raw["windows"]
        ),
        source_path=repo_relative(path, base),
    )


def _policy(raw: dict[str, Any], path: Path, base: Path) -> Policy:
    return Policy(
        id=raw["id"],
        version=raw["version"],
        effective_from=_as_date(raw["effective_from"]),
        effective_to=_as_date_or_none(raw.get("effective_to")),
        supersedes=raw["supersedes"],
        kind=raw["kind"],
        decision_path=raw["decision_path"],
        safe_state=raw["safe_state"],
        marker=raw.get("marker"),
        title=raw.get("title"),
        description=raw.get("description"),
        steps=tuple(
            PolicyStep(
                step=s["step"],
                hours_to_expiry_at_most=s["hours_to_expiry_at_most"],
                depth_pct=s["depth_pct"],
                source=_provenance(s["source"]),
            )
            for s in raw["steps"]
        ),
        floor_behaviour=FloorBehaviour(
            when_step_breaches_floor=raw["floor_behaviour"]["when_step_breaches_floor"],
            statement=raw["floor_behaviour"]["statement"],
        ),
        idempotency_key=tuple(raw.get("idempotency_key", ())),
        source_path=repo_relative(path, base),
    )


def _reason_codes(raw: dict[str, Any]) -> ReasonCodes:
    return ReasonCodes(
        at_decision=tuple(
            ReasonCode(
                code=c["code"],
                meaning=c["meaning"],
                what_would_fix_it=c.get("what_would_fix_it"),
                guardrail=c.get("guardrail"),
            )
            for c in raw["at_decision"]
        ),
        at_design=tuple(
            ReasonCode(
                code=c["code"], meaning=c["meaning"], what_would_fix_it=c.get("what_would_fix_it")
            )
            for c in raw["at_design"]
        ),
        at_readout=tuple(
            ReasonCode(code=c["code"], meaning=c["meaning"], check=c.get("check"))
            for c in raw["at_readout"]
        ),
    )


def _balance_covariates(raw: dict[str, Any]) -> BalanceCovariates:
    return BalanceCovariates(
        version=raw["version"],
        effective_from=_as_date(raw["effective_from"]),
        covariates=tuple(
            Covariate(
                id=c["id"],
                type=c["type"],
                measured=c["measured"],
                description=c["description"],
                lookback_weeks=c.get("lookback_weeks"),
                source_relation=c.get("source_relation"),
            )
            for c in raw["covariates"]
        ),
    )


def _inference(raw: dict[str, Any]) -> InferenceSettings:
    quantiles = raw["quantiles"]
    carryover = raw["carryover"]

    def number(key: str) -> Decimal:
        return _as_decimal(raw[key]["value"])

    def whole(key: str) -> int:
        return int(raw[key]["value"])

    return InferenceSettings(
        version=raw["version"],
        effective_from=_as_date(raw["effective_from"]),
        alpha=number("alpha"),
        target_power=number("target_power"),
        z_two_sided_alpha=_as_decimal(quantiles["z_two_sided_alpha"]["value"]),
        z_one_sided_alpha=_as_decimal(quantiles["z_one_sided_alpha"]["value"]),
        z_power=_as_decimal(quantiles["z_power"]["value"]),
        balance_tolerance_smd=number("balance_tolerance_smd"),
        exposure_min_pct=number("exposure_min_pct"),
        holdout_share_pct=number("holdout_share_pct"),
        neighbour_radius_m=whole("neighbour_radius_m"),
        permutation_draws=whole("permutation_draws"),
        max_assignment_attempts=whole("max_assignment_attempts"),
        carryover=Carryover(
            reference_price_memory=carryover["reference_price_memory"]["value"],
            cross_price_substitution=carryover["cross_price_substitution"]["value"],
            washout_weeks=carryover["washout_weeks"]["value"],
        ),
    )


def _aa_harness(raw: dict[str, Any]) -> AaHarness:
    seeds = raw["seeds"]
    machinery = raw["machinery"]

    def number(key: str) -> Decimal:
        return _as_decimal(raw[key]["value"])

    return AaHarness(
        version=raw["version"],
        effective_from=_as_date(raw["effective_from"]),
        seeds=HarnessSeeds(
            world=int(seeds["world"]["value"]),
            lotteries_per_world_seed=int(seeds["lotteries_per_world_seed"]["value"]),
            pathology_world_seeds=int(seeds["pathology_world_seeds"]["value"]),
            pathology_lotteries_per_world_seed=int(
                seeds["pathology_lotteries_per_world_seed"]["value"]
            ),
            interference_lotteries_per_world_seed=int(
                seeds["interference_lotteries_per_world_seed"]["value"]
            ),
        ),
        binomial_level=number("binomial_level"),
        false_refusal_max_pct=number("false_refusal_max_pct"),
        per_world_min_correct_pct=number("per_world_min_correct_pct"),
        mde_pct_of_pre_period_mean=number("mde_pct_of_pre_period_mean"),
        unit_exposed_min_ack_pct=number("unit_exposed_min_ack_pct"),
        machinery=MachineryConfiguration(
            world_seeds=int(machinery["world_seeds"]["value"]),
            lotteries=int(machinery["lotteries"]["value"]),
            scale=str(machinery["scale"]["value"]),
        ),
    )


# --------------------------------------------------------------------------- the load


def load(contracts_dir: Path | None = None) -> ContractSet:
    """Load, validate and resolve every contract, or raise `ContractError` with all of them."""
    root = Path(contracts_dir) if contracts_dir is not None else CONTRACTS_DIR
    base = root.resolve().parent
    schema_dir = root / "schemas"
    registry = _schema_registry(schema_dir)
    violations: list[Violation] = []
    counted = Census()

    def read(path: Path) -> Any:
        return yaml.load(path.read_text(encoding="utf-8"), Loader=_LiteralLoader)

    def missing(path: Path) -> Violation:
        return Violation(
            path=repo_relative(path, base),
            locator="",
            rule=MISSING_CONTRACT,
            detail=(
                "the loader names this file and it is not on disk. A contract that moved "
                "without its loader is a contract nobody is reading, and the failure is "
                "silent everywhere else: every consumer simply stops seeing it."
            ),
        )

    def validated(
        paths: Iterable[Path], schema_name: str, family: str
    ) -> list[tuple[Path, dict[str, Any]]]:
        kept: list[tuple[Path, dict[str, Any]]] = []
        for path in paths:
            if not path.is_file():
                violations.append(missing(path))
                continue
            raw = read(path)
            errors = _validate(
                raw, schema_name, path=path, schema_dir=schema_dir, registry=registry, base=base
            )
            if family in PROVENANCE_FAMILIES:
                nonlocal counted
                counted += census(raw)
                errors += check_provenance(raw, path=repo_relative(path, base))
            violations.extend(errors)
            if not errors:
                kept.append((path, raw))
        return kept

    metrics = tuple(
        _metric(raw, path, base)
        for path, raw in validated(
            sorted((root / "metrics").glob("*.yaml")), "metric.schema.json", "metrics"
        )
    )
    guardrails = tuple(
        _guardrail(raw, path, base)
        for path, raw in validated(
            sorted((root / "guardrails").glob("*.yaml")), "guardrail.schema.json", "guardrails"
        )
    )
    policies = tuple(
        _policy(raw, path, base)
        for path, raw in validated(
            sorted((root / "policies").glob("*.yaml")), "policy.schema.json", "policies"
        )
    )

    design_dir = root / "design"
    reason_codes_pairs = validated(
        [root / REASON_CODES],
        "reason_codes.schema.json",
        "vocabularies",
    )
    covariate_pairs = validated(
        [design_dir / "balance_covariates.yaml"], "balance_covariates.schema.json", "design"
    )
    inference_pairs = validated([design_dir / "inference.yaml"], "inference.schema.json", "design")
    harness_pairs = validated([design_dir / "aa_harness.yaml"], "aa_harness.schema.json", "design")
    form_path = design_dir / "form.schema.yaml"
    if form_path.is_file():
        form_raw = read(form_path)
        violations.extend(_check_form(form_raw, form_path, base))
    else:
        form_raw = {}
        violations.append(missing(form_path))
    violations.extend(_check_every_file_is_claimed(root, base))

    violations.extend(_check_metric_families(metrics))
    violations.extend(_check_guardrail_windows(guardrails))
    violations.extend(_check_policy_chain(policies, root, base))

    if violations:
        raise ContractError(violations, census=counted)

    return ContractSet(
        metrics=metrics,
        guardrails=guardrails,
        policies=policies,
        reason_codes=_reason_codes(reason_codes_pairs[0][1]),
        balance_covariates=_balance_covariates(covariate_pairs[0][1]),
        inference=_inference(inference_pairs[0][1]),
        aa_harness=_aa_harness(harness_pairs[0][1]),
        design_form=MappingProxyType(form_raw),
        census=counted,
    )


# --------------------------------------------------------------------------- checks


def _check_metric_families(metrics: tuple[Metric, ...]) -> list[Violation]:
    violations: list[Violation] = []
    for metric_id in sorted({m.id for m in metrics}):
        family = sorted((m for m in metrics if m.id == metric_id), key=lambda m: m.version)
        head = family[0]
        for problem in check_timeline(family, what=f"metric {metric_id}"):
            violations.append(
                Violation(path=head.source_path, locator="", rule="timeline", detail=problem)
            )
        present = {m.version: m for m in family}
        for metric in family:
            violations.extend(_check_restatement(metric, present))
            if metric.supersedes is not None and metric.supersedes not in present:
                violations.append(
                    Violation(
                        path=metric.source_path,
                        locator="/supersedes",
                        rule="version_deleted",
                        detail=(
                            f"supersedes v{metric.supersedes}, which is not in contracts/"
                            "metrics/. Every contract is versioned and never deleted — the "
                            "meaning of a closed experiment depends on the version it named "
                            "still being readable."
                        ),
                    )
                )
    for metric in metrics:
        try:
            parse_expression(metric.expression, tuple(s.alias for s in metric.sources))
        except ExpressionError as error:
            violations.append(
                Violation(
                    path=metric.source_path,
                    locator="/expression",
                    rule="expression_grammar",
                    detail=str(error),
                )
            )
        for source in metric.sources[1:]:
            if source.join != "full_outer_on_grain":
                violations.append(
                    Violation(
                        path=metric.source_path,
                        locator="/sources",
                        rule="join_undeclared",
                        detail=(
                            f"source {source.alias!r} is not the anchor and must declare "
                            "`join: full_outer_on_grain`, or a consumer would have to guess "
                            "how it attaches to the grain."
                        ),
                    )
                )
    return violations


def _normalised(expression: str) -> str:
    return " ".join(expression.split())


def _check_restatement(metric: Metric, family: dict[int, Metric]) -> list[Violation]:
    """Contract rule 4 — a change that affects past values implies a restatement.

    Stated in CLAUDE.md, and until now stated only there: `restatement` was a field the
    schema permitted and nothing required. Two things about a metric change the meaning of
    every number already published under it — the arithmetic and the rounding — and both are
    comparable against the predecessor at build time, so the rule is a gate rather than a
    convention.

    Deliberately narrow. It does not ask whether a restatement is *true*, only whether one
    was written when the definition moved. Nobody can compute honesty; anybody can compute
    whether two expressions differ.
    """
    violations: list[Violation] = []

    def bad(rule: str, detail: str, locator: str = "/restatement") -> None:
        violations.append(
            Violation(path=metric.source_path, locator=locator, rule=rule, detail=detail)
        )

    if metric.supersedes is None:
        if metric.restatement is not None:
            bad(
                "restatement_without_predecessor",
                "carries a restatement but supersedes nothing. A restatement is a statement "
                "about numbers already published under an earlier version; with no earlier "
                "version there is nothing to restate.",
            )
        return violations

    predecessor = family.get(metric.supersedes)
    if predecessor is None:
        return violations

    changes: list[str] = []
    if _normalised(metric.expression) != _normalised(predecessor.expression):
        changes.append("the expression")
    if metric.rounding != predecessor.rounding:
        changes.append(
            f"the rounding ({predecessor.rounding.mode}/{predecessor.rounding.decimals} "
            f"to {metric.rounding.mode}/{metric.rounding.decimals})"
        )

    if changes and metric.restatement is None:
        bad(
            "restatement_missing",
            f"changes {' and '.join(changes)} against v{predecessor.version} and carries no "
            "restatement. Every value already stated under the earlier version now has a "
            "different correct value, and doctrine rule 4 says a correction never erases what "
            "was previously stated: the prior value, the reason and the delta must remain "
            "recoverable. Add `restatement` naming the predecessor and what moved.",
        )
    if metric.restatement is not None and metric.restatement.from_version != metric.supersedes:
        bad(
            "restatement_mismatched",
            f"restates from v{metric.restatement.from_version} but supersedes "
            f"v{metric.supersedes}. A restatement that names the wrong predecessor points a "
            "reader at the wrong prior number.",
        )
    return violations


def _check_guardrail_windows(guardrails: tuple[Guardrail, ...]) -> list[Violation]:
    violations: list[Violation] = []
    for guardrail in guardrails:
        for problem in check_timeline(guardrail.windows, what=f"guardrail {guardrail.id}"):
            violations.append(
                Violation(
                    path=guardrail.source_path, locator="/windows", rule="timeline", detail=problem
                )
            )
    return violations


def _check_policy_chain(policies: tuple[Policy, ...], root: Path, base: Path) -> list[Violation]:
    """Every policy version named anywhere must still be on disk.

    Deleting `ladder_policy@v3` does not only lose a file: it makes the result of every
    experiment that named it as its control retroactively uninterpretable, because nobody
    can say afterwards what the control actually did.
    """
    violations: list[Violation] = []
    on_disk = {p.ref for p in policies}
    for policy in policies:
        if policy.supersedes is not None and policy.supersedes not in on_disk:
            violations.append(
                Violation(
                    path=policy.source_path,
                    locator="/supersedes",
                    rule="version_deleted",
                    detail=(
                        f"supersedes {policy.supersedes!r}, which is not in contracts/"
                        f"policies/ (found: {sorted(on_disk)}). No policy version is ever "
                        "deleted; the meaning of last year's experiment depends on exactly "
                        "what its control was."
                    ),
                )
            )
    for referenced, where in _referenced_policy_refs(root, base):
        if referenced not in on_disk:
            violations.append(
                Violation(
                    path=where,
                    locator="",
                    rule="version_deleted",
                    detail=(
                        f"references policy {referenced!r}, which is not in "
                        f"contracts/policies/ (found: {sorted(on_disk)})."
                    ),
                )
            )
    for policy_id in sorted({p.id for p in policies}):
        family = [p for p in policies if p.id == policy_id]
        head = min(family, key=lambda p: p.version)
        for problem in check_timeline(family, what=f"policy {policy_id}"):
            violations.append(
                Violation(path=head.source_path, locator="", rule="timeline", detail=problem)
            )
    return violations


_POLICY_REF = "@v"


def _referenced_policy_refs(root: Path, base: Path) -> list[tuple[str, str]]:
    """Every `<id>@v<n>` mentioned in a committed experiment design."""
    import re

    pattern = re.compile(r"\b([a-z][a-z0-9_]*@v[0-9]+)\b")
    found: list[tuple[str, str]] = []
    experiments = root.parent / "experiments"
    if not experiments.is_dir():
        return found
    for path in sorted(experiments.rglob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            found.append((match.group(1), repo_relative(path, base)))
    return found


def _check_form(form: Any, path: Path, base: Path = REPO_ROOT) -> list[Violation]:
    """The design form is a schema, so it is checked structurally rather than against one."""
    violations: list[Violation] = []
    rel = repo_relative(path, base)

    def bad(locator: str, rule: str, detail: str) -> None:
        violations.append(Violation(path=rel, locator=locator, rule=rule, detail=detail))

    if not isinstance(form, dict):
        bad("", "form", "the design form must be a mapping")
        return violations

    Draft202012Validator.check_schema(form)

    declared = form.get("x-design-fields")
    if not isinstance(declared, list) or len(declared) != 9:
        bad(
            "/x-design-fields",
            "form",
            "the form has nine fields. `x-design-fields` must name exactly nine, so that "
            "adding a tenth is a visible change rather than a quiet one.",
        )
        return violations

    properties = set(form.get("properties", {}))
    expected = set(declared) | {"filled_by"}
    if properties != expected:
        bad(
            "/properties",
            "form",
            f"properties {sorted(properties)} do not match the nine design fields plus "
            f"`filled_by` ({sorted(expected)}). `filled_by` is attribution, not a field, "
            "which is why it is counted separately.",
        )
    if set(form.get("required", [])) != expected:
        bad(
            "/required",
            "form",
            "every design field and `filled_by` is required. An optional field is a field "
            "that will be left empty exactly when it matters.",
        )
    for field in declared:
        spec = form.get("properties", {}).get(field, {})
        if not spec.get("description"):
            bad(f"/properties/{field}", "form", "every design field carries a description")
    return violations


def _check_every_file_is_claimed(root: Path, base: Path) -> list[Violation]:
    """No YAML under `contracts/` that nothing reads.

    The contract-side twin of the `orphan_artefact` check that already guards `generated/`,
    and it exists for a specific failure: a contract that is *moved* leaves a copy at the
    old address whenever the move is done with `cp` rather than `git mv`, or whenever a
    later merge resurrects one. The loader would go on reading the new address and nobody
    would ever be told that a second, stale, fully-valid-looking copy of the source of
    truth is sitting in the repository being read by human beings.

    It is also what makes a *rename* a build failure rather than a silent skip: a file the
    loader no longer names is unclaimed, and unclaimed is red.
    """
    violations: list[Violation] = []
    for path in sorted(root.rglob("*.yaml")):
        family = path.parent.name
        if family not in CLAIMED_FILES:
            violations.append(
                Violation(
                    path=repo_relative(path, base),
                    locator="",
                    rule=UNCLAIMED_CONTRACT,
                    detail=(
                        f"{family!r} is not a contract family this loader reads, so nothing "
                        f"in it reaches any consumer. Known families: "
                        f"{sorted(CLAIMED_FILES)}."
                    ),
                )
            )
            continue
        allowed = CLAIMED_FILES[family]
        if allowed is not None and path.name not in allowed:
            violations.append(
                Violation(
                    path=repo_relative(path, base),
                    locator="",
                    rule=UNCLAIMED_CONTRACT,
                    detail=(
                        f"nothing reads this file. contracts/{family}/ is read by name and "
                        f"the loader names {sorted(allowed)}. Either it was left behind by "
                        "a move — a stale copy of a source of truth is worse than no copy — "
                        "or it is new and the loader was never taught about it."
                    ),
                )
            )
    return violations
