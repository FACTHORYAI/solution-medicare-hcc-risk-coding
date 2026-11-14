task: extract_icd10

Extract the diseases and problems from one clinical note, code each one to
ICD-10-CM, and state whether the code maps to a Medicare HCC. Return only a JSON
array, one object per problem, with these keys:

- `chunk`: the problem text as written in the note.
- `icd10_code`: the most specific billable ICD-10-CM code for the problem.
- `hcc`: the Medicare HCC number the code maps to, or null when it maps to none.
- `assertion`: one of Present, Absent, Family, Past, Hypothetical, Possible,
  Conditional. Use "Family" for a relative's condition and "Past" for a resolved
  one; risk adjustment only counts conditions that are present.
- `confidence`: a number between 0 and 1.

Return [] when the note names no disease or problem. Return only the JSON array.
