"""A recording is every question, the agent that answered, and a digest over the lot.

`record.record` is what claim 6 will grade, so what this suite fixes is the three properties
that make a recording honest rather than a fixture: nothing filtered, the agent fingerprinted,
the directory digested. A scripted model stands in for the network.

## What this asserts

- Every question produces one numbered file, in order; the manifest's counts match the files.
- The manifest carries the model id, the contract version and both fingerprints, and the
  fingerprints are the ones the tree computes now.
- Editing any outcome file moves the digest; the manifest's digest is the directory's.
- A proposal round-trips with the MDE as a string, never a float.
- Recording into a directory that exists is refused: a recording is made once.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from holdout.agent import record as recording
from holdout.agent import registry as reg
from holdout.agent.propose import prompt_fingerprint
from holdout.contracts.loader import load
from tests.agent.fakes import GOOD_DELIVERY, Echo, Scripted, calls, text

CONTRACTS = load()
CONTEXT = {"metrics": "m", "roster": "r"}


def _recording(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    scripted = Scripted(
        [
            calls(("propose_design", GOOD_DELIVERY)),
            text("no thank you"),
            calls(("propose_design", dict(GOOD_DELIVERY, mde={"kind": "absolute", "value": 0}))),
        ]
    )
    monkeypatch.setattr(
        recording,
        "from_contracts",
        lambda _contracts: (scripted, recording.Ceilings(1000, 60, 6)),
    )
    out = tmp_path / "rec"
    recording.record(
        ["a", "b", "c"], context=CONTEXT, contracts=CONTRACTS, executor=Echo(), out=out
    )
    return out


def test_every_question_lands_and_the_manifest_counts_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = _recording(tmp_path, monkeypatch)
    files = sorted(p.name for p in out.glob("[0-9]*.json"))
    assert files == ["000.json", "001.json", "002.json"]
    manifest = json.loads((out / recording.MANIFEST).read_text(encoding="utf-8"))
    assert (manifest["questions"], manifest["proposals"], manifest["failed"]) == (3, 1, 2)
    outcomes = [json.loads((out / f).read_text(encoding="utf-8")) for f in files]
    assert [o["question"] for o in outcomes] == ["a", "b", "c"], "order is the order asked"
    assert [o["failed"] for o in outcomes] == [None, "no_delivery", "malformed_delivery"]


def test_the_manifest_names_the_agent_the_tree_has(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = json.loads((_recording(tmp_path, monkeypatch) / recording.MANIFEST).read_text())
    assert manifest["model_id"] == "fake"
    assert manifest["runtime_contract_version"] == CONTRACTS.runtime.version
    assert manifest["registry_fingerprint"] == reg.fingerprint()
    assert manifest["prompt_fingerprint"] == prompt_fingerprint(CONTEXT)


def test_an_edit_anywhere_moves_the_digest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = _recording(tmp_path, monkeypatch)
    manifest = json.loads((out / recording.MANIFEST).read_text(encoding="utf-8"))
    assert manifest["digest"] == recording.digest_of(out)
    target = out / "000.json"
    document = json.loads(target.read_text(encoding="utf-8"))
    document["proposal"]["mde"]["value"] = "50"
    target.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    assert recording.digest_of(out) != manifest["digest"], "an edited proposal kept its digest"


def test_the_mde_round_trips_as_a_string(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = _recording(tmp_path, monkeypatch)
    document = json.loads((out / "000.json").read_text(encoding="utf-8"))
    assert document["proposal"]["mde"]["value"] == "5.0"
    assert isinstance(document["proposal"]["mde"]["value"], str)


def test_a_recording_is_made_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = _recording(tmp_path, monkeypatch)
    with pytest.raises(FileExistsError):
        recording.record(["again"], context=CONTEXT, contracts=CONTRACTS, executor=Echo(), out=out)
    with pytest.raises(ValueError):
        recording.record(
            [], context=CONTEXT, contracts=CONTRACTS, executor=Echo(), out=tmp_path / "x"
        )
