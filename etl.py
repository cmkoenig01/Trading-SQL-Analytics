# load raw csvs into sqlite: stage, validate (sql rules), load valid rows, quarantine bad rows
import csv, sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
MARKETS = ["BTC", "ETH", "SOL", "XRP", "DOGE", "BNB", "AVAX", "LINK"]
VERSION_NOTES = {1: "initial", 2: "retrain 1", 3: "retrain 2", 4: "retrain 3"}


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def run(db_path="trading.db", data_dir="data"):
    data = ROOT / data_dir if not Path(data_dir).is_absolute() else Path(data_dir)
    db = Path(db_path)
    if db.exists():
        db.unlink()
    con = sqlite3.connect(db)
    con.executescript((ROOT / "schema.sql").read_text())

    con.executemany("INSERT INTO markets(asset) VALUES (?)", [(m,) for m in MARKETS])
    con.executemany("INSERT INTO model_versions(version_id, trained_at, notes) VALUES (?,?,?)",
                    [(v, f"2026-0{2 + v}-01", n) for v, n in VERSION_NOTES.items()])

    rows = read_csv(data / "trades.csv")
    cur = con.execute("INSERT INTO etl_load_log(source_file, loaded_at, rows_read) VALUES (?,?,?)",
                      ("trades.csv", datetime.now().isoformat(timespec="seconds"), len(rows)))
    load_id = cur.lastrowid
    cols = ["trade_id", "asset", "version_id", "opened_at", "side", "contracts",
            "entry_price", "predicted_prob", "won", "fees", "pnl"]
    con.executemany(f"INSERT INTO stg_trades({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                    [[r[c] for c in cols] for r in rows])

    con.executescript((ROOT / "validate.sql").read_text())
    con.execute("""INSERT INTO dq_rejects(load_id, row_num, trade_id, rule)
                   SELECT ?, row_num, trade_id, reject_rule FROM stg_checked WHERE reject_rule IS NOT NULL""",
                (load_id,))
    con.execute("""INSERT INTO trades(trade_id, market_id, version_id, opened_at, side, contracts,
                                      entry_price, predicted_prob, won, fees, pnl, load_id)
                   SELECT CAST(trade_id AS INTEGER), market_id, CAST(version_id AS INTEGER), opened_at, side,
                          CAST(contracts AS INTEGER), CAST(entry_price AS REAL), CAST(predicted_prob AS REAL),
                          CAST(won AS INTEGER), CAST(fees AS REAL), CAST(pnl AS REAL), ?
                   FROM stg_checked WHERE reject_rule IS NULL""", (load_id,))
    loaded = con.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    rejected = con.execute("SELECT COUNT(*) FROM dq_rejects WHERE load_id=?", (load_id,)).fetchone()[0]
    con.execute("UPDATE etl_load_log SET rows_loaded=?, rows_rejected=? WHERE load_id=?",
                (loaded, rejected, load_id))

    # orders: keep the link to a trade only if that trade passed validation
    orders = read_csv(data / "orders.csv")
    valid_trades = {r[0] for r in con.execute("SELECT trade_id FROM trades")}
    market_id = dict(con.execute("SELECT asset, market_id FROM markets"))
    out = []
    for o in orders:
        tid = int(o["trade_id"]) if o["trade_id"] and int(o["trade_id"]) in valid_trades else None
        out.append((int(o["order_id"]), tid, market_id[o["asset"]], o["submitted_at"],
                    float(o["limit_price"]), float(o["fill_price"]) if o["fill_price"] else None, o["status"]))
    con.executemany("""INSERT INTO order_events(order_id, trade_id, market_id, submitted_at,
                       limit_price, fill_price, status) VALUES (?,?,?,?,?,?,?)""", out)

    con.executemany("INSERT INTO daily_ledger VALUES (?,?)",
                    [(r["ledger_date"], float(r["reported_pnl"])) for r in read_csv(data / "ledger.csv")])
    con.commit()
    summary = dict(load_id=load_id, rows_read=len(rows), rows_loaded=loaded, rows_rejected=rejected)
    con.close()
    return summary


if __name__ == "__main__":
    print(run())
