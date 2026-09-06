"""Every `run:` block in every workflow is shell this machine can parse.

**Written because one did not, and nothing in this repository could have said so.**
`deploy.yml`'s first job carried

    runs=$(gh api "…"  # a comment \\
             --jq '…')

and `#` starts a comment that runs to end of line, so it swallowed the continuation, `$(` never
closed, and the block was a syntax error. GitHub runs `run:` with `bash -e {0}`, so **every
dispatch would have died at the first step of the first job**, with a message about an unexpected
EOF and nothing about what was wrong — in the one workflow that spends money.

**It survived a YAML parse and that is the whole point.** *"177 lines, YAML parses"* was true: a
`run:` block is a literal block scalar and YAML is happy with any bytes inside it. **The check
examined the wrong population**, which is `CLAUDE.md`'s boxed rule wearing a different hat:

> *A gate reports on what it examined. It becomes a lie when it reports what it examined as if it
> were what exists.*

**How the population is enumerated**, per the same rule: every `run:` string in every job step of
every `*.yml` under `.github/workflows/`. Not a list — a walk, so a workflow added tomorrow is
covered by existing.

**What this does not prove**, stated rather than discovered:

* **that the shell is correct** — only that it parses. `bash -n` catches structure, not a wrong
  flag, a missing quote around an expansion, or a command that does not exist on the runner.
* **that the text examined is the text executed, and this is the largest of the limits.** GitHub
  substitutes `${{ }}` **before** the shell sees the script, so for any block containing one, the
  string parsed here is neither what `bash` would run nor what the runner will run. Measured:

      printf 'make ${{ matrix.target }}\n' | bash -n -   ->  exit 0
      printf 'make ${{ matrix.target }}\n' | bash    -   ->  bad substitution

  **`bash -n` accepts what `bash` itself refuses.** `ci.yml` carries seven such expressions and
  works, because GitHub has rewritten them to `make claim-2` long before a shell is involved.
  **The population is the uninterpolated text**; the executed text is produced on GitHub from
  values that do not exist locally and cannot be examined here.

  **The hardening that would close it is a rule rather than a check** — values reach `run:`
  through `env:` and never through `${{ }}` inline, which is also the documented defence against
  script injection. `deploy.yml` already does exactly that, measured at zero; `ci.yml`'s seven are
  safe today only because matrix values are written in the workflow itself rather than by a
  stranger. `docs/FINDINGS.md` carries it.
* **that it parses the way the runner's shell will.** This asserts against the `bash` on whichever
  machine runs the suite. GitHub's `bash -e {0}` is a different build, and a construct valid in
  one and not the other is outside this net — the same limit `ops/figures.py` records about ruff
  versions, and the same shape as the `grep -P` incident, where the tool that ran was not the tool
  assumed.
* **that a composite action's shell is examined.** Only `run:` inside this repository's own
  workflow files is walked.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"


def _run_blocks() -> list[tuple[str, str, str]]:
    """`(workflow, job, script)` for every `run:` in the tree, read out of the files."""
    found: list[tuple[str, str, str]] = []
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        for job, spec in (document.get("jobs") or {}).items():
            for index, step in enumerate(spec.get("steps") or []):
                if isinstance(step, dict) and "run" in step:
                    name = step.get("name") or f"step {index}"
                    found.append((path.name, f"{job} :: {name}", step["run"]))
    return found


BLOCKS = _run_blocks()


def test_every_workflow_file_is_walked() -> None:
    """An empty population proves nothing — **and so does a file emptying inside a full one.**

    A single `assert BLOCKS` is a guard at the population level, and under-coverage happens at
    the **file** level: if `deploy.yml` stopped yielding steps — a renamed key, `steps` becoming
    a string, an edit that reshapes `jobs` — the other file's blocks would keep the population
    truthy and this gate would stay green **while the workflow that spends money was examined by
    nothing.** That is `claims-complete` aggregating only what `discover` emitted, one layer
    along.

    So each file is reported. **A workflow with zero `run:` blocks is not an error** — a workflow
    of pure `uses:` steps legitimately has none — it is *examined and empty*, which is
    `make terraform`'s own wording for a directory under `infra/` that carries no `.tf`.
    """
    assert WORKFLOWS.is_dir(), ".github/workflows/ is not where this test looks for it"
    present = {p.name for p in WORKFLOWS.glob("*.y*ml")}
    assert present, "no workflow file at all — this file would pass vacuously"
    walked = {name for name, _, _ in BLOCKS}
    for name in sorted(present):
        print(f"  {name:16} {sum(1 for n, _, _ in BLOCKS if n == name):3} run-block(s)")
    assert present >= walked, f"walked a file that is not there: {walked - present}"
    assert BLOCKS, "no `run:` block in any workflow — the walker sees the files and no steps"


def test_every_run_block_is_bash() -> None:
    """`bash -n` is the right instrument only for blocks that are bash, and nothing said they are.

    A step may declare `shell: python`, `pwsh`, `sh` or a custom line, and `defaults.run.shell`
    may set it for a whole job or workflow with no key on the step at all. **The two directions
    are not symmetric.** `shell: python` would be a false red, which this repository has already
    accepted once — *the cost is a false red rather than a missed default*. **`shell: sh` would be
    a false green**, because `bash -n` accepts bashisms `sh` rejects, and that is under-coverage,
    which is the one direction `make figures` calls a lie.

    So the assumption becomes a checked precondition: the day a non-bash shell appears, this
    **names it** rather than quietly applying the wrong parser to it.
    """
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        declared = [((document.get("defaults") or {}).get("run") or {}).get("shell")]
        for job, spec in (document.get("jobs") or {}).items():
            declared.append(((spec.get("defaults") or {}).get("run") or {}).get("shell"))
            for step in spec.get("steps") or []:
                if isinstance(step, dict) and "run" in step:
                    declared.append(step.get("shell"))
            del job
        for shell in declared:
            assert shell in (None, "bash"), (
                f"{path.name} declares `shell: {shell}`. This file parses every `run:` block with "
                "`bash -n`; a block in another shell is examined by the wrong instrument, and for "
                "`sh` that is a false green rather than a false red."
            )


@pytest.mark.parametrize(
    ("workflow", "where", "script"),
    BLOCKS,
    ids=[f"{w}::{j}" for w, j, _ in BLOCKS],
)
def test_every_run_block_parses_as_shell(workflow: str, where: str, script: str) -> None:
    result = subprocess.run(
        ["bash", "-n", "-"], input=script, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, (
        f"{workflow} :: {where} is not shell bash can parse.\n"
        f"{result.stderr.strip()}\n\n"
        "GitHub runs `run:` with `bash -e {0}`, so this fails at the step rather than at the "
        "gate — and in a workflow that applies infrastructure, that is after an approval has "
        "been spent."
    )
