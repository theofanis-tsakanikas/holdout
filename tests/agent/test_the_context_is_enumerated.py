"""What the agent is shown is a list somebody can state, and nothing in it is an outcome.

`context.enumerated` is the one place the agent's knowledge is assembled, and the assertion is
about its shape rather than its wording: a fixed set of entries in a fixed order, none of which
reaches past the pre-period, none of which names a path under `corpus/`, and a rendering that
is the same bytes for the same inputs -- which is what makes the prompt fingerprint a
fingerprint.

## What this asserts

- The entries are exactly the declared six, in insertion order.
- The roster entry names the surviving roster and the control arm and never the bare store
  count on its own -- `CLAUDE.md`'s most-corrected figure.
- No entry mentions `corpus/`, `seal`, `truth`, or the comparison window's inside.
- Same inputs, same bytes; a changed pre-period changes the fingerprint.
- The policies and metrics named are the contracts', all of them, and nothing else.

## What it does not check

- **That the wording is good.** Whether the context makes a strong proposer is measured by
  the recording, not asserted here.
"""

from __future__ import annotations

import re

from holdout.agent.context import PrePeriod, Roster, enumerated
from holdout.agent.propose import prompt_fingerprint, system_prompt
from holdout.contracts.loader import load

CONTRACTS = load()
PRE = PrePeriod(weeks=8, units=48, mean_cents=1417, variance_cents2=24312932)
ROSTER = Roster(stores=320, surviving=269, control_arm=53, categories=("bakery", "dairy"))
ENTRIES = ("metrics", "guardrails", "policies", "roster", "pre_period", "units_of_randomisation")


def test_the_entries_are_the_declared_six_in_order() -> None:
    context = enumerated(CONTRACTS, PRE, ROSTER)
    assert tuple(context) == ENTRIES, (
        f"the context holds {tuple(context)}; this file declares {ENTRIES}. A seventh entry is "
        "a decision about what the agent knows and is recorded here or not at all."
    )


def test_the_roster_entry_names_the_surviving_roster_and_the_arm() -> None:
    roster = enumerated(CONTRACTS, PRE, ROSTER)["roster"]
    assert "269" in roster and "53" in roster
    assert re.search(r"\b320\b stores", roster), (
        "the store count appears only as what the roster survived out of"
    )
    assert "never against the store count" in roster


def test_nothing_shown_reaches_an_outcome_or_the_corpus() -> None:
    everything = "\n".join(enumerated(CONTRACTS, PRE, ROSTER).values()) + system_prompt(
        enumerated(CONTRACTS, PRE, ROSTER)
    )
    for forbidden in ("corpus/", "seal", "truth.sealed", "potential outcome", "injected"):
        assert forbidden not in everything, f"the agent is shown {forbidden!r}"
    assert "Nothing measured inside the comparison window" in everything


def test_the_same_inputs_render_to_the_same_bytes() -> None:
    a = prompt_fingerprint(enumerated(CONTRACTS, PRE, ROSTER))
    b = prompt_fingerprint(enumerated(CONTRACTS, PRE, ROSTER))
    assert a == b
    moved = PrePeriod(weeks=8, units=48, mean_cents=1418, variance_cents2=24312932)
    assert prompt_fingerprint(enumerated(CONTRACTS, moved, ROSTER)) != a


def test_the_closed_lists_shown_are_the_contracts() -> None:
    context = enumerated(CONTRACTS, PRE, ROSTER)
    for metric_id in CONTRACTS.metric_ids:
        assert metric_id in context["metrics"]
    for policy in CONTRACTS.policies:
        assert f"{policy.id}@v{policy.version}" in context["policies"]
