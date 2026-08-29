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
import tempfile
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

#: What a module in this package may reach of the hashes the core also uses — **per name, not
#: per file.** A blanket exemption for `checks.py` was the first shape of this rule, and it
#: repeated the mistake `evals/guardrail/`'s version was rewritten to remove: *a rule scoped to
#: the file the legitimate use happens to live in would pass on the tree that had the bug*, and
#: `checks.py` is exactly where a reach from `A1` or `A2` would go. So each file names the
#: individual reaches it is allowed and nothing else.
#:
#: An **exclusion map, not an inclusion list** — every module in the package is found by a glob
#: and scanned; a file absent from this map is allowed nothing. That inversion is the other
#: lesson from claim 1: a guard that has to be remembered when a file is added is a guard that
#: will not be.
MAY_REACH = {
    #: `A10` compares the eval's own BLAKE2b against `hashlib` on purpose — that *is* the
    #: check — and the forger in `A7`, `A8` and `A9` recomputes the committed digest the way
    #: the system would, because that is what a careful forger does. Neither is a second
    #: opinion about where an arm belongs: `A1` and `A2` compare against `reference` alone,
    #: and the names below are the only two this file may reach.
    "checks.py": frozenset({"hashlib", "digest_for"}),
}

#: What no module in this package may reach unless `MAY_REACH` names it: the standard library's
#: BLAKE2b, and every name in the core that computes a digest, a key or a rank. `reference.py`
#: and `blake2b.py` exist precisely so that the second opinion shares none of them.
FORBIDDEN_MODULES = frozenset({"hashlib", "holdout.core.hashing"})
FORBIDDEN_NAMES = frozenset(
    {"canonical_bytes", "key_for", "rank_of", "digest_for", "covariate_digest", "digest"}
)

#: The subset of the above that is unambiguous **as an attribute**. `digest` and
#: `covariate_digest` are not in it and cannot be: `SealedAssignment.digest` and
#: `.covariate_digest` are fields a check legitimately reads, `reference.digest` is the eval's
#: own second implementation, and `hashlib`'s digest object has a `.digest()` too. A guard that
#: went red on all of those would be a guard somebody turns off. What keeps
#: `from holdout.core import hashing` then `hashing.digest(...)` caught is the alias rule
#: below, which fires on the import rather than on the call.
FORBIDDEN_ATTRIBUTES = frozenset({"canonical_bytes", "key_for", "rank_of", "digest_for"})

#: Modules whose *name* alone is a reach, when imported as an attribute source —
#: `from holdout.core import hashing` followed by `hashing.digest(...)` never mentions
#: `holdout.core.hashing` and never imports `digest`. It is the spelling that matches the file
#: tree, which is the spelling `CLAUDE.md` records the corpus barrier missing.
FORBIDDEN_MODULE_ALIASES = frozenset({"hashing", "assignment"})


