# E-Commerce Sales Forecasting & Intelligent Reporting

Phase 1 (SQL) and Phase 2 (Python EDA) implementation using the Olist Brazilian E-Commerce dataset.

## Quick Start

### 1. Download data

Get the Olist CSVs from [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and place them in `datasets/` (see [datasets/README.md](datasets/README.md)).

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure MySQL

Copy `.env.example` to `.env` and set your MySQL root password:

```
MYSQL_ROOT_PASSWORD=your_root_password
```

### 4. Run Phase 1 pipeline

```bash
python scripts/run_pipeline.py
```

This will:
- Create `olist_analytics` database and `olist_user`
- Load 8 CSV files into staging tables
- Build dimension tables and `sales_fact`
- Validate row counts

**Manual alternative:** Run `sql/01_create_database.sql` in MySQL Workbench as root, then:

```bash
python scripts/load_csv_to_mysql.py
python scripts/validate_sql.py
```

### 5. Run Phase 2 analysis

Open `notebooks/phase2_eda.ipynb` in Jupyter, or:

```bash
jupyter notebook notebooks/phase2_eda.ipynb
```

### 6. Cross-validate

```bash
python scripts/cross_validate.py
```

### 7. Anomaly detection

```bash
python scripts/detect_anomalies.py
```

Outputs `data/daily_anomalies.csv` and `data/daily_anomalies_chart.png`.

### 8. Daily pipeline (when new data arrives)

```bash
python scripts/run_daily_pipeline.py
```

See [docs/DATA_PIPELINE.md](docs/DATA_PIPELINE.md) for architecture.

### 9. Phase 3 forecasting

```bash
python scripts/run_forecast.py
```

Or open `notebooks/phase3_forecasting.ipynb` for ARIMA, Prophet, LSTM comparison. Models use **light validation-based tuning** (last 30 train days) for SARIMA orders, Prophet/Holt-Winters priors, and LSTM lookback.

See [docs/PHASE3_FORECASTING.md](docs/PHASE3_FORECASTING.md) for concepts (stationarity, rolling forecast, metrics).

**Prophet on Windows:** If Stan/cmdstan fails (common on Python 3.13), the code automatically falls back to **additive Holt-Winters** (weekly seasonality) while keeping the Prophet API in the notebook. Components plot uses `seasonal_decompose` when Prophet is unavailable.

### 10. Phase 4 — Power BI dashboard

```bash
python scripts/export_powerbi_data.py
python scripts/validate_powerbi_export.py
python scripts/generate_powerbi_pbip.py
```

Open `powerbi/Olist_Ecommerce_Dashboard.pbip` in **Power BI Desktop**, apply `powerbi/theme/OlistFuturistic.json`, build pages per [docs/PHASE4_POWERBI.md](docs/PHASE4_POWERBI.md), then **Save As** `powerbi/Olist_Ecommerce_Dashboard.pbix`.

## Project Structure

```
datasets/          # Olist CSV files (source data)
  incremental/     # Daily delta CSV exports (optional)
docs/              # Pipeline + forecasting + Power BI documentation
sql/               # Phase 1 DDL and analytical queries
scripts/           # Pipeline, loader, validation, forecasting, Power BI export
notebooks/         # Phase 2 EDA + Phase 3 forecasting notebooks
powerbi/           # PBIP project, theme, DAX, assets
data/
  powerbi/         # CSV exports for Power BI Import mode
  forecasts/       # model_comparison.csv, forecast_vs_actual.csv
  monthly_revenue.csv
  daily_anomalies.csv
```

## Project research report

Full narrative report (Phases 1–4, methodology, results, discussion):

- [`PROJECT_RESEARCH_REPORT.md`](PROJECT_RESEARCH_REPORT.md) — export to PDF locally if needed

## Key Design Decisions

1. Fact grain = one row per order line item
2. Delivered orders only for revenue analysis
3. English category names via translation table
4. Geolocation table excluded (customer state/city sufficient for region analysis)
