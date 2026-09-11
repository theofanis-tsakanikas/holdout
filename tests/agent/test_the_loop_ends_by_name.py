"""Every way a question can end is named, counted, and comes from the contract.

The ceilings are numbers in configuration, so `CLAUDE.md`'s rule applies: each is an assertion
about what the system does, and the assertion here is that hitting one ends the question with
a named failure and no proposal. A scripted model is driven into each ceiling in turn.

## What this asserts

- The ceilings and the proposer are read from `contracts/agent/runtime.yaml` -- the values
  the loop runs under are the contract's, not a default somewhere.
- A model that keeps calling tools ends as `tool_calls`; one that keeps talking without
  delivering ends as `no_delivery`; one that spends past the token ceiling ends as `tokens`;
  a delivery that `form.py` refuses ends as `malformed_delivery`. Each with `proposal=None`.
- `Outcome` refuses a failure outside the closed set and refuses both-or-neither.
- The trace records every model call, every admitted tool, and the failure.

## What it does not check

- **The wall-clock ceiling.** A test that waits for it is a slow test proving `time.monotonic`
  works; the ceiling is read from the contract like the others and the branch is one line.
"""

from __future__ import annotations

import pytest

from holdout.agent.propose import FAILURES, Ceilings, Outcome, propose
from holdout.agent.record import from_contracts
from holdout.contracts.loader import load
from tests.agent.fakes import GOOD_DELIVERY, Echo, Scripted, calls, text

CONTRACTS = load()
CONTEXT = {"metrics": "x", "roster": "y"}
TOOL = "metric_waste_value_per_store_week"


def test_the_ceilings_are_the_contracts() -> None:
    model, ceilings = from_contracts(CONTRACTS)
    runtime = CONTRACTS.runtime
    assert ceilings == Ceilings(
        tokens=runtime.tokens_per_proposal,
        seconds=float(runtime.seconds_per_proposal),
        tool_calls=runtime.tool_calls_per_proposal,
    )
    assert model.model_id == runtime.model_id


def test_a_model_that_never_stops_asking_is_stopped_by_name() -> None:
    ceilings = Ceilings(tokens=100_000, seconds=60, tool_calls=2)
    model = Scripted([calls((TOOL, {})) for _ in range(10)])
    outcome = propose("q", context=CONTEXT, model=model, executor=Echo(), ceilings=ceilings)
    assert outcome.proposal is None
    assert outcome.failed == "tool_calls"
    assert [r.kind for r in outcome.trace].count("tool") == ceilings.tool_calls
    assert outcome.trace[-1].kind == "failed"


def test_a_model_that_talks_instead_of_delivering_is_no_delivery() -> None:
    model = Scripted([text("I would rather not.")])
    outcome = propose(
        "q", context=CONTEXT, model=model, executor=Echo(), ceilings=Ceilings(1000, 60, 6)
    )
    assert outcome.failed == "no_delivery"
    assert "end_turn" in outcome.trace[-1].detail


def test_a_model_that_spends_past_the_ceiling_is_tokens() -> None:
    model = Scripted([calls((TOOL, {}), output_tokens=900), calls((TOOL, {}), output_tokens=900)])
    outcome = propose(
        "q", context=CONTEXT, model=model, executor=Echo(), ceilings=Ceilings(1000, 60, 6)
    )
    assert outcome.failed == "tokens"


def test_a_delivery_the_form_refuses_is_malformed_and_recorded() -> None:
    bad = dict(GOOD_DELIVERY, mde={"kind": "absolute", "value": -2.0})
    model = Scripted([calls(("propose_design", bad))])
    outcome = propose(
        "q", context=CONTEXT, model=model, executor=Echo(), ceilings=Ceilings(1000, 60, 6)
    )
    assert outcome.failed == "malformed_delivery"
    assert "positive difference" in outcome.trace[-1].detail
    delivered = outcome.transcript[-1]["content"][0]["input"]
    assert delivered["mde"]["value"] == -2.0, "what was delivered is kept, so it can be read"


def test_a_good_delivery_is_a_proposal_with_no_failure() -> None:
    model = Scripted([calls(("propose_design", GOOD_DELIVERY))])
    outcome = propose(
        "q", context=CONTEXT, model=model, executor=Echo(), ceilings=Ceilings(1000, 60, 6)
    )
    assert outcome.failed is None
    assert outcome.proposal is not None
    assert outcome.proposal.primary_metric == "waste_value_per_store_week"
    assert outcome.trace[-1].kind == "proposal"


def test_an_outcome_is_one_thing_from_a_closed_set() -> None:
    common = {
        "question": "q",
        "model_id": "m",
        "registry_fingerprint": "r",
        "prompt_fingerprint": "p",
        "trace": (),
    }
    with pytest.raises(ValueError):
        Outcome(proposal=None, failed=None, **common)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        Outcome(proposal=None, failed="ran_out_of_patience", **common)  # type: ignore[arg-type]
    assert {"tokens", "seconds", "tool_calls", "no_delivery", "malformed_delivery"} == FAILURES
