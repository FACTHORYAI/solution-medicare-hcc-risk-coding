"""Calculate the risk adjustment factor for every patient."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from medicare_hcc_risk_coding import raf
from medicare_hcc_risk_coding.jobs._duck import align
from medicare_hcc_risk_coding.schemas import PATIENT_RISK

INPUTS = ("patient_profiles",)
OUTPUTS = ("patient_risk",)


@dataclass(frozen=True)
class Params:
    """Parameters for the risk adjustment factor."""


def run(inputs: dict[str, pa.Table], params: Params) -> dict[str, pa.Table]:
    """Return the demographic and HCC components and their summed risk score per patient."""
    rows = []
    for profile in inputs["patient_profiles"].to_pylist():
        hccs = [int(hcc) for hcc in profile["hcc_list"] or []]
        rows.append(
            {
                "patient_id": profile["patient_id"],
                "age": profile["age"],
                "gender": profile["gender"],
                "demographic_weight": raf.demographic_weight(profile["age"], profile["gender"]),
                "hcc_weight": raf.hcc_weight(hccs),
                "risk_score": raf.risk_adjustment_factor(profile["age"], profile["gender"], hccs),
                "hcc_count": len(hccs),
            }
        )
    return {"patient_risk": align(pa.Table.from_pylist(rows, schema=PATIENT_RISK), PATIENT_RISK)}
