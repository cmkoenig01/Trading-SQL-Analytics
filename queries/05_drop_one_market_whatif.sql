-- what-if: re-run the portfolio with each market excluded; compare total p&l and max drawdown.
WITH daily AS (
    SELECT market_id, date(opened_at) AS d, SUM(pnl) AS pnl FROM trades GROUP BY market_id, d
),
scenarios AS (
    SELECT 0 AS excluded UNION ALL SELECT market_id FROM markets
),
scen_daily AS (
    SELECT s.excluded, d.d, SUM(d.pnl) AS pnl
    FROM scenarios s JOIN daily d ON d.market_id <> s.excluded
    GROUP BY s.excluded, d.d
),
curve AS (
    SELECT excluded, d, pnl, SUM(pnl) OVER (PARTITION BY excluded ORDER BY d) AS equity FROM scen_daily
),
dd AS (
    SELECT excluded, equity,
           equity - MAX(0, MAX(equity) OVER (PARTITION BY excluded ORDER BY d)) AS drawdown
    FROM curve
),
summary AS (
    SELECT excluded, ROUND(MIN(drawdown), 2) AS max_drawdown FROM dd GROUP BY excluded
),
totals AS (
    SELECT excluded, ROUND(SUM(pnl), 2) AS total_pnl FROM scen_daily GROUP BY excluded
)
SELECT COALESCE(m.asset, 'NONE (baseline)') AS excluded_market,
       t.total_pnl,
       s.max_drawdown
FROM summary s
JOIN totals t ON t.excluded = s.excluded
LEFT JOIN markets m ON m.market_id = s.excluded
ORDER BY s.max_drawdown DESC;
