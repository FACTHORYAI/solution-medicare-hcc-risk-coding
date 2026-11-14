# Medicare HCC Risk Coding

Code clinical notes to ICD-10-CM and HCCs, and read the resulting risk adjustment factors.

## Start here

1. Look at the sample tables in `data/sample` (synthetic): twelve clinical notes and the administrative status per patient.
2. Follow the pipeline: `prepare_notes` → `extract_icd10` (codes and HCCs) and `infer_demographics` (gender and age) → `build_patient_profiles` (only present conditions count) → `calculate_raf` (demographic weight plus HCC weights).
3. Ask a question:

| Question | Job |
| --- | --- |
| Which codes does a note yield? | `extract_icd10` |
| Which HCCs count for a patient? | `build_patient_profiles` |
| What is a patient's risk score, and why? | `calculate_raf` |
| How does the population distribute? | `raf_summary` |
| Which HCCs drive the scores? | `hcc_distribution` |

Named measures for the average risk score and HCC coverage live in `metrics/`.

## Notes

- The sample data is synthetic; real patient notes never enter this project.
- The risk adjustment factor is a simplified calculation from published example weights, not the official CMS-HCC model: it leaves out disease hierarchies, interactions and normalization.
- Results are for research and analytics, not coding-audit or reimbursement decisions.
