"""The `plan` environment has no reviewer, and every other environment has one.

**Both halves are dangerous in opposite directions and only one of them is obvious.**

`infra/bootstrap/oidc.tf` trusts three subjects — `environment:plan`, `environment:deploy` and
`environment:destroy` — and the whole difference between them is what a human is required to do
before a token is issued. `deploy` and `destroy` wait for an approval. **`plan` deliberately does
not**, because a plan is read-only and a gate that waits for a human before showing him what he
is approving is a gate that gets approved blind.

**So the property that makes `plan` useful is the property that makes it dangerous**, and it is
one line of configuration: `each.key == "plan" ? [] : [1]`. Somebody reading `github.tf` later,
finding an environment with no reviewer beside two that have one, will read it as an omission and
"fix" it. That is not a hypothetical shape — it is `docs/FINDINGS.md`'s D3 arriving by the front
door: the approval is then granted *before* the plan exists, which is an approval of nothing, and
the estate ends up with two rubber stamps where it had none.

**And the other direction is worse and quieter.** A fourth environment added to
`local.environments` inherits `[1]` and looks protected. One added to the exempt side of the same
ternary inherits nothing, and no gate anywhere says so — `terraform validate` is green either
way, and the diff is four characters.

## The predicate is an allowlist, and that is the point of the file

The obvious form is *`plan` has no reviewers*, which is an assertion about one name and says
nothing about the fourth environment. **This asserts instead that every environment is
classified, and that the only name permitted to be reviewerless is one written down here with a
reason.** An unrecognised exempt name is a failure rather than a pass — `Money`'s rule one layer
over, *a bound that rounds toward what it forbids is not a bound*.

## What this guarantees, and what it does not

**It does not constrain what AWS will trust.** `oidc.tf`'s trust policy accepts
`:environment:plan` from any workflow in this repository, for ever, and no test that reads files
can change what a token says. What this file constrains is the configuration that decides whether
a human is asked — and it composes with two things rather than standing alone:

- `deployment_branch_policy { protected_branches = true }`, asserted below, which is why only
  `main` can dispatch to any of the three at all;
- `ci` being a required check, which is why an offending edit cannot reach `main`.

**Both halves are load-bearing and the first is still unproven against rulesets** —
`docs/FINDINGS.md`'s finding 3 asks whether a branch policy resolves a ruleset-protected default
branch, and it is first answered by the first dispatch. **If that fails open, this file is what is
left standing there**, which is worth knowing before it is written rather than after.

## The limits, declared rather than discovered

- **It reads one canonical spelling of the guard** — `<condition> ? [] : [<something>]`, where
  the condition is `each.key == "..."` terms joined by `||`. Any other spelling **raises** rather
  than passing: an instrument that cannot enumerate its population does not report zero. A legal
  rewrite therefore costs a red run, which is the safe direction and the same trade
  `tests/infra/test_variable_declarations.py` takes.
- **It reads configuration, not the account.** An environment whose reviewer was removed in the
  browser reads as protected here. `CLAUDE.md` says *IaC only. No console actions, ever*, and
  this file is one of the things that makes that rule checkable rather than a promise — but it
  checks the promise, not the account.
- **It says nothing about who the reviewer is.** `users = [var.github_owner_id]` names the author,
  and doctrine rule 5 — *nothing approves itself* — is a question about people that no test here
  can answer.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
INFRA = REPO_ROOT / "infra"

#: The environments permitted to have no reviewer, each with the reason it is on this list. A
#: name reaching the exempt side of the guard without being here is a failure, which is the
#: whole shape of this file: **refuse by default.**
#:
#: `plan` — a plan is read-only, it is what the approval on `deploy` is an approval *of*, and an
#: approval collected before the plan exists is D3.
REVIEWERLESS_BY_DESIGN = frozenset({"plan"})

#: A top-level `resource "github_repository_environment" "label" { ... }`. The closing brace is
#: anchored at column zero so the nested `deployment_branch_policy { ... }` does not end it early.
_ENVIRONMENT_RESOURCE = re.compile(
    r'^resource\s+"github_repository_environment"\s+"(?P<label>[^"]+)"\s*\{(?P<body>.*?)^\}',
    re.MULTILINE | re.DOTALL,
)

#: `environments = ["plan", "deploy", "destroy"]` in a `locals` block. This is the population the
#: resource iterates, so it is read from the same tree rather than restated here — a hand-kept
#: copy would be a second definition of a contract value, which is doctrine rule 3.
_ENVIRONMENTS_LOCAL = re.compile(r"^\s*environments\s*=\s*\[(?P<items>[^\]]*)\]", re.MULTILINE)

#: The `for_each` **inside** the `dynamic "reviewers"` block, told apart from the resource's own
#: `for_each` by indentation. `terraform fmt` is what makes that reliable, and `make terraform`
#: is what runs it.
_NESTED_FOR_EACH = re.compile(r"^ {4}for_each\s*=\s*(?P<expr>.+?)\s*$", re.MULTILINE)

#: The one spelling this gate reads: a condition, then an empty list, then a non-empty one.
_GUARD = re.compile(r"^(?P<cond>.+?)\s*\?\s*\[\s*\]\s*:\s*\[(?P<otherwise>[^\]]+)\]$")

#: `for_each = [1]` and `for_each = []` — the two spellings that carry no condition at all.
#: They are read rather than refused; see `_exempt` for the measurement that says why.
_LITERAL_LIST = re.compile(r"^\[(?P<items>[^\]]*)\]$")

_KEY_EQUALS = re.compile(r'each\.key\s*==\s*"(?P<name>[^"]+)"')

_QUOTED = re.compile(r'"(?P<name>[^"]+)"')

_PROTECTED_BRANCHES = re.compile(r"^\s*protected_branches\s*=\s*true\s*$", re.MULTILINE)


def _layers() -> list[Path]:
    if not INFRA.is_dir():
        return []
    return sorted(p for p in INFRA.iterdir() if p.is_dir() and any(p.glob("*.tf")))


def _declared_environments(layer: Path) -> list[str]:
    """The names `local.environments` holds, read out of the layer that declares them."""
    for path in sorted(layer.glob("*.tf")):
        match = _ENVIRONMENTS_LOCAL.search(path.read_text(encoding="utf-8"))
        if match:
            return [m.group("name") for m in _QUOTED.finditer(match.group("items"))]
    return []


def _exempt(expr: str, names: list[str], where: str) -> set[str]:
    """The environments the guard sends down the empty branch.

    Raises on any spelling it cannot read, rather than returning an empty set — an empty set
    would pass two of the three assertions below and report that nothing is exempt.

    **The two literal forms are read rather than refused, and that is not a convenience.** The
    likeliest real edit here is not a rewritten ternary: it is somebody deleting the condition,
    leaving `for_each = [1]`, because that is what "give `plan` a reviewer like the other two"
    looks like when you type it. Measured — that mutation was planted — refusing it produces a
    red about *parsing* for a change whose defect is D3, and the message a gate prints when it
    bites is most of what the gate is worth. `[]` is the same edit in the other direction.
    """
    literal = _LITERAL_LIST.match(expr)
    if literal is not None:
        return set(names) if not literal.group("items").strip() else set()
    guard = _GUARD.match(expr)
    if guard is None:
        raise AssertionError(
            f"{where}: the reviewers guard reads `{expr}`, which this gate cannot parse. It "
            "reads one spelling — `<condition> ? [] : [<something>]` — and refuses rather than "
            "guessing, because a guard it misreads is a guard it reports as safe. Either write "
            "it in that form or extend this gate to read the new one."
        )
    condition = guard.group("cond")
    matched = {m.group("name") for m in _KEY_EQUALS.finditer(condition)}
    residue = _KEY_EQUALS.sub("", condition).replace("||", "").replace("(", "").replace(")", "")
    if not matched or residue.strip():
        raise AssertionError(
            f"{where}: the reviewers condition reads `{condition}`, which is not a disjunction "
            f'of `each.key == "..."` terms (left over: `{residue.strip()}`). This gate reads '
            "only that form. Anything else — a negation, a `contains()`, a variable — inverts or "
            "hides which environments are exempt, and a gate that guesses wrong reports an "
            "unprotected environment as protected."
        )
    return matched


def _environments() -> list[tuple[str, str, list[str], str]]:
    """Every `(where, label, declared names, body)` this repository's Terraform creates."""
    found: list[tuple[str, str, list[str], str]] = []
    for layer in _layers():
        names = _declared_environments(layer)
        for path in sorted(layer.glob("*.tf")):
            source = path.read_text(encoding="utf-8")
            for match in _ENVIRONMENT_RESOURCE.finditer(source):
                found.append(
                    (
                        str(path.relative_to(REPO_ROOT)),
                        match.group("label"),
                        names,
                        match.group("body"),
                    )
                )
    return found


