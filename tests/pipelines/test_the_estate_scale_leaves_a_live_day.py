"""The scale the estate loads carries a pre-period, a window, and a day after them.

**Three claims have to fit inside one world and the first arrangement fitted two of them.**

* the balance covariates declare an eight-week lookback, so the baseline must carry eight weeks
  before the window opens;
* the design form declares `max_duration` of eight weeks, so the window is eight;
* `run` drives *the day after the window closes*, held out by construction — and that day has to
  be a day the world actually generated. `erp.export` refuses one that is not, correctly, which
  would make the live day impossible rather than late.

`harness` is exactly sixteen weeks: eight and eight, and nothing left. `scenario` had the room and
could not carry the experiment at all — 384 units per arm needed against a control arm of
fourteen. `ESTATE` is the harness world with one more week, and `pipelines/window.py` reserves it.

## What it does not check

- **It does not check that the design is feasible.** That is the engine's answer, and it depends
  on the world's dispersion rather than on its calendar; `corpus/world/scale.py` carries the
  measurement that chose this world.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from corpus.world.scale import scale_by_name

from pipelines import window as window_module


#: The scale `infra/pipelines/variables.tf` defaults to. Read from Terraform rather than repeated,
#: so a change there is a change here — the two-declarations shape this register keeps finding.
def _declared_scale() -> str:
    import re
    from pathlib import Path

    variables = Path(__file__).resolve().parents[2] / "infra" / "pipelines" / "variables.tf"
    text = variables.read_text(encoding="utf-8")
    block = text[text.index('variable "corpus_scale"') :]
    found = re.search(r'default\s*=\s*"([^"]+)"', block)
    assert found, "infra/pipelines/variables.tf declares no default for corpus_scale"
    return found.group(1)


SCALE = _declared_scale()


def test_the_baseline_carries_the_covariates_lookback() -> None:
    opens, closes = window_module.baseline(SCALE)
    weeks = len(window_module.iso_weeks(opens, closes))
    assert weeks >= window_module.PRE_PERIOD_WEEKS, (
        f"the baseline of `{SCALE}` is {weeks} week(s) and the covariates declare a lookback of "
        f"{window_module.PRE_PERIOD_WEEKS}. A covariate measured over a shorter window is a "
        "covariate that says something other than what the contract says it says."
    )


def test_the_window_is_the_declared_duration() -> None:
    opens, closes = window_module.window(SCALE)
    weeks = len(window_module.iso_weeks(opens, closes))
    assert weeks == window_module.PERIOD_WEEKS, (
        f"the comparison window of `{SCALE}` is {weeks} week(s) and the design form declares "
        f"`max_duration` of {window_module.PERIOD_WEEKS}."
    )


def test_the_live_day_is_a_day_the_world_generated() -> None:
    scale = scale_by_name(SCALE)
    last = scale.start_date + timedelta(days=scale.days - 1)
    day = window_module.live_day(SCALE)
    assert scale.start_date <= day <= last, (
        f"`run` would drive {day} and `{SCALE}` runs {scale.start_date} to {last}.\n\n"
        "`erp.export` refuses a day the corpus does not have, so this is not a late live day — "
        "it is no live day at all. `pipelines/window.py` reserves "
        f"{window_module.LIVE_WEEKS} week(s) at the end for exactly this, and the world has to "
        "be long enough to give them."
    )


@pytest.mark.parametrize("name", ["estate"])
def test_the_declared_estate_world_is_the_one_this_gate_is_about(name: str) -> None:
    """If the default moves, this gate follows it — and says so when the new one does not fit."""
    assert name == SCALE or scale_by_name(SCALE).days >= scale_by_name(name).days, (
        f"the estate loads `{SCALE}`, which is shorter than `{name}`. The three windows above "
        "have to fit inside it, and this gate checks that they do — but a shorter world means "
        "the choice was made somewhere else and this comment is now the stale half."
    )
