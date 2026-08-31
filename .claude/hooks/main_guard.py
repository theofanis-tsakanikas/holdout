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

The defect this file keeps having
---------------------------------
**Three times, and each time as a spelling the file already knew about somewhere else.**

* `-C <path>` sat in `_TAKES_A_VALUE` so the subcommand hunt would step over it. The path was
  parsed and thrown away, and the branch was read from the session's directory instead — which
  refused a safe commit into a worktree and, worse, **allowed** `git -C <the checkout on main>
  commit` from a session on a branch;
* `GIT_DIR=` was known to `_COARSE`, whose prefix exists for environment assignments, and to
  `_is_git_commit`, which skips them — and absent from the enumeration of ways to name a
  repository. Found by review **of the fix for the first one**;
* `--git-dir <path>`, space-separated, sat in `_TAKES_A_VALUE` **three lines above** the
  enumeration that omitted it. Found by review of the fix for the second.

So the pattern, which is what the fourth will need, because it will look different again:

    A flag or a variable this file already handles for one purpose is a flag or a variable it
    can be asked about for another — and the second question is asked by a different function,
    written later, by somebody reading the first list and not the file.

`_NAMES_A_REPOSITORY` is therefore a **subset of `_TAKES_A_VALUE`, asserted at import** rather
than a second list kept in step by memory. Two lists of flags in one file, each missing a member
of the other, is how this reached three.
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
#:
#: A newline is **not** in this set, and cannot be: `shlex` with `whitespace_split` treats it
#: as whitespace, so no newline token ever reaches here. The first version of this file listed
#: it anyway, which made every line after the first join the first command — so the ordinary
#: two-line `git add -A` / `git commit -m x` was waved through while the one-line `&&` form
#: was caught. Lines are split before tokenising instead; see `_segments`.
_SEPARATORS = {"&&", "||", ";", "|", "&", "(", ")", "{", "}"}

#: Shell keywords that can stand in front of a command inside a compound statement. Without
#: these, `if …; then git commit; fi` and `for …; do git commit; done` both start their
#: segment with a keyword and never reach the `git` test.
_KEYWORDS = {"then", "do", "else", "elif", "!", "time", "exec", "nohup"}

#: `git`'s own options, before the subcommand. These two take their value as the next token,
#: so the token after them is never the subcommand.
_TAKES_A_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}

#: Used only when the command does not tokenise — an unbalanced quote, most often. Coarser
#: than the tokeniser and deliberately so: an unparsable command is the one case where
#: guessing wrong in the safe direction costs a retry and guessing wrong in the other costs
#: the branch.
#: `git` at a plausible *command* position — start of a line, or after a separator, with only
#: environment assignments in front of it. The looser `\bgit\b.*\bcommit\b` also matched
#: prose inside a heredoc, and a heredoc with an apostrophe in it is exactly what unbalances
#: the lexer and sends us here. A guard that refuses `Don't run git commit here` written into
#: a file is a guard that gets switched off.
_COARSE = re.compile(
    r"(?:^|[|&;()]|\bthen\b|\bdo\b)[ \t]*(?:[A-Za-z_]\w*=\S*[ \t]+)*"
    r"[\w./-]*\bgit\b[^|&;\n]*\bcommit\b",
    re.MULTILINE,
)

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


#: The only two consumers whose heredoc body provably cannot execute. A whitelist of two
#: rather than a classification of every consumer: not *is this executed?*, which needs the
#: command understood, but *is this one of the two forms that cannot execute?*, which is a
#: string comparison. `bash`, `sh`, `python3` and anything unrecognised keep their bodies
#: matched, and that is deliberate — an executing body reaches git through `os.system` or a
#: subprocess without any line beginning with `git`, so no pattern over the body would see it.
#:
#: **The workaround for a refused `python <<EOF` is the editor tool, not a wider list.** A
#: refusal recorded as a false positive is a refusal somebody later removes, and adding
#: `python` here opens exactly the hole this leaves closed.
_WRITES_ITS_INPUT = {"cat", "tee"}

#: `<<EOF`, `<<-EOF`, `<<'EOF'`, `<<"EOF"`. The delimiter is what ends the body.
_HEREDOC = re.compile(r"""<<-?[ \t]*(['"]?)(?P<delim>[A-Za-z_]\w*)\1""")

#: Anything that could carry the body onward to something that runs it. A pipe disqualifies
#: the line from the whitelist rather than being reasoned about separately, and so does a
#: command substitution — `$(cat <<EOF …)` is a body whose output the shell may execute.
_CARRIES_ONWARD = ("|", "$(", "`")


def _writes_rather_than_runs(line: str) -> bool:
    """Is this heredoc's body written somewhere, rather than executed?

    Fails closed by construction: a consumer that is not `cat` or `tee`, or a line that could
    carry the body onward, keeps its body matched.
    """
    if any(token in line for token in _CARRIES_ONWARD):
        return False
    try:
        lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return False
    index = 0
    while index < len(tokens) and re.fullmatch(r"[A-Za-z_]\w*=.*", tokens[index]):
        index += 1
    return index < len(tokens) and Path(tokens[index]).name in _WRITES_ITS_INPUT


def without_written_heredocs(command: str) -> str:
    """The command with the bodies of *written* heredocs removed.

    A heredoc body is data, not command — but only when nothing runs it. `bash <<EOF` and
    `cat > f <<EOF` differ **only** in the consumer, so nothing about the body can separate
    them and the consumer is the whole distinction.
    """
    lines = command.splitlines()
    kept: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        kept.append(line)
        index += 1
        match = _HEREDOC.search(line)
        if match is None or not _writes_rather_than_runs(line):
            continue
        delimiter = match.group("delim")
        while index < len(lines) and lines[index].strip() != delimiter:
            index += 1
        index += 1  # the terminator is not command either
    return "\n".join(kept)