_ENVIRONMENTS = _environments()


def test_there_is_an_environment_resource_to_check() -> None:
    """An empty population passes everything below it and proves nothing.

    A rename of `infra/`, a layer losing its `.tf` files, or the environments moving to a module
    would otherwise turn this whole file green by emptying it.
    """
    assert _ENVIRONMENTS, (
        "no `github_repository_environment` resource is declared under infra/ — every assertion "
        "in this file would pass vacuously. If the environments moved, this gate moves with them."
    )
    for where, label, names, _ in _ENVIRONMENTS:
        assert names, (
            f"{where}: `{label}` exists and no `environments = [...]` local was found in its "
            "layer, so the population it iterates is unknown and nothing below is checked."
        )


@pytest.mark.parametrize(
    ("where", "label", "names", "body"),
    _ENVIRONMENTS,
    ids=[f"{where}::{label}" for where, label, _, _ in _ENVIRONMENTS],
)
def test_only_an_allowlisted_environment_may_have_no_reviewer(
    where: str, label: str, names: list[str], body: str
) -> None:
    guards = _NESTED_FOR_EACH.findall(body)
    assert len(guards) == 1, (
        f"{where}: `{label}` has {len(guards)} nested `for_each` expressions where this gate "
        'expects exactly one — the `dynamic "reviewers"` guard. With a second nested block '
        "present, the guard this reads may not be the reviewers one."
    )
    exempt = _exempt(guards[0], names, f"{where}::{label}")

    unknown = sorted(exempt - REVIEWERLESS_BY_DESIGN)
    assert not unknown, (
        f"{where}: `{label}` gives no reviewer to {unknown}, and that name is not in "
        f"REVIEWERLESS_BY_DESIGN. An environment with no reviewer issues a token to whoever can "
        "dispatch to it, with no human in between. If it genuinely should be unattended, add it "
        "to that set with the reason — the point of this gate is that the decision is written "
        "down rather than inherited from a ternary."
    )

    declared = set(names)
    missing = sorted(REVIEWERLESS_BY_DESIGN & declared - exempt)
    assert not missing, (
        f"{where}: `{label}` declares {missing} and gives it a required reviewer. That is D3: "
        "the approval is collected before the plan it approves exists, so a human is asked to "
        "sign for something he cannot read, and the protection is a ceremony. If a reviewer on "
        "that environment is now wanted, this set is where the reason is argued."
    )

    unprotected = sorted(declared - exempt)
    assert unprotected, (
        f"{where}: `{label}` gives no environment a required reviewer. `deploy` and `destroy` "
        "spend money and destroy evidence; the trust policy issues their tokens on a dispatch "
        "alone, and the reviewer is the only human in that path."
    )


@pytest.mark.parametrize(
    ("where", "label", "names", "body"),
    _ENVIRONMENTS,
    ids=[f"{where}::{label}" for where, label, _, _ in _ENVIRONMENTS],
)
def test_every_environment_is_reachable_only_from_a_protected_branch(
    where: str, label: str, names: list[str], body: str
) -> None:
    """The half that makes the reviewer worth having.

    An environment reachable from any branch is a reviewer approving a branch nobody reviewed —
    and for `plan`, which has no reviewer at all, it is the only thing standing between a pushed
    branch and a federated token.
    """
    assert _PROTECTED_BRANCHES.search(body), (
        f"{where}: `{label}` does not set `protected_branches = true`. Without it the "
        "environment can be targeted from any branch, so an unreviewed branch can dispatch to "
        "it — which makes the required reviewer an approval of a diff nobody read, and makes "
        "`plan` reachable from a branch that never passed `ci`."
    )
