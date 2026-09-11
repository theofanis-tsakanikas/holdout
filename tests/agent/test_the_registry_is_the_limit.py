"""The agent may call exactly the compiled tools, and a call outside them is refused by name.

`T025`'s `stop_at`: *a call planted outside the registry being refused by name, not by the
agent declining to make one. A confinement that depends on the model behaving is not a
confinement.* So the case here is a scripted model that **does** make the call -- `run_sql`,
the tool every agent wants -- and what is asserted is what happened to it: refused, traced
under its own name, and answered to the model as an error rather than executed.

## What this asserts

- The registry is exactly what `holdout.contracts.compilers.compile_all` emits under
  `generated/agent_tools/`: same names, same definitions. Not a copy -- the compilation.
- A call to a name the registry lacks raises `ToolNotInRegistryError` naming it.
- Inside the loop, that refusal is a `refused_tool` trace row, the executor never sees it,
  and the model is told it was an error.
- The fingerprint moves when a definition moves and not when a file's header does.

**Measured biting, 2026-09-11:** the loop edited to look the name up directly and build a
`Tool` for whatever it did not find -- the shape a hurried refactor produces -- and
`test_the_loop_refuses_the_planted_call_and_never_executes_it` went red; restored, green.

## What it does not check

- **That the model cannot be talked into anything else.** It cannot: there is nothing else.
  A registry gate proves the set is closed; that `admit` is the only door is what the
  mutation above measured, and a second dispatch path added later is what it would catch.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from holdout.agent import registry as reg
from holdout.agent.propose import Ceilings, propose
from holdout.contracts.compilers import compile_all
from holdout.contracts.loader import load
from tests.agent.fakes import GOOD_DELIVERY, Echo, Scripted, calls

CONTRACTS = load()
CEILINGS = Ceilings(tokens=10_000, seconds=60, tool_calls=6)


def test_there_are_tools_to_confine_the_agent_to() -> None:
    """An empty registry passes every assertion below and confines nothing."""
    assert reg.registry(), "generated/agent_tools/ holds no tool; the registry is empty"


def test_the_registry_is_the_compilation_and_not_a_copy() -> None:
    compiled = {
        path: content
        for path, content in compile_all(CONTRACTS).items()
        if path.startswith("generated/agent_tools/")
    }
    assert compiled, "compile_all emits no agent tool; claim 5's third mechanism is gone"
    expected = {
        json.loads(content)["name"]: {
            "name": json.loads(content)["name"],
            "description": json.loads(content)["description"],
            "input_schema": json.loads(content)["input_schema"],
        }
        for content in compiled.values()
    }
    actual = {name: tool.definition() for name, tool in reg.registry().items()}
    assert actual == expected, (
        "the registry the agent is shown differs from what the contract compiles. "
        f"registry={sorted(actual)} compiled={sorted(expected)}"
    )


def test_a_call_outside_the_registry_is_refused_by_name() -> None:
    with pytest.raises(reg.ToolNotInRegistryError) as refused:
        reg.admit("run_sql")
    assert "'run_sql'" in str(refused.value)
    for name in reg.registry():
        assert name in str(refused.value), "the refusal names what exists, so nobody guesses"


def test_the_loop_refuses_the_planted_call_and_never_executes_it() -> None:
    """The model asks for `run_sql`, then delivers. The executor must not have run it."""

    ran: list[str] = []

    class Counting(Echo):
        def run(self, tool: reg.Tool, arguments: dict[str, object]) -> str:
            ran.append(tool.name)
            return super().run(tool, arguments)

    executor = Counting()
    model = Scripted(
        [
            calls(("run_sql", {"query": "select * from gold.readout"})),
            calls(("propose_design", GOOD_DELIVERY)),
        ]
    )
    outcome = propose("q", context={"a": "b"}, model=model, executor=executor, ceilings=CEILINGS)

    refused = [row for row in outcome.trace if row.kind == "refused_tool"]
    assert [row.name for row in refused] == ["run_sql"], "the refusal is traced under its own name"
    assert ran == [], "the planted call reached the executor"
    assert outcome.proposal is not None

    answered = model.seen[1]["messages"][-1]["content"]
    assert answered[0]["is_error"] is True, "the model is told the call was refused"
    assert "run_sql" in answered[0]["content"]


def test_the_fingerprint_follows_the_definition_and_not_the_file(tmp_path: Path) -> None:
    source = reg.TOOLS_DIR
    copy = tmp_path / "tools"
    copy.mkdir()
    for path in source.glob("*.json"):
        (copy / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    before = reg.fingerprint(reg.registry(copy))

    first = sorted(copy.glob("*.json"))[0]
    document = json.loads(first.read_text(encoding="utf-8"))
    document["$comment"] = "a regenerated header, which the model never sees"
    first.write_text(json.dumps(document), encoding="utf-8")
    assert reg.fingerprint(reg.registry(copy)) == before, "a header moved the fingerprint"

    document["description"] = document["description"] + " Now says something else."
    first.write_text(json.dumps(document), encoding="utf-8")
    assert reg.fingerprint(reg.registry(copy)) != before, "a changed description did not move it"