def _segments(command: str) -> list[list[str]]:
    """The command split into the individual commands it actually runs.

    Lines first, because `shlex` cannot see them: `whitespace_split` makes a newline
    indistinguishable from a space, so `git add -A` and the `git commit` on the next line
    would arrive as one segment and only the first `git` would ever be looked at.
    """
    segments: list[list[str]] = [[]]
    for line in command.splitlines():
        if segments[-1]:
            segments.append([])
        lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        for token in lexer:
            if token in _SEPARATORS:
                segments.append([])
            else:
                segments[-1].append(token)
    return [s for s in segments if s]


def _is_git_commit(segment: list[str]) -> bool:
    index = 0
    # `FOO=bar git commit` runs git just as surely as `git commit` does, and so does the
    # `git commit` that follows a `then` or a `do`.
    while index < len(segment) and (
        segment[index] in _KEYWORDS or re.fullmatch(r"[A-Za-z_]\w*=.*", segment[index])
    ):
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


#: The subset of `_TAKES_A_VALUE` whose value **is a repository**. Written as a subset rather
#: than as a second list, and checked as one below: two lists of flags in one file, each missing
#: a member of the other, is precisely how this defect reached its third instance.
#:
#: `-c`, `--namespace` and `--exec-path` also take values and name no repository, which is why
#: this is a marked subset and not the whole set.
_NAMES_A_REPOSITORY = frozenset({"-C", "--git-dir", "--work-tree"})

#: The same repositories, named through the environment rather than through a flag.
#:
#: **Three more were considered and tested, and none of them belongs here.** `GIT_COMMON_DIR`,
#: `GIT_OBJECT_DIRECTORY` and `GIT_CEILING_DIRECTORIES` were each set alone, pointing at a second
#: repository on `main`, with `git commit --allow-empty` run from a repository on a branch:
#: **not one of them made the commit land in the other repository.** `GIT_COMMON_DIR` was the
#: strongest candidate, because it exists *for worktrees* and worktrees are this function's
#: subject; measured, it can break local ref resolution but it does not redirect the commit.
#:
#: The negative is written down because the next person will reach the same list — `GIT_COMMON_DIR`
#: is the obvious fourth guess — and re-derive the same answer. A checked negative recorded is
#: worth what a positive is; the cost of not recording it is that somebody runs it again.
_ENVIRONMENT_NAMES_A_REPOSITORY = ("GIT_DIR=", "GIT_WORK_TREE=")

#: Kept honest here rather than by memory. A flag that names a repository must be a flag that
#: takes a value, or `_is_git_commit` would step over it wrongly while `_target_of` read it.
assert _NAMES_A_REPOSITORY <= _TAKES_A_VALUE


def _repository(value: str) -> str:
    """`GIT_DIR` and `--git-dir` name the `.git` directory; the branch is read from beside it."""
    path = Path(value)
    return str(path.parent if path.name == ".git" else path)


def _target_of(segment: list[str]) -> str | None:
    """The repository this segment commits into, or None for the session's directory.

    **Three spellings of the same thing, and the file knew all three before this function did.**
    `git -C <path>`, `git --git-dir <path>` — space-separated, which is why `--git-dir` sits in
    `_TAKES_A_VALUE` without an `=` — and `git --git-dir=<path>`. The environment is a fourth.

    Each was missed in turn: `-C` was parsed only to skip its value, `GIT_DIR=` was known to the
    lexer and absent from the enumeration, and `--git-dir <path>` sat three lines above the
    enumeration in the set that records which flags carry values. **The same defect, three
    times, each time as a spelling the file already knew about somewhere else.**
    """
    for index, token in enumerate(segment):
        if token in _NAMES_A_REPOSITORY and index + 1 < len(segment):
            return _repository(segment[index + 1])
        for flag in _NAMES_A_REPOSITORY:
            if flag.startswith("--") and token.startswith(f"{flag}="):
                return _repository(token.split("=", 1)[1])
        for name in _ENVIRONMENT_NAMES_A_REPOSITORY:
            if token.startswith(name):
                return _repository(token.split("=", 1)[1])
    return None


def commit_targets(command: str) -> list[str | None] | None:
    """Every repository this command line commits into, or None if it commits nowhere.

    A list rather than a boolean, because **the branch to judge is the branch of the
    repository the command targets** — not of the directory the session happens to sit in. A
    session working in a worktree has its cwd in the shared checkout; judging there refused a
    safe commit and, worse, allowed `git -C <the checkout on main> commit` from a branch.

    An empty list is impossible: a command either commits somewhere or returns None.
    """
    try:
        segments = _segments(without_written_heredocs(command))
    except ValueError:
        return [None] if _COARSE.search(command) else None
    targets = [_target_of(s) for s in segments if _is_git_commit(s)]
    return targets or None


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
    if not isinstance(command, str):
        return 0
    targets = commit_targets(command)
    if targets is None:
        return 0
    cwd = event.get("cwd")
    here = Path(cwd) if isinstance(cwd, str) else Path.cwd()
    for target in targets:
        where = here / target if target is not None else here
        if current_branch(where) == PROTECTED:
            sys.stderr.write(_REFUSAL.format(branch=PROTECTED) + "\n")
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
