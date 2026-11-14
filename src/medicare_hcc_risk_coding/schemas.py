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

HCC_WEIGHTS = pa.schema(
    [
        pa.field("hcc", pa.int32()),
        pa.field("hcc_name", pa.string()),
        pa.field("weight", pa.float64()),
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

# Graph tables, draft 0 (the shared contract for all solutions).
# graph_nodes: node_id is stable across runs and built as "<node_type>:<key>"; key is the
# natural key, with its code system where there is one (for example "rxnorm:11289").
GRAPH_NODES = pa.schema(
    [
        pa.field("node_id", pa.string()),
        pa.field("node_type", pa.string()),
        pa.field("key", pa.string()),
        pa.field("label", pa.string()),
        pa.field("properties", pa.string()),  # JSON text, only for things nobody filters on
    ]
)

# graph_edges: one fact per row. A fact points at another node (target_id) or holds a
# literal (value, with target_id null). Every node an edge names exists in graph_nodes.
# evidence_* ties the fact to the character span of a note; null when unknown.
GRAPH_EDGES = pa.schema(
    [
        pa.field("edge_id", pa.string()),  # stable: hash of source, relationship, target, evidence
        pa.field("source_id", pa.string()),
        pa.field("target_id", pa.string()),
        pa.field("relationship", pa.string()),
        pa.field("value", pa.string()),
        pa.field("valid_from", pa.date32()),
        pa.field("valid_to", pa.date32()),
        pa.field("evidence_document_id", pa.string()),
        pa.field("evidence_start", pa.int32()),
        pa.field("evidence_end", pa.int32()),
        pa.field("confidence", pa.float64()),
        pa.field("properties", pa.string()),
    ]
)
