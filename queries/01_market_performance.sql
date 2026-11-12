-- per-market scorecard: trades, win rate, p&l, and risk-adjusted view (join + aggregates).
SELECT m.asset,
       COUNT(*)                                  AS trades,
       ROUND(AVG(t.won) * 100, 1)                AS win_rate_pct,
       ROUND(SUM(t.pnl), 2)                      AS total_pnl,
       ROUND(AVG(t.pnl), 3)                      AS avg_pnl_per_trade,
       ROUND(SQRT(AVG(t.pnl * t.pnl) - AVG(t.pnl) * AVG(t.pnl)), 3) AS pnl_stdev,
       ROUND(AVG(t.pnl) / NULLIF(SQRT(AVG(t.pnl * t.pnl) - AVG(t.pnl) * AVG(t.pnl)), 0), 3) AS per_trade_sharpe
FROM trades t
JOIN markets m ON m.market_id = t.market_id
GROUP BY m.asset
ORDER BY total_pnl DESC;
