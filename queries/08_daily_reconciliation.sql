-- reconcile warehouse p&l against the exchange statement; list days that disagree.
WITH wh AS (SELECT date(opened_at) AS d, ROUND(SUM(pnl), 2) AS warehouse_pnl FROM trades GROUP BY d)
SELECT l.ledger_date,
       wh.warehouse_pnl,
       l.reported_pnl,
       ROUND(l.reported_pnl - wh.warehouse_pnl, 2) AS difference
FROM daily_ledger l
LEFT JOIN wh ON wh.d = l.ledger_date
WHERE wh.warehouse_pnl IS NULL OR ABS(l.reported_pnl - wh.warehouse_pnl) > 0.01
ORDER BY l.ledger_date;
