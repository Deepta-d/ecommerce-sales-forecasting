-- Phase 1: Create database and application user
-- Run as MySQL root (Workbench or CLI)

CREATE DATABASE IF NOT EXISTS olist_analytics
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'olist_user'@'localhost' IDENTIFIED BY 'olist_pass';

GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER
    ON olist_analytics.*
    TO 'olist_user'@'localhost';

FLUSH PRIVILEGES;

USE olist_analytics;
