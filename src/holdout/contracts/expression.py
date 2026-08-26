"""The declared grammar of a metric expression, and its parser. Stdlib only.

An expression is a signed sum of aggregate terms:

    <expression> ::= <term> { ("+" | "-") <term> }
    <term>       ::= "sum" "(" <inner> ")"

and **each `<inner>` references exactly one declared source alias**. That restriction is not
stylistic. A metric is defined at a grain over several relations, and the only way to
compute it without fanning out — three sale rows against two waste rows in the same cell
multiplying into six — is to aggregate each relation to the grain first and combine the
aggregates afterwards. A term that straddled two relations could not be assigned to either
CTE, so the grammar refuses it rather than letting a compiler guess.

Everything downstream falls out of this: the dbt model, the SQL function, the readout query
and the agent's tool definition are all rendered from the same parsed terms, which is what
"a contract compiles; it is never interpreted by hand-written code in two places" means in
practice.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

_ALIAS_REF = re.compile(r"\b([a-z]{1,3})\.([a-z_][a-z0-9_]*)\b")
_SUM = re.compile(r"^sum\s*\((?P<inner>.+)\)$", re.IGNORECASE | re.DOTALL)


class ExpressionError(ValueError):
    """An expression outside the declared grammar."""


@dataclass(frozen=True, slots=True)
class Term:
    index: int
    sign: Literal["+", "-"]
    alias: str
    inner: str
    """The aggregate argument with alias prefixes stripped, ready to sit inside the
    alias's own grouped CTE where the columns are unqualified."""

    @property
    def column(self) -> str:
        return f"term_{self.index}"

    def render(self) -> str:
        return f"sum({self.inner}) as {self.column}"


def parse(expression: str, aliases: tuple[str, ...]) -> tuple[Term, ...]:
    """Parse an expression, or raise `ExpressionError` naming what is wrong with it."""
    flat = " ".join(expression.split())
    if not flat:
        raise ExpressionError("empty expression")

    terms: list[Term] = []
    for index, (sign, chunk) in enumerate(_split_top_level(flat)):
        match = _SUM.match(chunk.strip())
        if match is None:
            raise ExpressionError(
                f"term {index + 1} is {chunk.strip()!r}. Every term must be a single "
                "sum(...) aggregate; the grammar has no room for a bare column, a nested "
                "expression or a second aggregate function."
            )
        inner = " ".join(match.group("inner").split())
        used = {ref.group(1) for ref in _ALIAS_REF.finditer(inner)}
        if not used:
            raise ExpressionError(
                f"term {index + 1} ({chunk.strip()!r}) references no source alias. Every "
                "column must be qualified, so that the term can be assigned to exactly one "
                "relation."
            )
        if len(used) > 1:
            raise ExpressionError(
                f"term {index + 1} ({chunk.strip()!r}) straddles aliases "
                f"{sorted(used)}. Each aggregate term must belong to exactly one relation, "
                "or aggregating to the grain fans out and the metric double-counts."
            )
        alias = used.pop()
        if alias not in aliases:
            raise ExpressionError(
                f"term {index + 1} references alias {alias!r}, which is not declared in "
                f"`sources` (declared: {list(aliases)})."
            )
        terms.append(
            Term(
                index=index,
                sign=sign,
                alias=alias,
                inner=_ALIAS_REF.sub(lambda m: m.group(2), inner),
            )
        )

    unused = [a for a in aliases if a not in {t.alias for t in terms}]
    if unused:
        raise ExpressionError(
            f"sources declare alias(es) {unused} that the expression never uses. A relation "
            "nobody reads is a join nobody needs, and it would still be emitted into every "
            "compiled consumer."
        )
    return tuple(terms)


def combine(terms: tuple[Term, ...]) -> str:
    """The arithmetic that puts the per-relation aggregates back together.

    A grain cell present in one relation and absent from the other is a real case — a week
    with sales and no waste — so a missing side contributes zero rather than turning the
    whole cell null.
    """
    parts: list[str] = []
    for term in terms:
        piece = f"coalesce({term.alias}.{term.column}, 0)"
        if not parts:
            parts.append(piece if term.sign == "+" else f"-{piece}")
        else:
            parts.append(f"{term.sign} {piece}")
    return " ".join(parts)


def _split_top_level(flat: str) -> list[tuple[Literal["+", "-"], str]]:
    chunks: list[tuple[Literal["+", "-"], str]] = []
    depth = 0
    start = 0
    sign: Literal["+", "-"] = "+"
    for position, char in enumerate(flat):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise ExpressionError("unbalanced parentheses")
        elif char in "+-" and depth == 0 and position > start:
            chunks.append((sign, flat[start:position]))
            sign = "+" if char == "+" else "-"
            start = position + 1
    if depth != 0:
        raise ExpressionError("unbalanced parentheses")
    chunks.append((sign, flat[start:]))
    return chunks
