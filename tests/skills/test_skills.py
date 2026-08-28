"""`.claude/skills/` — the procedures that ship with the repository, checked as wiring.

This is `tests/hooks/test_settings.py`'s argument one directory along, and deliberately a much
weaker one, because the failure it prevents is much smaller. A hook whose command does not
resolve leaves a **guarantee** silently dead while the suite stays green. A skill whose
frontmatter does not parse, or whose `name` disagrees with its directory, simply does not load:
it is a procedure nobody can invoke, which is visible the first time somebody tries.

What is worth checking anyway is the same class of thing — the parts a reader assumes are true
and nothing reads:

* the frontmatter parses, and carries the two keys an invocation is matched on;
* `name` is the directory, because that is what an invocation names;
* `description` says *when* to reach for the skill and not only what it is;
* **every file bundled beside a skill is referenced by it, and every relative link resolves.**
  `readme-standard` at user level bundles a `TEMPLATE.md` and a `CHECKLIST.md`; a skill that
  sends a session to a file that has been renamed is a hook wired to a path that moved, and a
  bundled file nothing points at is the copy nobody reads.

**The last pair is armed by a planted fixture and by nothing in `.claude/skills/`.** No skill
here bundles a second file today, so both directions would be vacuously green on the real tree —
the shape of defect this repository has already paid for once, in a text fallback whose twelve
parametrised sources all took the other branch. `_planted` builds a skill directory that is wrong
in each direction and requires the check to refuse it, exactly as `tests/ops/test_expiry.py`
arms `make expiry` with a deferral the real registry does not contain.

What this does **not** check, said here rather than assumed:

* **whether the skill is right.** Nothing can. The method `skills/claim/` describes is stood
  behind by the claim targets, `make gate-proof` and oversight level 2 — not by this file;
* **whether the skill is followed.** A procedure is not a guarantee; that distinction is the
  whole of `CLAUDE.md`'s three-mechanism table, and a test asserting otherwise would be claiming
  a hook where there is a skill;
* **references to repository paths.** `` `evals/README.md` `` inside a paragraph is prose about
  the repository, not wiring beside the skill, and resolving it here would make every renamed
  module a red skill test. The pull-request diff is what covers that.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS = REPO_ROOT / ".claude" / "skills"

#: A skill directory is `<name>/SKILL.md`, and `name` is what an invocation says.
ENTRY_POINT = "SKILL.md"

#: A markdown link whose target is relative — no scheme, no leading slash, no anchor. Those are
#: the only references that must resolve beside the skill; everything else is prose.
RELATIVE_LINK = re.compile(r"\[[^\]]*\]\((?!https?:|mailto:|#|/)([^)\s]+)\)")


def skill_dirs() -> list[Path]:
    if not SKILLS.is_dir():
        return []
    return sorted(p for p in SKILLS.iterdir() if p.is_dir())


def _frontmatter(text: str, where: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        raise AssertionError(f"{where}: SKILL.md does not open with YAML frontmatter")
    block, marker, _ = text[len("---\n") :].partition("\n---\n")
    if not marker:
        raise AssertionError(f"{where}: the frontmatter block is never closed")
    parsed = yaml.safe_load(block)
    assert isinstance(parsed, dict), f"{where}: frontmatter is not a mapping"
    return parsed


def unreferenced(skill: Path) -> list[str]:
    """Files bundled beside a skill that its `SKILL.md` never names — the copy nobody reads."""
    text = (skill / ENTRY_POINT).read_text(encoding="utf-8")
    bundled = {p.name for p in skill.iterdir() if p.is_file()} - {ENTRY_POINT}
    return sorted(name for name in bundled if name not in text)


def unresolved(skill: Path) -> list[str]:
    """Relative links in a `SKILL.md` that point at nothing on disk."""
    text = (skill / ENTRY_POINT).read_text(encoding="utf-8")
    targets = {m.group(1) for m in RELATIVE_LINK.finditer(text)}
    return sorted(t for t in targets if not (skill / t).exists())


def test_there_is_at_least_one_skill() -> None:
    """CLAUDE.md's skill table names four that live here; a run with none is the table lying.

    It asserts existence rather than the table's contents on purpose: three of the four are open
    tasks, and a test demanding all four would be red for the whole time they are correctly
    absent. A gate that fires on work not yet started teaches people to switch it off.
    """
    assert skill_dirs(), ".claude/skills/ holds no skill, and CLAUDE.md says it holds four"


@pytest.mark.parametrize("skill", skill_dirs(), ids=lambda p: p.name)
def test_every_skill_directory_has_its_entry_point(skill: Path) -> None:
    assert (skill / ENTRY_POINT).is_file(), f"{skill.name}/ has no {ENTRY_POINT}"


@pytest.mark.parametrize("skill", skill_dirs(), ids=lambda p: p.name)
def test_frontmatter_names_the_directory_and_says_when_to_use_it(skill: Path) -> None:
    front = _frontmatter((skill / ENTRY_POINT).read_text(encoding="utf-8"), skill.name)
    assert set(front) >= {"name", "description"}, f"{skill.name}: missing name or description"
    assert front["name"] == skill.name, (
        f"{skill.name}: frontmatter name is {front['name']!r}; an invocation names the directory"
    )
    description = front["description"]
    assert isinstance(description, str) and description.strip(), (
        f"{skill.name}: description is empty, so nothing can decide when to reach for it"
    )
    assert "use when" in description.lower(), (
        f"{skill.name}: the description says what the skill is and never when to invoke it"
    )


@pytest.mark.parametrize("skill", skill_dirs(), ids=lambda p: p.name)
def test_no_bundled_file_is_unreferenced(skill: Path) -> None:
    assert not unreferenced(skill), (
        f"{skill.name}: bundles files its SKILL.md never names: {unreferenced(skill)}"
    )


@pytest.mark.parametrize("skill", skill_dirs(), ids=lambda p: p.name)
def test_every_relative_link_resolves(skill: Path) -> None:
    assert not unresolved(skill), (
        f"{skill.name}: links to files that do not exist beside it: {unresolved(skill)}"
    )


# --------------------------------------------------------------- the two checks, armed

FRONTMATTER = "---\nname: {name}\ndescription: A planted skill. Use when arming this test.\n---\n"


def _planted(root: Path, name: str, body: str, bundled: dict[str, str]) -> Path:
    skill = root / name
    skill.mkdir()
    (skill / ENTRY_POINT).write_text(FRONTMATTER.format(name=name) + body, encoding="utf-8")
    for filename, content in bundled.items():
        (skill / filename).write_text(content, encoding="utf-8")
    return skill


def test_an_unreferenced_bundled_file_is_caught(tmp_path: Path) -> None:
    """No real skill bundles a file yet, so the real tree cannot arm this. A planted one can."""
    skill = _planted(
        tmp_path, "planted", "Open `TEMPLATE.md`.\n", {"TEMPLATE.md": "", "STRAY.md": ""}
    )
    assert unreferenced(skill) == ["STRAY.md"]


def test_a_referenced_bundled_file_is_not_caught(tmp_path: Path) -> None:
    """The other direction, because a check that refuses everything proves nothing either."""
    skill = _planted(tmp_path, "planted", "Open `TEMPLATE.md`.\n", {"TEMPLATE.md": ""})
    assert unreferenced(skill) == []


def test_a_relative_link_to_a_missing_file_is_caught(tmp_path: Path) -> None:
    skill = _planted(tmp_path, "planted", "See [the template](TEMPLATE.md).\n", {})
    assert unresolved(skill) == ["TEMPLATE.md"]


def test_an_absolute_or_external_link_is_left_alone(tmp_path: Path) -> None:
    """A URL and a repository-rooted path are prose, not wiring beside the skill."""
    body = "See [the docs](https://example.invalid/x) and [the plan](/PLAN.md).\n"
    skill = _planted(tmp_path, "planted", body, {})
    assert unresolved(skill) == []
