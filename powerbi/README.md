# Power BI Dashboard — Phase 4

## Deliverables in this folder

| Item | Description |
|------|-------------|
| `Olist_Ecommerce_Dashboard.pbip` | Power BI **project** — open in Desktop (model + 4 named pages) |
| `Olist_Ecommerce_Dashboard.pbix` | **You create this** — File → Save As after building visuals |
| `theme/OlistFuturistic.json` | Dark neon 3D-style theme |
| `assets/background.png` | Page background gradient |
| `dax/measures.dax` | KPI measures to paste into `_Metrics` table |
| `power_query/load_tables.pq` | Power Query reference |

## Create the .pbix file

1. Run `python scripts/setup_phase4.py` from project root
2. Double-click `Olist_Ecommerce_Dashboard.pbip`
3. If CSV load fails, use **Get Data → Text/CSV** and load all files from `data/powerbi/`
4. Apply theme and build pages per [docs/PHASE4_POWERBI.md](../docs/PHASE4_POWERBI.md)
5. **File → Save As** → `Olist_Ecommerce_Dashboard.pbix` (save in this folder)

Data source: `data/powerbi/*.csv` (regenerate with `python scripts/export_powerbi_data.py`).
