# Phase 3: Time-Series Forecasting

Concepts and implementation notes for daily revenue forecasting (30 / 60 / 90 days).

## Objective

Forecast daily e-commerce revenue using three approaches:

1. **SARIMA** — classical statistical model
2. **Prophet** — additive trend + seasonality
3. **LSTM** — simple deep learning baseline

Compare with **MAE**, **RMSE**, and **MAPE**.

## Data

- Source: `sales_fact` via `fetch_daily_revenue()` in [`scripts/anomaly_detection.py`](../scripts/anomaly_detection.py)
- Frequency: **Daily** (resampled to continuous calendar days, missing days = 0 revenue)
- Training window starts **2017-01-01** to avoid sparse 2016 noise
- ~516 train days + 90 test days (last 90 held out)

## Hyperparameter tuning (light)

Models auto-select parameters using the **last 30 days of train** as validation (`VAL_SIZE=30`). The final 90-day test holdout is never used for tuning.

| Model | Grid | Selection criterion |
|-------|------|---------------------|
| SARIMA | 4 orders × 3 seasonal orders | Lowest AIC on fit slice (tie-break: validation MAPE) |
| Prophet | 3×2 prior scales | Lowest validation MAPE |
| Holt-Winters | additive/multiplicative × damped on/off | Lowest validation MAPE |
| LSTM | lookback ∈ {28, 35, 42} | Lowest validation MAPE on 7-day chunks |

Selected values are exposed as module constants (`SARIMA_ORDER`, `PROPHET_PARAMS`, `HW_PARAMS`, `LSTM_LOOKBACK`) after the first fit in a run.

## Stationarity

A **stationary** series has constant mean and variance over time.

- **ADF test** (Augmented Dickey-Fuller): p-value < 0.05 → stationary
- Raw daily revenue is **non-stationary** (upward trend)
- **First difference** is closer to stationary → motivates `d=1` in ARIMA(1,1,1)

```python
from statsmodels.tsa.stattools import adfuller
adfuller(series)          # non-stationary
adfuller(series.diff())   # often stationary
```

## Train-Test Split (Time-Based)

**Never shuffle** time series data.

| Set | Definition |
|-----|------------|
| Train | All days except last 90 |
| Test | Last 90 days |

Evaluate forecasts at horizons **30**, **60**, and **90** days by comparing the first N steps of the 90-day forecast to actuals.

## Rolling Forecast

**Walk-forward** evaluation simulates production:

1. Fit model on history
2. Forecast next 7 days
3. Observe actuals, append to history
4. Re-fit and repeat

Implemented for SARIMA in `rolling_forecast_arima()` with 7-day steps.

## Models

### SARIMA

- Default fallback: `(1, 1, 1)` × `(1, 1, 1, 7)` — weekly seasonality on daily data
- Tuned from grid: orders `(1,1,1)`, `(2,1,1)`, `(1,1,2)`, `(0,1,1)` and seasonal `(1,1,1,7)`, `(0,1,1,7)`, `(1,1,0,7)`
- Library: `statsmodels.SARIMAX`

### Prophet

- `weekly_seasonality=True`, `yearly_seasonality=True` when train > 365 days
- Tuned priors: `changepoint_prior_scale` ∈ {0.05, 0.1, 0.5}, `seasonality_prior_scale` ∈ {5, 10}
- Components plot shows trend + seasonal decomposition
- **Windows fallback:** If Stan/cmdstan crashes (or HW wins validation), uses tuned Holt-Winters (`seasonal` add/mul, `damped_trend` True/False)

### LSTM

- Features per day: scaled revenue + cyclical day-of-week (sin/cos)
- Architecture: LSTM(64) → Dropout(0.2) → Dense(7)
- **7-day direct forecast chunks** (13 chunks for 90 days) instead of recursive 1-step prediction
- Lookback tuned from {28, 35, 42}; up to 80 epochs with early stopping (patience=8)

## Metrics

| Metric | Formula | Business meaning |
|--------|---------|------------------|
| MAE | mean(\|actual − forecast\|) | Average error in BRL |
| RMSE | sqrt(mean((actual − forecast)²)) | Penalizes large misses (spikes) |
| MAPE | mean(\|error / actual\|) × 100 | % error (zeros excluded) |

## Expected comparison

On Olist daily revenue (with light validation tuning):

- **Prophet / Holt-Winters** often strongest at 30–60 days when weekly seasonality dominates
- **SARIMA** competitive when weekly pattern is strong; params auto-selected from grid
- **LSTM** uses calendar features + 7-day chunks so the forecast line tracks weekly rhythm (not a flat recursive mean)

Spike days (e.g. 2017-11-24 Black Friday) inflate RMSE for all models.

## Run

```bash
# Notebook
jupyter notebook notebooks/phase3_forecasting.ipynb

# CLI (exports CSVs + chart)
python scripts/run_forecast.py
```

## Outputs

| File | Purpose |
|------|---------|
| `data/forecasts/model_comparison.csv` | MAE/RMSE/MAPE by model and horizon |
| `data/forecasts/forecast_vs_actual.csv` | Overlay data for Power BI |
| `data/forecasts/*_forecast_90d.csv` | Per-model forecasts |
| `data/forecasts/forecast_vs_actual.png` | Comparison chart |

## Phase 4 handoff

Import `forecast_vs_actual.csv` and `model_comparison.csv` into Power BI for the "Forecast vs actual" dashboard page.
