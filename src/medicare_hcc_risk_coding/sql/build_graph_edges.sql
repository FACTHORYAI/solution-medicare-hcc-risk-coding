-- Edges of the risk adjustment knowledge graph (graph tables, draft 0): one fact per row.
--   Patient -<relationship>-> Condition   one per problem a note names; the relationship
--       says how the note names it:
--         Present      HAS_CONDITION
--         Family       FAMILY_HISTORY_OF
--         Past         PAST_CONDITION
--         Absent       ABSENT_CONDITION
--         Possible     POSSIBLE_CONDITION
--         Hypothetical HYPOTHETICAL_CONDITION
--         Conditional  CONDITIONAL_CONDITION
--       The fact carries the note, the character span of the problem's text and the model's
--       confidence.
--   Condition -MAPS_TO_HCC-> HCC          one per code and HCC number the extraction pairs;
--       derived from the extraction, so it has no evidence and no confidence.
-- An edge is evidence of what a note says, not of what counts: only HAS_CONDITION problems
-- count towards the risk score.
-- The span is the first occurrence of the problem's text in the note (evidence_start inclusive,
-- evidence_end exclusive, 0-based), null when the text is not found. The notes carry no date,
-- so valid_from and valid_to are null.
WITH mentions AS (
    SELECT c.note_id,
           c.patient_id,
           trim(c.chunk) AS chunk,
           'Condition:icd10:' || trim(c.icd10_code) AS condition_id,
           CASE c.assertion
               WHEN 'Present' THEN 'HAS_CONDITION'
               WHEN 'Family' THEN 'FAMILY_HISTORY_OF'
               ELSE upper(c.assertion) || '_CONDITION'
           END AS relationship,
           c.confidence,
           instr(n.text, trim(c.chunk)) - 1 AS found
    FROM icd10_codes AS c
    LEFT JOIN notes AS n ON n.note_id = c.note_id
    WHERE trim(c.icd10_code) <> '' AND trim(c.chunk) <> ''
),
facts AS (
    SELECT 'Patient:' || patient_id AS source_id,
           condition_id AS target_id,
           relationship,
           note_id AS evidence_document_id,
           CASE WHEN found >= 0 THEN found END AS evidence_start,
           CASE WHEN found >= 0 THEN found + length(chunk) END AS evidence_end,
           confidence
    FROM mentions

    UNION ALL

    SELECT DISTINCT
           'Condition:icd10:' || trim(icd10_code),
           'HCC:hcc:' || CAST(hcc AS VARCHAR),
           'MAPS_TO_HCC',
           NULL::VARCHAR,
           NULL::BIGINT,
           NULL::BIGINT,
           NULL::DOUBLE
    FROM icd10_codes
    WHERE hcc IS NOT NULL AND trim(icd10_code) <> ''
),
keyed AS (
    SELECT md5(concat_ws('|', source_id, relationship, coalesce(target_id, ''),
                         '', coalesce(evidence_document_id, ''),
                         coalesce(evidence_start, -1))) AS edge_id,
           *
    FROM facts
)
SELECT edge_id,
       any_value(source_id) AS source_id,
       any_value(target_id) AS target_id,
       any_value(relationship) AS relationship,
       NULL::VARCHAR AS value,
       NULL::DATE AS valid_from,
       NULL::DATE AS valid_to,
       any_value(evidence_document_id) AS evidence_document_id,
       any_value(evidence_start) AS evidence_start,
       any_value(evidence_end) AS evidence_end,
       max(confidence) AS confidence,
       NULL::VARCHAR AS properties
FROM keyed
GROUP BY edge_id
ORDER BY evidence_document_id NULLS LAST, source_id, relationship, target_id, evidence_start
