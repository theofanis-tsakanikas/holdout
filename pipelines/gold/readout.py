"""Running `generated/readout/*.sql` — the compiled artefact, with its parameters bound here.

**The claim this module supports is narrower than *the generated SQL has been executed*, and the
difference is one sentence.** What runs is the file on disk with `:name` replaced by SQL literals
and **nothing else changed**, and `bind` is written so that is checkable rather than asserted:
the executed text and the file are built from the **same** spans, so
`Bound.original == path.read_text()` fails if a single character outside a marker moved.

Why the binding is here rather than the engine's
------------------------------------------------
Spark has named parameters — `spark.sql(text, args={...})` — and on Spark 4.2.0 they work.
**They stop working the moment Delta's SQL extension is installed**, which this repository
installs because gold is Delta. Isolated in three measurements:

    no Delta at all                                   select :x as v  ->  1
    Delta *catalog* only, no extension                select :x as v  ->  1
    spark.sql.extensions=DeltaSparkSessionExtension    select :x as v  ->  UNBOUND_SQL_PARAMETER

`DeltaSqlParser` does not carry `args` through `parsePlanWithParameters`, so the marker survives
into analysis unbound. **That is a fact about delta-spark 4.4.0 with Spark 4.2.0, not a defect of
this repository and not a reason to change the artefact** — on Databricks the query is handed to
a warehouse that binds its own parameters, which is why the compiler emits them.

And one of the four cannot be a parameter on any of these versions:

    from gold.decision_economics version as of :data_version
      -> [UNEXPECTED_USE_OF_PARAMETER_MARKER] … found during AST building

raised by Spark's own `AstBuilder.visitVersion`. A time-travel clause takes a literal, so even a
Delta that threaded `args` correctly would refuse this one.

The pin is the point, and it is falsifiable
-------------------------------------------
`CLAUDE.md`: *"The readout pins a Delta version. Without it, re-running last month's readout
returns a different number as late data arrives."* Measured, same query and same store:

    pinned at version 1, before late data      3.48
    pinned at version 1, after late data       3.48
    unpinned, after late data                902.48

So the test is two-sided: the pinned number must survive an append, and the unpinned number must
not. An assertion with only the first half would pass over a table nobody had appended to.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pyspark.sql import DataFrame, SparkSession

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Where the compiled readouts are. Read from disk on every run rather than imported, because the
#: artefact `make contracts` byte-compares is the file — anything else would be a second copy.
READOUT_DIR = REPO_ROOT / "generated" / "readout"

#: Every parameter marker the compiler emits, in the artefact's own spelling.
PARAMETER = re.compile(r":(?P<name>[a-z_]+)")


class ParameterError(ValueError):
    """A marker in the artefact has no value, or a value was supplied for no marker."""


def artefact(metric_identifier: str) -> Path:
    """The compiled readout for one metric, by the identifier the compilers file it under."""
    path = READOUT_DIR / f"{metric_identifier}.sql"
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} does not exist. The readout is compiled from a metric contract by "
            "`make contracts`, and a missing one means the contract is not in force rather "
            "than that this argument was misspelled."
        )
    return path


def _literal(value: object) -> str:
    """One value as SQL text. Strings are quoted and doubled; integers are written as they are.

    **Nothing else is accepted.** A binder that stringified anything it was handed would put a
    date, a list or a `None` into the query as whatever `str()` made of it, which is doctrine
    rule 3 arriving through a formatter.
    """
    if isinstance(value, bool) or not isinstance(value, int | str):
        raise ParameterError(
            f"{value!r} is a {type(value).__name__}; a readout parameter is an int (a Delta "
            "version) or a str (an experiment id, an ISO week). Anything else would reach the "
            "query as whatever str() made of it."
        )
    if isinstance(value, int):
        return str(value)
    return "'" + value.replace("'", "''") + "'"


@dataclass(frozen=True, slots=True)
class Bound:
    """One compiled readout, split at its parameter markers, with both texts derivable.

    **This is the shape that makes the claim checkable instead of asserted.** `fixed` holds the
    spans between markers, taken from the file and never touched; `names` and `literals` hold
    what was substituted. The two texts are then built from the *same* spans:

        original  = fixed[0] + ":" + names[0] + fixed[1] + …
        executed  = fixed[0] +  literals[0]   + fixed[1] + …

    So *the only difference is at parameter positions* is not a sentence anybody has to trust —
    it is `Bound.original == path.read_text()`, which fails if a single character outside a
    marker moved.
    """

    fixed: tuple[str, ...]
    names: tuple[str, ...]
    literals: tuple[str, ...]

    @property
    def original(self) -> str:
        return self._join(tuple(f":{name}" for name in self.names))

    @property
    def executed(self) -> str:
        return self._join(self.literals)

    def _join(self, fillings: tuple[str, ...]) -> str:
        out: list[str] = []
        for index, span in enumerate(self.fixed):
            out.append(span)
            if index < len(fillings):
                out.append(fillings[index])
        return "".join(out)


def bind(text: str, parameters: Mapping[str, object]) -> Bound:
    """Split the artefact at its markers and substitute a literal for each, refusing a mismatch.

    Both directions of mismatch are refused, because they are different mistakes. A marker with
    no value would reach the engine unbound and raise there — loudly, but naming Delta's parser
    rather than the caller. A value with no marker is a caller who believes they are restricting
    something they are not, and that one fails **silently**: the query runs, over more rows than
    intended.
    """
    found = {match.group("name") for match in PARAMETER.finditer(text)}
    supplied = set(parameters)
    if found - supplied:
        raise ParameterError(f"the readout names {sorted(found - supplied)} and nothing bound it")
    if supplied - found:
        raise ParameterError(
            f"{sorted(supplied - found)} was bound and the readout names no such parameter, so "
            "the query would run without the restriction the caller believes it applied"
        )
    fixed: list[str] = []
    names: list[str] = []
    literals: list[str] = []
    cursor = 0
    for match in PARAMETER.finditer(text):
        fixed.append(text[cursor : match.start()])
        names.append(match.group("name"))
        literals.append(_literal(parameters[match.group("name")]))
        cursor = match.end()
    fixed.append(text[cursor:])
    return Bound(tuple(fixed), tuple(names), tuple(literals))


def run(
    spark: SparkSession,
    metric_identifier: str,
    *,
    experiment_id: str,
    data_version: int,
    period_start: str,
    period_end: str,
) -> tuple[DataFrame, Bound]:
    """Execute one compiled readout, and hand back the text that was executed beside the result.

    The `Bound` is returned rather than logged because it is evidence: `bound.original` rebuilds
    the file from the same spans the executed text was built from, so a caller — or a test — can
    compare it against the file on disk and see that nothing outside a marker moved.
    """
    path = artefact(metric_identifier)
    bound = bind(
        path.read_text(encoding="utf-8"),
        {
            "experiment_id": experiment_id,
            "data_version": data_version,
            "period_start": period_start,
            "period_end": period_end,
        },
    )
    return spark.sql(bound.executed), bound
