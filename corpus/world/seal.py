"""The injected truth, sealed until the readout has been written.

`CLAUDE.md`: *"the injected truth lives in a sealed file the harness opens **only after** the
readout has been written."* This module is that file's format and the one door into it.

What is sealed, and what is not
-------------------------------
What is sealed is **behaviour**: which schedule the treated arm was given, how much trade
crossed to a neighbour, how many labels never took the price, how fast the novelty decayed.

What is **not** sealed — because it does not exist anywhere — is the effect on the metric. The
generator injects three more units per store, not four thousand euros per week, so the true
effect on `category_margin_per_store_week` has to be *computed*: re-run the world under
all-control with the same seed, loop over every event in Python, and subtract. That is T003's
reference implementation, and it happens after the readout for the same reason this file is
shut.

So opening this seal early does not hand anybody the answer. It hands them the ingredients,
which is quite bad enough: an exposure rate is exactly the number an honest exposure check is
supposed to discover for itself.

What the seal actually guarantees, stated exactly
-------------------------------------------------
**It is not encryption and it is not trying to be.** The keystream is derived from a nonce
stored in the same file, so anyone who reads this module can decode the payload without
touching `open_after_readout`. Calling it a lock would be the kind of sentence this repository
exists to refuse.

What it is:

- **The accident is impossible.** The truth is not in the harness's process. `run()` never
  returns it, no dataclass the harness holds has it as an attribute, and the file it sits in
  yields nothing to `cat`, `grep`, a diff or an editor. The realistic failure — a number in
  scope at the moment an estimate is formed, and a small unexamined decision made because of
  it — has nowhere to happen.
- **The legitimate opening is recorded.** `open_after_readout` refuses without a readout that
  exists, and appends the readout's digest to an append-only ledger inside the seal. An eval
  can then assert what `evals/uplift/` will assert: exactly one opening, and its digest is the
  digest of the readout that was published.
- **The seal cannot be edited quietly.** The commitment is a SHA-256 over the plaintext,
  written when the seal is made. `verify` recomputes it.

The limit is the same shape as the certificate's in `holdout.core.guardrails`, and it is worth
stating in the same words: a coordinated rewrite — decode the payload, change it, re-seal, and
forge the ledger — is not caught, because a seal never held independent evidence of its own
provenance. **It makes the mistake impossible and leaves the forgery visible.**
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

#: The file a world's truth is sealed into, beside whatever else the run wrote.
SEAL_FILENAME = "truth.sealed.json"

_FORMAT = "holdout/world-seal@1"


class SealError(Exception):
    """The seal cannot be read as a seal, or is being opened at the wrong moment."""


@dataclass(frozen=True, slots=True)
class WorldTruth:
    """What the generator injected. Behaviour, never a number about money.

    `effect_on_the_metric` is a sentence rather than a field with a value in it, and that is
    deliberate: a reader who came here looking for the answer should find the reason there
    isn't one, in the place they looked.
    """

    world: str
    title: str
    seed: str
    scale: str
    control_policy: dict[str, Any]
    treatment_policy: dict[str, Any]
    injection: dict[str, Any]
    exposure_by_store: list[dict[str, Any]]
    totals: dict[str, int]
    #: The stores this run actually covered, or `None` for the whole chain. A window's truth
    #: is not the world's truth, and a seal that did not say which one it was would be a
    #: partial exposure rate wearing a whole world's name.
    restricted_to_stores: list[str] | None = None
    effect_on_the_metric: str = (
        "Not here, and not anywhere. The generator injects behaviour, not a metric. The true "
        "effect on category_margin_per_store_week must be computed by re-running this world "
        "under all-control with the same seed and looping over every event — which is T003's "
        "reference implementation, and which happens after the readout."
    )


def _keystream(nonce: bytes, length: int) -> bytes:
    """A blake2b counter stream. An envelope, not a lock — see the module docstring."""
    out = bytearray()
    counter = 0
    while len(out) < length:
        out += hashlib.blake2b(
            counter.to_bytes(8, "big"), key=nonce, digest_size=64, person=b"holdout-seal"
        ).digest()
        counter += 1
    return bytes(out[:length])


def _obscure(plaintext: bytes, nonce: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(plaintext, _keystream(nonce, len(plaintext)), strict=True))


def seal(truth: WorldTruth, directory: Path) -> Path:
    """Write the truth into `directory`, shut. Returns the path, never the contents."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / SEAL_FILENAME
    plaintext = json.dumps(asdict(truth), sort_keys=True, indent=None).encode("utf-8")
    # Derived from the world and the seed, so a re-run of the same world produces a
    # byte-identical seal. A random nonce would make the seal the one part of a reproducible
    # corpus that could not be reproduced.
    nonce = hashlib.blake2b(
        f"{truth.world}\x1f{truth.seed}\x1f{truth.scale}".encode(), digest_size=32
    ).digest()
    document = {
        "format": _FORMAT,
        # The header is deliberately thin: enough to know *which* seal this is and to line it
        # up with a run, and not one field more. A header carrying the arm counts would be a
        # seal that leaks the shape of the assignment to anyone listing the directory.
        "world": truth.world,
        "seed": truth.seed,
        "scale": truth.scale,
        "sealed_at": datetime.now(UTC).isoformat(),
        "commitment_sha256": hashlib.sha256(plaintext).hexdigest(),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "payload": base64.b64encode(_obscure(plaintext, nonce)).decode("ascii"),
        "openings": [],
        "note": (
            "Sealed. It is opened by corpus.world.seal.open_after_readout, which requires the "
            "readout it is being checked against and records the opening below. Opening it any "
            "other way is possible and is the thing this file exists to make visible."
        ),
    }
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


