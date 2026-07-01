# Phase 4: Power BI Dashboard

Build the **Olist E-Commerce Dashboard** (`.pbix`) from CSV exports and the futuristic theme in this repo.

## Quick start

```bash
# 1. Ensure MySQL pipeline + forecasts are current
python scripts/run_pipeline.py
python scripts/run_forecast.py

# 2. Export Power BI datasets
python scripts/export_powerbi_data.py

# 3. Validate exports vs SQL
python scripts/validate_powerbi_export.py

# 4. Generate / refresh PBIP project (optional)
python scripts/generate_powerbi_pbip.py
```

Open **`powerbi/Olist_Ecommerce_Dashboard.pbip`** in Power BI Desktop (double-click or File → Open).

Apply theme: **View → Themes → Browse for themes** → `powerbi/theme/OlistFuturistic.json`

Set page background: **Format page → Page background → Image** → `powerbi/assets/background.png` (transparency ~20%).

**Save As** → `powerbi/Olist_Ecommerce_Dashboard.pbix`

---

## Data files (`data/powerbi/`)

| Table | Rows (approx) | Use |
|-------|---------------|-----|
| `sales_fact.csv` | 110,197 | Main fact — drill-down to line item |
| `dim_date.csv` | 714 | Date slicer + hierarchies |
| `fact_daily.csv` | 612 | Daily trend charts |
| `fact_monthly.csv` | 23 | Monthly bars + growth % |
| `fact_category.csv` | 72 | Top categories |
| `fact_product.csv` | 32,216 | Product rank / low performers |
| `fact_region.csv` | 4,272 | State + city map/bar |
| `fact_region_growth.csv` | 442 | High-growth regions (MoM %) |
| `forecast_vs_actual.csv` | 270 | Long format: date × model |
| `model_comparison.csv` | 9 | MAE/RMSE/MAPE by horizon |

**Extended columns on `sales_fact`:** `customer_city`, `payment_installments` (joined from dimensions).

---

## Semantic model — relationships

| From | To | Cardinality |
|------|-----|-------------|
| `sales_fact[order_date]` | `dim_date[date]` | *:1 |
| `fact_daily[date]` | `dim_date[date]` | 1:1 |
| `fact_monthly[month_start]` | `dim_date[date]` | *:1 |
| `forecast_vs_actual[date]` | `dim_date[date]` | *:1 |

Disable **auto-detect** when loading CSVs; create relationships manually in Model view.

Create empty table **`_Metrics`** (Enter Data → blank → rename) and paste measures from [`powerbi/dax/measures.dax`](../powerbi/dax/measures.dax).

---

## Page 1 — Executive Overview

**KPI cards (4 across top):**

| Card | Field |
|------|--------|
| Total Revenue | `[Total Revenue]` |
| Total Orders | `[Total Orders]` |
| Average Order Value | `[Average Order Value]` |
| Growth % | `[Revenue Growth %]` — format as % |

**Chart:** Line or area — `fact_monthly[month_start]` × `fact_monthly[revenue]`

**Drill-down:** Add `dim_date` hierarchy to axis: Year → Quarter → Month

**Slicers (sync on all pages):**

- `sales_fact[customer_state]` — dropdown
- `sales_fact[product_category]` — dropdown
- `dim_date[date]` — **Between** / relative date filter

**3D-style layout:** Group KPIs in a rectangle shape with dark fill `#1A1F3A`, 8px padding, neon border `#00E5FF`.

---

## Page 2 — Sales Trends

**Left:** Line chart — `fact_daily[date]` × `[Daily Revenue]`

**Right:** Clustered column — `fact_monthly[year_month]` × `fact_monthly[revenue]`

**Bottom (full width):** Line chart — `forecast_vs_actual[date]`  
- Values: `actual` (line, white, thick), `forecast` (legend: `model_name`)  
- Slicer: `model_name` (ARIMA, Prophet, LSTM)

**Bookmark (optional):** Toggle Daily vs Monthly focus

**Tooltip card:** `model_comparison` — show MAPE for selected model

---

## Page 3 — Product Insights

**Top categories:** Horizontal bar — Top 10 `fact_category[product_category]` by `fact_category[revenue]`  
- Sort descending, gradient data color cyan → magenta

**Low performers:** Table — filter `fact_product[performance_tier] = bottom`  
- Columns: `product_id`, `product_category`, `revenue`, `orders`

**Drill-down:** Enable on category bar → product level via `sales_fact` or `fact_product`

---

## Page 4 — Regional Analysis

**Map:** Filled map — `fact_region[customer_state]` (Brazil), color by `SUM(fact_region[revenue])`  
- Location: State/Province, country Brazil

**Bar chart:** Top 15 cities — `fact_region[customer_city]` by revenue (filter top N)

**Table:** `fact_region_growth` — columns: state, year_month, mom_growth_pct  
- Sort by `mom_growth_pct` descending; filter `orders >= 10`

**Drill-down:** State → City on bar chart 

---

## Slicer sync

Select all region/category/date slicers → **View → Sync slicers** → check all four pages.

---

## Refresh workflow

After daily pipeline:

```bash
python scripts/run_daily_pipeline.py   # includes export step
```

In Power BI Desktop: **Home → Refresh** (CSV paths must remain at `data/powerbi/`).

Update `ProjectRoot` in [`powerbi/power_query/load_tables.pq`](../powerbi/power_query/load_tables.pq) if the repo moves.

---

## Validation checklist

- [ ] `python scripts/validate_powerbi_export.py` passes
- [ ] KPI AOV ≈ R$ 159.83
- [ ] Forecast page shows 90 days × 3 models
- [ ] Brazil map renders state codes (SP, RJ, MG, …)
- [ ] Slicers filter all pages
- [ ] Theme applied; page background image set

---

## Files in `powerbi/`

| Path | Purpose |
|------|---------|
| `Olist_Ecommerce_Dashboard.pbip` | Project entry (open in Desktop) |
| `theme/OlistFuturistic.json` | Dark neon theme |
| `assets/background.png` | Page depth background |
| `dax/measures.dax` | KPI measures |
| `power_query/load_tables.pq` | M query reference |
