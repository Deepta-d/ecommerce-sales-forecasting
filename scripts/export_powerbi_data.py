"""Export CSV datasets for Power BI Phase 4 dashboard."""

from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import text

from db_utils import get_connection, get_engine

PROJECT_ROOT = Path(__file__).resolve().parent.parent
POWERBI_DIR = PROJECT_ROOT / "data" / "powerbi"
FORECAST_DIR = PROJECT_ROOT / "data" / "forecasts"
SQL_VIEW = PROJECT_ROOT / "sql" / "05_powerbi_export.sql"

load_dotenv(PROJECT_ROOT / ".env", override=True)


SALES_FACT_POWERBI_SQL = """
SELECT
    sf.order_id,
    sf.order_item_id,
    sf.order_date,
    sf.customer_location,
    c.customer_city,
    sf.customer_state,
    sf.product_id,
    sf.product_category,
    sf.price,
    sf.quantity,
    sf.total_revenue,
    sf.payment_type,
    p.payment_installments,
    sf.delivery_time_days
FROM sales_fact sf
LEFT JOIN dim_orders o ON sf.order_id = o.order_id
LEFT JOIN dim_customers c ON o.customer_id = c.customer_id
LEFT JOIN dim_payments p ON sf.order_id = p.order_id
"""


def ensure_view() -> None:
    """Optional: create v_sales_fact_powerbi when run as admin (sql/05_powerbi_export.sql)."""
    if not SQL_VIEW.exists():
        return
    try:
        sql = SQL_VIEW.read_text(encoding="utf-8")
        statements = [
            s.strip()
            for s in sql.split(";")
            if s.strip() and not s.strip().startswith("--")
        ]
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                for stmt in statements:
                    if stmt.upper().startswith("USE "):
                        continue
                    cur.execute(stmt)
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        print(f"  Note: view not created ({exc.__class__.__name__}) — using inline join query.")


def export_sales_fact(engine) -> pd.DataFrame:
    df = pd.read_sql(text(SALES_FACT_POWERBI_SQL), engine)
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df


