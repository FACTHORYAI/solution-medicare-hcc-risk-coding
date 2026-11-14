# Medicare HCC Risk Coding

Code clinical notes to ICD-10-CM and HCCs, and read the resulting risk adjustment factors.

## Start here

1. Look at the sample tables in `data/sample` (synthetic): `notes` holds 217 clinical notes for 150 patients, and `patient_status` the administrative status per patient.
2. Follow the pipeline: `prepare_notes` → `extract_icd10` (codes and HCCs) and `infer_demographics` (gender and age) → `build_patient_profiles` (only present conditions count) → `calculate_raf` (demographic weight plus HCC weights).
3. Read `graph_nodes` and `graph_edges`: every edge is one fact, how a note names a condition for a patient (present, family history, past, absent, possible, hypothetical or conditional) or which HCC a code maps to. Each patient fact names the note it came from and the text span.
4. Ask a question:

| Question | Job |
| --- | --- |
| Which codes does a note yield? | `extract_icd10` |
| Which HCCs count for a patient? | `build_patient_profiles` |
| What is a patient's risk score, and why? | `calculate_raf` |
| How does the population distribute? | `raf_summary` |
| Which HCCs drive the scores? | `hcc_distribution` |
| How do patients, conditions and HCCs connect? | `build_knowledge_graph` |

Named measures for the average risk score and HCC coverage live in `metrics/`.

## Notes

- The sample data is synthetic; real patient notes never enter this project.
- The two model jobs need a text model behind `medicare_hcc_risk_coding.text.interface`; a recorded stand-in exists for tests and demos. The other jobs run without any model.
- The risk adjustment factor is a simplified calculation from four example HCC weights, not the official CMS-HCC model: it leaves out most HCCs, disease hierarchies, interactions and normalization. An HCC without a weight (such as 85, 96 or 111) counts as 0.
- Results are for research and analytics, not coding-audit or reimbursement decisions.
