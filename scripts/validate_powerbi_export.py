"""Cross-validate Power BI CSV exports against MySQL analytical queries."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from db_utils import get_connection, get_engine

load_dotenv(PROJECT_ROOT / ".env", override=True)
POWERBI_DIR = PROJECT_ROOT / "data" / "powerbi"


def main() -> None:
    print("Phase 4: Validate Power BI exports\n")
    engine = get_engine()

    sf = pd.read_csv(POWERBI_DIR / "sales_fact.csv")
    monthly = pd.read_csv(POWERBI_DIR / "fact_monthly.csv")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM sales_fact")
            sql_rows = cur.fetchone()[0]
            cur.execute(
                """
                SELECT ROUND(SUM(total_revenue) / COUNT(DISTINCT order_id), 2)
                FROM sales_fact
                """
            )
            sql_aov = float(cur.fetchone()[0])
    finally:
        conn.close()

    csv_rows = len(sf)
    csv_aov = round(sf["total_revenue"].sum() / sf["order_id"].nunique(), 2)

    print(f"  sales_fact rows — SQL: {sql_rows:,} | CSV: {csv_rows:,} | match: {sql_rows == csv_rows}")
    print(f"  AOV (Query #5) — SQL: {sql_aov} | CSV: {csv_aov} | match: {abs(sql_aov - csv_aov) < 0.01}")

    sql_monthly = pd.read_sql(
        text(
            """
            SELECT LEFT(CAST(order_date AS CHAR), 7) AS `year_month`,
                   ROUND(SUM(total_revenue), 2) AS monthly_revenue
            FROM sales_fact
            GROUP BY LEFT(CAST(order_date AS CHAR), 7)
            ORDER BY `year_month`
            """
        ),
        engine,
    )
    merged = sql_monthly.merge(
        monthly[["year_month", "revenue"]],
        on="year_month",
        suffixes=("_sql", "_csv"),
    )
    max_diff = (merged["monthly_revenue"] - merged["revenue"]).abs().max()
    print(f"  Monthly revenue max diff: {max_diff:.2f} BRL (expect 0)")

    fc = POWERBI_DIR / "forecast_vs_actual.csv"
    if fc.exists():
        fdf = pd.read_csv(fc)
        print(f"  Forecast rows (long): {len(fdf):,} | models: {fdf['model_name'].nunique()}")

    ok = sql_rows == csv_rows and abs(sql_aov - csv_aov) < 0.01 and max_diff < 0.01
    print(f"\nValidation: {'PASSED' if ok else 'FAILED'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
