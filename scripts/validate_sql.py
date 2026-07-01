"""Execute SQL scripts and validate Phase 1 pipeline."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pymysql
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

EXPECTED_STAGING = {
    "stg_orders": 99441,
    "stg_order_items": 112650,
    "stg_customers": 99441,
    "stg_products": 32951,
    "stg_order_payments": 103886,
    "stg_category_translation": 71,
}

SALES_FACT_MIN_ROWS = 90000


def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "olist_user"),
        password=os.getenv("DB_PASSWORD", "olist_pass"),
        database=os.getenv("DB_NAME", "olist_analytics"),
        charset="utf8mb4",
        autocommit=True,
    )


def run_sql_file(conn, sql_path: Path) -> None:
    sql = sql_path.read_text(encoding="utf-8")
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    with conn.cursor() as cur:
        cur.execute("SET SESSION innodb_lock_wait_timeout = 300")
        executable = []
        for stmt in statements:
            upper = stmt.upper().lstrip()
            if upper.startswith("USE "):
                continue
            code_lines = [
                line for line in stmt.splitlines()
                if line.strip() and not line.strip().startswith("--")
            ]
            if not code_lines:
                continue
            executable.append(stmt)

        total = len(executable)
        for i, stmt in enumerate(executable, start=1):
            preview = " ".join(
                line for line in stmt.splitlines() if not line.strip().startswith("--")
            )[:70]
            print(f"  [{i}/{total}] {preview}...", flush=True)
            try:
                cur.execute(stmt)
            except pymysql.err.OperationalError as exc:
                if exc.args[0] == 1061:  # Duplicate key name (index already exists)
                    print(f"  [{i}/{total}] skipped (already exists)", flush=True)
                    continue
                raise
            print(f"  [{i}/{total}] done", flush=True)


def validate_counts(conn) -> bool:
    ok = True
    print("\n--- Validation ---")
    with conn.cursor() as cur:
        for table, expected in EXPECTED_STAGING.items():
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            status = "OK" if count == expected else "WARN"
            if count != expected:
                ok = False
            print(f"  [{status}] {table}: {count:,} (expected {expected:,})")

        cur.execute("SELECT COUNT(*) FROM sales_fact")
        fact_count = cur.fetchone()[0]
        if fact_count >= SALES_FACT_MIN_ROWS:
            print(f"  [OK] sales_fact: {fact_count:,} rows")
        else:
            print(f"  [FAIL] sales_fact: {fact_count:,} rows (expected >= {SALES_FACT_MIN_ROWS:,})")
            ok = False

        cur.execute(
            "SELECT COUNT(*) FROM sales_fact WHERE price < 0 OR total_revenue < 0"
        )
        bad_prices = cur.fetchone()[0]
        if bad_prices == 0:
            print("  [OK] No negative prices or revenue")
        else:
            print(f"  [FAIL] {bad_prices} rows with negative price/revenue")
            ok = False

        cur.execute(
            "SELECT COUNT(*) FROM sales_fact WHERE delivery_time_days < 0"
        )
        bad_delivery = cur.fetchone()[0]
        if bad_delivery == 0:
            print("  [OK] No negative delivery times")
        else:
            print(f"  [FAIL] {bad_delivery} rows with negative delivery time")
            ok = False

        cur.execute(
            """
            SELECT DATE_FORMAT(order_date, '%Y-%m') AS ym,
                   ROUND(SUM(total_revenue), 2) AS revenue
            FROM sales_fact
            GROUP BY ym
            ORDER BY ym
            LIMIT 3
            """
        )
        rows = cur.fetchall()
        print("\n  Sample monthly revenue (Query #2):")
        for ym, revenue in rows:
            print(f"    {ym}: R$ {revenue:,.2f}")

    return ok


def main() -> None:
    sql_path = PROJECT_ROOT / "sql" / "03_sales_fact.sql"
    if not sql_path.exists():
        print(f"Missing: {sql_path}", flush=True)
        sys.exit(1)

    conn = get_connection()
    try:
        print(f"Running {sql_path.name}...", flush=True)
        run_sql_file(conn, sql_path)

        if validate_counts(conn):
            print("\nValidation PASSED.", flush=True)
        else:
            print("\nValidation completed with warnings — review counts above.", flush=True)
            sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
