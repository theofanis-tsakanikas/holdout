"""The seal: what it guarantees, and — at the bottom of this file — what it does not.

`CLAUDE.md` puts the injected truth in *"a sealed file the harness opens **only after** the
readout has been written."* Two of the three things that sentence needs are structural and are
asserted here. The third is a discipline, and it is asserted here too, as a limit rather than
as a guarantee, in the same way `tests/core/test_certificate_forgery.py` asserts the
certificate's.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from corpus.world import events, prepare
from corpus.world.generate import StoreExposure
from corpus.world.seal import (
    SEAL_FILENAME,
    SealError,
    WorldTruth,
    header,
    open_after_readout,
    openings,
    verify,
)

SEED = "seal"


@pytest.fixture
def sealed(tmp_path: Path) -> Path:
    run = prepare("W3", seed=SEED, scale="smoke")
    for _ in events(run, seal_into=tmp_path):
        pass
    return tmp_path / SEAL_FILENAME


@pytest.fixture
def readout(tmp_path: Path) -> Path:
    path = tmp_path / "readout.json"
    path.write_text(json.dumps({"uplift_cents": 1234, "ci": [900, 1500]}), encoding="utf-8")
    return path


def test_running_a_world_without_a_seal_directory_writes_no_seal(tmp_path: Path) -> None:
    run = prepare("W6", seed=SEED, scale="smoke")
    for _ in events(run):
        pass
    assert not (tmp_path / SEAL_FILENAME).exists()


def test_the_stream_never_yields_the_truth(tmp_path: Path) -> None:
    """The one part of the seal that is a guarantee rather than a discipline.

    A harness cannot condition on a number it was never handed. `generate` yields exposure
    records among its events and `events` filters them out — so this asserts the filter, on
    the world where the exposure record is most tempting to look at.
    """
    run = prepare("W3", seed=SEED, scale="smoke")
    withheld = {StoreExposure.__name__, WorldTruth.__name__}
    for event in events(run, seal_into=tmp_path):
        # By name rather than by `isinstance`, because the declared return type already
        # excludes both and a type checker would fold the assertion away as unreachable —
        # leaving a test that reads as a guarantee and executes as nothing.
        assert type(event).__name__ not in withheld


def test_nothing_a_caller_holds_carries_the_truth() -> None:
    """Asserted over the whole public surface rather than over the fields somebody remembered.

    A `Run` is handed to every consumer. If it grew an attribute holding the injection, the
    seal would still be written, still be shut, and still be pointless.
    """
    run = prepare("W3", seed=SEED, scale="smoke")
    for name in dir(run):
        if name.startswith("_"):
            continue
        assert not isinstance(getattr(run, name), WorldTruth)
    assert not any(
        word in name for name in dir(run) for word in ("truth", "effect", "exposure", "injection")
    )


def test_the_seal_opens_against_a_readout_and_records_the_opening(
    sealed: Path, readout: Path
) -> None:
    assert openings(sealed) == []
    truth = open_after_readout(sealed, readout)
    assert truth.world == "W3"
    assert truth.injection["ack_failure_pct_treated"] == 30
    assert truth.exposure_by_store

    ledger = openings(sealed)
    assert len(ledger) == 1
    assert ledger[0]["readout"] == readout.name
    assert (
        ledger[0]["readout_sha256"]
        == __import__("hashlib").sha256(readout.read_bytes()).hexdigest()
    )


def test_the_seal_refuses_to_open_before_the_readout_exists(sealed: Path, tmp_path: Path) -> None:
    """The ordering guarantee, and the whole reason the argument is a path and not a flag."""
    with pytest.raises(SealError, match="does not exist"):
        open_after_readout(sealed, tmp_path / "not-written-yet.json")
    assert openings(sealed) == []


def test_a_second_opening_is_recorded_beside_the_first(sealed: Path, readout: Path) -> None:
    """Append-only. An eval asserts *exactly one* opening; overwriting would hide the second."""
    open_after_readout(sealed, readout)
    other = readout.parent / "readout-2.json"
    other.write_text('{"uplift_cents": 9999}', encoding="utf-8")
    open_after_readout(sealed, other)
    ledger = openings(sealed)
    assert [entry["readout"] for entry in ledger] == [readout.name, other.name]


def test_the_truth_is_not_lying_in_the_file_in_plain_sight(sealed: Path, readout: Path) -> None:
    """Nothing in the sealed bytes can be found by looking for it.

    The strings searched for are taken **from the truth itself** after it is opened, not from
    a list somebody wrote while thinking about what to hide. A hand-written list would test
    the author's imagination; this tests the file.
    """
    raw = sealed.read_text(encoding="utf-8")
    truth = open_after_readout(sealed, readout)
    for phrase in (
        truth.injection["violates"],
        truth.injection["correct_behaviour"],
        truth.treatment_policy["policy_id"],
        str(truth.totals["acks_failed"]),
        truth.exposure_by_store[0]["store_id"],
    ):
        assert phrase not in raw, phrase


def test_a_seal_written_over_a_window_says_it_is_a_window(tmp_path: Path, readout: Path) -> None:
    """A window's truth is not the world's truth.

    `--only-stores` is a legitimate way to look at a scenario-scale world without materialising
    it, and a seal written beside one covers those stores alone. An exposure rate over three
    stores carrying the whole world's name is exactly the kind of number this repository refuses
    to let anyone quote, so the seal records the restriction it was written under.
    """
    directory = tmp_path / "window"
    run = prepare("W3", seed=SEED, scale="smoke")
    wanted = [run.chain.stores[1].store_id, run.chain.stores[4].store_id]
    for _ in events(run, seal_into=directory, only_stores=wanted):
        pass

    truth = open_after_readout(directory / SEAL_FILENAME, readout)
    assert truth.restricted_to_stores == wanted
    assert truth.totals["stores"] == len(wanted)
    assert [record["store_id"] for record in truth.exposure_by_store] == wanted


def test_a_seal_over_the_whole_world_says_so(sealed: Path, readout: Path) -> None:
    truth = open_after_readout(sealed, readout)
    assert truth.restricted_to_stores is None
    assert truth.totals["stores"] == prepare("W3", seed=SEED, scale="smoke").scale.stores


def test_the_header_says_which_seal_this_is_and_nothing_more(sealed: Path) -> None:
    """Listing a directory must not reveal the shape of the assignment."""
    keys = set(header(sealed))
    assert keys == {"world", "seed", "scale", "sealed_at", "openings"}
    assert header(sealed)["world"] == "W3"


def test_an_edited_seal_does_not_match_its_own_commitment(sealed: Path, readout: Path) -> None:
    document = json.loads(sealed.read_text(encoding="utf-8"))
    document["payload"] = document["payload"][:-8] + "AAAAAAAA"
    sealed.write_text(json.dumps(document, indent=2), encoding="utf-8")
    assert not verify(sealed)
    with pytest.raises(SealError, match="has been edited"):
        open_after_readout(sealed, readout)


def test_a_file_that_is_not_a_seal_is_refused(tmp_path: Path) -> None:
    junk = tmp_path / "junk.json"
    junk.write_text("{}", encoding="utf-8")
    with pytest.raises(SealError, match="not a"):
        header(junk)
    with pytest.raises(SealError, match="cannot be read as a seal"):
        header(tmp_path / "absent.json")


def test_the_same_world_seals_byte_for_byte_the_same_truth(tmp_path: Path) -> None:
    """Except for the timestamp, which is when it was sealed and not what was sealed.

    A random nonce would make the seal the one part of a reproducible corpus that could not be
    reproduced, and "re-run it yourself" is the whole of how anybody checks this project.
    """
    payloads = []
    for index in (1, 2):
        directory = tmp_path / str(index)
        run = prepare("W4", seed=SEED, scale="smoke")
        for _ in events(run, seal_into=directory):
            pass
        payloads.append(json.loads((directory / SEAL_FILENAME).read_text(encoding="utf-8")))
    assert payloads[0]["payload"] == payloads[1]["payload"]
    assert payloads[0]["commitment_sha256"] == payloads[1]["commitment_sha256"]


def test_the_seal_holds_behaviour_and_not_a_number_about_money(sealed: Path, readout: Path) -> None:
    """`CLAUDE.md`: the generator *"injects a known effect on behaviour, not on the metric."*

    So there is no field in here that could be read as the answer, and the field where a
    reader would look for one contains the reason there isn't one instead.
    """
    truth = open_after_readout(sealed, readout)
    assert "must be computed" in truth.effect_on_the_metric
    for name in ("uplift", "margin", "effect_size", "true_effect"):
        assert not any(name in field for field in truth.injection)
        assert not any(name in field for field in truth.totals)


def test_the_limit_is_asserted_rather_than_described(sealed: Path) -> None:
    """A coordinated rewrite is not caught, and this is the test that says so out loud.

    Decode the payload, change it, re-seal it with a fresh commitment and an empty ledger, and
    every check in this file passes. The seal makes the *mistake* impossible — the truth is
    never in the harness's hands by accident — and leaves the *forgery* visible only to
    someone who compares the seal against a re-run of the world.

    Stating it here is the point. `PLAN.md` records the same limit for the certificate type,
    in the same words, for the same reason: a limit written in a docstring is prose, and a
    limit written as a passing test is a fact about the code.
    """
    import base64
    import hashlib

    from corpus.world.seal import _obscure

    document = json.loads(sealed.read_text(encoding="utf-8"))
    nonce = base64.b64decode(document["nonce"])
    plaintext = _obscure(base64.b64decode(document["payload"]), nonce)
    forged = json.loads(plaintext)
    forged["injection"]["ack_failure_pct_treated"] = 0
    body = json.dumps(forged, sort_keys=True, indent=None).encode("utf-8")
    document["payload"] = base64.b64encode(_obscure(body, nonce)).decode("ascii")
    document["commitment_sha256"] = hashlib.sha256(body).hexdigest()
    sealed.write_text(json.dumps(document, indent=2), encoding="utf-8")

    assert verify(sealed), "the forgery was caught, and this repository's prose says it is not"
