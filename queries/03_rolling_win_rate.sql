-- rolling 50-trade win rate per market; latest value per market flags recent decay.
WITH rolled AS (
    SELECT t.market_id, t.opened_at, t.won,
           ROW_NUMBER() OVER w AS n,
           AVG(t.won) OVER (PARTITION BY t.market_id ORDER BY t.opened_at
                            ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) AS rolling_win_rate
    FROM trades t
    WINDOW w AS (PARTITION BY t.market_id ORDER BY t.opened_at)
),
latest AS (
    SELECT market_id, rolling_win_rate, ROW_NUMBER() OVER (PARTITION BY market_id ORDER BY opened_at DESC) AS rk
    FROM rolled WHERE n >= 50
),
overall AS (SELECT market_id, AVG(won) AS all_time FROM trades GROUP BY market_id)
SELECT m.asset,
       ROUND(o.all_time * 100, 1)           AS all_time_win_pct,
       ROUND(l.rolling_win_rate * 100, 1)   AS last_50_win_pct,
       ROUND((l.rolling_win_rate - o.all_time) * 100, 1) AS gap_pts
FROM latest l
JOIN overall o ON o.market_id = l.market_id
JOIN markets m ON m.market_id = l.market_id
WHERE l.rk = 1
ORDER BY gap_pts;
