-- Nodes of the risk adjustment knowledge graph (graph tables, draft 0).
-- node_id = node_type || ':' || key, stable across runs. There are three node types:
--   Patient    key the patient id, label the patient id; properties hold the gender and age
--              the demographics give (JSON text), null when there are none.
--   Condition  key 'icd10:<code>', label the problem's text as extracted (the longest text,
--              the most specific wording, when notes word one code differently). One per code in icd10_codes, whatever
--              the assertion: a family history or a denied problem is a condition too.
--   HCC        key 'hcc:<number>', label the HCC's name from hcc_weights, else 'HCC <number>'
--              for an HCC the simplified model has no weight for. One per HCC number that
--              icd10_codes carries.
-- A node is one row however many notes mention it.
WITH patients AS (
    SELECT patient_id FROM notes
    UNION
    SELECT patient_id FROM icd10_codes
),
hccs AS (
    SELECT DISTINCT hcc FROM icd10_codes WHERE hcc IS NOT NULL
),
mentions AS (
    SELECT 'Patient' AS node_type,
           p.patient_id AS key,
           p.patient_id AS label,
           CASE WHEN d.patient_id IS NOT NULL
                THEN json_object('gender', d.gender, 'age', d.age)::VARCHAR
           END AS properties
    FROM patients AS p
    LEFT JOIN demographics AS d ON d.patient_id = p.patient_id

    UNION ALL

    SELECT 'Condition',
           'icd10:' || trim(icd10_code),
           trim(chunk),
           NULL::VARCHAR
    FROM icd10_codes
    WHERE trim(icd10_code) <> '' AND trim(chunk) <> ''

    UNION ALL

    SELECT 'HCC',
           'hcc:' || CAST(h.hcc AS VARCHAR),
           coalesce(w.hcc_name, 'HCC ' || CAST(h.hcc AS VARCHAR)),
           NULL::VARCHAR
    FROM hccs AS h
    LEFT JOIN hcc_weights AS w ON w.hcc = h.hcc
)
SELECT node_type || ':' || key AS node_id,
       node_type,
       key,
       min_by(label, (-length(label), label)) AS label,
       max(properties) AS properties
FROM mentions
GROUP BY node_type, key
ORDER BY node_id
