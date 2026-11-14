"""How the population distributes over risk-score bands."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from medicare_hcc_risk_coding import io
from medicare_hcc_risk_coding.jobs._duck import align, run_query
from medicare_hcc_risk_coding.schemas import RAF_BANDS

INPUTS = ("patient_risk",)
OUTPUTS = ("raf_bands",)


@dataclass(frozen=True)
class Params:
    """Parameters for the risk-band summary."""


def run(inputs: dict[str, pa.Table], params: Params) -> dict[str, pa.Table]:
    """Return patient counts and the average risk score per risk band."""
    table = run_query(io.read_sql("raf_bands"), inputs)
    return {"raf_bands": align(table, RAF_BANDS)}
