-- data quality summary: what the pipeline rejected and why (lineage via etl_load_log).
SELECT r.rule,
       COUNT(*) AS rows_rejected,
       ROUND(100.0 * COUNT(*) / l.rows_read, 2) AS pct_of_load
FROM dq_rejects r
JOIN etl_load_log l ON l.load_id = r.load_id
GROUP BY r.rule, l.rows_read
ORDER BY rows_rejected DESC;
