"""Every `uses:` in every workflow names a commit, not a tag or a branch.

`ci.yml` said *pinned by sha like every other action here*, and it was true of `ci.yml` and of
none of the five workflows that carry the deploy role and the Databricks secret: those took
`@v4`, `@v3` and `databricks/setup-cli@main` -- a branch, on the workflow that runs `destroy`.
A tag moves when its publisher moves it; a branch moves when anyone with push does. Found by a
fresh-context review on 2026-09-12. The population is every workflow file, enumerated, so a
sixth workflow arrives under this rule rather than beside it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
USES = re.compile(r"^\s*-?\s*uses:\s*(?P<ref>[^\s#]+)", re.MULTILINE)
PINNED = re.compile(r"^[\w.-]+/[\w.-]+(/[\w./-]+)?@[0-9a-f]{40}$")


def _workflows() -> list[Path]:
    found = sorted(p for p in WORKFLOWS.iterdir() if p.suffix in (".yml", ".yaml"))
    assert found, "no workflow under .github/workflows/, so this gate would pass over nothing"
    return found


@pytest.mark.parametrize("path", _workflows(), ids=lambda p: p.name)
def test_every_action_the_workflow_uses_is_pinned_to_a_commit(path: Path) -> None:
    refs = [m.group("ref") for m in USES.finditer(path.read_text(encoding="utf-8"))]
    assert refs, f"{path.name} uses no action, which this reader does not expect"
    loose = [ref for ref in refs if not PINNED.match(ref)]
    assert not loose, (
        f"{path.name} takes {loose} by tag or branch. Pin each to a commit sha and write the "
        "tag it was resolved from beside it, as every other action in this repository is."
    )
