-- Share of patients with at least one HCC counted towards risk adjustment.
SELECT CAST(SUM(CASE WHEN hcc_count > 0 THEN 1 ELSE 0 END) AS DOUBLE) / count(*) AS patients_with_hcc
FROM patient_risk
