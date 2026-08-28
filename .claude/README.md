# The AI layer, in this repository

CLAUDE.md names three mechanisms and one job each. This directory holds the second and the third.

| | is | acts | here |
|---|---|---|---|
| `CLAUDE.md`, layered | a **rule** | passively, wherever you are working | the repository root |
| Skill | a **procedure** | when you invoke it by name | `skills/` |
| Hook | a **guarantee** | the harness enforces it, wanted or not | `hooks/`, wired by `settings.json` |

A rule that holds wherever you are → `CLAUDE.md`. A procedure that recurs and carries
judgment → a skill. **Something that must never happen → a hook.**

Everything here is committed, so the skills and the hooks travel with the repository and go
through a pull request and CI like everything else. A guarantee that lives only on one laptop is
not one, and a method that lives only in a conversation is not reviewable.

## The skills

A skill lives **here** rather than at user level when it shapes the code in this repository, and
at `~/.claude/skills/` when it produces something outside it — CLAUDE.md's criterion, and the
reason `banner` and `readme-standard` are not here while these are.

| | is invoked for |
|---|---|
| `skills/claim/` | building one of the seven claims end to end: the eval, its `gate-proof` mutations, its `make claim-N`, and the statement of where the independence is and what is not proved |

Three more are declared in `CLAUDE.md` and not yet written: `defect-to-rule` (T00C),
`contract-change`, and `integration-review` (T008).

**A skill committed here is not a copy of a shared one. It is the record of the method that built
*this* project**, and it is not supposed to match the next repository — it is supposed to be
accurate about what happened here. `skills/claim/` is extracted from **two** closed claims rather
than one, because with one sample the shape is whatever that sample does; the second one is what
turns a template into a rule with a named variation, and it produced a finding while being written.

## The hooks — what is here, and what earns its place

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
  invisible to it, because there is no `Import` node to find. **The gate behind it no longer
  has that hole at module level**: `tests/boundary/test_corpus_imports_nothing.py` also
  imports every `corpus/` module with `holdout` unreachable through `sys.meta_path`, so a
  dynamic import taken at import time raises whatever it was spelled as. A dynamic import
  *inside a function* still runs neither check, and the hook remains blind to both — it reads
  source, and the source is where the ordinary mistake is.
  The first version of that test blocked `builtins.__import__`, which backs the `import`
  statement and nothing else, so it did not catch the case it was written for and stayed green
  while it did not. `tests/boundary/conftest.py` is the one implementation now and
  `tests/boundary/test_blocking.py` drives it with the spelling that defeated its predecessor.
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

`tests/skills/test_skills.py` is the same argument one directory along, and a much weaker one
because the failure is smaller: a skill whose frontmatter does not parse, or whose `name` does not
match its directory, does not load — it is a procedure nobody can invoke rather than a guarantee
silently not running. What that test does **not** check is whether the skill is *right*; nothing
can, and the claim targets, `make gate-proof` and oversight level 2 are what stand behind the
method it describes. Its own limits are stated in its docstring.
