"""The agent surface — what it reads, what it may call, and what it may produce.

**Not on the decision path.** `CLAUDE.md` is unambiguous: no LLM is anywhere near the 2.4
million pricing decisions a day, which are taken inside the pipeline by code from a pinned
model version. This package is the other AI system in that file's table — the one that runs a
handful of times a week, takes text and context, and produces the judgment fields of an
experiment design. The two never call each other.

Three limits, and each is a type or a file rather than an instruction
---------------------------------------------------------------------
* `registry` — the agent may call exactly the tools the metric contract compiles. There is no
  SQL tool and no catalog browse, so the set of expressible questions is closed.
* `proposal` — the agent produces a `ProposedDesign`, which is seven fields and has nowhere to
  put `max_duration` or `decision_rule`. It cannot become a `DesignForm` without somebody else
  supplying them.
* `context` — what it is shown is an enumerated list, not a directory.

Where it runs is deliberately not decided here
----------------------------------------------
Nothing in this package opens a connection. A caller supplies a client, so the same agent runs
against a model API from a laptop while somebody is working on the prompt, and through the
estate's AI Gateway when the recording that claim 6 grades is made. **The runtime is an
adapter and the agent is not**, which is what keeps the claim from depending on an estate
being up.
"""
