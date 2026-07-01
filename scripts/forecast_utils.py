"""Time-series forecasting utilities for Phase 3."""

from __future__ import annotations

import warnings
from math import sqrt
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import MinMaxScaler
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.statespace.sarimax import SARIMAX

from anomaly_detection import fetch_daily_revenue

warnings.filterwarnings("ignore")

HORIZONS = [30, 60, 90]
TEST_SIZE = 90
VAL_SIZE = 30
TRAIN_START = "2017-01-01"
FORECAST_DIR = Path(__file__).resolve().parent.parent / "data" / "forecasts"

# Selected hyperparameters (updated during tuning)
DEFAULT_SARIMA_ORDER = (1, 1, 1)
DEFAULT_SARIMA_SEASONAL = (1, 1, 1, 7)
SARIMA_ORDER = DEFAULT_SARIMA_ORDER
SARIMA_SEASONAL = DEFAULT_SARIMA_SEASONAL
PROPHET_PARAMS: dict[str, Any] = {
    "changepoint_prior_scale": 0.05,
    "seasonality_prior_scale": 10.0,
}
HW_PARAMS: dict[str, Any] = {"seasonal": "add", "damped_trend": False}
PROPHET_BACKEND = "prophet"
DEFAULT_LSTM_LOOKBACK = 35
LSTM_LOOKBACK = DEFAULT_LSTM_LOOKBACK
LSTM_EPOCHS = 80
LSTM_UNITS = 64
FORECAST_CHUNK = 7
ROLLING_STEP = 7

SARIMA_ORDER_GRID = [(1, 1, 1), (2, 1, 1), (1, 1, 2), (0, 1, 1)]
SARIMA_SEASONAL_GRID = [(1, 1, 1, 7), (0, 1, 1, 7), (1, 1, 0, 7)]
PROPHET_CP_GRID = [0.05, 0.1, 0.5]
PROPHET_SP_GRID = [5.0, 10.0]
HW_SEASONAL_GRID = ["add", "mul"]
HW_DAMPED_GRID = [True, False]
LSTM_LOOKBACK_GRID = [28, 35, 42]

_tuning_state: dict[str, bool] = {"arima": False, "prophet": False, "lstm": False}


def reset_tuning_state() -> None:
    """Reset tuning flags so the next run re-selects hyperparameters."""
    for key in _tuning_state:
        _tuning_state[key] = False


def load_daily_series(train_start: str | None = TRAIN_START) -> pd.Series:
    """Load daily revenue, resample to continuous daily index, return y series."""
    daily = fetch_daily_revenue()
    daily = daily.set_index("order_date").sort_index()
    series = daily["revenue"].resample("D").sum().fillna(0.0)
    series.name = "y"
    if train_start:
        series = series[series.index >= pd.Timestamp(train_start)]
    return series


def adf_test(series: pd.Series, title: str = "series") -> dict[str, Any]:
    """Augmented Dickey-Fuller test for stationarity."""
    result = adfuller(series.dropna(), autolag="AIC")
    return {
        "title": title,
        "adf_statistic": result[0],
        "p_value": result[1],
        "used_lags": result[2],
        "n_obs": result[3],
        "is_stationary": result[1] < 0.05,
    }


def time_series_split(series: pd.Series, test_size: int = TEST_SIZE):
    train = series.iloc[:-test_size]
    test = series.iloc[-test_size:]
    return train, test


def _train_val_split(train: pd.Series, val_size: int = VAL_SIZE):
    """Split train into fit + validation (last val_size days)."""
    if len(train) <= val_size + 14:
        return train, train.iloc[0:0]
    return train.iloc[:-val_size], train.iloc[-val_size:]


def _validation_mape(val_series: pd.Series, preds: np.ndarray) -> float:
    m = evaluate_forecast(val_series.values, np.asarray(preds, dtype=float))
    return float(m["MAPE"])


