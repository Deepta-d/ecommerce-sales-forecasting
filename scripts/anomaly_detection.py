"""Daily revenue anomaly detection (z-score and rolling deviation)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sqlalchemy import text

from db_utils import get_engine

ZSCORE_THRESHOLD = 2.0
ROLLING_WINDOW = 7
ROLLING_THRESHOLD = 2.0


def fetch_daily_revenue() -> pd.DataFrame:
    """Load daily revenue and order counts from sales_fact."""
    engine = get_engine()
    daily = pd.read_sql(
        text(
            """
            SELECT
                order_date,
                SUM(total_revenue) AS revenue,
                COUNT(DISTINCT order_id) AS orders
            FROM sales_fact
            GROUP BY order_date
            ORDER BY order_date
            """
        ),
        engine,
    )
    daily["order_date"] = pd.to_datetime(daily["order_date"])
    daily["revenue"] = daily["revenue"].astype(float)
    return daily


def detect_anomalies(
    daily: pd.DataFrame,
    z_threshold: float = ZSCORE_THRESHOLD,
    rolling_window: int = ROLLING_WINDOW,
    rolling_threshold: float = ROLLING_THRESHOLD,
) -> pd.DataFrame:
    """
    Flag daily revenue spikes and drops using:
    - Global z-score
    - Rolling mean/std deviation (adapts to growth trends)
    """
    result = daily.copy().sort_values("order_date").reset_index(drop=True)

    mean_rev = result["revenue"].mean()
    std_rev = result["revenue"].std()
    result["z_score"] = (result["revenue"] - mean_rev) / std_rev
    result["is_anomaly_zscore"] = result["z_score"].abs() > z_threshold

    result["rolling_mean"] = (
        result["revenue"].rolling(rolling_window, min_periods=3).mean()
    )
    result["rolling_std"] = (
        result["revenue"].rolling(rolling_window, min_periods=3).std()
    )
    result["rolling_z"] = (
        (result["revenue"] - result["rolling_mean"]) / result["rolling_std"]
    )
    result["pct_from_rolling"] = (
        (result["revenue"] - result["rolling_mean"]) / result["rolling_mean"] * 100
    )
    result["is_anomaly_rolling"] = result["rolling_z"].abs() > rolling_threshold

    result["is_anomaly"] = result["is_anomaly_zscore"] | result["is_anomaly_rolling"]
    result["anomaly_type"] = np.where(
        ~result["is_anomaly"],
        "normal",
        np.where(result["revenue"] > result["rolling_mean"], "spike", "drop"),
    )

    return result


def get_top_anomalies(daily_flagged: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Return top anomaly days ranked by absolute z-score."""
    anomalies = daily_flagged[daily_flagged["is_anomaly"]].copy()
    anomalies["abs_z"] = anomalies["z_score"].abs()
    cols = [
        "order_date",
        "revenue",
        "orders",
        "z_score",
        "rolling_z",
        "pct_from_rolling",
        "anomaly_type",
        "is_anomaly_zscore",
        "is_anomaly_rolling",
    ]
    return anomalies.sort_values("abs_z", ascending=False).head(n)[cols]
