-- The average risk adjustment factor across the population.
SELECT avg(risk_score) AS average_raf
FROM patient_risk
