"""A variable that says anywhere in its block that it has no default may not declare one.

**This exists because they did not.** `infra/lakehouse/dashboards.tf`'s `warehouse_id` said
*"declared with no default so that a layer applying these resources has to say which warehouse
rather than inheriting one somebody typed here"* — two lines above `default = ""`, whose comment
gave the reason as `validate-only`. The description asserted the absence of the thing declared
below it, and the default removed exactly the protection the description claimed: an apply that
forgot `warehouse_id` would not have stopped, it would have bound two dashboards to the warehouse
named by the empty string.

**The stated reason did not hold either.** Measured on the layer with the default removed,
`terraform init -backend=false && terraform validate` succeeds, and `terraform plan -input=false`
**stops** with *"The root module input variable "warehouse_id" is not set, and has no default
value."* So nothing needed the default and something needed its absence.

**Why a rule rather than an assertion about `warehouse_id`.** A test naming that one variable
would be a hand-kept population of one, and would say nothing to the next layer — and `T017` is
the next thing to touch `infra/`, which is the whole argument for landing this before it. The
class is *a stated intent contradicting its own declaration*, and it is checkable exactly
because the block is where somebody wrote down what they meant.

**It reads the whole `variable` block, not the `description` attribute, and that is deliberate.**
The phrase is looked for in the description, in comments and in anything else inside the braces.
Measured on two probes: a variable whose *comment* reads `# no default: this must be supplied per
environment` beside a `default = "x"` is **caught**, and description-scoped matching would have
missed it — the defect this file removed had half its reason in a comment (`# validate-only: T020
supplies the real one`).

**So the block is the correct scope rather than the convenient one**, and the distinction is
worth the sentence: an argument that narrowing would *cost* something — parsing both the heredoc
and the quoted form of `description` — is an argument from convenience, and it would not have
survived somebody willing to pay it. The argument that survives is that narrowing **misses a
defect**, and the probe above is what says so.

**What this does not prove, and the hole is the same shape as the guard.** It keys on a phrase
somebody chose to write, so it sees a contradiction only where the block states one:

- a variable that genuinely must have no default and **does not say so** is invisible here;
- so is one that says it in other words — *"supplied by the caller"*, *"required"*, *"never
  defaulted"* — none of which this reads;
- and it says nothing about whether a default that exists is a good one, whether the rest of a
  description is true, or whether a variable that should have been declared exists at all.

**And it over-reaches, in the safe direction, declared here rather than discovered.** Because it
reads the block, a variable whose comment merely contains the words — `# deliberately not a no
default case` — is refused although nothing about it is wrong. Measured: that probe fails by name.
It only ever refuses, never permits, so the cost is a false red rather than a missed default; the
fix in that case is to write the comment differently, and this sentence is what stops the next
reader treating the red as a mystery.

`parent_path` has a default, says nothing about not having one, and is right. **A guard that
overstated its reach here would be the joke `ops/figures.py` was built to prevent** — a gate
reporting what it examined as though that were what exists.

**And this is not a general *descriptions agree with declarations* gate, and does not claim to
be.** It is one clause, checkable because *no default* is a phrase with exactly one declaration
to compare against. **One instance is one instance.** `docs/reviews/phase-2.md` §8 is the
standing argument for not generalising early — *a rule generalised at three instances is scoped
to the forms those three wore* — and it applies here, so the next class waits for the next
instance rather than being inferred from this one.

**Why this one is written at a single instance anyway**, since §8's argument is the repository's
own and is not being waved at. Two things differ:

- **§8's subject is a hand-kept registry**, whose entries somebody maintains. This is an
  enumeration over a population read out of the tree, which is the shape `ops/figures.py` argues
  for by name — a rule, not a list — and the failure modes are not the same.
- **The asymmetry of waiting.** A stale registered figure is stale. **An unguarded `.tf` default
  is invisible to every gate that exists**: `make terraform` runs `validate`, which passed with
  the default and passes without it. Waiting for a second instance means the second instance
  arrives unnoticed, in a layer that costs money, written by whoever next wants `validate` quiet.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
INFRA = REPO_ROOT / "infra"

#: A top-level `variable "name" { ... }` block. The closing brace is anchored at column zero, so
#: a nested `validation { ... }` — indented, as `terraform fmt` writes it — does not end the
#: match early. A layer that indents a top-level block would defeat this, and `terraform fmt`
#: is what stops that being a thing anybody writes.
_VARIABLE = re.compile(
    r'^variable\s+"(?P<name>[^"]+)"\s*\{(?P<body>.*?)^\}', re.MULTILINE | re.DOTALL
)

#: The claim, as English rather than as a keyword, looked for **anywhere in the block** — the
#: description, a comment, or anything else between the braces. See the docstring for why the
#: description alone is not the scope, and for what that over-reach costs.
_SAYS_NO_DEFAULT = re.compile(r"no default", re.IGNORECASE)

#: The declaration. `default` may be commented out, and a `#` line is not a declaration.
_DECLARES_DEFAULT = re.compile(r"^[ \t]*default[ \t]*=", re.MULTILINE)


def _layers() -> list[Path]:
    if not INFRA.is_dir():
        return []
    return sorted(p for p in INFRA.iterdir() if p.is_dir() and any(p.glob("*.tf")))


def _variables() -> list[tuple[str, str, str]]:
    """Every `(layer, name, body)` declared under `infra/`, read out of the tree."""
    found: list[tuple[str, str, str]] = []
    for layer in _layers():
        for path in sorted(layer.glob("*.tf")):
            source = path.read_text(encoding="utf-8")
            for match in _VARIABLE.finditer(source):
                found.append(
                    (str(path.relative_to(REPO_ROOT)), match.group("name"), match.group("body"))
                )
    return found


def test_there_are_layers_and_variables_to_check() -> None:
    """An empty population passes every assertion below it and proves nothing.

    `ops/figures.py` states the rule this instantiates: an instrument that cannot answer raises
    rather than reporting zero. A layer added with no `.tf` file, or a rename of `infra/`, would
    otherwise turn this whole file green by emptying it.
    """
    assert _layers(), "infra/ holds no layer with a .tf file — this file would pass vacuously"
    assert _variables(), "no variable is declared under infra/ — nothing below asserts anything"


#: `layer::variable`, so a failure names the declaration rather than printing its body. The
#: default ids stringify every parameter, and a heredoc description makes that unreadable.
_VARIABLES = _variables()


@pytest.mark.parametrize(
    ("where", "name", "body"),
    _VARIABLES,
    ids=[f"{where}::{name}" for where, name, _ in _VARIABLES],
)
def test_a_variable_that_says_it_has_no_default_declares_none(
    where: str, name: str, body: str
) -> None:
    if not _SAYS_NO_DEFAULT.search(body):
        return
    assert not _DECLARES_DEFAULT.search(body), (
        f"{where}: `{name}` says somewhere in its block that it has no default, and declares "
        "one. A block that asserts the absence of the thing declared inside it is worse than one "
        "that says nothing: it tells the "
        "next reader a protection is in place, and the default is what removes it. An apply that "
        f"omits `{name}` will not stop — it will bind whatever the default says."
    )
