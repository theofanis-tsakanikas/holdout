"""No module under `corpus/` may import `holdout`. The whole of claim 1's independence.

`tests/boundary/test_core_imports_nothing.py` keeps the cloud out of the core. This is the
mirror of it, pointing the other way: it keeps the *system* out of the data that is supposed
to be independent of the system.

CLAUDE.md states the barrier for `corpus/world/` and gives the reason — a generator sharing
a "compute margin" function with the estimator would cancel a bug in it and both would agree
on a wrong number. The same argument applies a sentence earlier to `corpus/real/`: a corpus
that can reach the gates it exists to attack has stopped being an independent corpus, and it
would stop being one gradually, by the ordinary drift of whoever is editing both.

Checked by reading the source rather than by importing, for two reasons. An import test only
catches a *module-level* import, and the dangerous one is the local import inside a function
that somebody added in a hurry. And a `corpus` module that imported `holdout` successfully
would leave the test passing while the barrier was gone.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

CORPUS = Path(__file__).resolve().parents[2] / "corpus"

FORBIDDEN = "holdout"


def _modules() -> list[Path]:
    return sorted(CORPUS.rglob("*.py"))


def test_the_corpus_directory_has_modules_to_police() -> None:
    """A barrier over an empty directory is a barrier that has never been tested."""
    assert _modules(), "corpus/ contains no Python at all — this test would pass vacuously"


@pytest.mark.parametrize("module", _modules(), ids=lambda p: str(p.relative_to(CORPUS)))
def test_no_corpus_module_imports_the_system(module: Path) -> None:
    tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
    offences: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            offences += [
                a.name
                for a in node.names
                if a.name == FORBIDDEN or a.name.startswith(f"{FORBIDDEN}.")
            ]
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and (node.module == FORBIDDEN or node.module.startswith(f"{FORBIDDEN}."))
        ):
            offences.append(node.module)
    assert not offences, (
        f"{module.relative_to(CORPUS)} imports {offences}. The corpus is the independent "
        "evidence claim 1 is attacked with; the moment it can see the guardrails it is "
        "attacking, it starts agreeing with them. The join belongs in evals/, not here."
    )
