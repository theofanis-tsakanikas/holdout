"""A model that answers from a script, so the loop is tested without a socket.

The loop reads four things off a response -- `stop_reason`, `content`, `usage`, and each
block's `type`, `name`, `id`, `input` -- and these stand-ins carry exactly those. What they do
not do is validate a tool schema: a `strict` tool is enforced by the API, and a fake that
enforced it would be this suite agreeing with itself about what the API does. The tests that
need a malformed delivery therefore send one the API would have accepted -- valid JSON, wrong
by an invariant only `form.py` knows -- which is also the shape a real model produced.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from holdout.agent.registry import Tool


@dataclass
class Block:
    type: str
    text: str = ""
    name: str = ""
    id: str = ""
    input: dict[str, Any] = field(default_factory=dict)

    def model_dump(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "text": self.text,
            "name": self.name,
            "id": self.id,
            "input": self.input,
        }


@dataclass
class Usage:
    input_tokens: int = 100
    output_tokens: int = 50


@dataclass
class Response:
    stop_reason: str
    content: list[Block]
    usage: Usage = field(default_factory=Usage)


def text(words: str) -> Response:
    return Response(stop_reason="end_turn", content=[Block(type="text", text=words)])


def calls(*uses: tuple[str, dict[str, Any]], output_tokens: int = 50) -> Response:
    blocks = [
        Block(type="tool_use", name=name, id=f"toolu_{i}", input=arguments)
        for i, (name, arguments) in enumerate(uses)
    ]
    return Response(
        stop_reason="tool_use", content=blocks, usage=Usage(output_tokens=output_tokens)
    )


@dataclass
class Scripted:
    """Answers each `create` with the next response; asked past the end, it stops talking."""

    responses: list[Response]
    model_id: str = "fake"
    seen: list[dict[str, Any]] = field(default_factory=list)

    def create(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int,
    ) -> Response:
        # A copy, because the loop appends to its own list after the call returns and a test
        # reading `seen` wants what the model was sent, not what the list became.
        self.seen.append(
            {"system": system, "messages": list(messages), "tools": tools, "max_tokens": max_tokens}
        )
        if not self.responses:
            return text("nothing left to say")
        return self.responses.pop(0)


class Echo:
    """An executor that answers every admitted tool with its own name."""

    def run(self, tool: Tool, arguments: dict[str, Any]) -> str:
        return f"{tool.name} answered"


GOOD_DELIVERY: dict[str, Any] = {
    "hypothesis": "A deeper end-of-day markdown on bakery reduces waste value per store-week.",
    "intervention": {"treatment": "ladder_policy@v1", "control": "ladder_policy@v1"},
    "scope": {"categories": ["bakery"], "products": None, "stores": "all"},
    "primary_metric": "waste_value_per_store_week",
    "unit": "store",
    "mde": {"kind": "relative_pct", "value": 5.0, "direction": "decrease"},
    "exclusions": [],
}
