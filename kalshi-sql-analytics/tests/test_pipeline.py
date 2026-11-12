# pipeline tests (stdlib unittest): python -m unittest discover -s tests -v
import json, sqlite3, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import generate_data, etl, run_analysis


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls.tmp.name)
        cls.manifest = generate_data.main(out_dir=str(tmp), seed=7, n_trades=1100)
        cls.db = str(tmp / "t.db")
        cls.summary = etl.run(cls.db, data_dir=str(tmp))
        cls.con = sqlite3.connect(cls.db)
        cls.results = run_analysis.run(cls.db, out_dir=str(tmp / "out"))

    @classmethod
    def tearDownClass(cls):
        cls.con.close()
        cls.tmp.cleanup()

    def q(self, sql):
        return self.con.execute(sql).fetchall()

    def test_every_injected_issue_is_caught(self):
        got = dict(self.q("SELECT rule, COUNT(*) FROM dq_rejects GROUP BY rule"))
        m = self.manifest
        self.assertEqual(got["R1_DUPLICATE_ID"], m["duplicates"])
        self.assertEqual(got["R2_MISSING_REQUIRED"], m["missing"])
        self.assertEqual(got["R3_UNKNOWN_MARKET"], m["unknown_market"])
        self.assertEqual(got["R4_PRICE_OUT_OF_RANGE"], m["price_range"])
        self.assertEqual(got["R5_PNL_MISMATCH"], m["pnl_mismatch"])

    def test_row_counts_balance(self):
        s = self.summary
        self.assertEqual(s["rows_read"], s["rows_loaded"] + s["rows_rejected"])

    def test_no_bad_rows_reach_fact_table(self):
        self.assertEqual(self.q("SELECT COUNT(*) FROM trades WHERE entry_price<=0 OR entry_price>=1")[0][0], 0)
        self.assertEqual(self.q("SELECT COUNT(*) FROM (SELECT trade_id FROM trades GROUP BY trade_id HAVING COUNT(*)>1)")[0][0], 0)
        bad = self.q("""SELECT COUNT(*) FROM trades
                        WHERE ABS(pnl - (contracts*(won-entry_price) - fees)) > 0.01""")[0][0]
        self.assertEqual(bad, 0)

    def test_foreign_keys_hold(self):
        self.assertEqual(self.q("PRAGMA foreign_key_check"), [])

    def test_lineage_recorded(self):
        self.assertEqual(self.q("SELECT COUNT(*) FROM trades WHERE load_id IS NULL")[0][0], 0)

    def test_reconciliation_finds_exactly_the_planted_days(self):
        found = sorted(r[0] for r in self.results["08_daily_reconciliation"][1])
        self.assertEqual(found, self.manifest["ledger_bad_dates"])

    def test_drawdown_is_never_positive(self):
        peak, final, mdd, day = self.results["04_portfolio_drawdown"][1][0]
        self.assertLessEqual(mdd, 0)
        self.assertGreaterEqual(peak, final)

    def test_drawdown_total_matches_sum_of_pnl(self):
        total = self.q("SELECT ROUND(SUM(pnl),2) FROM trades")[0][0]
        final = self.results["04_portfolio_drawdown"][1][0][1]
        self.assertAlmostEqual(total, final, places=2)

    def test_whatif_baseline_matches_portfolio(self):
        rows = {r[0]: r for r in self.results["05_drop_one_market_whatif"][1]}
        total = self.q("SELECT ROUND(SUM(pnl),2) FROM trades")[0][0]
        self.assertAlmostEqual(rows["NONE (baseline)"][1], total, places=2)
        self.assertAlmostEqual(rows["NONE (baseline)"][2],
                               self.results["04_portfolio_drawdown"][1][0][2], places=2)

    def test_market_scorecard_covers_all_trades(self):
        n = sum(r[1] for r in self.results["01_market_performance"][1])
        self.assertEqual(n, self.summary["rows_loaded"])

    def test_fill_rate_between_0_and_100(self):
        for r in self.results["06_fill_rate_slippage"][1]:
            self.assertTrue(0 <= r[2] <= 100)


if __name__ == "__main__":
    unittest.main()
