"""A recording: every question asked, every answer given, and enough to know who gave it.

Claim 6 grades a recording rather than a live call, and `PLAN.md` argues why: a required check
that calls a paid, non-deterministic third party on every push is a check that goes red when
a vendor retires a model, spends money proving what was proved, and cannot be reproduced. So
the model is called **deliberately**, by this module, and what it produced is written down once
with everything needed to grade it later and nothing that would let it be graded differently.

What makes a recording honest rather than a fixture in a costume
----------------------------------------------------------------
Three properties, each written into `manifest.json` and each checked by the eval that reads it:

* **Every question is recorded, in the order asked.** A recording is not a selection. Nothing
  here filters an outcome, and the manifest carries the count so a directory with one file
  fewer than it claims is a directory somebody edited.
* **The agent that answered is fingerprinted.** The registry as the model saw it, the prompt
  and the delivery tool as the model saw them, the model id and the contract version. The eval
  recomputes the fingerprints from the tree and refuses a recording whose agent is not the one
  in the tree — `STALE`, the same word `gate-proof` uses for a mutation whose target moved.
* **The recording is digested.** One hash over every outcome file, so an edited proposal is an
  edited digest.

What is deliberately not here
-----------------------------
No verdict. The engine's answer about a proposal is computed by the eval on every run, from the
proposal and the contracts as they stand, never read back from disk. A recording that carried
its own refusals would be the eval agreeing with a file.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from holdout.agent.client import BedrockModel, Model
from holdout.agent.propose import Ceilings, Executor, Outcome, propose
from holdout.contracts.model import ContractSet

MANIFEST = "manifest.json"


@dataclass(frozen=True, slots=True)
class Recorded:
    """Where a recording landed and what it holds, for the caller's report."""

    directory: Path
    questions: int
    proposals: int
    failed: int
    digest: str


def from_contracts(contracts: ContractSet) -> tuple[Model, Ceilings]:
    """The proposer and the ceilings, read from `contracts/agent/runtime.yaml` and nowhere else."""
    runtime = contracts.runtime
    model = BedrockModel(
        model_id=runtime.model_id,
        region=runtime.region,
        legacy_endpoint=runtime.legacy_endpoint,
        thinking=None if runtime.legacy_endpoint else {"type": "adaptive"},
    )
    ceilings = Ceilings(
        tokens=runtime.tokens_per_proposal,
        seconds=float(runtime.seconds_per_proposal),
        tool_calls=runtime.tool_calls_per_proposal,
    )
    return model, ceilings


def record(
    questions: list[str],
    *,
    context: dict[str, str],
    contracts: ContractSet,
    executor: Executor,
    out: Path,
    recorded_on: date | None = None,
) -> Recorded:
    """Ask every question, write every outcome, and seal the directory with a digest."""
    if not questions:
        raise ValueError("a recording of no questions records nothing and proves nothing")
    model, ceilings = from_contracts(contracts)
    out.mkdir(parents=True, exist_ok=False)

    outcomes: list[Outcome] = []
    for index, question in enumerate(questions):
        outcome = propose(
            question, context=context, model=model, executor=executor, ceilings=ceilings
        )
        (out / f"{index:03d}.json").write_text(
            json.dumps(_plain(outcome), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        outcomes.append(outcome)

    digest = digest_of(out)
    proposals = sum(1 for o in outcomes if o.proposal is not None)
    failed = sum(1 for o in outcomes if o.failed is not None)
    manifest: dict[str, Any] = {
        "recorded_on": (recorded_on or datetime.now(UTC).date()).isoformat(),
        "model_id": model.model_id,
        "runtime_contract_version": contracts.runtime.version,
        "registry_fingerprint": outcomes[0].registry_fingerprint,
        "prompt_fingerprint": outcomes[0].prompt_fingerprint,
        "context_entries": list(context),
        "questions": len(outcomes),
        "proposals": proposals,
        "failed": failed,
        "digest": digest,
    }
    (out / MANIFEST).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return Recorded(
        directory=out,
        questions=len(outcomes),
        proposals=proposals,
        failed=failed,
        digest=digest,
    )


def digest_of(directory: Path) -> str:
    """One hash over every outcome file, by name, so an edit anywhere moves it."""
    sha = hashlib.sha256()
    for path in sorted(directory.glob("[0-9][0-9][0-9].json")):
        sha.update(path.name.encode("utf-8"))
        sha.update(path.read_bytes())
    return sha.hexdigest()


def _plain(outcome: Outcome) -> dict[str, Any]:
    """An outcome as JSON, with the proposal in the form's own field names.

    `Decimal` becomes a string, never a float: the MDE was declared as a decimal and a float
    written here would be a second rounding nobody declared.
    """
    proposal: dict[str, Any] | None = None
    if outcome.proposal is not None:
        p = outcome.proposal
        proposal = {
            "hypothesis": p.hypothesis,
            "intervention": {
                "treatment": p.intervention.treatment,
                "control": p.intervention.control,
            },
            "scope": {
                "categories": list(p.scope.categories),
                "products": None if p.scope.products is None else list(p.scope.products),
                "stores": None if p.scope.stores is None else list(p.scope.stores),
            },
            "primary_metric": p.primary_metric,
            "unit": p.unit.value,
            "mde": {
                "kind": p.mde.kind.value,
                "value": str(p.mde.value),
                "direction": p.mde.direction.value,
            },
            "exclusions": [{"store_id": e.store_id, "reason": e.reason} for e in p.exclusions],
        }
    return {
        "question": outcome.question,
        "model_id": outcome.model_id,
        "registry_fingerprint": outcome.registry_fingerprint,
        "prompt_fingerprint": outcome.prompt_fingerprint,
        "proposal": proposal,
        "failed": outcome.failed,
        "trace": [asdict(row) for row in outcome.trace],
        "transcript": list(outcome.transcript),
    }
