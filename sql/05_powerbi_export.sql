-- Phase 4: Power BI export view (enriched sales_fact)
-- Run after 03_sales_fact.sql. Does not modify sales_fact.

USE olist_analytics;

DROP VIEW IF EXISTS v_sales_fact_powerbi;

CREATE VIEW v_sales_fact_powerbi AS
SELECT
    sf.order_id,
    sf.order_item_id,
    sf.order_date,
    sf.customer_location,
    c.customer_city,
    sf.customer_state,
    sf.product_id,
    sf.product_category,
    sf.price,
    sf.quantity,
    sf.total_revenue,
    sf.payment_type,
    p.payment_installments,
    sf.delivery_time_days
FROM sales_fact sf
LEFT JOIN dim_orders o ON sf.order_id = o.order_id
LEFT JOIN dim_customers c ON o.customer_id = c.customer_id
LEFT JOIN dim_payments p ON sf.order_id = p.order_id;
