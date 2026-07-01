"""Shared database connection helpers."""

from __future__ import annotations

import os
from urllib.parse import quote_plus

import pymysql
from dotenv import load_dotenv
from sqlalchemy import create_engine

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=True)


def get_engine():
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    user = quote_plus(os.getenv("DB_USER", "olist_user"))
    password = quote_plus(os.getenv("DB_PASSWORD", "olist_pass"))
    database = os.getenv("DB_NAME", "olist_analytics")
    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
    return create_engine(url)


def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "olist_user"),
        password=os.getenv("DB_PASSWORD", "olist_pass"),
        database=os.getenv("DB_NAME", "olist_analytics"),
        charset="utf8mb4",
    )


def fetch_monthly_revenue() -> pd.DataFrame:
    """Run Query #2 without pandas/pymysql % formatting conflicts."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    LEFT(CAST(order_date AS CHAR), 7) AS `year_month`,
                    ROUND(SUM(total_revenue), 2) AS monthly_revenue
                FROM sales_fact
                GROUP BY LEFT(CAST(order_date AS CHAR), 7)
                ORDER BY `year_month`
                """
            )
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            return pd.DataFrame(rows, columns=columns)
    finally:
        conn.close()
