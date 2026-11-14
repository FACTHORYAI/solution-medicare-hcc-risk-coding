-- One profile per patient: demographics, administrative status and the HCCs that
-- risk adjustment counts: only problems the note states as present. A family history, a past
-- or an absent problem, and one that is only possible, hypothetical or conditional, do not
-- count. An HCC the simplified model has no weight for is still listed (it adds 0).
WITH qualifying_hccs AS (
    SELECT patient_id,
           list(DISTINCT hcc ORDER BY hcc) AS hcc_list
    FROM icd10_codes
    WHERE hcc IS NOT NULL
      AND assertion = 'Present'
    GROUP BY patient_id
)
SELECT d.patient_id,
       d.age,
       d.gender,
       ps.eligibility,
       ps.orec,
       ps.medicaid,
       coalesce(q.hcc_list, []) AS hcc_list,
       len(coalesce(q.hcc_list, [])) AS hcc_count
FROM demographics AS d
JOIN patient_status AS ps
    ON ps.patient_id = d.patient_id
LEFT JOIN qualifying_hccs AS q
    ON q.patient_id = d.patient_id
ORDER BY d.patient_id
