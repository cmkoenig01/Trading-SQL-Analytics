# Trading Analytics Warehouse (SQL)

A small SQL data pipeline and analytics layer for an automated trading system: raw exports are staged, validated with
SQL data quality rules, loaded into a normalized schema, and analyzed with window functions and CTEs.

**The bundled data is synthetic.** `generate_data.py` creates a fake trade history with known, planted data quality
problems so the pipeline can be tested end to end. To use real exports, put them in `data/` with the same columns and skip
the generator.

## Run it
```
python generate_data.py        # make synthetic CSVs in data/
python etl.py                  # stage -> validate -> load into trading.db
python run_analysis.py         # run all queries, print results, write CSVs to output/
python -m unittest discover -s tests -v
```
Requires Python 3.9+ and SQLite 3.25+ (window functions). No other dependencies.

## What it demonstrates
- **Schema design:** normalized tables, primary and foreign keys, CHECK constraints, indexes (`schema.sql`).
- **ETL with data quality:** raw landing table, five SQL validation rules, a quarantine table for rejects, and a load log for
  lineage (`validate.sql`, `etl.py`).
- **Analytics SQL:** joins, CTEs, window functions (running totals, rolling averages, running max for drawdown), conditional
  aggregation, and what-if scenario analysis (`queries/`).
- **Reconciliation:** compares warehouse totals against an exchange statement and lists days that disagree.
- **Testing:** 11 unittest cases check that every planted bad row is caught, row counts balance, constraints hold, and
  query results agree with each other.
- **BI-ready output:** each query exports a CSV that loads straight into Tableau or Power BI.

## Data quality rules
| Rule | Catches |
|---|---|
| R1_DUPLICATE_ID | repeated trade ids |
| R2_MISSING_REQUIRED | blank required fields |
| R3_UNKNOWN_MARKET | markets not in the reference table |
| R4_PRICE_OUT_OF_RANGE | entry price outside (0, 1) |
| R5_PNL_MISMATCH | stated P&L that disagrees with contracts, price, outcome, and fees |

## Queries
| File | Question it answers |
|---|---|
| 01 | Per-market win rate, P&L, and risk-adjusted return |
| 02 | Monthly P&L with a running cumulative total |
| 03 | Rolling 50-trade win rate vs all-time, to spot decay |
| 04 | Portfolio equity curve and max drawdown |
| 05 | What happens to P&L and drawdown if each market is dropped |
| 06 | Fill rate and slippage by market |
| 07 | Model calibration by version, to flag drift |
| 08 | Days where warehouse P&L disagrees with the ledger |
| 09 | Data quality report from the pipeline |
| 10 | Performance by time of day |

## Limits
- SQLite keeps it dependency free. The SQL is mostly standard and ports to Postgres or Snowflake with small changes
  (`strftime` and `date()` become `date_trunc` and `to_char`, and the `WINDOW` clause is supported in Postgres).
- Results on synthetic data show the pipeline works, not anything about real trading performance.
