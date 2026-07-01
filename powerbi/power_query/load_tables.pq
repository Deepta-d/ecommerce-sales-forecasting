// Power BI — Power Query (Advanced Editor)
// Set project root once, then load all CSV tables from data/powerbi/

let
    ProjectRoot = "D:\E-commerce Sales forecasting",
    DataFolder = ProjectRoot & "\data\powerbi",
    LoadCsv = (fileName as text) =>
        let
            Source = Csv.Document(
                File.Contents(DataFolder & "\" & fileName),
                [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
            ),
            Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
            Typed = Table.TransformColumnTypes(
                Promoted,
                List.Transform(
                    Table.ColumnNames(Promoted),
                    each {_, type text}
                )
            )
        in
            Typed,
    sales_fact =
        let
            T = LoadCsv("sales_fact.csv"),
            Changed = Table.TransformColumnTypes(
                T,
                {
                    {"order_date", type date},
                    {"price", type number},
                    {"quantity", Int64.Type},
                    {"total_revenue", type number},
                    {"payment_installments", Int64.Type},
                    {"delivery_time_days", Int64.Type}
                }
            )
        in
            Changed,
    dim_date =
        let
            T = LoadCsv("dim_date.csv"),
            Changed = Table.TransformColumnTypes(
                T,
                {
                    {"date", type date},
                    {"year", Int64.Type},
                    {"quarter", Int64.Type},
                    {"month", Int64.Type},
                    {"day_of_week", Int64.Type},
                    {"is_weekend", type logical}
                }
            )
        in
            Changed,
    fact_daily =
        let
            T = LoadCsv("fact_daily.csv"),
            Changed = Table.TransformColumnTypes(
                T,
                {
                    {"date", type date},
                    {"revenue", type number},
                    {"orders", Int64.Type},
                    {"items", Int64.Type},
                    {"aov", type number}
                }
            )
        in
            Changed,
    fact_monthly =
        let
            T = LoadCsv("fact_monthly.csv"),
            Changed = Table.TransformColumnTypes(
                T,
                {
                    {"month_start", type date},
                    {"revenue", type number},
                    {"orders", Int64.Type},
                    {"aov", type number},
                    {"revenue_growth_pct", type number}
                }
            )
        in
            Changed,
    fact_category = LoadCsv("fact_category.csv"),
    fact_product = LoadCsv("fact_product.csv"),
    fact_region = LoadCsv("fact_region.csv"),
    fact_region_growth = LoadCsv("fact_region_growth.csv"),
    forecast_vs_actual =
        let
            T = LoadCsv("forecast_vs_actual.csv"),
            Changed = Table.TransformColumnTypes(
                T,
                {
                    {"date", type date},
                    {"actual", type number},
                    {"forecast", type number},
                    {"forecast_error", type number},
                    {"forecast_error_pct", type number}
                }
            )
        in
            Changed,
    model_comparison = LoadCsv("model_comparison.csv")
in
    sales_fact

// Duplicate this query for each table name above, changing the final `in` clause.
// Or use Power BI: Get Data → Text/CSV → select each file in data/powerbi/
