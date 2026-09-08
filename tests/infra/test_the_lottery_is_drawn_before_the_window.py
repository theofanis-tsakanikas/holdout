"""`backfill` seals the lottery before it generates the days the lottery governs.

**This is the one ordering the whole repository rests on.** `CLAUDE.md`'s thesis is that an
uplift number produced without a valid holdout is a build failure, and a holdout is valid only if
the assignment was committed before the outcome existed. `pipelines/gold/assignment.py` refuses a
write at or after the period opens, and `corpus/world/__init__.py` says of the assignment
`prepare` applies by default that it is *a convenience and not a lottery*.

So the estate's history is two slices: the baseline under `all-control`, then the comparison
window under the arms `experiment_design` sealed. **Run in the other order — or with the design
step missing — every step still succeeds.** The window is generated, the readout runs, a number
comes out, and it is a number about an assignment nobody drew. Nothing raises, and that is what
this gate is for.

## What it does not check

- **It does not check that the arms reach the generator.** `--arms table` and the schema it reads
  are asserted by `tests/infra/test_a_task_names_its_catalog.py` and exercised end to end by
  `tests/pipelines/test_experiments.py`, which builds both slices and reads both out.
- **It reads the workflow, not a run.** A dispatch that was edited in the GitHub UI is invisible
  here, which is the same limit every gate over a file in this repository has.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKFILL = REPO_ROOT / ".github" / "workflows" / "backfill.yml"

#: The three jobs whose order is the claim, in the order that makes it true.
ORDER: tuple[str, ...] = (
    "job_history_baseline",
    "job_experiment_design",
    "job_history_window",
)


def _positions() -> dict[str, int]:
    """Where each job is first started in the workflow's script."""
    text = BACKFILL.read_text(encoding="utf-8")
    return {name: text.find(name) for name in ORDER}


def test_the_workflow_starts_all_three() -> None:
    """An absent job passes every ordering assertion below it and proves nothing."""
    assert BACKFILL.is_file(), f"{BACKFILL} is gone; this gate and the workflow move together."
    missing = [name for name, where in _positions().items() if where < 0]
    assert not missing, (
        f"backfill.yml never starts {missing}. Either the estate loads its history some other "
        "way now — which is a finding, because the way it loaded before generated arms nobody "
        "drew — or this reader stopped seeing the jobs and the order below is unchecked."
    )


def test_the_lottery_is_sealed_before_the_window_is_generated() -> None:
    where = _positions()
    ordered = sorted(ORDER, key=lambda name: where[name])
    assert ordered == list(ORDER), (
        f"backfill.yml runs {ordered}.\n\n"
        "The comparison window must be generated after the lottery is sealed and the baseline "
        "before it. Run the other way round, every step still succeeds and the readout states "
        "an uplift over an assignment that was drawn once the outcome was already on disk — "
        "which is the failure this repository exists to make impossible, arriving inside it.\n\n"
        f"The order is: {' -> '.join(ORDER)}"
    )
