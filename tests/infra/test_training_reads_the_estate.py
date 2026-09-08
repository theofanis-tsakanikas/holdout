"""The training job trains on the estate's silver, and registers what it trained.

**`infra/ml/training.tf` describes its job as *Trains on the estate, runs the five promotion
gates, registers a version only if they pass*, and for three of those clauses that was a
description of nothing.** `pipelines/ml/__main__.py` had one path: build a rehearsal corpus in a
temporary directory, load it, train on it, print the assessment, exit zero. The eight months
`backfill` loads were never opened. Nothing in the repository imported `mlflow` at all, so no
version was ever created — while `backfill.yml` read `databricks model-versions list` and took
the highest one, and `infra/serving` pointed an endpoint at it.

**Every part of that ran green.** A model fitted on a freshly generated world is a model, the job
succeeds, and the number `run` would publish would belong to data the estate has never seen —
which is `CLAUDE.md`'s own thesis, failing one layer below the number it is about.

So two flags decide whether this job does what its description says, and this asserts both.

## What it does not check

- **It does not check that a version appears.** That needs the estate; `backfill` is where it is
  measured, and it now fails loudly rather than silently if none does.
- **It does not check the schema's name is right.** A wrong schema fails at read time with a
  refusal naming the missing table, which is a cheap signal.
"""

from __future__ import annotations

import pytest

from tests.infra import tasks

TRAINING = [
    (where, parameters)
    for where, parameters in tasks.parameter_lists()
    if parameters and parameters[0] == "pipelines.ml"
]

#: Each flag, and what its absence would mean rather than what it is called.
REQUIRED = {
    "--silver-schema": (
        "the job would build a rehearsal corpus in a temporary directory and train on that, "
        "leaving the history backfill loaded unread"
    ),
    "--model": (
        "the job would train, print its assessment and register nothing, and the step after it "
        "would look for a version that was never created"
    ),
}


def test_there_is_a_training_task_to_check() -> None:
    """An empty population passes every assertion below it and proves nothing."""
    assert TRAINING, (
        "no task under infra/ runs `pipelines.ml`. Either training moved — which is a finding — "
        "or this reader stopped seeing it."
    )


@pytest.mark.parametrize("flag", sorted(REQUIRED))
def test_the_training_task_passes(flag: str) -> None:
    for where, parameters in TRAINING:
        assert flag in parameters, (
            f"{where} runs `pipelines.ml` without `{flag}`, so {REQUIRED[flag]}.\n\n"
            "The job succeeds either way. That is the whole reason this is a gate."
        )
