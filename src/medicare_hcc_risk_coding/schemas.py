"""PyArrow schemas for every table the jobs read or write."""

import pyarrow as pa

NOTES_RAW = pa.schema(
    [
        pa.field("note_id", pa.string()),
        pa.field("patient_id", pa.string()),
        pa.field("text", pa.string()),
    ]
)

NOTES = pa.schema(
    [
        pa.field("note_id", pa.string()),
        pa.field("patient_id", pa.string()),
        pa.field("text", pa.string()),
    ]
)

PATIENT_STATUS = pa.schema(
    [
        pa.field("patient_id", pa.string()),
        pa.field("eligibility", pa.string()),
        pa.field("orec", pa.string()),
        pa.field("medicaid", pa.bool_()),
    ]
)

ICD10_CODES = pa.schema(
    [
        pa.field("note_id", pa.string()),
        pa.field("patient_id", pa.string()),
        pa.field("chunk", pa.string()),
        pa.field("icd10_code", pa.string()),
        pa.field("hcc", pa.int32()),
        pa.field("assertion", pa.string()),
        pa.field("confidence", pa.float64()),
    ]
)

REJECTED = pa.schema(
    [
        pa.field("note_id", pa.string()),
        pa.field("reason", pa.string()),
        pa.field("model_answer", pa.string()),
    ]
)

DEMOGRAPHICS = pa.schema(
    [
        pa.field("patient_id", pa.string()),
        pa.field("gender", pa.string()),
        pa.field("age", pa.int32()),
        pa.field("confidence", pa.float64()),
    ]
)

PATIENT_PROFILES = pa.schema(
    [
        pa.field("patient_id", pa.string()),
        pa.field("age", pa.int32()),
        pa.field("gender", pa.string()),
        pa.field("eligibility", pa.string()),
        pa.field("orec", pa.string()),
        pa.field("medicaid", pa.bool_()),
        pa.field("hcc_list", pa.list_(pa.int32())),
        pa.field("hcc_count", pa.int32()),
    ]
)

PATIENT_RISK = pa.schema(
    [
        pa.field("patient_id", pa.string()),
        pa.field("age", pa.int32()),
        pa.field("gender", pa.string()),
        pa.field("demographic_weight", pa.float64()),
        pa.field("hcc_weight", pa.float64()),
        pa.field("risk_score", pa.float64()),
        pa.field("hcc_count", pa.int32()),
    ]
)

RAF_BANDS = pa.schema(
    [
        pa.field("risk_band", pa.string()),
        pa.field("patients", pa.int64()),
        pa.field("avg_risk_score", pa.float64()),
    ]
)

HCC_DISTRIBUTION = pa.schema(
    [
        pa.field("hcc", pa.int32()),
        pa.field("hcc_name", pa.string()),
        pa.field("patients", pa.int64()),
        pa.field("weight", pa.float64()),
    ]
)
