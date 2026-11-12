-- execution quality: fill rate and average slippage (in cents) per market.
SELECT m.asset,
       COUNT(*)                                                   AS orders,
       ROUND(AVG(CASE WHEN o.status = 'filled' THEN 1.0 ELSE 0 END) * 100, 1) AS fill_rate_pct,
       ROUND(AVG(CASE WHEN o.status = 'filled' THEN (o.fill_price - o.limit_price) * 100 END), 2) AS avg_slippage_cents
FROM order_events o
JOIN markets m ON m.market_id = o.market_id
GROUP BY m.asset
ORDER BY fill_rate_pct;
