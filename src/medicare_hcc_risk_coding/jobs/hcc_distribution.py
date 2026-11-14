"""Which HCCs drive the risk scores."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from medicare_hcc_risk_coding import io
from medicare_hcc_risk_coding.jobs._duck import align, run_query
from medicare_hcc_risk_coding.schemas import HCC_DISTRIBUTION

INPUTS = ("patient_profiles", "hcc_weights")
OUTPUTS = ("hcc_distribution",)


@dataclass(frozen=True)
class Params:
    """Parameters for the HCC distribution."""


def run(inputs: dict[str, pa.Table], params: Params) -> dict[str, pa.Table]:
    """Return the patient count and weight of every HCC the cohort carries."""
    table = run_query(io.read_sql("hcc_distribution"), inputs)
    return {"hcc_distribution": align(table, HCC_DISTRIBUTION)}
