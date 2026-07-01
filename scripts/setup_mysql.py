"""Create olist_analytics database and application user (requires MySQL root)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pymysql
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

MYSQL_BIN = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"


def get_root_connection():
    password = os.getenv("MYSQL_ROOT_PASSWORD", "")
    if not password:
        print(
            "ERROR: MYSQL_ROOT_PASSWORD is not set in .env\n"
            "Set your MySQL root password in .env, then re-run:\n"
            "  python scripts/setup_mysql.py"
        )
        sys.exit(1)

    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user="root",
        password=password,
        charset="utf8mb4",
        autocommit=True,
    )


def run_sql_file(conn, sql_path: Path) -> None:
    sql = sql_path.read_text(encoding="utf-8")
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    with conn.cursor() as cur:
        for stmt in statements:
            if stmt.upper().startswith("USE "):
                continue
            cur.execute(stmt)
    print(f"  Executed: {sql_path.name}")


def main() -> None:
    sql_path = PROJECT_ROOT / "sql" / "01_create_database.sql"
    print("Setting up MySQL database...")
    conn = get_root_connection()
    try:
        run_sql_file(conn, sql_path)
        print("Database setup complete.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
