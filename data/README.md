# Sample data

Every file below is synthetic, generated for this repository from hand-written clinical
notes; no real patient data. Licence: CC0-1.0. The folder is a few kilobytes in total,
far under the 5 MB per file and 20 MB per folder limits.

| File | What it is | Where it came from | Licence | Synthetic |
| --- | --- | --- | --- | --- |
| `notes_raw.parquet` | 12 clinical notes: note_id, patient_id, text | Hand-written for this repository | CC0-1.0 | yes |
| `notes.parquet` | The notes that carry both identifiers and text | `prepare_notes` | CC0-1.0 | yes |
| `patient_status.parquet` | Administrative status per patient: eligibility, orec, medicaid | Hand-written for this repository | CC0-1.0 | yes |
| `hcc_weights.parquet` | The HCC weights used by the simplified risk model: hcc, name, weight | From `raf.py` | CC0-1.0 | yes |
| `icd10_codes.parquet` | Coded problems per note with HCC and assertion status | `extract_icd10` | CC0-1.0 | yes |
| `demographics.parquet` | Inferred gender at birth and age per patient | `infer_demographics` | CC0-1.0 | yes |
| `patient_profiles.parquet` | Demographics, administrative status and the counted HCCs per patient | `build_patient_profiles` | CC0-1.0 | yes |
| `patient_risk.parquet` | Demographic weight, HCC weight and risk score per patient | `calculate_raf` | CC0-1.0 | yes |
| `raf_bands.parquet` | Patient counts and average risk score per risk band | `raf_summary` | CC0-1.0 | yes |
| `hcc_distribution.parquet` | Patient counts and weights per HCC | `hcc_distribution` | CC0-1.0 | yes |

The notes cover the four HCCs whose weights the solution's README publishes: HCC 18
(diabetes with chronic complications, 0.625), HCC 19 (diabetes without complication,
0.124), HCC 35 (inflammatory bowel disease, 0.279) and HCC 40 (rheumatoid arthritis,
0.423). Two notes deliberately carry conditions that risk adjustment must **not** count:
a past Crohn's disease and a family history of diabetes.

The risk adjustment factor is a **simplified** calculation: the published example weights
above plus a documented age/sex table (female 70-74 = 0.346, from the README example).
It is not the official CMS-HCC model, which adds disease hierarchies, interactions and a
normalization factor; a workspace plugs the official model in behind the same job.

The original solution's dataset was **not** republished: it is a set of transcribed
medical reports from mtsamples.com, whose redistribution licence was not verified. This
repository ships its own synthetic notes instead.
