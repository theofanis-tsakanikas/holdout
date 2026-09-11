"""The one place in `holdout.agent` that opens a connection.

Everything else in this package is pure over plain data, so that the same agent runs from a
laptop while somebody is working on the prompt and through the estate when the recording that
claim 6 grades is made. The model is reached through a `Model`, which is three methods and no
opinion about transport, and this module holds the only implementation that talks to a network.

Bedrock, and why
----------------
The model is reached through **Amazon Bedrock with the AWS credentials this account already
has** — the same identity that applies `infra/bootstrap` from a laptop, and the same role CI
assumes through OIDC. No second secret exists anywhere, which is the property `CLAUDE.md` names
under *no long-lived credentials*, and it is the pattern the portfolio's other agent already
uses. The client is the Anthropic SDK's Bedrock client rather than a hand-rolled `boto3` call:
the request and response shapes are the Messages API's, so the loop in `propose.py` reads the
same whatever carries it.

The model id is a contract value
--------------------------------
`contracts/agent/runtime.yaml` declares it with a source and a verification date, like every
other number that comes from outside this repository. A model id typed into a Python file is
the *value without a source* the contract layer exists to refuse, and it is also the thing a
recording is stamped with: a proposal made by a model nobody can name is a proposal from nobody.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, cast


class Model(Protocol):
    """What the loop needs from a model, and nothing more.

    `create` takes the Messages API's shapes and returns its response object. The loop reads
    `stop_reason`, `content` and `usage` from it, so an implementation for the estate's
    gateway has exactly one method to provide.
    """

    @property
    def model_id(self) -> str: ...

    def create(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int,
    ) -> Any: ...


@dataclass(frozen=True, slots=True)
class BedrockModel:
    """Claude, through Amazon Bedrock, with whatever AWS credentials the process has.

    `import anthropic` happens inside `create` rather than at module level, for the same reason
    `ops/figures.py` defers an import: this module is imported by the recording's *reader*, and
    the reader runs on every CI job without the `agent` extra installed. An import at module
    scope would make thirteen jobs fail collection over a client one job uses.
    """

    model_id: str
    region: str
    #: `{"type": "adaptive"}` on the 4.6+ family; `None` omits the parameter, which is what a
    #: model that predates adaptive thinking requires rather than a 400.
    thinking: dict[str, Any] | None = None
    #: Bedrock serves Claude through two endpoints. The Messages-API endpoint carries the
    #: current generation under bare ids (`anthropic.claude-opus-5`); the older `InvokeModel`
    #: path carries ARN-versioned ids (`eu.anthropic.claude-haiku-4-5-20251001-v1:0`) behind an
    #: inference-profile prefix. Which one a model id belongs to is a fact about the id, so it
    #: is declared beside it rather than guessed from its spelling.
    legacy_endpoint: bool = False

    def create(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int,
    ) -> Any:
        from anthropic import AnthropicBedrock, AnthropicBedrockMantle

        client = (
            AnthropicBedrock(aws_region=self.region)
            if self.legacy_endpoint
            else AnthropicBedrockMantle(aws_region=self.region)
        )
        extra: dict[str, Any] = {} if self.thinking is None else {"thinking": self.thinking}
        return client.messages.create(
            model=self.model_id,
            max_tokens=max_tokens,
            system=system,
            # Plain dicts in the SDK's own TypedDict shapes; the cast tells mypy so, and the
            # API is what checks it, which is the only checker that can.
            messages=cast(Any, messages),
            tools=cast(Any, tools),
            **extra,
        )
