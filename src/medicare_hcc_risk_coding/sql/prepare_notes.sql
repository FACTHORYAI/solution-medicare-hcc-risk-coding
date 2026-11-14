-- The notes that carry both identifiers and text.
SELECT note_id, patient_id, text
FROM notes_raw
WHERE note_id IS NOT NULL AND note_id <> ''
  AND patient_id IS NOT NULL AND patient_id <> ''
  AND text IS NOT NULL AND text <> ''
ORDER BY note_id
