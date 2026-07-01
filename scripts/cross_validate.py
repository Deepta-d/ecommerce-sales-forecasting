"""Cross-validate Phase 2 Python monthly revenue vs SQL Query #2."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import text

from db_utils import fetch_monthly_revenue, get_engine

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)


def main() -> None:
    engine = get_engine()
    sql_monthly = fetch_monthly_revenue()
    sql_monthly["monthly_revenue"] = sql_monthly["monthly_revenue"].astype(float)

    df = pd.read_sql(text("SELECT order_date, total_revenue FROM sales_fact"), engine)
    df["order_date"] = pd.to_datetime(df["order_date"])
    python_monthly = (
        df.set_index("order_date")
        .resample("ME")["total_revenue"]
        .sum()
        .reset_index()
    )
    python_monthly["year_month"] = python_monthly["order_date"].dt.strftime("%Y-%m")
    python_monthly["monthly_revenue"] = python_monthly["total_revenue"].round(2)

    merged = sql_monthly.merge(
        python_monthly[["year_month", "monthly_revenue"]],
        on="year_month",
        suffixes=("_sql", "_python"),
    )
    merged["diff"] = (merged["monthly_revenue_sql"] - merged["monthly_revenue_python"]).abs()
    max_diff = merged["diff"].max()

    print("Cross-validation: SQL Query #2 vs Python monthly resample\n")
    print(merged.to_string(index=False))
    print(f"\nMax absolute difference: R$ {max_diff:.4f}")

    if max_diff < 0.01:
        print("\nCross-validation PASSED.")
    else:
        print("\nCross-validation FAILED — totals do not match.")
        sys.exit(1)


if __name__ == "__main__":
    main()
