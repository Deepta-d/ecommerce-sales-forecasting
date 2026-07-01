"""Detect and report daily sales anomalies (spikes/drops)."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from dotenv import load_dotenv

from anomaly_detection import detect_anomalies, fetch_daily_revenue, get_top_anomalies

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
load_dotenv(PROJECT_ROOT / ".env", override=True)


def export_results(daily_flagged: pd.DataFrame) -> Path:
    DATA_DIR.mkdir(exist_ok=True)
    out_path = DATA_DIR / "daily_anomalies.csv"
    daily_flagged.to_csv(out_path, index=False)
    return out_path


def plot_anomalies(daily_flagged: pd.DataFrame) -> Path:
    DATA_DIR.mkdir(exist_ok=True)
    out_path = DATA_DIR / "daily_anomalies_chart.png"

    anomalies = daily_flagged[daily_flagged["is_anomaly"]]
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(
        daily_flagged["order_date"],
        daily_flagged["revenue"],
        linewidth=0.8,
        alpha=0.8,
        label="Daily revenue",
    )
    spikes = anomalies[anomalies["anomaly_type"] == "spike"]
    drops = anomalies[anomalies["anomaly_type"] == "drop"]
    ax.scatter(
        spikes["order_date"],
        spikes["revenue"],
        color="green",
        s=40,
        zorder=3,
        label="Spike",
    )
    ax.scatter(
        drops["order_date"],
        drops["revenue"],
        color="red",
        s=40,
        zorder=3,
        label="Drop",
    )
    ax.set_title("Daily Revenue with Detected Anomalies")
    ax.set_ylabel("Revenue (BRL)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def main() -> None:
    daily = fetch_daily_revenue()
    flagged = detect_anomalies(daily)
    top = get_top_anomalies(flagged, n=10)

    spike_count = (flagged["anomaly_type"] == "spike").sum()
    drop_count = (flagged["anomaly_type"] == "drop").sum()

    print("Daily Sales Anomaly Detection\n")
    print(f"  Days analyzed:     {len(flagged):,}")
    print(f"  Anomalies found:   {flagged['is_anomaly'].sum():,}")
    print(f"    Spikes:          {spike_count:,}")
    print(f"    Drops:           {drop_count:,}")
    print("\nTop 10 anomaly days:\n")
    print(top.to_string(index=False))

    csv_path = export_results(flagged)
    chart_path = plot_anomalies(flagged)
    print(f"\nExported: {csv_path}")
    print(f"Chart:    {chart_path}")

    if flagged["is_anomaly"].sum() == 0:
        print("\nNo anomalies detected at current thresholds.")
        sys.exit(0)


if __name__ == "__main__":
    main()
