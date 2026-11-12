-- monthly p&l per market with a running cumulative total (window function over a cte).
WITH monthly AS (
    SELECT m.asset,
           strftime('%Y-%m', t.opened_at) AS month,
           COUNT(*)                       AS trades,
           ROUND(SUM(t.pnl), 2)           AS pnl
    FROM trades t JOIN markets m ON m.market_id = t.market_id
    GROUP BY m.asset, month
)
SELECT asset, month, trades, pnl,
       ROUND(SUM(pnl) OVER (PARTITION BY asset ORDER BY month), 2) AS cumulative_pnl
FROM monthly
ORDER BY asset, month;
