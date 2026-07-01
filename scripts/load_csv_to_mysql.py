"""Load Olist CSV files into MySQL staging tables."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import text

from db_utils import get_engine

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASETS_DIR = PROJECT_ROOT / "datasets"
load_dotenv(PROJECT_ROOT / ".env", override=True)

CHUNK_SIZE = 5000

TABLE_CONFIG = [
    {
        "file": "olist_orders_dataset.csv",
        "table": "stg_orders",
        "parse_dates": [
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    },
    {
        "file": "olist_order_items_dataset.csv",
        "table": "stg_order_items",
        "parse_dates": ["shipping_limit_date"],
    },
    {
        "file": "olist_customers_dataset.csv",
        "table": "stg_customers",
        "parse_dates": [],
    },
    {
        "file": "olist_products_dataset.csv",
        "table": "stg_products",
        "parse_dates": [],
    },
    {
        "file": "olist_order_payments_dataset.csv",
        "table": "stg_order_payments",
        "parse_dates": [],
    },
    {
        "file": "product_category_name_translation.csv",
        "table": "stg_category_translation",
        "parse_dates": [],
    },
    {
        "file": "olist_sellers_dataset.csv",
        "table": "stg_sellers",
        "parse_dates": [],
    },
    {
        "file": "olist_order_reviews_dataset.csv",
        "table": "stg_order_reviews",
        "parse_dates": ["review_creation_date", "review_answer_timestamp"],
    },
]


def main() -> None:
    engine = get_engine()
    sql = sql_path.read_text(encoding="utf-8")
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    with engine.connect() as conn:
        for stmt in statements:
            if stmt.upper().lstrip().startswith("USE "):
                continue
            conn.execute(text(stmt))
        conn.commit()


def load_table(engine, config: dict) -> int:
    csv_path = DATASETS_DIR / config["file"]
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    parse_dates = config.get("parse_dates") or []
    df = pd.read_csv(csv_path, parse_dates=parse_dates if parse_dates else False)

    for col in parse_dates:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    df.to_sql(
        config["table"],
        engine,
        if_exists="replace",
        index=False,
        chunksize=CHUNK_SIZE,
        method="multi",
    )
    return len(df)


def main() -> None:
    engine = get_engine()
    ddl_path = PROJECT_ROOT / "sql" / "02_create_tables.sql"
    print("Creating staging and dimension tables...")
    run_sql_file(engine, ddl_path)

    print("\nLoading CSV files into MySQL staging tables...\n")

    with engine.connect() as conn:
        conn.execute(text(f"USE {os.getenv('DB_NAME', 'olist_analytics')}"))

    total_rows = 0
    for config in TABLE_CONFIG:
        rows = load_table(engine, config)
        total_rows += rows
        print(f"  {config['table']:<30} {rows:>10,} rows")

    print(f"\nDone. Loaded {total_rows:,} total rows across {len(TABLE_CONFIG)} tables.")


if __name__ == "__main__":
    main()
