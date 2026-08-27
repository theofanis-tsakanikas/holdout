# The AI layer, in this repository

CLAUDE.md names three mechanisms and one job each. This directory holds the third.

| | is | acts |
|---|---|---|
| `CLAUDE.md`, layered | a **rule** | passively, wherever you are working |
| Skill | a **procedure** | when you invoke it by name |
| Hook | a **guarantee** | the harness enforces it, wanted or not |

A rule that holds wherever you are → `CLAUDE.md`. A procedure that recurs and carries
judgment → a skill. **Something that must never happen → a hook.**

`settings.json` is committed, so the hooks travel with the repository and go through a pull
request and CI like everything else. A guarantee that lives only on one laptop is not one.

## What is here, and what earns its place

| | fires on | refuses |
|---|---|---|
| `hooks/corpus_isolation.py` | `Write` · `Edit` · `MultiEdit`, and after every `Bash` | a module under `corpus/` that imports `holdout` **or** `src.holdout` |
| `hooks/main_guard.py` | `Bash` | `git commit` while on `main` |

`NotebookEdit` is deliberately not wired. The barrier covers `*.py`, which is what the gate
behind it covers, so a notebook was never policed and listing the tool was wiring that could
not fire. Advertising a guarantee that cannot run is worse than not having it.

**The bar is deliberately high: a hook that duplicates a check CI already makes green-or-red
does not belong here.** Both of these have a gate behind them already, and neither is that
gate:

- The corpus barrier's gate is `tests/boundary/test_corpus_imports_nothing.py`. It runs on
  every push, `main` cannot take a violation, and it is not going anywhere. What it cannot do
  is run *now* — so a session can build for an hour on top of a barrier that is already gone
  and find out at the end. The rule itself lives in `ops/isolation.py` and has exactly one
  implementation; the test and the hook are its two callers, at two different moments.
- The commit guard's gate is the `main` ruleset, which has no bypass actors and refuses the
  *push* by name. What it cannot do is stop the commit from being made — and the cost of that
  is not a broken `main`, it is the twenty minutes of `git reset` before the pull request can
  be opened, and the temptation at minute nineteen to just push.

## Both fail open on input they cannot read

A hook that dies on a malformed event takes the session's editing with it, and a hook that has
to be switched off to get work done is a hook that gets switched off. The test and CI remain
the gate. Failing open here costs a turn; failing closed costs the session.

## How an edit is read

An `Edit` hands over a *fragment*, not a module, and a fragment read on its own is read badly:
an indented block does not parse, an import after a semicolon is invisible to a line-anchored
scan, and a line inside a docstring looks exactly like code. So the fragment is not read on its
own — the file is read from disk, the edit applied to a copy, and what gets checked is the
module the write would actually produce. `ops.isolation.offences` then tries the AST, then the
AST over a dedented copy, and only what survives both reaches the text scan. Each step down is
a step toward guessing, so each is taken only when the one above has failed.

## What the hooks do not catch, stated rather than assumed

- `corpus_isolation` refuses the **write** it is shown. A file written by `Bash` — a heredoc,
  a `sed -i`, a generator script — reaches no `PreToolUse` hook with a `file_path`, so the
  same hook re-reads `corpus/` from disk after every `Bash` call. That is a `PostToolUse`
  hook: it surfaces the violation in the turn that created it and it **cannot un-write the
  file**. It is not the guarantee. The test is.
- `corpus_isolation` reads imports, not behaviour. `importlib.import_module("holdout")` is
  invisible to it, exactly as it is to the boundary test, and always has been.
- The text scan — reached only for a fragment that survives both parse attempts, which in
  practice means an `Edit` against a file that does not exist — is line-anchored, so it cannot
  see `x = 1; import holdout`. `tests/boundary/` asserts that limit directly rather than
  leaving it for whoever hits it.
- `main_guard` reads the command line it is given. A `git commit` inside a shell script the
  command *invokes* is not on that command line. It also judges the branch by the session's
  working directory, so `git -C elsewhere commit` is refused on the strength of *this*
  repository's branch — the safe direction, and a case that does not arise here.
- On a command line `shlex` cannot tokenise — an unbalanced quote, most often a heredoc with
  an apostrophe in it — `main_guard` falls back to a narrow grep that requires `git` at a
  plausible command position. It can still be wrong in both directions there; it is the one
  place the code guesses, and it guesses toward refusing.
- Neither hook runs for anyone editing this repository without the harness. That is what CI
  is for, and why `make check` covers `ops/` and `.claude/hooks/` on the same terms as `src/`.

## The wiring is tested too

`settings.json` could name a file that does not exist, the exec bit could be cleared, the
shebang could be wrong — and every one of those leaves the suite green with both guarantees
silently dead, which is worse than never claiming them. `tests/hooks/test_settings.py` reads
this file, resolves each command, and runs each hook **through its shebang** rather than by
handing it to an interpreter. It also asserts that every hook on disk is wired and every wired
hook is on disk.
