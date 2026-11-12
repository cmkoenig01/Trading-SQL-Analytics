-- data quality rules applied to the staging table. first failing rule wins.
DROP VIEW IF EXISTS stg_checked;
CREATE VIEW stg_checked AS
SELECT
    s.*,
    m.market_id,
    CASE
        WHEN ROW_NUMBER() OVER (PARTITION BY s.trade_id ORDER BY s.row_num) > 1
            THEN 'R1_DUPLICATE_ID'
        WHEN NULLIF(s.trade_id,'') IS NULL OR NULLIF(s.entry_price,'') IS NULL
          OR NULLIF(s.contracts,'') IS NULL OR NULLIF(s.pnl,'') IS NULL
          OR NULLIF(s.won,'') IS NULL OR NULLIF(s.fees,'') IS NULL
            THEN 'R2_MISSING_REQUIRED'
        WHEN m.market_id IS NULL
            THEN 'R3_UNKNOWN_MARKET'
        WHEN CAST(s.entry_price AS REAL) <= 0 OR CAST(s.entry_price AS REAL) >= 1
            THEN 'R4_PRICE_OUT_OF_RANGE'
        WHEN ABS(CAST(s.pnl AS REAL)
                 - (CAST(s.contracts AS REAL) * (CAST(s.won AS REAL) - CAST(s.entry_price AS REAL))
                    - CAST(s.fees AS REAL))) > 0.01
            THEN 'R5_PNL_MISMATCH'
    END AS reject_rule
FROM stg_trades s
LEFT JOIN markets m ON m.asset = s.asset;
