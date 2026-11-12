# run every query in queries/, print results, and export csvs (ready for tableau or power bi)
import csv, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).parent


def run(db_path="trading.db", out_dir="output"):
    out = ROOT / out_dir
    out.mkdir(exist_ok=True)
    con = sqlite3.connect(db_path)
    results = {}
    for q in sorted((ROOT / "queries").glob("*.sql")):
        cur = con.execute(q.read_text())
        cols = [c[0] for c in cur.description]
        rows = cur.fetchall()
        results[q.stem] = (cols, rows)
        with open(out / f"{q.stem}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(rows)
    con.close()
    return results


def show(results):
    for name, (cols, rows) in results.items():
        print(f"\n== {name} ==")
        widths = [max(len(str(c)), *(len(str(r[i])) for r in rows)) if rows else len(str(c))
                  for i, c in enumerate(cols)]
        print("  ".join(str(c).ljust(w) for c, w in zip(cols, widths)))
        for r in rows[:12]:
            print("  ".join(str(v).ljust(w) for v, w in zip(r, widths)))


if __name__ == "__main__":
    show(run(*(sys.argv[1:2] or ["trading.db"])))
