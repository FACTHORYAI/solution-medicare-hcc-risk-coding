"""The jobs of this solution: plain functions from named tables to named tables."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pyarrow as pa

from medicare_hcc_risk_coding.jobs import (
    build_patient_profiles,
    calculate_raf,
    extract_icd10,
    hcc_distribution,
    infer_demographics,
    prepare_notes,
    raf_summary,
)


@dataclass(frozen=True)
class JobSpec:
    """One job: its callable, its parameter class and its input and output tables."""

    name: str
    description: str
    run: Callable[..., dict[str, pa.Table]]
    params_cls: type
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    needs_model: bool = False


REGISTRY: dict[str, JobSpec] = {
    spec.name: spec
    for spec in (
        JobSpec(
            name="prepare_notes",
            description="Prepare the notes: keep the rows that carry both identifiers and text.",
            run=prepare_notes.run,
            params_cls=prepare_notes.Params,
            inputs=prepare_notes.INPUTS,
            outputs=prepare_notes.OUTPUTS,
        ),
        JobSpec(
            name="extract_icd10",
            description="Code each note's problems to ICD-10-CM with HCC and assertion.",
            run=extract_icd10.run,
            params_cls=extract_icd10.Params,
            inputs=extract_icd10.INPUTS,
            outputs=extract_icd10.OUTPUTS,
            needs_model=True,
        ),
        JobSpec(
            name="infer_demographics",
            description="Infer the patient's gender at birth and age from each note.",
            run=infer_demographics.run,
            params_cls=infer_demographics.Params,
            inputs=infer_demographics.INPUTS,
            outputs=infer_demographics.OUTPUTS,
            needs_model=True,
        ),
        JobSpec(
            name="build_patient_profiles",
            description="One profile per patient: demographics, status and the counted HCCs.",
            run=build_patient_profiles.run,
            params_cls=build_patient_profiles.Params,
            inputs=build_patient_profiles.INPUTS,
            outputs=build_patient_profiles.OUTPUTS,
        ),
        JobSpec(
            name="calculate_raf",
            description="Calculate the risk adjustment factor for every patient.",
            run=calculate_raf.run,
            params_cls=calculate_raf.Params,
            inputs=calculate_raf.INPUTS,
            outputs=calculate_raf.OUTPUTS,
        ),
        JobSpec(
            name="raf_summary",
            description="How the population distributes over risk-score bands.",
            run=raf_summary.run,
            params_cls=raf_summary.Params,
            inputs=raf_summary.INPUTS,
            outputs=raf_summary.OUTPUTS,
        ),
        JobSpec(
            name="hcc_distribution",
            description="Which HCCs drive the risk scores.",
            run=hcc_distribution.run,
            params_cls=hcc_distribution.Params,
            inputs=hcc_distribution.INPUTS,
            outputs=hcc_distribution.OUTPUTS,
        ),
    )
}


def param_values(spec: JobSpec, args: Any) -> Any:
    """Build the job's Params instance from parsed command-line arguments."""
    values = {
        field.name: getattr(args, field.name)
        for field in spec.params_cls.__dataclass_fields__.values()
    }
    return spec.params_cls(**values)


def call_run(
    spec: JobSpec, inputs: dict[str, pa.Table], params: Any, model: Any
) -> dict[str, pa.Table]:
    """Call the job's run with the arguments its signature asks for."""
    if spec.needs_model:
        return spec.run(inputs=inputs, params=params, model=model)
    return spec.run(inputs=inputs, params=params)
