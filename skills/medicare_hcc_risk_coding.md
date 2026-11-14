# Medicare HCC Risk Coding — agent instructions

You help members code clinical notes to ICD-10-CM and HCCs, and read the resulting risk adjustment factors.

## What the project provides

- Sample tables in `data/sample` (synthetic): `notes_raw` and `notes` (clinical notes), `patient_status` (administrative status), `hcc_weights` (the HCC weights), and the derived `icd10_codes`, `demographics`, `patient_profiles`, `patient_risk`, `raf_bands` and `hcc_distribution`.
- Jobs under `src/medicare_hcc_risk_coding/jobs`: note preparation, ICD-10/HCC coding and demographic inference (both behind a `TextModel`), the patient profile and risk calculation, and two summaries.

## How to answer a question

1. Classify what the member asks: which codes a note yields (`icd10_codes`), which HCCs count for a patient (`patient_profiles`), what a patient's risk score is and why (`patient_risk`), how the population distributes (`raf_bands`), or which HCCs drive the scores (`hcc_distribution`).
2. Check the parameters with `uv run python -m medicare_hcc_risk_coding <job> --help`; the jobs are parameter-light, so most answers come straight from the tables.
3. Read `patient_profiles.hcc_list` carefully: risk adjustment counts only conditions that are present — `Family`, `Past` and `Absent` findings are excluded before the risk score is calculated.
4. Report results as a table with the counts behind them, and show the components (`demographic_weight` and `hcc_weight`) when quoting a risk score.

## Data care

- The sample data is synthetic; real patient notes never enter this project.
- The risk adjustment factor is a **simplified** calculation from published example weights, not the official CMS-HCC model. Say so whenever a score is quoted, and never present it as a payment determination.
- Results are for research and analytics, not clinical, coding-audit or reimbursement decisions.
