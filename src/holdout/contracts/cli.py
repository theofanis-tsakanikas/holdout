"""`make contracts`.

Validates every contract against its schema, recompiles every consumer, and goes red when
a generated artefact is stale or when a `value` has no `source`. It is not enough that the
definition exists — it must be provable that everyone is using it, now.

Three subcommands:

    check     validate, recompile in memory, refuse if disk differs   (what CI runs)
    compile   validate, then write the artefacts                      (what an author runs)
    validate  validate only

`check` never writes. A build step that repairs the thing it is checking cannot fail, and a
check that cannot fail is not a gate.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from holdout.contracts.compilers import compile_all, in_force_metrics
from holdout.contracts.errors import CompilationError, ContractError, Violation
from holdout.contracts.loader import CONTRACTS_DIR, REPO_ROOT, load
from holdout.contracts.model import ContractSet
from holdout.contracts.provenance import Census

COMPILE = "not_compilable"
STALE = "stale_artefact"
MISSING = "missing_artefact"
ORPHAN = "orphan_artefact"


def _provenance_line(counted: Census) -> str:
    """The one line in this build destined for a terminal screenshot.

    The denominator is every `value` the walk found, not every source it found — the earlier
    version divided a count by itself and could only ever print 100%. It is printed on a red
    build too, from the census carried on the failure, so the ratio can report bad news.
    """
    return (
        f"provenance   {counted.sourced}/{counted.values} values carry a source"
        f" · {counted.legal} legal instrument · {counted.scenario} scenario assumption"
    )


def _artefact_violations(expected: dict[str, str], root: Path) -> list[Violation]:
    violations: list[Violation] = []
    for rel, content in sorted(expected.items()):
        path = root / rel
        if not path.exists():
            violations.append(
                Violation(
                    path=rel,
                    locator="",
                    rule=MISSING,
                    detail=(
                        "the contract compiles into this artefact and it is not on disk. "
                        "Run `make contracts-write`."
                    ),
                )
            )
            continue
        on_disk = path.read_text(encoding="utf-8")
        if on_disk != content:
            violations.append(
                Violation(
                    path=rel,
                    locator="",
                    rule=STALE,
                    detail=(
                        "what is on disk is not what the contract compiles to. Either the "
                        "contract changed and this was not regenerated, or this file was "
                        "edited by hand — and a hand-edited consumer is a second definition, "
                        "which is the one thing the contract layer exists to prevent. Run "
                        "`make contracts-write`."
                    ),
                )
            )
    known = set(expected)
    generated_root = root / "generated"
    if generated_root.is_dir():
        for path in sorted(generated_root.rglob("*")):
            if not path.is_file():
                continue
            rel = str(path.relative_to(root))
            if rel not in known:
                violations.append(
                    Violation(
                        path=rel,
                        locator="",
                        rule=ORPHAN,
                        detail=(
                            "no contract compiles to this file. It is either left over from a "
                            "contract that was removed, or it was written by hand — and a "
                            "hand-written file under generated/ will be read as generated."
                        ),
                    )
                )
    return violations


def _write(expected: dict[str, str], root: Path) -> list[str]:
    changed: list[str] = []
    for rel, content in sorted(expected.items()):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            path.write_text(content, encoding="utf-8")
            changed.append(rel)
    return changed


def _summary(contracts: ContractSet, expected: dict[str, str]) -> list[str]:
    in_force = in_force_metrics(contracts)
    return [
        f"contracts    metrics {len(contracts.metrics)}"
        f" ({len(in_force)} in force, {len(contracts.metrics) - len(in_force)} superseded"
        f" and kept)"
        f" · guardrails {len(contracts.guardrails)}"
        f" · policies {len(contracts.policies)}",
        f"vocabularies reason codes {len(contracts.reason_codes.all_codes)}"
        f" ({len(contracts.reason_codes.at_decision)} at decision,"
        f" {len(contracts.reason_codes.at_design)} at design,"
        f" {len(contracts.reason_codes.at_readout)} at readout)"
        f" · balance covariates {len(contracts.balance_covariates.covariates)}",
        # The inference settings compile to nothing — no consumer is generated from them —
        # so this line is the only place the build says out loud that they were read at
        # all. A contract validated by nobody's eye and consumed by no artefact is one
        # nobody would notice going missing.
        f"inference    alpha {contracts.inference.alpha}"
        f" · power {contracts.inference.target_power}"
        f" · holdout {contracts.inference.holdout_share_pct}%"
        f" · exposure floor {contracts.inference.exposure_min_pct}%"
        f" · SMD tolerance {contracts.inference.balance_tolerance_smd}"
        f" · B {contracts.inference.permutation_draws}",
        # And the same argument for the harness's own contract, which compiles to nothing
        # either. It is printed on its own line rather than folded into the one above,
        # because the whole reason the two files are separate is that one is what the core
        # reads and the other is what the eval reads.
        f"aa harness   K {contracts.aa_harness.seeds.draws}"
        f" ({contracts.aa_harness.seeds.world} world seed(s)"
        f" x {contracts.aa_harness.seeds.lotteries_per_world_seed} lotteries)"
        f" · binomial at {contracts.aa_harness.binomial_level}"
        f" · MDE {contracts.aa_harness.mde_pct_of_pre_period_mean}% of the pre-period mean"
        f" · machinery at {contracts.aa_harness.machinery.scale}",
        # And the third contract that compiles to nothing, for the same reason as the two
        # above. Its own line rather than a fold, because `ml` is a family and not a section
        # of `design/`: nothing in `pipelines/ml/` is the engine that decides whether an
        # experiment may exist, and a file printed under the wrong heading is a file read by
        # the wrong consumer one session later.
        f"training     evaluation {contracts.training.evaluation_days}d"
        f" · min train {contracts.training.min_training_days}d"
        f" · reconstruction floor {contracts.training.min_observed_share}"
        f" · calibration {contracts.training.calibration_tolerance_pct}%"
        f" (per-segment family alarm {contracts.training.segment_family_false_alarm_rate}"
        f" above {contracts.training.min_segment_days} day(s))"
        f" · RMSE ≤ {contracts.training.rmse_share_of_baseline} of baseline",
        _provenance_line(contracts.census),
        f"generated    {len(expected)} artefact(s) from {len(in_force)} metric(s)"
        f" and the design form",
    ]


def _fail(violations: list[Violation], counted: Census | None = None) -> int:
    if counted is not None and counted.values:
        print(_provenance_line(counted), file=sys.stderr)
    print("", file=sys.stderr)
    for violation in violations:
        print(str(violation), file=sys.stderr)
    print("", file=sys.stderr)
    print(f"FAILED  {len(violations)} contract violation(s)", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="holdout-contracts", description=__doc__)
    parser.add_argument(
        "command", choices=["check", "compile", "validate"], nargs="?", default="check"
    )
    parser.add_argument("--contracts", type=Path, default=CONTRACTS_DIR)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)

    try:
        contracts = load(args.contracts)
    except ContractError as error:
        counted = error.census
        return _fail(error.violations, counted if isinstance(counted, Census) else None)

    try:
        expected: dict[str, Any] = compile_all(contracts)
    except CompilationError as error:
        return _fail(
            [
                Violation(
                    path=error.source_path,
                    locator=error.locator,
                    rule=COMPILE,
                    detail=str(error),
                )
            ],
            contracts.census if isinstance(contracts.census, Census) else None,
        )

    if args.command == "validate":
        for line in _summary(contracts, expected):
            print(line)
        print("\nOK      every contract validates")
        return 0

    if args.command == "compile":
        changed = _write(expected, args.root)
        for line in _summary(contracts, expected):
            print(line)
        if changed:
            print("\nwrote:")
            for rel in changed:
                print(f"  {rel}")
        print(f"\nOK      {len(changed)} artefact(s) rewritten, {len(expected)} total")
        return 0

    violations = _artefact_violations(expected, args.root)
    if violations:
        return _fail(violations)
    for line in _summary(contracts, expected):
        print(line)
    # Two numbers from two places: what the contracts compile to, and what is on disk. The
    # earlier line printed `len(expected)` over itself — a ratio that could only ever read
    # 100%, which is the same defect a previous review removed from the provenance line.
    on_disk = sum(1 for path in (args.root / "generated").rglob("*") if path.is_file())
    print(
        f"\nOK      {len(expected)} artefact(s) compiled from contracts · "
        f"{on_disk} file(s) under generated/ · every byte matches"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