def _reaches_the_core_s_hash(source: Path) -> list[str]:
    """Every reach in one module: imports, aliased module imports, and attribute access.

    The attribute scan is the half the first version of this rule did not have, and it is the
    half `evals/guardrail/`'s equivalent does. Without it `from holdout.core import hashing`
    then `hashing.digest(...)`, and `from holdout.core.experiment import assignment as a` then
    `a.digest_for(...)`, both pass — the two most natural spellings of the thing forbidden.
    """
    allowed = MAY_REACH.get(source.name, frozenset())
    found: list[str] = []

    def offend(line: int, what: str, reach: str) -> None:
        if reach not in allowed:
            found.append(f"{source.name}:{line} {what}")

    tree = ast.parse(source.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in FORBIDDEN_MODULES:
                    offend(node.lineno, f"imports {alias.name}", alias.name)
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module in FORBIDDEN_MODULES:
                offend(node.lineno, f"imports from {module}", module)
            if module.startswith("holdout"):
                for alias in node.names:
                    if alias.name in FORBIDDEN_NAMES:
                        offend(node.lineno, f"imports {alias.name} from {module}", alias.name)
                    elif alias.name in FORBIDDEN_MODULE_ALIASES:
                        offend(
                            node.lineno,
                            f"imports the module {alias.name} from {module}, which puts its "
                            "hashing one attribute away",
                            alias.name,
                        )
        if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_ATTRIBUTES:
            offend(node.lineno, f"reaches {ast.unparse(node)}", node.attr)
    return found


def test_the_second_implementation_never_reaches_the_hash_it_is_a_second_opinion_about() -> None:
    """The defect `evals/guardrail/rounding.py` was written to close, one claim along.

    There the eval's own floor ended in `Money.as_lower_bound` — the core's own rounding
    primitive — under a docstring claiming independence. Here the equivalent would be
    `reference.py` calling `hashlib.blake2b`, or importing `digest_for`: the two would then
    agree on a wrong digest and `A2` would report 100% while saying nothing.

    **What this does not cover**, because a static scan cannot and the alternative would be a
    sentence pretending otherwise: a reach assembled at run time (`getattr(module, name)`, an
    `importlib` call, a name rebound through a dict); a reach through a *third* module that is
    itself allowed nothing today but could be added; and any equivalence that is not a shared
    call at all — `reference.py` re-deriving the same wrong constant as the core would pass
    this and every other check here. What answers the last one is `A10`, which pins the eval's
    hash to a vector published by somebody who has never seen this repository.
    """
    offences: list[str] = []
    for source in sorted(PACKAGE.glob("*.py")):
        offences.extend(_reaches_the_core_s_hash(source))
    assert not offences, "\n".join(offences)


def test_the_exemption_map_names_only_files_that_exist() -> None:
    """A rule may not carry an exemption for a module nobody has.

    Claim 1's version of this test is `test_every_module_that_may_round_with_the_core_still
    _exists`, and the reason is the same: an exemption outliving its file is a hole with a
    name, waiting for somebody to create that file again for an unrelated reason.
    """
    missing = sorted(name for name in MAY_REACH if not (PACKAGE / name).exists())
    assert not missing, f"{missing} is exempted and does not exist"


def test_the_guard_catches_the_two_spellings_that_match_the_file_tree() -> None:
    """The guard, shown to bite, on cases its author did not invent.

    Both come from oversight level 2 reading this branch in fresh context: they are the
    spellings the first version of the rule missed, and they are the ones somebody reaching
    for the core's hash would actually write, because they are what the file tree looks like.
    `CLAUDE.md` records the identical miss in the corpus barrier — `import src.holdout`, the
    spelling that matches the tree — so this is that defect's second appearance and the first
    time it is planted rather than found.
    """
    planted = {
        "from holdout.core import hashing": "from holdout.core import hashing\nx = hashing.digest([])\n",
        "assignment as a": (
            "from holdout.core.experiment import assignment as a\ny = a.digest_for()\n"
        ),
        "import hashlib": "import hashlib\n",
        "from hashlib import blake2b": "from hashlib import blake2b\n",
        "from holdout.core.hashing import digest": "from holdout.core.hashing import digest\n",
        "attribute reach": "import m\nz = m.canonical_bytes([])\n",
        "aliased attribute reach": (
            "from holdout.core.experiment import assignment\nw = assignment.rank_of('a', b'')\n"
        ),
    }
    tmp = Path(tempfile.mkdtemp()) / "planted.py"
    for label, source in planted.items():
        tmp.write_text(source, encoding="utf-8")
        assert _reaches_the_core_s_hash(tmp), f"the guard did not catch: {label}"


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


def test_a_coordinated_deletion_is_caught_by_the_committed_strata(
    one_seal: tuple[build.Drawn, SealedAssignment],
) -> None:
    """The finding claim 3's eval produced, and the line that closed it — both pinned.

    **This test used to assert the opposite, and the name it had was
    `test_a_coordinated_deletion_is_invisible_to_the_contamination_check`.** That was true
    when it was written: `contamination.check` walked `seal.roster`, which
    `SealedAssignment` derives as `tuple(sorted(self.arms))`, so a control store deleted from
    the assignment table with the digest recomputed to match left the check nothing to
    compare against — it reported the assignment intact and `sealed()` agreed. The eval
    measured it at 24 of 72 erasure routes and published `48/72 = 66.67%`.

    Oversight level 2 read the deferral that carried it and found the deferral wrong rather
    than the measurement: `check` already computes `redraw(seal)`, whose key set is the
    roster the lottery was drawn over — from the **strata**, which are committed and digested
    as their own section — and then discarded it one line later. The prior wording stays in
    `docs/DECISIONS.md` per doctrine rule 4, and this test now asserts the closure.

    The strata are a *sound* witness and not merely an available one, which the second half
    below is what shows: a forger who deletes the unit from the strata as well changes which
    unit holds the smallest rank in that stratum, so `reassigned` fires instead.
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
        # Everything the forgery was designed to satisfy still holds — and it is refused anyway.
        assert sealed(seal)
        assert found.digest_matches
        assert found.redraw_matches
        assert found.dropped == (victim,)
        assert not found.is_clean
    assert sealed(seal), "the seal did not survive being attacked and restored"


def test_deleting_the_unit_from_the_strata_as_well_is_caught_by_the_redraw(
    one_seal: tuple[build.Drawn, SealedAssignment],
) -> None:
    """The obvious counter-move, and why the strata are a sound witness rather than a handy one.

    The case is not one this test's author invented: it is the move oversight level 2 made
    when checking whether the closure above could be walked around, and it is the move an
    attacker who has read `contamination.py` would make next.
    """
    item, seal = one_seal
    victim = seal.control[0]
    without = MappingProxyType({u: a for u, a in seal.arms.items() if u != victim})
    strata = tuple(tuple(u for u in stratum if u != victim) for stratum in seal.strata)
    with checks._rewritten(
        seal,
        _arms=without,
        _strata=strata,
        _digest=digest_for(
            experiment_id=seal.experiment_id,
            seed=seal.seed,
            form_digest=seal.form_digest,
            strata=strata,
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
        assert found.dropped == (), "the strata no longer name the erased store"
        assert not found.redraw_matches, (
            "removing a stratum's control changes which unit holds the smallest rank in it, "
            "so the redraw disagrees with the arms even though both were rewritten together"
        )
        assert not found.is_clean
    assert sealed(seal)


def test_the_readout_still_refuses_the_erasure_one_function_later(
    one_seal: tuple[build.Drawn, SealedAssignment],
) -> None:
    """Defence in depth, kept because it is what held the door while the check could not see.

    An erased store still reports an outcome, and `close` refuses outcomes from units it never
    assigned. That is a *second* refusal now rather than the only one, and `A8` asserts both
    layers for exactly that reason: the contamination check catching it is what should hold,
    and this is what held it before anything did.
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
