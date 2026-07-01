"""Full Phase 1 pipeline: setup DB, load CSVs, build fact table, validate."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pymysql
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = PROJECT_ROOT / "scripts"
load_dotenv(PROJECT_ROOT / ".env", override=True)


def app_user_ready() -> bool:
    try:
        conn = pymysql.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER", "olist_user"),
            password=os.getenv("DB_PASSWORD", "olist_pass"),
            database=os.getenv("DB_NAME", "olist_analytics"),
            connect_timeout=3,
        )
        conn.close()
        return True
    except pymysql.Error:
        return False


def run_script(name: str) -> None:
    path = SCRIPTS / name
    print(f"\n{'=' * 60}\n>>> {name}\n{'=' * 60}")
    result = subprocess.run(
        [sys.executable, "-u", str(path)], cwd=str(PROJECT_ROOT)
    )
    if result.returncode != 0:
        print(f"\nPipeline stopped: {name} failed (exit {result.returncode})")
        sys.exit(result.returncode)


def main() -> None:
    env_file = PROJECT_ROOT / ".env"
    example_file = PROJECT_ROOT / ".env.example"

    if not env_file.exists() and example_file.exists():
        import shutil

        shutil.copy(example_file, env_file)
        print("Created .env from .env.example")
        print("IMPORTANT: Set MYSQL_ROOT_PASSWORD in .env before first run.\n")

    steps = ["load_csv_to_mysql.py", "validate_sql.py"]
    if app_user_ready():
        print("Application user connected — skipping database setup.")
    else:
        steps = ["setup_mysql.py"] + steps

    for step in steps:
        run_script(step)

    print("\n" + "=" * 60)
    print("Phase 1 pipeline complete.")
    print("Next: open notebooks/phase2_eda.ipynb for Phase 2 analysis.")
    print("=" * 60)


if __name__ == "__main__":
    main()
