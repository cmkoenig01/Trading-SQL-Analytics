# generate a synthetic trading dataset (not real trades) with known injected data quality issues
# run: python generate_data.py [--seed 7] [--trades 1100]
# writes data/trades.csv, data/orders.csv, data/ledger.csv, data/manifest.json
# to use real data, export your own trades to the same columns and skip this script
import argparse, csv, json, random
from datetime import datetime, timedelta
from pathlib import Path

MARKETS = ["BTC", "ETH", "SOL", "XRP", "DOGE", "BNB", "AVAX", "LINK"]
# edge = true win probability above the entry price, vol = contract size multiplier
PROFILE = {"BTC": (0.05, 1.0), "ETH": (0.04, 1.0), "SOL": (0.0, 2.2), "XRP": (0.035, 1.0),
           "DOGE": (0.03, 1.2), "BNB": (0.045, 0.9), "AVAX": (0.025, 1.1), "LINK": (0.03, 1.0)}
START = datetime(2026, 3, 1)
DAYS = 120


def clip(x, lo, hi):
    return max(lo, min(hi, x))


def build(seed, n_trades):
    rng = random.Random(seed)
    trades, orders = [], []
    for tid in range(1, n_trades + 1):
        asset = rng.choice(MARKETS)
        edge, vol = PROFILE[asset]
        ts = START + timedelta(days=rng.random() * DAYS)
        ts = ts.replace(microsecond=0)
        version = min(4, 1 + int((ts - START).days // 30))
        entry = round(rng.uniform(0.25, 0.75), 2)
        drift = 0.15 if (asset == "AVAX" and version == 4) else 0.0  # model drift planted late
        true_p = clip(entry + edge, 0.02, 0.98)
        predicted = round(clip(true_p + drift + rng.gauss(0, 0.04), 0.01, 0.99), 3)
        won = 1 if rng.random() < true_p else 0
        contracts = max(1, int(rng.choice([5, 10, 15, 20, 30, 40]) * vol))
        fees = round(0.07 * contracts * entry * (1 - entry), 2)
        pnl = round(contracts * (won - entry) - fees, 2)
        trades.append(dict(trade_id=tid, asset=asset, version_id=version,
                           opened_at=ts.isoformat(sep=" "), side=rng.choice(["yes", "no"]),
                           contracts=contracts, entry_price=entry, predicted_prob=predicted,
                           won=won, fees=fees, pnl=pnl))
        slip = round(rng.choice([0, 0, 0.01, 0.01, 0.02]), 2)
        orders.append(dict(trade_id=tid, asset=asset, submitted_at=ts.isoformat(sep=" "),
                           limit_price=entry, fill_price=round(entry + slip, 2), status="filled"))
    # orders that never filled (no trade row)
    for _ in range(int(n_trades * 0.25)):
        asset = rng.choice(MARKETS)
        ts = (START + timedelta(days=rng.random() * DAYS)).replace(microsecond=0)
        orders.append(dict(trade_id="", asset=asset, submitted_at=ts.isoformat(sep=" "),
                           limit_price=round(rng.uniform(0.25, 0.75), 2), fill_price="", status="unfilled"))
    rng.shuffle(orders)
    for i, o in enumerate(orders, 1):
        o["order_id"] = i

    # inject data quality issues into the raw trade export
    ids = list(range(len(trades)))
    rng.shuffle(ids)
    pick = lambda k: [ids.pop() for _ in range(k)]
    manifest = {"seed": seed, "clean_trades": n_trades}
    for i in pick(8):  trades[i]["entry_price"] = ""
    for i in pick(6):  trades[i]["entry_price"] = rng.choice([0, 1.0, 1.2])
    for i in pick(5):  trades[i]["asset"] = "DOGE2"
    for i in pick(7):  trades[i]["pnl"] = round(trades[i]["pnl"] + 5.0, 2)
    corrupted = set(range(len(trades))) - set(ids)
    dup_idx = pick(12)
    dups = [dict(trades[i]) for i in dup_idx]
    trades.extend(dups)
    # ledger = exchange statement, it covers every trade that passes validation
    daily = {}
    for i, t in enumerate(trades[:n_trades]):
        if i in corrupted:
            continue
        d = t["opened_at"][:10]
        daily[d] = round(daily.get(d, 0) + t["pnl"], 2)
    ledger = [dict(ledger_date=d, reported_pnl=v) for d, v in sorted(daily.items())]
    bad_days = rng.sample(range(len(ledger)), 3)
    for i in bad_days:
        ledger[i]["reported_pnl"] = round(ledger[i]["reported_pnl"] + rng.choice([-3.5, 2.25, 7.0]), 2)
    manifest.update(missing=8, price_range=6, unknown_market=5, pnl_mismatch=7, duplicates=12,
                    total_bad=38, ledger_bad_days=len(bad_days),
                    ledger_bad_dates=sorted(ledger[i]["ledger_date"] for i in bad_days))
    return trades, orders, ledger, manifest


def write_csv(path, rows, cols):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def main(out_dir="data", seed=7, n_trades=1100):
    out = Path(out_dir)
    out.mkdir(exist_ok=True)
    trades, orders, ledger, manifest = build(seed, n_trades)
    write_csv(out / "trades.csv", trades, ["trade_id", "asset", "version_id", "opened_at", "side",
              "contracts", "entry_price", "predicted_prob", "won", "fees", "pnl"])
    write_csv(out / "orders.csv", orders, ["order_id", "trade_id", "asset", "submitted_at",
              "limit_price", "fill_price", "status"])
    write_csv(out / "ledger.csv", ledger, ["ledger_date", "reported_pnl"])
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--trades", type=int, default=1100)
    a = ap.parse_args()
    print(main(seed=a.seed, n_trades=a.trades))
