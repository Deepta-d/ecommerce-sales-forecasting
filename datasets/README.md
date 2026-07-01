# Olist Dataset Files

Place the [Olist Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) CSV files in this folder before running the pipeline.

## Required files (8)

| File | Used in pipeline |
|------|------------------|
| `olist_orders_dataset.csv` | Yes |
| `olist_order_items_dataset.csv` | Yes |
| `olist_customers_dataset.csv` | Yes |
| `olist_products_dataset.csv` | Yes |
| `olist_order_payments_dataset.csv` | Yes |
| `product_category_name_translation.csv` | Yes |
| `olist_sellers_dataset.csv` | Yes |
| `olist_order_reviews_dataset.csv` | Yes |

**Not required:** `olist_geolocation_dataset.csv` (excluded — customer state/city is sufficient).

## Daily incremental loads (optional)

Drop delta CSV exports into `datasets/incremental/` with the same filenames, then run:

```bash
python scripts/run_daily_pipeline.py
```

Raw CSVs are **not** committed to Git due to size (~120 MB). Clone the repo, download from Kaggle, and run `python scripts/run_pipeline.py`.