def _document(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SealError(f"{path} cannot be read as a seal: {error}") from error
    if not isinstance(document, dict) or document.get("format") != _FORMAT:
        raise SealError(f"{path} is not a {_FORMAT} seal")
    return document


def header(path: Path) -> dict[str, Any]:
    """Which world, which seed, which scale, and who has opened it. No payload."""
    document = _document(path)
    return {key: document[key] for key in ("world", "seed", "scale", "sealed_at", "openings")}


def openings(path: Path) -> list[dict[str, Any]]:
    """The ledger. Every legitimate opening, in the order they happened."""
    ledger = _document(path)["openings"]
    return list(ledger) if isinstance(ledger, list) else []


def verify(path: Path) -> bool:
    """Does the payload still hash to the commitment written when the seal was made?"""
    document = _document(path)
    plaintext = _obscure(base64.b64decode(document["payload"]), base64.b64decode(document["nonce"]))
    return hashlib.sha256(plaintext).hexdigest() == str(document["commitment_sha256"])


def open_after_readout(path: Path, readout: Path) -> WorldTruth:
    """Open the seal against a readout that has already been written.

    Refuses when the readout does not exist, which is the whole of the ordering guarantee: a
    caller cannot get here before the number it is about to be graded on is on disk and
    unchangeable. The readout's digest goes into the ledger, so the grading can be checked
    afterwards by someone who was not in the room.
    """
    document = _document(path)
    if not readout.is_file():
        raise SealError(
            f"{readout} does not exist. The seal opens after the readout has been written, "
            "never before — an estimate formed while the truth was in scope is not evidence "
            "of anything."
        )
    if not verify(path):
        raise SealError(f"{path} does not match its own commitment; it has been edited")
    body = readout.read_bytes()
    plaintext = _obscure(base64.b64decode(document["payload"]), base64.b64decode(document["nonce"]))
    document["openings"].append(
        {
            "opened_at": datetime.now(UTC).isoformat(),
            "readout": readout.name,
            "readout_sha256": hashlib.sha256(body).hexdigest(),
            "readout_bytes": len(body),
        }
    )
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return WorldTruth(**json.loads(plaintext))
