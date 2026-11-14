"""One smoke test per job, on the synthetic sample data."""

from __future__ import annotations

from pathlib import Path

import pytest

from medicare_hcc_risk_coding import io, raf
from medicare_hcc_risk_coding.config import Settings
from medicare_hcc_risk_coding.jobs import REGISTRY, call_run
from medicare_hcc_risk_coding.schemas import (
    DEMOGRAPHICS,
    HCC_DISTRIBUTION,
    ICD10_CODES,
    NOTES,
    PATIENT_PROFILES,
    PATIENT_RISK,
    RAF_BANDS,
)
from medicare_hcc_risk_coding.text.recorded import RecordedTextModel, load_answers

REPO = Path(__file__).resolve().parent.parent
SETTINGS = Settings(sample_dir=REPO / "data" / "sample", output_dir=REPO / "output")

SAMPLE_TABLES = (
    "notes_raw",
    "notes",
    "patient_status",
    "hcc_weights",
    "icd10_codes",
    "demographics",
    "patient_profiles",
    "patient_risk",
    "raf_bands",
    "hcc_distribution",
)


@pytest.fixture(scope="module")
def recorded_model() -> RecordedTextModel:
    return RecordedTextModel(load_answers(io.read_json(REPO / "tests" / "recorded_answers.json")))


@pytest.fixture(scope="module")
def tables() -> dict[str, object]:
    return {name: io.read_table(name, SETTINGS) for name in SAMPLE_TABLES}


def run_job(name: str, inputs: dict, model=None):
    spec = REGISTRY[name]
    return call_run(spec, inputs, spec.params_cls(), model)


def test_prepare_notes(tables: dict) -> None:
    outputs = run_job("prepare_notes", {"notes_raw": tables["notes_raw"]})
    assert outputs["notes"].schema.equals(NOTES)
    assert outputs["notes"].equals(tables["notes"].select(NOTES.names))
    assert outputs["notes"].num_rows == 12


def test_extract_icd10(tables: dict, recorded_model: RecordedTextModel) -> None:
    outputs = run_job("extract_icd10", {"notes": tables["notes"]}, recorded_model)
    codes = outputs["icd10_codes"]
    assert codes.schema.equals(ICD10_CODES)
    assert codes.equals(tables["icd10_codes"].select(ICD10_CODES.names))
    assert codes.num_rows == 19
    assert outputs["rejected_icd10"].num_rows == 0
    hccs = {row["hcc"] for row in codes.to_pylist() if row["hcc"] is not None}
    assert hccs == {18, 19, 35, 40}


def test_extract_icd10_rejects_bad_code(tables: dict) -> None:
    class BadCodeModel:
        def complete(self, instructions: str, text: str) -> str:
            return (
                '[{"chunk": "diabetes", "icd10_code": "NOT A CODE", '
                '"hcc": 19, "assertion": "Present", "confidence": 0.9}]'
            )

    outputs = run_job("extract_icd10", {"notes": tables["notes"].slice(0, 1)}, BadCodeModel())
    assert outputs["icd10_codes"].num_rows == 0
    rejected = outputs["rejected_icd10"].to_pylist()
    assert len(rejected) == 1
    assert "not an ICD-10-CM code" in rejected[0]["reason"]


def test_infer_demographics(tables: dict, recorded_model: RecordedTextModel) -> None:
    outputs = run_job("infer_demographics", {"notes": tables["notes"]}, recorded_model)
    demographics = outputs["demographics"]
    assert demographics.schema.equals(DEMOGRAPHICS)
    assert demographics.equals(tables["demographics"].select(DEMOGRAPHICS.names))
    assert demographics.num_rows == 12
    assert outputs["rejected_demographics"].num_rows == 0


def test_build_patient_profiles(tables: dict) -> None:
    outputs = run_job(
        "build_patient_profiles",
        {
            "icd10_codes": tables["icd10_codes"],
            "demographics": tables["demographics"],
            "patient_status": tables["patient_status"],
        },
    )
    profiles = outputs["patient_profiles"]
    assert profiles.schema.equals(PATIENT_PROFILES)
    assert profiles.equals(tables["patient_profiles"].select(PATIENT_PROFILES.names))
    rows = {row["patient_id"]: row for row in profiles.to_pylist()}
    assert rows["p01"]["hcc_list"] == [18, 35]
    # p06's Crohn's disease is a past condition and p05's diabetes is a family history:
    # neither may count towards risk adjustment.
    assert rows["p06"]["hcc_list"] == []
    assert rows["p05"]["hcc_list"] == [18]


def test_calculate_raf(tables: dict) -> None:
    outputs = run_job("calculate_raf", {"patient_profiles": tables["patient_profiles"]})
    risk = outputs["patient_risk"]
    assert risk.schema.equals(PATIENT_RISK)
    assert risk.equals(tables["patient_risk"].select(PATIENT_RISK.names))
    rows = {row["patient_id"]: row for row in risk.to_pylist()}
    # The published example: female 70-74 = 0.346, HCC 18 = 0.625, HCC 35 = 0.279.
    assert rows["p01"]["risk_score"] == pytest.approx(1.250)
    assert rows["p01"]["demographic_weight"] == pytest.approx(0.346)
    assert rows["p11"]["risk_score"] == pytest.approx(1.468)
    assert rows["p04"]["risk_score"] == pytest.approx(0.290)
    for row in rows.values():
        assert row["risk_score"] == pytest.approx(
            row["demographic_weight"] + row["hcc_weight"], abs=1e-6
        )


def test_raf_bands(tables: dict) -> None:
    outputs = run_job("raf_summary", {"patient_risk": tables["patient_risk"]})
    bands = outputs["raf_bands"]
    assert bands.schema.equals(RAF_BANDS)
    assert bands.equals(tables["raf_bands"].select(RAF_BANDS.names))
    assert sum(row["patients"] for row in bands.to_pylist()) == 12
    ordered = [row["risk_band"] for row in bands.to_pylist()]
    assert ordered == ["<0.5", "0.5-1.0", "1.0-1.5"]


def test_hcc_distribution(tables: dict) -> None:
    outputs = run_job(
        "hcc_distribution",
        {"patient_profiles": tables["patient_profiles"], "hcc_weights": tables["hcc_weights"]},
    )
    distribution = outputs["hcc_distribution"]
    assert distribution.schema.equals(HCC_DISTRIBUTION)
    assert distribution.equals(tables["hcc_distribution"].select(HCC_DISTRIBUTION.names))
    rows = {row["hcc"]: row for row in distribution.to_pylist()}
    assert rows[18]["patients"] == 4
    assert rows[18]["weight"] == pytest.approx(0.625)
    assert rows[18]["hcc_name"] == "Diabetes with chronic complications"


def test_raf_weights_are_documented() -> None:
    assert raf.risk_adjustment_factor(72, "female", [18]) == pytest.approx(0.971)
    assert raf.risk_adjustment_factor(72, "female", [18, 35]) == pytest.approx(1.250)
    assert raf.hcc_weight([999]) == 0.0
    with pytest.raises(ValueError, match="gender"):
        raf.demographic_weight(70, "unknown")
