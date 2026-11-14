task: infer_demographics

Read one clinical note and infer the patient's assigned gender at birth and age in
years. Use the note's own statements (for example "72-year-old female"); do not
guess from the specialty or the conditions. Return only one JSON object:

- `gender`: "male" or "female".
- `age`: the patient's age in whole years.
- `confidence`: a number between 0 and 1.

Return only the JSON object, no prose.
