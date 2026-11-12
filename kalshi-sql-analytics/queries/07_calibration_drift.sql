-- model calibration by model version and market: predicted probability vs realized win rate.
-- a growing gap on the newest version flags drift worth investigating.
SELECT m.asset,
       t.version_id,
       COUNT(*)                                        AS trades,
       ROUND(AVG(t.predicted_prob), 3)                 AS avg_predicted,
       ROUND(AVG(t.won), 3)                            AS realized_win_rate,
       ROUND(AVG(t.predicted_prob) - AVG(t.won), 3)    AS calibration_gap
FROM trades t
JOIN markets m ON m.market_id = t.market_id
GROUP BY m.asset, t.version_id
HAVING COUNT(*) >= 20
ORDER BY ABS(AVG(t.predicted_prob) - AVG(t.won)) DESC
LIMIT 10;
