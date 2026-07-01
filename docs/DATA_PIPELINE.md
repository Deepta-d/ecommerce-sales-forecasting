# Data Pipeline Architecture

How the system stays up to date when **new e-commerce data arrives daily**.

## Current vs daily flow

### One-time setup (already built)

```
datasets/*.csv  →  load_csv_to_mysql.py  →  MySQL staging  →  03_sales_fact.sql  →  sales_fact
                                                                              ↓
                                                                    phase2_eda.ipynb
                                                                              ↓
                                                                    data/monthly_revenue.csv
```

Run once:

```bash
python scripts/run_pipeline.py
```

### Daily refresh (production pattern)

```
datasets/incremental/*.csv  →  load_incremental.py  →  append to staging
                                                              ↓
                                                    validate_sql.py (rebuild fact)
                                                              ↓
                                                    detect_anomalies.py
                                                              ↓
                                                    monthly_revenue.csv + Power BI
```

Run on a schedule (e.g. every morning):

```bash
python scripts/run_daily_pipeline.py
```

## Pipeline steps explained

| Step | Script | What it does |
|------|--------|----------------|
| 1. Ingest | `load_incremental.py` | Appends new CSV rows from `datasets/incremental/` into `stg_*` tables. Primary keys prevent exact duplicate rows. |
| 2. Transform | `validate_sql.py` | Re-runs `03_sales_fact.sql` — rebuilds `dim_*` and `sales_fact` from all staging data. |
| 3. Detect | `detect_anomalies.py` | Flags daily revenue spikes/drops (z-score + rolling deviation). Writes `data/daily_anomalies.csv`. |
| 4. Export | `run_daily_pipeline.py` | Refreshes `data/monthly_revenue.csv` for forecasting / dashboards. |
| 5. Forecast | `run_forecast.py` | Refreshes `data/forecasts/` (ARIMA, Prophet, LSTM comparison). |

## If new data comes daily — what happens?

1. **Export** new orders/items from your source system into CSV files (same schema as Olist).
2. **Drop** files into `datasets/incremental/` (e.g. `olist_orders_dataset.csv` with only yesterday's rows).
3. **Scheduler** runs `python scripts/run_daily_pipeline.py` at 6:00 AM.
4. **MySQL** staging grows incrementally; `sales_fact` is rebuilt so analytics always reflect full history.
5. **Anomaly script** compares the latest days against rolling baselines and logs spikes/drops.
6. **Power BI** (Phase 4) connects to `sales_fact` and refreshes after the pipeline succeeds.

## Scheduling options

**Windows Task Scheduler**

- Trigger: Daily at 6:00 AM
- Action: `python D:\E-commerce Sales forecasting\scripts\run_daily_pipeline.py`
- Start in: `D:\E-commerce Sales forecasting`

**Linux cron**

```cron
0 6 * * * cd /path/to/project && python scripts/run_daily_pipeline.py >> logs/pipeline.log 2>&1
```

## Failure handling

| Failure | Behavior |
|---------|----------|
| No incremental files | `load_incremental.py` skips; fact table still rebuilt from existing data |
| `validate_sql.py` fails | Pipeline stops — downstream dashboards keep yesterday's data |
| Duplicate `order_id` | MySQL primary key rejects duplicate insert (safe to re-run same file) |
| Anomaly on latest day | Logged in `data/daily_anomalies.csv` for business review |

## Idempotency

- Staging tables use primary keys (`order_id`, etc.) so re-processing the same incremental file does not double-count.
- `sales_fact` is fully rebuilt each run — always consistent with staging, no partial fact updates to debug.

## Folder layout

```
datasets/
  olist_*.csv              # Initial full load
  incremental/
    olist_orders_dataset.csv   # Daily delta exports (optional)
scripts/
  run_pipeline.py          # One-time full load
  run_daily_pipeline.py    # Daily refresh orchestrator
  load_incremental.py      # Append new CSVs
  detect_anomalies.py      # Spike/drop detection
  anomaly_detection.py     # Shared detection logic
data/
  monthly_revenue.csv      # Forecast input (refreshed daily)
  daily_anomalies.csv      # Flagged anomaly days
  daily_anomalies_chart.png
```
