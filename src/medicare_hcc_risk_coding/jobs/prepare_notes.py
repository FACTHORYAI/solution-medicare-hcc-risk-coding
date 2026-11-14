"""Prepare the notes: keep the rows that carry both identifiers and text."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from medicare_hcc_risk_coding import io
from medicare_hcc_risk_coding.jobs._duck import align, run_query
from medicare_hcc_risk_coding.schemas import NOTES

INPUTS = ("notes_raw",)
OUTPUTS = ("notes",)


@dataclass(frozen=True)
class Params:
    """Parameters for the note preparation."""


def run(inputs: dict[str, pa.Table], params: Params) -> dict[str, pa.Table]:
    """Return the notes that carry both a note and a patient identifier."""
    table = run_query(io.read_sql("prepare_notes"), inputs)
    return {"notes": align(table, NOTES)}
