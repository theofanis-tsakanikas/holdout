"""The ledger is a gate, so something has to break it on purpose.

`make gate-proof` no longer executes anything — it audits that every planted mutation is
owned by exactly one `claim-N` target. That makes it the one gate in this repository that
cannot be proved by a `gate-proof` mutation, because it *is* `gate-proof`. So it is proved
here instead, the same way and to the same standard: every check is shown to fail on a
deliberately broken arrangement, not merely to pass on the real one.

A gate that has only ever been seen green has not been tested. That applies to the accountant
as much as to anything it counts.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from evals.gate_proof import ledger
from evals.gate_proof.engine import Mutation

REPO = Path(__file__).resolve().parents[2]


def _mutation(
    *,
    identity: str = "a-break",
    claim: int = 1,
    directory: str | None = None,
    file: str = "src/holdout/core/money.py",
    anchor: str = "class MoneyError(TypeError):\n",
) -> Mutation:
    parent = directory if directory is not None else f"claim-{claim}"
    return Mutation(
        source=ledger.MUTATIONS_DIR / parent / f"{identity}.yaml",
        id=identity,
        claim=claim,
        eval_module="evals.guardrail",
        targets=("G2.certified-price-inside-exact-bounds",),
        breaks="something",
        file=file,
        anchor=anchor,
        replacement="class MoneyError(ValueError):\n",
    )


def _makefile(body: str) -> tuple[ledger.Target, ...]:
    return ledger.targets(textwrap.dedent(body))


# ------------------------------------------------------------------ the Makefile parser


def test_a_recipe_belongs_to_the_target_above_it() -> None:
    parsed = {
        t.name: t.recipe
        for t in _makefile("""\
        claim-1:  ## a claim
        \t$(RUN) python -m evals.guardrail
        \t$(RUN) python -m evals.gate_proof --claim 1

        gate-proof:
        \t$(RUN) python -m evals.gate_proof
        """)
    }
    assert parsed["claim-1"] == (
        "$(RUN) python -m evals.guardrail",
        "$(RUN) python -m evals.gate_proof --claim 1",
    )
    assert parsed["gate-proof"] == ("$(RUN) python -m evals.gate_proof",)


def test_a_variable_assignment_is_not_a_target() -> None:
    """`PYTHON_DIRS := src tests` and `UV ?= uv` both contain a colon."""
    assert [t.name for t in _makefile("PYTHON_DIRS := src tests\nUV ?= uv\n")] == []


def test_naming_the_module_without_a_claim_is_not_executing() -> None:
    """The distinction the whole split rests on. `engine.run` requires a claim."""
    ledger_target, executor = _makefile("""\
        gate-proof:
        \t$(RUN) python -m evals.gate_proof

        claim-4:
        \t$(RUN) python -m evals.gate_proof --claim 4
        """)
    assert ledger_target.executes == frozenset()
    assert executor.executes == frozenset({4})


# ---------------------------------------------------------------- every check, broken


def test_an_orphaned_mutation_is_caught() -> None:
    targets = _makefile("claim-1:\n\t$(RUN) python -m evals.gate_proof --claim 1\n")
    check = ledger.check_every_mutation_is_owned_once([_mutation(claim=9)], targets)
    assert not check.passed
    assert "no Makefile target" in check.counterexamples[0]


def test_a_mutation_two_targets_both_run_is_caught() -> None:
    """The thirteen minutes. Regression against the arrangement quietly coming back."""
    targets = _makefile("""\
        claim-1:
        \t$(RUN) python -m evals.gate_proof --claim 1

        gate-proof:
        \t$(RUN) python -m evals.gate_proof --claim 1
        """)
    check = ledger.check_every_mutation_is_owned_once([_mutation()], targets)
    assert not check.passed
    assert "run by claim-1, gate-proof" in check.counterexamples[0]


def test_a_claim_target_with_nothing_planted_against_it_is_caught() -> None:
    targets = _makefile("""\
        claim-1:
        \t$(RUN) python -m evals.gate_proof --claim 1

        claim-2:
        \t$(RUN) python -m evals.uplift
        """)
    check = ledger.check_every_claim_target_owns_a_gate([_mutation(claim=1)], targets)
    assert not check.passed
    assert "claim-2" in check.counterexamples[0]


def test_a_ledger_that_executes_is_caught() -> None:
    targets = _makefile("gate-proof:\n\t$(RUN) python -m evals.gate_proof --claim 1\n")
    assert not ledger.check_the_ledger_executes_nothing(targets).passed


def test_two_mutations_sharing_an_id_are_caught() -> None:
    check = ledger.check_mutation_ids_are_unique([_mutation(), _mutation()])
    assert not check.passed


def test_a_mutation_in_the_wrong_directory_is_caught() -> None:
    check = ledger.check_mutation_lives_under_the_claim_it_declares(
        [_mutation(claim=1, directory="claim-2")]
    )
    assert not check.passed


@pytest.mark.parametrize(
    ("anchor", "why"),
    [
        ("this text is nowhere in money.py at all\n", "no longer occurs"),
        ("\n", "occurs many times"),
    ],
)
def test_an_anchor_that_no_longer_lands_exactly_once_is_caught(anchor: str, why: str) -> None:
    check = ledger.check_every_anchor_is_aimed_at_one_place([_mutation(anchor=anchor)])
    assert not check.passed, why


def test_a_mutation_naming_a_file_that_does_not_exist_is_caught() -> None:
    check = ledger.check_every_anchor_is_aimed_at_one_place([_mutation(file="src/holdout/gone.py")])
    assert not check.passed
    assert "does not exist" in check.counterexamples[0]


# ----------------------------------------------------------------- the real arrangement


def test_the_repository_s_own_arrangement_audits_clean() -> None:
    report = ledger.audit()
    assert report.passed, [c.id for c in report.checks if not c.passed]


def test_every_committed_mutation_is_owned_by_its_own_claim_target() -> None:
    """Stated as its own test because it is the sentence the split exists to make true."""
    all_targets = ledger.targets()
    for mutation in ledger.load_mutations():
        assert ledger.owners_of(mutation, all_targets) == (f"claim-{mutation.claim}",)
