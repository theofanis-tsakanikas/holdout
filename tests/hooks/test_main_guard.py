"""`git commit` on `main` is refused at the only moment at which refusing it is free.

The repository ruleset already refuses the *push*, with no bypass actors, and that is the
gate. What it cannot do is stop the commit from being made — and a session that has committed
three times to a local `main` has to unpick them before it can open the pull request every
piece of work goes through. The cost of the missing guard is not a broken `main`; it is the
twenty minutes of `git reset` and the temptation, at minute nineteen, to just push.

The tests run against real repositories in `tmp_path`, because "am I on `main`" is a question
only git can answer and stubbing it would test the stub.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

HOOK = "main_guard.py"


def _repo(path: Path, branch: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", branch, "-q"], cwd=path, check=True)
    return path


@pytest.fixture
def on_main(tmp_path: Path) -> Path:
    return _repo(tmp_path / "on-main", "main")


@pytest.fixture
def on_a_branch(tmp_path: Path) -> Path:
    return _repo(tmp_path / "on-a-branch", "ops/hooks")


def _bash(command: str, cwd: Path) -> dict[str, Any]:
    return {
        "hook_event_name": "PreToolUse",
        "cwd": str(cwd),
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }


REFUSED = [
    pytest.param("git commit -m 'wip'", id="the plain one"),
    pytest.param("git commit --amend --no-edit", id="an amend is still a commit"),
    pytest.param("make check && git commit -m 'x'", id="after a separator"),
    pytest.param("git add -A; git commit -m 'x'", id="after a semicolon"),
    pytest.param("git -c user.email=x@y.z commit -m 'x'", id="behind a -c that takes a value"),
    pytest.param("GIT_AUTHOR_NAME=x git commit -m 'y'", id="behind an environment assignment"),
    pytest.param("git --no-pager commit -m 'x'", id="behind a valueless option"),
    pytest.param("/usr/bin/git commit -m 'x'", id="by absolute path"),
    # Everything below was allowed by the first version of this hook. `_SEPARATORS` listed a
    # newline, but `shlex` with `whitespace_split` never produces a newline token, so every
    # line after the first joined the first command and only its first `git` was looked at.
    # The guard bit the form a reviewer would type into a test and missed the form a session
    # actually writes.
    pytest.param("git add -A\ngit commit -m 'x'", id="on the next line — the ordinary form"),
    pytest.param("echo hi > f.txt\ngit commit -am 'x'", id="on the next line, after anything"),
    pytest.param("if true; then git commit -m 'x'; fi", id="after a `then`"),
    pytest.param("for f in a; do git commit -m 'x'; done", id="after a `do`"),
]


@pytest.mark.parametrize("command", REFUSED)
def test_it_refuses_a_commit_on_main(fire: Callable[..., Any], on_main: Path, command: str) -> None:
    fired = fire(HOOK, _bash(command, on_main), cwd=on_main)
    assert fired.refused, f"{command!r} was allowed on main: {fired.stdout}"
    assert "Never commit to `main`" in fired.stderr
    assert "git checkout -b" in fired.stderr, "a refusal that does not name the fix is a wall"


@pytest.mark.parametrize("command", REFUSED)
def test_the_same_commands_are_fine_on_a_branch(
    fire: Callable[..., Any], on_a_branch: Path, command: str
) -> None:
    """The rule is one branch per closed piece of work — inside it, commit freely and often."""
    fired = fire(HOOK, _bash(command, on_a_branch), cwd=on_a_branch)
    assert fired.code == 0, fired.stderr


ALLOWED_ON_MAIN = [
    pytest.param("git status", id="git, but not commit"),
    pytest.param("git log --oneline -5", id="reading"),
    pytest.param("git push origin main", id="push — the ruleset refuses it by name"),
    pytest.param('echo "git commit -m x"', id="the words, not the command"),
    pytest.param("grep -rn 'git commit' docs/", id="the words in an argument"),
    pytest.param("make check", id="nothing to do with git"),
    pytest.param(
        "cat > notes.md <<'EOF'\nDon't run git commit here\nEOF",
        id="prose in a heredoc whose apostrophe breaks the lexer",
    ),
]


@pytest.mark.parametrize("command", ALLOWED_ON_MAIN)
def test_it_does_not_refuse_what_is_not_a_commit(
    fire: Callable[..., Any], on_main: Path, command: str
) -> None:
    """A guard that fires on `echo \"git commit\"` gets switched off within the week."""
    fired = fire(HOOK, _bash(command, on_main), cwd=on_main)
    assert fired.code == 0, f"{command!r} was refused on main: {fired.stderr}"


def test_a_command_it_cannot_tokenise_is_refused_rather_than_waved_through(
    fire: Callable[..., Any], on_main: Path
) -> None:
    """An unbalanced quote is the one case where the safe direction costs only a retry."""
    fired = fire(HOOK, _bash('git commit -m "oops', on_main), cwd=on_main)
    assert fired.refused, fired.stdout


def test_a_detached_head_is_not_on_main(fire: Callable[..., Any], tmp_path: Path) -> None:
    """Detached is not `main`, so there is nothing to refuse — and saying so is the honest answer."""
    repo = _repo(tmp_path / "detached", "main")
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@e.st",
            "-c",
            "user.name=t",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "root",
        ],
        cwd=repo,
        check=True,
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()
    subprocess.run(["git", "checkout", "-q", head], cwd=repo, check=True)
    fired = fire(HOOK, _bash("git commit -m 'x'", repo), cwd=repo)
    assert fired.code == 0, fired.stderr


def test_an_unborn_main_is_still_main(fire: Callable[..., Any], on_main: Path) -> None:
    """A repository with no commit yet is on `main`, and its first commit is the one refused."""
    fired = fire(HOOK, _bash("git commit -m 'initial'", on_main), cwd=on_main)
    assert fired.refused, fired.stdout


def test_it_ignores_every_tool_that_is_not_bash(fire: Callable[..., Any], on_main: Path) -> None:
    event = {
        "hook_event_name": "PreToolUse",
        "cwd": str(on_main),
        "tool_name": "Write",
        "tool_input": {"file_path": "x.py", "content": "git commit -m 'x'"},
    }
    fired = fire(HOOK, event, cwd=on_main)
    assert fired.code == 0, fired.stderr


def test_it_fails_open_on_input_it_cannot_read(fire: Callable[..., Any], on_main: Path) -> None:
    fired = fire(HOOK, "{ not json", cwd=on_main)
    assert fired.code == 0, fired.stderr


# ------------------------------------------- the repository the command targets, not the cwd
#
# Two defects, one sentence: **the guard was judged against something other than the command it
# was refusing** — the wrong directory here, the wrong text below. Both were found on
# 2026-08-31 by two sessions sharing a checkout, which is the arrangement `CLAUDE.md`'s git rule
# requires and the one nothing had ever been run against.


def _worktree(of: Path, at: Path, branch: str) -> Path:
    subprocess.run(["git", "worktree", "add", "-q", str(at), "-b", branch], cwd=of, check=True)
    return at


def test_a_commit_into_a_worktree_on_a_branch_is_allowed(
    on_main: Path, tmp_path: Path, fire: Callable[..., Any]
) -> None:
    """The safe commit the old hook refused.

    A session whose cwd is the shared checkout, committing into a worktree that is on a branch.
    The old version read `event["cwd"]`, found `main`, and refused — blocking exactly the
    workflow two sessions sharing a repository are required to use.
    """
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "root"], cwd=on_main, check=True)
    tree = _worktree(on_main, tmp_path / "wt", "ops/somewhere")
    assert fire(HOOK, _bash(f"git -C {tree} commit -m 'x'", on_main)).code == 0


def test_a_commit_into_the_checkout_on_main_is_refused_from_a_branch(
    on_main: Path, tmp_path: Path, fire: Callable[..., Any]
) -> None:
    """The dangerous direction, which the old hook **allowed**.

    A session whose cwd is on a branch, committing into the checkout that is on `main`. The old
    version judged the session's directory, found a branch, and let it through — the guard
    permitting exactly what it exists to prevent.
    """
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "root"], cwd=on_main, check=True)
    tree = _worktree(on_main, tmp_path / "wt", "ops/elsewhere")
    assert fire(HOOK, _bash(f"git -C {on_main} commit -m 'x'", tree)).code == 2


def test_the_environment_names_a_repository_too(
    on_main: Path, tmp_path: Path, fire: Callable[..., Any]
) -> None:
    """`GIT_DIR` is a fourth spelling, and the first fix enumerated only the flags.

    Two places in the hook already handled environment assignments — `_COARSE`'s prefix and
    `_is_git_commit`'s skip — and the third forgot they exist. Found by review of the fix, which
    is the original defect surviving its own repair in a different spelling.
    """
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "root"], cwd=on_main, check=True)
    tree = _worktree(on_main, tmp_path / "wt", "ops/env")
    assert fire(HOOK, _bash(f"GIT_DIR={on_main}/.git git commit -m 'x'", tree)).code == 2
    assert (
        fire(
            HOOK, _bash(f"GIT_WORK_TREE={on_main} GIT_DIR={on_main}/.git git commit -m 'x'", tree)
        ).code
        == 2
    )


def test_the_environment_can_also_name_a_safe_repository(
    on_main: Path, tmp_path: Path, fire: Callable[..., Any]
) -> None:
    """The mirror, so the fix refuses the **right** repository rather than merely more of them."""
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "root"], cwd=on_main, check=True)
    tree = _worktree(on_main, tmp_path / "wt", "ops/mirror")
    assert fire(HOOK, _bash(f"GIT_DIR={tree}/.git git commit -m 'x'", on_main)).code == 0


# ------------------------------------------------------ a heredoc body is data, unless it runs


def test_a_heredoc_that_writes_prose_about_a_commit_is_allowed(
    on_main: Path, fire: Callable[..., Any]
) -> None:
    """The false positive that made two sessions work around the guard in one hour.

    It needs **both** an apostrophe — which unbalances `shlex` and drops to `_COARSE` — and a
    shell operator inside the quoted text for `_COARSE` to match after. The docstring's own
    example, `Don't run git commit here`, is the half-case that works, which is why its author
    believed it closed.
    """
    quoted = "`git add -A && git commit`"
    command = f"cat > note.md <<'EOF'\nIt caught {quoted} on one line and didn't on two.\nEOF"
    assert fire(HOOK, _bash(command, on_main)).code == 0


def test_a_heredoc_written_to_a_file_is_allowed_even_when_its_body_is_a_command(
    on_main: Path, fire: Callable[..., Any]
) -> None:
    """A runbook documenting a git command is a file, not a commit.

    This route never reaches `_COARSE`: lines are split, the body line tokenises cleanly, and
    `_is_git_commit` returns true. `bash <<EOF` and `cat > f <<EOF` with identical bodies got
    identical verdicts, and **the two commands differ only in the consumer** — so nothing about
    the body can separate them.
    """
    assert fire(HOOK, _bash("cat > runbook.md <<'EOF'\ngit commit -m x\nEOF", on_main)).code == 0


@pytest.mark.parametrize(
    "command",
    [
        pytest.param("bash <<'EOF'\ngit commit -m x\nEOF", id="bash runs its body"),
        pytest.param("sh <<'EOF'\ngit commit -m x\nEOF", id="sh runs its body"),
        pytest.param("cat <<'EOF' | bash\ngit commit -m x\nEOF", id="a pipe carries it onward"),
        pytest.param("python3 - <<'EOF'\ngit commit -m x\nEOF", id="python runs its body"),
        pytest.param("x=$(cat <<'EOF'\ngit commit -m x\nEOF\n)", id="a substitution may run it"),
    ],
)
def test_an_executed_heredoc_keeps_its_body_matched(
    command: str, on_main: Path, fire: Callable[..., Any]
) -> None:
    """The whitelist is two consumers, and everything else fails closed.

    `python` is refused **deliberately**: its body executes and can reach git through
    `os.system` or a subprocess with no line beginning with `git`, so no pattern over the body
    would see it. **The workaround is the editor tool, not a wider list** — a refusal recorded
    as a false positive is a refusal somebody later removes.
    """
    assert fire(HOOK, _bash(command, on_main)).code == 2
