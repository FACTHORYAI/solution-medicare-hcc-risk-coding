<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FACTHORYAI/.github/main/brand/word-mark-only-mono.svg">
    <img alt="Facthory" src="https://raw.githubusercontent.com/FACTHORYAI/.github/main/brand/word-mark-only.svg" width="360">
  </picture>
</p>

# Medicare HCC Risk Coding

Suggest HCC codes and risk adjustment factors from clinical notes for Medicare risk adjustment, in Facthory.

![Licence: Apache-2.0](https://img.shields.io/badge/licence-Apache--2.0-blue) ![Runs on Facthory](https://img.shields.io/badge/runs%20on-Facthory-1f6feb) ![Status: install coming](https://img.shields.io/badge/status-install%20coming-lightgrey)

> **Install coming.** This is a Facthory solution: its data, analysis code, agent skill and starting pages load into a Facthory workspace as a ready project. Installing from this page is not available yet; this repository is being prepared for it.

## What it does

Medicare HCC Risk Coding reads free-text clinical notes and turns them into a risk adjustment score per patient, as tables. A note such as "The patient is a 72-year-old female with type 2 diabetes mellitus with diabetic mononeuropathy and Crohn's disease of the small intestine without complications" gives two coded problems, each with an HCC number, and the patient's age and sex. The score is a simplified illustration of Medicare risk adjustment, not the official CMS-HCC model.

1. **Prepare.** `prepare_notes` keeps the notes that carry a note identifier, a patient identifier and text, and drops the rest.
2. **Read the notes.** Two jobs read each note through a text model, which answers in JSON that is validated before it becomes rows. Answers that fail validation go to `rejected_*` tables with the reason.
   - `extract_icd10`: every disease or problem the note names, coded to ICD-10-CM, with the HCC number the code maps to (or none), an assertion status (Present, Absent, Family, Past, Hypothetical, Possible or Conditional) and a confidence;
   - `infer_demographics`: the patient's gender at birth and age, read from the note's own words.
3. **Profile.** `build_patient_profiles` joins the demographics, the administrative status per patient and the HCCs, and keeps only HCCs from problems the note states as present. A family history, a past or absent problem, and one that is only possible, hypothetical or conditional, do not count.
4. **Score.** `calculate_raf` adds the demographic weight (age band and sex) and the weight of each counted HCC. The model has weights for four HCCs only; any other HCC counts as 0.
5. **Summarise.** `raf_summary` counts patients and averages the score per risk band, and `hcc_distribution` counts the patients that carry each HCC.
6. **Build the graph.** `build_knowledge_graph` turns the extracted rows into two tables, `graph_nodes` and `graph_edges`: patients, conditions and HCCs, and how each note names each condition. Every edge records the note and text span it came from.

Step 2 needs a text model. Steps 1 and 3 to 6 are plain SQL on DuckDB or plain Python and need none. A score is for a qualified person to review, not a payment.

## How it works in Facthory

- Jobs read tables and write tables. They draw no screens and own no storage; querying, charting, joining with your own data, permissions and audit belong to the platform.
- The knowledge graph is two tables, not a graph database. See "Graph tables" below. Any graph view can be drawn from them.
- The agent skill in `skills/` and the starter page in `pages/` describe how to work with the tables and the jobs.
- Sample data in this repository is synthetic. No real patient data.

## What the result could look like

![Mock-up of a Facthory report page titled "Risk adjustment results", marked "Sample data": four figures (patients scored, average risk score, patients with a counted HCC, problems not counted), a table of the patients with the highest risk scores with age, gender, counted HCCs and score, a bar chart of the patients per HCC, and a bar chart of the problems by assertion status.](docs/images/risk-adjustment-results-mockup.png)

A design illustration of a report built from this solution's tables, drawn from this repository's own sample data (invented notes). It is a mock-up and not a screenshot of a released feature; the score is a simplified illustration and not a payment determination.

## The design in one picture

This diagram shows the design. It is a concept, not a map of finished platform features.

![Flow diagram "From clinical notes to RAF risk scores": source data (clinical notes, PDF lab reports, medical images; protected health data) is ingested as raw unstructured clinical notes; the Facthory NLP engine identifies undiagnosed conditions and codes them into coded patient records (for example HCC and ICD-10); the updated RAF risk score is then calculated for each beneficiary and shown in a medical report. Each stage is recorded in the data catalog.](docs/images/clinical-notes-to-raf-scores.png)

This repository covers clinical notes only: `extract_icd10` codes each problem to ICD-10-CM with its HCC number and assertion status through a text model, and `calculate_raf` computes a simplified risk adjustment factor per patient. PDF lab reports and medical images are not read, and the score is a simplified illustration, not the official CMS-HCC model.

## Jobs

| Job | What it does | Inputs | Outputs |
| --- | --- | --- | --- |
| `prepare_notes` | Keeps the notes that carry both identifiers and text | `notes_raw` | `notes` |
| `extract_icd10` | Codes each disease or problem to ICD-10-CM with its HCC number and assertion status | `notes` | `icd10_codes`, `rejected_icd10` |
| `infer_demographics` | Infers the patient's gender at birth and age from each note | `notes` | `demographics`, `rejected_demographics` |
| `build_patient_profiles` | One profile per patient, keeping only HCCs from problems stated as present (not `Family`, `Past`, `Absent`, `Possible`, `Hypothetical` or `Conditional`) | `icd10_codes`, `demographics`, `patient_status` | `patient_profiles` |
| `calculate_raf` | The demographic weight, the HCC weight and their summed risk score per patient | `patient_profiles` | `patient_risk` |
| `raf_summary` | Patient counts and average risk score per risk band | `patient_risk` | `raf_bands` |
| `hcc_distribution` | Which HCCs drive the scores, with patient counts and weights | `patient_profiles`, `hcc_weights` | `hcc_distribution` |
| `build_knowledge_graph` | Builds the knowledge graph of patients, conditions and HCCs as node and edge tables | `notes`, `icd10_codes`, `demographics`, `hcc_weights` | `graph_nodes`, `graph_edges` |

The two model jobs take a `TextModel` (see `src/medicare_hcc_risk_coding/text/interface.py`) as a third argument; Facthory provides model access, and every answer is validated: a code that is not ICD-10-CM, an HCC out of range or an unknown assertion goes to the rejected table with the reason. The table of notes and every table extracted from it have a `note_id` column that names the note; the graph's `evidence_document_id` holds the same value. Named measures live in `metrics/`.

### Graph tables

The graph follows the "graph tables, draft 0" shape that all Facthory solutions share.

- `graph_nodes`: `node_id` (stable across runs, `<node_type>:<key>`), `node_type`, `key` (the natural key, with its code system where there is one, for example `icd10:E11.9`), `label`, `properties` (JSON text).
- `graph_edges`: `edge_id` (stable hash of source, relationship, target or value, and evidence), `source_id`, `target_id` (null when the fact is a literal), `relationship`, `value` (the literal, else null), `valid_from` and `valid_to` (dates the fact held; `valid_to` is null when unknown), `evidence_document_id`, `evidence_start`, `evidence_end` (character offsets in that note; null when the text was not found), `confidence` (null when not scored), `properties`.

Every node an edge names exists in `graph_nodes`, and a fact has either `target_id` or `value`, never both. In this repository the nodes are:

- `Patient`, one per patient (`Patient:p001`), labelled with the patient id; `properties` holds the gender and age as JSON (`{"gender": "female", "age": 72}`), and is null for a patient without demographics.
- `Condition`, one per ICD-10-CM code in `icd10_codes` (`Condition:icd10:E11.9`), labelled with the longest wording of it in the notes. A family history (`Z83.3`) or a denied problem is a condition too.
- `HCC`, one per HCC number in `icd10_codes` (`HCC:hcc:18`), labelled with the name from `hcc_weights`, or `HCC 85` for a number the simplified model has no weight for.

The facts are:

- `Patient -<relationship>-> Condition` for every problem a note names, where the relationship says how the note names it: `HAS_CONDITION` (Present), `FAMILY_HISTORY_OF` (Family), `PAST_CONDITION` (Past), `ABSENT_CONDITION` (Absent), `POSSIBLE_CONDITION` (Possible), `HYPOTHETICAL_CONDITION` (Hypothetical) or `CONDITIONAL_CONDITION` (Conditional). The edge carries the note, the span of the problem's text and the model's confidence.
- `Condition -MAPS_TO_HCC-> HCC` for every code and HCC number the extraction pairs. It is derived from the extraction, so it has no evidence and no confidence.

An edge is evidence of what a note says, not of what counts: only `HAS_CONDITION` problems count towards the score. A node is shared by all notes; `evidence_document_id` (a `note_id` of `notes`) says which note a fact belongs to. The evidence span is the first occurrence of the problem's text in that note (`evidence_start` inclusive, `evidence_end` exclusive, 0-based). The notes carry no date, so `valid_from` and `valid_to` are always null.

## Data

The sample tables in `data/sample/` are synthetic and CC0-1.0: `notes_raw`, `notes`, `patient_status`, `hcc_weights`, `icd10_codes`, `demographics`, `patient_profiles`, `patient_risk`, `raf_bands`, `hcc_distribution`, `graph_nodes` and `graph_edges`. They hold 217 invented notes for 150 invented patients (222 raw rows, five of which lack an id or text and are dropped), 646 coded problems, 184 graph nodes and 663 edges, made by `data/generate_sample.py`. The notes name problems that map to HCC 18, 19, 35 and 40, problems with no HCC, and a few that map to HCC numbers the simplified model has no weight for (85, 96 and 111, in the CMS-HCC version 24 numbering). See [data/README.md](data/README.md) for origin and licence per file. No real patient data.

## Run it locally

```
uv sync
uv run python -m medicare_hcc_risk_coding extract_icd10 --model-answers tests/recorded_answers.json
uv run python -m medicare_hcc_risk_coding infer_demographics --model-answers tests/recorded_answers.json
uv run python -m medicare_hcc_risk_coding calculate_raf
uv run python -m medicare_hcc_risk_coding raf_summary
uv run python -m medicare_hcc_risk_coding build_knowledge_graph
uv run pytest
```

`uv run python -m medicare_hcc_risk_coding --help` lists every job; each job has its own `--help`. The two model jobs additionally take `--model-answers <file>` with a recorded-answers JSON (see `tests/recorded_answers.json`), since they read notes through a model behind `text.interface`; the other jobs run without any model. Verified on the synthetic sample data only, not yet in a Facthory workspace.

The risk adjustment factor is a **simplified** calculation: four example HCC weights (HCC 18 = 0.625, HCC 19 = 0.124, HCC 35 = 0.279, HCC 40 = 0.423) plus an age and sex table whose female 70-74 cell (0.346) is the one published value and whose other cells are illustrative. It is not the official CMS-HCC model, so a score is an illustration of the pipeline, not a payment determination.

## Open points

- **No clinical text model ships.** `extract_icd10` and `infer_demographics` run through the `TextModel` interface. The only implementation is `text/recorded.py`, which replays recorded answers for the sample notes. A model must be plugged in behind `text/interface.py` before new notes can be processed. A rules-based stand-in for clinical extraction is deliberately not provided.
- **Each note is read twice.** The two model jobs each send the note to the model with their own prompt. Facthory will replace them with one combined extraction call per document: one prompt and one JSON schema that returns the problems with their codes and assertions, and the demographics, together.
- **Codes are resolved inside the extraction prompt.** There is no vocabulary lookup. The ICD-10-CM codes in the sample are real, public codes that were written from memory and have not been checked against the current release of the code set. The HCC numbers follow the CMS-HCC version 24 numbering as the sample's author knows it, and are not verified either.
- **The risk model is the simplified one.** It has weights for four HCCs only (18, 19, 35 and 40). The notes of the sample also name problems that map to other HCC numbers (85, 96 and 111): they are a patient's counted HCCs, they show in `hcc_distribution`, and they weigh 0 because they are not in the model's table. The official CMS-HCC model has many more HCCs, disease hierarchies, interactions and a normalisation factor. Its mapping tables are public and are not included here, and no CMS table is copied.
- **The age and sex weights are illustrative**, apart from the one published cell (female, 70 to 74: 0.346). Ages below 60 use the weights of the 60 to 64 band.
- **Only a problem stated as present counts.** A family history, a past or absent problem, and a possible, hypothetical or conditional one never reach the score. The real coding rules (the encounter, the provider, the year of service) are not modelled: the notes carry no date.
- **A patient with two notes** gets the age and gender of the note the model is more sure of, and the union of the HCCs of both notes. The notes are not ordered in time.
- **Evidence spans are found by text search**, not reported by the model: `evidence_start` and `evidence_end` mark the first occurrence of the problem's text in the note, and are null when it is not found (for example a word the model normalised). `valid_from` and `valid_to` are always null.
- **The graph keeps every mention.** Family histories, denied and possible problems are conditions with their own relationship; filter on `HAS_CONDITION` to see what counts.
- **No graph algorithms** are included. Paths, similarity and communities would be added as jobs over the edge tables.
- **Installing into Facthory is not available yet.** The code is verified on the sample data on a laptop only.
- **The sample is invented and small.** It is generated from templates, so its notes are cleaner than real clinical text, and it shows the shape of the tables, not realistic volumes or accuracy. The extracted rows are exact by construction, not model output.
- **The Dockerfile has not been built or verified.**
- **DuckDB 2.x only.** The code uses the DuckDB 2.0 Arrow API (`to_arrow_table`).
- No orchestrator or DAG files: Facthory, or a scheduler, calls the jobs.

## Not for clinical use

This is software for research and analytics. It is not a medical device and must not be used to diagnose or treat a patient. Results can be wrong; a qualified person reviews them.

## Disclaimers

Bandpey GmbH (“Facthory”) does not dispense medical, diagnosis, or treatment advice. This Solution (“tool”) is for informational purposes only and may not be used as a substitute for professional medical advice, treatment, or diagnosis. This tool may not be used within Facthory to process Protected Health Information (“PHI”) as defined in the Health Insurance Portability and Accountability Act of 1996, unless you have executed with Facthory a contract that allows for processing PHI, an accompanying Business Associate Agreement (BAA), and are running this tool within a HIPAA Account.

## Licence

Apache-2.0. See [LICENSE](LICENSE). "Facthory" and the Facthory logo are trademarks of their owner and are not covered by that licence. This includes the logo shown in the images under `docs/images/`.