def build_dim_date(min_date: pd.Timestamp, max_date: pd.Timestamp) -> pd.DataFrame:
    dates = pd.date_range(min_date, max_date, freq="D")
    df = pd.DataFrame({"date": dates})
    df["year"] = df["date"].dt.year
    df["quarter"] = df["date"].dt.quarter
    df["month"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.strftime("%B")
    df["year_month"] = df["date"].dt.strftime("%Y-%m")
    df["day_of_week"] = df["date"].dt.dayofweek
    df["day_name"] = df["date"].dt.strftime("%A")
    df["is_weekend"] = df["day_of_week"].isin([5, 6])
    return df


def build_fact_daily(sf: pd.DataFrame) -> pd.DataFrame:
    daily = (
        sf.groupby("order_date", as_index=False)
        .agg(
            revenue=("total_revenue", "sum"),
            orders=("order_id", "nunique"),
            items=("order_item_id", "count"),
        )
        .rename(columns={"order_date": "date"})
    )
    daily["aov"] = daily["revenue"] / daily["orders"].replace(0, np.nan)
    return daily


def build_fact_monthly(sf: pd.DataFrame) -> pd.DataFrame:
    sf = sf.copy()
    sf["year_month"] = sf["order_date"].dt.strftime("%Y-%m")
    monthly = (
        sf.groupby("year_month", as_index=False)
        .agg(
            revenue=("total_revenue", "sum"),
            orders=("order_id", "nunique"),
        )
        .sort_values("year_month")
    )
    monthly["month_start"] = pd.to_datetime(monthly["year_month"] + "-01")
    monthly["aov"] = monthly["revenue"] / monthly["orders"].replace(0, np.nan)
    monthly["revenue_growth_pct"] = monthly["revenue"].pct_change() * 100
    return monthly


def build_fact_category(sf: pd.DataFrame) -> pd.DataFrame:
    cat = (
        sf.groupby("product_category", as_index=False)
        .agg(
            revenue=("total_revenue", "sum"),
            orders=("order_id", "nunique"),
            items=("order_item_id", "count"),
        )
        .sort_values("revenue", ascending=False)
    )
    total = cat["revenue"].sum()
    cat["revenue_share_pct"] = (cat["revenue"] / total * 100).round(2)
    cat["rank"] = range(1, len(cat) + 1)
    return cat


def build_fact_product(sf: pd.DataFrame, top_n: int = 10, bottom_n: int = 15) -> pd.DataFrame:
    prod = (
        sf.groupby(["product_id", "product_category"], as_index=False)
        .agg(
            revenue=("total_revenue", "sum"),
            units=("order_item_id", "count"),
            orders=("order_id", "nunique"),
        )
        .sort_values("revenue", ascending=False)
    )
    prod["rank"] = range(1, len(prod) + 1)
    prod["performance_tier"] = "mid"
    prod.loc[prod["rank"] <= top_n, "performance_tier"] = "top"
    prod.loc[prod["rank"] > len(prod) - bottom_n, "performance_tier"] = "bottom"
    return prod


def build_fact_region(sf: pd.DataFrame) -> pd.DataFrame:
    region = (
        sf.groupby(["customer_state", "customer_city"], as_index=False)
        .agg(
            revenue=("total_revenue", "sum"),
            orders=("order_id", "nunique"),
            items=("order_item_id", "count"),
        )
        .sort_values("revenue", ascending=False)
    )
    region["aov"] = region["revenue"] / region["orders"].replace(0, np.nan)
    return region


def build_fact_region_growth(sf: pd.DataFrame, min_orders: int = 10) -> pd.DataFrame:
    sf = sf.copy()
    sf["year_month"] = sf["order_date"].dt.strftime("%Y-%m")
    monthly_state = (
        sf.groupby(["customer_state", "year_month"], as_index=False)
        .agg(revenue=("total_revenue", "sum"), orders=("order_id", "nunique"))
        .sort_values(["customer_state", "year_month"])
    )
    monthly_state["prior_revenue"] = monthly_state.groupby("customer_state")["revenue"].shift(1)
    monthly_state["mom_growth_pct"] = (
        (monthly_state["revenue"] - monthly_state["prior_revenue"])
        / monthly_state["prior_revenue"].replace(0, np.nan)
        * 100
    )
    monthly_state = monthly_state[monthly_state["orders"] >= min_orders]
    monthly_state = monthly_state.dropna(subset=["mom_growth_pct"])
    return monthly_state


def export_forecast_long() -> pd.DataFrame | None:
    wide_path = FORECAST_DIR / "forecast_vs_actual.csv"
    if not wide_path.exists():
        return None
    wide = pd.read_csv(wide_path)
    wide["date"] = pd.to_datetime(wide["date"])
    model_cols = [c for c in wide.columns if c not in ("date", "actual")]
    long = wide.melt(
        id_vars=["date", "actual"],
        value_vars=model_cols,
        var_name="model_name",
        value_name="forecast",
    )
    long["forecast_error"] = long["actual"] - long["forecast"]
    long["forecast_error_pct"] = np.where(
        long["actual"] != 0,
        np.abs(long["forecast_error"] / long["actual"]) * 100,
        np.nan,
    )
    return long


def main() -> None:
    print("Phase 4: Export Power BI datasets\n")
    POWERBI_DIR.mkdir(parents=True, exist_ok=True)

    ensure_view()
    engine = get_engine()
    sf = export_sales_fact(engine)
    print(f"  sales_fact rows: {len(sf):,}")

    min_d, max_d = sf["order_date"].min(), sf["order_date"].max()
    tables = {
        "sales_fact.csv": sf,
        "dim_date.csv": build_dim_date(min_d, max_d),
        "fact_daily.csv": build_fact_daily(sf),
        "fact_monthly.csv": build_fact_monthly(sf),
        "fact_category.csv": build_fact_category(sf),
        "fact_product.csv": build_fact_product(sf),
        "fact_region.csv": build_fact_region(sf),
        "fact_region_growth.csv": build_fact_region_growth(sf),
    }

    for name, df in tables.items():
        path = POWERBI_DIR / name
        df.to_csv(path, index=False)
        print(f"  wrote {name} ({len(df):,} rows)")

    forecast_long = export_forecast_long()
    if forecast_long is not None:
        forecast_long.to_csv(POWERBI_DIR / "forecast_vs_actual.csv", index=False)
        print(f"  wrote forecast_vs_actual.csv ({len(forecast_long):,} rows, long format)")
    else:
        print("  skip forecast_vs_actual.csv (run scripts/run_forecast.py first)")

    comp_src = FORECAST_DIR / "model_comparison.csv"
    if comp_src.exists():
        shutil.copy(comp_src, POWERBI_DIR / "model_comparison.csv")
        print("  copied model_comparison.csv")
    else:
        print("  skip model_comparison.csv (run scripts/run_forecast.py first)")

    print(f"\nExports saved to {POWERBI_DIR}")


if __name__ == "__main__":
    main()
