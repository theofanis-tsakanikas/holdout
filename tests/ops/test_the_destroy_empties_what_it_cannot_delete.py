"""A container Terraform owns, holding contents Terraform never made.

    Error: cannot delete registered model: Function 'holdout.gold.demand' is not empty.
    The function has 3 model versions(s)

**`destroy target=all` stopped there on 2026-09-10**, run 34466329417, with `serving` already
gone and `pipelines`, `lakehouse` and `foundation` untouched behind it. Unity Catalog refuses to
delete a registered model that holds versions, and `databricks_registered_model` takes no
`force_destroy` — measured against the provider's documentation, whose optional arguments for
that resource are `owner`, `comment` and `storage_location`. Every other Unity Catalog container
this repository declares does take it, and every one of them sets it: `databricks_catalog`,
`databricks_schema`, `databricks_metastore`.

**So the layer can create the model and cannot remove it once the estate has filled it**, and
the estate is what fills it — the training job writes versions, not Terraform.

## Why it took until the tenth to fire

`backfill` first succeeded end to end that morning. Every destroy before it ran against a model
with no versions, and an empty container deletes cleanly. **The absent test was not one nobody
thought of; it is one nobody can write** — *has this ever run against a full one* is a property
of the history, not of the tree. What can be written is this: if the tree declares a container
Terraform cannot empty, the teardown has to empty it.

## What this asserts

Every `databricks_registered_model` declared under `infra/` is matched by a `destroy.yml` whose
teardown loop **empties the model before it destroys the layer** — either by deleting versions
inline or by calling a shell function that does.

**The first version of this file asserted something weaker and a planted mutation said so.** It
required the text `databricks model-versions delete` to occur before `terraform ... destroy`
anywhere in the step. Deleting the call site left the function *definition* standing above the
loop, the text still occurred in the right order, and the gate stayed green over a workflow that
would have failed exactly the way the one it was written for did. **A command defined is not a
command run**, and the function's name is discovered from the script rather than typed here, so
renaming it does not quietly empty the population.

**Measured biting, three planted mutations, each restored after:**

    the call site deleted, the function left standing   ->  red
    the call moved below `terraform destroy`            ->  red
    the deletion itself replaced with `true`            ->  red
    the tree as it stands                               ->  green

The first of those is the one this file was green over before it was rewritten.

## What it does not check

- **It does not check that the emptying works**, only that it is dispatched before the thing it
  has to precede. The account is the only thing that can answer the first question, and the step
  at the end of `destroy.yml` is what asks it.
- **It does not enumerate other resource types with the same defect.** One is known, by having
  failed. A list of types written from imagination would be the second definition of a provider
  schema this repository does not read.
- **It reads text, not order of execution** — the same limit `tests/ops/test_cli_is_installed.py`
  declares about `run:` blocks.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
INFRA = REPO_ROOT / "infra"
DESTROY = REPO_ROOT / ".github" / "workflows" / "destroy.yml"

_COMMENT = re.compile(r"^\s*#.*$", re.MULTILINE)
_MODEL = re.compile(r'resource\s+"databricks_registered_model"\s+"([^"]+)"')

#: The deletion, and the command that has to come after it. Matched on the subcommand rather than
#: on a whole line, so reformatting the script does not empty this gate's population.
_EMPTIES = re.compile(r"databricks\s+model-versions\s+delete\b")
_DESTROYS = re.compile(r"terraform\s+-chdir=[^\s]+\s+destroy\b")

#: The loop that walks the layers, and a shell function definition. Both are read out of the
#: script so that this file names no identifier the script could rename underneath it.
_LOOP = re.compile(r"for\s+layer\s+in\s+\$layers;\s*do\n(?P<body>.*?)\n\s*done\b", re.DOTALL)
_FUNCTION = re.compile(r"^\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\{", re.MULTILINE)


def _emptying_names(script: str) -> set[str]:
    """Every shell function in `script` whose body deletes a model version.

    The body is taken as everything from the definition to the next definition or the end, which
    is coarse and is stated as coarse: two functions where the second deletes and the first does
    not would both be named. It errs toward accepting, and the assertion it feeds errs toward
    refusing, so the pair does not quietly widen.
    """
    defined = list(_FUNCTION.finditer(script))
    names: set[str] = set()
    for index, match in enumerate(defined):
        end = defined[index + 1].start() if index + 1 < len(defined) else len(script)
        if _EMPTIES.search(script[match.start() : end]):
            names.add(match.group("name"))
    return names


def _declared_models() -> list[str]:
    """Every `<layer>::<name>` a `databricks_registered_model` is declared under."""
    found: list[str] = []
    for path in sorted(INFRA.glob("*/*.tf")):
        text = _COMMENT.sub("", path.read_text(encoding="utf-8"))
        for name in _MODEL.findall(text):
            found.append(f"{path.parent.name}::{name}")
    return found


def _destroy_scripts() -> list[str]:
    """Every `run:` block in `destroy.yml` that runs `terraform destroy`."""
    document: Any = yaml.safe_load(DESTROY.read_text(encoding="utf-8"))
    scripts: list[str] = []
    for spec in (document.get("jobs") or {}).values():
        for step in spec.get("steps") or []:
            if isinstance(step, dict) and _DESTROYS.search(str(step.get("run", ""))):
                scripts.append(str(step["run"]))
    return scripts


MODELS = _declared_models()
SCRIPTS = _destroy_scripts()


def test_there_is_a_model_to_empty() -> None:
    """An empty population passes everything below it and proves nothing.

    If this goes red because no layer declares a registered model any more, that is a finding
    about the estate and not a reason for the assertions under it to pass in silence.
    """
    assert INFRA.is_dir(), "infra/ is not where this test looks for it"
    assert MODELS, (
        "no layer under infra/ declares a databricks_registered_model. Either nothing registers "
        "a model version any more -- which would mean the ml layer no longer owns the thing "
        "backfill trains -- or this reader stopped seeing it."
    )
    for model in MODELS:
        print(f"  {model}")


def test_there_is_a_teardown_to_check() -> None:
    """The same guard for the other half of the pair."""
    assert SCRIPTS, (
        "no step in destroy.yml runs `terraform destroy`. Either the teardown works some other "
        "way now, or this reader stopped seeing it -- and the case below would pass over a "
        "workflow that destroys nothing."
    )


@pytest.mark.parametrize("script", SCRIPTS, ids=[f"script-{i}" for i in range(len(SCRIPTS))])
def test_the_teardown_empties_the_model_before_it_destroys_the_layer(script: str) -> None:
    assert _EMPTIES.search(script), (
        f"infra/ declares {len(MODELS)} registered model(s) -- {', '.join(MODELS)} -- and this "
        "step deletes no model version anywhere. Unity Catalog refuses to delete a registered "
        "model that holds versions, and the provider offers no force_destroy for it, so the "
        "destroy stops on the ml layer with serving already gone and everything below it still "
        "standing and still billing."
    )

    loop = _LOOP.search(script)
    assert loop, (
        "this step destroys layers but not in a `for layer in $layers` loop any more. The "
        "assertion below reads that loop's body to find out what runs before the destroy, so a "
        "teardown shaped differently needs this reader taught the new shape rather than left "
        "passing over it."
    )

    body = loop.group("body")
    destroys = _DESTROYS.search(body)
    assert destroys, "the loop body no longer runs `terraform destroy`"

    before = body[: destroys.start()]
    inline = _EMPTIES.search(before) is not None
    called = any(
        re.search(rf"(?:^|[\s;&|(]){re.escape(name)}\b", before) for name in _emptying_names(script)
    )

    assert inline or called, (
        "the layer is destroyed without the model being emptied first. The deletion exists in "
        "this step -- it just never runs before `terraform destroy`, which is the only place it "
        "can do any good. **A command defined is not a command run**: this assertion reads the "
        "loop body, because the first version of it read the whole step and stayed green when "
        "the call site was deleted and the function was left standing."
    )
