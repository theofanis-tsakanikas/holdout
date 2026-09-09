"""A refused design prints what it needs, not only that it refused.

**On the estate the design step printed this and stopped:**

    fresh-ladder               REFUSED  UNDERPOWERED_FOR_CAPACITY, UNDERPOWERED_FOR_DURATION

Two codes and nothing to act on — not how many units the design needs, not how many the roster
has, not what would change either. The run then ended, so the only way to learn the number was to
dispatch again, which at this estate's size is about forty minutes.

`DesignRefusalReason` carries a `detail` and a `what_would_fix_it`, and refuses to exist without
both: *a refusal with no remedy is an obstacle*, in its own `__post_init__`. Printing the code
alone throws away the half that says what to do — which is the half a person reading a red run
actually needs.

> `evals/report.py` prints every check rather than the first, `promotion.Assessment.refusals` is
> plural, and `ops/run_job.sh` prints every failed task. This is the same rule, and the design
> step was the one place that broke it.
"""

from __future__ import annotations

import pytest
from pipelines.gold import experiments

from holdout.core.design import DesignRefusal, DesignRefusalReason
from holdout.core.design.codes import DesignRefusalCode


@pytest.fixture
def refusal() -> DesignRefusal:
    """The refusal the estate produced, with its own words in it."""
    return DesignRefusal(
        experiment_id="fresh-ladder",
        reasons=(
            DesignRefusalReason(
                code=DesignRefusalCode.UNDERPOWERED_FOR_CAPACITY,
                detail="100 units on the roster and 214 per arm are needed",
                what_would_fix_it="a larger roster, or an MDE the roster can carry",
            ),
        ),
    )


def test_the_detail_and_the_remedy_are_printed(
    refusal: DesignRefusal, capsys: pytest.CaptureFixture[str]
) -> None:
    experiments.report_refusal("fresh-ladder", refusal)
    printed = capsys.readouterr().out

    assert "UNDERPOWERED_FOR_CAPACITY" in printed, "the code is the one thing that was there"
    assert "214 per arm are needed" in printed, (
        "the detail is missing, which is the figure the refusal exists to carry. Without it a "
        "red run says a design is infeasible and not by how much."
    )
    assert "a larger roster" in printed, (
        "the remedy is missing. `DesignRefusalReason` will not exist without one, and printing "
        "the code alone discards it."
    )


def test_every_reason_is_printed_not_only_the_first(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A design can be refused three ways at once, and fixing one leaves the other two."""
    refusal = DesignRefusal(
        experiment_id="fresh-ladder-peeking",
        reasons=(
            DesignRefusalReason(
                code=DesignRefusalCode.STOPPING_RULE_PERMITS_PEEKING,
                detail="group-sequential with no spending function",
                what_would_fix_it="declare a spending function, or a single readout at the end",
            ),
            DesignRefusalReason(
                code=DesignRefusalCode.UNDERPOWERED_FOR_DURATION,
                detail="the smallest window reaching power is 31 weeks",
                what_would_fix_it="a longer max_duration, or a larger MDE",
            ),
        ),
    )
    experiments.report_refusal("fresh-ladder-peeking", refusal)
    printed = capsys.readouterr().out

    for expected in ("STOPPING_RULE_PERMITS_PEEKING", "31 weeks", "spending function"):
        assert expected in printed, (
            f"{expected!r} is not in the output, so a reader fixing the first reason would "
            "dispatch again to meet the second."
        )
