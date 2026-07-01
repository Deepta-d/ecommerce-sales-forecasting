-- Phase 1: Staging and dimension table DDL
-- Run after 01_create_database.sql (as olist_user or root)

USE olist_analytics;

-- ---------------------------------------------------------------------------
-- Staging tables (mirror CSV schemas)
-- ---------------------------------------------------------------------------

DROP TABLE IF EXISTS stg_order_reviews;
DROP TABLE IF EXISTS stg_sellers;
DROP TABLE IF EXISTS stg_order_payments;
DROP TABLE IF EXISTS stg_order_items;
DROP TABLE IF EXISTS stg_orders;
DROP TABLE IF EXISTS stg_products;
DROP TABLE IF EXISTS stg_customers;
DROP TABLE IF EXISTS stg_category_translation;

CREATE TABLE stg_orders (
    order_id VARCHAR(32) NOT NULL,
    customer_id VARCHAR(32) NOT NULL,
    order_status VARCHAR(20),
    order_purchase_timestamp DATETIME,
    order_approved_at DATETIME,
    order_delivered_carrier_date DATETIME,
    order_delivered_customer_date DATETIME,
    order_estimated_delivery_date DATETIME,
    PRIMARY KEY (order_id),
    INDEX idx_stg_orders_customer (customer_id),
    INDEX idx_stg_orders_status (order_status)
);

CREATE TABLE stg_order_items (
    order_id VARCHAR(32) NOT NULL,
    order_item_id INT NOT NULL,
    product_id VARCHAR(32) NOT NULL,
    seller_id VARCHAR(32) NOT NULL,
    shipping_limit_date DATETIME,
    price DECIMAL(10, 2),
    freight_value DECIMAL(10, 2),
    PRIMARY KEY (order_id, order_item_id),
    INDEX idx_stg_items_product (product_id),
    INDEX idx_stg_items_seller (seller_id)
);

CREATE TABLE stg_customers (
    customer_id VARCHAR(32) NOT NULL,
    customer_unique_id VARCHAR(32) NOT NULL,
    customer_zip_code_prefix VARCHAR(10),
    customer_city VARCHAR(100),
    customer_state CHAR(2),
    PRIMARY KEY (customer_id),
    INDEX idx_stg_customers_unique (customer_unique_id)
);

CREATE TABLE stg_products (
    product_id VARCHAR(32) NOT NULL,
    product_category_name VARCHAR(100),
    product_name_lenght DECIMAL(10, 2),
    product_description_lenght DECIMAL(10, 2),
    product_photos_qty DECIMAL(10, 2),
    product_weight_g DECIMAL(10, 2),
    product_length_cm DECIMAL(10, 2),
    product_height_cm DECIMAL(10, 2),
    product_width_cm DECIMAL(10, 2),
    PRIMARY KEY (product_id),
    INDEX idx_stg_products_category (product_category_name)
);

CREATE TABLE stg_order_payments (
    order_id VARCHAR(32) NOT NULL,
    payment_sequential INT NOT NULL,
    payment_type VARCHAR(20),
    payment_installments INT,
    payment_value DECIMAL(10, 2),
    PRIMARY KEY (order_id, payment_sequential),
    INDEX idx_stg_payments_type (payment_type)
);

CREATE TABLE stg_category_translation (
    product_category_name VARCHAR(100) NOT NULL,
    product_category_name_english VARCHAR(100),
    PRIMARY KEY (product_category_name)
);

CREATE TABLE stg_sellers (
    seller_id VARCHAR(32) NOT NULL,
    seller_zip_code_prefix VARCHAR(10),
    seller_city VARCHAR(100),
    seller_state CHAR(2),
    PRIMARY KEY (seller_id)
);

CREATE TABLE stg_order_reviews (
    review_id VARCHAR(32) NOT NULL,
    order_id VARCHAR(32) NOT NULL,
    review_score INT,
    review_comment_title VARCHAR(255),
    review_comment_message TEXT,
    review_creation_date DATETIME,
    review_answer_timestamp DATETIME,
    PRIMARY KEY (review_id),
    INDEX idx_stg_reviews_order (order_id)
);

-- ---------------------------------------------------------------------------
-- Dimension tables (cleaned layer) — populated in 03_sales_fact.sql
-- ---------------------------------------------------------------------------

DROP TABLE IF EXISTS dim_payments;
DROP TABLE IF EXISTS dim_orders;
DROP TABLE IF EXISTS dim_products;
DROP TABLE IF EXISTS dim_customers;

CREATE TABLE dim_customers (
    customer_id VARCHAR(32) NOT NULL,
    customer_unique_id VARCHAR(32) NOT NULL,
    customer_zip_code_prefix VARCHAR(10),
    customer_city VARCHAR(100),
    customer_state CHAR(2),
    customer_location VARCHAR(150),
    PRIMARY KEY (customer_id),
    INDEX idx_dim_customers_state (customer_state)
);

CREATE TABLE dim_products (
    product_id VARCHAR(32) NOT NULL,
    product_category_name VARCHAR(100),
    product_category VARCHAR(100) NOT NULL,
    product_weight_g DECIMAL(10, 2),
    PRIMARY KEY (product_id),
    INDEX idx_dim_products_category (product_category)
);

CREATE TABLE dim_orders (
    order_id VARCHAR(32) NOT NULL,
    customer_id VARCHAR(32) NOT NULL,
    order_status VARCHAR(20),
    order_purchase_timestamp DATETIME,
    order_delivered_customer_date DATETIME,
    delivery_time_days INT,
    PRIMARY KEY (order_id),
    INDEX idx_dim_orders_purchase (order_purchase_timestamp)
);

CREATE TABLE dim_payments (
    order_id VARCHAR(32) NOT NULL,
    payment_type VARCHAR(20) NOT NULL,
    payment_installments INT,
    payment_value DECIMAL(10, 2),
    PRIMARY KEY (order_id)
);
