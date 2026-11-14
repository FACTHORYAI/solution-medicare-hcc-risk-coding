-- Which HCCs drive the risk scores, and how many patients carry each one.
WITH hccs AS (
    SELECT pp.patient_id, unnest(pp.hcc_list) AS hcc
    FROM patient_profiles AS pp
)
SELECT h.hcc,
       coalesce(max(w.hcc_name), '') AS hcc_name,
       count(DISTINCT h.patient_id) AS patients,
       coalesce(max(w.weight), 0.0) AS weight
FROM hccs AS h
LEFT JOIN hcc_weights AS w
    ON w.hcc = h.hcc
GROUP BY h.hcc
ORDER BY patients DESC, h.hcc
