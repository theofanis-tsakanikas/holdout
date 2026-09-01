"""One tree, one run — and the guard answers with the trigger's *effect*, never its spelling.

Until 2026-09-01 `ci.yml` carried `on: push:` with no branch filter beside a `pull_request`
scoped to `main`. A push to a branch with an open pull request fired both, so this whole
workflow was entered twice for one sha: measured at ~58 h of redundant runner time over five
days, 34.9 h of it `claim-2`. `ci.yml`'s own `on:` comment carries the measurement and the
command that produced it.

**Why this file exists at all.** Nothing in the repository could have said the workflow ran
twice. `make check` cannot see the forge, the duplication is invisible in a green checks list
because both runs are green, and the one comment in `ci.yml` that circled it — *the cancelled
one is sometimes the required check* — described the mechanism that kept it harmless rather
than the cause. It was found by pairing the Actions run list on `headSha`, which is a question
nobody asks twice. So the rule gets a gate instead of a memory.

**What is refused: a push to a branch that is not `main` starting this workflow.** Not the
string `branches: [main]`, which is one spelling of a rule with many. `CLAUDE.md`:

> A guard tested by its author is tested in the shape the guard already handles.

A guard matching the literal line would pass on `branches: ['**']`, on
`branches: [main, 'ops/*']`, and on `branches-ignore:` — three ways to write a filter that
filters nothing, none of which look like the defect and all of which restore it. So the
question is put to the parsed `on:` block as GitHub would evaluate it: *given this
configuration, does a push to `ops/some-branch` start this workflow?* Each of those three is
driven below as an attack, alongside the exact shape `main` was in.

**And the instrument raises rather than answering.** `_matches` implements the subset of
GitHub's filter-pattern syntax this repository uses — `*`, `**`, `?` and literals. Negation
(`!`), character ranges (`[…]`) and `+` are refused by name rather than approximated, because
a pattern matcher that quietly returns the wrong answer for a syntax it does not implement is
`grep -P` again: *an instrument that cannot answer raises rather than returning zero.*

What this does **not** cover, stated so the docstring is not the thing overstating coverage:

* it reads `.github/workflows/ci.yml` and no other workflow. The four dispatch workflows spend
  money and are `workflow_dispatch` only; if one ever grows a `push` trigger, nothing here
  looks at it.
* it says nothing about what the `main` ruleset requires. That is a fact about the forge, no
  file carries it, and `docs/reviews/phase-1.md` §2d is what it costs to assume otherwise.
* it cannot tell whether the forge resolves two check runs of one name by taking the latest or
  either. That question is dissolved rather than answered — after this filter a pull-request
  head carries one run of each context — and it is deliberately not asserted anywhere.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

#: A branch name that is not `main` and is shaped like the ones this repository actually uses.
#: `CLAUDE.md`: branch names name the work, not the ticket.
A_WORKING_BRANCH = "ops/ci-runs-once-per-tree"


class UnsupportedPatternError(Exception):
    """A filter pattern this matcher does not implement, refused instead of approximated."""


def _matches(pattern: str, branch: str) -> bool:
    """Does `branch` match one GitHub filter pattern?

    `**` crosses `/`, `*` does not, `?` is one character that is not `/`. Anything else with a
    meaning in GitHub's syntax raises: this guard is allowed to be narrow and is not allowed to
    be wrong.
    """
    if pattern.startswith("!"):
        raise UnsupportedPatternError(f"negated pattern {pattern!r} is not implemented here")
    if "[" in pattern or "+" in pattern:
        raise UnsupportedPatternError(
            f"pattern {pattern!r} uses syntax this matcher does not implement"
        )

    out: list[str] = []
    i = 0
    while i < len(pattern):
        char = pattern[i]
        if pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif char == "*":
            out.append("[^/]*")
            i += 1
        elif char == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(char))
            i += 1
    return re.fullmatch("".join(out), branch) is not None


def push_starts_workflow(on_block: Any, branch: str) -> bool:
    """Would a push to `branch` start a workflow with this `on:` block?

    GitHub's rule, and the two halves that make the defect possible: a `push` key with **no**
    `branches` and no `branches-ignore` matches every branch, and `branches-ignore` allows
    everything it does not name.
    """
    if not isinstance(on_block, dict):
        raise UnsupportedPatternError(f"the on: block is {type(on_block).__name__}, not a mapping")
    if "push" not in on_block:
        return False

    push = on_block["push"]
    if push is None:  # `push:` with nothing under it — the shape `main` carried.
        return True
    if not isinstance(push, dict):
        raise UnsupportedPatternError(f"the push trigger is {type(push).__name__}, not a mapping")

    if "branches" in push:
        return any(_matches(p, branch) for p in push["branches"])
    if "branches-ignore" in push:
        return not any(_matches(p, branch) for p in push["branches-ignore"])
    return True  # tags-only filters do not constrain branches.


def _on_block(text: str) -> Any:
    """The `on:` block, read past YAML 1.1 deciding that `on` is the boolean `True`."""
    loaded = yaml.safe_load(text)
    for key in (True, "on"):
        if key in loaded:
            return loaded[key]
    raise UnsupportedPatternError("ci.yml has no on: block in a shape this test can read")


def _ci_text() -> str:
    return CI_WORKFLOW.read_text(encoding="utf-8")


# ------------------------------------------------------------------ the rule, as it stands today


def test_a_push_to_a_working_branch_does_not_start_ci() -> None:
    """The finding, as a standing assertion: one tree gets one run."""
    on_block = _on_block(_ci_text())
    assert not push_starts_workflow(on_block, A_WORKING_BRANCH), (
        f"a push to {A_WORKING_BRANCH!r} starts ci, so a branch with an open pull request "
        "enters this workflow twice for one sha — the state measured at ~58 h of redundant "
        "runner time over five days"
    )


def test_a_push_to_main_still_starts_ci() -> None:
    """The other direction, because a filter that covers nothing is the cheap way to pass above.

    `main` is where the four dispatch workflows run from and where a squash-merge lands, so it
    is the one branch a push must still be judged on.
    """
    assert push_starts_workflow(_on_block(_ci_text()), "main")


def test_a_pull_request_into_main_still_starts_ci() -> None:
    """And the event that now carries every branch, so the trade above is the only trade.

    If `pull_request` were ever narrowed too, the two tests above would both still pass and a
    branch would be covered by nothing at all.
    """
    on_block = _on_block(_ci_text())
    pull_request = on_block["pull_request"]
    assert pull_request is None or any(
        _matches(p, "main") for p in pull_request.get("branches", ["**"])
    ), "pull requests into main no longer start ci, so a branch is covered by no event at all"


# ------------------------------------------------- four filters that filter nothing, each driven


@pytest.mark.parametrize(
    ("name", "replacement"),
    [
        # The exact state `main` was in until 2026-09-01.
        ("no filter at all", "on:\n  push:\n  pull_request:\n    branches: [main]\n"),
        # Three that a reader scanning for `branches:` would take for a filter.
        (
            "a pattern that matches everything",
            "on:\n  push:\n    branches: ['**']\n  pull_request:\n    branches: [main]\n",
        ),
        (
            "main plus the branches this repository actually uses",
            "on:\n  push:\n    branches: [main, 'ops/*']\n  pull_request:\n    branches: [main]\n",
        ),
        (
            "an ignore list that names something else",
            "on:\n  push:\n    branches-ignore: [gh-pages]\n  pull_request:\n"
            "    branches: [main]\n",
        ),
    ],
)
def test_a_filter_that_does_not_filter_is_refused(name: str, replacement: str) -> None:
    """Each restores the duplication, and none of them looks like the defect.

    A guard keyed to the literal line `branches: [main]` passes on three of these four. That is
    the whole reason this file asks the question of the parsed configuration instead.
    """
    text = _ci_text()
    current = "on:\n  push:\n    branches: [main]\n  pull_request:\n    branches: [main]\n"
    assert current in text, "ci.yml's on: block is not in the shape this attack rewrites"

    attacked = _on_block(text.replace(current, replacement, 1))
    assert push_starts_workflow(attacked, A_WORKING_BRANCH), (
        f"the attack {name!r} was supposed to restore the duplication and did not, so it "
        "proves nothing about the guard above"
    )


# --------------------------------------------------------- the matcher answers or it refuses


@pytest.mark.parametrize(
    ("pattern", "branch", "expected"),
    [
        ("main", "main", True),
        ("main", "ops/x", False),
        ("**", "ops/x", True),
        ("*", "ops/x", False),  # `*` does not cross a slash, which is the whole trap in `ops/*`
        ("*", "main", True),
        ("ops/*", "ops/x", True),
        ("ops/*", "ops/x/y", False),
        ("ops/**", "ops/x/y", True),
        ("mai?", "main", True),
        ("mai?", "ma/n", False),
    ],
)
def test_the_matcher_agrees_with_githubs_documented_semantics(
    pattern: str, branch: str, expected: bool
) -> None:
    assert _matches(pattern, branch) is expected


@pytest.mark.parametrize("pattern", ["!main", "releases/[0-9]", "ma+in"])
def test_a_pattern_the_matcher_does_not_implement_raises(pattern: str) -> None:
    """`grep -P` one layer along: silence and success must not look the same.

    Each of these has a meaning in GitHub's syntax that this matcher does not implement. A
    matcher that returned `False` for them would report *this branch is not covered* from a
    rule it never evaluated.
    """
    with pytest.raises(UnsupportedPatternError):
        _matches(pattern, "main")
