#!/usr/bin/env python3
"""Never commit to `main`. The rule from CLAUDE.md's git workflow, made a guarantee.

`main` is already protected by a repository ruleset with no bypass actors, so a commit made
here could never be *pushed*. That is the gate and it is not in question. What the ruleset
cannot do is stop the commit from being made in the first place — and a session that has
committed three times to a local `main` has to unpick them before it can open the pull
request that CLAUDE.md says every piece of work goes through. The cost is not a broken `main`;
it is the twenty minutes of `git reset` and the temptation, at minute nineteen, to just push.

So this is deliberately not a duplicate of the ruleset. The ruleset refuses the push; this
refuses the commit, at the only moment at which refusing it is free.

Scope is exactly `git commit`. `git push` is left alone: the ruleset already refuses it by
name, and CLAUDE.md's rule about the money-spending workflows dispatching from `main` only is
a workflow condition rather than a local one.
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

PROTECTED = "main"

#: Shell tokens that end one command and begin another. A `git commit` after any of these is
#: still a `git commit`; a `git commit` inside `echo "..."` is not, which is why the command
#: is tokenised rather than grepped.
_SEPARATORS = {"&&", "||", ";", "|", "&", "(", ")", "{", "}", "\n"}

#: `git`'s own options, before the subcommand. These two take their value as the next token,
#: so the token after them is never the subcommand.
_TAKES_A_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}

#: Used only when the command does not tokenise — an unbalanced quote, most often. Coarser
#: than the tokeniser and deliberately so: an unparsable command is the one case where
#: guessing wrong in the safe direction costs a retry and guessing wrong in the other costs
#: the branch.
_COARSE = re.compile(r"\bgit\b[^|&;\n]*\bcommit\b")

_REFUSAL = (
    "Refusing `git commit` on `{branch}`.\n"
    'CLAUDE.md: "Never commit to `main`. One branch per closed piece of work — which means '
    'one branch per session, not one per commit."\n'
    "`main` is protected by a ruleset with no bypass actors, so this commit could never be "
    "pushed; it would only have to be unpicked. Branch first — the name names the work, not "
    "the ticket:\n"
    "    git checkout -b <area>/<what-it-closes>\n"
    "then commit freely. Those commits are restore points; the merge is a squash."
)


def _segments(command: str) -> list[list[str]]:
    """The command split into the individual commands it actually runs."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    tokens = list(lexer)
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token in _SEPARATORS:
            segments.append([])
        else:
            segments[-1].append(token)
    return [s for s in segments if s]


def _is_git_commit(segment: list[str]) -> bool:
    index = 0
    # `FOO=bar git commit` runs git just as surely as `git commit` does.
    while index < len(segment) and re.fullmatch(r"[A-Za-z_]\w*=.*", segment[index]):
        index += 1
    if index >= len(segment) or Path(segment[index]).name != "git":
        return False
    index += 1
    while index < len(segment):
        token = segment[index]
        if not token.startswith("-"):
            return token == "commit"
        index += 2 if token in _TAKES_A_VALUE else 1
    return False


def commits(command: str) -> bool:
    """Does this command line run `git commit`?"""
    try:
        segments = _segments(command)
    except ValueError:
        return bool(_COARSE.search(command))
    return any(_is_git_commit(segment) for segment in segments)


def current_branch(cwd: Path) -> str | None:
    """The branch `cwd` is on, or None for a detached HEAD or no repository at all.

    `symbolic-ref` rather than `rev-parse --abbrev-ref`, for two reasons that both matter
    here. It answers on an unborn branch — a repository with no commit yet is still *on*
    `main` and a commit made there is exactly the one this refuses. And it fails on a detached
    HEAD instead of returning the string `HEAD`, which is the honest answer: a detached HEAD
    is not on `main`, so there is nothing to refuse.
    """
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    branch = result.stdout.strip()
    return branch or None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if not isinstance(event, dict) or event.get("tool_name") != "Bash":
        return 0
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0
    command = tool_input.get("command")
    if not isinstance(command, str) or not commits(command):
        return 0
    cwd = event.get("cwd")
    branch = current_branch(Path(cwd) if isinstance(cwd, str) else Path.cwd())
    if branch != PROTECTED:
        return 0
    sys.stderr.write(_REFUSAL.format(branch=branch) + "\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
