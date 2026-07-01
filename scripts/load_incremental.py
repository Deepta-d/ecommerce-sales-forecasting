"""Load incremental CSV files from datasets/incremental/ into staging tables."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import text

from db_utils import get_engine
from load_csv_to_mysql import TABLE_CONFIG

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INCREMENTAL_DIR = PROJECT_ROOT / "datasets" / "incremental"
load_dotenv(PROJECT_ROOT / ".env", override=True)


def load_incremental_table(engine, config: dict, csv_path: Path) -> int:
    parse_dates = config.get("parse_dates") or []
    df = pd.read_csv(csv_path, parse_dates=parse_dates if parse_dates else False)
    for col in parse_dates:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Append new rows; primary keys on staging tables prevent exact duplicates.
    df.to_sql(
        config["table"],
        engine,
        if_exists="append",
        index=False,
        chunksize=5000,
        method="multi",
    )
    return len(df)


def main() -> None:
    if not INCREMENTAL_DIR.exists():
        INCREMENTAL_DIR.mkdir(parents=True)
        print(f"Created {INCREMENTAL_DIR}")
        print("Place new daily CSV exports here (same filenames as datasets/).")
        print("No incremental files to load — skipping.")
        return

    files = {p.name: p for p in INCREMENTAL_DIR.glob("*.csv")}
    if not files:
        print(f"No CSV files in {INCREMENTAL_DIR} — skipping incremental load.")
        return

    engine = get_engine()
    total = 0
    print(f"Loading incremental files from {INCREMENTAL_DIR}...\n")

    for config in TABLE_CONFIG:
        csv_path = files.get(config["file"])
        if not csv_path:
            continue
        rows = load_incremental_table(engine, config, csv_path)
        total += rows
        print(f"  Appended {rows:>6,} rows -> {config['table']}")

    if total == 0:
        print("\nNo matching incremental files found.")
        return

    print(f"\nIncremental load complete ({total:,} rows appended).")
    print("Run validate_sql.py next to refresh sales_fact.")


if __name__ == "__main__":
    main()