def evaluate_forecast(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """MAE, RMSE, MAPE — excludes zero actuals for MAPE."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mae = mean_absolute_error(y_true, y_pred)
    rmse = sqrt(mean_squared_error(y_true, y_pred))
    mask = y_true != 0
    if mask.any():
        mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
    else:
        mape = float("nan")
    return {"MAE": mae, "RMSE": rmse, "MAPE": mape}


def metrics_at_horizons(
    y_true: pd.Series,
    y_pred: np.ndarray,
    horizons: list[int] = HORIZONS,
    model_name: str = "model",
) -> pd.DataFrame:
    rows = []
    for h in horizons:
        m = evaluate_forecast(y_true.iloc[:h].values, y_pred[:h])
        rows.append({"model": model_name, "horizon": h, **m})
    return pd.DataFrame(rows)


def _fit_sarima_forecast(
    train: pd.Series,
    steps: int,
    order: tuple[int, int, int],
    seasonal_order: tuple[int, int, int, int],
) -> np.ndarray | None:
    try:
        model = SARIMAX(
            train,
            order=order,
            seasonal_order=seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        fit = model.fit(disp=False)
        return fit.forecast(steps=steps).values
    except Exception:
        return None


def _select_sarima_params(train: pd.Series) -> tuple[tuple[int, int, int], tuple[int, int, int, int]]:
    """Light grid search on train fit slice; select lowest AIC (tie-break: validation MAPE)."""
    global SARIMA_ORDER, SARIMA_SEASONAL

    fit_series, val_series = _train_val_split(train)
    if len(val_series) == 0:
        return SARIMA_ORDER, SARIMA_SEASONAL

    best_aic = float("inf")
    best_mape = float("inf")
    best_order = DEFAULT_SARIMA_ORDER
    best_seasonal = DEFAULT_SARIMA_SEASONAL

    for order in SARIMA_ORDER_GRID:
        for seasonal in SARIMA_SEASONAL_GRID:
            try:
                model = SARIMAX(
                    fit_series,
                    order=order,
                    seasonal_order=seasonal,
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                )
                fit = model.fit(disp=False)
                preds = fit.forecast(steps=len(val_series)).values
                mape = _validation_mape(val_series, preds)
                aic = fit.aic
                if aic < best_aic or (aic == best_aic and mape < best_mape):
                    best_aic = aic
                    best_mape = mape
                    best_order = order
                    best_seasonal = seasonal
            except Exception:
                continue

    SARIMA_ORDER, SARIMA_SEASONAL = best_order, best_seasonal
    return best_order, best_seasonal


def forecast_arima(train: pd.Series, steps: int = TEST_SIZE) -> np.ndarray:
    global SARIMA_ORDER, SARIMA_SEASONAL

    if not _tuning_state["arima"]:
        _select_sarima_params(train)
        _tuning_state["arima"] = True

    preds = _fit_sarima_forecast(train, steps, SARIMA_ORDER, SARIMA_SEASONAL)
    if preds is None:
        preds = _fit_sarima_forecast(train, steps, (1, 1, 1), (1, 1, 1, 7))
    if preds is None:
        raise RuntimeError("SARIMA fit failed for all parameter combinations.")
    return preds


def _forecast_holt_winters(
    train: pd.Series,
    steps: int,
    seasonal: str = "add",
    damped_trend: bool = False,
) -> np.ndarray:
    """Holt-Winters fallback when Prophet/Stan is unavailable."""
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    trend = "add"
    model = ExponentialSmoothing(
        train,
        trend=trend,
        damped_trend=damped_trend,
        seasonal=seasonal,
        seasonal_periods=7,
        initialization_method="estimated",
    )
    fit = model.fit(optimized=True)
    return fit.forecast(steps).values


def _forecast_prophet_with_params(
    train: pd.Series,
    steps: int,
    changepoint_prior_scale: float,
    seasonality_prior_scale: float,
) -> np.ndarray:
    from prophet import Prophet

    train_df = train.reset_index()
    train_df.columns = ["ds", "y"]
    model = Prophet(
        weekly_seasonality=True,
        yearly_seasonality=len(train) > 365,
        daily_seasonality=False,
        n_changepoints=15,
        changepoint_prior_scale=changepoint_prior_scale,
        seasonality_prior_scale=seasonality_prior_scale,
    )
    model.fit(train_df)
    future = model.make_future_dataframe(periods=steps, freq="D", include_history=False)
    forecast = model.predict(future)
    return forecast["yhat"].values


def _prophet_available(train: pd.Series) -> bool:
    try:
        _forecast_prophet_with_params(train, min(7, len(train)), 0.05, 10.0)
        return True
    except Exception:
        return False


def _select_prophet_or_hw_params(train: pd.Series) -> None:
    """Select Prophet priors or Holt-Winters seasonal/damped via validation MAPE."""
    global PROPHET_PARAMS, HW_PARAMS, PROPHET_BACKEND

    fit_series, val_series = _train_val_split(train)
    if len(val_series) == 0:
        return

    best_mape = float("inf")
    prophet_ok = _prophet_available(fit_series)

    if prophet_ok:
        for cp in PROPHET_CP_GRID:
            for sp in PROPHET_SP_GRID:
                try:
                    preds = _forecast_prophet_with_params(
                        fit_series, len(val_series), cp, sp
                    )
                    mape = _validation_mape(val_series, preds)
                    if mape < best_mape:
                        best_mape = mape
                        PROPHET_PARAMS = {
                            "changepoint_prior_scale": cp,
                            "seasonality_prior_scale": sp,
                        }
                        PROPHET_BACKEND = "prophet"
                except Exception:
                    continue

    for seasonal in HW_SEASONAL_GRID:
        for damped in HW_DAMPED_GRID:
            try:
                preds = _forecast_holt_winters(
                    fit_series, len(val_series), seasonal=seasonal, damped_trend=damped
                )
                mape = _validation_mape(val_series, preds)
                if mape < best_mape:
                    best_mape = mape
                    HW_PARAMS = {"seasonal": seasonal, "damped_trend": damped}
                    PROPHET_BACKEND = "hw"
            except Exception:
                continue


def forecast_prophet(train: pd.Series, steps: int = TEST_SIZE) -> np.ndarray:
    if not _tuning_state["prophet"]:
        _select_prophet_or_hw_params(train)
        _tuning_state["prophet"] = True

    if PROPHET_BACKEND == "hw":
        return _forecast_holt_winters(
            train,
            steps,
            seasonal=HW_PARAMS["seasonal"],
            damped_trend=HW_PARAMS["damped_trend"],
        )

    try:
        return _forecast_prophet_with_params(
            train,
            steps,
            PROPHET_PARAMS["changepoint_prior_scale"],
            PROPHET_PARAMS["seasonality_prior_scale"],
        )
    except Exception as exc:
        print(f"Prophet unavailable ({exc.__class__.__name__}); using Holt-Winters fallback.")
        return _forecast_holt_winters(
            train,
            steps,
            seasonal=HW_PARAMS["seasonal"],
            damped_trend=HW_PARAMS["damped_trend"],
        )


def fit_prophet_model(train: pd.Series):
    """Return fitted Prophet model, or None if Stan backend fails."""
    if not _tuning_state["prophet"]:
        _select_prophet_or_hw_params(train)
        _tuning_state["prophet"] = True

    try:
        from prophet import Prophet

        train_df = train.reset_index()
        train_df.columns = ["ds", "y"]
        model = Prophet(
            weekly_seasonality=True,
            yearly_seasonality=len(train) > 365,
            daily_seasonality=False,
            n_changepoints=15,
            changepoint_prior_scale=PROPHET_PARAMS["changepoint_prior_scale"],
            seasonality_prior_scale=PROPHET_PARAMS["seasonality_prior_scale"],
        )
        model.fit(train_df)
        return model
    except Exception:
        return None


def plot_seasonal_components(train: pd.Series) -> None:
    """Trend/seasonality plot when Prophet components are unavailable."""
    from statsmodels.tsa.seasonal import seasonal_decompose

    decomp = seasonal_decompose(train, model="additive", period=7, extrapolate_trend="freq")
    decomp.plot()
    plt.tight_layout()


def _dow_features(index: pd.DatetimeIndex) -> np.ndarray:
    dow = index.dayofweek.astype(float)
    angle = 2 * np.pi * dow / 7.0
    return np.column_stack([np.sin(angle), np.cos(angle)])


def _build_lstm_feature_matrix(
    revenues_scaled: np.ndarray,
    dates: pd.DatetimeIndex,
) -> np.ndarray:
    dow = _dow_features(dates)
    return np.column_stack([revenues_scaled, dow[:, 0], dow[:, 1]])


def _build_lstm_chunk_sequences(
    features: np.ndarray,
    revenues_scaled: np.ndarray,
    lookback: int,
    chunk: int,
) -> tuple[np.ndarray, np.ndarray]:
    xs, ys = [], []
    for i in range(lookback, len(revenues_scaled) - chunk + 1):
        xs.append(features[i - lookback : i])
        ys.append(revenues_scaled[i : i + chunk])
    return np.array(xs), np.array(ys)


def _fit_lstm_model(
    x_train: np.ndarray,
    y_train: np.ndarray,
    lookback: int,
    chunk: int,
    epochs: int = LSTM_EPOCHS,
) -> Any:
    import tensorflow as tf

    val_size = max(1, int(len(x_train) * 0.15))
    x_fit, x_val = x_train[:-val_size], x_train[-val_size:]
    y_fit, y_val = y_train[:-val_size], y_train[-val_size:]

    model = tf.keras.Sequential(
        [
            tf.keras.layers.LSTM(LSTM_UNITS, input_shape=(lookback, 3)),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(chunk),
        ]
    )
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3), loss="mse")
    model.fit(
        x_fit,
        y_fit,
        validation_data=(x_val, y_val),
        epochs=epochs,
        batch_size=32,
        verbose=0,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(
                patience=8, restore_best_weights=True, monitor="val_loss"
            )
        ],
    )
    return model


def _lstm_chunk_forecast(
    model: Any,
    train: pd.Series,
    scaler: MinMaxScaler,
    lookback: int,
    steps: int,
    future_index: pd.DatetimeIndex | None = None,
) -> np.ndarray:
    if future_index is None:
        last_date = train.index[-1]
        future_index = pd.date_range(
            start=last_date + pd.Timedelta(days=1), periods=steps, freq="D"
        )

    history_scaled = scaler.transform(train.values.reshape(-1, 1)).flatten().tolist()
    history_dates: list[pd.Timestamp] = list(train.index)
    preds_scaled: list[float] = []
    future_ptr = 0

    while len(preds_scaled) < steps:
        chunk_len = min(FORECAST_CHUNK, steps - len(preds_scaled))
        window_rev = np.array(history_scaled[-lookback:])
        window_dates = pd.DatetimeIndex(history_dates[-lookback:])
        features = _build_lstm_feature_matrix(window_rev, window_dates)
        x = features.reshape(1, lookback, 3)
        chunk_pred = model.predict(x, verbose=0)[0][:chunk_len]
        chunk_dates = future_index[future_ptr : future_ptr + chunk_len]
        future_ptr += chunk_len
        for val, dt in zip(chunk_pred[:chunk_len], chunk_dates):
            preds_scaled.append(float(val))
            history_scaled.append(float(val))
            history_dates.append(dt)

    return scaler.inverse_transform(np.array(preds_scaled[:steps]).reshape(-1, 1)).flatten()


def _select_lstm_lookback(train: pd.Series) -> int:
    """Pick lookback from grid using validation MAPE on 7-day chunked forecast."""
    global LSTM_LOOKBACK

    fit_series, val_series = _train_val_split(train)
    if len(val_series) == 0:
        return LSTM_LOOKBACK

    best_mape = float("inf")
    best_lookback = DEFAULT_LSTM_LOOKBACK
    baseline_mape = float("inf")

    for lookback in LSTM_LOOKBACK_GRID:
        try:
            scaler = MinMaxScaler()
            scaled = scaler.fit_transform(fit_series.values.reshape(-1, 1)).flatten()
            features = _build_lstm_feature_matrix(scaled, fit_series.index)
            x_train, y_train = _build_lstm_chunk_sequences(
                features, scaled, lookback, FORECAST_CHUNK
            )
            if len(x_train) < 20:
                continue
            model = _fit_lstm_model(x_train, y_train, lookback, FORECAST_CHUNK, epochs=40)
            preds = _lstm_chunk_forecast(
                model,
                fit_series,
                scaler,
                lookback,
                len(val_series),
                future_index=val_series.index,
            )
            mape = _validation_mape(val_series, preds)
            if lookback == DEFAULT_LSTM_LOOKBACK:
                baseline_mape = mape
            if mape < best_mape:
                best_mape = mape
                best_lookback = lookback
        except Exception:
            continue

    if baseline_mape < float("inf") and best_mape > baseline_mape - 1.0:
        best_lookback = DEFAULT_LSTM_LOOKBACK

    LSTM_LOOKBACK = best_lookback
    return best_lookback


def forecast_lstm(train: pd.Series, steps: int = TEST_SIZE) -> np.ndarray:
    import tensorflow as tf

    tf.get_logger().setLevel("ERROR")

    if not _tuning_state["lstm"]:
        _select_lstm_lookback(train)
        _tuning_state["lstm"] = True

    lookback = LSTM_LOOKBACK
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(train.values.reshape(-1, 1)).flatten()
    features = _build_lstm_feature_matrix(scaled, train.index)
    x_train, y_train = _build_lstm_chunk_sequences(
        features, scaled, lookback, FORECAST_CHUNK
    )
    model = _fit_lstm_model(x_train, y_train, lookback, FORECAST_CHUNK)
    return _lstm_chunk_forecast(model, train, scaler, lookback, steps)


def rolling_forecast_arima(
    train: pd.Series,
    test: pd.Series,
    step: int = ROLLING_STEP,
) -> pd.Series:
    """Walk-forward forecast: refit SARIMA every `step` days."""
    history = train.copy()
    preds = []
    dates = []
    for start in range(0, len(test), step):
        end = min(start + step, len(test))
        horizon = end - start
        fc = forecast_arima(history, steps=horizon)
        preds.extend(fc)
        dates.extend(test.index[start:end])
        history = pd.concat([history, test.iloc[start:end]])
    return pd.Series(preds, index=dates, name="rolling_arima")


def run_all_models(
    series: pd.Series | None = None,
    test_size: int = TEST_SIZE,
) -> tuple[pd.Series, pd.Series, dict[str, np.ndarray], pd.DataFrame]:
    """Train all models and return train, test, forecasts dict, comparison table."""
    reset_tuning_state()
    if series is None:
        series = load_daily_series()
    train, test = time_series_split(series, test_size)

    forecasts = {
        "ARIMA": forecast_arima(train, steps=test_size),
        "Prophet": forecast_prophet(train, steps=test_size),
        "LSTM": forecast_lstm(train, steps=test_size),
    }

    comparison_parts = [
        metrics_at_horizons(test, preds, model_name=name)
        for name, preds in forecasts.items()
    ]
    comparison = pd.concat(comparison_parts, ignore_index=True)
    return train, test, forecasts, comparison


def save_forecast_outputs(
    test: pd.Series,
    forecasts: dict[str, np.ndarray],
    comparison: pd.DataFrame,
    train: pd.Series | None = None,
) -> Path:
    FORECAST_DIR.mkdir(parents=True, exist_ok=True)

    comparison.to_csv(FORECAST_DIR / "model_comparison.csv", index=False)

    for name, preds in forecasts.items():
        slug = name.lower()
        out = pd.DataFrame(
            {
                "date": test.index,
                "actual": test.values,
                "forecast": preds,
            }
        )
        out.to_csv(FORECAST_DIR / f"{slug}_forecast_90d.csv", index=False)

    overlay = pd.DataFrame({"date": test.index, "actual": test.values})
    for name, preds in forecasts.items():
        overlay[name] = preds
    overlay.to_csv(FORECAST_DIR / "forecast_vs_actual.csv", index=False)

    plot_forecast_comparison(test, forecasts, FORECAST_DIR / "forecast_vs_actual.png")
    return FORECAST_DIR


def plot_forecast_comparison(
    test: pd.Series,
    forecasts: dict[str, np.ndarray],
    out_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(test.index, test.values, label="Actual", linewidth=2, color="black")
    colors = {"ARIMA": "steelblue", "Prophet": "darkorange", "LSTM": "seagreen"}
    for name, preds in forecasts.items():
        ax.plot(test.index, preds, label=name, alpha=0.85, color=colors.get(name))
    ax.set_title("90-Day Forecast vs Actual (Test Set)")
    ax.set_ylabel("Revenue (BRL)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def best_model_at_horizon(comparison: pd.DataFrame, horizon: int = 90) -> str:
    subset = comparison[comparison["horizon"] == horizon].copy()
    subset = subset.sort_values("MAPE")
    return subset.iloc[0]["model"]
