-- One profile per patient: demographics, administrative status and the HCCs that
-- risk adjustment counts (present conditions only, not family or past history).
WITH qualifying_hccs AS (
    SELECT patient_id,
           list(DISTINCT hcc ORDER BY hcc) AS hcc_list
    FROM icd10_codes
    WHERE hcc IS NOT NULL
      AND assertion NOT IN ('Family', 'Past', 'Absent')
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
