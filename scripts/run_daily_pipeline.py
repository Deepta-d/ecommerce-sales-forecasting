"""Daily refresh pipeline: incremental load, fact rebuild, anomaly check."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = PROJECT_ROOT / "scripts"
load_dotenv(PROJECT_ROOT / ".env", override=True)


def run_script(name: str, required: bool = True) -> None:
    path = SCRIPTS / name
    print(f"\n{'=' * 60}\n>>> {name}\n{'=' * 60}")
    result = subprocess.run(
        [sys.executable, "-u", str(path)], cwd=str(PROJECT_ROOT)
    )
    if result.returncode != 0:
        if required:
            print(f"\nPipeline stopped: {name} failed (exit {result.returncode})")
            sys.exit(result.returncode)
        print(f"\nWarning: {name} failed (exit {result.returncode}) — continuing.")


def export_monthly_revenue() -> None:
    """Refresh monthly_revenue.csv for forecasting."""
    sys.path.insert(0, str(SCRIPTS))
    from anomaly_detection import fetch_daily_revenue

    daily = fetch_daily_revenue()
    daily = daily.set_index("order_date")
    monthly = (
        daily.resample("ME")
        .agg(revenue=("revenue", "sum"), orders=("orders", "sum"))
        .reset_index()
    )
    monthly["aov"] = monthly["revenue"] / monthly["orders"]
    out = PROJECT_ROOT / "data" / "monthly_revenue.csv"
    out.parent.mkdir(exist_ok=True)
    monthly.to_csv(out, index=False)
    print(f"\nExported {out}")


def main() -> None:
    print("Daily E-Commerce Analytics Pipeline")
    print("=" * 60)
    print(
        "Flow: incremental CSVs -> refresh sales_fact -> anomaly check -> export\n"
        "See docs/DATA_PIPELINE.md for architecture details.\n"
    )

    # Optional: append new rows from datasets/incremental/
    run_script("load_incremental.py", required=False)

    # Rebuild dimensions + sales_fact from staging
    run_script("validate_sql.py", required=True)

    # Flag unusual daily sales
    run_script("detect_anomalies.py", required=True)

    # Update forecast input
    export_monthly_revenue()

    # Refresh forecasts (optional — can be slow)
    run_script("run_forecast.py", required=False)

    # Phase 4 — Power BI CSV exports
    run_script("export_powerbi_data.py", required=False)

    print("\n" + "=" * 60)
    print("Daily pipeline complete.")
    print("Next: refresh Power BI Desktop (data/powerbi/) — see docs/PHASE4_POWERBI.md")
    print("=" * 60)


if __name__ == "__main__":
    main()
