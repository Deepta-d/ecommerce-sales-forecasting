-- Phase 1: 14 analytical business queries
-- Run against olist_analytics.sales_fact (and staging where noted)

USE olist_analytics;

-- ---------------------------------------------------------------------------
-- Query 1: Daily sales
-- ---------------------------------------------------------------------------
SELECT
    order_date,
    ROUND(SUM(total_revenue), 2) AS daily_revenue,
    COUNT(DISTINCT order_id) AS order_count
FROM sales_fact
GROUP BY order_date
ORDER BY order_date;

-- ---------------------------------------------------------------------------
-- Query 2: Monthly revenue
-- ---------------------------------------------------------------------------
SELECT
    DATE_FORMAT(order_date, '%Y-%m') AS year_month,
    ROUND(SUM(total_revenue), 2) AS monthly_revenue,
    COUNT(DISTINCT order_id) AS order_count
FROM sales_fact
GROUP BY DATE_FORMAT(order_date, '%Y-%m')
ORDER BY year_month;

-- ---------------------------------------------------------------------------
-- Query 3: Revenue by category
-- ---------------------------------------------------------------------------
SELECT
    product_category,
    ROUND(SUM(total_revenue), 2) AS category_revenue,
    COUNT(*) AS items_sold
FROM sales_fact
GROUP BY product_category
ORDER BY category_revenue DESC;

-- ---------------------------------------------------------------------------
-- Query 4: Revenue by region (state)
-- ---------------------------------------------------------------------------
SELECT
    customer_state,
    ROUND(SUM(total_revenue), 2) AS region_revenue,
    COUNT(DISTINCT order_id) AS order_count
FROM sales_fact
GROUP BY customer_state
ORDER BY region_revenue DESC;

-- ---------------------------------------------------------------------------
-- Query 5: Average order value (AOV) — overall
-- ---------------------------------------------------------------------------
SELECT
    ROUND(SUM(total_revenue) / COUNT(DISTINCT order_id), 2) AS avg_order_value
FROM sales_fact;

-- ---------------------------------------------------------------------------
-- Query 6: Top-selling products (by revenue)
-- ---------------------------------------------------------------------------
SELECT
    product_id,
    ROUND(SUM(total_revenue), 2) AS product_revenue,
    COUNT(*) AS units_sold
FROM sales_fact
GROUP BY product_id
ORDER BY product_revenue DESC
LIMIT 20;

-- ---------------------------------------------------------------------------
-- Query 7: Customer repeat rate
-- ---------------------------------------------------------------------------
SELECT
    ROUND(
        100.0 * SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) AS repeat_customer_pct,
    COUNT(*) AS total_unique_customers,
    SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) AS repeat_customers
FROM (
    SELECT
        c.customer_unique_id,
        COUNT(DISTINCT o.order_id) AS order_count
    FROM stg_orders o
    INNER JOIN stg_customers c ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
) customer_orders;

-- ---------------------------------------------------------------------------
-- Query 8: Revenue by payment type
-- ---------------------------------------------------------------------------
SELECT
    payment_type,
    ROUND(SUM(total_revenue), 2) AS payment_revenue,
    COUNT(DISTINCT order_id) AS order_count
FROM sales_fact
GROUP BY payment_type
ORDER BY payment_revenue DESC;

-- ---------------------------------------------------------------------------
-- Query 9: Average delivery time by state
-- ---------------------------------------------------------------------------
SELECT
    customer_state,
    ROUND(AVG(delivery_time_days), 2) AS avg_delivery_days,
    COUNT(*) AS item_count
FROM sales_fact
WHERE delivery_time_days IS NOT NULL
GROUP BY customer_state
ORDER BY avg_delivery_days DESC;

-- ---------------------------------------------------------------------------
-- Query 10: Orders per month
-- ---------------------------------------------------------------------------
SELECT
    DATE_FORMAT(order_date, '%Y-%m') AS year_month,
    COUNT(DISTINCT order_id) AS monthly_orders
FROM sales_fact
GROUP BY DATE_FORMAT(order_date, '%Y-%m')
ORDER BY year_month;

-- ---------------------------------------------------------------------------
-- Query 11: Category share (% of total revenue)
-- ---------------------------------------------------------------------------
SELECT
    product_category,
    ROUND(SUM(total_revenue), 2) AS category_revenue,
    ROUND(
        100.0 * SUM(total_revenue) / SUM(SUM(total_revenue)) OVER (),
        2
    ) AS revenue_share_pct
FROM sales_fact
GROUP BY product_category
ORDER BY revenue_share_pct DESC;

-- ---------------------------------------------------------------------------
-- Query 12: Weekend vs weekday sales
-- ---------------------------------------------------------------------------
SELECT
    CASE
        WHEN DAYOFWEEK(order_date) IN (1, 7) THEN 'Weekend'
        ELSE 'Weekday'
    END AS day_type,
    ROUND(SUM(total_revenue), 2) AS total_revenue,
    COUNT(DISTINCT order_id) AS order_count,
    ROUND(AVG(total_revenue), 2) AS avg_item_revenue
FROM sales_fact
GROUP BY
    CASE
        WHEN DAYOFWEEK(order_date) IN (1, 7) THEN 'Weekend'
        ELSE 'Weekday'
    END;

-- ---------------------------------------------------------------------------
-- Query 13: Top 10 cities by revenue
-- ---------------------------------------------------------------------------
SELECT
    customer_location,
    customer_state,
    ROUND(SUM(total_revenue), 2) AS city_revenue,
    COUNT(DISTINCT order_id) AS order_count
FROM sales_fact
GROUP BY customer_location, customer_state
ORDER BY city_revenue DESC
LIMIT 10;

-- ---------------------------------------------------------------------------
-- Query 14: Monthly AOV trend
-- ---------------------------------------------------------------------------
SELECT
    DATE_FORMAT(order_date, '%Y-%m') AS year_month,
    ROUND(SUM(total_revenue), 2) AS monthly_revenue,
    COUNT(DISTINCT order_id) AS monthly_orders,
    ROUND(SUM(total_revenue) / COUNT(DISTINCT order_id), 2) AS monthly_aov
FROM sales_fact
GROUP BY DATE_FORMAT(order_date, '%Y-%m')
ORDER BY year_month;

-- ---------------------------------------------------------------------------
-- Query 15: Daily sales with z-score anomaly flags (top 20 by |z|)
-- ---------------------------------------------------------------------------
SELECT
    order_date,
    daily_revenue,
    z_score,
    CASE WHEN ABS(z_score) > 2 THEN 'anomaly' ELSE 'normal' END AS anomaly_flag
FROM (
    SELECT
        order_date,
        ROUND(SUM(total_revenue), 2) AS daily_revenue,
        ROUND(
            (SUM(total_revenue) - AVG(SUM(total_revenue)) OVER ())
            / STDDEV_POP(SUM(total_revenue)) OVER (),
            2
        ) AS z_score
    FROM sales_fact
    GROUP BY order_date
) scored
ORDER BY ABS(z_score) DESC
LIMIT 20;
