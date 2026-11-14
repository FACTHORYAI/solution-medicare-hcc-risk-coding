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

Suggest HCC codes and risk adjustment factors from clinical notes for Medicare risk adjustment, in Facthory.

## How it will work in Facthory

- You install it into a workspace and get a project: sample data, the analysis, the agent's instructions and starting pages.
- Its results are tables and pages in your workspace, so you can query them, chart them and ask the agent about them, inside your permissions.
- Sample data in this repository is synthetic or openly licensed. No real patient data.

## Not for clinical use

This is software for research and analytics. It is not a medical device and must not be used to diagnose or treat a patient. Results can be wrong; a qualified person reviews them.

## Licence

Apache-2.0. See [LICENSE](LICENSE). "Facthory" and the Facthory logo are trademarks of their owner and are not covered by that licence.

## Jobs

| Job | What it does | Inputs | Outputs |
| --- | --- | --- | --- |
| `prepare_notes` | Keeps the notes that carry both identifiers and text | `notes_raw` | `notes` |
| `extract_icd10` | Codes each disease or problem to ICD-10-CM with its HCC number and assertion status | `notes` | `icd10_codes`, `rejected_icd10` |
| `infer_demographics` | Infers the patient's gender at birth and age from each note | `notes` | `demographics`, `rejected_demographics` |
| `build_patient_profiles` | One profile per patient, keeping only HCCs that risk adjustment counts (not `Family`, `Past` or `Absent`) | `icd10_codes`, `demographics`, `patient_status` | `patient_profiles` |
| `calculate_raf` | The demographic weight, the HCC weight and their summed risk score per patient | `patient_profiles` | `patient_risk` |
| `raf_summary` | Patient counts and average risk score per risk band | `patient_risk` | `raf_bands` |
| `hcc_distribution` | Which HCCs drive the scores, with patient counts and weights | `patient_profiles`, `hcc_weights` | `hcc_distribution` |

The two coding jobs take a `TextModel` (see `src/medicare_hcc_risk_coding/text/interface.py`) as a third argument; Facthory provides model access, and every answer is validated — a code that is not ICD-10-CM, an HCC out of range or an unknown assertion goes to the rejected table with the reason. Named measures live in `metrics/`.

## Data

The sample tables in `data/sample/` are synthetic and openly licensed (CC0-1.0): twelve clinical notes, the administrative status per patient, the HCC weights, and the derived coding, profile and risk tables. See [data/README.md](data/README.md) for one row per file with origin and licence. No real patient data.

## Run it locally

```
uv sync
uv run python -m medicare_hcc_risk_coding extract_icd10 --model-answers tests/recorded_answers.json
uv run python -m medicare_hcc_risk_coding infer_demographics --model-answers tests/recorded_answers.json
uv run python -m medicare_hcc_risk_coding calculate_raf
uv run python -m medicare_hcc_risk_coding raf_summary
uv run pytest
```

`uv run python -m medicare_hcc_risk_coding --help` lists every job; each job has its own `--help`. The two coding jobs additionally take `--model-answers <file>` with a recorded-answers JSON (see `tests/recorded_answers.json`), since they read notes through a model behind `text.interface`; the other jobs run without any model.

The risk adjustment factor is a **simplified** calculation: the published example weights from the original solution's documentation (female 70-74 = 0.346; HCC 18 = 0.625, HCC 19 = 0.124, HCC 35 = 0.279, HCC 40 = 0.423) plus the documented age and sex table. It is not the official CMS-HCC model — disease hierarchies, interactions and the normalization factor are left out — so a score is an illustration of the pipeline, not a payment determination.

