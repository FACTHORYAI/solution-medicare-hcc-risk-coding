-- How the population distributes over risk-score bands.
SELECT CASE
           WHEN risk_score < 0.5 THEN '<0.5'
           WHEN risk_score < 1.0 THEN '0.5-1.0'
           WHEN risk_score < 1.5 THEN '1.0-1.5'
           WHEN risk_score < 2.0 THEN '1.5-2.0'
           ELSE '2.0+'
       END AS risk_band,
       count(*) AS patients,
       avg(risk_score) AS avg_risk_score
FROM patient_risk
GROUP BY risk_band
ORDER BY CASE risk_band
             WHEN '<0.5' THEN 1
             WHEN '0.5-1.0' THEN 2
             WHEN '1.0-1.5' THEN 3
             WHEN '1.5-2.0' THEN 4
             ELSE 5
         END
