# Medicare HCC Risk Coding — agent instructions

You help members code clinical notes to ICD-10-CM and HCCs, and read the resulting risk adjustment factors.

## What the project provides

- Sample tables in `data/sample` (synthetic): `notes_raw` and `notes` (217 invented clinical notes for 150 patients), `patient_status` (administrative status), `hcc_weights` (the HCC weights), the extracted `icd10_codes` and `demographics`, the derived `patient_profiles`, `patient_risk`, `raf_bands` and `hcc_distribution`, and the knowledge graph as `graph_nodes` and `graph_edges`. Every row of the extracted tables names its note in `note_id`.
- Jobs under `src/medicare_hcc_risk_coding/jobs`: note preparation, ICD-10/HCC coding and demographic inference (both behind a `TextModel`), the patient profile and risk calculation, two summaries, and one job that turns the extracted rows into graph node and edge tables.

## How to answer a question

1. Classify what the member asks: which codes a note yields (`icd10_codes`), which HCCs count for a patient (`patient_profiles`), what a patient's risk score is and why (`patient_risk`), how the population distributes (`raf_bands`), which HCCs drive the scores (`hcc_distribution`), or how the patients, conditions and HCCs of the notes connect (`build_knowledge_graph`).
2. Check the parameters with `uv run python -m medicare_hcc_risk_coding <job> --help`; the jobs are parameter-light, so most answers come straight from the tables.
3. Read `patient_profiles.hcc_list` carefully: risk adjustment counts only problems the note states as present. `Family`, `Past`, `Absent`, `Possible`, `Hypothetical` and `Conditional` findings are excluded before the risk score is calculated. An HCC the simplified model has no weight for (for example 85, 96 or 111 in the sample) is listed and weighs 0.
4. `graph_nodes` holds one row per `Patient`, `Condition` or `HCC` node (`node_id`, `node_type`, `key`, `label`); `graph_edges` holds one fact per row: `Patient -HAS_CONDITION | FAMILY_HISTORY_OF | PAST_CONDITION | ABSENT_CONDITION | POSSIBLE_CONDITION | HYPOTHETICAL_CONDITION | CONDITIONAL_CONDITION-> Condition` and `Condition -MAPS_TO_HCC-> HCC`. Join edges to nodes on `source_id` / `target_id`. Each patient edge names the note it came from (`evidence_document_id`, a `note_id` of `notes`) and the character span (`evidence_start`, `evidence_end`) of the problem's text; an edge records what a note says, and only `HAS_CONDITION` problems count. Quote the evidence when you explain a result.
5. Report results as a table with the counts behind them, and show the components (`demographic_weight` and `hcc_weight`) when quoting a risk score.

## Data care

- The sample data is synthetic; real patient notes never enter this project.
- The two model jobs need a text model behind `text.interface`; the repository ships a recorded stand-in for tests and demos. The other jobs run without any model.
- The risk adjustment factor is a **simplified** calculation from four example HCC weights and an illustrative age and sex table, not the official CMS-HCC model. Say so whenever a score is quoted, and never present it as a payment determination.
- The sample's ICD-10-CM codes are real but were written from memory and are not checked against the current release; its HCC numbers follow the CMS-HCC version 24 numbering as the author knows it.
- Results are for research and analytics, not clinical, coding-audit or reimbursement decisions.
