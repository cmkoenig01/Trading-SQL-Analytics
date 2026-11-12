-- time-of-day pattern: does performance vary by hour? (grouped case bucket)
SELECT CASE WHEN CAST(strftime('%H', opened_at) AS INTEGER) < 6  THEN '00-05'
            WHEN CAST(strftime('%H', opened_at) AS INTEGER) < 12 THEN '06-11'
            WHEN CAST(strftime('%H', opened_at) AS INTEGER) < 18 THEN '12-17'
            ELSE '18-23' END AS hour_block,
       COUNT(*) AS trades,
       ROUND(AVG(won) * 100, 1) AS win_rate_pct,
       ROUND(SUM(pnl), 2) AS total_pnl
FROM trades
GROUP BY hour_block
ORDER BY hour_block;
