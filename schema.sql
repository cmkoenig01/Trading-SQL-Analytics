-- core schema for the trading analytics warehouse (sqlite, standard sql where possible).
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS markets (
    market_id    INTEGER PRIMARY KEY,
    asset        TEXT NOT NULL UNIQUE,
    interval_min INTEGER NOT NULL DEFAULT 15
);

CREATE TABLE IF NOT EXISTS model_versions (
    version_id  INTEGER PRIMARY KEY,
    trained_at  TEXT NOT NULL,
    notes       TEXT
);

-- pipeline audit trail: one row per load, used for lineage.
CREATE TABLE IF NOT EXISTS etl_load_log (
    load_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file    TEXT NOT NULL,
    loaded_at      TEXT NOT NULL,
    rows_read      INTEGER,
    rows_loaded    INTEGER,
    rows_rejected  INTEGER
);

-- raw landing table: everything is text so bad data never blocks a load.
CREATE TABLE IF NOT EXISTS stg_trades (
    row_num        INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id       TEXT, asset TEXT, version_id TEXT, opened_at TEXT, side TEXT,
    contracts      TEXT, entry_price TEXT, predicted_prob TEXT, won TEXT,
    fees           TEXT, pnl TEXT
);

-- validated fact table. check constraints are the last line of defense.
CREATE TABLE IF NOT EXISTS trades (
    trade_id        INTEGER PRIMARY KEY,
    market_id       INTEGER NOT NULL REFERENCES markets(market_id),
    version_id      INTEGER NOT NULL REFERENCES model_versions(version_id),
    opened_at       TEXT NOT NULL,
    side            TEXT NOT NULL CHECK (side IN ('yes','no')),
    contracts       INTEGER NOT NULL CHECK (contracts > 0),
    entry_price     REAL NOT NULL CHECK (entry_price > 0 AND entry_price < 1),
    predicted_prob  REAL NOT NULL CHECK (predicted_prob BETWEEN 0 AND 1),
    won             INTEGER NOT NULL CHECK (won IN (0,1)),
    fees            REAL NOT NULL CHECK (fees >= 0),
    pnl             REAL NOT NULL,
    load_id         INTEGER NOT NULL REFERENCES etl_load_log(load_id)
);
CREATE INDEX IF NOT EXISTS ix_trades_market_time ON trades (market_id, opened_at);

-- quarantine for rows that failed a data quality rule.
CREATE TABLE IF NOT EXISTS dq_rejects (
    load_id   INTEGER NOT NULL,
    row_num   INTEGER NOT NULL,
    trade_id  TEXT,
    rule      TEXT NOT NULL
);

-- orders sent to the exchange, including ones that never filled.
CREATE TABLE IF NOT EXISTS order_events (
    order_id      INTEGER PRIMARY KEY,
    trade_id      INTEGER REFERENCES trades(trade_id),
    market_id     INTEGER NOT NULL REFERENCES markets(market_id),
    submitted_at  TEXT NOT NULL,
    limit_price   REAL NOT NULL,
    fill_price    REAL,
    status        TEXT NOT NULL CHECK (status IN ('filled','unfilled'))
);

-- exchange statement totals, used for daily reconciliation.
CREATE TABLE IF NOT EXISTS daily_ledger (
    ledger_date   TEXT PRIMARY KEY,
    reported_pnl  REAL NOT NULL
);
