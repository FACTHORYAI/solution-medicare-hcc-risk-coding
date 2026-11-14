"""One patient profile: demographics, administrative status and the counted HCCs."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from medicare_hcc_risk_coding import io
from medicare_hcc_risk_coding.jobs._duck import align, run_query
from medicare_hcc_risk_coding.schemas import PATIENT_PROFILES

INPUTS = ("icd10_codes", "demographics", "patient_status")
OUTPUTS = ("patient_profiles",)


@dataclass(frozen=True)
class Params:
    """Parameters for the patient profiles."""


def run(inputs: dict[str, pa.Table], params: Params) -> dict[str, pa.Table]:
    """Return the profile rows, keeping only HCCs that risk adjustment counts."""
    table = run_query(io.read_sql("build_patient_profiles"), inputs)
    return {"patient_profiles": align(table, PATIENT_PROFILES)}
