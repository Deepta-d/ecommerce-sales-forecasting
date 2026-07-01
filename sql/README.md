# SQL Scripts — Phase 1

Run these scripts **in order** against local MySQL 8.x.

## Prerequisites

- MySQL Server 8.x running locally
- Python environment with dependencies from `requirements.txt`

## Quick start (automated)

```bash
# 1. Copy and edit credentials
copy .env.example .env

# 2. Set MYSQL_ROOT_PASSWORD in .env to your MySQL root password

# 3. Run full pipeline (setup, load CSVs, build fact table, validate)
python scripts/run_pipeline.py
```

## Manual execution (MySQL Workbench)

| Order | File | Run as | Purpose |
|-------|------|--------|---------|
| 1 | `01_create_database.sql` | root | Create `olist_analytics` DB and `olist_user` |
| 2 | `02_create_tables.sql` | olist_user | Create staging + dimension DDL |
| 3 | — | — | Run `python scripts/load_csv_to_mysql.py` |
| 4 | `03_sales_fact.sql` | olist_user | Build dimensions and `sales_fact` |
| 5 | `04_analytical_queries.sql` | olist_user | 15 business queries (+ anomaly query) |
| 6 | `05_powerbi_export.sql` | root (optional) | View `v_sales_fact_powerbi` for Power BI; export script uses inline join if view unavailable |

## Default credentials (.env.example)

| Variable | Default |
|----------|---------|
| DB_HOST | localhost |
| DB_PORT | 3306 |
| DB_NAME | olist_analytics |
| DB_USER | olist_user |
| DB_PASSWORD | olist_pass |

## Expected row counts (approximate)

| Table | Rows |
|-------|------|
| stg_orders | 99,441 |
| stg_order_items | 112,650 |
| stg_customers | 99,441 |
| stg_products | 32,951 |
| stg_order_payments | 103,886 |
| stg_category_translation | 71 |
| sales_fact | ~96,000–97,000 (delivered line items) |
