"""Run Phase 3 forecasting models and export results."""

from __future__ import annotations

from dotenv import load_dotenv

from forecast_utils import (
    FORECAST_DIR,
    HORIZONS,
    TEST_SIZE,
    adf_test,
    best_model_at_horizon,
    load_daily_series,
    run_all_models,
    save_forecast_outputs,
    time_series_split,
)

load_dotenv()


def main() -> None:
    print("Phase 3: Time-Series Forecasting\n")
    series = load_daily_series()
    print(f"  Daily observations: {len(series):,}")
    print(f"  Date range: {series.index.min().date()} to {series.index.max().date()}")

    adf_raw = adf_test(series, "raw revenue")
    adf_diff = adf_test(series.diff().dropna(), "first difference")
    print(f"\n  ADF (raw) p-value: {adf_raw['p_value']:.4f} stationary={adf_raw['is_stationary']}")
    print(f"  ADF (diff) p-value: {adf_diff['p_value']:.4f} stationary={adf_diff['is_stationary']}")

    train, test, forecasts, comparison = run_all_models(series)
    save_forecast_outputs(test, forecasts, comparison, train)

    print(f"\n  Train size: {len(train):,} | Test size: {len(test):,} (last {TEST_SIZE} days)")
    print("\nModel comparison (MAE / RMSE / MAPE):\n")
    print(comparison.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    winner = best_model_at_horizon(comparison, horizon=90)
    print(f"\nBest model at 90-day horizon (lowest MAPE): {winner}")
    print(f"\nOutputs saved to {FORECAST_DIR}")


if __name__ == "__main__":
    main()
