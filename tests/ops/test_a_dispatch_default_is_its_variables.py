"""A dispatch input that overrides a Terraform variable carries that variable's default.

**A default corrected where it is written and left standing where it is chosen is not a corrected
default.** `infra/foundation/variables.tf` renamed `create_metastore` to `owns_metastore` and
moved its default from `false` to `true`, with the reasoning at length: *a name describing an
event cannot express a state*, and `false` on a project that owns the region's metastore plans a
**destroy** of it and every catalog, schema, grant and external location in it. That change was
made the same day the destroy was planned for real and cancelled with seconds to spare.

`deploy.yml` passes `TF_VAR_owns_metastore: ${{ inputs.owns_metastore }}` unconditionally, so the
variable's default never applies to a dispatch. **The input's default stayed `false`** — still
carrying, in its own comment, the argument the variable had just abandoned. What a person gets by
opening *Run workflow* and pressing the button was unchanged by the fix.

## What it does

For every `TF_VAR_x: ${{ inputs.x }}` a workflow declares, it finds `variable "x"` under `infra/`
and requires the two defaults to agree. **Both are the same decision written twice**, which is the
shape this repository keeps finding: three lists of packages, two lists of models, and now two
defaults for one flag.

## What it does not check

- **It does not check that the default is right.** It checks that there is one of it. Which value
  is safe is an argument, and it belongs beside the variable where it already is.
- **Only variables a workflow overrides are in the population.** A variable no dispatch names has
  one default and cannot disagree with itself.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
INFRA = REPO_ROOT / "infra"

_OVERRIDES = re.compile(r"TF_VAR_(\w+):\s*\$\{\{\s*inputs\.(\w+)\s*\}\}")
_INPUT_DEFAULT = re.compile(
    r"^      (\w+):\n(?:^        .*\n)*?^        default:\s*(\S+)\s*$", re.MULTILINE
)
_VARIABLE_DEFAULT = re.compile(
    r'variable\s+"(\w+)"\s*\{(?:[^{}]|\{[^{}]*\})*?^\s*default\s*=\s*(\S+)\s*$',
    re.MULTILINE,
)


def _pairs() -> list[tuple[str, str, str, str]]:
    """`(workflow, name, dispatch default, variable default)` for every overridden variable."""
    variables: dict[str, str] = {}
    for path in sorted(INFRA.glob("*/variables.tf")):
        for name, value in _VARIABLE_DEFAULT.findall(path.read_text(encoding="utf-8")):
            variables.setdefault(name, value)

    found: list[tuple[str, str, str, str]] = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        inputs = dict(_INPUT_DEFAULT.findall(text))
        for variable, given in _OVERRIDES.findall(text):
            if variable in inputs and variable in variables and variable == given:
                found.append((path.name, variable, inputs[variable], variables[variable]))
    return found


PAIRS = _pairs()


def test_there_are_overrides_to_check() -> None:
    """An empty population passes every assertion below it and proves nothing."""
    names = {name for _w, name, _i, _v in PAIRS}
    assert "owns_metastore" in names, (
        "the override this gate was written for is not in the population, so either the flag "
        f"moved — which is a finding — or this reader stopped seeing it. Found: {sorted(names)}"
    )


@pytest.mark.parametrize(
    ("workflow", "name", "dispatch", "variable"),
    PAIRS,
    ids=[f"{w}::{n}" for w, n, _i, _v in PAIRS],
)
def test_the_dispatch_default_matches_the_variables(
    workflow: str, name: str, dispatch: str, variable: str
) -> None:
    assert dispatch == variable, (
        f"{workflow} offers `{name}` with a default of `{dispatch}` and "
        f"infra declares its default as `{variable}`.\n\n"
        "The workflow passes the input unconditionally, so the variable's default never reaches "
        "a dispatch: what a person gets by pressing Run workflow is the one above. Two defaults "
        "for one flag is one of them being wrong, and the one that is wrong is the one nobody "
        "re-reads.\n\n"
        "Change the input's default to match, and keep the argument for the value beside the "
        "variable where it already is."
    )
