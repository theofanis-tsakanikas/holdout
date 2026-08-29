"""The measuring instrument, measured — claim 3's half.

Claim 3's eval is evidence, and evidence held to a lower standard than the code it judges
stops being evidence. These tests are about the eval itself.

`CLAUDE.md`'s rule, in its own words:

> **A guard tested by its author is tested in the shape the guard already handles.**

The shape claim 3's guard already handles is *repetition*: `draw` reads no clock, no
environment and no random source, so calling it twice agrees with itself and would agree just
as loudly on a lottery that ignored the committed seed. So the first test below is the one
`evals/guardrail/` needed for its rounding, moved one claim along — **the second
implementation must not reach the first one's hash** — and the last two pin figures the eval
publishes, including the one that is not flattering.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import MappingProxyType

import pytest
from evals.assignment import build, checks, reference
from evals.assignment.blake2b import blake2b

from holdout.contracts.loader import load
from holdout.core.experiment import Arm, ReadoutError, SealedAssignment, sealed
from holdout.core.experiment import contamination as contamination_module
from holdout.core.experiment.assignment import digest_for

PACKAGE = Path(checks.__file__).parent

#: Modules under `evals/assignment/` that may reach a hash the core also uses, each with the
#: reason. An **exclusion list, not an inclusion list** — every other module in the package is
#: found by a glob rather than named here, so a module added later is scanned without anybody
#: having to remember. That inversion is the lesson `evals/guardrail/`'s version of this rule
#: was rewritten to carry: a guard that has to be remembered when a file is added is a guard
#: that will not be.
MAY_REACH_THE_CORE_S_HASH = {
    #: `A10` compares the eval's own BLAKE2b against `hashlib` on purpose — that is the check,
    #: not a leak — and the forger in `A7` recomputes the committed digest the way the system
    #: would, because that is what a careful forger does. Neither is a second opinion about
    #: where an arm belongs: `A1` and `A2` compare against `reference.py` alone.
    "checks.py",
}

#: What a module in this package may not reach: the standard library's BLAKE2b, and every
#: name in the core that computes a digest, a key or a rank. `reference.py` and `blake2b.py`
#: exist precisely so that the second opinion shares none of them.
FORBIDDEN_IMPORTS = frozenset({"hashlib", "holdout.core.hashing"})
THE_CORE_S_HASHING = frozenset(
    {"canonical_bytes", "key_for", "rank_of", "digest_for", "covariate_digest"}
)


def _reaches_the_core_s_hash(source: Path) -> list[str]:
    tree = ast.parse(source.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in FORBIDDEN_IMPORTS:
                    found.append(f"{source.name}:{node.lineno} imports {alias.name}")
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module in FORBIDDEN_IMPORTS:
                found.append(f"{source.name}:{node.lineno} imports from {module}")
            if module.startswith("holdout."):
                for alias in node.names:
                    if alias.name in THE_CORE_S_HASHING:
                        found.append(f"{source.name}:{node.lineno} imports {alias.name}")
    return found


def test_the_second_implementation_never_reaches_the_hash_it_is_a_second_opinion_about() -> None:
    """The defect `evals/guardrail/rounding.py` was written to close, one claim along.

    There the eval's own floor ended in `Money.as_lower_bound` — the core's own rounding
    primitive — under a docstring claiming independence. Here the equivalent would be
    `reference.py` calling `hashlib.blake2b`, or importing `digest_for`: the two would then
    agree on a wrong digest and `A2` would report 100% while saying nothing.
    """
    offences: list[str] = []
    for source in sorted(PACKAGE.glob("*.py")):
        if source.name in MAY_REACH_THE_CORE_S_HASH:
            continue
        offences.extend(_reaches_the_core_s_hash(source))
    assert not offences, "\n".join(offences)


def test_the_independent_lottery_can_actually_disagree() -> None:
    """A check that cannot fail is one somebody will later mistake for a check that passed.

    `A1` compares 4,129 units and reports 100%. This is what makes that number mean
    something: change one character of the committed seed and the second implementation
    disagrees with the recorded arms, on the same strata, in the same call.
    """
    strata = (("ST0001", "ST0002", "ST0003"), ("ST0004", "ST0005", "ST0006"))
    ours = reference.lottery(strata, seed="holdout-committed", draw_index=0)
    theirs = reference.lottery(strata, seed="holdout-committee", draw_index=0)
    assert ours != theirs
    assert reference.lottery(strata, seed="holdout-committed", draw_index=1) != ours


def test_the_second_implementation_is_not_the_first_one_in_disguise() -> None:
    """RFC 7693 Appendix A, asserted in the suite as well as published by the eval.

    The vector is quoted from the instrument rather than from this repository, and it is the
    only expected answer in claim 3's eval that was chosen by somebody who has never seen it.
    """
    assert blake2b(b"abc").hex() == checks.RFC_7693_ABC


# ------------------------------------------------------------------------------ the figures


@pytest.fixture(scope="module")
def one_seal() -> tuple[build.Drawn, SealedAssignment]:
    contracts = load()
    configuration = next(
        c
        for c in build.configurations(contracts)
        if c.at_the_contract_share and c.scale_name == "scenario"
    )
    drawn = build.run_the_lottery(configuration)
    assert drawn.seal is not None
    return drawn, drawn.seal


def test_a_coordinated_deletion_is_invisible_to_the_contamination_check(
    one_seal: tuple[build.Drawn, SealedAssignment],
) -> None:
    """The finding claim 3's eval produced, pinned so that fixing it is a restatement.

    `contamination.check` derives the roster it walks **from the arms it is checking**, so a
    control store deleted from the assignment table with the digest recomputed to match leaves
    nothing for it to compare against. It reports the assignment intact. The eval publishes
    this as `48/72 = 66.67%`, and `evals/assignment/README.md` and `docs/DECISIONS.md` both
    say so; a change that closes the gap makes this test red, which is doctrine rule 4 working
    rather than a test in the way.
    """
    item, seal = one_seal
    victim = seal.control[0]
    without = MappingProxyType({u: a for u, a in seal.arms.items() if u != victim})
    with checks._rewritten(
        seal,
        _arms=without,
        _digest=digest_for(
            experiment_id=seal.experiment_id,
            seed=seal.seed,
            form_digest=seal.form_digest,
            strata=seal.strata,
            arms=without,
        ),
    ):
        found = contamination_module.check(
            seal,
            delivered=dict.fromkeys(seal.roster, build.CONTROL_POLICY),
            treatment_policy=build.TREATMENT_POLICY,
            control_policy=build.CONTROL_POLICY,
            form_digest=item.configuration.form_digest,
        )
        assert found.redraw_matches
        assert sealed(seal)
    assert sealed(seal), "the seal did not survive being attacked and restored"


def test_what_refuses_that_erasure_is_the_readout_one_function_later(
    one_seal: tuple[build.Drawn, SealedAssignment],
) -> None:
    """The other half of the same finding, driven rather than named.

    An erased store still reports an outcome, and `close` refuses outcomes from units it never
    assigned. That is what stops the erasure, and it is one function past the check whose
    docstring points at this route.
    """
    item, seal = one_seal
    contracts = load()
    victim = seal.control[0]
    without = MappingProxyType({u: a for u, a in seal.arms.items() if u != victim})
    with (
        checks._rewritten(
            seal,
            _arms=without,
            _digest=digest_for(
                experiment_id=seal.experiment_id,
                seed=seal.seed,
                form_digest=seal.form_digest,
                strata=seal.strata,
                arms=without,
            ),
        ),
        pytest.raises(ReadoutError, match="never assigned"),
    ):
        checks._close(item, seal, contracts)
    assert sealed(seal)


def test_the_contract_s_own_holdout_share_never_reaches_no_admissible_assignment() -> None:
    """Why the grid sweeps the share at all, asserted rather than left in a paragraph.

    At 20% a control arm always leaves five units to a stratum, so `strata_of` never returns
    `None` on any roster this corpus produces. The refusal it feeds is live code that the
    contract's own share cannot drive, which is exactly the coverage hole rule 4 of
    `evals/README.md` exists to refuse.
    """
    contracts = load()
    configurations = build.configurations(contracts)
    at_the_contract_share = [c for c in configurations if c.at_the_contract_share]
    swept = [c for c in configurations if not c.at_the_contract_share]
    assert at_the_contract_share and swept

    refused_at_the_contract_share = [
        c for c in at_the_contract_share if build.run_the_lottery(c).refused
    ]
    refused_when_swept = [c for c in swept if build.run_the_lottery(c).refused]
    assert not refused_at_the_contract_share
    assert refused_when_swept, (
        "the swept shares no longer reach a roster no stratification can hold both arms of, "
        "so NO_ADMISSIBLE_ASSIGNMENT is a branch nothing in this eval drives"
    )


def test_every_stratum_gives_up_exactly_one_control(
    one_seal: tuple[build.Drawn, SealedAssignment],
) -> None:
    """The property the whole construction rests on, over a roster nobody here chose."""
    _, seal = one_seal
    for stratum in seal.strata:
        controls = [u for u in stratum if seal.arms[u] is Arm.CONTROL]
        assert len(controls) == 1, f"{stratum} gave up {len(controls)} controls"
    assert len(seal.control) == len(seal.strata)
