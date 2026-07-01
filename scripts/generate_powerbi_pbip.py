"""Generate Power BI Project (PBIP) semantic model for Phase 4.

Open powerbi/Olist_Ecommerce_Dashboard.pbip in Power BI Desktop,
apply theme + build visuals per docs/PHASE4_POWERBI.md, then Save As .pbix.
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
POWERBI_ROOT = PROJECT_ROOT / "powerbi"
PBIP_NAME = "Olist_Ecommerce_Dashboard"
DATA_REL = "..\\..\\data\\powerbi"

TABLES = [
    "sales_fact",
    "dim_date",
    "fact_daily",
    "fact_monthly",
    "fact_category",
    "fact_product",
    "fact_region",
    "fact_region_growth",
    "forecast_vs_actual",
    "model_comparison",
]

RELATIONSHIPS = [
    ("sales_fact", "order_date", "dim_date", "date"),
    ("fact_daily", "date", "dim_date", "date"),
    ("fact_monthly", "month_start", "dim_date", "date"),
    ("forecast_vs_actual", "date", "dim_date", "date"),
]


def m_csv_partition(table: str) -> str:
    path = f"{DATA_REL}\\\\{table}.csv"
    return f"""
    partition '{table}' = m
        mode: import
        source =
            let
                Source = Csv.Document(
                    File.Contents("{path}"),
                    [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
                ),
                #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars = true])
            in
                #"Promoted Headers"
""".strip()


def write_pbip() -> None:
    sm_dir = POWERBI_ROOT / f"{PBIP_NAME}.SemanticModel" / "definition"
    report_dir = POWERBI_ROOT / f"{PBIP_NAME}.Report" / "definition"
    sm_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    # PBIP root
    pbip = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0",
        "artifacts": [
            {"report": {"path": f"{PBIP_NAME}.Report"}},
            {"dataset": {"path": f"{PBIP_NAME}.SemanticModel"}},
        ],
        "settings": {"enableAutoRecovery": True},
    }
    (POWERBI_ROOT / f"{PBIP_NAME}.pbip").write_text(
        json.dumps(pbip, indent=2), encoding="utf-8"
    )

    # Semantic model definition.pbism
    (POWERBI_ROOT / f"{PBIP_NAME}.SemanticModel" / "definition.pbism").write_text(
        json.dumps({"version": "1.0", "datasetReference": {"byPath": {"path": "."}}}, indent=2),
        encoding="utf-8",
    )

    # database.tmdl
    table_refs = "\n".join(f"ref table {t}" for t in TABLES)
    database = f"""database
\tcompatibilityLevel: 1567

{table_refs}
"""
    (sm_dir / "database.tmdl").write_text(database, encoding="utf-8")

    # tables
    tables_dir = sm_dir / "tables"
    tables_dir.mkdir(exist_ok=True)
    for table in TABLES:
        tmdl = f"table {table}\n\n{m_csv_partition(table)}\n"
        (tables_dir / f"{table}.tmdl").write_text(tmdl, encoding="utf-8")

    # relationships.tmdl
    rel_lines = []
    for i, (from_t, from_c, to_t, to_c) in enumerate(RELATIONSHIPS, 1):
        rel_lines.append(
            f"relationship rel_{i}\n"
            f"\tfromColumn: {from_t}.{from_c}\n"
            f"\ttoColumn: {to_t}.{to_c}\n"
            f"\tcrossFilteringBehavior: oneDirection\n"
        )
    (sm_dir / "relationships.tmdl").write_text("\n".join(rel_lines), encoding="utf-8")

    # Report definition.pbir
    (POWERBI_ROOT / f"{PBIP_NAME}.Report" / "definition.pbir").write_text(
        json.dumps(
            {
                "version": "1.0",
                "datasetReference": {
                    "byPath": {"path": f"../{PBIP_NAME}.SemanticModel"}
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    pages = [
        ("ExecutiveOverview", "Executive Overview"),
        ("SalesTrends", "Sales Trends"),
        ("ProductInsights", "Product Insights"),
        ("RegionalAnalysis", "Regional Analysis"),
    ]
    pages_dir = report_dir / "pages"
    pages_dir.mkdir(exist_ok=True)
    page_order = []
    for page_id, display_name in pages:
        page_folder = pages_dir / page_id
        page_folder.mkdir(exist_ok=True)
        page_order.append(page_id)
        (page_folder / "page.json").write_text(
            json.dumps(
                {
                    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/page/1.0.0/schema.json",
                    "name": page_id,
                    "displayName": display_name,
                    "displayOption": "FitToPage",
                    "width": 1280,
                    "height": 720,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    (pages_dir / "pages.json").write_text(
        json.dumps({"pageOrder": page_order}, indent=2), encoding="utf-8"
    )

    print(f"Generated PBIP at {POWERBI_ROOT / f'{PBIP_NAME}.pbip'}")


if __name__ == "__main__":
    write_pbip()
