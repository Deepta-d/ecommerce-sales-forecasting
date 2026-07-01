-- Phase 1: Build dimension tables and sales_fact
-- Requires staging tables to be loaded first

USE olist_analytics;

-- ---------------------------------------------------------------------------
-- Dimension: customers
-- ---------------------------------------------------------------------------
DELETE FROM dim_customers;

INSERT INTO dim_customers (
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state,
    customer_location
)
SELECT
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    TRIM(customer_city),
    customer_state,
    CONCAT(TRIM(customer_city), ', ', customer_state)
FROM stg_customers;

-- ---------------------------------------------------------------------------
-- Dimension: products (with English category names)
-- ---------------------------------------------------------------------------
DELETE FROM dim_products;

INSERT INTO dim_products (
    product_id,
    product_category_name,
    product_category,
    product_weight_g
)
SELECT
    p.product_id,
    p.product_category_name,
    COALESCE(t.product_category_name_english, 'unknown') AS product_category,
    p.product_weight_g
FROM stg_products p
LEFT JOIN stg_category_translation t
    ON p.product_category_name = t.product_category_name;

-- ---------------------------------------------------------------------------
-- Dimension: orders (delivery time computed)
-- ---------------------------------------------------------------------------
DELETE FROM dim_orders;

INSERT INTO dim_orders (
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp,
    order_delivered_customer_date,
    delivery_time_days
)
SELECT
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp,
    order_delivered_customer_date,
    CASE
        WHEN order_delivered_customer_date IS NOT NULL
             AND order_purchase_timestamp IS NOT NULL
        THEN DATEDIFF(order_delivered_customer_date, order_purchase_timestamp)
        ELSE NULL
    END AS delivery_time_days
FROM stg_orders;

-- ---------------------------------------------------------------------------
-- Dimension: payments (primary payment per order)
-- ---------------------------------------------------------------------------
DELETE FROM dim_payments;

INSERT INTO dim_payments (
    order_id,
    payment_type,
    payment_installments,
    payment_value
)
SELECT
    order_id,
    COALESCE(payment_type, 'unknown') AS payment_type,
    payment_installments,
    payment_value
FROM (
    SELECT
        order_id,
        payment_type,
        payment_installments,
        payment_value,
        ROW_NUMBER() OVER (
            PARTITION BY order_id ORDER BY payment_sequential
        ) AS rn
    FROM stg_order_payments
) ranked
WHERE rn = 1;

-- ---------------------------------------------------------------------------
-- Sales fact table (grain: one row per order line item, delivered orders only)
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS sales_fact;

CREATE TABLE sales_fact (
    order_id VARCHAR(32) NOT NULL,
    order_item_id INT NOT NULL,
    order_date DATE NOT NULL,
    customer_location VARCHAR(150),
    customer_state CHAR(2),
    product_id VARCHAR(32),
    product_category VARCHAR(100),
    price DECIMAL(10, 2),
    quantity INT,
    total_revenue DECIMAL(10, 2),
    payment_type VARCHAR(20),
    delivery_time_days INT,
    PRIMARY KEY (order_id, order_item_id)
);

INSERT INTO sales_fact (
    order_id,
    order_item_id,
    order_date,
    customer_location,
    customer_state,
    product_id,
    product_category,
    price,
    quantity,
    total_revenue,
    payment_type,
    delivery_time_days
)
SELECT
    oi.order_id,
    oi.order_item_id,
    DATE(o.order_purchase_timestamp) AS order_date,
    c.customer_location,
    c.customer_state,
    oi.product_id,
    pr.product_category,
    oi.price,
    1 AS quantity,
    oi.price + oi.freight_value AS total_revenue,
    COALESCE(p.payment_type, 'unknown') AS payment_type,
    o.delivery_time_days
FROM stg_order_items oi
INNER JOIN dim_orders o ON oi.order_id = o.order_id
INNER JOIN dim_customers c ON o.customer_id = c.customer_id
LEFT JOIN dim_products pr ON oi.product_id = pr.product_id
LEFT JOIN dim_payments p ON oi.order_id = p.order_id
WHERE o.order_status = 'delivered';

-- Indexes for analytical queries
CREATE INDEX idx_sales_fact_order_date ON sales_fact (order_date);
CREATE INDEX idx_sales_fact_category ON sales_fact (product_category);
CREATE INDEX idx_sales_fact_state ON sales_fact (customer_state);
CREATE INDEX idx_sales_fact_product ON sales_fact (product_id);
