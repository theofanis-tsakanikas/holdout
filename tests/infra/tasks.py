"""Reading the Databricks tasks out of Terraform, once, for the gates that judge them.

Three gates ask different questions of the same population — *does this task name its catalog*,
*does dbt run after what writes its sources*, *does training read the estate* — and a population
enumerated three ways is three chances for one of them to be reading a different set from the one
it reports on. So the enumeration is here and the gates state what they assert against it.

**Terraform is read as text rather than planned.** A plan needs credentials and an account; what
these gates check is a property of the repository, and `CLAUDE.md`'s rule is *IaC only, no console
actions* — so the file is the authority.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INFRA = REPO_ROOT / "infra"

_COMMENT = re.compile(r"^\s*#.*$", re.MULTILINE)
#: `parameters = [` and `parameters = concat(`. **The second was invisible and that is the kind
#: of hole this repository keeps finding.** A task whose list is built by `concat` — the two
#: history slices, whose window instance appends four arguments the baseline does not take —
#: matched nothing, so it silently left every gate's population that reads this. A gate over a
#: population that quietly excludes the interesting member is a gate that reports OK.
_PARAMETERS = re.compile(r"parameters\s*=\s*(\[|concat\s*\()")
_STRING = re.compile(r'"([^"]*)"')
_TASK_KEY = re.compile(r'task_key\s*=\s*"([^"]+)"')


def files() -> list[Path]:
    """Every Terraform file under `infra/`, in a stable order."""
    return sorted(INFRA.glob("*/*.tf")) if INFRA.is_dir() else []


def parameter_lists() -> list[tuple[str, list[str]]]:
    """Every `(where, parameters)` any layer gives a task, comments removed first.

    Comments are stripped before the list is read: a comment inside a parameter list that
    happened to quote something would otherwise become a parameter nobody passed.

    **An expression is kept as `<expr>` rather than as its text.** `local.catalog` and
    `local.zone_path["bronze"]` are values Terraform resolves, and reading the second one's inner
    string as a parameter would invent one. What these gates assert is which *flags* a task
    passes; what each flag resolves to is Terraform's business and a plan's.
    """
    found: list[tuple[str, list[str]]] = []
    for path in files():
        text = _COMMENT.sub("", path.read_text(encoding="utf-8"))
        for match in _PARAMETERS.finditer(text):
            where = str(path.relative_to(REPO_ROOT))
            found.append((where, _tokens(_region(text, match))))
    return found


def _region(text: str, match: re.Match[str]) -> str:
    """Everything the parameters expression contains, whichever way it was written.

    A `concat(...)` is read whole and its brackets left in: `_tokens` splits on the commas that
    separate elements at depth zero, so the inner lists' commas are inside a bracket and the
    lists themselves come back as `<expr>` — which would lose the flags. So for `concat` the
    brackets are stripped first and the pieces joined, giving one flat list, which is what
    Terraform will hand the task.
    """
    if match.group(1) == "[":
        return _bracketed(text, match.end(), closing="]")
    inside = _bracketed(text, match.end(), closing=")")
    pieces: list[str] = []
    depth = 0
    current = ""
    for character in inside:
        if character == "[":
            depth += 1
            if depth == 1:
                current = ""
                continue
        if character == "]":
            depth -= 1
            if depth == 0:
                pieces.append(current)
                continue
        if depth:
            current += character
    return ",".join(piece for piece in pieces if piece.strip())


def _bracketed(text: str, start: int, *, closing: str = "]") -> str:
    r"""The text up to the `]` that closes the list, and not the first `]` in it.

    `local.zone_path["bronze"]` carries a bracket of its own. A non-greedy `\[(.*?)\]` stops
    there and returns a list one element long — which read as a task that passes `--bronze` and
    nothing else, on the very gate whose job is to notice a missing flag. Measured: the silver
    task's `--catalog` disappeared from the enumeration while the file still had it.
    """
    opening = {"]": "[", ")": "("}[closing]
    depth = 1
    quoted = False
    for offset, character in enumerate(text[start:]):
        if character == '"':
            quoted = not quoted
        if quoted:
            continue
        if character == opening:
            depth += 1
        elif character == closing:
            depth -= 1
            if depth == 0:
                return text[start : start + offset]
    return text[start:]


def _tokens(block: str) -> list[str]:
    """One entry per comma-separated element: the string it is, or `<expr>` for anything else."""
    parameters: list[str] = []
    for element in _elements(block):
        literal = _STRING.fullmatch(element)
        parameters.append(literal.group(1) if literal else "<expr>")
    return parameters


def _elements(block: str) -> list[str]:
    """Split on the commas that separate elements, and not on the ones inside brackets."""
    elements: list[str] = []
    current = ""
    depth = 0
    quoted = False
    for character in block:
        if character == '"':
            quoted = not quoted
        if not quoted and character in "[({":
            depth += 1
        if not quoted and character in "])}":
            depth -= 1
        if character == "," and depth == 0 and not quoted:
            elements.append(current.strip())
            current = ""
            continue
        current += character
    if current.strip():
        elements.append(current.strip())
    return [element for element in elements if element]


def task_blocks(path: Path) -> list[tuple[str, str]]:
    """Every `(task_key, body)` in one Terraform file, split on `task {` at task indentation.

    Crude on purpose: the shape being read is two levels deep and stable, and a real HCL parse
    would be a dependency this repository does not otherwise need.
    """
    text = path.read_text(encoding="utf-8")
    blocks: list[tuple[str, str]] = []
    parts = text.split("\n  task {")
    for part in parts[1:]:
        body = part.split("\n  }")[0]
        key = _TASK_KEY.search(body)
        blocks.append((key.group(1) if key else "?", body))
    return blocks
