"""The acceptance's own two halves: it reads the vocabulary, and it asks for what it was told to.

**`ops/run_assertions.py` is what closes phase 3**, and until 2026-09-10 no part of it had ever
executed against a row — `gold.readout` was written by nothing, which this register holds as its
own finding. The first run that produced a readout failed it three times, and two of the three
were the assertion rather than the estate:

    FAIL  no experiment produced a number ...
    FAIL  fresh-ladder refused with `UNDERPOWERED_FOR_CAPACITY`, which is not in the closed
          vocabulary. Adding a code is a code change with a test.
    FAIL  fresh-ladder-peeking refused with `STOPPING_RULE_PERMITS_PEEKING`, which is not in
          the closed vocabulary.

Both codes are in `contracts/vocabularies/reason_codes.yaml`, declared four lines apart.

## The vocabulary was read as if it were a list of strings

    codes.update(str(c) for c in section)

Each section is a list of **entries**, and `str()` over a dictionary yields the whole mapping as
text. So the set held twenty-odd stringified dictionaries and no code at all — **every** refusal
would have been reported as undeclared. The check that reads a contract to close a vocabulary had
itself never been read.

## And the flags named halves that fired regardless

`main` parsed `--require-number` and `--require-refusal` and used them only to decide whether to
call `check_experiments`; inside it, a readout with no number failed whatever had been asked for.
`run.yml` passes `--require-refusal` alone, for the reason `PLAN.md` records: this corpus cannot
power the declared experiment, and requiring a number would mean choosing an MDE that makes the
refusal go away.

## What this does not check

- **It does not check the codes are the right ones.** That is the contract's business and
  `tests/contracts/` holds it; what is here is that the reader can see them at all.
"""

from __future__ import annotations

import pytest

from ops import run_assertions

#: Two codes from two different moments, so a reader that finds only one section still fails.
DECLARED = ("COST_STALE", "UNDERPOWERED_FOR_CAPACITY", "STOPPING_RULE_PERMITS_PEEKING")


def test_the_vocabulary_is_read_as_codes() -> None:
    codes = run_assertions._declared_reason_codes()
    assert codes, "the reader returned nothing, which calls every refusal undeclared"
    for code in DECLARED:
        assert code in codes, (
            f"`{code}` is declared in contracts/vocabularies/reason_codes.yaml and the reader "
            f"did not find it. What it found instead: {sorted(codes)[:3]}\n\n"
            "A section is a list of entries and each entry names its code in a `code` key; "
            "`str()` over those entries yields whole dictionaries, which is what the first "
            "version collected."
        )
    assert not any(character in code for code in codes for character in "{}:'"), (
        "a code carries dictionary punctuation, so entries are being stringified rather than "
        "read — the defect this gate exists for, in the shape it originally had."
    )


@pytest.mark.parametrize(
    ("require_number", "require_refusal", "rows", "expected"),
    [
        # A readout of two refusals — what this estate actually produces — passes when the
        # refusal is what was asked for, and fails when a number was.
        (False, True, [("a", None, "COST_STALE"), ("b", None, "COST_STALE")], 0),
        (True, True, [("a", None, "COST_STALE"), ("b", None, "COST_STALE")], 1),
        # And the other way: a readout with no refusal fails only when one was required.
        (True, False, [("a", 1.0, None)], 0),
        (True, True, [("a", 1.0, None)], 1),
    ],
    ids=["refusals asked for", "number asked for", "numbers only", "refusal missing"],
)
def test_each_half_is_asked_for_rather_than_assumed(
    monkeypatch: pytest.MonkeyPatch,
    require_number: bool,
    require_refusal: bool,
    rows: list[tuple[str, float | None, str | None]],
    expected: int,
) -> None:
    monkeypatch.setattr(run_assertions, "_sql", lambda *_a, **_k: rows)
    failed = run_assertions.check_experiments(
        "holdout",
        "warehouse",
        require_number=require_number,
        require_refusal=require_refusal,
    )
    assert failed == expected, (
        f"with require_number={require_number} and require_refusal={require_refusal} over "
        f"{rows}, the check returned {failed} and should have returned {expected}. A flag that "
        "names a half and does not gate it is a flag that reads as a choice and is not one."
    )
