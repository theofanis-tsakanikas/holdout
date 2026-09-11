"""The tools the agent may call, which is the whole of what it may do.

**The registry is the limit, not the prompt.** An instruction not to write SQL is a request; a
registry with no SQL tool in it is a property of the system. What the agent can reach is
exactly the compiled metric tools under `generated/agent_tools/` — one per metric in the
contract, each one a closed input schema with no expression field — and nothing else. There
is no catalog browse and no free-text query, so **a question the registry cannot express is a
question the agent cannot ask**, whatever it is willing to try.

Why the compiled artefact and not the contract
----------------------------------------------
`generated/agent_tools/*.json` is what `holdout.contracts.compilers.agent_tool` emits and what
`make contracts` byte-compares on every run. Reading the compiled file is reading the contract
through the one consumer the gate already guarantees; loading the contract here and building
the definitions a second time would be the second definition rule 3 of the contract layer
exists to refuse. It is also what a deployed runtime does, which is why it is not a
convenience: the agent needs no contract loader to run.

The digest is the point of `fingerprint()`
------------------------------------------
Claim 6 grades a recorded generation rather than a live call, for reasons argued in
`evals/design/`. That is only honest while the recording is provably from the agent that is in
the tree — so a run records this fingerprint, and the eval recomputes it. A registry that
gained a tool after the proposals were recorded makes the recording stale, loudly, in the same
way `make contracts` refuses a stale artefact and `gate-proof` reports a mutation whose target
has moved.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = REPO_ROOT / "generated" / "agent_tools"


class ToolNotInRegistryError(LookupError):
    """A call to something the agent was never given.

    Raised rather than answered, and it names what was asked for and what exists. The
    alternative — returning an error string the model can read — teaches a model to retry
    variations, which is the behaviour a registry exists to make pointless.
    """


@dataclass(frozen=True, slots=True)
class Tool:
    """One callable, as the model is shown it."""

    name: str
    description: str
    input_schema: dict[str, Any]

    def definition(self) -> dict[str, Any]:
        """The shape a model API takes. Nothing here is agent-specific to one vendor."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


def registry(tools_dir: Path | None = None) -> dict[str, Tool]:
    """Every tool the agent has, keyed by name, read from the compiled artefacts."""
    directory = tools_dir if tools_dir is not None else TOOLS_DIR
    found: dict[str, Tool] = {}
    for path in sorted(directory.glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        tool = Tool(
            name=document["name"],
            description=document["description"],
            input_schema=document["input_schema"],
        )
        if tool.name in found:
            raise ToolNotInRegistryError(
                f"two compiled artefacts both declare the tool {tool.name!r}. A registry with "
                "a duplicate name has no single answer to what a call reaches."
            )
        found[tool.name] = tool
    return found


def admit(name: str, tools: dict[str, Tool] | None = None) -> Tool:
    """The one door a call goes through.

    Every path that executes a tool call goes through this function, so the refusal cannot be
    forgotten by a caller that builds its own dispatch table.
    """
    available = registry() if tools is None else tools
    if name not in available:
        raise ToolNotInRegistryError(
            f"{name!r} is not a tool this agent has. It has "
            f"{sorted(available) if available else 'none'}. The registry is compiled from the "
            "metric contract and is the whole of what the agent may reach; a question it "
            "cannot express is a question that does not get asked."
        )
    return available[name]


def fingerprint(tools: dict[str, Tool] | None = None) -> str:
    """A digest over the registry as the model is shown it.

    Taken over the definitions rather than over the files, so a comment or a regenerated
    header does not move it and a changed description does. A description is part of what the
    model was told, and a proposal made against different instructions is a proposal from a
    different agent.
    """
    available = registry() if tools is None else tools
    canonical = json.dumps(
        [available[name].definition() for name in sorted(available)],
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
