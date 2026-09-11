"""The loop: a business question in, a `ProposedDesign` or a named non-answer out.

What the model is asked to do, in one sentence: fill the judgment fields of an experiment
design that would answer a business question, using only the context it is shown and the tools
it is given. What it may not do is enforced by shape rather than by instruction — the design
is delivered by calling a tool whose schema is the form with the two forbidden fields removed,
so a proposal that fills `decision_rule` is not a disobedient proposal, it is a malformed tool
call the API refuses before this module sees it.

Three ceilings, and what hitting one means
-------------------------------------------
A proposal has a token ceiling, a wall-clock ceiling and a tool-call ceiling, all declared in
`contracts/agent/runtime.yaml` with a source beside each. Hitting one produces **no proposal**
and a named exhaustion rather than a truncated design: a truncated form is a design nobody
wrote that still parses, and it would be counted under N as though somebody had proposed it.
An exhaustion is not a refusal either — the closed vocabulary's `at_design` codes are answers
about designs, and there is no design here to answer about. It is its own outcome, recorded
as such, so claim 6's three numbers are counted over proposals that exist.

Every tool call goes through `registry.admit`
---------------------------------------------
Including the one that delivers the proposal. There is no dispatch table in this file that
could grow a case `admit` does not know about; a name the registry has not heard of raises
before anything is executed, and the trace records the attempt by name.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol

from holdout.agent.client import Model
from holdout.agent.proposal import ProposalError, ProposedDesign
from holdout.agent.registry import Tool, ToolNotInRegistryError, admit, fingerprint, registry
from holdout.core.design.form import (
    DesignFormError,
    Exclusion,
    Intervention,
    Mde,
    MdeDirection,
    MdeKind,
    Scope,
    Unit,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
FORM_SCHEMA = REPO_ROOT / "generated" / "design" / "form.schema.json"

PROPOSE = "propose_design"

#: The second and last turn a question gets when the first ended in prose. Part of what the
#: model is told, so part of the prompt fingerprint.
NUDGE = (
    f"That analysis is not an answer. Either call `{PROPOSE}` now with the design you have "
    "reasoned your way to -- a design you expect to be refused is still a design, and the "
    "refusal is the system's to give -- or say in one line that no design can be expressed "
    "for this question and why."
)

#: Attribution rather than a field, stamped by `complete()`, and so never in the delivery tool.
ATTRIBUTION = "filled_by"


def not_the_agents(form: dict[str, Any]) -> frozenset[str]:
    """The fields the agent never fills, read from the form rather than typed here.

    `contracts/design/form.schema.yaml` marks them with `x-never-filled-by: [agent]`, and the
    marker survives compilation. A set written out in this file would be a second definition
    of that marker -- correct today, and silently wrong the day the contract moved it.
    """
    return frozenset(
        name
        for name, spec in form["properties"].items()
        if "agent" in spec.get("x-never-filled-by", [])
    ) | {ATTRIBUTION}


#: JSON Schema keywords the tool API refuses, found by sending the compiled form and reading the
#: 400 -- `tools.3.custom: For 'array' type, property 'uniqueItems' is not supported` -- rather
#: than by guessing at the subset. **Removing a keyword here weakens nothing that is checked**:
#: every constraint the tool schema drops is re-imposed by `parse()` and by `form.py`'s own
#: invariants, so a model that hands over a duplicated exclusion is refused a step later, by
#: name, instead of at the API. What it does cost is one round trip. The list is printed by the
#: test that asserts the derivation, so a keyword added here without a reason is visible.
UNSUPPORTED_BY_TOOLS: frozenset[str] = frozenset({"uniqueItems", "exclusiveMinimum"})


class Executor(Protocol):
    """Runs a metric tool the registry admitted, and returns what the model is shown."""

    def run(self, tool: Tool, arguments: dict[str, Any]) -> str: ...


@dataclass(frozen=True, slots=True)
class Ceilings:
    tokens: int
    seconds: float
    tool_calls: int


@dataclass(frozen=True, slots=True)
class TraceRow:
    """One thing that happened, in order. `kind` is one of a closed set of five."""

    step: int
    kind: str  # model | tool | proposal | refused_tool | nudge | failed
    name: str
    input_tokens: int = 0
    output_tokens: int = 0
    elapsed_s: float = 0.0
    detail: str = ""


#: The ways a question ends without a proposal, closed so a recording can be counted over them.
#: None of these is a design refusal: a refusal is the engine's answer about a design, and in
#: every case here there is no design to answer about. `malformed_delivery` is the one that a
#: real model produces most -- a negative MDE, with the sign carrying the direction the form
#: keeps in its own field -- and it is refused by `form.py` by name, which is the seam this
#: package inherits rather than reinvents.
FAILURES: frozenset[str] = frozenset(
    {"tokens", "seconds", "tool_calls", "no_delivery", "malformed_delivery"}
)


@dataclass(frozen=True, slots=True)
class Outcome:
    """What one question produced. Exactly one of `proposal` and `failed` is set."""

    question: str
    model_id: str
    registry_fingerprint: str
    prompt_fingerprint: str
    proposal: ProposedDesign | None
    failed: str | None
    trace: tuple[TraceRow, ...]
    transcript: tuple[dict[str, Any], ...] = field(default=())

    def __post_init__(self) -> None:
        if (self.proposal is None) == (self.failed is None):
            raise ValueError("an outcome is a proposal or a named failure, never both or neither")
        if self.failed is not None and self.failed not in FAILURES:
            raise ValueError(f"{self.failed!r} is not a failure this package declares")


def proposal_tool(schema_path: Path | None = None) -> dict[str, Any]:
    """The delivery tool, derived from the compiled form rather than written out.

    A second copy of the nine fields here would be the second definition rule 3 of the contract
    layer refuses, and it would drift the day a closed list changed. So the compiled schema is
    read and three keys are removed; `tests/agent/test_the_proposal_tool_is_the_form_minus_two.py`
    asserts the derivation against the file rather than against a copy of it.
    """
    path = schema_path if schema_path is not None else FORM_SCHEMA
    form = json.loads(path.read_text(encoding="utf-8"))
    withheld = not_the_agents(form)
    properties = {k: _tool_safe(v) for k, v in form["properties"].items() if k not in withheld}
    required = [k for k in form["required"] if k not in withheld]
    return {
        "name": PROPOSE,
        "description": (
            "Deliver the design. Call this exactly once, when you have decided. The two "
            "fields this tool does not have -- how long the business will allow, and what "
            "will be done with each outcome -- are not yours to fill and will be supplied by "
            "whoever runs the experiment."
        ),
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": properties,
            "required": required,
        },
        "strict": True,
    }


def _tool_safe(schema: Any) -> Any:
    """The same schema with the keywords the tool API refuses removed, recursively.

    `oneOf` becomes `anyOf`: the API refuses the first and takes the second, and the form's two
    uses of it -- null-or-a-list, `"all"`-or-a-list -- are disjoint alternatives, for which the
    two keywords say the same thing.
    """
    if isinstance(schema, dict):
        safe: dict[str, Any] = {}
        for key, value in schema.items():
            if key in UNSUPPORTED_BY_TOOLS:
                continue
            if key == "minItems" and isinstance(value, int) and value > 1:
                # The API takes 0 or 1 here and nothing else -- `got: [2, 5]` was the answer to
                # sending the form's own bounds. The bound stays where `form.py` checks it.
                safe[key] = 1
                continue
            safe["anyOf" if key == "oneOf" else key] = _tool_safe(value)
        return safe
    if isinstance(schema, list):
        return [_tool_safe(item) for item in schema]
    return schema


def system_prompt(context: dict[str, str]) -> str:
    """What the model is told, assembled from the enumerated context in a fixed order.

    The order is the context's own insertion order, which `context.enumerated` fixes, so the
    same context renders to the same bytes and the fingerprint below means something.
    """
    shown = "\n\n".join(f"## {name}\n{text}" for name, text in context.items())
    return (
        "You design one randomised experiment to answer a business question about pricing "
        "in a supermarket chain. You fill the judgment fields of the design and nothing else: "
        "a hypothesis, the intervention as two declared policies, the scope, the primary "
        "metric, the unit of randomisation, the smallest difference worth detecting, and any "
        "store exclusions with a reason each.\n\n"
        "You do not decide how long the business will allow or what will be done with the "
        "result; those fields do not exist in the tool you deliver with.\n\n"
        "A design is checked by code after you deliver it -- power against the pre-period "
        "variance, interference by unit, the metric against the contract -- and an infeasible "
        "design is refused with a reason code that names what would fix it. That refusal is "
        "the system's to give and is useful to the people who asked, so deliver a design "
        "whenever the question can be expressed in the form at all, even one you expect to "
        "be refused. Decline only when no design can be expressed -- a category the estate "
        "does not have, a policy that does not exist. Propose what you judge best; do not "
        "shade the minimum detectable effect upward to pass a check you can see coming, "
        "because a difference nobody would act on is not worth detecting.\n\n"
        "What you know is below, and it is all you know. Nothing measured inside the "
        "comparison window is available to you.\n\n"
        f"{shown}\n\n"
        f"Deliver by calling `{PROPOSE}` once."
    )


def prompt_fingerprint(context: dict[str, str]) -> str:
    """A digest over the system prompt and the delivery tool -- what the model was told."""
    canonical = json.dumps(
        {"system": system_prompt(context), "deliver": proposal_tool(), "nudge": NUDGE},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def propose(
    question: str,
    *,
    context: dict[str, str],
    model: Model,
    executor: Executor,
    ceilings: Ceilings,
) -> Outcome:
    """Ask, loop over tool calls under the ceilings, and return what came out."""
    tools = registry()
    definitions = [tool.definition() for _, tool in sorted(tools.items())] + [proposal_tool()]
    admitted = dict(tools)
    admitted[PROPOSE] = Tool(
        name=PROPOSE, description="delivery", input_schema=proposal_tool()["input_schema"]
    )

    messages: list[dict[str, Any]] = [{"role": "user", "content": question}]
    trace: list[TraceRow] = []
    transcript: list[dict[str, Any]] = [{"role": "user", "content": question}]
    started = time.monotonic()
    tokens_spent = 0
    tool_calls_made = 0
    step = 0
    nudged = False

    def failed(which: str, detail: str) -> Outcome:
        trace.append(TraceRow(step=step, kind="failed", name=which, detail=detail))
        return Outcome(
            question=question,
            model_id=model.model_id,
            registry_fingerprint=fingerprint(tools),
            prompt_fingerprint=prompt_fingerprint(context),
            proposal=None,
            failed=which,
            trace=tuple(trace),
            transcript=tuple(transcript),
        )

    while True:
        step += 1
        elapsed = time.monotonic() - started
        if elapsed > ceilings.seconds:
            return failed("seconds", f"{elapsed:.1f}s against a ceiling of {ceilings.seconds}s")

        call_started = time.monotonic()
        response = model.create(
            system=system_prompt(context),
            messages=messages,
            tools=definitions,
            max_tokens=max(1024, ceilings.tokens - tokens_spent),
        )
        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        tokens_spent += output_tokens
        trace.append(
            TraceRow(
                step=step,
                kind="model",
                name=model.model_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                elapsed_s=time.monotonic() - call_started,
                detail=str(getattr(response, "stop_reason", "")),
            )
        )
        content = [_plain(block) for block in response.content]
        transcript.append({"role": "assistant", "content": content})

        if tokens_spent > ceilings.tokens:
            return failed("tokens", f"{tokens_spent} against a ceiling of {ceilings.tokens}")

        tool_uses = [b for b in response.content if getattr(b, "type", "") == "tool_use"]
        if response.stop_reason != "tool_use" or not tool_uses:
            if not nudged:
                # **One nudge, and only one.** Measured on 2026-09-11: ten of twelve questions
                # ended with the model writing its analysis as prose and stopping, the design
                # it had reasoned its way to never delivered. A second turn that says "deliver
                # or decline in one line" is not pressure to propose what the model judges
                # impossible -- declining is still an answer -- and it is bounded, so a model
                # that will not deliver costs one more call and not a loop. Recorded in the
                # trace as its own kind, so a recording shows which proposals needed it.
                nudged = True
                trace.append(TraceRow(step=step, kind="nudge", name=PROPOSE))
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": NUDGE})
                transcript.append({"role": "user", "content": NUDGE})
                continue
            return failed(
                "no_delivery",
                f"the model stopped with {response.stop_reason!r} without calling {PROPOSE}",
            )

        messages.append({"role": "assistant", "content": response.content})
        results: list[dict[str, Any]] = []
        for use in tool_uses:
            arguments = dict(use.input) if isinstance(use.input, dict) else {}
            try:
                tool = admit(use.name, admitted)
            except ToolNotInRegistryError as refused:
                trace.append(
                    TraceRow(step=step, kind="refused_tool", name=use.name, detail=str(refused))
                )
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": use.id,
                        "content": str(refused),
                        "is_error": True,
                    }
                )
                continue

            if tool.name == PROPOSE:
                try:
                    proposal = parse(arguments)
                except ProposalError as malformed:
                    return failed("malformed_delivery", str(malformed))
                trace.append(TraceRow(step=step, kind="proposal", name=PROPOSE))
                return Outcome(
                    question=question,
                    model_id=model.model_id,
                    registry_fingerprint=fingerprint(tools),
                    prompt_fingerprint=prompt_fingerprint(context),
                    proposal=proposal,
                    failed=None,
                    trace=tuple(trace),
                    transcript=tuple(transcript),
                )

            tool_calls_made += 1
            if tool_calls_made > ceilings.tool_calls:
                return failed(
                    "tool_calls", f"{tool_calls_made} against a ceiling of {ceilings.tool_calls}"
                )
            answer = executor.run(tool, arguments)
            trace.append(TraceRow(step=step, kind="tool", name=tool.name, detail=answer[:120]))
            results.append({"type": "tool_result", "tool_use_id": use.id, "content": answer})

        messages.append({"role": "user", "content": results})
        transcript.append({"role": "user", "content": results})


def parse(arguments: dict[str, Any]) -> ProposedDesign:
    """The delivery tool's arguments into the seven-field type, refusing shape by name.

    The schema has already been enforced by the API when the tool is strict, so what this
    catches is the handful of invariants a schema cannot express and `form.py` does -- the
    hypothesis length, the duplicated exclusion, the MDE as a `Decimal` and never a float.
    """
    try:
        mde = arguments["mde"]
        scope = arguments["scope"]
        return ProposedDesign(
            hypothesis=str(arguments["hypothesis"]),
            intervention=Intervention(
                treatment=str(arguments["intervention"]["treatment"]),
                control=str(arguments["intervention"]["control"]),
            ),
            scope=Scope(
                categories=tuple(scope["categories"]),
                products=None if scope.get("products") is None else tuple(scope["products"]),
                stores=None if scope.get("stores") in (None, "all") else tuple(scope["stores"]),
            ),
            primary_metric=str(arguments["primary_metric"]),
            unit=Unit(arguments["unit"]),
            mde=Mde(
                kind=MdeKind(mde["kind"]),
                value=Decimal(str(mde["value"])),
                direction=MdeDirection(mde.get("direction", "either")),
            ),
            exclusions=tuple(
                Exclusion(store_id=str(e["store_id"]), reason=str(e["reason"]))
                for e in arguments.get("exclusions", [])
            ),
        )
    except (KeyError, TypeError, ValueError, DesignFormError) as malformed:
        raise ProposalError(f"the delivered design is not a proposal: {malformed}") from malformed


def _plain(block: Any) -> dict[str, Any]:
    """A response block as plain data, for the transcript a recording keeps."""
    if hasattr(block, "model_dump"):
        dumped: dict[str, Any] = block.model_dump()
        return dumped
    return {"type": getattr(block, "type", "unknown"), "repr": repr(block)}
