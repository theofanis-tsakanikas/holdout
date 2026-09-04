"""`python -m evals.definition` — claim 5's numbers, and an exit code.

It builds a rehearsal-scale world through bronze, silver and gold before it can compare
anything, which is minutes rather than seconds. That cost is the claim: the SQL mechanism is
the compiled artefact **executed**, and an eval that skipped the pipeline would be comparing
three implementations against data no engine ever produced.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from evals.definition import build, checks
from evals.report import Report, main


def run() -> Report:
    from holdout.contracts import loader
    from holdout.contracts.compilers import in_force_metrics

    repo = Path(__file__).resolve().parents[2]
    contracts = loader.load(repo / "contracts")
    metric = next(m for m in in_force_metrics(contracts) if m.id == checks.METRIC_ID)
    tool = json.loads(
        (repo / "generated" / "agent_tools" / f"{metric.id}.v{metric.version}.json").read_text(
            encoding="utf-8"
        )
    )

    with tempfile.TemporaryDirectory(prefix="holdout-claim-5-") as scratch:
        root = Path(scratch)
        # Everything the engine says goes to stderr: `make gate-proof` reads this process's
        # stdout as JSON, and a progress bar on it is an eval that reported nothing.
        with build.engine_noise_on_stderr():
            schema, spark = build.gold_tables(root)
            try:
                # The one cell this eval writes itself. See `build.CONSTRUCTED_CELL`: the corpus
                # cannot exercise the contract's rounding at all, and this is the value where
                # the two rounding rules part company.
                build.append_constructed_cell(spark, schema, root)
                economics, waste = build.economics_and_waste(spark, schema)
                answer = build.sql_answer(spark, schema, metric)
                unpriced, priced = build.drop_counts(spark, schema)
            finally:
                spark.stop()

    return checks.report(answer, economics, waste, metric, tool, unpriced, priced)


if __name__ == "__main__":
    sys.exit(main(run(), sys.argv[1:]))
