-- portfolio equity curve and max drawdown (running max via window function).
WITH daily AS (
    SELECT date(opened_at) AS d, SUM(pnl) AS pnl FROM trades GROUP BY d
),
curve AS (
    SELECT d, pnl, SUM(pnl) OVER (ORDER BY d) AS equity FROM daily
),
dd AS (
    SELECT d, equity,
           equity - MAX(0, MAX(equity) OVER (ORDER BY d)) AS drawdown
    FROM curve
)
SELECT ROUND(MAX(equity), 2)  AS peak_equity,
       ROUND((SELECT equity FROM dd ORDER BY d DESC LIMIT 1), 2) AS final_equity,
       ROUND(MIN(drawdown), 2) AS max_drawdown,
       (SELECT d FROM dd ORDER BY drawdown LIMIT 1) AS worst_day
FROM dd;
