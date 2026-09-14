"""`ops/demo_queries.sql` is a Databricks SQL notebook and the file `inspect` executes, at once.

One file, two readers: `infra/lakehouse` imports it as a notebook, one cell per block with its
explanation in a markdown cell above; `ops/inspect_estate.py` executes every `-- @name` block
against the warehouse. This holds the two shapes together — a block the notebook shows must be a
block the gate runs, and the other way round — so the queries a viewer types are the queries
that were measured.
"""

from __future__ import annotations

import re
from pathlib import Path

from ops.inspect_estate import DEMO_QUERIES, demo_blocks

TEXT = DEMO_QUERIES.read_text(encoding="utf-8")


def test_the_file_is_a_notebook_source() -> None:
    assert TEXT.startswith("-- Databricks notebook source\n")
    assert "-- COMMAND ----------" in TEXT


def test_every_block_the_gate_runs_has_its_own_cell_with_an_explanation_above() -> None:
    blocks = demo_blocks(TEXT)
    assert len(blocks) >= 10
    cells = TEXT.split("-- COMMAND ----------")
    named = [c for c in cells if re.search(r"^-- @name ", c, re.MULTILINE)]
    assert len(named) == len(blocks), "a block is not a cell of its own, or a cell holds two"
    for index, cell in enumerate(cells):
        match = re.search(r"^-- @name (\S+)", cell, re.MULTILINE)
        if not match:
            continue
        above = cells[index - 1]
        assert f"-- MAGIC ## {match.group(1)}" in above, (
            f"the cell for {match.group(1)} has no markdown cell naming it above"
        )


def test_the_terraform_imports_this_file_and_nothing_else_as_the_demo() -> None:
    tf = (Path(__file__).resolve().parents[2] / "infra" / "lakehouse" / "dashboards.tf").read_text()
    assert 'source   = "${path.module}/../../ops/demo_queries.sql"' in tf
    assert 'language = "SQL"' in tf
